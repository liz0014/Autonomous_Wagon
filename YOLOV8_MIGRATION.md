# YOLOv8 Migration Summary

## Changes Made

Your autonomous wagon project has been successfully updated to run on **YOLOv8** instead of YOLOv6-nano. Here's what was changed:

### 1. **requirements.txt** 
- **Removed:** `depthai` (DepthAI/OAK-D specific framework)
- **Added:** `ultralytics>=8.0.0` (YOLOv8 package)
- **Also added:** `opencv-python>=4.8.0`, `numpy>=1.24.0`, `Flask>=2.3.0`

### 2. **app/config/settings.py**
- Changed: `YOLO_MODEL = "yolov6-nano"` → `YOLO_MODEL = "yolov8n"`
- YOLOv8 nano model is lightweight and suitable for edge devices like Raspberry Pi

### 3. **app/vision/oakd_camera.py** (Major rewrite)
- **Old approach:** DepthAI pipeline with OAK-D specific DetectionNetwork
- **New approach:** OpenCV camera + YOLOv8 inference
- **Added:** `DetectionResult` class for backward compatibility
  - Maintains the same attributes (xmin, ymin, xmax, ymax, confidence, label)
  - Ensures rest of codebase works without changes
- **Camera support:** 
  - OpenCV VideoCapture (0 = default camera)
  - Can use OAK-D if configured as default camera
  - Fallback to webcam if no OAK-D available

### 4. **app/web/app.py**
- Updated `_stream()` function to use new camera/model API
- Changed: `pipeline.start() / pipeline.stop()` → `camera.release()`
- Changed: Queue-based detection → YOLOv8 inference-based detection

## Architecture

```
Camera (OpenCV)
    ↓
YOLOv8 Inference
    ↓
DetectionResult objects (backward compatible)
    ↓
Person detection logic (unchanged)
    ↓
Follow logic (unchanged)
    ↓
Motor control (unchanged)
```

## Installation

Before running, install the new dependencies:

```bash
pip install -r requirements.txt
```

On Raspberry Pi, the first run will download the YOLOv8 nano model (~6MB).

## Key Features

 **Backward compatible** - Rest of the codebase (navigation, control) unchanged  
 **Lightweight** - YOLOv8n is efficient on Raspberry Pi  
 **Flexible camera** - Works with OAK-D, USB webcams, or Raspberry Pi camera  
 **Person-only detection** - Filters to only detect "person" class (COCO index 0)  
 **Same output format** - Detection boxes remain in normalized coordinates (0-1)

## Testing

To test locally before deploying:

```bash
python run.py
# Then visit http://localhost:5000 in a browser
```

## Notes

- YOLOv8 uses COCO dataset classes; person is always at index 0
- Confidence threshold set to 0.3 (adjust in `frame_generator()` if needed)
- Model will auto-download on first run
- If using OAK-D, ensure it's set as default camera in system
