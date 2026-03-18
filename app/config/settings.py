"""
settings.py
-----------
Single source of truth for tunable parameters.
Edit here — nothing else needs to change.
"""
# Command strings emitted by follow_logic and consumed by state_machine
SEARCH_CMD = "SEARCH"
FOLLOW_CMD = "FOLLOW"
STOP_CMD   = "STOP"

# ── Camera / detection ────────────────────────────────────────────────────────
YOLO_MODEL          = "yolov6-nano"   # Luxonis Model Zoo name
FRAME_CENTER_FRACTION = 0.5           # 0.5 = exact horizontal centre

# ── Follow behaviour ──────────────────────────────────────────────────────────
# Pixel area of target bbox that triggers STOP (tune for your environment)
STOP_AREA_THRESHOLD = 90_000

# ── Motor drive ───────────────────────────────────────────────────────────────
BASE_SPEED       = 0.55   # 0.0–1.0 forward cruise speed
SEARCH_TURN_SPEED = 0.30  # spin-in-place speed while searching
STEER_GAIN       = 0.40   # how aggressively steer corrects heading

# ── GPIO pin assignments (BCM numbering) ──────────────────────────────────────
PIN_LEFT_FWD  = 17
PIN_LEFT_REV  = 27
PIN_LEFT_PWM  = 12   # hardware PWM recommended

PIN_RIGHT_FWD = 22
PIN_RIGHT_REV = 23
PIN_RIGHT_PWM = 13   # hardware PWM recommended

PWM_FREQ_HZ   = 1000

# ── Serial bridge (optional) ──────────────────────────────────────────────────
SERIAL_ENABLED = False
SERIAL_PORT    = "/dev/ttyUSB0"
SERIAL_BAUD    = 115200

# ── Flask web server ──────────────────────────────────────────────────────────
FLASK_HOST  = "0.0.0.0"
FLASK_PORT  = 5000
JPEG_QUALITY = 85   # 0-100, lower = faster stream on slow WiFi