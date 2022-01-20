from flask import Flask, render_template, request, abort, send_file, redirect

from flask.helpers import total_seconds
import requests
from requests.auth import HTTPDigestAuth
import os, sys
import os.path, glob
from datetime import datetime, time

import logging, logging.handlers
import syslog
import threading
from threading import Thread, Timer, Event
import CIPS_Analyzer

class AnalysisThread(threading.Thread):
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
        print("Thread duration: {}".format((end_time-start_time).total_seconds))

class AutoAnalysisTimer():
    def __init__(self, timer, target):
        self._should_continue = False
        self.is_running = False       
        self.timer = timer
        self.target = target
        self.thread = None

    def _handle_target(self):
        print("_handle_target")
        self.is_running = True
        self.target()
        self.is_running = False
        self._start_timer()

    def _start_timer(self):
        if self._should_continue:
            self.thread = Timer(self.timer, self._handle_target)
            self.thread.start()

    def start(self):
        if not self._should_continue and not self.is_running:
            self._should_continue = True
            self._start_timer()
        else:
            print("Timer already started or running, please wait if you're restarting.")

    def cancel(self):
        if self.thread is not None:
            self._should_continue = False # Just in case thread is running and cancel fails.
            self.thread.cancel()
        else:
            print("Timer never started or failed to initialize.")

    def status(self):
        print("AutoTimer + status")
        print(self._should_continue)
        return self._should_continue


syslog.openlog(sys.argv[0])
threadlock = threading.Lock
Analysis_threads = []
Analysis_pool = threading.BoundedSemaphore(value=10)
current_working_dir = os.getcwd()

app = Flask(__name__, template_folder='templates')
CIPS = CIPS_Analyzer.CIPS()




@app.route('/')
def hello_world():
    return render_template("main.html",threads=len(Analysis_threads), timer = autoTimer.status())

@app.route('/files', defaults={'req_path': ''})
# @app.route('/files/', defaults={'req_path': ''})
@app.route('/files/<path:req_path>')
def dir_listing(req_path):
    print("dir_listing")
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
def webtrigger():
    getImage()
    return redirect("http://127.0.0.1", code=302)

@app.route("/startTimer")
def webStartTimer():
    autoTimer.start()
    return redirect("http://127.0.0.1", code=302) 


@app.route("/stopTimer")
def webStopTimer():
    autoTimer.cancel()
    return redirect("http://127.0.0.1", code=302)

def getImage():
    print("getImage")
    url = "http://10.0.66.70/Streaming/channels/1/picture"
    authen = HTTPDigestAuth('test','T3sterer')
    timestamp = datetime.utcnow()
    datestamp= datetime.utcnow().strftime("%Y%m%d")
    filename = "{}".format(timestamp.strftime("%Y%m%d-%H%M%S"))

    download_Picture(url, authen, current_working_dir, filename)
    download_time = datetime.utcnow()
    #START analysis THREAD
    Analysis_pool.acquire()
    thread = AnalysisThread(current_working_dir, datestamp, filename)
    thread.start()
    Analysis_threads.append(thread)


def download_Picture(url, authen, file_location, filename):
    print("download_Picture")
    #bug : authen is not working correctly, for now hard coded
    logging.info("download_Picture({} {} {})".format(url, file_location, filename))

    target_folder = "{}/data/rawData/".format(os.getcwd())
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)
    rawPictureData = requests.get(url, auth=HTTPDigestAuth('test','T3sterer'))    
    print("response code : {}".format(rawPictureData.status_code))
    target_file = "{}/data/rawData/{}.jpg".format(file_location, filename)
    if rawPictureData.status_code == 200:
        

        print("valid response code, now saving the image")
        with open(target_file, 'wb') as f:
            f.write(rawPictureData.content)



autoTimer = AutoAnalysisTimer(6, getImage)
DEBUG = False
if __name__ == '__main__':
    app.debug = True
    app.run(host="0.0.0.0", port=80)
  
