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

from app.vision.oakd_camera import build_pipeline, frame_generator
from app.vision.utils import draw_person_detections, draw_hud
from app.vision.tracking import PersonTracker
from app.navigation.follow_logic import compute_follow_cmd
from app.navigation.state_machine import StateMachine, WagonState
from app.control import brain, motor_pwm, serial
from app.config.settings import FLASK_HOST, FLASK_PORT, JPEG_QUALITY

flask_app = Flask(__name__)

# Global tracker — persists across frames in the stream
_tracker = PersonTracker()

_INDEX = """
<!doctype html>
<html>
<head>
  <title>Autonomous Wagon</title>
  <style>
    body { background:#111; color:#eee; font-family:monospace; text-align:center; margin:0; padding:10px; }
    img  { max-width:100%; border:2px solid #0f0; margin-top:12px; }
    .controls { margin-bottom:15px; }
    button { padding:10px 20px; margin:5px; font-size:16px; cursor:pointer; border:none; border-radius:5px; }
    .lock-btn { background:#0f0; color:#000; font-weight:bold; }
    .lock-btn:hover { background:#0d0; }
    .lock-btn.locked { background:#f00; }
    .lock-btn.locked:hover { background:#d00; }
    .status { margin-top:10px; font-size:14px; color:#ffff00; }
  </style>
  <script>
    let isLocked = false;
    
    async function toggleLock() {
      const btn = document.getElementById('lock-btn');
      const endpoint = isLocked ? '/unlock' : '/lock';
      try {
        const response = await fetch(endpoint, {method: 'POST'});
        const data = await response.json();
        isLocked = data.locked;
        updateButton();
        updateStatus(data);
      } catch (err) {
        console.error('Error:', err);
      }
    }
    
    function updateButton() {
      const btn = document.getElementById('lock-btn');
      if (isLocked) {
        btn.textContent = 'UNLOCK (Click on Person)';
        btn.classList.add('locked');
      } else {
        btn.textContent = 'LOCK (Click on Person)';
        btn.classList.remove('locked');
      }
    }
    
    function updateStatus(data) {
      const status = document.getElementById('status');
      if (data.locked) {
        status.textContent = ' Tracking locked | Missed frames: ' + data.missed_frames;
      } else if (data.is_lost) {
        status.textContent = ' Person LOST — waiting...';
      } else {
        status.textContent = ' Ready to lock onto a person';
      }
    }
  </script>
</head>
<body>
  <h2>Autonomous Wagon — Live Feed & Control</h2>
  <div class="controls">
    <button id="lock-btn" class="lock-btn" onclick="toggleLock()">LOCK (Click on Person)</button>
  </div>
  <div class="status" id="status"> Ready to lock onto a person</div>
  <img src="/video">
</body>
</html>
"""


@flask_app.route("/")
def index():
    return render_template_string(_INDEX)


@flask_app.route("/lock", methods=["POST"])
def lock_person():
    """Called when user clicks LOCK button. Expects the best detection from this frame."""
    # The actual locking happens in the stream when _lock_pending is True
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

    camera, model, label_map = build_pipeline()

    start    = time.monotonic()
    nn_count = 0
    
    # On first lock, save the target person
    _lock_pending = False

    try:
        for frame, detections in frame_generator(camera, model):
            nn_count += 1

            # Vision — draw blue boxes on all detected persons
            person_count = draw_person_detections(frame, detections, label_map)

            # ── Tracker: update with this frame's detections ────────────────
            # This scores each detection against our saved person (if locked)
            target = _tracker.update(detections, frame)
            
            # If not locked yet, optionally auto-lock to largest (simple fallback)
            if not _tracker.locked and detections and not _lock_pending:
                # Find largest person as fallback when not tracking
                best_box = None
                best_area = 0
                for det in detections:
                    label = label_map.get(det.label, str(det.label))
                    if label == "person":
                        x1, y1, x2, y2 = (int(det.xmin * frame.shape[1]),
                                         int(det.ymin * frame.shape[0]),
                                         int(det.xmax * frame.shape[1]),
                                         int(det.ymax * frame.shape[0]))
                        area = (x2 - x1) * (y2 - y1)
                        if area > best_area:
                            best_area = area
                            best_box = (x1, y1, x2, y2, det.confidence)
                
                # Auto-lock to largest person as fallback
                if best_box:
                    _tracker.lock(best_box, frame)
                    target = best_box

            # Calculate area of current target (for follow logic)
            area = 0
            if target is not None:
                x1, y1, x2, y2, conf = target
                area = (x2 - x1) * (y2 - y1)

            # ── Navigation: compute steering and command ────────────────────
            if _tracker.is_lost:
                # Person lost — wagon should stop
                cmd, steer, frame_center = "STOP", 0.0, frame.shape[1] // 2
            else:
                cmd, steer, frame_center = compute_follow_cmd(frame, target, area)

            # State machine — transition to new state
            state = sm.update(cmd)

            # Control — send speeds to motors (only if LOCKED)
            # Unlock disables motor control for safety
            if _tracker.locked:
                brain.execute(state, steer)
                serial.send(cmd, steer)
            else:
                # Not tracking — disable motors
                brain.execute(WagonState.STOP, 0.0)
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
            
            draw_hud(frame, cmd, steer, person_count, nn_fps, target, frame_center)
            
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
        camera.release()


def create_app():
    """Initialise hardware then return the Flask app."""
    motor_pwm.init()
    serial.init()
    return flask_app


if __name__ == "__main__":
    app = create_app()
    app.run(host=FLASK_HOST, port=FLASK_PORT, threaded=True)