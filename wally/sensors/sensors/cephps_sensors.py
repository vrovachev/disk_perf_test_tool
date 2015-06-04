from ..discover import provides
from .pscpu_sensors import pscpu_stat
from .psram_sensors import psram_stat


@provides("ceph-ps")
def ceph_ps_stat(disallowed_prefixes=None, allowed_prefixes=None):
    ps_stat = pscpu_stat(allowed_prefixes=("ceph"))
    ps_stat.update(psram_stat(allowed_prefixes=("ceph")))
    return ps_stat

