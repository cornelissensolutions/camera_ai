from flask import Flask, render_template, request, abort, send_file, redirect

from flask.helpers import total_seconds
import requests
from requests.auth import HTTPDigestAuth
import os, sys
import os.path
from datetime import datetime, time
from PIL import Image, ImageFont, ImageDraw, ImageEnhance
import logging
import syslog
import threading

syslog.openlog(sys.argv[0])
threadlock = threading.Lock
Analysis_threads = []
Analysis_pool = threading.BoundedSemaphore(value=10)

app = Flask(__name__, template_folder='templates')

class AnalysisThread(threading.Thread):
    def __init__(self, current_working_dir, datestamp, filename):
        threading.Thread.__init__(self)
        self.current_working_dir = current_working_dir
        self.datestamp = datestamp
        self.filename = filename
        
    def run(self):
        analyze_picture(self.current_working_dir, self.datestamp, self.filename)
        Analysis_pool.release()

@app.route('/')
def hello_world():
    return "<meta http-equiv='refresh' content='30'>  <br> HELLO WORLD <br>{} working Threads <br><a href='/getImage'> Get Image</a><br><a href='files'>data </a>".format(len(Analysis_threads))

@app.route('/files', defaults={'req_path': ''})
@app.route('/files/<path:req_path>')
def dir_listing(req_path):
    print("dir_listing")
    BASE_DIR = '/Users/leoncornelissen/Dev/camera_ai/code/data'

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

@app.route("/getImage")
def getImage():
    logging.info("app.route(/getImage) -> getImage()")
    url = "http://10.0.66.70/Streaming/channels/1/picture"
    authen = HTTPDigestAuth('test','T3sterer')
    timestamp = datetime.utcnow()
    datestamp= datetime.utcnow().strftime("%Y%m%d")
    filename = "{}".format(timestamp.strftime("%Y%m%d-%H%M%S"))
    current_working_dir = os.getcwd()

    download_Picture(url, authen, current_working_dir, filename)
    download_time = datetime.utcnow()
    #START THREAD
    Analysis_pool.acquire()
    thread = AnalysisThread(current_working_dir, datestamp, filename)
    thread.start()
    Analysis_threads.append(thread)
    # predictions = analyze_picture(current_working_dir, datestamp, filename)
    print("end of analyzation")
    end_time = datetime.utcnow()
    download_duration = (download_time - timestamp).total_seconds()
    analysis_dutation = (end_time - download_time).total_seconds()
    total_duration = (end_time - timestamp).total_seconds()
    # return send_file("analyzed/" + datestamp + "/" +filename + "_analyzed.jpg", mimetype='image/gif')
    # return "Image {} analyzed, <br><br> download time: {} s + analysis time: {} s -> {} seconds".format(filename, download_duration, analysis_dutation, total_duration)
    return redirect("http://10.0.0.216", code=302)

@app.route("/analyze", methods = ['POST'])
def analyze():
    data = request.form # a multidict containing POST data
    print(data)
    if request.method == 'POST':
        f = request.form
        print(f)
    return "<p>data received!</p>"



def analyze_picture(current_working_dir, datestamp, filename):
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

def download_Picture(url, authen, file_location, filename):
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

if __name__ == '__main__':
    app.debug = True
    app.run(host="0.0.0.0", port=80)
  
