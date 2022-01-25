from asyncio import threads
import configparser
from flask import Flask, render_template, request, abort, send_file, redirect, send_from_directory, Response
from itsdangerous import exc
from werkzeug.utils import secure_filename
from requests.auth import HTTPDigestAuth
import os, sys
import os.path
from datetime import datetime, time

import logging, logging.handlers
#import syslog
import threading
from threading import  Timer
import CIPS_Analyzer
import CIPS_Camera

"""
    seperate thread to load camera's from config
"""
class AddCameraFromConfigThread(threading.Thread):
    def __init__(self, configFile):
        threading.Thread.__init__(self)
        self.configFile = configFile

    def run(self):
        logging.debug("run AddCameraFromConfigThread for {}".format(self.configFile))
        config = loadConfigFile(self.configFile)
        #TODO add check if camera is already added 
        loadCamera(config)
    


"""
    seperate thread to do all analysis 
"""
class AnalysisThread(threading.Thread):
    def __init__(self, cameraObject):
        threading.Thread.__init__(self)
        self.camera = cameraObject

    def run(self):
        logging.debug("run AnalysisThread")
        start_time = datetime.utcnow()
        CIPS.run(self.camera)
        Analysis_pool.release()
        Analysis_threads.remove(self)
        end_time = datetime.utcnow()
        logging.debug("Thread duration: {}".format((end_time-start_time).total_seconds()))

    def kill(self):
        print("kill")
        #todo does not kill yet
        Analysis_pool.release()
        Analysis_threads.remove(self)

class AutoAnalysisTimer():
    def __init__(self, timer, target):
        self._should_continue = False
        self.is_running = False       
        self.timer = timer
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
        if not self._should_continue and not self.is_running:
            self._should_continue = True
            self._start_timer()
        else:
            logging.debug("Timer already started or running, please wait if you're restarting.")

    def cancel(self):
        logging.debug("cancel")
        if self.thread is not None:
            self._should_continue = False # Just in case thread is running and cancel fails.
            self.thread.cancel()
        else:
            logging.debug("Timer never started or failed to initialize.")

    def updateTimerFreq(self,newTime):
        logging.debug("updateTimerFreq")
        self.cancel()
        self.timer = newTime
        self.start()

    def status(self):
        logging.debug("status")
        return self._should_continue



root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
fileHandler = logging.FileHandler('camera.log', 'w', 'utf-8')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(threadName)s ::  \t%(message)s')
fileHandler.setFormatter(formatter)
root_logger.addHandler(fileHandler)

threadlock = threading.Lock
Analysis_threads = []
Analysis_pool = threading.BoundedSemaphore(value=10)
current_working_dir = os.getcwd()

CONFIG_FOLDER = '{}/config'.format(current_working_dir)
ALLOWED_EXTENSIONS = {'txt', 'ini'}

app = Flask(__name__, template_folder='templates')
CIPS = CIPS_Analyzer.CIPS()
CAMERAS = []

@app.route('/')
def hello_world():
    return render_template("main.html", threads=len(Analysis_threads), 
                                        cameras = CAMERAS,
                                        timerStatus = autoTimer.status(), 
                                        timerValue=autoTimer.timer, 
                                        debugStatus = CIPS.debugStatus(),
                                        endpointURL = CIPS.ANALYZER.url
                                        )

@app.route('/downloadLog')
def downloadLog():
    try:
        return send_from_directory(os.getcwd(), "camera.log", as_attachment=True)
    except FileNotFoundError:
        abort(404)

@app.route('/viewLog')
def viewLog():
    with open("camera.log", "r") as f:
        content = f.read()
    return Response(content, mimetype='text/plain') 

@app.route('/files', defaults={'req_path': ''})
@app.route('/files/', defaults={'req_path': ''})
@app.route('/files/<path:req_path>')
def dir_listing(req_path):
    logging.debug("dir_listing") 
    BASE_DIR = '{}/data'.format(os.getcwd())

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

@app.route("/updateTimer", methods=["GET", "POST"])
def updateTimer():
    logging.debug("updateTimer") 
    print("update time")
    newTimerValue = request.form.get("newTimerValue")
    autoTimer.updateTimerFreq(int(newTimerValue))
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

@app.route("/updateEndpoint", methods=["POST"])
def updateEndpoint():
    logging.debug("updateEndpoint")
    newEndpoint = request.form.get("newEndPointURL")
    CIPS.updateEndpointURL(newEndpoint)
    return redirect('/')

@app.route("/uploadCameraConfig", methods=["POST"])
def uploadCamera():
    print("upload camera")
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
        file.save(os.path.join(app.config['CONFIG_FOLDER'], "camera", filename))

    return redirect('/')

@app.route("/loadCameraFromConfig")
def loadCameraFromConfig():
    logging.debug("loadCameraFromConfig") 
    #load all ini files in config/camera
    for file in os.listdir(os.path.join(app.config["CONFIG_FOLDER"],"camera")):
        print(file)
        filelocation = os.path.join(app.config["CONFIG_FOLDER"],"camera",file)
        thread = AddCameraFromConfigThread(filelocation)
        thread.start()
    return redirect('/')



"""
    load config file 
"""
def loadConfigFile(filelocation):
    logging.debug("loadConfigFile({})".format(filelocation))
    config = configparser.ConfigParser()
    config.read(filelocation)
    #TODO validate config settings
    return config

"""
    load Camera into camera pool
"""
def loadCamera(config):
    logging.debug("loadCamera")
    #todo add validator of values
    name = config["CAMERA"]["name"]
    ip = config["CAMERA"]["ip"]
    url = config["CAMERA"]["url"]
    username = config["CAMERA"]["username"]
    password = config["CAMERA"]["password"]
    print(username)
    brand = config["CAMERA"]["brand"]
    exclude_objects = config["CAMERA"]["exclude_objects"] 
    if username != "":
        logging.debug("add camera with authentication")
        CAM = CIPS_Camera.CIPS_Camera(name, url, HTTPDigestAuth(username,password), exclude_objects )
    else:
        logging.debug("add camera without authentication")
        CAM = CIPS_Camera.CIPS_Camera(name, url, None, exclude_objects)
    CAMERAS.append(CAM)
    CIPS.get_ImageStream(CAM)

"""
    Shutdown the webserver in a graceful manner
"""
def shutdown_server():
    logging.debug("shutdown_server") 
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()     


"""
    returns if file extension is valid
"""
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

"""
    triggers the analysis thread per camera registered
"""
def getImageStream():
    logging.debug("getImageStream") 
    #START analysis THREAD per loaded camera
    for CAM in CAMERAS:
        Analysis_pool.acquire()
        thread = AnalysisThread(CAM)
        thread.start()
        Analysis_threads.append(thread)

autoTimer = AutoAnalysisTimer(5, getImageStream)

if __name__ == '__main__':
    app.debug = True
    app.config['CONFIG_FOLDER'] = CONFIG_FOLDER
    app.run(host="0.0.0.0", port=80)
  
