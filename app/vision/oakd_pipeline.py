"""

--------------
OAK-D pipeline

"""
import depthai as dai
import blobconverter
import numpy as np
import cv2
import os

os.makedirs("frames", exist_ok=True)
device = dai.Device()

with dai.Pipeline(device) as pipeline:

    # RGB Camera
    # CAM_A is the centre RGB lens on the OAK-D-LITE
    # requestOutput asks the VPU to convert and resize the frame before
    # sending it to the host — so getCvFrame() returns clean BGR data
    cam_rgb = pipeline.create(dai.node.Camera).build(dai.CameraBoardSocket.CAM_A) 
    cam_out = cam_rgb.requestOutput(
        (640, 352),
        type=dai.ImgFrame.Type.BGR888p, # BGR format — matches what OpenCV expects 
        fps=20) 
    cam_rgb.setNumFramesPools(2, 2, 2, )  # ← reduce frame pool
    queue_rgb = cam_out.createOutputQueue()

    # Left Mono Camera
    # CAM_B is the left stereo lens
    # GRAY8 = 8-bit grayscale — mono cameras don't output color
    # 640x400 is the max resolution the OAK-D-LITE stereo pair supports
    mono_left = pipeline.create(dai.node.Camera).build(dai.CameraBoardSocket.CAM_B)
    left_out = mono_left.requestOutput(
        (320, 200), 
        type=dai.ImgFrame.Type.GRAY8, 
        fps=20)
    mono_left.setNumFramesPools(2, 2, 2, )  # ← reduce frame pool

    # Right Mono Camera
    mono_right = pipeline.create(dai.node.Camera).build(dai.CameraBoardSocket.CAM_C)
    right_out = mono_right.requestOutput(
        (320, 200), 
        type=dai.ImgFrame.Type.GRAY8, 
        fps=20)
    mono_right.setNumFramesPools(2, 2, 2,)

    # StereoDepth
    # in v3 StereoDepth.build() takes left and right outputs directly
    stereo = pipeline.create(dai.node.StereoDepth).build(
        left=left_out,
        right=right_out,
        presetMode=dai.node.StereoDepth.PresetMode.FAST_DENSITY,
    )
    stereo.setLeftRightCheck(True)
    stereo.setSubpixel(False)  # depth values as whole numbers in mm
    stereo.setDepthAlign(dai.CameraBoardSocket.CAM_A)# aligns depth to RGB frame
    stereo.setOutputSize(320, 200) # width must be a multiple of 16
    queue_depth = stereo.depth.createOutputQueue()

    #IMU
    imu = pipeline.create(dai.node.IMU) #reads accelerometer and gyroscope from the device
    imu.enableIMUSensor([
        dai.IMUSensor.ACCELEROMETER_RAW,  # linear movement (forward, back, up, down)
        dai.IMUSensor.GYROSCOPE_RAW,      # rotation (tilt, spin)
    ], 100)                               # 100 readings per second
    imu.setBatchReportThreshold(1)        # send data as soon as 1 packet is ready
    imu.setMaxBatchReports(10)            # never buffer more than 10 packets
    queue_imu = imu.out.createOutputQueue()
    
    # ── YOLOv8n Detection Network ─────────────────────────────────────────────
    # download YOLOv8n blob — converts and caches it locally
    blob_path = blobconverter.from_zoo(
        name="yolov8n_coco_640x352",
        zoo_type="depthai",
        shaves=6,                    # VPU cores allocated to the NN
    )

    nn = pipeline.create(dai.node.DetectionNetwork)
    nn.setBlobPath(blob_path)        # load the blob directly
    nn.setConfidenceThreshold(0.3)   # ignore detections below 30% confidence
    nn.setNumInferenceThreads(1)     # 1 threads on VPU for speed
    nn.input.setBlocking(False)      # don't freeze pipeline waiting for NN
    nn.input.setMaxSize(1)         # only keep latest frame

    # link RGB camera to NN — preview size must match blob input (640x352)
    cam_out.link(nn.input)
    queue_nn = nn.out.createOutputQueue()

    pipeline.start()
    frame_count = 0
    while pipeline.isRunning() and frame_count < 10:

        # get RGB frame — keep trying until we get one
        rgb_in = queue_rgb.tryGet()
        if rgb_in is None:
            continue                 # no frame yet, try again

        rgb_frame = rgb_in.getCvFrame()

        # get depth frame
        depth_in = queue_depth.tryGet()
        if depth_in is not None:
            depth_frame = depth_in.getFrame()

        # get detections
        nn_in = queue_nn.tryGet()
        if nn_in is not None:
            for det in nn_in.detections:
                h, w = rgb_frame.shape[:2]
                x1 = int(det.xmin * w)
                y1 = int(det.ymin * h)
                x2 = int(det.xmax * w)
                y2 = int(det.ymax * h)
                cv2.rectangle(rgb_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(rgb_frame, f"{det.label} {det.confidence:.0%}",
                            (x1, y1 - 6),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.5, (0, 255, 0), 1)

        # get IMU data
        imu_in = queue_imu.tryGet()
        if imu_in is not None:
            for packet in imu_in.packets:
                accel = packet.acceleroMeter
                gyro  = packet.gyroscope
                print(f"  accel: x={accel.x:.2f} y={accel.y:.2f} z={accel.z:.2f}")
                print(f"  gyro:  x={gyro.x:.2f}  y={gyro.y:.2f}  z={gyro.z:.2f}")

        # save frame
        filename = f"frames/frame_{frame_count:04d}.jpg"
        cv2.imwrite(filename, rgb_frame)
        print(f"Saved {filename}")
        frame_count += 1

print("Done — check frames/")
    