"""
test_camera_motors.py
---------------------
Simple test: spin wheels when person detected, stop when not.
No tracking, no steering, no state machine — just detection → motors.
"""
import RPi.GPIO as GPIO
import numpy as np
import depthai as dai
import time

# ── Motor setup ───────────────────────────────────────────────────────────────
PIN_LEFT  = 13
PIN_RIGHT = 12
FREQ      = 100
V_MAX     = 1.0

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(PIN_LEFT,  GPIO.OUT)
GPIO.setup(PIN_RIGHT, GPIO.OUT)

pwm_left  = GPIO.PWM(PIN_LEFT,  FREQ)
pwm_right = GPIO.PWM(PIN_RIGHT, FREQ)
pwm_left.start(1)
pwm_right.start(1)

def set_speed(speed):
    """speed: 0.0 to 1.0"""
    duty = speed * V_MAX * 100
    duty = max(0, min(100, duty))
    pwm_left.ChangeDutyCycle(duty)
    pwm_right.ChangeDutyCycle(duty)

# ── Camera + detection setup ──────────────────────────────────────────────────
BLOB_PATH      = "/home/lpaisano/.cache/blobconverter/yolov8n_openvino_2022.1_12shave.blob"
IMG_W, IMG_H   = 640, 352
CONF_THRESHOLD = 0.20
IOU_THRESHOLD  = 0.35
PERSON_CLASS   = 0

_score_buffer = None
_SMOOTH_ALPHA = 0.15

def decode_yolov8(output):
    global _score_buffer
    pred = output.squeeze(0).T
    boxes  = pred[:, :4]
    scores = pred[:, 4:]

    if _score_buffer is None or _score_buffer.shape != scores.shape:
        _score_buffer = scores.copy()
    else:
        _score_buffer = _SMOOTH_ALPHA * scores + (1 - _SMOOTH_ALPHA) * _score_buffer

    scores    = _score_buffer
    class_ids = np.argmax(scores, axis=1)
    confs     = scores[np.arange(len(scores)), class_ids]
    mask      = confs >= CONF_THRESHOLD
    boxes     = boxes[mask]
    confs     = confs[mask]
    class_ids = class_ids[mask]

    if len(boxes) == 0:
        return []

    import cv2
    cx, cy, w, h = boxes[:,0], boxes[:,1], boxes[:,2], boxes[:,3]
    x1 = (cx - w/2).astype(int)
    y1 = (cy - h/2).astype(int)

    indices = cv2.dnn.NMSBoxes(
        [[int(x1[i]), int(y1[i]), int(w[i]), int(h[i])] for i in range(len(x1))],
        confs.tolist(), CONF_THRESHOLD, IOU_THRESHOLD
    )
    return [(int(class_ids[i])) for i in indices]

# ── Pipeline ──────────────────────────────────────────────────────────────────
device   = dai.Device()
pipeline = dai.Pipeline(device)
cam      = pipeline.create(dai.node.Camera).build(dai.CameraBoardSocket.CAM_A)
nn_input = cam.requestOutput((IMG_W, IMG_H), type=dai.ImgFrame.Type.BGR888p, fps=30)
nn       = pipeline.create(dai.node.NeuralNetwork)
nn.setBlobPath(BLOB_PATH)
nn.setNumInferenceThreads(2)
nn.input.setBlocking(False)
nn.input.setMaxSize(1)
nn_input.link(nn.input)
q_nn = nn.out.createOutputQueue(maxSize=4, blocking=False)

# ── Main loop ─────────────────────────────────────────────────────────────────
print("Starting — stand in front of camera...")
print("Person detected → wheels spin at 30% speed")
print("No person → wheels stop")
print("Ctrl+C to exit")

try:
    with pipeline:
        pipeline.start()
        time.sleep(1.0)  # warmup

        warmup = 0
        while pipeline.isRunning():
            msg = q_nn.tryGet()
            if msg is None:
                continue

            output    = np.array(msg.getTensor("output0"))
            classes   = decode_yolov8(output)
            warmup   += 1

            if warmup < 15:
                continue

            person_detected = PERSON_CLASS in classes

            if person_detected:
                print("PERSON detected → spinning wheels")
                set_speed(0.75)   # 75% speed
            else:
                print("No person → stopping")
                set_speed(0.0)

except KeyboardInterrupt:
    pass

# ── Cleanup ───────────────────────────────────────────────────────────────────
set_speed(0.0)
pwm_left.stop()
pwm_right.stop()
GPIO.cleanup()
print("Done")