from sqlalchemy.orm import relationship
from web_app import db
from web_app import app


class Build(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    id = db.Column(db.Integer, primary_key=True)
    build = db.Column(db.String(64), index=True, unique=True)
    md5 = db.Column(db.String(64), index=True, unique=True)
    type = db.Column(db.Integer, index=True, unique=True)


class Param(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    type = db.Column(db.String(64))
    descr = db.Column(db.String(4096))


class ParamCombination(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    params = relationship("Param")


class Lab(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    type = db.Column(db.String(4096))


class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    build_id = db.Column(db.Integer)
    lab_id = db.Column(db.Integer)
    time = db.Column(db.DateTime)
    params_combination = relationship("ParamCombination", uselist=False)
    bandwith = db.Column(db.Float)
    meta = db.Column(db.String(4096))
