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
import CIPS_Camera
class AnalysisThread(threading.Thread):
    def __init__(self, cameraObject):
        threading.Thread.__init__(self)
        self.camera = cameraObject

    def run(self):
        start_time = datetime.utcnow()
        CIPS.run(self.camera)
        Analysis_pool.release()
        Analysis_threads.remove(self)
        end_time = datetime.utcnow()
        print("Thread duration: {}".format((end_time-start_time).total_seconds()))

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

    def updateTimerFreq(self,newTime):
        self.cancel()
        self.timer = newTime
        self.start()

    def status(self):
        return self._should_continue


syslog.openlog(sys.argv[0])
threadlock = threading.Lock
Analysis_threads = []
Analysis_pool = threading.BoundedSemaphore(value=10)
current_working_dir = os.getcwd()

app = Flask(__name__, template_folder='templates')
CIPS = CIPS_Analyzer.CIPS()
CAM = CIPS_Camera.CIPS_Camera("achterdeur", "http://10.0.66.70/Streaming/channels/1/picture", HTTPDigestAuth('test','T3sterer'), ["chair", "bench", "potted plant"] )



@app.route('/')
def hello_world():
    return render_template("main.html",threads=len(Analysis_threads), timer = autoTimer.status(), debug = CIPS.debugStatus())

@app.route('/files', defaults={'req_path': ''})
@app.route('/files/', defaults={'req_path': ''})
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
    getImageStream()
    return redirect("http://127.0.0.1", code=302)

@app.route("/startTimer")
def webStartTimer():
    autoTimer.start()
    return redirect("http://127.0.0.1", code=302) 

@app.route("/stopTimer")
def webStopTimer():
    autoTimer.cancel()
    return redirect("http://127.0.0.1", code=302)

# @app.route("updateTimer", method=['POST'])
# def updateTimer():
#     i = request.form["newTimerValue"]
#     print(i)
#     autoTimer.updateTimerFreq(i)
#     return redirect("http://127.0.0.1", code=302)
@app.route("/stopServer")
def stopWebServer():
    shutdown_server()
    return "server shutting down"

@app.route("/enableDebug")
def enableDebug():
    CIPS.enableDebug()
    return redirect("http://127.0.0.1", code=302)
    
@app.route("/disableDebug")
def disableDebug():
    CIPS.disableDebug()
    return redirect("http://127.0.0.1", code=302)




def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()     


def getImageStream():
    print("getImageStream")
    #START analysis THREAD
    Analysis_pool.acquire()
    thread = AnalysisThread(CAM)
    thread.start()
    Analysis_threads.append(thread)





autoTimer = AutoAnalysisTimer(5, getImageStream)

if __name__ == '__main__':
    app.debug = True
    app.run(host="0.0.0.0", port=80)
  
