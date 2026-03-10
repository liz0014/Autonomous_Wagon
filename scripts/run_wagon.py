
"""
full robot:

"""

import time
from app.vision.oak_camera import OakPersonDetector
from app.vision.person_detection import target_person
from app.navigation.follow_logic import decide_follow_command
from app.control.brain import execute_command

def main():
    detector = OakPersonDetector()
    detector.start()

    while detector.is_running():
        frame, detections, label_map = detector.get_frame_and_detections()
        h, w = frame.shape[:2]

        target, area = target_person(frame, detections, label_map)
        result = decide_follow_command(w, target, area)

        print(f"CMD={result['cmd']} STEER={result['steer']:+.2f}")
        execute_command(result["cmd"], result["steer"])

        time.sleep(0.05)

if __name__ == "__main__":
    main()