from PIL import JpegImagePlugin
import requests
import logging
from PIL import Image
from io import BytesIO
class CIPS_Camera:
    """
    CAMERA class
    """

    def __init__(self, name, url, auth, brand="random", exclude=[], include=[]):
        logging.info("Init {} for {}".format(__name__, name))    
        self.name = name
        self.url = url
        self.auth = auth
        self.brand = brand
        self.excludeList = exclude
        self.includeList = include
        self.online = True
        self.threshold = 1
        self.latestMovementTime = ""
        self.previousContent = ""
        self.latestContent = ""
        self.get_CameraImage()
        self.get_CameraImage()        

    def get_LatestContent(self):
        return self.latestContent

    def get_PreviousContent(self):
        return self.previousContent

    def get_LatestBytes(self):
        return self.latestBytes

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
        
        content = self.get_Response()
        if content:
            self.previousContent = self.latestContent
            self.latestContent = content
            try:
                logging.debug("saving latest camera image")
                with open("data/{}.jpg".format(self.name), "wb") as latestImage:
                    latestImage.write(content)
                return True 
            except:
                logging.error("{}.get_CameraImage : FAILED saving latest camera file".format(__name__))
            return self.latestContent
        else:
            logging.error("{}.get_CameraImage : No valid response code")
            return False
