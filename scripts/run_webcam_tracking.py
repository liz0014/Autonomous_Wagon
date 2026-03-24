"""
run_webcam_tracking.py
----------------------
Run YOLOv8n on your webcam and feed detections into the PersonTracker.
Prints per-frame tracking info and computed navigation values (cmd, steer,
speed_factor). Press 'q' to quit.

Requires: `ultralytics`, `opencv-python`, `numpy` (see requirements.txt)
"""

import sys
import time
import os
import cv2
import numpy as np

# Ensure project root is on sys.path so imports like `from app...` work
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

try:
    from ultralytics import YOLO
except Exception:
    print("ultralytics not installed. Install with: pip install ultralytics")
    sys.exit(1)

from app.vision.tracking import PersonTracker
from app.navigation.person_detection_logic import get_all_persons
from app.navigation.follow_logic import compute_follow_cmd


# ── Orange hi-vis HSV range (tune for your lighting) ─────────────────────────
ORANGE_HSV_LOWER = np.array([5, 160, 160])
ORANGE_HSV_UPPER = np.array([25, 255, 255])
ORANGE_MIN_RATIO = 0.08   # at least 8 % of the bbox must be orange


def boxes_from_ultralytics(results, frame):
    """Return (x1,y1,x2,y2,conf) only for persons wearing orange hi-vis."""
    out = []
    if results is None:
        return out
    for box in results.boxes:
        cls_id = int(box.cls[0])
        label = results.names[cls_id]
        if label != "person":
            continue
        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
        conf = float(box.conf[0])

        # HSV orange check on the crop
        crop = frame[max(0, y1):y2, max(0, x1):x2]
        if crop.size == 0:
            continue
        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, ORANGE_HSV_LOWER, ORANGE_HSV_UPPER)
        orange_ratio = mask.sum() / 255 / mask.size
        if orange_ratio >= ORANGE_MIN_RATIO:
            out.append((x1, y1, x2, y2, conf))
    return out


def main(source=0):
    model = YOLO("yolov8n.pt")
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print("Cannot open webcam")
        return

    tracker = PersonTracker()
    nn_count = 0
    start = time.time()

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            res = model(frame, verbose=False)[0]
            dets = boxes_from_ultralytics(res, frame)

            # Convert to same format as tracker expects (x1,y1,x2,y2,conf)
            active = tracker.update(dets)
            target = tracker.get_best_target(active)

            if target is not None:
                _tid, x1, y1, x2, y2, conf = target
                area = max(0, x2 - x1) * max(0, y2 - y1)
                ttuple = (x1, y1, x2, y2, conf)
            else:
                area = 0
                ttuple = None

            cmd, steer, speed_factor, frame_center = compute_follow_cmd(frame, ttuple, area)

            nn_count += 1
            nn_fps = nn_count / max(1e-6, time.time() - start)

            # Draw detections and tracks
            for tid, x1, y1, x2, y2, conf in active:
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 0), 2)
                cx = int((x1 + x2) / 2)
                cy = int(y1) - 8
                cv2.putText(frame, f"ID:{tid}", (cx - 20, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)

            if ttuple is not None:
                x1, y1, x2, y2, conf = ttuple
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 3)

            cv2.putText(frame, f"CMD:{cmd} STEER:{steer:+.2f} SPD:{speed_factor:.0%} FPS:{nn_fps:.1f}",
                        (8, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)

            cv2.imshow("Webcam Tracking", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    src = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    main(src)
