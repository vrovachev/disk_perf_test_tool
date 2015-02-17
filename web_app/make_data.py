from flask import json
from sqlalchemy.orm import Session
from web_app import db
from web_app.models import Build, Lab, Result, ParamCombination, Param


def add_io_params(session):
    param1 = Param(name="operation", type='{write, randwrite,read, randread}', descr="type of write operation")
    param2 = Param(name="sync", type='{a, s}', descr="Write mode synchronous/asynchronous")
    param3 = Param(name="block size", type='size_kmg')

    session.add(param1)
    session.add(param2)
    session.add(param3)

    session.commit()


def add_build(session, build_name, build_type, md5):
    build = Build(type=build_type, name=build_name, md5=md5)
    session.add(build)
    session.commit()

    return build.id


def insert_results(session, build_id, lab_id, params_combination_id,
                   time=None, bandwith=0.0, meta=""):
    result = Result(build_id=build_id, lab_id=lab_id, params_combination_id=params_combination_id, time=time,
                    bandwith=bandwith, meta=meta)
    session.add(result)
    session.commit()


def json_to_db(json_data):
    data = json.loads(json_data)
    with db.session() as session:
        for build_data in data:
            build_id = add_build(session,
                                 build_data.pop("build_id"),
                                 build_data.pop("type"),
                                 build_data.pop("iso_md5"))

            for params, (bw, dev) in build_data.items():
                param_id = add_io_params(session, *params.split(" "))
                # insert_results(session, build_id, param_id, bw, dev)


if __name__ == '__main__':
    add_io_params()
    add_build("Some build", "GA", "bla bla")