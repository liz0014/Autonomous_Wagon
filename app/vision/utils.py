import numpy as np
import cv2

def frame_norm(frame, bbox):
    """bbox is (xmin, ymin, xmax, ymax) in 0..1 range; returns pixel coords."""
    norm_vals = np.full(len(bbox), frame.shape[0], dtype=np.float32)
    norm_vals[::2] = frame.shape[1]
    return (np.clip(np.array(bbox, dtype=np.float32), 0, 1) * norm_vals).astype(int)

def draw_person_detections(frame, detections, label_map):
    """Draw all person boxes. Returns person_count."""
    person_count = 0
    for det in detections:
        label = label_map[det.label] if det.label < len(label_map) else str(det.label)
        if label != "person":
            continue

        person_count += 1
        x1, y1, x2, y2 = frame_norm(frame, (det.xmin, det.ymin, det.xmax, det.ymax)).tolist()

        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
        conf = int(det.confidence * 100)
        cv2.putText(frame, f"person {conf}%", (x1 + 6, y1 + 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2
        cv2.circle(frame, (cx, cy), 4, (255, 255, 255), -1)

    return person_count