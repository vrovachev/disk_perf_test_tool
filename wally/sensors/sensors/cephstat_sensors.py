from ..discover import provides
from .utils import SensorInfo, is_dev_accepted, execute


mon_command_list = []
osd_command_list = []

@provides("ceph_stat")
def ceph_stat(disallowed_prefixes=None, allowed_prefixes=None):
    results = {}
    return results


def daemons_list():
    """Prepare daemons calls"""
    cmd = "ps auxww |sed -nEe 's/^.*ceph-(mon|osd) .*-i *([^ ]*) .*/\1.\2/p'"
    ps = execute(cmd)
    return ps.split("\n")


def get_daemons_dump():
    result = {}
    for daemon in daemons_list():
        commands = osd_command_list if "osd" in daemon else mon_command_list
        for com in commands:
            cmd = "ceph daemon {0} {1}".format(daemon, com)
            name = "{0}:{1}".format(daemon, com)
            result[name] = execute(cmd)


