"""
web/app.py
----------
Flask MJPEG stream — headless-friendly.
Browse to http://<pi-ip>:5000 from any device on the same network.

Per-frame pipeline:
  camera → detections → tracker (with LOCK/UNLOCK) → compute steer/cmd
  → state machine → motors → HUD overlay → JPEG → browser
"""

import time
import cv2
from flask import Flask, Response, render_template_string, jsonify, request
import threading

from app.vision.oakd_pipeline import build_pipeline, frame_generator
from app.vision.utils import draw_person_detections, draw_hud
from app.vision.tracking import PersonTracker
from app.navigation.follow_logic import compute_follow_cmd
from app.navigation.state_machine import StateMachine, WagonState
import app.control.motor_pwm as motor_pwm
import app.control.brain as brain
import app.control.serial as serial
from app.config.settings import FLASK_HOST, FLASK_PORT, JPEG_QUALITY
import atexit

flask_app = Flask(__name__)

# Global tracker — persists across frames in the stream
_tracker = PersonTracker()
_detection_lock = threading.Lock()
_shared = {
    "detections": [], "frame" : None
}

_INDEX = """
<!doctype html>
<html>
<head>
  <title>Autonomous Wagon</title>
  <style>
    body { background:#111; color:#eee; font-family:monospace; text-align:center; margin:0; padding:10px; }
    #video-feed { max-width:100%; border:2px solid #0f0; margin-top:12px; cursor:crosshair; display:block; margin-left:auto; margin-right:auto; }
    .controls { margin-bottom:15px; }
    button { padding:10px 20px; margin:5px; font-size:16px; cursor:pointer; border:none; border-radius:5px; }
    .unlock-btn { background:#f00; color:#fff; font-weight:bold; }
    .unlock-btn:hover { background:#d00; }
    .status { margin-top:10px; font-size:14px; color:#ffff00; }
  </style>
  <script>
    async function handleVideoClick(event) {
      // Get the image element and its rendered size in the browser
      const img = document.getElementById('video-feed');
      const rect = img.getBoundingClientRect();

      // img.naturalWidth/Height is the actual frame size (640x352)
      // rect.width/height is how big it appears on screen
      // We scale the click to match actual frame coordinates
      const scaleX = img.naturalWidth  / rect.width;
      const scaleY = img.naturalHeight / rect.height;
      const frameX = Math.round((event.clientX - rect.left) * scaleX);
      const frameY = Math.round((event.clientY - rect.top)  * scaleY);

      try {
        const response = await fetch('/lock', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({x: frameX, y: frameY})
        });
        const data = await response.json();
        updateStatus(data);
      } catch (err) {
        console.error('Lock error:', err);
      }
    }

    async function unlock() {
      try {
        const response = await fetch('/unlock', {method: 'POST'});
        const data = await response.json();
        updateStatus(data);
      } catch (err) {
        console.error('Unlock error:', err);
      }
    }

    function updateStatus(data) {
      const status = document.getElementById('status');
      const btn = document.getElementById('unlock-btn');
      if (data.locked) {
        // Show UNLOCK button and update status
        status.textContent = 'LOCKED — following person | missed=' + data.missed_frames;
        status.style.color = '#00ff00';
        btn.style.display = 'inline-block';
      } else if (data.is_lost) {
        status.textContent = 'Person LOST — click on someone to re-lock';
        status.style.color = '#ff4400';
        btn.style.display = 'none';
      } else {
        status.textContent = 'Click on a person in the video to lock';
        status.style.color = '#ffff00';
        btn.style.display = 'none';
      }
    }
  </script>
</head>
<body>
  <h2>Autonomous Wagon — Live Feed & Control</h2>
  <div class="controls">
    <!-- UNLOCK button — only visible when locked -->
    <button id="unlock-btn" class="unlock-btn" onclick="unlock()" style="display:none;">
      UNLOCK
    </button>
  </div>
  <div class="status" id="status">Click on a person in the video to lock</div>
  <!-- cursor:crosshair shows the user the video is clickable -->
  <img id="video-feed" src="/video" onclick="handleVideoClick(event)">
</body>
</html>
"""

@flask_app.route("/")
def index():
    return render_template_string(_INDEX)


@flask_app.route("/lock", methods=["POST"])
def lock_person():
    
    # Parse the JSON body sent by the browser click handler
    # Expected format: {"x": 312, "y": 180}

    data = request.get_json()
    click_x = data.get("x")
    click_y = data.get("y")
    with _detection_lock:
      dets = list(_shared["detections"])
      frm = _shared["frame"].copy() if _shared["frame"] is not None else None
        

    # If the click had no coordinates or there are no detections yet,
    # return current state without changing anything
    if click_x is None or not dets:
        return jsonify({
            "locked": _tracker.locked,
            "missed_frames": _tracker.missed_frames,
            "is_lost": _tracker.is_lost,
            "message": "No detections available"
        })

    # Step 1: Check if the click lands inside any bounding box
    clicked_box = None
    for det in dets:
        x1, y1, x2, y2, conf, *_ = det
        if x1 <= click_x <= x2 and y1 <= click_y <= y2:
            clicked_box = det
            break

    # Step 2: Fallback — find nearest box if click missed all boxes
    if clicked_box is None:
        best_dist = float("inf")
        for det in dets:
            x1, y1, x2, y2, conf, *_ = det
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            dist = ((cx - click_x) ** 2 + (cy - click_y) ** 2) ** 0.5
            if dist < best_dist:
                best_dist = dist
                clicked_box = det

    # Step 3: Lock the tracker onto the chosen person
    if clicked_box is not None and frm is not None:
        _tracker.lock(clicked_box, frm)

    # Return updated tracker state to the browser so the UI can update
    return jsonify({
        "locked": _tracker.locked,
        "missed_frames": _tracker.missed_frames,
        "is_lost": _tracker.is_lost
    })



@flask_app.route("/unlock", methods=["POST"])
def unlock_person():
    """Called when user clicks UNLOCK button."""
    _tracker.unlock()
    return jsonify({
        "locked": _tracker.locked,
        "missed_frames": _tracker.missed_frames,
        "is_lost": _tracker.is_lost
    })


@flask_app.route("/video")
def video():
    return Response(_stream(), mimetype="multipart/x-mixed-replace; boundary=frame")


def _stream():
    """
    Core generator: camera → detection → tracker → navigation → motor → JPEG.
    
    Tracker modes:
      - Not locked: shows detections but wagon doesn't move
      - Locked: tracks person with position/color/size matching
      - Lost: person disappeared > 10 frames, wagon freezes
    """
    sm = StateMachine()

    pipeline, device, q_rgb, q_nn, q_depth, q_imu = build_pipeline()


    start    = time.monotonic()
    nn_count = 0
    last_detections = []

    try:
          for frame, detections in frame_generator(pipeline,device, q_rgb, q_nn, q_depth, q_imu ):
            nn_count +=1
            if detections:
              last_detections = detections
            else:
                detections = last_detections

            with _detection_lock:
                _shared["detections"] = detections
                _shared["frame"] = frame.copy()
    
            person_count = draw_person_detections(frame, detections)
            target = _tracker.update(detections, frame)

            area = 0
            if target is not None:
                x1, y1, x2, y2, conf, *_ = target
                area = (x2 - x1)*(y2-y1)

            if not _tracker.locked or _tracker.is_lost:
                cmd, steer, speed_factor, frame_center = "STOP", 0.0, 0.0, frame.shape[1] // 2
            else:
                cmd, steer, speed_factor, frame_center = compute_follow_cmd(frame, target, area)

            state = sm.update(cmd)


            
# Temporary auto-lock for motor testing — remove when click-to-lock is fixed
            
            
            # Control — send speeds to motors (only if LOCKED)
            # Unlock disables motor control for safety
            if _tracker.locked:
                brain.execute(state, steer, speed_factor)
                serial.send(cmd, steer)
            else:
                # Not tracking — disable motors
                brain.execute(WagonState.STOP, 0.0, 0.0)
                serial.send("STOP", 0.0)
            

            # HUD — paint telemetry onto the frame
            nn_fps = nn_count / max(1e-6, time.monotonic() - start)
            
            # Add tracker status to HUD
            tracker_status = ""
            if _tracker.locked:
                tracker_status = f"  [LOCKED] missed={_tracker.missed_frames}"
            elif _tracker.is_lost:
                tracker_status = "  [LOST — person disappeared]"
            else:
                tracker_status = "  [IDLE — click LOCK to track]"
            
            draw_hud(frame, cmd, steer, person_count, nn_fps, target, frame_center, speed_factor)
            
            # Draw tracker status on frame
            cv2.putText(frame, tracker_status, (8, frame.shape[0] - 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)

            # Encode and stream
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]
            ok, jpg = cv2.imencode(".jpg", frame, encode_params)
            if not ok:
                continue

            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n"
                   + jpg.tobytes()
                   + b"\r\n")
    finally:
        # Device cleanup is handled by the context manager in frame_generator
        pass


def create_app():
    """Initialise hardware (motor PWM, serial) then return the Flask app."""
    motor_pwm.init()
    serial.init()

    atexit.register(motor_pwm.cleanup)
    return flask_app


if __name__ == "__main__":
    app = create_app()
    app.run(host=FLASK_HOST, port=FLASK_PORT, threaded=True)