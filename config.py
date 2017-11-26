#!/usr/bin/env python
# -*- coding: utf-8 -*-

HOST = "172.20.10.2"
LOCALHOST = "localhost"
PORT = 5000

IMAGE_HOST = HOST + ":" + str(PORT)

UPLOAD_FOLDER = './files'
TESS_DATA_FOLDER = './tessdata'


DATABASE_PATH = 'sqlite:///restaurantmenu123456.db'


FIREBASE_API_KEY = "AAAAiRo5RTc:APA91bGRhoxm8zEOg9sM2qGj6UwgePxnpHBqojq6KXUBFDvl-XlY9DyKsQnxLthE6zJlMAvVL4Uul-LfNoc93QrSRBEbv1N0PbxdldJ67mkFlNB_kyVmSZ-QH0kZ5nVYoofkMyqszDCu"


def setup_for_remote():
    IMAGE_HOST = 'mmbabaev.pythonanywhere.com'
    UPLOAD_FOLDER = '/home/mmbabaev/MenuRecognition/files'
    TESS_DATA_FOLDER = '/home/mmbabaev/MenuRecognition/tessdata'