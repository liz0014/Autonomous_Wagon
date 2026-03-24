"""
run_wagon.py
------------
Headless full-robot loop (no Flask, no video stream).
Camera → detect → track → navigate → drive motors.
"""

import time
import logging

from app.vision.oakd_camera import build_pipeline, frame_generator
from app.vision.tracking import PersonTracker
from app.navigation.person_detection_logic import get_all_persons
from app.navigation.follow_logic import compute_follow_cmd
from app.navigation.state_machine import StateMachine
from app.control import brain, motor_pwm, serial

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)


def main():
    motor_pwm.init()
    serial.init()

    sm = StateMachine()
    tracker = PersonTracker()

    pipeline, q_rgb, q_det, label_map = build_pipeline()
    pipeline.start()

    try:
        for frame, detections in frame_generator(q_rgb, q_det):
            person_dets = get_all_persons(frame, detections, label_map)
            active_tracks = tracker.update(person_dets)
            target_track = tracker.get_best_target(active_tracks)

            if target_track is not None:
                _tid, x1, y1, x2, y2, conf = target_track
                target = (x1, y1, x2, y2, conf)
                area = max(0, x2 - x1) * max(0, y2 - y1)
            else:
                target, area = None, 0

            cmd, steer, speed_factor, _ = compute_follow_cmd(frame, target, area)
            state = sm.update(cmd)
            brain.execute(state, steer, speed_factor)
            serial.send(cmd, steer)

            print(f"CMD={cmd}  STEER={steer:+.2f}  SPD={speed_factor:.0%}")
            time.sleep(0.01)
    except KeyboardInterrupt:
        pass
    finally:
        motor_pwm.cleanup()
        serial.close()
        pipeline.stop()


if __name__ == "__main__":
    main()