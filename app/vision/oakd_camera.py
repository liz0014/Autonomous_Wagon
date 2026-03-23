"""
oakd_camera.py
--------------
Camera pipeline using YOLOv8 with OpenCV.
Yields (frame, detections) tuples for person detection.
Compatible interface with the rest of the app.
"""

import cv2
from ultralytics import YOLO
from app.config.settings import YOLO_MODEL


class DetectionResult:
    """Simple detection object matching DepthAI format for backward compatibility."""
    
    def __init__(self, xmin, ymin, xmax, ymax, confidence, label):
        self.xmin = xmin
        self.ymin = ymin
        self.xmax = xmax
        self.ymax = ymax
        self.confidence = confidence
        self.label = label


def build_pipeline():
    """
    Initialize YOLOv8 model and camera.
    Returns (camera, model, label_map) tuple.
    label_map is a dict with 0 -> 'person' for compatibility.
    """
    # Load YOLOv8 model
    model = YOLO(YOLO_MODEL)
    
    # Standard COCO classes - person is at index 0
    label_map = {0: 'person', 1: 'bicycle', 2: 'car', 3: 'motorbike', 
                 4: 'aeroplane', 5: 'bus', 6: 'train', 7: 'truck'}
    
    # Open default camera (0 = built-in camera, or OAK-D if configured)
    camera = cv2.VideoCapture(0)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    camera.set(cv2.CAP_PROP_FPS, 30)
    
    return camera, model, label_map


def frame_generator(camera, model):
    """
    Generator: yields (cv_frame, detections_list).
    Uses YOLOv8 inference on each frame.
    """
    while True:
        ret, frame = camera.read()
        if not ret:
            continue
        
        # Run YOLOv8 inference
        results = model(frame, conf=0.3, verbose=False)
        
        detections = []
        if results and len(results) > 0:
            result = results[0]
            h, w = frame.shape[:2]
            
            # Convert YOLOv8 results to DetectionResult format
            for box in result.boxes:
                # Get bounding box coordinates (xyxy format)
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                
                # Normalize to 0..1 range
                xmin = x1 / w
                ymin = y1 / h
                xmax = x2 / w
                ymax = y2 / h
                
                confidence = float(box.conf[0])
                class_id = int(box.cls[0])
                
                # Only include person detections
                if class_id == 0:  # COCO class 0 = person
                    det = DetectionResult(xmin, ymin, xmax, ymax, confidence, class_id)
                    detections.append(det)
        
        yield frame, detections