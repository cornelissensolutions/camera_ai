""""
Image analyzer class
"""
import logging, os, os.path
from PIL import Image, ImageFont, ImageDraw, ImageEnhance
import requests

class CIPS:
    def __init__(self):
        print("nit")

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