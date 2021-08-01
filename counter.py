import json
import threading
import time
import uuid
from datetime import datetime
import requests
import cv2
import requests
from PIL.Image import fromarray
import numpy as np
import imutils
import urllib3

frames = []
def getGPS():
    res = requests.get("https://ipinfo.io/")
    data = res.json()
    location = data['loc']
    gps = '{"ip":"' + data['ip'] + '","region":"' + data['region'] + '","location":"' + data['loc'] + '"}'
    # print(gps)
    return gps

class PeopleCounting:
    def __init__(self):
        configJson=open('Config.json')
        self.Config=json.load(configJson)

    def callbackFunc(self,frame, status, time):
        sendThread = SendToServer(frame, status, time,self.Config['CameraID'])
        sendThread.start()

    def gen(self):
        """Video streaming generator function."""
        cap = cv2.VideoCapture('video13.mp4')  # replace video.mp4 by the address of the video you want to play
        avg = None
        xvalues = list()
        motion = list()
        count1 = 0
        count2 = 0

        # Read until video is completed
        while cap.isOpened():
            ret, frame = cap.read()
            flag = True
            if frame is None:
                break
            frame = imutils.resize(frame, width=500)

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)

            if avg is None:
                avg = gray.copy().astype("float")
                continue

            cv2.accumulateWeighted(gray, avg, 0.5)
            frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(avg))
            thresh = cv2.threshold(frameDelta, 2, 255, cv2.THRESH_BINARY)[1]
            thresh = cv2.dilate(thresh, None, iterations=2)
            (cnts, _) = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for c in cnts:
                if cv2.contourArea(c) < 5500:
                    continue
                (x, y, w, h) = cv2.boundingRect(c)
                xvalues.append(x)
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
                frames.append(frame)
                flag = False

            no_x = len(xvalues)

            if no_x > 2:
                difference = xvalues[no_x - 1] - xvalues[no_x - 2]
                if (difference > 0):
                    motion.append(1)
                else:
                    motion.append(0)

            if flag is True:
                if no_x > 5:
                    val, times = self.find_max(motion)
                    if val == 1 and times >= 15:
                        count1 += 1
                        # 0 là vào 1 là ra
                        self.callbackFunc(frames[int(len(frames)/2)], 0, datetime.now())
                        del frames[:]
                    else:
                        count2 += 1
                        self.callbackFunc(frames[int(len(frames)/2)+8], 1, datetime.now())
                        del frames[:]
                xvalues = list()
                motion = list()

            # cv2.line(frame, (250, 0), (250, 480), (0, 255, 0), 2)
            # cv2.line(frame, (300, 0), (300, 480), (0, 255, 0), 2)
            cv2.putText(frame, "In: {}".format(count1), (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            cv2.putText(frame, "Out: {}".format(count2), (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            cv2.imshow("Frame", frame)
            k = cv2.waitKey(24) & 0xff
            if k == 27:
                break
        cap.release()

    def find_max(self,k):
        d = {}
        maximum = ('', 0)  # (occurring element, occurrences)
        for n in k:
            if n in d:
                d[n] += 1
            else:
                d[n] = 1

            # Keep track of maximum on the go
            if d[n] > maximum[1]:
                maximum = (n, d[n])

        return maximum

class SendToServer(threading.Thread):
    def __init__(self, frame, status, time,cameraID):
        self.frame = frame
        self.status = status
        self.time = time
        self.cameraID=cameraID
        threading.Thread.__init__(self)

    def run(self):
        baseurl = "https://localhost:44320/api/"
        img = fromarray(self.frame)
        imageName = "Image" + str(uuid.uuid4())
        img.save("Image/" + imageName + ".png")
        uploadFileUrl = baseurl + "file"
        files = {'media': open('Image/' + imageName + '.png', 'rb')}
        try:
            response = requests.post(uploadFileUrl, files=files, verify=False)
            response = json.loads(response.text)
            pathToUpload = response["data"][0]
            gps=getGPS()
            data = {
                "image": pathToUpload,
                "time": self.time.strftime("%m-%d-%Y %H:%M:%S"),
                "type": self.status,
                "gps":  gps,
                "CameraID": self.cameraID
            }
            print(data)

            response = requests.post(baseurl + "counter", data=data, verify=False)
            print("response : " + response.text)
        except:
            print("Co loi tu server")





if __name__ == '__main__':
   urllib3.disable_warnings()
   peoplecounting=PeopleCounting();
   peoplecounting.gen()