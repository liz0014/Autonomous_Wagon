import time
import cv2
import depthai as dai
from flask import Flask, Response

app = Flask(__name__)

# --- DepthAI v3 pipeline setup (NO XLink nodes) ---
pipeline = dai.Pipeline()

cam = pipeline.create(dai.node.Camera).build()

# Request an output stream directly from the camera node
# BGR888p works nicely with OpenCV
out = cam.requestOutput(
    size=(640, 480),
    type=dai.ImgFrame.Type.BGR888p,
    fps=15,
)

q = out.createOutputQueue()  # v3 way (replaces device.getOutputQueue)
pipeline.start()

def gen_frames():
    while pipeline.isRunning():
        frame_msg = q.get()           # blocking get
        frame = frame_msg.getCvFrame()

        ok, jpg = cv2.imencode(".jpg", frame)
        if not ok:
            continue

        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" + jpg.tobytes() + b"\r\n")
        time.sleep(0.001)

@app.route("/")
def index():
    return "<h3>LIVE!</h3><img src='/video'>"

@app.route("/video")
def video():
    return Response(gen_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")

if __name__ == "__main__":
    # Listen on all interfaces so your laptop can connect
    app.run(host="0.0.0.0", port=5000, threaded=True)
