"""
web/app.py
----------
Flask MJPEG stream — headless-friendly.
Browse to http://<pi-ip>:5000 from any device on the same network.

Per-frame pipeline:
  camera → detections → pick target → compute steer/cmd
  → state machine → motors → HUD overlay → JPEG → browser
"""

import time
import cv2
from flask import Flask, Response, render_template_string

from app.vision.oakd_camera import build_pipeline, frame_generator
from app.vision.utils import draw_person_detections, draw_hud
from app.navigation.person_detection_logic import get_best_person
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
    """Core generator: camera → detection → navigation → motor → JPEG."""
    sm = StateMachine()

    pipeline, q_rgb, q_det, label_map = build_pipeline()
    pipeline.start()

    start    = time.monotonic()
    nn_count = 0

    try:
        for frame, detections in frame_generator(q_rgb, q_det):
            nn_count += 1

            # Vision — draw blue boxes on all detected persons
            person_count = draw_person_detections(frame, detections, label_map)

            # Target selection — pick the largest/closest person
            target, area = get_best_person(frame, detections, label_map)

            # Navigation — compute steering and command
            cmd, steer, frame_center = compute_follow_cmd(frame, target, area)

            # State machine — transition to new state
            state = sm.update(cmd)

            # Control — send speeds to motors
            brain.execute(state, steer)
            serial.send(cmd, steer)

            # HUD — paint telemetry onto the frame
            nn_fps = nn_count / max(1e-6, time.monotonic() - start)
            draw_hud(frame, cmd, steer, person_count, nn_fps, target, frame_center)

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
    """Initialise hardware then return the Flask app."""
    motor_pwm.init()
    serial.init()
    return flask_app


if __name__ == "__main__":
    app = create_app()
    app.run(host=FLASK_HOST, port=FLASK_PORT, threaded=True)