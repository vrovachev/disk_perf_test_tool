from flask import json
from sqlalchemy import sql
from sqlalchemy.orm import Session
from web_app import db
from web_app.models import Build, Lab, Result, ParamCombination, Param


def add_io_params(session):
    param1 = Param(name="operation", type='{"write", "randwrite", "read", "randread"}', descr="type of write operation")
    param2 = Param(name="sync", type='{"a", "s"}', descr="Write mode synchronous/asynchronous")
    param3 = Param(name="block size", type='{"1k", "2k", "4k", "8k", "16k", "32k", "64k", "128k", "256k"}')

    session.add(param1)
    session.add(param2)
    session.add(param3)

    session.commit()


def add_build(session, build_id, build_name, build_type, md5):
    build = Build(type=build_type, build_id=build_id, name=build_name, md5=md5)
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
    params_names = sorted([s for s in dir(ParamCombination) if s.startswith('param_')])
    d = zip(params_names, params)
    where = ""

    for item in d:
        where = sql.and_(where, getattr(ParamCombination, item[0]) == item[1])

    query = session.query(ParamCombination).filter(where)
    rs = session.execute(query).fetchall()


    if len(rs) == 0:
        param_comb = ParamCombination()

        for p in params_names:
            i = int(p.split('_')[1])
            param_comb.__setattr__('param_' + str(i), params[i - 1])

            param = session.query(Param).filter(Param.id == i).one()
            values = eval(param.type)

            if params[i - 1] not in values:
                values.add(params[i - 1])
                param.type = str(values)

        session.add(param_comb)
        session.commit()
        return param_comb.id
    else:
        return rs[0][0]
        session.commit()


def add_lab(lab_name):
    pass


def json_to_db(json_data):
    data = json.loads(json_data)
    session = db.session()
    add_io_params(session)

    for build_data in data:
        build_id = add_build(session,
                             build_data.pop("build_id"),
                             build_data.pop("name"),
                             build_data.pop("type"),
                             build_data.pop("iso_md5"))

        from datetime import datetime
        date =  build_data.pop("date")
        # date = datetime.strftime((date, "%Y-%m-%d %H:%M:%S.%f")
        for params, [bw, dev] in build_data.items():
            param_comb_id = add_param_comb(session, *params.split(" "))
            print param_comb_id
            result = Result(param_combination_id=param_comb_id, bandwith=bw)
            session.add(result)
            session.commit()


def load_data(*params):
    session = db.session()
    params_names = sorted([s for s in dir(ParamCombination) if s.startswith('param_')])
    d = zip(params_names, params)
    where = ""

    for item in d:
        where = sql.and_(where, getattr(ParamCombination, item[0]) == item[1])

    query = session.query(ParamCombination).filter(where)
    rs = session.execute(query).fetchall()

    ids = [r[0] for r in rs]

    results = session.query(Result).filter(Result.param_combination_id.in_(ids))
    rs = session.execute(results).fetchall()

    return [r[5] for r in rs]



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
    # print load_data("write")
