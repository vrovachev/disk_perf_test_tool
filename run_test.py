import os
import sys
import json
import time
import shutil
import pprint
import weakref
import logging
import os.path
import argparse
import traceback
import subprocess
import contextlib


import ssh_runner
import io_scenario
from utils import log_error
from rest_api import add_test
from itest import IOPerfTest, run_test_iter, PgBenchTest
from starts_vms import nova_connect, create_vms_mt, clear_all
from formatters import get_formatter


try:
    import rally_runner
except ImportError:
    rally_runner = None


logger = logging.getLogger("io-perf-tool")
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
logger.addHandler(ch)

log_format = '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
formatter = logging.Formatter(log_format,
                              "%H:%M:%S")
ch.setFormatter(formatter)


tool_type_mapper = {
    "iozone": IOPerfTest,
    "fio": IOPerfTest,
    "pgbench": PgBenchTest,
}


def run_io_test(tool,
                script_args,
                test_runner,
                keep_temp_files=False):

    files_dir = os.path.dirname(io_scenario.__file__)

    path = 'iozone' if 'iozone' == tool else 'fio'
    src_testtool_path = os.path.join(files_dir, path)

    obj_cls = tool_type_mapper[tool]
    obj = obj_cls(script_args,
                  src_testtool_path,
                  None,
                  keep_temp_files,
                  tool
                  )

    return test_runner(obj)


class FileWrapper(object):
    def __init__(self, fd, conn):
        self.fd = fd
        self.channel_wr = weakref.ref(conn)

    def read(self):
        return self.fd.read()

    @property
    def channel(self):
        return self.channel_wr()


class LocalConnection(object):
    def __init__(self):
        self.proc = None

    def exec_command(self, cmd):
        PIPE = subprocess.PIPE
        self.proc = subprocess.Popen(cmd,
                                     shell=True,
                                     stdout=PIPE,
                                     stderr=PIPE,
                                     stdin=PIPE)
        res = (self.proc.stdin,
               FileWrapper(self.proc.stdout, self),
               self.proc.stderr)
        return res

    def recv_exit_status(self):
        return self.proc.wait()

    def open_sftp(self):
        return self

    def close(self):
        pass

    def put(self, localfile, remfile):
        return shutil.copy(localfile, remfile)

    def mkdir(self, remotepath, mode):
        os.mkdir(remotepath)
        os.chmod(remotepath, mode)

    def chmod(self, remotepath, mode):
        os.chmod(remotepath, mode)

    def copytree(self, src, dst):
        shutil.copytree(src, dst)


def get_local_runner(clear_tmp_files=True):
    def closure(obj):
        res = []
        obj.set_result_cb(res.append)
        test_iter = run_test_iter(obj,
                                  LocalConnection())
        next(test_iter)

        with log_error("!Run test"):
            next(test_iter)
        return res

    return closure


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Run disk io performance test")

    parser.add_argument("--tool_type", help="test tool type",
                        choices=['iozone', 'fio', 'pgbench'])

    parser.add_argument("-l", dest='extra_logs',
                        action='store_true', default=False,
                        help="print some extra log info")

    parser.add_argument("-o", "--test-opts", dest='opts',
                        help="cmd line options for test")

    parser.add_argument("-f", "--test-opts-file", dest='opts_file',
                        type=argparse.FileType('r'), default=None,
                        help="file with cmd line options for test")
    #
    # parser.add_argument("-t", "--test-directory", help="directory with test",
    #                     dest="test_directory", required=True)

    parser.add_argument("--tenant", help="tenant name",
                        dest="tenant", required=True, default="admin")

    parser.add_argument("--username", help="username",
                        dest="tenant", required=True, default="admin")

    parser.add_argument("--password", help="password",
                        dest="tenant", required=True, default="admin")

    parser.add_argument("-t", "--test", help="test to run",
                        dest="test_directory", required=True,
                        choices=['io', 'pgbench', 'two_scripts'])

    parser.add_argument("--max-preparation-time", default=300,
                        type=int, dest="max_preparation_time")

    parser.add_argument("-b", "--build-info", default=None,
                        dest="build_name")

    parser.add_argument("-d", "--data-server-url", default=None,
                        dest="data_server_url")

    parser.add_argument("-n", "--lab-name", default=None,
                        dest="lab_name")

    parser.add_argument("--create-vms-opts", default=None,
                        help="Creating vm's before run ssh runner",
                        dest="create_vms_opts")

    parser.add_argument("-k", "--keep", default=False,
                        help="keep temporary files",
                        dest="keep_temp_files", action='store_true')

    choices = ["local", "ssh"]

    if rally_runner is not None:
        choices.append("rally")

    parser.add_argument("--runner", required=True,
                        choices=choices, help="runner type")

    parser.add_argument("--runner-extra-opts", default=None,
                        dest="runner_opts", help="runner extra options")

    return parser.parse_args(argv)


def get_opts(opts_file, test_opts):
    if opts_file is not None and test_opts is not None:
        print "Options --opts-file and --opts can't be " + \
            "provided same time"
        exit(1)

    if opts_file is None and test_opts is None:
        print "Either --opts-file or --opts should " + \
            "be provided"
        exit(1)

    if opts_file is not None:
        opts = []

        opt_lines = opts_file.readlines()
        opt_lines = [i for i in opt_lines if i != "" and not i.startswith("#")]

        for opt_line in opt_lines:
            if opt_line.strip() != "":
                opts.append([opt.strip()
                             for opt in opt_line.strip().split(" ")
                             if opt.strip() != ""])
    else:
        opts = [[opt.strip()
                 for opt in test_opts.split(" ")
                 if opt.strip() != ""]]

    if len(opts) == 0:
        print "Can't found parameters for tests. Check" + \
            "--opts-file or --opts options"
        exit(1)

    return opts


def format_result(res, formatter):
    data = "\n{0}\n".format("=" * 80)
    data += pprint.pformat(res) + "\n"
    data += "{0}\n".format("=" * 80)
    templ = "{0}\n\n====> {1}\n\n{2}\n\n"
    return templ.format(data, formatter(res), "=" * 80)


@contextlib.contextmanager
def start_test_vms(opts):
    create_vms_opts = {}
    for opt in opts.split(","):
        name, val = opt.split("=", 1)
        create_vms_opts[name] = val

    user = create_vms_opts.pop("user")
    key_file = create_vms_opts.pop("key_file")
    aff_group = create_vms_opts.pop("aff_group", None)
    raw_count = create_vms_opts.pop("count", "x1")

    logger.debug("Connection to nova")
    nova = nova_connect()

    if raw_count.startswith("x"):
        logger.debug("Getting amount of compute services")
        count = len(nova.services.list(binary="nova-compute"))
        count *= int(raw_count[1:])
    else:
        count = int(raw_count)

    if aff_group is not None:
        scheduler_hints = {'group': aff_group}
    else:
        scheduler_hints = None

    create_vms_opts['scheduler_hints'] = scheduler_hints

    logger.debug("Will start {0} vms".format(count))

    try:
        ips = [i[0] for i in create_vms_mt(nova, count, **create_vms_opts)]

        uris = ["{0}@{1}::{2}".format(user, ip, key_file) for ip in ips]

        yield uris
    except:
        traceback.print_exc()
    finally:
        logger.debug("Clearing")
        clear_all(nova)


def add_meta_info(result, opts):
    result[0]["username"] = opts.username
    result[0]["password"] = opts.passowrd
    result[0]["tenant_name"] = opts.tenant
    result[0]["lab_url"] = "http://172.16.52.112:8000"
    result[0]["ceph_version"] = "v0.80 Firefly"
    result[0]["lab_name"] = "Perf-1-Env"
    result[0]["iso_md5"] = "bla bla"
    result[0]["build_id"] = "1"
    result[0]["type"] = "GA"
    result[0]["date"] = "Thu Feb 12 19:11:56 2015"


def main(argv):
    opts = parse_args(argv)
    results = []

    if opts.extra_logs:
        logger.setLevel(logging.DEBUG)
        ch.setLevel(logging.DEBUG)

    test_opts = get_opts(opts.opts_file, opts.opts)

    if opts.runner == "rally":
        logger.debug("Use rally runner")
        for script_args in test_opts:

            cmd_line = " ".join(script_args)
            logger.debug("Run test with {0!r} params".format(cmd_line))

            runner = rally_runner.get_rally_runner(
                files_dir=os.path.dirname(io_scenario.__file__),
                rally_extra_opts=opts.runner_opts.split(" "),
                max_preparation_time=opts.max_preparation_time,
                keep_temp_files=opts.keep_temp_files)

            res = run_io_test(opts.tool_type,
                              script_args,
                              runner,
                              opts.keep_temp_files)
            logger.debug(format_result(res, get_formatter(opts.tool_type)))

    elif opts.runner == "local":
        logger.debug("Run on local computer")
        try:
            for script_args in test_opts:
                cmd_line = " ".join(script_args)
                logger.debug("Run test with {0!r} params".format(cmd_line))
                runner = get_local_runner(opts.keep_temp_files)
                res = run_io_test(opts.tool_type,
                                  script_args,
                                  runner,
                                  opts.keep_temp_files,
                                  )
                results.append(res[0])
                logger.debug(format_result(res, get_formatter(opts.tool_type)))
        except:
            traceback.print_exc()
            return 1

    elif opts.runner == "ssh":
        logger.debug("Use ssh runner")

        uris = []

        if opts.create_vms_opts is not None:
            vm_context = start_test_vms(opts.create_vms_opts)
            uris += vm_context.__enter__()
        else:
            vm_context = None

        if opts.runner_opts is not None:
            uris += opts.runner_opts.split(";")

        if len(uris) == 0:
            logger.critical("You need to provide at least" +
                            " vm spawn params or ssh params")
            return 1

        try:
            for script_args in test_opts:
                cmd_line = " ".join(script_args)
                logger.debug("Run test with {0!r} params".format(cmd_line))
                latest_start_time = opts.max_preparation_time + time.time()
                runner = ssh_runner.get_ssh_runner(uris,
                                                   latest_start_time,
                                                   opts.keep_temp_files)
                res = run_io_test(opts.tool_type,
                                  script_args,
                                  runner,
                                  opts.keep_temp_files)
                logger.debug(format_result(res, get_formatter(opts.tool_type)))

        except:
            traceback.print_exc()
            return 1
        finally:
            if vm_context is not None:
                vm_context.__exit__()
                logger.debug("Clearing")

    if opts.data_server_url:
        result = json.loads(get_formatter(opts.tool_type)(results))
        result[0]['name'] = opts.build_name
        add_meta_info(result, opts)
        add_test(opts.build_name, result, opts.data_server_url)

    return 0


# command line parametres
# --tool_type fio  -f scripts/commands.txt -d http://172.16.52.80/ -t io --runner local
if __name__ == '__main__':
    exit(main(sys.argv[1:]))

# {\
#         "username": "admin",\
#         "password": "admin", \
#         "tenant_name": "admin",\
#         "lab_url": "http://172.16.52.112:8000",\
#         "ceph_version": "v0.80 Firefly",\
#         "lab_name": "Perf-1-Env",\
#         "iso_md5": "bla bla"\
#         "build_id": "1",\
#         "randwrite a 256k": [16885, 1869],\
#         "randwrite s 4k": [79, 2],\
#         "read a 64k": [74398, 11618],\
#         "write s 1024k": [7490, 193],\
#         "randwrite a 64k": [14167, 4665],\#
#         "randread a 1024k": [68683, 8604],\
#         "randwrite s 256k": [3277, 146],\
#         "write a 1024k": [24069, 660],\
#         "type": "sometype",\
#         "write a 64k": [24555, 1006],\
#         "write s 64k": [1285, 57],\
#         "write a 256k": [24928, 503],\
#         "write s 256k": [4029, 192],\
#         "randwrite a 1024k": [23980, 1897],\
#         "randread a 64k": [27257, 17268],\
#         "randwrite s 1024k": [8504, 238],\
#         "randread a 256k": [60868, 2637],\
#         "randread a 4k": [3612, 1355],\
#         "read a 1024k": [71122, 9217],\
#         "date": "Thu Feb 12 19:11:56 2015",\
#         "write s 4k": [87, 3],\
#         "read a 4k": [88367, 6471],\
#         "read a 256k": [80904, 8930],\
#         "name": "somedev",\
#         "randwrite s 1k": [20, 0],\
#         "randwrite s 64k": [1029, 34],\
#         "write s 1k": [21, 0],\#
#     }]'