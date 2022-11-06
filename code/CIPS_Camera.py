import requests
import logging


class CIPS_Camera:
    """
    CAMERA class
    """

    def __init__(self,
                 name,
                 url,
                 auth,
                 brand="random",
                 exclude=[],
                 include=[]):
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
        function = "{}.get_Response()".format(__name__)
        logging.debug(function)
        try:
            logging.debug("{} : request {} ".format(function, self.url))
            if self.auth is not None:
                response = requests.get(self.url, auth=self.auth)
            else:
                response = requests.get(self.url)
        except ConnectionError:
            logging.error("{} : Camera connection error".format(function))
            print("CONNECTION ERROR")
            return False
        logging.debug("{} : status code : {}".format(function,
                                                     response.status_code))
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
        function = "{}.get_CameraImage()".format(__name__)
        logging.debug(function)
        content = self.get_Response()
        if content:
            self.previousContent = self.latestContent
            self.latestContent = content
            try:
                logging.debug("saving latest camera image")
                with open("data/{}.jpg".format(self.name), "wb") as lastImage:
                    lastImage.write(content)
                return True
            except OSError:
                logging.error("FAILED saving latest camera file")
            return self.latestContent
        else:
            logging.error("{} : No valid response code".format(function))
            return False
