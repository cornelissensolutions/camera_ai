import cv2
class CIPS_CAMERA_FEED:
    def __init__(self,camera):
        self.camera = camera
        feedURL = "rtsp://{}:{}@{}".format(self.camera.username, self.camera.password, self.camera.url.replace("http://",""))
        self.feed = cv2.VideoCapture(feedURL)
    
    def getFeed(self):
        ret, frame = self.feed.read()
        return frame
