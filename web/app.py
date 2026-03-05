import time
import cv2
from flask import Flask, Response

from vision.oak_yolo import start_yolo_pipeline
from vision.utils import draw_person_detections
from vision.tracking import target_person
from control.brain import decide_command
from control.motor_pwm import MotorPWM

app = Flask(__name__)

motor = MotorPWM(pwm_pin=18, duty_stop=7.5, duty_forward=8.2)

@app.route("/")
def index():
    return "<h3>Person Detection</h3><img src='/video'>"

@app.route("/video")
def video():
    def gen():
        # Start motor + pipeline once per stream
        motor.start()
        motor.stop()

        pipeline, q_rgb, q_det, label_map = start_yolo_pipeline("yolov6-nano")

        start = time.monotonic()
        nn_counter = 0
        detections = []

        try:
            while pipeline.isRunning():
                in_rgb = q_rgb.get()
                in_det = q_det.get()

                frame = in_rgb.getCvFrame()

                if in_det is not None:
                    detections = in_det.detections
                    nn_counter += 1

                # Draw all persons (blue boxes)
                person_count = draw_person_detections(frame, detections, label_map)

                # Target selection
                h, w = frame.shape[:2]
                frame_center = w // 2

                target, area = target_person(frame, detections, label_map)
                has_target = (target is not None)

                # Decide command (SEARCH / FOLLOW / STOP)
                cmd = decide_command(area, has_target, stop_area_threshold=90000)

                # Motor action
                if cmd == "FOLLOW":
                    motor.forward()
                else:
                    motor.stop()

                # Overlay target + aiming info (green box)
                steer = 0.0
                if has_target:
                    x1, y1, x2, y2, conf = target
                    cx = (x1 + x2) // 2
                    error = cx - frame_center

                    steer = float(error) / float(frame_center)
                    steer = max(-1.0, min(1.0, steer))

                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
                    cv2.line(frame, (frame_center, 0), (frame_center, h), (255, 255, 255), 1)
                    cv2.circle(frame, (cx, (y1 + y2) // 2), 6, (0, 255, 0), -1)
                    cv2.putText(frame, f"Target cx={cx} err={error} steer={steer:+.2f} area={area}",
                                (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                else:
                    cv2.putText(frame, "No target",
                                (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

                # Overlay command + fps (ALWAYS shown)
                nn_fps = nn_counter / max(1e-6, (time.monotonic() - start))
                cv2.putText(frame, f"CMD: {cmd}  STEER: {steer:+.2f}",
                            (8, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

                cv2.putText(frame, f"NN FPS: {nn_fps:.1f}  Persons: {person_count}",
                            (8, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

                ok, jpg = cv2.imencode(".jpg", frame)
                if not ok:
                    continue

                yield (b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n\r\n" + jpg.tobytes() + b"\r\n")

        finally:
            motor.stop()
            motor.cleanup()

    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")