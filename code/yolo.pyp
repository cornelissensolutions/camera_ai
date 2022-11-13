#https://www.imurgence.com/home/blog/how-to-do-object-detection-in-python-using-yolo
#https://ultralytics.com/yolov5 -> vhttps://pytorch.org/get-started/locally/
# Install below libraries using terminal 
# pip install pillow
# pip install opencv-python

# Importing libraries  into the project 
from PIL import Image
import numpy as np
import cv2

# Resizing the image using pillow
#image resize automation
image = Image.open('yolo-test-image1.jpg')
div=image.size[0]/500
resized_image = image.resize((round(image.size[0]/div),round(image.size[1]/div)))
resized_image.save('na.jpg')

#yolov3 algoritham
#importing weights
classes_names=['person','bicycle','car','motorbike','aeroplane','bus','train','truck','boat','traffic light','fire hydrant','stop sign','parking meter','bench','bird','cat','dog','horse','sheep','cow','elephant','bear','zebra','giraffe','backpack','umbrella','handbag','tie','suitcase','frisbee','skis','snowboard','sports ball','kite','baseball bat','baseball glove','skateboard','surfboard','tennis racket','bottle','wine glass','cup','fork','knife','spoon','bowl','banana','apple','sandwich','orange','broccoli','carrot','hot dog','pizza','donut','cake','chair','sofa','pottedplant','bed','diningtable','toilet','tvmonitor','laptop','mouse','remote','keyboard','cell phone','microwave','oven','toaster','sink','refrigerator','book','clock','vase','scissors','teddy bear','hair drier','toothbrush']
model=cv2.dnn.readNet("yolov3.weights","yolov3.cfg")
layer_names = model.getLayerNames()
output_layers=[layer_names[i[0]-1]for i in model.getUnconnectedOutLayers()]

# Here we need to import the image which is previously resized for the neural network.
image=cv2.imread("na.jpg")
height, width, channels = image.shape
# In the call to ,cv2.dnn.blobFromImage(image, scalefactor=1.0, size, mean, swapRB=True),size can be 224,224 for low quality 416,416 for medium quality.