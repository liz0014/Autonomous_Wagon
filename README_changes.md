README_changes
==============

This file summarizes the code changes made to the repository relative to
the original code snapshot. Changes were implemented to wire YOLOv8n into
the vision pipeline, add proportional distance control, implement a basic
IoU-based person tracker, smooth motor acceleration, and fix scripts +
dependencies so the project is runnable for testing.

High-level summary
------------------
- Replaced hardcoded YOLOv6 usage with `yolov8n` model name and added
  `DETECTION_LABEL` config for easier swapping to a vest/class-specific model.
- Added proportional distance control (bbox area → `speed_factor`) so the
  wagon slows as the target approaches rather than only STOP/FOLLOW binary.
- Implemented `PersonTracker` (IoU matching + velocity prediction + track IDs)
  to maintain consistent targets across frames and handle brief occlusions.
- Added acceleration ramping (`ACCEL_RAMP_RATE`) in the drive logic to
  smooth speed changes and avoid jerky motor commands.
- Added a fallback YOLOv8n webcam detector for non-OAK testing (`wagon_vision_yolo8.py`).
- Fixed runner scripts (`scripts/run_wagon.py`, `scripts/run_web_stream.py`,
  `scripts/run_vision.py`) and populated `requirements.txt`.

Files changed (key edits)
-------------------------
- app/config/settings.py
  - YOLO_MODEL set to `yolov8n`
  - Added `DETECTION_LABEL`, `TARGET_AREA`, `MIN_AREA`, `ACCEL_RAMP_RATE`,
    `TRACKER_MAX_LOST_FRAMES`, `TRACKER_IOU_THRESHOLD`

- app/vision/oakd_camera.py
  - Load `YOLO_MODEL` from settings instead of hardcoded `yolov6-nano`.

- app/vision/wagon_vision_yolo8.py
  - New helper to run YOLOv8n via Ultralytics on a webcam or file for
    local tuning when OAK-D hardware is unavailable.

- app/vision/utils.py
  - `draw_person_detections` now filters by `DETECTION_LABEL`.
  - HUD updated to show `speed_factor` percentage.

- app/navigation/follow_logic.py
  - Now returns `(cmd, steer, speed_factor, frame_center)`.
  - Linear mapping from bbox area to `speed_factor` in [0.0, 1.0].

- app/vision/tracking.py
  - New IoU-based `PersonTracker` with `Track` class, greedy matching,
    velocity smoothing and track lifetime handling.

- app/control/brain.py
  - Accepts `speed_factor`, applies it to `BASE_SPEED`, and ramps
    left/right speeds with `_ramp()` limited by `ACCEL_RAMP_RATE`.

- app/navigation/person_detection_logic.py
  - Added `get_all_persons()` returning detection tuples for the tracker.

- app/web/app.py
  - Integrates `PersonTracker`, uses `speed_factor` and `draw_hud()` update,
    added `create_app()` factory.

- scripts/run_wagon.py, scripts/run_web_stream.py, scripts/run_vision.py
  - Rewritten to use the updated APIs and to be runnable for testing.

- requirements.txt
  - Populated with `depthai`, `opencv-python`, `numpy`, `flask`, `pyserial`.

Notes & next steps
------------------
- The tracker and distance-to-speed mapping use default constants in
  `settings.py`. Tune `TARGET_AREA`, `MIN_AREA`, and the tracker's IoU
  threshold for your specific camera mounting and environment.
- If you plan to detect a hi-vis vest class instead of `person`, train or
  convert a YOLOv8 model and set `DETECTION_LABEL` accordingly.
- Pushing changes created a new branch `Zach` (see git push result).
README_changes
==============

This file summarizes the code changes made to the repository relative to
the original code snapshot. Changes were implemented to wire YOLOv8n into
the vision pipeline, add proportional distance control, implement a basic
IoU-based person tracker, smooth motor acceleration, and fix scripts +
dependencies so the project is runnable for testing.

High-level summary
------------------
- Replaced hardcoded YOLOv6 usage with `yolov8n` model name and added
  `DETECTION_LABEL` config for easier swapping to a vest/class-specific model.
- Added proportional distance control (bbox area → `speed_factor`) so the
  wagon slows as the target approaches rather than only STOP/FOLLOW binary.
- Implemented `PersonTracker` (IoU matching + velocity prediction + track IDs)
  to maintain consistent targets across frames and handle brief occlusions.
- Added acceleration ramping (`ACCEL_RAMP_RATE`) in the drive logic to
  smooth speed changes and avoid jerky motor commands.
- Added a fallback YOLOv8n webcam detector for non-OAK testing (`wagon_vision_yolo8.py`).
- Fixed runner scripts (`scripts/run_wagon.py`, `scripts/run_web_stream.py`,
  `scripts/run_vision.py`) and populated `requirements.txt`.

Files changed (key edits)
-------------------------
- app/config/settings.py
  - YOLO_MODEL set to `yolov8n`
  - Added `DETECTION_LABEL`, `TARGET_AREA`, `MIN_AREA`, `ACCEL_RAMP_RATE`,
    `TRACKER_MAX_LOST_FRAMES`, `TRACKER_IOU_THRESHOLD`

- app/vision/oakd_camera.py
  - Load `YOLO_MODEL` from settings instead of hardcoded `yolov6-nano`.

- app/vision/wagon_vision_yolo8.py
  - New helper to run YOLOv8n via Ultralytics on a webcam or file for
    local tuning when OAK-D hardware is unavailable.

- app/vision/utils.py
  - `draw_person_detections` now filters by `DETECTION_LABEL`.
  - HUD updated to show `speed_factor` percentage.

- app/navigation/follow_logic.py
  - Now returns `(cmd, steer, speed_factor, frame_center)`.
  - Linear mapping from bbox area to `speed_factor` in [0.0, 1.0].

- app/vision/tracking.py
  - New IoU-based `PersonTracker` with `Track` class, greedy matching,
    velocity smoothing and track lifetime handling.

- app/control/brain.py
  - Accepts `speed_factor`, applies it to `BASE_SPEED`, and ramps
    left/right speeds with `_ramp()` limited by `ACCEL_RAMP_RATE`.

- app/navigation/person_detection_logic.py
  - Added `get_all_persons()` returning detection tuples for the tracker.

- app/web/app.py
  - Integrates `PersonTracker`, uses `speed_factor` and `draw_hud()` update,
    added `create_app()` factory.

- scripts/run_wagon.py, scripts/run_web_stream.py, scripts/run_vision.py
  - Rewritten to use the updated APIs and to be runnable for testing.

- requirements.txt
  - Populated with `depthai`, `opencv-python`, `numpy`, `flask`, `pyserial`.

Notes & next steps
------------------
- The tracker and distance-to-speed mapping use default constants in
  `settings.py`. Tune `TARGET_AREA`, `MIN_AREA`, and the tracker's IoU
  threshold for your specific camera mounting and environment.
- If you plan to detect a hi-vis vest class instead of `person`, train or
  convert a YOLOv8 model and set `DETECTION_LABEL` accordingly.
- Pushing changes created a new branch `Zach` (see git push result).
