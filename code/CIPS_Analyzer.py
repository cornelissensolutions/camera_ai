""""
Image analyzer class
"""
from io import BytesIO
import logging, os, os.path
from PIL import Image, ImageFont, ImageDraw, ImageEnhance
import requests
import CIPS_Camera
import threading
from threading import Thread, Timer, Event
import datetime
threadlock = threading.Lock
Analysis_threads = []
Analysis_pool = threading.BoundedSemaphore(value=10)
current_working_dir = os.getcwd()


class AnalysisThread(threading.Thread): #in progress
    def __init__(self, current_working_dir, datestamp, filename):
        threading.Thread.__init__(self)
        self.current_working_dir = current_working_dir
        self.datestamp = datestamp
        self.filename = filename
        
    def run(self):
        start_time = datetime.utcnow()
        CIPS.analyze_picture(self.current_working_dir, self.datestamp, self.filename)
        Analysis_pool.release()
        Analysis_threads.remove(self)
        end_time = datetime.utcnow()
        print("Thread duration: {}".format((end_time-start_time).total_seconds()))


class CIPS:
    DEBUG = False
    def __init__(self):
        print("init CIPS Analyzer")

    def enableDebug(self):
        self.DEBUG = True

    def disableDebug(self):
        self.DEBUG = False 

    def debugStatus(self):
        return self.DEBUG   

    def analyze(self,cameraObject):       
        print("analyze")


    def get_ImageStream(self, camera, timeStamp):
        filename = "{}_{}".format(camera.name, timeStamp.strftime("%Y%m%d-%H%M%S"))
        target_file_location = "{}/data/rawData/{}.jpg".format(os.getcwd(), filename)
        response = requests.get(camera.url, auth=camera.auth)
        if response.status_code == 200:
            img = response.content
            if self.DEBUG:
                print("valid response code, DEBUG mode is on : now saving the image to RawData")
                with open(target_file_location, 'wb') as f:
                    f.write(response.content)
            return img
        else:
            return False
    
    def _analyse_image_stream(self,camera, img, timeStamp):
        print("_analyse_image_stream")
        parent_filename = "{}_{}-analyzed.jpg".format(timeStamp.strftime("%Y%m%d-%H%M%S"), camera.name)
        target_file_folder = "{}/data/analyzed/{}/".format(os.getcwd(), timeStamp.strftime("%Y%m%d"))

        response = requests.post("http://10.0.66.4:123/v1/vision/detection", files={"image":img}, data={"api_key":""}).json()
        print(response)

        image = Image.open(BytesIO(img)).convert("RGB") 
        i=0
        draw = ImageDraw.Draw(image) #renamed image_org to image
        for item in response["predictions"]:
            label = item["label"]
            y_max = int(item["y_max"])
            y_min = int(item["y_min"])
            x_max = int(item["x_max"])
            x_min = int(item["x_min"])
            confidence = str(int(item["confidence"] * 100))
            if label not in camera.exclude:
                cropped = image.crop((x_min, y_min, x_max, y_max))
                print("saving analyzed object")
                filename = "{}_{}_{}-{}.jpg".format(timeStamp.strftime("%Y%m%d-%H%M%S"),camera.name, label, i)
                cropped.save("{}/{}.jpg".format(target_file_folder, filename))

            draw.rectangle([x_min, y_min, x_max, y_max], fill=None, outline="Black" )
            text = label + " - " + confidence + "%"
            draw.text((x_min+20, y_min+20), text)

            i += 1
            print(item["label"])
        print(response["predictions"])

        if response["predictions"] != []:
            print("only saving image once something is found")
            print("saving original object")
            safeTarget = "{}/{}".format(target_file_folder, parent_filename)
            print(safeTarget)
            image.save(safeTarget,"JPEG")


    def analyze_picture(self, current_working_dir, datestamp, filename):
        logging.info("analyze_picture({} {} {})".format(current_working_dir, datestamp, filename))
        print("analyze picture with params : {} {} {}".format(current_working_dir, datestamp, filename))
        target_folder = "{}/data/analyzed/{}".format(current_working_dir, datestamp)
        if not os.path.exists(target_folder):
            os.makedirs(target_folder)
        input_file = "{}/data/rawData/{}.jpg".format(current_working_dir,filename)
        output_file = "{}/data/analyzed/{}/{}".format(current_working_dir,datestamp, filename)
        try:
            image_data = open(input_file,"rb").read()
            image_org = Image.open(input_file).convert("RGB")    
            image=image_org
        except FileNotFoundError:
            print("[-] ERROR input file not found : {}".format(input_file))
            return "<p> [-] ERROR : input file not found</p>"
        print("send image data to deepstack ")

        response = requests.post("http://10.0.66.4:123/v1/vision/detection", files={"image":image_data}, data={"api_key":""}).json()
        print(response)

        i=0
        draw = ImageDraw.Draw(image_org)
        for item in response["predictions"]:
            label = item["label"]
            y_max = int(item["y_max"])
            y_min = int(item["y_min"])
            x_max = int(item["x_max"])
            x_min = int(item["x_min"])
            confidence = str(int(item["confidence"] * 100))
            
            cropped = image.crop((x_min, y_min, x_max, y_max))
            print("saving analyzed object")
            cropped.save("{}/data/analyzed/{}/{}-{}_{}.jpg".format(current_working_dir, datestamp, filename, i,label))

            draw.rectangle([x_min, y_min, x_max, y_max], fill=None, outline="Black" )
            text = label + " - " + confidence + "%"
            draw.text((x_min+20, y_min+20), text)

            i += 1
            print(item["label"])
        print(response["predictions"])

        if response["predictions"] != []:
            print("only saving image once something is found")
            print("saving original object")
            safeTarget = "{}/data/analyzed/{}/{}-analyzed.jpg".format(current_working_dir, datestamp, filename)
            print(safeTarget)
            image.save(safeTarget,"JPEG")