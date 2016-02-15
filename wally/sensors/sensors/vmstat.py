import subprocess

from ..discover import provides
from .utils import SensorInfo


@provides("vmstat")
def io_stat(disallowed_prefixes=None, allowed_prefixes=None):
    results = {}
    p = subprocess.Popen('vmstat', stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    out, err = p.communicate()
    out_lines = out.strip().split('\n')
    keys = [k.strip() for k in out_lines[1].split()]
    values = [v.strip() for v in out_lines[2].split()]
    for key, value in zip(keys, values):
        results[key] = SensorInfo(value, False)

    return results
