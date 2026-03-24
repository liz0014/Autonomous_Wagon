"""
web/app.py
----------
Flask MJPEG stream — headless-friendly.
Browse to http://<pi-ip>:5000 from any device on the same network.

Per-frame pipeline:
  camera → detections → tracker → pick target → compute steer/cmd/speed
  → state machine → motors (with ramp) → HUD overlay → JPEG → browser
"""

import time
import cv2
from flask import Flask, Response, render_template_string

from app.vision.oakd_camera import build_pipeline, frame_generator
from app.vision.utils import draw_person_detections, draw_hud
from app.vision.tracking import PersonTracker
from app.navigation.person_detection_logic import get_all_persons
from app.navigation.follow_logic import compute_follow_cmd
from app.navigation.state_machine import StateMachine
from app.control import brain, motor_pwm, serial
from app.config.settings import FLASK_HOST, FLASK_PORT, JPEG_QUALITY

flask_app = Flask(__name__)

_INDEX = """
<!doctype html>
<html>
<head>
  <title>Autonomous Wagon</title>
  <style>
    body { background:#111; color:#eee; font-family:monospace; text-align:center; }
    img  { max-width:100%; border:2px solid #0f0; margin-top:12px; }
  </style>
</head>
<body>
  <h2>Autonomous Wagon — Live Feed</h2>
  <img src="/video">
</body>
</html>
"""


@flask_app.route("/")
def index():
    return render_template_string(_INDEX)


@flask_app.route("/video")
def video():
    return Response(_stream(), mimetype="multipart/x-mixed-replace; boundary=frame")


def _stream():
    """Core generator: camera → detection → tracker → navigation → motor → JPEG."""
    sm = StateMachine()
    tracker = PersonTracker()

    pipeline, q_rgb, q_det, label_map = build_pipeline()
    pipeline.start()

    start    = time.monotonic()
    nn_count = 0

    try:
        for frame, detections in frame_generator(q_rgb, q_det):
            nn_count += 1

            # Vision — draw blue boxes on all detected persons
            person_count = draw_person_detections(frame, detections, label_map)

            # Tracker — get persistent IDs for all person detections
            person_dets = get_all_persons(frame, detections, label_map)
            active_tracks = tracker.update(person_dets)
            target_track = tracker.get_best_target(active_tracks)

            # Unpack tracker output to (x1,y1,x2,y2,conf) + area
            if target_track is not None:
                _tid, x1, y1, x2, y2, conf = target_track
                target = (x1, y1, x2, y2, conf)
                area = max(0, x2 - x1) * max(0, y2 - y1)
            else:
                target, area = None, 0

            # Navigation — compute steering, speed factor, and command
            cmd, steer, speed_factor, frame_center = compute_follow_cmd(
                frame, target, area
            )

            # State machine — transition to new state
            state = sm.update(cmd)

            # Control — send speeds to motors (with acceleration ramp)
            brain.execute(state, steer, speed_factor)
            serial.send(cmd, steer)

            # HUD — paint telemetry onto the frame
            nn_fps = nn_count / max(1e-6, time.monotonic() - start)
            draw_hud(frame, cmd, steer, person_count, nn_fps,
                     target, frame_center, speed_factor)

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
        pipeline.stop()


def create_app():
    """Factory used by run.py and tests."""
    motor_pwm.init()
    serial.init()
    return flask_app


def create_app():
    """Initialise hardware then return the Flask app."""
    motor_pwm.init()
    serial.init()
    return flask_app


if __name__ == "__main__":
    app = create_app()
    app.run(host=FLASK_HOST, port=FLASK_PORT, threaded=True)