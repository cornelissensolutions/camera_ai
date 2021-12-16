from flask import Flask, render_template, request, abort, send_file
import requests
from requests.auth import HTTPDigestAuth
import os, sys
from datetime import datetime
from PIL import Image, ImageFont, ImageDraw, ImageEnhance
import logging
import syslog
syslog.openlog(sys.argv[0])

app = Flask(__name__, template_folder='templates')

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"

@app.route("/getImage")
def getImage():
    logging.info("app.route(/getImage) -> getImage()")
    url = "http://10.0.66.70/Streaming/channels/1/picture"
    authen = HTTPDigestAuth{'test','T3sterer'}
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    datestamp= datetime.utcnow().strftime("%Y%m%d")
    filename = "{}".format(timestamp)
    current_working_dir = os.getcwd()

    download_Picture(url, authen, current_working_dir, filename)
    predictions = analyze_picture(current_working_dir, datestamp, filename)
    print("end of analyzation")
    # return send_file("analyzed/" + datestamp + "/" +filename + "_analyzed.jpg", mimetype='image/gif')
    return "Image {} analyzed, <br>{} items predicted {}<br>stored ".format(filename, len(predictions), predictions)

@app.route("/analyze", methods = ['POST'])
def analyze():
    data = request.form # a multidict containing POST data
    print(data)
    if request.method == 'POST':
        f = request.form
        print(f)
    return "<p>data received!</p>"


@app.route('/list', defaults={'req_path': ''})
@app.route('/list/<path:req_path>')
def dir_listing(req_path):
    BASE_DIR = os.getcwd()

    # Joining the base and the requested path
    abs_path = os.path.join(BASE_DIR, req_path)

    # Return 404 if path doesn't exist
    if not os.path.exists(abs_path):
        return abort(404)

    # Check if path is a file and serve
    if os.path.isfile(abs_path):
        return send_file(abs_path)

    # Show directory contents
    files = os.listdir(abs_path)
    return render_template("{}/templates/dirtree.html".format(BASE_DIR), files=files)


def analyze_picture(current_working_dir, datestamp, filename):
    logging.info("analyze_picture({} {} {})".format(current_working_dir, datestamp, filename))
    print("analyze picture with params : {} {} {}".format(current_working_dir, datestamp, filename))
    target_folder = "{}/data/analyzed/{}".format(current_working_dir, datestamp)
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)
    input_file = "{}/data/rawData/{}".format(current_working_dir,filename)
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
    print("saving original object")
    safeTarget = "{}/data/analyzed/{}/{}-analyzed.jpg".format(current_working_dir, datestamp, filename)
    print(safeTarget)
    image.save(safeTarget,"JPEG")
    return response["predictions"]

def download_Picture(url, authen, file_location, filename):
    #bug : authen is not working correctly, for now hard coded
    logging.info("download_Picture({} {} {})".format(url, file_location, filename))

    target_folder = "{}/data/rawData/".format(os.getcwd())
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)
    rawPictureData = requests.get(url, auth=HTTPDigestAuth('test','T3sterer'))    
    print("response code : {}".format(rawPictureData.status_code))
    target_file = "{}/data/rawData/{}".format(file_location, filename)
    if rawPictureData.status_code == 200:
        print("valid response code, now saving the image")
        with open(target_file, 'wb') as f:
            f.write(rawPictureData.content)

if __name__ == '__main__':
    app.debug = True
    app.run(host="0.0.0.0", port=80)
  
