
# A very simple Flask Hello World app for you to get started with...

from flask import Flask

app = Flask(__name__)

import cv2
import numpy as np
from matplotlib import pyplot as plt

def test():
    img_rgb = cv2.imread('/Users/Babaev/Desktop/picture.png')
    img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2GRAY)
    template = cv2.imread('/Users/Babaev/Desktop/template.png', 0)
    w, h = template.shape[::-1]

    res = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)

    # for line in res:
    #    for point in line:
    #        print point

    threshold = 0.45
    loc = np.where(res >= threshold)

    for pt in zip(*loc[::-1]):
        cv2.rectangle(img_rgb, pt, (pt[0] + w, pt[1] + h), (0, 0, 255), 2)

    cv2.imwrite('result1.png', img_rgb)



@app.route('/')
def hello_world():
    test()
    return 'Hello from Flask test!'

