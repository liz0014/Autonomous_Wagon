<<<<<<< HEAD
=======
"""
wagon_vision_yolo8.py
---------------------
Standalone YOLOv8n detector using Ultralytics — for testing on a regular
webcam or video file when OAK-D hardware is not available.

Usage:
    pip install ultralytics
    python -m app.vision.wagon_vision_yolo8          # webcam
    python -m app.vision.wagon_vision_yolo8 video.mp4 # file
"""

import sys
import cv2


def run(source=0):
    from ultralytics import YOLO

    model = YOLO("yolov8n.pt")

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"Cannot open source: {source}")
        return

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            results = model(frame, verbose=False)[0]

            for box in results.boxes:
                cls_id = int(box.cls[0])
                label = results.names[cls_id]
                if label != "person":
                    continue
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, f"{label} {conf:.0%}", (x1, y1 - 6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

            cv2.imshow("YOLOv8n Webcam", frame)
            if cv2.waitKey(1) == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else 0
    run(src)
>>>>>>> 404f2e000986a15dc4759eb136cb94cd9a5514a4
