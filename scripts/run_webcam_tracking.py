"""
run_webcam_tracking.py
----------------------
Run YOLOv8n on your webcam with single-person lock-on tracking.
Uses Kalman prediction + 3-way scoring (position, color, size).

Press 'l' to lock onto the largest person, 'u' to unlock, 'q' to quit.

Requires: `ultralytics`, `opencv-python`, `numpy` (see requirements.txt)
"""

import sys
import time
import cv2
import numpy as np

try:
    from ultralytics import YOLO
except Exception:
    print("ultralytics not installed. Install with: pip install ultralytics")
    sys.exit(1)

from app.vision.tracking import PersonTracker

# DetectionResult class for compatibility
class DetectionResult:
    def __init__(self, xmin, ymin, xmax, ymax, confidence):
        self.xmin = xmin
        self.ymin = ymin
        self.xmax = xmax
        self.ymax = ymax
        self.confidence = confidence
        self.label = 0  # person class


def boxes_from_ultralytics(results, frame):
    """Convert Ultralytics results to DetectionResult list (normalized coords)."""
    detections = []
    if results is None:
        return detections
    
    h, w = frame.shape[:2]
    for box in results.boxes:
        cls_id = int(box.cls[0])
        label = results.names[cls_id]
        if label != "person":
            continue
        
        # Get normalized coordinates
        x1, y1, x2, y2 = box.xyxy[0]
        xmin = float(x1) / w
        ymin = float(y1) / h
        xmax = float(x2) / w
        ymax = float(y2) / h
        conf = float(box.conf[0])
        
        det = DetectionResult(xmin, ymin, xmax, ymax, conf)
        detections.append(det)
    
    return detections


def main(source=0):
    model = YOLO("yolov8n.pt")
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print("Cannot open webcam")
        return

    tracker = PersonTracker()
    nn_count = 0
    start = time.time()

    print("Controls:")
    print("  'l'     — LOCK onto the largest person")
    print("  'u'     — UNLOCK and reset")
    print("  'q'     — QUIT")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Run YOLOv8 inference
            res = model(frame, verbose=False)[0]
            detections = boxes_from_ultralytics(res, frame)

            # Update tracker with detections and frame
            target = tracker.update(detections, frame)

            # Compute area for follow logic (if target available)
            area = 0
            if target is not None:
                x1, y1, x2, y2, conf = target
                area = max(0, x2 - x1) * max(0, y2 - y1)

            # Draw all detected persons (blue boxes)
            for det in detections:
                x1 = int(det.xmin * frame.shape[1])
                y1 = int(det.ymin * frame.shape[0])
                x2 = int(det.xmax * frame.shape[1])
                y2 = int(det.ymax * frame.shape[0])
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)

            # Draw tracker status
            if tracker.locked:
                status = f"[LOCKED] missed={tracker.missed_frames}"
                status_color = (0, 255, 0)  # green
            elif tracker.is_lost:
                status = "[LOST] person disappeared"
                status_color = (0, 0, 255)  # red
            else:
                status = "[IDLE] press 'l' to lock"
                status_color = (255, 255, 0)  # yellow

            cv2.putText(frame, status, (8, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)

            # Draw predicted position (blue circle)
            if tracker.predicted_x is not None:
                cv2.circle(frame, (int(tracker.predicted_x), int(tracker.predicted_y)),
                          8, (255, 0, 0), 2)

            # Draw locked target (green box)
            if target is not None:
                x1, y1, x2, y2, conf = target
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)),
                             (0, 255, 0), 3)

            # Compute FPS
            nn_count += 1
            nn_fps = nn_count / max(1e-6, time.time() - start)

            # Draw info text
            info = f"FPS: {nn_fps:.1f}  Area: {area:.0f}"
            cv2.putText(frame, info, (8, frame.shape[0] - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            cv2.imshow("Webcam Tracking (Kalman + Scoring)", frame)

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
                        area_det = (x2 - x1) * (y2 - y1)
                        if area_det > best_area:
                            best_area = area_det
                            best_box = (x1, y1, x2, y2, det.confidence)
                    if best_box:
                        tracker.lock(best_box, frame)
                        print("✓ Locked onto person")
            elif key == ord('u'):
                tracker.unlock()
                print("✓ Unlocked")

    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    src = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    main(src)
