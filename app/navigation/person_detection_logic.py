from app.vision.utils import frame_norm


def get_best_person(frame, detections, label_map):
    best = None
    best_area = 0

    for det in detections:
        label = label_map[det.label] if det.label < len(label_map) else str(det.label)
        if label != "person":
            continue

        bbox = frame_norm(frame, (det.xmin, det.ymin, det.xmax, det.ymax))
        x1, y1, x2, y2 = bbox.tolist()
        area = max(0, x2 - x1) * max(0, y2 - y1)

        if area > best_area:
            best_area = area
            best = (x1, y1, x2, y2, det.confidence)

    return best, best_area