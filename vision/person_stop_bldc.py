import time
import signal
import sys

import depthai as dai
import numpy as np

# =========================
#  MOTOR CONTROL (PWM)
# =========================
try:
    import RPi.GPIO as GPIO
    ON_PI = True
except ImportError:
    ON_PI = False
    print("[WARN] RPi.GPIO not found. Motor output will be disabled (testing mode).")

# ---- Pi GPIO pin for throttle PWM (GPIO18 supports hardware PWM on Pi)
PWM_PIN = 18
PWM_FREQ_HZ = 50  # RC/servo style signal

# These duty cycles are COMMON defaults for "servo-like" throttle.
# You MUST tune them for your controller.
DUTY_STOP = 7.5       # often neutral
DUTY_FORWARD = 8.2    # small forward command
DUTY_REVERSE = 6.8    # optional (not used by default)

# Prevent spamming PWM with the same value
_last_duty = None
_pwm = None


def motor_init():
    global _pwm, _last_duty
    if not ON_PI:
        return

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(PWM_PIN, GPIO.OUT)

    _pwm = GPIO.PWM(PWM_PIN, PWM_FREQ_HZ)
    _pwm.start(DUTY_STOP)
    _last_duty = DUTY_STOP
    print("[MOTOR] PWM initialized on GPIO", PWM_PIN)


def motor_set_duty(duty):
    """Set throttle PWM duty cycle safely (and only if changed)."""
    global _last_duty
    if not ON_PI:
        print(f"[MOTOR][SIM] duty={duty}")
        return

    # Clamp duty to a reasonable range
    duty = float(np.clip(duty, 5.0, 10.0))

    if _last_duty is None or abs(duty - _last_duty) > 0.01:
        _pwm.ChangeDutyCycle(duty)
        _last_duty = duty


def motor_stop():
    motor_set_duty(DUTY_STOP)


def motor_forward():
    motor_set_duty(DUTY_FORWARD)


def motor_cleanup():
    if not ON_PI:
        return
    try:
        motor_stop()
        time.sleep(0.1)
        _pwm.stop()
    except Exception:
        pass
    GPIO.cleanup()
    print("[MOTOR] Cleaned up")


# =========================
#  VISION CONFIG
# =========================
# Person label for MobileNet-SSD (COCO-like label map used by DepthAI examples)
# The DepthAI MobileNet-SSD blob often uses the Pascal VOC labels.
# In the standard example, "person" is label 15 for the VOC set.
# To avoid label confusion, we’ll just use det.label == 15 as "person".
PERSON_LABEL = 15

# Movement logic settings
STOP_DISTANCE_MM = 900      # if person is closer than this -> stop (tune)
CENTER_TOL_PX = 60          # how far from center before we "turn" (future)
CONF_MIN = 0.50             # min detection confidence

# Behavior settings
NO_PERSON_TIMEOUT_S = 0.4   # if no person seen recently -> stop
LOOP_PRINT_EVERY_S = 0.3    # print status rate


# =========================
#  DEPTHAI PIPELINE
# =========================
def create_pipeline():
    pipeline = dai.Pipeline()

    # Color camera
    cam_rgb = pipeline.createColorCamera()
    cam_rgb.setPreviewSize(300, 300)       # NN input size
    cam_rgb.setInterleaved(False)
    cam_rgb.setFps(30)

    # Mono cameras for stereo depth
    mono_l = pipeline.createMonoCamera()
    mono_r = pipeline.createMonoCamera()
    mono_l.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
    mono_r.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
    mono_l.setBoardSocket(dai.CameraBoardSocket.LEFT)
    mono_r.setBoardSocket(dai.CameraBoardSocket.RIGHT)

    stereo = pipeline.createStereoDepth()
    stereo.setDefaultProfilePreset(dai.node.StereoDepth.PresetMode.HIGH_DENSITY)
    stereo.setDepthAlign(dai.CameraBoardSocket.RGB)
    stereo.setSubpixel(True)

    mono_l.out.link(stereo.left)
    mono_r.out.link(stereo.right)

    # Spatial detection network (MobileNet SSD)
    spatial_nn = pipeline.createMobileNetSpatialDetectionNetwork()
    spatial_nn.setBlobPath("mobilenet-ssd_openvino_2021.4_6shave.blob")  # <-- see note below
    spatial_nn.setConfidenceThreshold(CONF_MIN)
    spatial_nn.input.setBlocking(False)
    spatial_nn.setBoundingBoxScaleFactor(0.5)
    spatial_nn.setDepthLowerThreshold(100)     # mm
    spatial_nn.setDepthUpperThreshold(10000)   # mm

    # Link inputs
    cam_rgb.preview.link(spatial_nn.input)
    stereo.depth.link(spatial_nn.inputDepth)

    # Outputs
    xout_nn = pipeline.createXLinkOut()
    xout_nn.setStreamName("nn")
    spatial_nn.out.link(xout_nn.input)

    xout_rgb = pipeline.createXLinkOut()
    xout_rgb.setStreamName("rgb")
    cam_rgb.preview.link(xout_rgb.input)

    return pipeline


# =========================
#  MAIN LOOP
# =========================
def main():
    motor_init()
    motor_stop()

    pipeline = create_pipeline()

    last_person_time = 0.0
    last_print_time = 0.0

    def handle_exit(sig, frame):
        print("\n[EXIT] Stopping motors...")
        motor_stop()
        motor_cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    print("[INFO] Starting OAK-D Lite pipeline...")
    print("[NOTE] If you get a blob error: see instructions at bottom of this file.\n")

    with dai.Device(pipeline) as device:
        q_nn = device.getOutputQueue(name="nn", maxSize=4, blocking=False)
        q_rgb = device.getOutputQueue(name="rgb", maxSize=4, blocking=False)

        while True:
            in_nn = q_nn.tryGet()
            in_rgb = q_rgb.tryGet()

            # We don't *need* the frame for motion control, but it helps with width/center.
            frame_w = 300
            frame_h = 300
            if in_rgb is not None:
                frame = in_rgb.getCvFrame()
                frame_h, frame_w = frame.shape[:2]

            person_best = None
            person_best_area = 0

            if in_nn is not None:
                detections = in_nn.detections

                for det in detections:
                    if det.label != PERSON_LABEL:
                        continue
                    if det.confidence < CONF_MIN:
                        continue

                    # bbox in pixels
                    x1 = int(det.xmin * frame_w)
                    y1 = int(det.ymin * frame_h)
                    x2 = int(det.xmax * frame_w)
                    y2 = int(det.ymax * frame_h)
                    area = max(0, x2 - x1) * max(0, y2 - y1)

                    # keep the largest "person"
                    if area > person_best_area:
                        person_best_area = area
                        person_best = (x1, y1, x2, y2, det)

            now = time.time()

            if person_best is not None:
                x1, y1, x2, y2, det = person_best
                cx = (x1 + x2) // 2
                frame_cx = frame_w // 2

                # Depth in mm from Spatial NN
                z_mm = int(det.spatialCoordinates.z)

                last_person_time = now

                # --- Decision logic (STOP or FORWARD for now) ---
                if z_mm > 0 and z_mm < STOP_DISTANCE_MM:
                    motor_stop()
                    action = "STOP (too close)"
                else:
                    motor_forward()
                    action = "FORWARD"

                # (Optional future) Left/Right steering decision:
                # if cx < frame_cx - CENTER_TOL_PX: action = "LEFT"
                # elif cx > frame_cx + CENTER_TOL_PX: action = "RIGHT"

                if now - last_print_time > LOOP_PRINT_EVERY_S:
                    print(f"[TRACK] person cx={cx}/{frame_cx}  z={z_mm}mm  -> {action}")
                    last_print_time = now

            else:
                # No person detected recently -> STOP
                if (now - last_person_time) > NO_PERSON_TIMEOUT_S:
                    motor_stop()

                if now - last_print_time > LOOP_PRINT_EVERY_S:
                    print("[TRACK] no person -> STOP")
                    last_print_time = now

            time.sleep(0.01)


if __name__ == "__main__":
    main()