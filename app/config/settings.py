"""
settings.py
-----------
Single source of truth for tunable parameters.

"""
# Command strings emitted by follow_logic and consumed by state_machine
SEARCH_CMD = "SEARCH"
FOLLOW_CMD = "FOLLOW"
STOP_CMD   = "STOP"

# ── Camera / detection ────────────────────────────────────────────────────────
#YOLO_MODEL            = "yolov8n"    
DETECTION_LABEL       = "person"      # class to track (swap when using a custom vest model)
FRAME_CENTER_FRACTION = 0.6           # 0.6 = exact horizontal centre

# ── Follow behaviour ──────────────────────────────────────────────────────────
# Bounding-box area thresholds (tune for your camera resolution + mount height)
TARGET_AREA         = 50_000   # bbox area at ~1 m following distance
STOP_AREA_THRESHOLD = 90_000   # too close → full stop
MIN_AREA            =  5_000   # far away → full cruise speed


# ── Depth-based distance control (meters) ────────────────────────────────────
# These replace pixel area thresholds when stereo depth is available.
STOP_DIST_M     = 0.85   # walk closer than 0.8m the wagon stops
TARGET_DIST_M   = 1.2   #walk between 0.8m and 3.0m wagon follows 
FOLLOW_START_M  = 2.0   # walk beyond 2.0 m wagon goes full speed

# ── Motor drive ───────────────────────────────────────────────────────────────
BASE_SPEED        = 0.90   # 0.0–1.0 forward cruise speed, 
SEARCH_TURN_SPEED = 0.30   # spin-in-place speed while searching
STEER_GAIN        = 0.20   # how aggressively steer corrects heading
ACCEL_RAMP_RATE   = 0.03   # max speed change per frame (smooths jerks)
MID_MOVE_SPEED = 0.75

# ── Tracker ───────────────────────────────────────────────────────────────────
TRACKER_MAX_LOST_FRAMES = 15   # frames before a track is dropped
TRACKER_IOU_THRESHOLD   = 0.2  # minimum IoU to match detection to track

# ── GPIO pin assignments (BCM numbering) ──────────────────────────────────────

PIN_LEFT_PWM  = 12   # hardware PWM 
PIN_RIGHT_PWM = 13   # hardware PWM 

PWM_FREQ_HZ   = 1000

# ── Serial bridge ──────────────────────────────────────────────────
SERIAL_ENABLED = False
SERIAL_PORT    = "/dev/ttyUSB0"
SERIAL_BAUD    = 115200

# ── Flask web server ──────────────────────────────────────────────────────────
FLASK_HOST  = "0.0.0.0"
FLASK_PORT  = 5000
JPEG_QUALITY = 85   # 0-100, lower = faster stream on slow WiFi 