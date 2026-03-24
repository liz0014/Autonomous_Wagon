from app.vision.utils import frame_norm
from app.config.settings import DETECTION_LABEL


def get_all_persons(frame, detections, label_map):
    """
    Return a list of (x1, y1, x2, y2, confidence) for every detection
    matching DETECTION_LABEL.  Fed directly into PersonTracker.update().
    """
    persons = []
    for det in detections:
        label = label_map[det.label] if det.label < len(label_map) else str(label_map)
        if label != DETECTION_LABEL:
            continue
        bbox = frame_norm(frame, (det.xmin, det.ymin, det.xmax, det.ymax))
        x1, y1, x2, y2 = bbox.tolist()
        persons.append((x1, y1, x2, y2, det.confidence))
    return persons


def get_best_person(frame, detections, label_map):
    """Pick the largest person by bounding box area (legacy convenience)."""
    persons = get_all_persons(frame, detections, label_map)
    best = None
    best_area = 0

    for p in persons:
        x1, y1, x2, y2, conf = p
        area = max(0, x2 - x1) * max(0, y2 - y1)
        if area > best_area:
            best_area = area
            best = p

    return best, best_area