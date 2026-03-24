"""
run_vision.py
-------------
Vision-only test: camera → detect → display with OpenCV window.
No motors, no Flask — just a local preview for tuning detection.
"""

import cv2

from app.vision.oakd_camera import build_pipeline, frame_generator
from app.vision.utils import draw_person_detections
from app.navigation.person_detection_logic import get_all_persons
from app.vision.tracking import PersonTracker


def main():
    tracker = PersonTracker()

    pipeline, q_rgb, q_det, label_map = build_pipeline()
    pipeline.start()

    try:
        for frame, detections in frame_generator(q_rgb, q_det):
            draw_person_detections(frame, detections, label_map)

            person_dets = get_all_persons(frame, detections, label_map)
            active_tracks = tracker.update(person_dets)

            # Draw track IDs on frame
            for tid, x1, y1, x2, y2, conf in active_tracks:
                cx = int((x1 + x2) / 2)
                cy = int(y1) - 8
                cv2.putText(frame, f"ID:{tid}", (cx - 20, cy),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            cv2.imshow("Autonomous Wagon — Vision", frame)
            if cv2.waitKey(1) == ord("q"):
                break
    finally:
        pipeline.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()