import requests
import logging

class CIPS_Camera:
    def __init__(self, name, url, auth, exclude=[], include=[]):
        print("init CIPS Camera")
        self.name = name
        self.url = url
        self.auth = auth
        self.excludeList = exclude
        self.includeList = include
    def status(self):
        return requests.get(self.url, auth=self.auth).status_code
    
    def stream(self):
        logging.debug("stream")
        try:
            logging.debug("request {} ".format(self.url))
            response = requests.get(self.url, auth=self.auth)
        except ConnectionError:
            logging.error("Camera connection error")
            print("CONNECTION ERROR")
            return False
        except:
            logging.error("ERROR retrieving data")
            return False
        return response