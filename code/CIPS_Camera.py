import requests

class CIPS_Camera:
    def __init__(self, name, url, auth):
        print("init CIPS Camera")
        self.name = name
        self.url = url
        self.auth = auth
    
    def status(self):
        return requests.get(self.url, auth=self.auth).status_code
    
    def stream(self):
        return requests.get(self.url, auth=self.auth).content