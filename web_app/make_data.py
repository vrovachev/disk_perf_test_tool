from sqlalchemy.orm import Session
from web_app import db
from web_app.models import Build, Lab, Result, ParamCombination, Param


def add_io_params():
    session = db.session()
    param1 = Param(name="operation", type='{write, randwrite,read, randread}', descr="type of write operation")
    param2 = Param(name="sync", type='{a, s}', descr="Write mode synchronous/asynchronous")
    param3 = Param(name="block size", type='size_kmg')

    session.add(param1)
    session.add(param2)
    session.add(param3)

    session.commit()


def add_build(build_name, build_type, md5):
    session = db.session()
    build = Build(type=build_type, name=build_name, md5=md5)
    session.add(build)
    session.commit()



if __name__ == '__main__':
    add_io_params()
    add_build("Some build", "GA", "bla bla")