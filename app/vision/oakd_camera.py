"""
oakd_camera.py
--------------
Manages the DepthAI pipeline for the OAK-D Lite.
Yields (frame, detections) tuples so the rest of the app
stays decoupled from hardware specifics.
"""

import depthai as dai


def build_pipeline():
    """
    Build and return (pipeline, q_rgb, q_det, label_map).
    Uses YOLOv6-nano from the Luxonis Model Zoo.
    Caller is responsible for pipeline.start() / pipeline.stop().
    """
    pipeline = dai.Pipeline()

    camera = pipeline.create(dai.node.Camera).build()

    det_nn = pipeline.create(dai.node.DetectionNetwork).build(
        camera,
        dai.NNModelDescription("yolov6-nano")
    )
    label_map = det_nn.getClasses()

    q_rgb = det_nn.passthrough.createOutputQueue()
    q_det = det_nn.out.createOutputQueue()

    return pipeline, q_rgb, q_det, label_map


def frame_generator(q_rgb, q_det):
    """
    Generator: yields (cv_frame, detections_list).
    Non-blocking — if either queue has nothing, detections stay stale.
    """
    detections = []
    while True:
        in_rgb = q_rgb.get()
        in_det = q_det.tryGet()   # non-blocking so RGB never stalls

        frame = in_rgb.getCvFrame()

        if in_det is not None:
            detections = in_det.detections

        yield frame, detections