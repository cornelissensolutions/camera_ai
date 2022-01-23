""""
Image analyzer class
"""
from io import BytesIO
import logging, os, os.path
from PIL import Image, ImageFont, ImageDraw, ImageEnhance
import requests
from datetime import datetime, time

class CIPS:
    DEBUG = False
    SAFE_RAW_FILES = False

    current_working_dir = os.getcwd()
    def __init__(self):
        logging.debug("init CIPS Analyzer") 
        print("init CIPS Analyzer")

    def enableDebug(self):
        logging.debug("enableDebug") 
        self.DEBUG = True
        self.SAFE_RAW_FILES = True

    def disableDebug(self):
        logging.debug("disableDebug") 
        self.DEBUG = False 
        self.SAFE_RAW_FILES = False

    def debugStatus(self):
        logging.debug("debugStatus") 
        return self.DEBUG   

    def run(self,cameraObject):    
        logging.debug("CIPS thread run()")   
        timestamp = self._current_timeStamp()
        
        stream = self.get_ImageStream(cameraObject ,timestamp)
        streamTime = self._current_timeStamp()
        getStreamDuration = round((streamTime-timestamp).total_seconds(),2)

        self._analyse_image_stream(cameraObject, stream, timestamp)
        finishedTime = self._current_timeStamp()

        analyzeDuration = round((finishedTime - streamTime).total_seconds(),2)
        print("Run duration : {} + {}".format(getStreamDuration, analyzeDuration))
        logging.debug("Run duration : {} + {}".format(getStreamDuration, analyzeDuration))

    def get_ImageStream(self, camera, timeStamp):
        logging.debug("get_ImageStream")  
        filename = "{}_{}".format(camera.name, timeStamp.strftime("%Y%m%d-%H%M%S"))
        target_file_location = "{}/data/rawData/{}.jpg".format(self.current_working_dir, filename)
        try:
            response = requests.get(camera.url, auth=camera.auth)
        except ConnectionError:
            print("CONNECTION ERROR")
            return False
        if response.status_code == 200:
            img = response.content
            if self.SAFE_RAW_FILES:
                print("valid response code, DEBUG mode is on : now saving the image to RawData")
                with open(target_file_location, 'wb') as f:
                    f.write(response.content)
            return img
        else:
            return False
    
    def _analyse_image_stream(self,camera, img, timeStamp):
        logging.debug("_analyse_image_stream") 
        print("_analyse_image_stream")
        parent_filename = "{}_{}-analyzed.jpg".format(timeStamp.strftime("%Y%m%d-%H%M%S"), camera.name)
        target_file_folder = "{}/data/analyzed/{}/".format(self.current_working_dir, timeStamp.strftime("%Y%m%d"))

        response = requests.post("http://10.0.66.4:123/v1/vision/detection", files={"image":img}, data={"api_key":""}).json()
        logging.debug("DEEPSTACK status : {}".format(response["success"]))
        if response["success"]:
            logging.debug("DEEPSTACK responses : {}".format(response["predictions"]))
            image = Image.open(BytesIO(img)).convert("RGB") 
            safeFile = False
            i=0
            draw = ImageDraw.Draw(image) #renamed image_org to image
            for item in response["predictions"]:
                label = item["label"]
                y_max = int(item["y_max"])
                y_min = int(item["y_min"])
                x_max = int(item["x_max"])
                x_min = int(item["x_min"])
                confidence = str(int(item["confidence"] * 100))
                if label not in camera.excludelist:
                    safeFile = True
                    cropped = image.crop((x_min, y_min, x_max, y_max))
                    print("saving analyzed object")
                    filename = "{}_{}_{}-{}.jpg".format(timeStamp.strftime("%Y%m%d-%H%M%S"),camera.name, label, i)
                    cropped.save("{}/{}.jpg".format(target_file_folder, filename))

                draw.rectangle([x_min, y_min, x_max, y_max], fill=None, outline="Black" )
                text = label + " - " + confidence + "%"
                draw.text((x_min+20, y_min+20), text)
                i += 1


            if safeFile:
                print("only saving image once something of interest is found")
                safeTarget = "{}/{}".format(target_file_folder, parent_filename)
                image.save(safeTarget,"JPEG")
        else:
            print(response["error"])
    
    def _current_timeStamp(self):
        #CHANGE FOR TIMEZONE    
        return datetime.utcnow()