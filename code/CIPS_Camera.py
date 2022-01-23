import requests
import logging

class CIPS_Camera:
    def __init__(self, name, url, auth, exclude=[]):
        print("init CIPS Camera")
        self.name = name
        self.url = url
        self.auth = auth
        self.excludelist = exclude

    def status(self):
        return requests.get(self.url, auth=self.auth).status_code
    
    def stream(self):
        try:
            response = requests.get(self.url, auth=self.auth)
        except ConnectionError:
            logging.error("Camera connection error")
            print("CONNECTION ERROR")
            return False
        return response