"""`main` is the top level module for your Flask application."""

from __future__ import print_function
from flask_sqlalchemy import SQLAlchemy
from flask import Flask

import pytesseract
from PIL import Image
import urllib, cStringIO
import sys
from flask import jsonify
from flask import request
import os
import time
import json

from sqlalchemy.ext.declarative import DeclarativeMeta

class AlchemyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj.__class__, DeclarativeMeta):
            # an SQLAlchemy class
            fields = {}
            for field in [x for x in dir(obj) if not x.startswith('_') and x != 'metadata']:
                data = obj.__getattribute__(field)
                try:
                    json.dumps(data)  # this will fail on non-encodable values, like other classes
                    fields[field] = data
                except TypeError:
                    fields[field] = None
            # a json-encodable dict
            return fields

        return json.JSONEncoder.default(self, obj)
#from main import app

# Note: We don't need to call run() since our application is embedded within
# the App Engine WSGI application server.

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test1.db'
db = SQLAlchemy(app)


class PropertyType:
    TEXT = 0
    NUMBER = 1
    IMAGE = 2


class Menu(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), nullable=False)

    positions = db.relationship('Position', backref='menu', lazy=True)

    def data(self):
        data = {}
        data["id"] = self.id
        data['title'] = self.title

        positions = []
        for position in self.positions:
            positions.append(position.data())
        data["positions"] = positions

        return data

    def to_json(self):
        return json.dumps(self.data())


    @staticmethod
    def menu_with_id(id):
        list = db.session.query(Menu).filter(Menu.id == id).all()
        if len(list) > 0:
            return list[0]
        else:
            return None


class Position(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), default="")
    description = db.Column(db.String(80), default="")
    price = db.Column(db.String(80), default="")

    menu_id = db.Column(db.Integer, db.ForeignKey('menu.id'),
                          nullable=False)

    properties = db.relationship('PositionProperty', backref='position', lazy=True)

    def data(self):
        data = {}
        data["id"] = self.id
        data["title"] = self.title

        props = []
        for prop in self.properties:
            props.append(prop.data())

        data["properties"] = props

        return data

    def to_json(self):
        return json.dumps(self.data())


class PositionProperty(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(80), nullable=False)
    value = db.Column(db.String(80), default="")
    type = db.Column(db.Integer, default=PropertyType.TEXT)

    position_id = db.Column(db.Integer, db.ForeignKey('position.id'),
                        nullable=False)

    def data(self):
        data = {}
        data["id"] = self.id
        data["key"] = self.key
        data["value"] = self.value
        data["type"] = self.type

        return data

    def to_json(self):
        return json.dumps(self.data())



app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


print("start")

#host = "172.20.10.3"
host = "172.20.10.2"

@app.route('/clear')
def clear_data():
    meta = db.metadata
    for table in reversed(meta.sorted_tables):
        db.session.execute(table.delete())
    db.session.commit()

    setup_db()

    return "success"

#clear_data()
db.create_all()

@app.route('/')
def hello():
    """Return a friendly HTTP greeting."""
    return 'Hello World!'


@app.route('/position', methods=['POST'])
def recognize_position():
    menu_id = request.args.get("menuId")
    menu = Menu.menu_with_id(menu_id)

    template = json.loads(request.form.get("position"))
    properties = []

    for property_json in template["properties"]:
        key = property_json["name"]
        file = request.files[key]
        property_value = image_to_string(file)

        property = PositionProperty(key=key, value=property_value)
        properties.append(property)

    position = Position()
    position.properties = properties

    menu.positions.append(position)

    db.session.add(menu)
    db.session.add(position)
    db.session.commit()

    print(position)
    return position.to_json()


def image_to_string(file):
    filename = str(time.time()).replace(".", "") + ".png"
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(path)
    # return jsonify({'upload':True, 'name' : filename})

    image = Image.open(path)
    return pytesseract.image_to_string(image, "rus")


@app.route('/menu', methods=["GET", "POST"])
def menu():
    if request.method == "GET":
        menu_id = request.args["menuId"]
        menu = Menu.menu_with_id(menu_id)
        #return jsonify({"result": menu.to_json()})
        return menu.to_json()


@app.route('/picture', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files['file']
        if file:
            filename = str(time.time()).replace(".", "") + ".jpg"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return jsonify({'upload':True, 'name' : filename})

    return ""


@app.route('/test')
def test():
    url = "https://realpython.com/images/blog_images/ocr/results2.png"
    file = cStringIO.StringIO(urllib.urlopen(url).read())
    image = Image.open(file)
    s = pytesseract.image_to_string(image)
    return s


@app.route('/test1', methods=['GET', 'POST'])
def test1():
    if request.method == 'POST':
        file = request.files['file']
        if file:
            filename = str(time.time()).replace(".", "") + ".png"
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(path)
            #return jsonify({'upload':True, 'name' : filename})

            image = Image.open(path)
            result = pytesseract.image_to_string(image, "rus")

            print(filename, file=sys.stderr)
            print(result, file=sys.stderr)
            return jsonify({'upload':True, 'recognized': result})

    return jsonify({"error": "error"})


@app.route('/setup')
def setup_db():
    menu = Menu(id=1, title="Test menu")

    db.session.add(menu)
    db.session.commit()

    return "menu was setup"


@app.errorhandler(404)
def page_not_found(e):
    """Return a custom 404 error."""
    return 'Sorry, Nothing at this URL.', 404


@app.errorhandler(500)
def application_error(e):
    """Return a custom 500 error."""
    return 'Sorry, unexpected error: {}'.format(e), 500

app.run(host=host)