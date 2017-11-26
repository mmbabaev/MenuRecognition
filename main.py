from project import image_to_string
import pytesseract
from config import TESS_DATA_FOLDER
from PIL import Image

image = Image.open('/Users/babaev/Desktop/menu-recognizer-flask/files/1-151129575169.png')
tessdata_dir_config = '--tessdata-dir "' + TESS_DATA_FOLDER +'"'
print pytesseract.image_to_string(image, "rus", config=tessdata_dir_config)