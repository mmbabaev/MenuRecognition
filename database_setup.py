#!/usr/bin/env python
# -*- coding: utf-8 -*-e
# Python file creates the database with 3 tables: User, Restaurant, and MenuItem

from sqlalchemy import Column, ForeignKey, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

from sqlalchemy.orm import sessionmaker

import datetime
import re
import config

from config import DATABASE_PATH
from sqlalchemy import Table

Base = declarative_base()


engine = create_engine(DATABASE_PATH)
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


user_edit_restaurants_association_table = Table('user_edit_restaurants_association', Base.metadata,
    Column('user_id', Integer, ForeignKey('user.id')),
    Column('restaurant_id', Integer, ForeignKey('restaurant.id'))
)


# Creating the User table to track the users creating/adding items to the
# Restaurant and MenuItem tables
class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    last_name = Column(String(250))
    email = Column(String(250), nullable=False)
    password = Column(String(250))

    social_id = Column(String(250))

    filename = Column(String(250))
    image_url = Column(String(250))

    fir_token = Column(String(250))

    @property
    def is_active(self):
        return True

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return unicode(self.id)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'name': self.name,
            'lastName': self.last_name,
            'id': self.id,
            'email': self.email,
            'imageUrl': self.image_url or self.filename
        }

    @staticmethod
    def get_by_id(user_id):
        return session.query(User).filter_by(id=user_id).first()

    @staticmethod
    def get_by_social_id(social_id):
        return session.query(User).filter_by(social_id=social_id).first()


class OcrTemplate(Base):
    __tablename__ = 'ocr_template'

    name = Column(String(80), nullable=False)
    id = Column(Integer, primary_key=True)

    properties = relationship('PropertyOcrTemplate', cascade='delete, delete-orphan')

    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)


    def add_properties(self, properties_dict):
        for property_dict in properties_dict:
            property_template = PropertyOcrTemplate(template_id=self.id)
            property_template.fill_with_dict(property_dict)

            session.add(property_template)
            session.commit()

    @property
    def serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            'properties': [prop.serialize for prop in self.properties]
        }


class PropertyOcrTemplate(Base):
    __tablename__ = 'property_ocr_template'

    name = Column(String(80))
    id = Column(Integer, primary_key=True)
    color = Column(Integer)

    x = Column(Float, nullable=False)
    y = Column(Float, nullable=False)
    width = Column(Float, nullable=False)
    height = Column(Float, nullable=False)

    template_id = Column(Integer, ForeignKey('ocr_template.id'))
    template = relationship(OcrTemplate)

    def fill_with_dict(self, d):
        self.name = d.get("name")
        self.color = d.get('color')

        self.x = d.get('x')
        self.y = d.get('y')
        self.width = d.get('width')
        self.height = d.get('height')

    @property
    def serialize(self):
        return {
            'name': self.name,
            'color': self.color,

            'x': self.x,
            'y': self.y,
            'width': self.width,
            'height': self.height
        }


# Creating the Restaurant table
class Restaurant(Base):
    __tablename__ = 'restaurant'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)

    categories = relationship('Category', cascade='delete, delete-orphan')

    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)

    latitude = Column(Float)
    longitude = Column(Float)

    created_date = Column(DateTime, default=datetime.datetime.utcnow)

    edit_users = relationship("User", secondary=user_edit_restaurants_association_table)

    @staticmethod
    def user_restaurants(user_id):
        result = []
        rests = session.query(Restaurant)
        for rest in rests:
            if rest.user_id == user_id:
                result.append(rest)
                continue

            for edit_user in rest.edit_users:
                if edit_user.id == user_id:
                    result.append(rest)
                    break

        return result

    @staticmethod
    def get_by_id(id):
        return session.query(Restaurant).filter_by(id=id).first()

    # This method is for extracting the list of restaurants in JSON format
    @property
    def serialize(self):
        """Return object data in easily serializeable format"""

        categories = self.categories
        if categories is None:
            categories = []

        if self.latitude is not None and self.longitude is not None:
            location = {
                'longitude': self.longitude,
                'latitude': self.latitude
            }
        else:
            location = None

        return {
            'name': self.name,
            'id': self.id,
            'userId': self.user_id,
            'location': location,
            'categories': [cat.serialize for cat in categories],
            'editUsers': [user.serialize for user in self.edit_users]
        }

    @property
    def full_serialize(self):
        result = self.serialize
        result['categories'] = [cat.serialize for cat in self.categories]
        return result


class Category(Base):
    __tablename__ = 'category'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)

    menuitems = relationship('MenuItem', cascade='delete, delete-orphan')

    restaurant_id = Column(Integer, ForeignKey('restaurant.id'))
    restaurant = relationship(Restaurant)

    template_id = Column(Integer, ForeignKey('ocr_template.id'))
    template = relationship(OcrTemplate)

    @property
    def serialize(self):
        template_ser = None
        if self.template is not None:
            template_ser = self.template.serialize

        return {
            'id': self.id,
            'name': self.name,
            'items': [item.serialize for item in self.menuitems],
            'template': template_ser
        }

    @staticmethod
    def get_by_id(id):
        return session.query(Category).filter_by(id=id).first()


# Creating the MenuItem table
class MenuItem(Base):
    __tablename__ = 'menu_item'

    id = Column(Integer, primary_key=True)
    image_name = Column(String(80))

    category_id = Column(Integer, ForeignKey('category.id'))
    category = relationship(Category)

    properties = Column(String(500))

    @property
    def prop_dict(self):
        return eval(self.properties)

    @property
    def name(self):
        return self.prop_dict.get("name", "")

    @property
    def description(self):
        return self.prop_dict.get("description", "")

    @property
    def price(self):
        s = self.prop_dict.get("price", 0)
        return self.parse_float(s)

    def parse_float(self, s):
        if s == 0:
            return 0
        try:
            result = ''.join(i for i in s if i in "0123456789.")
            return float(result)
        except:
            return 0

    @property
    def imageUrl(self):
        filename = self.image_name
        if filename is None:
            return None
        else:
            filename = filename.replace('.png', '')

        return "http://" + config.IMAGE_HOST + "/images/" + filename



    # This method is for extracting the list of menu items in JSON format
    @property
    def serialize(self):
        return {
            'name': self.name or "",
            'description': self.description or "",
            'id': self.id,
            'price': self.price or 0,

            'properties': self.prop_dict,

            'imageUrl': self.imageUrl
        }

    @staticmethod
    def get_by_id(menu_item_id):
        return session.query(MenuItem).filter_by(id=menu_item_id).first()



# Creating the database file
#engine = create_engine(DATABASE_PATH)
#Base.metadata.create_all(engine)


def init_test_data():
    user1 = User(id=1, name=u"Михаил", last_name=u"Бабаев", email="mmbabaev@gmail.com", password="Qwerty1234")
    session.add(user1)
    session.commit()

    user2 = User(id=2, name=u"Иван", last_name=u"Иванов", email="babay123@yandex.ru", password="Qwerty1234")
    session.add(user2)
    session.commit()

    user3 = User(id=3, name=u"Вупкин", last_name=u"Пупкин", email="test@gmail.com", password="Qwerty1234")
    session.add(user3)
    session.commit()

#temp
    temp1 = OcrTemplate(name="Template1", id=1, user_id=1)
    temp2 = OcrTemplate(name="Template2", id=2, user_id=2)

    session.add(temp1)
    session.add(temp2)
    session.commit()

#temp prop
    prop1 = PropertyOcrTemplate(name="title", id=1, color=0, x=0, y=0,width=60,height=10)
    prop2 = PropertyOcrTemplate(name="description", id=2, color=1, x=0, y=20, width=60, height=10)
    prop3 = PropertyOcrTemplate(name="price", id=3, color=2, x=0, y=40, width=60, height=10)

    prop4 = PropertyOcrTemplate(name="title", id=4, color=0, x=0, y=0, width=60, height=10)
    prop5 = PropertyOcrTemplate(name="image", id=5, color=1, x=0, y=20, width=60, height=10)
    prop6 = PropertyOcrTemplate(name="price", id=6, color=2, x=0, y=40, width=60, height=10)

    prop1.template_id = temp1.id
    prop2.template_id = temp1.id
    prop3.template_id = temp1.id

    prop4.template_id = temp2.id
    prop5.template_id = temp2.id
    prop6.template_id = temp2.id

    session.add(prop1)
    session.add(prop2)
    session.add(prop3)
    session.add(prop4)
    session.add(prop5)
    session.add(prop6)
    session.commit()

    rest1 = Restaurant(id=1, name="Rest1", user_id=1, created_date=datetime.datetime.now())
    rest2 = Restaurant(id=2, name="Rest2", user_id=1, latitude=63, longitude=12, created_date=datetime.datetime.now())
    rest3 = Restaurant(id=3, name="rest3", user_id=2, created_date=datetime.datetime.now())

    rest1.edit_users.append(user2)

    session.add(rest1)
    session.add(rest2)
    session.add(rest3)
    session.commit()

#cat
    cat1 = Category(id=1, name="cat1-1", restaurant_id=1)
    cat2 = Category(id=2, name="cat1-2", restaurant_id=1, template_id=2)
    session.add(cat1)
    session.add(cat2)
    session.commit()

#item
    props1 = str({"name": u"Продукт 1", "description": "product description 1", "price": "123"})
    item1 = MenuItem(id=1, properties=props1, category_id=1)

    props2 = str({"name": u"Продукт 2", "description": "product description 2", "price": "321"})
    item2 = MenuItem(id=2, properties=props2, category_id=1)

    props3 = str({"name": u"Продукт 3", "description": "product description 3", "price": "144.3"})
    item3 = MenuItem(id=3, properties=props3, category_id=1)

    session.add(item1)
    session.add(item2)
    session.add(item3)
    session.commit()


#test template
    temp = OcrTemplate(name="TemplateTest", id=10, user_id=1)

    session.add(temp)
    session.commit()

    # temp prop
    prop1 = PropertyOcrTemplate(name="name", id=10, color=0, x=176.5, y=62.5, width=140.5, height=20.5)
    prop2 = PropertyOcrTemplate(name="description", id=20, color=1, x=176.5, y=84.25, width=151, height=22.5)
    prop3 = PropertyOcrTemplate(name="price", id=30, color=2, x=169, y=105.5, width=39, height=32)

    prop1.template_id = temp.id
    prop2.template_id = temp.id
    prop3.template_id = temp.id

    cat1.template_id = temp.id

    session.add(temp)
    session.add(prop1)
    session.add(prop2)
    session.add(prop3)
    session.commit()

#init_test_data()

try:
    init_test_data()
    print()
except:
    session.rollback()

