from PIL import JpegImagePlugin
import requests
import logging


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
        self.previousImage = JpegImagePlugin.JpegImageFile
        self.online = True
        self.threshold = 1
        

    def getPreviousImage(self):
        return self.previousImage

    def setPrevious(self, img):
        self.previousImage = img
    
    def getResponse(self):
        """
        Returns the image stream of a camera
        """
        logging.debug("{}.getResponse()".format(__name__))
        try:
            logging.debug("request {} ".format(self.url))
            if self.auth != None:
                logging.debug("stream get auth")
                response = requests.get(self.url, auth=self.auth)
            else:
                logging.debug("stream get")
                response = requests.get(self.url)
        except ConnectionError:
            logging.error("Camera connection error")
            print("CONNECTION ERROR")
            return False
        except:
            logging.error("ERROR retrieving data")
            return False
        return response


    def get_ImageStream(self):
        """
        Get the image stream from a given camera feed. and saves it to latest  
        params: 
        camera      Camera class object
        return  img object
        """
        logging.debug("{}.get_ImageStream()".format(__name__))
        
        response = self.getResponse()
        if response:
            logging.debug("response status code : {}".format(response.status_code))
            if response.status_code == 200:
                img = response.content
                try:
                    logging.debug("saving latest camera image")
                    with open("data/{}.jpg".format(self.name), "wb") as latestImage:
                        latestImage.write(img)
                except:
                    logging.error("FAILED saving latest camera file")
                return img
            else:
                logging.error("No valid response code")
                return False
        else:
            logging.error("not retrieving data")
            return False