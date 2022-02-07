""""
Image analyzer class
"""
from calendar import c
from io import BytesIO
import logging, os, os.path
import math
from PIL import Image, ImageFont, ImageDraw, ImageEnhance, ImageChops, ImageStat, JpegImagePlugin

import requests
from datetime import datetime, time



class DEEPSTACK:
    def __init__(self, URL=""):
        logging.info("Init {}".format(__name__))
        self.url = URL
    
    """
        Analyze the given image on certain predictions
    """
    def analyze(self, img):
        logging.debug("analyze image")
        response = requests.post(self.url, files={"image":img}, data={"api_key":""}).json()
        return response
    
    """
        Update Deepstack URL to point to another server
    """
    def updateURL(self, url):
        self.url = url


class NOTIFIER:
    def __init__(self,url):
        logging.info("Init {}".format(__name__))
        #https://core.telegram.org/bots/api#sendmessage
        self.url = url

    def message(self, text):
        requests.get(self.url)

class CIPS:
    DEBUG = False
    SAFE_RAW_FILES = False
    SAFE_CROPPED_FILES = False
    current_working_dir = os.getcwd()

    def __init__(self):
        print("init CIPS Analyzer")
        logging.info("Init {}".format(__name__))
        self.init_DeepStack("http://localhost:123/v1/vision/detection")


    def init_DeepStack(self, url):
        self.ANALYZER = DEEPSTACK(url)

    def enableDebug(self):
        logging.debug("enableDebug")
        self.DEBUG = True
        self.SAFE_RAW_FILES = True
        self.SAFE_CROPPED_FILES = True

    def disableDebug(self):
        logging.debug("disableDebug")
        self.DEBUG = False
        self.SAFE_RAW_FILES = False
        self.SAFE_CROPPED_FILES = False

    def debugStatus(self):
        return self.DEBUG
    
    def updateEndpointURL(self, url):
        self.ANALYZER.updateURL(url)
        return self.ANALYZER.url

    """
        Is triggered by thread to gather image feed and performs analasis 
    """
    def run(self,cameraObject):
        logging.debug("CIPS thread run()")
        timestamp = self._current_timeStamp()
        
        stream = cameraObject.get_ImageStream()
        filename = "{}_{}".format(cameraObject.name, timestamp.strftime("%Y%m%d-%H%M%S-%f"))
        target_RAW_file_folder = "{}/data/rawData".format(self.current_working_dir)
        if self.SAFE_RAW_FILES:
            logging.debug("SAFE RAW FILES mode is on, saving camera response to RawData")
            self._safe_image(stream, target_RAW_file_folder, filename)

        streamTime = self._current_timeStamp()
        getStreamDuration = round((streamTime-timestamp).total_seconds(),2)

        if stream != False:
            logging.debug("CIPS thread run got image content, continue to analyze image")
            self._analyse_image_stream(cameraObject, stream, timestamp)
        finishedTime = self._current_timeStamp()

        analyzeDuration = round((finishedTime - streamTime).total_seconds(),2)
        print("Run duration : {} + {}".format(getStreamDuration, analyzeDuration))
        logging.debug("Run duration : {} + {}".format(getStreamDuration, analyzeDuration))


    

    def _analyse_image_stream(self,camera, img, timeStamp):
        """
        _analyse_image_stream
        params:
        camera      camera object to obtain settings and previous image
        img         img feed 
        timeStamp   for saving the files if something interesting is found
        """
        logging.debug("_analyse_image_stream")
        print("_analyse_image_stream")


        #Determine delta compared to previous image
        inputImage = Image.open(BytesIO(img)).convert("RGB")
        previousImage = camera.getPreviousImage()
        diff_ratio = 0
        if previousImage == None:
            print("None")
            previousImage = inputImage
        try:
            diff = ImageChops.difference(inputImage, previousImage)
            stat = ImageStat.Stat(diff)
            diff_ratio = (sum(stat.mean) / (len(stat.mean) * 255)) *100
            print("diff ratio : {}".format(diff_ratio))
        except:
            print("error determine delta")


        camera.setPrevious(inputImage)
        if diff_ratio > camera.threshold:
            parent_filename = "{}_{}-{}-analyzed.jpg".format(timeStamp.strftime("%Y%m%d-%H%M%S"), round(diff_ratio, 3), camera.name)
            target_file_folder = "{}/data/analyzed/{}".format(self.current_working_dir, timeStamp.strftime("%Y%m%d"))

            try:
                response = self.ANALYZER.analyze(img)
            except requests.exceptions.ConnectionError:
                logging.error("Connection error to Analyzer")
                return 
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
                    if label not in camera.excludeList:
                        safeFile = True
                    if self.SAFE_CROPPED_FILES:
                        cropped = image.crop((x_min, y_min, x_max, y_max))
                        print("saving analyzed object : {}".format(label))
                        filename = "{}_{}_{}-{}.jpg".format(timeStamp.strftime("%Y%m%d-%H%M%S"),camera.name, label, i)
                        logging.debug("Saving cropped image {} to {}".format(filename, target_file_folder))
                        #TODO combine in central save class
                        if not os.path.exists(target_file_folder):
                            logging.debug("need to create target folder {}".format(target_file_folder))
                            os.makedirs(target_file_folder)
                        cropped.save("{}/{}".format(target_file_folder, filename))
                        #self._safe_image(cropped, target_file_folder, filename)

                    draw.rectangle([x_min, y_min, x_max, y_max], fill=None, outline="Black" )
                    text = label + " - " + confidence + "%"
                    draw.text((x_min+20, y_min+20), text)
                    i += 1
                if safeFile:
                    print("only saving image once something of interest is found")
                    safeTarget = "{}/{}".format(target_file_folder, parent_filename)
                    #TODO combine in central save class
                    if not os.path.exists(target_file_folder):
                        logging.debug("need to create target folder {}".format(target_file_folder))
                        os.makedirs(target_file_folder)
                    image.save(safeTarget,"JPEG")
            else:
                print(response["error"])


    def _image_entropy(self, img):
        """calculate the entropy of an image"""
        """dont know what it does and why the output numbers are so close"""
        # this could be made more efficient using numpy
        histogram = img.histogram()
        histogram_length = sum(histogram)
        samples_probability = [float(h) / histogram_length for h in histogram]
        return -sum([p * math.log(p, 2) for p in samples_probability if p != 0])


    def _safe_image(self, image, folder, filename):
        """
        param image : image object to be saved
        param folder : destination folder 
        param filename : filename of the file
        """
        logging.debug("{}._safe_image(img, {}, {}".format(__name__, folder, filename))
        if not os.path.exists(folder):
            logging.debug("need to create target folder")
            os.makedirs(folder)
        try:
            with open("{}/{}.jpg".format(folder, filename), "wb") as latest:
                latest.write(image)
            #image.save(folder, filename)
        except:
            logging.error("Failed saving file {} to {}".format(filename, folder))

    """
        _current_timeStamp
    """
    def _current_timeStamp(self):
        #CHANGE FOR TIMEZONE    
        return datetime.utcnow()