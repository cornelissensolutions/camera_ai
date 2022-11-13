"""
Image analyzer class
"""
import logging
import math
import os
import os.path
from datetime import datetime
from io import BytesIO
# import cv2
import requests
from PIL import Image, ImageChops, ImageDraw, ImageStat


class DEEPSTACK:
    timeoutTime = 10
    def __init__(self, url=""):
        logging.info("Init {}".format(__name__))
        self.url = url
        self.status = False
        # self.online = self.getStatus()

    def analyze(self, img):
        """
        Analyze the given image on certain predictions
        param img should be byte array
        """
        logging.debug("{}.analyze(image)".format(__name__))
        try:
            response = requests.post(self.url,
                                     files={"image": img},
                                     data={"api_key": ""},
                                     timeout=self.timeoutTime).json()
        except ConnectionError:
            logging.error("Connection error to Analyzer")
            return False
        return response

    def getStatus(self):
        """
        Get the online / offline status of the endpoint
        """
        logging.debug("{}.getStatus".format(__name__))
        url = ("/".join(self.url.split("/")[0:3]))
        logging.debug("get status from url : {}".format(url))
        try:
            response = requests.get(url,
                                    timeout=self.timeoutTime)
        except ConnectionRefusedError:
            logging.debug("failed connecting")
            self.status = False
            return
        except ConnectionError:
            logging.debug("Connection error")
            self.status = False
            return
        except TimeoutError:
            logging.debug("connection timeout error")
            self.status = False
            return

        logging.debug("return code : {}".format(response.status_code))
        if response.status_code == 200:
            self.status = True
        else:
            self.status = False


    def update_url(self, url):
        """
        Update Deepstack URL to point to another server
        """
        self.url = url
        self.getStatus()


class NOTIFIER:
    """
    FGET NOTIFICATIONS
    """
    def __init__(self, url):
        logging.info("Init {}".format(__name__))
        # https://core.telegram.org/bots/api#sendmessage
        self.url = url

    def message(self, text):
        requests.get(self.url)


class CIPS:
    DEBUG = False
    SAFE_RAW_FILES = False
    SAFE_CROPPED_FILES = False
    cwd = os.getcwd()

    def __init__(self):
        print("init CIPS Analyzer")
        logging.info("Init {}".format(__name__))
        self.init_DeepStack("http://visiondetection:123/v1/vision/detection")
        print("loaded deepstack endpoint")
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
        print(url)
        self.ANALYZER.update_url(url)
        return self.ANALYZER.url

    """
        Is triggered by thread to gather image feed and performs analasis
    """
    def run(self, cameraObject):
        logging.debug("CIPS thread run()")
        timestamp = self._current_timeStamp()

        imageSucceed = cameraObject.get_CameraImage()
        filename = "{}_{}".format(cameraObject.name,
                                  timestamp.strftime("%Y%m%d-%H%M%S-%f"))

        target_RAW_file_folder = "{}/data/rawData".format(self.cwd)
        if self.SAFE_RAW_FILES:
            logging.debug("saving camera response to RawData")
            self._safe_image(cameraObject.get_LatestContent(),
                             target_RAW_file_folder,
                             filename)

        streamTime = self._current_timeStamp()
        getStreamDuration = round((streamTime-timestamp).total_seconds(), 2)

        if imageSucceed:
            logging.debug("got image content, continue to determine delta")
            ratio = self._determine_image_ratio(cameraObject)
            if ratio > cameraObject.threshold:
                logging.debug("movement detected, go to determine object")
                self._analyse_image(cameraObject, timestamp)
        finishedTime = self._current_timeStamp()

        analyzeDuration = round((finishedTime - streamTime).total_seconds(), 2)
        print("Run duration : {} + {}".format(getStreamDuration,
                                              analyzeDuration))
        logging.debug("Run duration : {} + {}".format(getStreamDuration,
                                                      analyzeDuration))

    def _determine_image_ratio(self, camera):
        """
        camera object to collect previous and current image
        """
        # Determine delta compared to previous image
        # print(camera.latestImage)
        camLatestBytes = BytesIO(camera.get_LatestContent())
        inputImage = Image.open(camLatestBytes).convert("RGB")
        camPreviousBytes = BytesIO(camera.get_PreviousContent())
        previousImage = Image.open(camPreviousBytes).convert("RGB")
        diff_ratio = 0
        if previousImage is None:
            print("None")
            previousImage = inputImage

        diff = ImageChops.difference(inputImage, previousImage)
        stat = ImageStat.Stat(diff)
        diff_ratio = (sum(stat.mean) / (len(stat.mean) * 255)) * 100
        print("diff ratio : {}".format(diff_ratio))
        return diff_ratio

    def _analyse_image(self, camera, timeStamp):
        """
        _analyse_image
        params:
        camera      camera object to obtain settings and previous image
        timeStamp   for saving the files if something interesting is found
        """
        logging.debug("{}._analyse_image({},{}".format(__name__,
                                                       camera.name,
                                                       timeStamp))
        print("_analyse_image")
        foldername = timeStamp.strftime("%Y%m%d")
        fileDateName = timeStamp.strftime("%Y%m%d-%H%M%S")
        target_file_folder = "{}/data/analyzed/{}".format(self.cwd,
                                                          foldername)
        parent_filename = "{}_{}-analyzed.jpg".format(fileDateName,
                                                      camera.name)

        inputBytes = camera.get_LatestContent()
        response = self.ANALYZER.analyze(inputBytes)  # should be input bytes
        logging.debug("DEEPSTACK status : {}".format(response["success"]))
        if response:
            logging.debug("responses : {}".format(response["predictions"]))
            image = Image.open(BytesIO(inputBytes)).convert("RGB")
            safeFile = False
            i = 0
            draw = ImageDraw.Draw(image)  # renamed image_org to image
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
                    timeName = timeStamp.strftime("%Y%m%d-%H%M%S")
                    print("saving analyzed object : {}".format(label))
                    filename = "{}_{}_{}-{}.jpg".format(timeName,
                                                        camera.name,
                                                        label,
                                                        i)
                    logging.debug("Saving cropped image {}".format(filename) +
                                  " to {}".format(target_file_folder))
                    if not os.path.exists(target_file_folder):
                        logging.debug("need to create target folder")
                        os.makedirs(target_file_folder)
                    cropped.save("{}/{}".format(target_file_folder, filename))

                draw.rectangle([x_min, y_min, x_max, y_max],
                               fill=None,
                               outline="green",
                               width=2)
                text = label + " - " + confidence + "%"
                draw.text((x_min+20, y_min+20), text)
                i += 1
            if safeFile:
                print("only saving image once something of interest is found")
                safeTarget = "{}/{}".format(target_file_folder,
                                            parent_filename)
                if not os.path.exists(target_file_folder):
                    logging.debug("need to create target folder")
                    os.makedirs(target_file_folder)
                image.save(safeTarget, "JPEG")
        else:
            print(response["error"])

    def createVideo(self, folder):
        """
        Create an video file from files in a folder
        """
        logging.debug("{}.createVideo()".format(__name__))
        img_array = []
        folderContent = sorted(os.listdir(folder))
        # for filename in folderContent:
        #     if filename.endswith(".jpg"):
        #         img = cv2.imread("{}/{}".format(folder, filename))
        #         height, width, layers = img.shape
        #         size = (width, height)
        #         img_array.append(img)

        # fps = 2
        # fourcc = cv2.VideoWriter_fourcc(*'XVID')
        # out = cv2.VideoWriter('{}/output.avi'.format(folder),
        #                       fourcc,
        #                       fps,
        #                       size)
        # for i in range(len(img_array)):
        #     out.write(img_array[i])
        # out.release()
        logging.info("[+] done rendering video for folder {}".format(folder))

    def _image_entropy(self, img):
        """calculate the entropy of an image"""
        """dont know what it does and why the output numbers are so close"""
        # this could be made more efficient using numpy
        histogram = img.histogram()
        histogram_length = sum(histogram)
        samples_probability = [float(h) / histogram_length for h in histogram]
        formula = [p * math.log(p, 2) for p in samples_probability if p != 0]
        return -sum(formula)

    def _safe_image(self, image, folder, filename):
        """
        param image : image object to be saved
        param folder : destination folder
        param filename : filename of the file
        """
        logging.debug("{}._safe_image(img, {}, {}".format(__name__,
                                                          folder,
                                                          filename))
        if not os.path.exists(folder):
            os.makedirs(folder)
        try:
            with open("{}/{}.jpg".format(folder, filename), "wb") as latest:
                latest.write(image)
        except OSError:
            logging.error("Failed saving file" +
                          "{} to {}".format(filename,
                                            folder))

    """
        _current_timeStamp
    """
    def _current_timeStamp(self):
        local_now = datetime.now()
        return local_now
