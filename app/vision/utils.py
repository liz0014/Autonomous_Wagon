import numpy as np
import cv2

from app.config.settings import DETECTION_LABEL


def draw_person_detections(frame, detections, label_map):
    """
    Draw bounding boxes + confidence for every detection.
    detections are tuples: (x1, y1, x2, y2, conf)
    Returns the count of detections drawn.
    """
    person_count = 0
    for det in detections:
        x1, y1, x2, y2, conf = det

        person_count += 1

        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
        confidence = int(conf * 100)
        cv2.putText(frame, f"{DETECTION_LABEL} {confidence}%", (x1 + 6, y1 + 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2
        cv2.circle(frame, (cx, cy), 4, (255, 255, 255), -1)

    return person_count


def draw_hud(frame, cmd, steer, person_count, nn_fps,
             target=None, frame_center=None, speed_factor=0.0):
    """
    Render HUD overlay: target highlight, center line, telemetry text.
    """
    h, w = frame.shape[:2]

    if target is not None and frame_center is not None:
        x1, y1, x2, y2, conf = target
        cx = (x1 + x2) // 2
        error = cx - frame_center

        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
        cv2.line(frame, (frame_center, 0), (frame_center, h), (255, 255, 255), 1)
        cv2.circle(frame, (cx, (y1 + y2) // 2), 6, (0, 255, 0), -1)

        cv2.putText(frame,
                    f"Target cx={cx} err={error} steer={steer:+.2f}",
                    (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    cv2.putText(frame, f"CMD: {cmd}  STEER: {steer:+.2f}  SPD: {speed_factor:.0%}",
                (8, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

    cv2.putText(frame, f"NN FPS: {nn_fps:.1f}  Persons: {person_count}",
                (8, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
