""""
Image analyzer class
"""
from io import BytesIO
import logging, os, os.path
from PIL import Image, ImageFont, ImageDraw, ImageEnhance
import requests
from datetime import datetime, time

class DEEPSTACK:
    def __init__(self, URL=""):
        self.url = URL
    
    def analyze(self, img):
        response = requests.post(self.url, files={"image":img}, data={"api_key":""}).json()
        return response
    
    def updateURL(self, url):
        self.url = url

class CIPS:
    DEBUG = False
    SAFE_RAW_FILES = False
    current_working_dir = os.getcwd()

    def __init__(self):
        logging.debug("init CIPS Analyzer")
        self.ANALYZER = DEEPSTACK("http://localhost:123/v1/vision/detection")
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
    
    def updateEndpointURL(self, url):
        self.ANALYZER.updateURL(url)
        return self.ANALYZER.url

    def run(self,cameraObject):
        logging.debug("CIPS thread run()")
        timestamp = self._current_timeStamp()
        
        stream = self.get_ImageStream(cameraObject ,timestamp)
        streamTime = self._current_timeStamp()
        getStreamDuration = round((streamTime-timestamp).total_seconds(),2)

        if stream != False:
            self._analyse_image_stream(cameraObject, stream, timestamp)
        finishedTime = self._current_timeStamp()

        analyzeDuration = round((finishedTime - streamTime).total_seconds(),2)
        print("Run duration : {} + {}".format(getStreamDuration, analyzeDuration))
        logging.debug("Run duration : {} + {}".format(getStreamDuration, analyzeDuration))

    def get_ImageStream(self, camera, timeStamp):
        logging.debug("get_ImageStream")
        filename = "{}_{}".format(camera.name, timeStamp.strftime("%Y%m%d-%H%M%S"))
        target_RAW_file_folder = "{}/data/rawData".format(self.current_working_dir)
        target_RAW_file_location = "{}/{}.jpg".format(target_RAW_file_folder, filename)
        if not os.path.exists(target_RAW_file_folder):
            os.makedirs(target_RAW_file_folder)

        response = camera.stream()

        if response.status_code == 200:
            img = response.content
            if self.SAFE_RAW_FILES:
                logging.debug("SAFE RAW FILES mode is on, saving camera response to RawData")
                try:
                    with open(target_RAW_file_location, 'wb') as f:
                        f.write(response.content)
                except:
                    logging.error("FAILED to safe RAW file")
                    return False

            try:
                with open("data/achterdeur.jpg", "wb") as latest:
                    latest.write(response.content)
            except:
                logging.error("FAILED saving latest camera file")
            return img
        else:
            return False
    
    def _analyse_image_stream(self,camera, img, timeStamp):
        logging.debug("_analyse_image_stream")
        print("_analyse_image_stream")
        parent_filename = "{}_{}-analyzed.jpg".format(timeStamp.strftime("%Y%m%d-%H%M%S"), camera.name)
        target_file_folder = "{}/data/analyzed/{}/".format(self.current_working_dir, timeStamp.strftime("%Y%m%d"))

        #TODO: add try except
        response = self.ANALYZER.analyze(img)
        #response = requests.post("http://10.0.66.4:123/v1/vision/detection", files={"image":img}, data={"api_key":""}).json()
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
                    #self._safe_image(cropped, target_file_folder, filename)
                    cropped.save("{}/{}.jpg".format(target_file_folder, filename))
                    self._safe_image(cropped, target_file_folder, filename)

                draw.rectangle([x_min, y_min, x_max, y_max], fill=None, outline="Black" )
                text = label + " - " + confidence + "%"
                draw.text((x_min+20, y_min+20), text)
                i += 1
            if safeFile:
                print("only saving image once something of interest is found")
                safeTarget = "{}/{}".format(target_file_folder, parent_filename)
                image.save(safeTarget,"JPEG")
                self._safe_image(image, target_file_folder, parent_filename)
        else:
            print(response["error"])

    def _safe_image(self, image, folder, filename):
        if not os.path.exists(folder):
            os.makedirs(folder)
        try:
            image.save(folder, filename)
        except:
            logging.error("Failed saving file {} to {}".format(filename, folder))

        return 1
    def _current_timeStamp(self):
        #CHANGE FOR TIMEZONE    
        return datetime.utcnow()