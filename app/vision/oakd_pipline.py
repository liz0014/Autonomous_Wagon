"""

--------------
OAK-D pipline

"""
import depthai as dai
import blobconverter
import numpy as np
import cv2

pipline = dai.Pipeline()



#color camera node
cam_rgb = pipline.createColorCamera() # registers  color camera node inside the pipline 
cam_rgb.setBoardSocket(dai.CameraBoardSocket.CAM_A) # sets the camera socket to CAM_A (the RGB camera)
cam_rgb.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P) # sets the camera resolution to 1080p
cam_rgb.setPreviewSize(640, 352) # this is what yolo,8n expects 

cam_rgb.setInterleaved(False) 
cam_rgb.setColorOrder(dai.ColorCameraProperties.ColorOrder.BGR)

cam_rgb.setFps(30) # 30fps on both RGB and mono cameras keeps them in sync for stereo depth later. 

# MonoCamera Nodes - Left and right

#Left
mono_left = pipline.createMonoCamera()
mono_left.setBoardSocket(dai.CameraBoardSocket.CAM_B)
mono_left.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P) #highest resolution the OAK d lite stereo pair supports
mono_left.setFps(30) # 30fps on both RGB and mono cameras keeps them in sync


#Right
mono_right = pipline.createMonoCamera()
mono_right.setBoardSocket(dai.CameraBoardSocket.CAM_C)
mono_right.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P) #highest resolution the OAK d lite stereo pair supports
mono_right.setFps(30) #30fps on both RGB and mono cameras keeps them in sync





for node in pipline.getAllNodes():
    print(f"ID: {node.id} Type:{type(node).__name__}")


 

