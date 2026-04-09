"""

--------------
OAK-D pipeline
pipeline for the autonomous wagon.
DepthAI v3 API with YOLOv8n custom blob.

"""
import depthai as dai
import numpy as np
import cv2
import os
import time

BLOB_PATH      = "/home/lpaisano/.cache/blobconverter/yolov8n_openvino_2022.1_6shave.blob"
IMG_W          = 640
IMG_H          = 352
CONF_THRESHOLD = 0.15
IOU_THRESHOLD  = 0.25 #if two boxes overlap by more than 45%, keep only the most confident one and throw the other away.
PERSON_CLASS   = 0
_score_buffer = None
_SMOOTH_ALPHA = 0.15 

def decode_yolov8(output, conf_thresh=CONF_THRESHOLD):
    global _score_buffer 
    #squeeze(0) removes the batch dimension
    pred = output.squeeze(0) # (1, 84, 4620) to (84, 4620)
    pred = pred.T # (84, 4620) to  (4620, 84)
    boxes  = pred[:, :4]   # first 4 values = cx, cy, w, h
    scores = pred[:, 4:]   # remaining 80 values = class scores

    # ── Temporal smoothing ────────────────────────────────────────────
    # Instead of using this frame's scores raw, blend them with the
    # running average. This dampens the flicker caused by frame-to-frame
    # score instability in the 6-shave blob.
    if _score_buffer is None or _score_buffer.shape != scores.shape:
        _score_buffer = scores.copy()
    else:
        _score_buffer = _SMOOTH_ALPHA * scores + (1 - _SMOOTH_ALPHA) * _score_buffer

    scores = _score_buffer
    # ─────────────────────────────────────────────────────────────────


    class_ids = np.argmax(scores, axis=1)
    confs     = scores[np.arange(len(scores)), class_ids]
    mask      = confs >= conf_thresh
    boxes     = boxes[mask]
    confs     = confs[mask]
    class_ids = class_ids[mask]

    if len(boxes) == 0:
        return []
    cx, cy, w, h = boxes[:,0], boxes[:,1], boxes[:,2], boxes[:,3]
    x1 = (cx - w / 2).astype(int)
    y1 = (cy - h / 2).astype(int)
    x2 = (cx + w / 2).astype(int)
    y2 = (cy + h / 2).astype(int)

    results = []
    indices = cv2.dnn.NMSBoxes(
        [[int(x1[i]), int(y1[i]), int(w[i]), int(h[i])] for i in range(len(x1))],
        confs.tolist(), conf_thresh, IOU_THRESHOLD
    )
    for i in indices:
        results.append((int(x1[i]), int(y1[i]), int(x2[i]), int(y2[i]),
                        float(confs[i]), int(class_ids[i])))
    return results

"""
YOLOv8n outputs cx,cy,w,h (center x, center y, width, height) but our tracker expects x1,y1,x2,y2

"""
def build_pipeline():
    device = dai.Device()
    pipeline = dai.Pipeline(device)
    #RGB Camera
    cam_rgb     = pipeline.create(dai.node.Camera).build(dai.CameraBoardSocket.CAM_A)
    display_out = cam_rgb.requestOutput((IMG_W, IMG_H), type=dai.ImgFrame.Type.BGR888p, fps=30)
    nn_input    = cam_rgb.requestOutput((IMG_W, IMG_H), type=dai.ImgFrame.Type.BGR888p, fps=30)

    #Mono Cameras
    mono_left  = pipeline.create(dai.node.Camera).build(dai.CameraBoardSocket.CAM_B)
    mono_right = pipeline.create(dai.node.Camera).build(dai.CameraBoardSocket.CAM_C)
    left_out   = mono_left.requestOutput((640, 400), type=dai.ImgFrame.Type.GRAY8, fps=30)
    right_out  = mono_right.requestOutput((640, 400), type=dai.ImgFrame.Type.GRAY8, fps=30)

    #stereo Depth
    stereo = pipeline.create(dai.node.StereoDepth).build(
        left=left_out,
        right=right_out,
        presetMode=dai.node.StereoDepth.PresetMode.FAST_DENSITY,
    )
    stereo.setLeftRightCheck(True)
    stereo.setSubpixel(False)
    stereo.setDepthAlign(dai.CameraBoardSocket.CAM_A)
    stereo.setOutputSize(640, 400)

    #Yolov8n
    #Loads our custom compiled blob. Links the second camera output to the NN input.
    nn = pipeline.create(dai.node.NeuralNetwork)
    nn.setBlobPath(BLOB_PATH)
    nn.setNumInferenceThreads(2)
    nn.input.setBlocking(False)
    nn.input.setMaxSize(1)
    nn_input.link(nn.input)

    #IMU
    imu = pipeline.create(dai.node.IMU)
    imu.enableIMUSensor([
        dai.IMUSensor.ACCELEROMETER_RAW,
        dai.IMUSensor.GYROSCOPE_RAW,
    ], 100)
    imu.setBatchReportThreshold(1)
    imu.setMaxBatchReports(10)

    #Queues 
    #Opens all data streams. Returns everything frame_generator needs.
    queue_rgb   = display_out.createOutputQueue(maxSize=1, blocking=False)
    queue_nn    = nn.out.createOutputQueue(maxSize=1, blocking=False)
    queue_depth = stereo.depth.createOutputQueue(maxSize=1, blocking=False)
    queue_imu   = imu.out.createOutputQueue(maxSize=4, blocking=False)

    return pipeline, device, queue_rgb, queue_nn, queue_depth, queue_imu
"""
This is the function app.py calls. It starts the device, reads all queues continuously, and yields (frame, detections) forever.
"""
def frame_generator(pipeline, device, queue_rgb, queue_nn, queue_depth, queue_imu, conf_threshold=CONF_THRESHOLD):
    global _score_buffer
    _score_buffer = None        # reset buffer on every pipeline start

    with pipeline:
        pipeline.start()
        time.sleep(1.0)         # let auto-exposure settle

        warmup_frames = 0
        WARMUP_COUNT  = 20      # build buffer for 20 frames before showing boxes

        while pipeline.isRunning():
            rgb_in   = queue_rgb.tryGet()
            nn_in    = queue_nn.tryGet()
            depth_in = queue_depth.tryGet()
            imu_in   = queue_imu.tryGet()

            if rgb_in is None:
                continue

            frame = rgb_in.getCvFrame()

            detections = []
            if nn_in is not None:
                output = np.array(nn_in.getTensor("output0"))
                warmup_frames += 1

                if warmup_frames <= WARMUP_COUNT:
                    # build the smoothing buffer but emit nothing yet
                    decode_yolov8(output, conf_threshold)
                else:
                    # buffer is warm — emit real detections
                    all_dets = decode_yolov8(output, conf_threshold)
                    for x1, y1, x2, y2, conf, cls in all_dets:
                        if cls != PERSON_CLASS:
                            continue
                        detections.append((x1, y1, x2, y2, conf))

            yield frame, detections

if __name__ == "__main__":
    import os
    os.makedirs("frames", exist_ok=True)

    pipeline, device, q_rgb, q_nn, q_depth, q_imu = build_pipeline()

    count = 0
    for frame, detections in frame_generator(pipeline, device, q_rgb, q_nn, q_depth, q_imu):
        print(f"frame {count} — {len(detections)} persons — shape: {frame.shape}")

        # draw boxes
        for x1, y1, x2, y2, conf in detections:
            cv2.rectangle(frame, (x1,y1), (x2,y2), (0,255,0), 2)
            cv2.putText(frame, f"person {conf:.0%}",
                        (x1, y1-6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 1)

        cv2.imwrite(f"frames/frame_{count:04d}.jpg", frame)
        count += 1
        if count >= 30:
            break
