from sqlalchemy import ForeignKey, Table
from sqlalchemy.orm import relationship
from web_app import db
from web_app import app


class Build(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    md5 = db.Column(db.String(64))
    type = db.Column(db.Integer)


class Param(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    type = db.Column(db.String(64))
    descr = db.Column(db.String(4096))


class ParamCombination(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    param_1 = db.Column(db.Integer, ForeignKey('param.id'))
    param_2 = db.Column(db.Integer, ForeignKey('param.id'))
    param_3 = db.Column(db.Integer, ForeignKey('param.id'))


class Lab(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    type = db.Column(db.String(4096))


class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    build_id = db.Column(db.Integer)
    lab_id = db.Column(db.Integer)
    time = db.Column(db.DateTime)
    param_combination_id = db.Column(db.Integer, ForeignKey('param_combination.id'))
    param_combination = relationship("param_combination")
    bandwith = db.Column(db.Float)
    meta = db.Column(db.String(4096))
