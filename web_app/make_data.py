from flask import json
from sqlalchemy.orm import Session
from web_app import db
from web_app.models import Build, Lab, Result, ParamCombination, Param


def add_io_params(session):
    param1 = Param(name="operation", type='{"write", "randwrite", "read", "randread"}', descr="type of write operation")
    param2 = Param(name="sync", type='{"a", "s"}', descr="Write mode synchronous/asynchronous")
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


def add_param_comb(session, *params):
    print params
    # result = session.query(ParamCombination).filter().all()
    # print result[0].param_1
    # print result[0].param_2
    # print result[0].param_3

    r = session.query(Param).filter(Param.id == 1).one()
    print r
    result = eval(r.type)

    p = "bla"
    if p not in result:
        result.add(p)

    r.type = str(result)
    session.add(r)
    session.commit()

    print result


def json_to_db(json_data):
    data = json.loads(json_data)
    #
    session = db.session()
    add_io_params(session)
    for build_data in data:
        # build_id = add_build(session,
        #                      build_data.pop("build_id"),
        #                      build_data.pop("type"),
        #                      build_data.pop("iso_md5"))

        for params, [bw, dev] in build_data.items():
            param_comb_id = add_param_comb(session, *params.split(" "))
            # insert_results(session, build_id, param_id, bw, dev)


if __name__ == '__main__':
    # add_build("Some build", "GA", "bla bla")
    json_data = '[{\
        "randwrite a 256k": [16885, 1869],\
        "randwrite s 4k": [79, 2],\
        "read a 64k": [74398, 11618],\
        "write s 1024k": [7490, 193],\
        "randwrite a 64k": [14167, 4665],\
        "build_id": "1",\
        "randread a 1024k": [68683, 8604],\
        "randwrite s 256k": [3277, 146],\
        "write a 1024k": [24069, 660],\
        "type": "GA",\
        "write a 64k": [24555, 1006],\
        "write s 64k": [1285, 57],\
        "write a 256k": [24928, 503],\
        "write s 256k": [4029, 192],\
        "randwrite a 1024k": [23980, 1897],\
        "randread a 64k": [27257, 17268],\
        "randwrite s 1024k": [8504, 238],\
        "randread a 256k": [60868, 2637],\
        "randread a 4k": [3612, 1355],\
        "read a 1024k": [71122, 9217],\
        "date": "Thu Feb 12 19:11:56 2015",\
        "write s 4k": [87, 3],\
        "read a 4k": [88367, 6471],\
        "read a 256k": [80904, 8930],\
        "name": "GA - 6.0 GA",\
        "randwrite s 1k": [20, 0],\
        "randwrite s 64k": [1029, 34],\
        "write s 1k": [21, 0],\
        "iso_md5": "bla bla"\
    }]'

    json_to_db(json_data)
