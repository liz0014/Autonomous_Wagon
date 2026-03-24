"""
run_wagon.py
------------
Headless full-robot loop (no Flask, no video stream).
Automatically locks onto the largest detected person and drives toward them.

Camera → detect → track (Kalman+scoring) → navigate → drive motors.
"""

import time
import logging

from app.vision.oakd_camera import build_pipeline, frame_generator
from app.vision.tracking import PersonTracker
from app.navigation.follow_logic import compute_follow_cmd
from app.navigation.state_machine import StateMachine
from app.control import brain, motor_pwm, serial

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)

logger = logging.getLogger(__name__)


def main():
    motor_pwm.init()
    serial.init()

    sm = StateMachine()
    tracker = PersonTracker()

    camera, model, label_map = build_pipeline()

    logger.info("Starting autonomous wagon...")
    logger.info("Will auto-lock onto the first person detected.")

    try:
        for frame, detections in frame_generator(camera, model):
            # Auto-lock to largest person if not already locked
            if not tracker.locked and detections:
                best_box = None
                best_area = 0
                for det in detections:
                    x1 = int(det.xmin * frame.shape[1])
                    y1 = int(det.ymin * frame.shape[0])
                    x2 = int(det.xmax * frame.shape[1])
                    y2 = int(det.ymax * frame.shape[0])
                    area = (x2 - x1) * (y2 - y1)
                    if area > best_area:
                        best_area = area
                        best_box = (x1, y1, x2, y2, det.confidence)
                if best_box:
                    tracker.lock(best_box, frame)
                    logger.info("✓ Locked onto person")

            # Update tracker with current detections
            target = tracker.update(detections, frame)

            # Compute navigation command
            area = 0
            if target is not None:
                x1, y1, x2, y2, conf = target
                area = (x2 - x1) * (y2 - y1)

            cmd, steer, speed_factor, _ = compute_follow_cmd(frame, target, area)
            state = sm.update(cmd)

            # Execute motion (only if locked, for safety)
            if tracker.locked:
                brain.execute(state, steer, speed_factor)
                serial.send(cmd, steer)
            else:
                # Not tracking — disable motors
                brain.execute(state, 0.0, 0.0)
                serial.send("STOP", 0.0)

            logger.info(f"CMD={cmd:<6} STEER={steer:+.2f}  SPD={speed_factor:.0%}  "
                       f"LOCKED={tracker.locked}  LOST={tracker.is_lost}  "
                       f"MISSED={tracker.missed_frames}")
            time.sleep(0.01)

    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
    finally:
        logger.info("Shutting down...")
        brain.execute(state, 0.0, 0.0)
        serial.send("STOP", 0.0)
        motor_pwm.cleanup()
        serial.close()
        camera.release()
        logger.info("Done.")


if __name__ == "__main__":
    main()