import time
import cv2
import depthai as dai
import numpy as np
from flask import Flask, Response

app = Flask(__name__)

def frame_norm(frame, bbox):
    # bbox is in 0..1 range -> convert to pixel coords
    norm_vals = np.full(len(bbox), frame.shape[0])
    norm_vals[::2] = frame.shape[1]
    return (np.clip(np.array(bbox), 0, 1) * norm_vals).astype(int)

def target_person(frame, detections, label_map):
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

def draw_person_detections(frame, detections, label_map):
    person_count = 0
    for det in detections:
        label = label_map[det.label] if det.label < len(label_map) else str(det.label)
        if label != "person":
            continue

        person_count += 1
        bbox = frame_norm(frame, (det.xmin, det.ymin, det.xmax, det.ymax))
        x1, y1, x2, y2 = bbox.tolist()

        # Box + text
        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
        conf = int(det.confidence * 100)
        cv2.putText(frame, f"person {conf}%", (x1 + 6, y1 + 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # Center point
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2
        cv2.circle(frame, (cx, cy), 4, (255, 255, 255), -1)

    return person_count

@app.route("/")
def index():
    return "<h3>Person Detection</h3><img src='/video'>"

@app.route("/video")
def video():
    def gen():
        # TUNING KNOBS FOR PI 4 
        STREAM_FPS = 15              # cap streaming fps
        JPEG_QUALITY = 60            # lower = faster, more compression
        frame_period = 1.0 / STREAM_FPS
        last_frame_time = time.monotonic()
       

        # Create pipeline
        with dai.Pipeline() as pipeline:
            camera = pipeline.create(dai.node.Camera).build()

            # Detection network
            det_nn = pipeline.create(dai.node.DetectionNetwork).build(
                camera,
                dai.NNModelDescription("yolov6-nano")
            )
            label_map = det_nn.getClasses()

            # Queues
            q_rgb = det_nn.passthrough.createOutputQueue()
            q_det = det_nn.out.createOutputQueue()

            # IMPORTANT: prevent backlog + blocking
            q_rgb.setMaxSize(1)
            q_rgb.setBlocking(False)
            q_det.setMaxSize(1)
            q_det.setBlocking(False)

            pipeline.start()

            start = time.monotonic()
            nn_counter = 0
            detections = []

            while pipeline.isRunning():
                # Cap streaming FPS (reduce CPU load)
                now = time.monotonic()
                dt = now - last_frame_time
                if dt < frame_period:
                    time.sleep(frame_period - dt)
                last_frame_time = time.monotonic()

                # Get latest RGB (block a little if needed)
                in_rgb = q_rgb.tryGet()
                if in_rgb is None:
                    # if no frame available yet, skip this iteration
                    continue

                frame = in_rgb.getCvFrame()

                # Get detections WITHOUT blocking
                in_det = q_det.tryGet()
                if in_det is not None:
                    detections = in_det.detections
                    nn_counter += 1

                # Draw detections
                person_count = draw_person_detections(frame, detections, label_map)

                # Follow logic overlay
                h, w = frame.shape[:2]
                frame_center = w // 2
                cv2.line(frame, (frame_center, 0), (frame_center, h), (255, 255, 255), 1)

                cmd = "SEARCH"
                steer = 0.0

                target, area = target_person(frame, detections, label_map)

                if target is not None:
                    x1, y1, x2, y2, conf = target
                    cx = (x1 + x2) // 2
                    error = cx - frame_center

                    steer = float(error) / float(frame_center)
                    steer = max(-1.0, min(1.0, steer))

                    # TEMP distance proxy
                    cmd = "STOP" if area > 90000 else "FOLLOW"

                    # Target highlight
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
                    cv2.circle(frame, (cx, (y1 + y2) // 2), 6, (0, 255, 0), -1)

                    cv2.putText(frame, f"Target cx={cx} err={error} steer={steer:+.2f} area={area}",
                                (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

                cv2.putText(frame, f"CMD: {cmd}  STEER: {steer:+.2f}",
                            (8, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

                # FPS overlay ALWAYS (not only when target exists)
                nn_fps = nn_counter / max(1e-6, (time.monotonic() - start))
                cv2.putText(frame, f"NN FPS: {nn_fps:.1f}  Persons: {person_count}",
                            (8, frame.shape[0] - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

                # ALWAYS encode + yield (prevents browser freeze)
                ok, jpg = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
                if not ok:
                    continue

                yield (b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n\r\n" + jpg.tobytes() + b"\r\n")

    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")

if __name__ == "__main__":
    # For Pi 4 demo stability, avoid extra threads spawning extra work
    app.run(host="0.0.0.0", port=5000, threaded=False)