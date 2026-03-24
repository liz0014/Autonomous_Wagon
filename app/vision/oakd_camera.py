"""
oakd_camera.py
--------------
Camera + YOLOv8 integration. Returns DetectionResult objects for backward compatibility.
Supports OAK-D Lite via OpenCV (set as default camera in system) or any USB webcam.

Usage:
    camera, model, label_map = build_pipeline()
    for frame, detections in frame_generator(camera, model):
        # detections is a list of DetectionResult objects
        for det in detections:
            print(f"Person at {det.xmin}, {det.ymin} with conf {det.confidence}")
"""

import cv2
from ultralytics import YOLO
from app.config.settings import YOLO_MODEL


class DetectionResult:
    """Backward-compatible detection result matching DepthAI format."""
    def __init__(self, xmin, ymin, xmax, ymax, confidence, label=0):
        self.xmin = xmin
        self.ymin = ymin
        self.xmax = xmax
        self.ymax = ymax
        self.confidence = confidence
        self.label = label


def build_pipeline():
    """
    Build and return (camera, model, label_map).
    
    Returns:
        camera     : cv2.VideoCapture object
        model      : YOLO model instance
        label_map  : dict mapping class_id to class_name (from YOLO)
    """
    # Load YOLOv8 model (auto-downloads on first run)
    model = YOLO(YOLO_MODEL + ".pt")
    
    # Open default camera (0 = OAK-D if set as default, else webcam)
    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        raise RuntimeError("Cannot open camera. Ensure OAK-D/webcam is connected.")
    
    # Optional: tune camera resolution for better performance
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    # Get class names from YOLO model
    label_map = model.names  # dict: {0: 'person', 1: 'bicycle', ...}
    
    return camera, model, label_map


def frame_generator(camera, model, conf_threshold=0.3):
    """
    Generator: yields (cv_frame, detections_list).
    
    Args:
        camera          : cv2.VideoCapture object
        model           : YOLO model instance
        conf_threshold  : float, minimum confidence to keep detection (0-1)
    
    Yields:
        frame           : numpy BGR image
        detections      : list of DetectionResult objects (only "person" class)
    """
    while True:
        ok, frame = camera.read()
        if not ok:
            break
        
        # Run YOLOv8 inference
        results = model(frame, verbose=False)[0]
        
        # Extract detections
        detections = []
        for box in results.boxes:
            cls_id = int(box.cls[0])
            class_name = results.names[cls_id]
            
            # Filter for "person" class only
            if class_name != "person":
                continue
            
            # Check confidence threshold
            conf = float(box.conf[0])
            if conf < conf_threshold:
                continue
            
            # Convert to normalized coordinates (0..1)
            x1, y1, x2, y2 = box.xyxy[0]
            h, w = frame.shape[:2]
            
            xmin = float(x1) / w
            ymin = float(y1) / h
            xmax = float(x2) / w
            ymax = float(y2) / h
            
            # Create DetectionResult for backward compatibility
            det = DetectionResult(
                xmin=xmin, ymin=ymin, xmax=xmax, ymax=ymax,
                confidence=conf, label=cls_id
            )
            detections.append(det)
        
        yield frame, detections