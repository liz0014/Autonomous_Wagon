# Autonomous Wagon

An autonomous Wagon that detects and follows people using computer vision. Powered by a Raspberry Pi, OAK-D camera, and YOLOv6/v8 neural networks.

## Table of Contents

- [Overview](#overview)
- [Hardware Requirements](#hardware-requirements)
- [Software Setup](#software-setup)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Running the Wagon](#running-the-wagon)
- [Web Interface](#web-interface)
- [Development](#development)
- [Troubleshooting](#troubleshooting)

## Overview

The Autonomous Wagon is designed to autonomously search for and follow a person in its environment. It operates through a simple state machine with three states:

- **SEARCH**: No person detected; wagon rotates in place to scan the environment
- **FOLLOW**: Person detected; wagon drives toward them while maintaining steering corrections
- **STOP**: Person is too close; wagon stops and holds position

The system runs entirely on a Raspberry Pi with:
- **Vision**: OAK-D camera running YOLOv6-nano YOLO model for person detection
- **Motion**: Differential drive steering with independent left/right motor control via GPIO PWM
- **Interface**: Flask-based web server streaming MJPEG video with real-time HUD overlay
- **Coordination**: Modular control system separating vision logic, navigation, and motor control

## Hardware Requirements

### Essential Components
- **Raspberry Pi 4** (4GB+ RAM recommended) or **Raspberry Pi 5**
- **OAK-D Camera** (Luxonis) for person detection
- **2× DC Motors** with wheels
- **Motor Driver** (e.g., L298N or Adafruit Motor Hat) supporting GPIO PWM
- **Power Supply** (adequate for Pi + motors; recommend 2× USB-C or single PSU with BEC regulator)
- **USB Hub or Cable** for OAK-D camera connection

### GPIO Pin Requirements (BCM numbering, customizable)
- **Left Motor**: GPIO 17 (FWD), 27 (REV), 12 (PWM)
- **Right Motor**: GPIO 22 (FWD), 23 (REV), 13 (PWM)

See [Configuration](#configuration) for pin reassignment.

## Software Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Autonomous_Wagon
```

### 2. Create Python Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Install DepthAI SDK (for OAK-D Camera)

```bash
python3 -m pip install depthai
```

### 5. Download the YOLO Model

The system uses Luxonis Model Zoo. Models are automatically downloaded on first run, but you can pre-download:

```bash
# Models are cached in ~/.cache/blobconverter/
# or configure in app/vision/oakd_camera.py
```

### 6. Verify Setup

Test the camera pipeline:

```bash
python3 scripts/run_vision.py
```

Test motor control (requires GPIO access):

```bash
sudo python3 scripts/run_wagon.py
```

## Project Structure

```
Autonomous_Wagon/
├── app/                              # Main application package
│   ├── config/
│   │   └── settings.py              # Central configuration (EDIT THIS)
│   ├── control/
│   │   ├── brain.py                 # Motor control logic
│   │   ├── motor_pwm.py             # GPIO PWM driver
│   │   ├── serial.py                # Optional serial bridge
│   │   └── __pycache__/
│   ├── navigation/
│   │   ├── state_machine.py         # FSM: SEARCH/FOLLOW/STOP
│   │   ├── person_detection_logic.py # Person targeting
│   │   └── follow_logic.py          # Steering compute
│   ├── vision/
│   │   ├── oakd_camera.py           # OAK-D pipeline builder
│   │   ├── wagon_vision_yolo8.py    # YOLOv8 implementation
│   │   ├── wagon_vision_yolo6.py    # YOLOv6 implementation
│   │   ├── tracking.py              # Frame-to-frame tracking
│   │   ├── utils.py                 # Drawing utilities
│   │   └── __pycache__/
│   └── web/
│       ├── app.py                   # Flask server & MJPEG stream
│       └── __pycache__/
├── scripts/
│   ├── run_vision.py                # Standalone vision test
│   ├── run_wagon.py                 # Full wagon run
│   ├── run_web_stream.py            # Web stream only
│   └── __pycache__/
├── tests/
│   ├── test_wheels.py               # Motor control tests
│   ├── test_wheels_demo.py          # Interactive motor demo
│   ├── test_oakd_raspi.py           # Camera tests
│   ├── test_person_detection.py     # Detection pipeline tests
│   ├── test_person_logic.py         # Person targeting tests
│   └── test_acceleration_serial.py
├── run.py                           # Main entry point
├── requirements.txt                 # Python dependencies
└── README.md                        # This file
```


### Key Settings

```python
# ── Camera / Detection ────────────────────────────────────────────────
YOLO_MODEL          # "yolov6-nano" or "yolov8s" — model choice
FRAME_CENTER_FRACTION # 0.5 = exact horizontal center

# ── Follow Behaviour ──────────────────────────────────────────────────
STOP_AREA_THRESHOLD # Pixel area of target bbox that triggers STOP
                    # (tune for your environment; ~90k is starting point)

# ── Motor Drive ───────────────────────────────────────────────────────
BASE_SPEED          # Forward cruise speed [0.0–1.0]

# ── GPIO Pins (BCM numbering) ────────────────────────────────────────
PIN_LEFT_FWD, PIN_LEFT_REV, PIN_LEFT_PWM
PIN_RIGHT_FWD, PIN_RIGHT_REV, PIN_RIGHT_PWM
PWM_FREQ_HZ         # PWM frequency (1000 Hz default)


# ── Flask Web Server ──────────────────────────────────────────────────
FLASK_HOST          # 0.0.0.0 (accessible on network)
FLASK_PORT          # 5000
JPEG_QUALITY        # 0–100 (lower = faster on slow WiFi)
```

## Running the Wagon

### Quick Start (Full System)

```bash
source .venv/bin/activate
python3 run.py
```

The wagon will start searching for a person. Navigate to `http://<pi-ip>:5000` in a browser to view the MJPEG stream with HUD.

### Run Individual Components

**Vision pipeline only** (no motors, no web):
```bash
python3 scripts/run_vision.py
```

**Web stream only** (camera + web interface, no motor control):
```bash
python3 scripts/run_web_stream.py
```

**Full wagon** (with motor control):
```bash
sudo python3 scripts/run_wagon.py
```

### Stopping the Wagon

- Press **Ctrl+C** in the terminal to stop gracefully
- Motors will turn off immediately
- Camera and web server will close

## Web Interface

Browse to `http://<raspberry-pi-ip>:5000` from any device on the same network (e.g., phone, laptop, desktop).

**HUD Overlay Shows:**
- Person bounding boxes (green = detected, tracked)
- Center frame line (cyan)
- Current state (SEARCH/FOLLOW/STOP) in top-left
- Steer value and motor speeds
- FPS counter

## Development

### Code Organization

- **Vision Logic** (`app/vision/`): Frame capture, YOLO inference, detection drawing
- **Navigation Logic** (`app/navigation/`): Person targeting, steering compute, state control
- **Motor Control** (`app/control/`): GPIO PWM, brake, speed commands
- **Web Interface** (`app/web/`): Flask server, MJPEG streaming, HUD generation
- **Configuration** (`app/config/`): Single source of truth for all parameters

### Key Concepts

**Person Detection Logic** (`app/navigation/person_detection_logic.py`):
- Filters YOLO detections for person class
- Tracks best target between frames
- Computes target position relative to frame center

**Follow Logic** (`app/navigation/follow_logic.py`):
- Computes steering value based on target horizontal offset
- Generates state commands (SEARCH/FOLLOW/STOP) based on bbox area
- Normalized steering output: `[-1.0, +1.0]`

**Brain** (`app/control/brain.py`):
- Translates `(WagonState, steer)` into motor speeds
- Implements differential drive: slows one wheel, speeds up the other
- Formula: `correction = steer * STEER_GAIN`; then `left = BASE - correction`, `right = BASE + correction`

**State Machine** (`app/navigation/state_machine.py`):
- Three states: SEARCH, FOLLOW, STOP
- Transitions controlled by commands from follow_logic

### Testing

Run the included tests to verify components:

```bash
# Motor control
python3 tests/test_wheels.py

# Camera & detection
python3 tests/test_oakd_raspi.py

# Person detection logic
python3 tests/test_person_detection.py
python3 tests/test_person_logic.py

# Interactive motor demo
python3 tests/test_wheels_demo.py
```

### Adding New Features

1. **New Navigation Behavior**: Add state to `WagonState` enum in `state_machine.py`; update command logic in `follow_logic.py`
2. **New Motor Control**: Extend `brain.py` to handle new states
3. **Obstacle Avoidance**: Integrate depth data from OAK-D stereo pair into follow logic

## Troubleshooting

### Camera Not Detected

```bash
lsusb | grep OAK
# Should show Luxonis device. If not:
# 1. Check USB port and cable
# 2. Try different USB port (avoid hub if possible)
# 3. Reboot Pi: sudo reboot
```

### Motor Not Responding

```bash
# Test GPIO pins directly:
python3 tests/test_wheels_demo.py
# Interactive menu to test each motor and direction

# Verify pin assignments:
grep -E "PIN_" app/config/settings.py
# Update if pins don't match your hardware

# Check PWM frequency is reasonable (1000 Hz default):
grep PWM_FREQ app/config/settings.py
```

### Web Stream Laggy

1. Reduce JPEG_QUALITY in settings.py
2. Reduce frame resolution in `oakd_camera.py`
3. Lower PWM_FREQ if motor control is blocking
4. Use local WiFi (not internet gateway)

### Permission Denied on GPIO

Ensure you're running with `sudo`:
```bash
sudo python3 run.py
```

Or configure GPIO permissions:
```bash
sudo usermod -a -G gpio $USER
sudo reboot
```

### YOLO Model Download Fails

Models are cached in `~/.cache/blobconverter/`. If download hangs:

```bash
# Clear cache and retry
rm -rf ~/.cache/blobconverter/

# Or manually check connectivity
curl https://api.blobconverter.luxonis.com/ -v
```

## Contributing

When adding or modifying code:

1. **Update settings.py** for any new tunable parameters
2. **Document functions** with docstrings explaining inputs and outputs
3. **Test changes** against existing tests and manually
4. **Run tests** before committing: `python3 -m pytest tests/` (if pytest installed)
5. **Update this README** if adding new features or changing configuration

## License

[Add license info here if applicable]

## Contact / Questions

[Add team contact info or link to issues tracker]
