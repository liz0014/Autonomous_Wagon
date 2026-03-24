"""
run_vision.py
-------------
Vision-only test: camera → detect → track (with Kalman + scoring) → display.
No motors, no Flask — just a local preview for tuning detection and tracking.

Press 'l' to lock onto a person, 'u' to unlock.
Press 'q' to quit.
"""

import cv2

from app.vision.oakd_camera import build_pipeline, frame_generator
from app.vision.utils import draw_person_detections
from app.vision.tracking import PersonTracker


def main():
    tracker = PersonTracker()

    camera, model, label_map = build_pipeline()

    print("Controls:")
    print("  'l'     — LOCK onto the largest person")
    print("  'u'     — UNLOCK and reset")
    print("  'q'     — QUIT")

    try:
        for frame, detections in frame_generator(camera, model):
            # Draw all detections
            draw_person_detections(frame, detections, label_map)

            # Update tracker with detections
            target = tracker.update(detections, frame)

            # Draw tracker status
            if tracker.locked:
                status = f"[LOCKED] missed={tracker.missed_frames}"
                color = (0, 255, 0)  # green
            elif tracker.is_lost:
                status = "[LOST] person disappeared"
                color = (0, 0, 255)  # red
            else:
                status = "[IDLE] press 'l' to lock"
                color = (255, 255, 0)  # yellow

            cv2.putText(frame, status, (8, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

            # Draw predicted position (blue circle) and actual target (green box)
            if tracker.predicted_x is not None:
                cv2.circle(frame, (int(tracker.predicted_x), int(tracker.predicted_y)),
                          8, (255, 0, 0), 2)

            if target is not None:
                x1, y1, x2, y2, conf = target
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)),
                             (0, 255, 0), 3)
                cx = int((x1 + x2) / 2)
                cy = int(y1) - 10
                cv2.putText(frame, f"{conf:.0%}", (cx - 20, cy),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            cv2.imshow("Autonomous Wagon — Vision + Tracking", frame)

            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('l'):
                # Auto-lock to largest person
                if detections:
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
                        print("✓ Locked onto person")
            elif key == ord('u'):
                tracker.unlock()
                print("✓ Unlocked")

    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()