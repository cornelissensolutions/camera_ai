import requests
import logging



class CIPS_Camera:
    def __init__(self, name, url, auth, brand="random", exclude=[], include=[]):
        logging.info("Init {} for {}".format(__name__, name))
        
        print("init CIPS Camera")
        self.name = name
        self.url = url
        self.auth = auth
        self.brand = brand
        self.excludeList = exclude
        self.includeList = include

    """
        Returns the imaage stream of a camera
    """
    def stream(self):
        logging.debug("stream")
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