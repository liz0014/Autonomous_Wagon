import depthai as dai

def start_yolo_pipeline(model_name="yolov6-nano"):
    """
    Starts Luxonis v3 pipeline (your current working pattern).
    Returns: (pipeline, q_rgb, q_det, label_map)
    """
    pipeline = dai.Pipeline()

    camera = pipeline.create(dai.node.Camera).build()

    det_nn = pipeline.create(dai.node.DetectionNetwork).build(
        camera,
        dai.NNModelDescription(model_name)
    )
    label_map = det_nn.getClasses()

    q_rgb = det_nn.passthrough.createOutputQueue()
    q_det = det_nn.out.createOutputQueue()

    pipeline.start()
    return pipeline, q_rgb, q_det, label_map