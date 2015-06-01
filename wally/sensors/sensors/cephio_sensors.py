from ..discover import provides
from .io_sensors import io_stat


@provides("ceph-io")
def ceph_io_stat(disallowed_prefixes=None, allowed_prefixes=None):
    iostat = io_stat()
    if allowed_prefixes is not None:
        results = {name: value
                   for name, value in iostat.items()
                   if name.partition(".")[0] in allowed_prefixes}
    else:
        results = {}
    return results
