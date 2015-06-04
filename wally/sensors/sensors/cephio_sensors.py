from os import path, readlink

from ..discover import provides
from .io_sensors import io_stat
from .utils import execute


@provides("ceph-io")
def ceph_io_stat(disallowed_prefixes=None, allowed_prefixes=None):
    iostat = io_stat()
    devs = get_cephosd_disks()
    results = {"{0}_osd{1}".format(name, devs[name.partition(".")[0]]): value
               for name, value in iostat.items()
               if name.partition(".")[0] in devs}
    return results


def get_cephosd_disks():
    """Find osd and journal disks"""
    devs = {}
    mounted = execute("mount")
    for line in mounted.split("\n"):
        if line.startswith("/dev/") and "osd" in line:
            disk, _, osdpath = line.split()[0:3]
            # find partition name
            dev = disk.replace("/dev/", "")
            # find osd name
            osdnum = open(path.join(osdpath, "whoami")).readline()
            # find osd journal location
            journal_dev = readlink(path.join(osdpath, "journal"))
            journal_dev = journal_dev.replace("/dev/", "")
            # add to dict
            devs[dev] = osdnum
            devs[journal_dev] = "{0}journal".format(osdnum)
    return devs

