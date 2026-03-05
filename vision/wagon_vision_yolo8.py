"""
Autonomous Wagon — DepthAI v3 + Flask browser stream
OAK-D Lite: SpatialDetectionNetwork (replaces YoloSpatialDetectionNetwork)
"""

import cv2
import depthai as dai
import threading
import time
from flask import Flask, Response

# ---- CONFIG ----
# v3 uses NNModelDescription with a model name (downloads from Luxonis zoo)
# OR use a local .blob path — see note below
MODEL_NAME   = "yolov6-nano"   # pulled from Luxonis model zoo automatically
CONF_THRESHOLD = 0.5
FPS = 20

app = Flask(__name__)
latest_frame = None
frame_lock   = threading.Lock()


# ---- Flask Routes ----
def generate_frames():
    while True:
        with frame_lock:
            if latest_frame is None:
                time.sleep(0.01)
                continue
            _, jpeg = cv2.imencode('.jpg', latest_frame,
                                   [cv2.IMWRITE_JPEG_QUALITY, 80])
            frame_bytes = jpeg.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(1 / FPS)


@app.route('/')
def index():
    return '''
    <html><head>
        <title>Autonomous Wagon</title>
        <style>
            body  { background:#0d0d0d; color:#00ff88; font-family:monospace;
                    display:flex; flex-direction:column; align-items:center; margin:0; padding:20px; }
            h2    { letter-spacing:3px; margin-bottom:16px; }
            img   { max-width:100%; border:2px solid #00ff88; border-radius:4px; }
            small { color:#555; margin-top:8px; }
        </style>
    </head><body>
        <h2> AUTONOMOUS WAGON — LIVE</h2>
        <img src="/video_feed">
        <small>YOLO on OAK-D Lite · DepthAI v3</small>
    </body></html>
    '''


@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


# ---- DepthAI v3 Pipeline ----
def run_pipeline():
    global latest_frame

    # v3: NNModelDescription — downloads model from Luxonis zoo if not cached
    modelDescription = dai.NNModelDescription(MODEL_NAME)

    with dai.Pipeline() as pipeline:

        # --- Cameras (v3 syntax: .build(socket)) ---
        cam_rgb    = pipeline.create(dai.node.Camera).build(dai.CameraBoardSocket.CAM_A)
        mono_left  = pipeline.create(dai.node.Camera).build(dai.CameraBoardSocket.CAM_B)
        mono_right = pipeline.create(dai.node.Camera).build(dai.CameraBoardSocket.CAM_C)

        # --- Stereo Depth ---
        stereo = pipeline.create(dai.node.StereoDepth)
        stereo.setDefaultProfilePreset(dai.node.StereoDepth.PresetMode.FAST_DENSITY)
        stereo.setDepthAlign(dai.CameraBoardSocket.CAM_A)

        # Link mono cameras to stereo (v3: requestOutput returns a linkable output)
        mono_left.requestOutput(
            (640, 400), type=dai.ImgFrame.Type.GRAY8
        ).link(stereo.left)
        mono_right.requestOutput(
            (640, 400), type=dai.ImgFrame.Type.GRAY8
        ).link(stereo.right)

        # --- SpatialDetectionNetwork (v3 replacement for YoloSpatialDetectionNetwork) ---
        # .build() handles all the camera→nn and stereo→nn linking automatically
        spatial_nn = pipeline.create(dai.node.SpatialDetectionNetwork).build(
            cam_rgb, stereo, modelDescription, fps=FPS
        )
        spatial_nn.setConfidenceThreshold(CONF_THRESHOLD)
        spatial_nn.setBoundingBoxScaleFactor(0.5)
        spatial_nn.setDepthLowerThreshold(100)
        spatial_nn.setDepthUpperThreshold(5000)

        # Get class labels from the model itself (no manual list needed!)
        label_map = spatial_nn.getClasses()

        # --- Output queues ---
        # passthrough = the RGB frame that was used for inference
        rgb_queue = spatial_nn.passthrough.createOutputQueue(maxSize=4, blocking=False)
        det_queue = spatial_nn.out.createOutputQueue(maxSize=4, blocking=False)

        pipeline.start()
        print(f" Pipeline running — open http://<your-pi-ip>:5000")
        print(f"   Labels loaded: {label_map[:5]}...")

        while pipeline.isRunning():
            frame_msg = rgb_queue.tryGet()
            det_msg   = det_queue.tryGet()

            if frame_msg is None:
                time.sleep(0.005)
                continue

            frame = frame_msg.getCvFrame()

            if det_msg is not None:
                for det in det_msg.detections:
                    h, w = frame.shape[:2]
                    x1 = int(det.xmin * w)
                    y1 = int(det.ymin * h)
                    x2 = int(det.xmax * w)
                    y2 = int(det.ymax * h)

                    label   = label_map[det.label] if det.label < len(label_map) else str(det.label)
                    depth_m = det.spatialCoordinates.z / 1000.0
                    conf    = int(det.confidence * 100)

                    # Red if close, yellow if medium, green if far
                    if depth_m < 0.8:
                        color = (0, 0, 255)
                    elif depth_m < 1.5:
                        color = (0, 165, 255)
                    else:
                        color = (0, 255, 0)

                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(frame, f"{label} {depth_m:.1f}m ({conf}%)",
                                (x1, max(y1 - 8, 12)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

                    navigate(label, depth_m)

            with frame_lock:
                latest_frame = frame.copy()


def navigate(label, depth_m):
    """Hook your motor controller here."""
    if label in ("stop sign",) and depth_m < 1.5:
        print(f"[STOP] {label} at {depth_m:.2f}m")
        # stop_motors()
    elif label == "person" and depth_m < 1.0:
        print(f"[STOP] {label} at {depth_m:.2f}m")
        # stop_motors()
    # else:
    #     drive_forward()


if __name__ == "__main__":
    pipeline_thread = threading.Thread(target=run_pipeline, daemon=True)
    pipeline_thread.start()

    # Give pipeline a moment to init before Flask starts serving
    time.sleep(2)

    print(" Flask starting on http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, threaded=True)