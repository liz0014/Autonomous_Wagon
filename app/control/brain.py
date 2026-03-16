import time
import cv2

from app.navigation.person_detection_logic import target_person
from app.navigation.follow_logic import compute_follow_command
from app.vision.utils import frame_norm


def draw_person_detections(frame, detections, label_map):
    person_count = 0

    for det in detections:
        label = label_map[det.label] if det.label < len(label_map) else str(det.label)
        if label != "person":
            continue

        person_count += 1
        bbox = frame_norm(frame, (det.xmin, det.ymin, det.xmax, det.ymax))
        x1, y1, x2, y2 = bbox.tolist()

        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
        conf = int(det.confidence * 100)
        cv2.putText(
            frame,
            f"person {conf}%",
            (x1 + 6, y1 + 18),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
        )

        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2
        cv2.circle(frame, (cx, cy), 4, (255, 255, 255), -1)

    return person_count


class Brain:
    def __init__(self):
        self.start_time = time.monotonic()
        self.nn_counter = 0

    def process(self, frame, detections, label_map):
        self.nn_counter += 1

        person_count = draw_person_detections(frame, detections, label_map)

        h, w = frame.shape[:2]
        frame_center = w // 2

        target = target_person(frame, detections, label_map)
        result = compute_follow_command(w, target)

        if target is not None:
            x1 = target["x1"]
            y1 = target["y1"]
            x2 = target["x2"]
            y2 = target["y2"]
            cx = result["cx"]

            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
            cv2.line(frame, (frame_center, 0), (frame_center, h), (255, 255, 255), 1)
            cv2.circle(frame, (cx, (y1 + y2) // 2), 6, (0, 255, 0), -1)

            cv2.putText(
                frame,
                f"Target cx={cx} err={result['error']} steer={result['steer']:+.2f} area={result['area']}",
                (8, 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1,
            )

        cv2.putText(
            frame,
            f"CMD: {result['cmd']}  STEER: {result['steer']:+.2f}",
            (8, 45),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
        )

        nn_fps = self.nn_counter / max(1e-6, (time.monotonic() - self.start_time))
        cv2.putText(
            frame,
            f"NN FPS: {nn_fps:.1f}  Persons: {person_count}",
            (8, frame.shape[0] - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
        )

        return frame, result