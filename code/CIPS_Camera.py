import requests
import logging
import cv2
from requests.auth import HTTPDigestAuth
from datetime import datetime

from rx import start
class CIPS_Camera:
    """
    CAMERA class
    """

    def __init__(self, name, url, username, password, brand="random", exclude=[], include=[]):
        logging.info("Init {} for {}".format(__name__, name))    
        self.name = name
        self.url = url
        self.auth = HTTPDigestAuth(username,password)
        self.brand = brand
        self.excludeList = exclude
        self.includeList = include
        self.username = username
        self.password = password
        self.online = True
        self.threshold = 1
        self.latestMovementTime = ""
        self.previousContent = ""
        self.latestContent = ""
        feedURL = "rtsp://{}:{}@{}".format(username, password, self.url.replace("http://",""))
        self.feed = cv2.VideoCapture(feedURL)
        self.latestFrame = ""

    def get_LatestContent(self):
        return self.latestContent

    def get_PreviousContent(self):
        return self.previousContent


    def get_LatestImage(self):
        return self.latestImage

    def get_PreviousImage(self):
        return self.previousImage

    
    def set_PreviousImage(self, img):
        self.previousImage = img

    
    
    def get_Response(self):
        """
        Returns the image stream of a camera
        """
        logging.debug("{}.get_Response()".format(__name__))
        try:
            logging.debug("{}.get_response : request {} ".format(__name__, self.url))
            if self.auth != None:
                response = requests.get(self.url, auth=self.auth)
            else:
                response = requests.get(self.url)
        except ConnectionError:
            logging.error("{}.get_Response : Camera connection error".format(__name__))
            print("CONNECTION ERROR")
            return False
        except:
            logging.error("{} get_Response : ERROR retrieving data".format(__name__))
            return False
        
        logging.debug("{}.get_Response : response status code : {}".format(__name__, response.status_code))
        if response.status_code == 200:
            return response.content
        else:
            return False


    def get_CameraImage(self):
        """
        Get the image stream from a given camera feed. and saves it to latest  
        params: 
        camera      Camera class object
        return  img object
        """
        logging.debug("{}.get_ImageStream()".format(__name__))
        startTime = datetime.now()
        content = self.get_Response()
        if content:
            self.previousContent = self.latestContent
            self.latestContent = content
            try:
                logging.debug("saving latest camera image")
                with open("data/{}.jpg".format(self.name), "wb") as latestImage:
                    latestImage.write(content)
                status = True
            except:
                logging.error("{}.get_CameraImage : FAILED saving latest camera file".format(__name__))
            return self.latestContent
        else:
            logging.error("{}.get_CameraImage : No valid response code")
            status = False
        endTime = datetime.now()
        duration = endTime - startTime
        print(duration)
        return status

    def get_CameraFrame(self):
        startTime = datetime.now()
        self.previousContent = self.latestContent
        
        ret, frame = self.feed.read()
        while type(frame) == None:
            ret, frame = self.feed.read()
        endTime = datetime.now()
        duration = endTime - startTime
        print("get frame from feed duration: {}".format(duration))
        print("type : {}".format(type(frame)))
        self.latestContent = frame
        return frame
