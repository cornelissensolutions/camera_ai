from configparser import ConfigParser
from flask import Flask, render_template, request
from flask import abort, send_file, redirect, send_from_directory, Response
from werkzeug.utils import secure_filename
from requests.auth import HTTPDigestAuth
import os
import sys
import os.path
from datetime import datetime
import subprocess
import logging
import logging.handlers

# import syslog
import threading
from threading import Timer
import CIPS_Analyzer
import CIPS_Camera


class AddCameraFromConfigThread(threading.Thread):
    '''seperate thread to load camera's from config file'''
    def __init__(self, configFile):
        print("add camera")
        threading.Thread.__init__(self)
        self.configFile = configFile

    def run(self):
        logging.debug("run AddCameraFromConfigThread for " +
                      "{}".format(self.configFile))
        config = loadConfigFile(self.configFile)
        # TODO add check if camera is already added

        loadCamera(config)


class videoRenderThread():
    '''Create Video in seperate thread to optimize responsiveness'''
    def __init__(self, folder):
        self.folder = folder

    def run(self):
        CIPS.createVideo(self.folder)


class AnalysisThread(threading.Thread):
    '''Start all analysis in seperate thread'''

    def __init__(self, cameraObject):
        threading.Thread.__init__(self)
        self.camera = cameraObject

    def run(self):
        logging.debug("run AnalysisThread")
        start_time = datetime.utcnow()
        CIPS.run(self.camera)
        Analysis_pool.release()
        end_time = datetime.utcnow()
        delta = (end_time-start_time).total_seconds()
        logging.debug("Thread duration: {}".format(delta))
        Analysis_threads.remove(self)
        sys.exit()

    def kill(self):
        print("kill")
        # TODO does not kill yet
        Analysis_pool.release()
        Analysis_threads.remove(self)


class AutoAnalysisTimer():

    def __init__(self, timer, target):
        self._should_continue = False
        self.is_running = False
        self.timer = timer
        self.FPS = int(1/timer)
        self.target = target
        self.thread = None

    def _handle_target(self):
        logging.debug("_handle_target")
        self.is_running = True
        self.target()
        self.is_running = False
        self._start_timer()

    def _start_timer(self):
        logging.debug("_start_timer")
        if self._should_continue:
            self.thread = Timer(self.timer, self._handle_target)
            self.thread.start()

    def start(self):
        logging.debug("start")
        self.FPS = int(1/self.timer)
        if not self._should_continue and not self.is_running:
            self._should_continue = True
            self._start_timer()
        else:
            logging.debug("Timer already started or running," +
                          " please wait if you're restarting.")

    def cancel(self):
        logging.debug("cancel")
        if self.thread is not None:
            self._should_continue = False
            # Just in case thread is running and cancel fails.
            self.thread.cancel()
        else:
            logging.debug("Timer never started or failed to initialize.")

    def updateTimerFreq(self, newTime):
        logging.debug("updateTimerFreq")
        self.cancel()
        self.timer = newTime
        self.start()

    def updateFPS(self, FPS):
        logging.debug("updateFPS")
        self.cancel()
        self.timer = 1/FPS
        self.start()

    def status(self):
        return self._should_continue


root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
logFile = "camera.log"
fileHandler = logging.FileHandler(logFile, 'w', 'utf-8')
form = '%(asctime)s - %(levelname)s - %(threadName)s ::  \t%(message)s'
formatter = logging.Formatter(form)
fileHandler.setFormatter(formatter)
# root_logger.addHandler(fileHandler)
size = 15 * 1024 * 1024
maxFileSizeHandler = logging.handlers.RotatingFileHandler(logFile,
                                                          mode='w',
                                                          maxBytes=size,
                                                          backupCount=3,
                                                          encoding=None,
                                                          delay=0)
maxFileSizeHandler.setFormatter(formatter)
root_logger.addHandler(maxFileSizeHandler)


threadlock = threading.Lock
renderVideoThreadLock = threading.Lock
Analysis_threads = []
Analysis_pool = threading.BoundedSemaphore(value=10)
current_working_dir = os.getcwd()

CONFIG_FOLDER = '{}/config'.format(current_working_dir)
ALLOWED_EXTENSIONS = {'txt', 'ini'}

app = Flask(__name__, template_folder='templates')
print("start")
CIPS = CIPS_Analyzer.CIPS()
CAMERAS = []


@app.route('/')
def hello_world():
    return render_template("main.html",
                           threads=len(Analysis_threads),
                           cameras=CAMERAS,
                           timerStatus=autoTimer.status(),
                           timerValue=autoTimer.timer,
                           FPSValue=autoTimer.FPS,
                           debugStatus=CIPS.debugStatus(),
                           endpointURL=CIPS.ANALYZER.url,
                           endpointStatus=CIPS.ANALYZER.status,
                           hash=HASH)


@app.route('/addCameraPage')
def addCameraPage():
    return render_template("editCamera.html")


@app.route('/cameras')
def cameras():
    return render_template("cameras.html", cameras=CAMERAS)


@app.route('/downloadLog')
def downloadLog():
    try:
        return send_from_directory(os.getcwd(),
                                   "camera.log",
                                   as_attachment=True)
    except FileNotFoundError:
        abort(404)


@app.route("/editCameraPage/<name>")
def editCameraPage(name):
    logging.debug("{}.editCameraPage({})".format(__name__, name))
    for C in CAMERAS:
        if C.name == name:
            CAM = C
    return render_template("editCamera.html", camera=CAM)


@app.route('/files', defaults={'req_path': ''})
@app.route('/files/', defaults={'req_path': ''})
@app.route('/files/<path:req_path>')
def dir_listing(req_path):
    logging.debug("dir_listing")
    BASE_DIR = '{}/data'.format(os.getcwd())

    # remove double //
    req_path.replace("//", "/")
    # Joining the base and the requested path
    abs_path = os.path.join(BASE_DIR, req_path)

    # Return 404 if path doesn't exist
    if not os.path.exists(abs_path):
        return abort(404)

    # Check if path is a file and serve
    if os.path.isfile(abs_path):
        return send_file(abs_path)

    # Show directory contents
    files = sorted(os.listdir(abs_path))
    template = "files.html"
    return render_template(template, files=files)


@app.route('/manuallyCreateCameraFile', methods=["GET", "POST"])
def manuallyCreateCameraFile():
    logging.debug("manuallyCreateCameraFile")
    CameraData = request.form
    createCameraConfig(CameraData)
    return redirect('/cameras')


@app.route("/renderVideo/<date>")
def renderVideo(date):
    folder = "{}/data/analyzed/{}".format(os.getcwd(), date)

    thread = videoRenderThread(folder)
    thread.run()
    return redirect('/')


@app.route("/trigger")
def trigger():
    logging.debug("/trigger")
    getImageStream()
    return redirect('/')


@app.route("/startTimer")
def startTimer():
    logging.debug("/startTimer")

    autoTimer.start()
    return redirect('/')


@app.route("/stopTimer")
def stopTimer():
    logging.debug("/stopTimer")
    autoTimer.cancel()
    return redirect('/')


@app.route('/updateFPS', methods=["GET", "POST"])
def updateFPS():
    logging.debug("updateFPS")
    newFPSValue = float(request.form.get("FPSValue"))
    autoTimer.updateTimerFreq(float(1/newFPSValue))
    return redirect('/')


@app.route("/updateLogLevel", methods=["GET", "POST"])
def updateLogLevel():
    print("web trigger")
    logLevel = request.form.get("logLevel")
    print(logLevel)
    changeLogLevel(logLevel)
    return redirect('/')


@app.route("/updateTimer", methods=["GET", "POST"])
def updateTimer():
    logging.debug("updateTimer")
    print("update time")
    newTimerValue = request.form.get("newTimerValue")
    autoTimer.updateTimerFreq(float(newTimerValue))
    return redirect('/')


@app.route("/stopServer")
def stopServer():
    logging.debug("stopServer")
    shutdown_server()
    return "server shutting down"


@app.route("/enableDebug")
def enableDebug():
    logging.debug("enableDebug")
    CIPS.enableDebug()
    return redirect('/')


@app.route("/disableDebug")
def disableDebug():
    logging.debug("disableDebug")
    CIPS.disableDebug()
    return redirect('/')


@app.route("/killAllThreads")
def killAllThreads():
    logging.debug("killAllThreads")
    for t in Analysis_threads:
        t.kill()
    return redirect('/')


@app.route("/removeCameraFile/<name>", methods=["GET"])
def removeCameraFile(name):
    logging.debug("{}.removeCameraFile({})".format(__name__, name))
    unloadCameraByName(name)
    fileLocation = "{}/config/camera/{}.ini".format(os.getcwd(), name)
    removeFile(fileLocation)
    return redirect('/cameras')


@app.route("/removePictureFile/<file>", methods=["GET"])
def removePictureFile(file):
    logging.debug("{}.removePictureFile({})".format(__name__, file))
    fileLocation = "{}/{}".format(os.getcwd(), file)
    removeFile(fileLocation)
    return redirect('/files')


@app.route("/unloadCamera/<name>", methods=["GET"])
def unloadCamera(name):
    logging.debug("{}.unloadCamera({})".format(__name__, name))
    if request.method == "GET":
        unloadCameraByName(name)
    return redirect('/cameras')


@app.route("/updateEndpoint", methods=["POST"])
def updateEndpoint():
    logging.debug("updateEndpoint")
    newEndpoint = request.form.get("newEndPointURL")
    CIPS.updateEndpointURL(newEndpoint)
    return redirect('/')


@app.route("/uploadCameraConfig", methods=["POST"])
def uploadCameraConfig():
    logging.debug("{}.uploadCameraConfig".format(__name__))
    dataFile = request.files
    print(dataFile)
    if 'file' not in request.files:
        print('No file part')
        return "NO FILE PART <a href='/'> RETURN HOME</a>"
    file = request.files['file']
    # If the user does not select a file, the browser submits an
    # empty file without a filename.
    if file.filename == '':
        print('No selected file')
        return "NO FILE SELECTED <a href='/'> RETURN HOME</a>"
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['CONFIG_FOLDER'],
                               "camera",
                               filename))
    return redirect('/')


@app.route("/loadCameras")
def loadCameras():
    logging.debug("{}.loadCameras".format(__name__))
    loadCamerasFromConfig()
    return redirect('/cameras')


@app.route('/viewLog')
def viewLog():
    logging.debug("{}.viewLog".format(__name__))
    with open("camera.log", "r") as f:
        content = f.read()
    return Response(content, mimetype='text/plain')


def changeLogLevel(logLevel):
    logging.debug("{}.changeLogLevel({})".format(__name__, logLevel))
    if logLevel == "DEBUG":
        logging.info("change log level to DEBUG")
        root_logger.setLevel(logging.DEBUG)
    if logLevel == "INFO":
        logging.info("change log level to INFO")
        root_logger.setLevel(logging.INFO)
    if logLevel == "WARNING":
        logging.info("change log level to WARNING")
        root_logger.setLevel(logging.WARNING)


def loadCamerasFromConfig():
    logging.debug("{}.loadCamerasFromConfig".format(__name__))
    print("loadConfig")
    loadThreads = []

    configdir = os.path.join(app.config["CONFIG_FOLDER"], "camera")
    for file in os.listdir(configdir):
        if file[-4:] == ".ini":
            filelocation = os.path.join(configdir, file)
            thread = AddCameraFromConfigThread(filelocation)
            thread.start()
            loadThreads.append(thread)
    # logging.info("[+] wait for all threads to finish")
    # for t in loadThreads:
    #     t.join()


def loadConfigFile(filelocation):
    """
    load config file
    """
    logging.debug("loadConfigFile({})".format(filelocation))
    config = ConfigParser()
    config.read(filelocation)
    # TODO validate config settings
    return config


"""
CAMERA specific functions
"""


def createCameraConfig(data):
    # check is config file exists, then edit
    # GetAllData
    config = ConfigParser()
    config.add_section("CAMERA")
    config.set('CAMERA', 'name', data.get("cameraName"))
    config.set('CAMERA', 'brand', data.get("cameraBrand"))
    config.set('CAMERA', 'model', data.get("cameraModel"))
    config.set('CAMERA', 'ip', data.get("cameraIP"))
    config.set('CAMERA', 'url', data.get("cameraURL"))
    config.set('CAMERA', 'username', data.get("cameraUsername"))
    config.set('CAMERA', 'password', data.get("cameraPassword"))
    # array does not load correct
    excludeObjects = data.getlist("exclude")
    excludeString = "[" + ", ".join(excludeObjects) + "]"
    config.set('CAMERA', 'exclude_objects', excludeString)
    # validateAllData
    # print(configFileData)
    storeLocation = "{}/config/camera/{}.ini".format(os.getcwd(),
                                                     data.get("cameraName"))

    with open(storeLocation, 'w') as outputFile:
        config.write(outputFile)
    loadCamera(config)
    # load camera


def loadCamera(config):
    """
    load Camera into camera pool
    """
    logging.debug("loadCamera")
    # todo add validator of values
    name = config["CAMERA"]["name"]
    # ip = config["CAMERA"]["ip"]
    url = config["CAMERA"]["url"]
    username = config["CAMERA"]["username"]
    password = config["CAMERA"]["password"]
    brand = config["CAMERA"]["brand"]
    exclude_objects = config["CAMERA"]["exclude_objects"]

    if username != "":
        logging.debug("create camera object with authentication")
        CAM = CIPS_Camera.CIPS_Camera(name,
                                      url,
                                      HTTPDigestAuth(username, password),
                                      brand,
                                      exclude_objects)
    else:
        logging.debug("create camera object without authentication")
        CAM = CIPS_Camera.CIPS_Camera(name, url, None, brand, exclude_objects)
    if not any(c.name == CAM.name for c in CAMERAS):
        logging.debug("adding CAMERA object to array of camera's")
        CAMERAS.append(CAM)
    else:
        logging.debug("CAMERA object was already registered in the past")


def unloadCameraByName(name):
    """
    Unload a specific camera from the array of cameras
    """
    logging.debug("{}.unloadCameraByName({})".format(__name__, name))
    for CAM in CAMERAS:
        if CAM.name == name:
            CAMERAS.remove(CAM)


def shutdown_server():
    """
    Shutdown the webserver in a graceful manner
    """
    logging.debug("shutdown_server")
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()


def allowed_file(filename):
    """
    returns if file extension is valid
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def getImageStream():
    """
    triggers the analysis thread per camera registered
    """
    logging.debug("{}.getImageStream".format(__name__))
    for CAM in CAMERAS:
        Analysis_pool.acquire()
        thread = AnalysisThread(CAM)
        thread.start()
        Analysis_threads.append(thread)


def removeFile(file):
    logging.debug("{}.removeFile({})".format(__name__, file))
    os.remove(file)


autoTimer = AutoAnalysisTimer(0.2, getImageStream)
HASH = ""

if __name__ == '__main__':
    """    HASH = subprocess.check_output(['git',
                                    'log',
                                    '-1',
                                    "--pretty=format:'%ci'"])
    HASH = HASH.decode('ascii').strip()
    """
    print("start main")
    HASH = "dEbug"
    app.debug = True
    app.config['CONFIG_FOLDER'] = CONFIG_FOLDER
    app.run(host="0.0.0.0", port=80)
    loadCamerasFromConfig()
