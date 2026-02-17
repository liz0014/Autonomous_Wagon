import depthai as dai
import cv2

# Create pipeline
pipeline = dai.Pipeline()

# Create camera node
cam = pipeline.create(dai.node.Camera)

cam.setBoardSocket(dai.CameraBoardSocket.RGB)
cam.setSize(640, 480)

# Create output
xout = pipeline.create(dai.node.XLinkOut)
xout.setStreamName("rgb")

cam.out.link(xout.input)

# Start device
with dai.Device(pipeline) as device:
    print("Device connected")

    q = device.getOutputQueue("rgb", maxSize=4, blocking=False)

    while True:
        frame = q.get().getCvFrame()

        cv2.imshow("OAK-D RGB", frame)

        if cv2.waitKey(1) == ord('q'):
            break

cv2.destroyAllWindows()
