#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json

import flask
import pytesseract
from PIL import Image
from flask import Flask, session, send_from_directory
from flask import jsonify
from flask import request
from flask_babel import Babel
from flask_babel import gettext
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
from flask_sqlalchemy import *

import config
import database_setup
from api_error import ApiError
from config import DATABASE_PATH, UPLOAD_FOLDER, TESS_DATA_FOLDER
from database_setup import User, Restaurant, Category, MenuItem, OcrTemplate
from helpers.social_helper import *
from helpers.fir_helper import notify_user

from helpers.send_email import send_mail_files

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_PATH
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = "Kjkszpj1"

session = database_setup.session

babel = Babel(app)

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(user_id)


@app.route('/social_login', methods=['POST'])
def social_login():
    json = request.json

    social_id = json.get('socialId')
    email = json.get('email')

    token = json.get('token')
    platform = json.get('platform')

    fir_token = json.get('firToken')

    registered_user = User.get_by_social_id(social_id)
    if registered_user is None:

        if platform == "FB":
            json = fb_info(social_id, token)
        else:
            json = vk_info(social_id, token)

        if json is None:
            raise ApiError("Произошла ошибка авторизации")

        image_url = json.get('image_url')
        first_name = json.get("first_name")
        last_name = json.get("last_name")
        if email is None or len(email) == 0:
            email = json.get('email')

        print(image_url)

        user = User(social_id=social_id, email=email,
                    name=first_name, last_name=last_name,
                    image_url=image_url, fir_token=fir_token)

        session.add(user)
        session.commit()

        login_user(user)

        return jsonify(user.serialize)

    registered_user.fir_token = fir_token
    login_user(registered_user)

    return jsonify(registered_user.serialize)


@app.route('/login', methods=['POST'])
def login():
    email = request.json.get('email')
    password = request.json.get('password')

    check_login_args(email, password)

    registered_user = session.query(User).filter(User.email == email).first()

    if registered_user is None:
        raise ApiError(gettext("User not registered"))

    if registered_user.password != password:
        raise ApiError(gettext("Invalid email and password combination"))


    flask.flash('Logged in successfully.')

    registered_user.fir_token = request.json.get('firToken')

    login_user(registered_user)

    return jsonify(registered_user.serialize)


@app.route('/logout', methods=['DELETE'])
def logout():
    logout_user()
    return jsonify(success=True)


def check_login_args(email, password):
    if email is None or not email:
        raise ApiError(gettext("Email is required"))

    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        raise ApiError(gettext("Invalid email"))

    if password is None or not password:
        raise ApiError(gettext("Password is required"))

    if password.lower() == password or password.upper() == password or not password.isalnum():
        raise ApiError(gettext("Invalid password"))


def check_register_args(email, password, name):
    check_login_args(email, password)
    if name is None:
        raise ApiError(gettext("Name is required"))


@app.route('/register', methods=['POST'])
def register():

    body = request.json
    email = body.get('email')
    password = body.get('password')
    name = body.get('name')
    last_name = body.get('lastName')
    fir_token = body.get('firToken')

    check_register_args(email, password, name)

    image_file = request.files.get('image')
    filename = None

    if image_file:
        filename = str(time.time()).replace(".", "") + ".jpg"
        image_file.save(os.path.join(UPLOAD_FOLDER, filename))

    user = User(name=name, last_name=last_name, email=email, password=password, filename=filename, fir_token=fir_token)
    session.add(user)
    session.commit()

    login_user(user)

    return jsonify(user.serialize)


@app.route('/restaurant')
@login_required
def restaurants():
   # rests = session.query(Restaurant).order_by(desc(Restaurant.created_date))
    rests = Restaurant.user_restaurants(current_user.id)
    return jsonify([rest.serialize for rest in rests])


@app.route('/restaurant/<int:restaurant_id>', methods=['GET', 'DELETE'])
@login_required
def restaurant(restaurant_id):

    rest = Restaurant.get_by_id(restaurant_id)
    if rest is None:
        raise ApiError("Restaurant is not exist")

    if request.method == "GET":
        return jsonify(rest.full_serialize)
    else:
        session.delete(rest)
        session.commit()
        return jsonify(success=True)


@app.route('/restaurant/new', methods=['POST'])
@login_required
def create_restaurant():
    # create new restaurant
    body = request.json

    rest = Restaurant()

    rest.name = body['name']
    rest.user_id = current_user.id

    location = body.get('location')
    if location is not None:
        rest.latitude = location.get('longitude')
        rest.latitude = location.get('latitude')

    session.add(rest)
    session.commit()

    return jsonify(rest.serialize)


@app.route('/restaurant/<int:restaurant_id>/add_category', methods=['POST'])
@login_required
def add_category(restaurant_id):

    restaurant = Restaurant.get_by_id(restaurant_id)
    if restaurant is None:
        raise ApiError("Restaurant not exist")

    if restaurant.user_id != current_user.id:
        raise ApiError("you have not access to this restaurant")

    category = Category()
    name = request.json.get('name')

    if name is None:
        raise ApiError("Name is required")

    category.name = name

    category.restaurant_id = restaurant_id

    session.add(category)
    session.commit()

    template_dict  = request.json.get('template')

    if template_dict is not None:
        add_template_dict_for_category(template_dict, category)

    return jsonify(category.serialize)


@app.route('/category/<int:category_id>', methods=["DELETE"])
@login_required
def delete_category(category_id):
    category = Category.get_by_id(category_id)
    session.delete(category)
    session.commit()
    return jsonify(success=True)


def add_template_dict_for_category(template_dict, category):
    name = template_dict.get('name')
    if name is None:
        name = category.name

    template = OcrTemplate(name=name, user_id=current_user.id)
    session.add(template)
    session.commit()

    props = template_dict['properties']
    template.add_properties(props)
    session.add(template)
    session.commit()

    category.template_id = template.id
    session.add(category)
    session.commit()


@app.route('/item/<int:item_id>', methods=['PUT', 'DELETE'])
@login_required
def update_item(item_id):
    item = MenuItem.get_by_id(item_id)
    if item is None:
        raise ApiError("item is not exist")

    if request.method == 'DELETE':
        session.delete(item)
        session.commit()
        return jsonify(success=True)

    dict = request.json.get('properties')
    print(dict)
    print(str(dict))
    item.properties = str(dict)

    session.add(item)
    session.commit()

    return jsonify(item.serialize)


"""
@app.route('/category/<int:category_id>/add_position', methods=['POST'])
@login_required
def add_position(category_id):
    category = Category.get_by_id(category_id)
    if category is None:
        raise ApiError("category is not exist")

    #TODO:
    image_name = ""

    menu_item = MenuItem(category_id, request.json, image_name)
    session.add(menu_item)
    session.commit()
"""


@app.route('/category/<int:category_id>/recognize_position', methods=['POST'])
@login_required
def recognize_position(category_id):
    category = Category.get_by_id(category_id)
    if category is None:
        raise ApiError("category is not exist")

    template = json.loads(request.form.get("position"))
    properties = {}

    new_position = MenuItem(category_id=category_id)

    for property_json in template["properties"]:
        key = property_json["name"]
        image_file = request.files[key]

        if key == 'image':
            filename = generate_filename()
            path = os.path.join(UPLOAD_FOLDER, filename)
            image_file.save(path)
            print(filename)
            print(path)
            new_position.image_name = filename
        else:
            property_value = image_to_string(image_file)
            properties[key] = property_value

    new_position.properties = str(properties)

    session.add(category)
    session.add(new_position)
    session.commit()

    return jsonify(new_position.serialize)


def image_to_string(file):
    filename = generate_filename()
    path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(path)

    image = Image.open(path)

    tessdata_dir_config = '--tessdata-dir "' + TESS_DATA_FOLDER + '"'
    return pytesseract.image_to_string(image, "rus", config=tessdata_dir_config)
    #return pytesseract.image_to_string(image, "rus")


"""
    preprocess = "thresh"
    #preprocess = "thresh"

    # load the example image and convert it to grayscale

    image = cv2.imread(path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # check to see if we should apply thresholding to preprocess the
    # image
    if preprocess == "thresh":
        gray = cv2.threshold(gray, 0, 255,
                             cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

    # make a check to see if median blurring should be done to remove
    # noise
    elif preprocess == "blur":
        gray = cv2.medianBlur(gray, 3)

    # write the grayscale image to disk as a temporary file so we can
    # apply OCR to it
    filename = "gray-" + filename + ".png".format(os.getpid())
    path = os.path.join(UPLOAD_FOLDER, filename)
    cv2.imwrite(path, gray)

    image = Image.open(path)
    return pytesseract.image_to_string(image, "rus")
"""



def generate_filename(prefix=""):
    return prefix + str(current_user.id) + "-" + str(time.time()).replace(".", "") + ".png"

#@app.route('/images/upload', methods=['POST'])

@app.route('/images/<string:filename>')
def image(filename):
    uploads = app.config['UPLOAD_FOLDER']

    return send_from_directory(directory=uploads, filename=filename + ".png")



@app.route('/restaurant/<int:rest_id>/available_users')
@login_required
def available_users(rest_id):
    restaurant = Restaurant.get_by_id(rest_id)
    edit_users = restaurant.edit_users
    current_id = current_user.id

    edit_users_ids = []
    for user in edit_users:
        edit_users_ids.append(user.id)

    users = session.query(User).filter(User.id != current_id)
    result = []
    for user in users:
        if user.id not in edit_users_ids:
            result.append(user)

    return jsonify([user.serialize for user in result])


@app.route('/restaurant/<int:rest_id>/edit_user/<int:user_id>', methods=['POST', 'DELETE'])
@login_required
def change_edit_user(rest_id, user_id):
    restaurant = Restaurant.get_by_id(rest_id)

    if restaurant.user_id != current_user.id:
        raise ApiError("Меню " + restaurant.name + " не принадлежит данному пользователю!")

    user = User.get_by_id(user_id)

    add_access = request.method == 'POST'
    if add_access:
        restaurant.edit_users.append(user)
    else:
        restaurant.edit_users.remove(user)

    notify_user(user, current_user, restaurant, add_access)

    session.add(restaurant)
    session.add(user)
    session.commit()

    return jsonify([user.serialize for user in restaurant.edit_users])


@app.route('/send_jsons', methods=['POST'])
@login_required
def send_jsons():
    #send_to = request.json.get('user_id')
    send_to = current_user.email

    filenames = []

    restaurants = Restaurant.user_restaurants(current_user.id)
    for rest in restaurants:
        filename = generate_filename(rest.name)
        filename = filename.replace('.png', '.json')
        path = os.path.join(UPLOAD_FOLDER, filename)
        with open(path, 'w') as outfile:
            data = rest.serialize
            json.dump(data, outfile)
        filenames.append(path)

    send_mail_files(filenames, send_to)

    return jsonify(success=True)


@babel.localeselector
def get_locale():
    return request.accept_languages.best_match({"ru" : "rus"}.keys())


def raise_default_error(status_code):
    raise ApiError("Произошла ошибка при выполнении запроса", status_code)

"""
@app.errorhandler(404)
def handle_not_found():
    raise_default_error(404)


@app.errorhandler(500)
def handle_server_error():
    raise_default_error(500)


@app.errorhandler(405)
def handle_method_error():
    raise_default_error(405)
"""

@app.errorhandler(ApiError)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response




#config.HOST = config.LOCALHOST
host = config.HOST

if __name__ == '__main__':
    app.run(host, port=config.PORT)




