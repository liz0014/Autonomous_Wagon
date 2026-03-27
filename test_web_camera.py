import depthai as dai
import numpy as np
import cv2
import os

os.makedirs("frames", exist_ok=True)
device = dai.Device()

BLOB_PATH = "/home/lpaisano/.cache/blobconverter/yolov8n_openvino_2022.1_6shave.blob"
CONF_THRESHOLD = 0.3
IOU_THRESHOLD  = 0.45
IMG_W, IMG_H   = 640, 352

def decode_yolov8(output, conf_thresh=CONF_THRESHOLD):
    # output shape: (1, 84, 4620) → squeeze to (84, 4620)
    pred = output.squeeze(0)          # (84, 4620)
    pred = pred.T                     # (4620, 84)

    # split box coords and class scores
    boxes  = pred[:, :4]              # (4620, 4) — cx, cy, w, h
    scores = pred[:, 4:]              # (4620, 80) — class scores

    # get best class and confidence per anchor
    class_ids = np.argmax(scores, axis=1)    # (4620,)
    confs     = scores[np.arange(len(scores)), class_ids]  # (4620,)

    # filter by confidence
    mask = confs >= conf_thresh
    boxes     = boxes[mask]
    confs     = confs[mask]
    class_ids = class_ids[mask]

    if len(boxes) == 0:
        return []

    # convert cx,cy,w,h → x1,y1,x2,y2 in pixel coords
    cx, cy, w, h = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
    x1 = ((cx - w / 2)).astype(int)
    y1 = ((cy - h / 2)).astype(int)
    x2 = ((cx + w / 2)).astype(int)
    y2 = ((cy + h / 2)).astype(int)

    # NMS
    results = []
    indices = cv2.dnn.NMSBoxes(
        [[int(x1[i]), int(y1[i]), int(w[i]), int(h[i])] for i in range(len(x1))],
        confs.tolist(), conf_thresh, IOU_THRESHOLD
    )
    for i in indices:
        results.append((int(x1[i]), int(y1[i]), int(x2[i]), int(y2[i]),
                        float(confs[i]), int(class_ids[i])))
    return results


with dai.Pipeline(device) as pipeline:

    cam = pipeline.create(dai.node.Camera).build()
    display_out = cam.requestOutput((IMG_W, IMG_H), type=dai.ImgFrame.Type.BGR888p, fps=20)
    nn_input    = cam.requestOutput((IMG_W, IMG_H), type=dai.ImgFrame.Type.BGR888p, fps=20)
    queue_rgb   = display_out.createOutputQueue(maxSize=1, blocking=False)

    nn = pipeline.create(dai.node.NeuralNetwork)
    nn.setBlobPath(BLOB_PATH)
    nn.setNumInferenceThreads(2)
    nn.input.setBlocking(False)
    nn.input.setMaxSize(1)
    nn_input.link(nn.input)
    queue_nn = nn.out.createOutputQueue(maxSize=1, blocking=False)

    pipeline.start()

    frame_count = 0
    while pipeline.isRunning() and frame_count < 30:
        rgb_in = queue_rgb.tryGet()
        nn_in  = queue_nn.tryGet()

        if rgb_in is None:
            continue

        rgb_frame = rgb_in.getCvFrame()

        if nn_in is not None:
            output = np.array(nn_in.getTensor("output0"))
            dets   = decode_yolov8(output)
            print(f"frame {frame_count} — {len(dets)} detections")

            for x1, y1, x2, y2, conf, cls in dets:
                if cls != 0:  # person only
                    continue
                cv2.rectangle(rgb_frame, (x1,y1), (x2,y2), (0,255,0), 2)
                cv2.putText(rgb_frame, f"person {conf:.0%}",
                            (x1, y1-6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 1)

        cv2.imwrite(f"frames/frame_{frame_count:04d}.jpg", rgb_frame)
        frame_count += 1

print("Done — check frames/")