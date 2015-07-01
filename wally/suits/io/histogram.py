from os import listdir
from os.path import isfile, join

from wally.suits.io.fio import load_fio_log_file


def make_histogram(dir_path, total_time, iops=True, skip_range=5):
    """
        @dir_path - path to dir with fio log files
        @total_time - time how log fio tests were proceed
        @iops - whether we have iops data or bandwith
        @skip_ranges - range from histogram in percent that is neglected.
    """
    if iops:
        file_pattern = 'iops'
    else:
        file_pattern = 'bw'

    files = [join(dir_path, f) for f in listdir(dir_path)
             if isfile(join(dir_path, f)) and
             join(dir_path, f).endswith('log') and
             file_pattern in join(dir_path, f)]

    intervals = []
    id = 1
    begins = {}
    ends = {}
    values = {}

    #read all data from all files and put to the same array intervals.
    for f in files:
        series = load_fio_log_file(f)

        for begin, lenght, value in series.data:
            end = begin + lenght

            if end >= total_time * (100 - skip_range) / 100.0:
                end = total_time * (100 - skip_range) / 100.0

            begins[-id] = begin
            ends[id] = end
            values[id] = value
            intervals.append((begin, -id))
            intervals.append((end, id))
            id += 1

    #sort key points by the time. begin of interval always goes before end.
    intervals = sorted(intervals)
    current = 0
    i = 0
    hist = []

    while i < len(intervals):
        # current - is current iops value.
        # if open point is encountered that iops value is added to current
        # else is substracted.
        while i + 1 < len(intervals) and \
              intervals[i][0] == intervals[i + 1][0]:
            if intervals[i][1] < 0:
                current += values[-intervals[i][1]]
            else:
                current -= values[intervals[i][1]]

            i += 1
        # add value of the last interval that starts at the same point.
        if intervals[i][1] < 0:
            current += values[-intervals[i][1]]
        else:
            current -= values[intervals[i][1]]

        # if the last considered interval is not the last in the array.
        if i < len(intervals) - 1:
            i += 1
            value = (intervals[i][0] - intervals[i - 1][0]) * current
            hist.append((intervals[i - 1][0], intervals[i][0], value))
        else:
            # if the last considered interval is the last at the array
            # use total_time as rightest point.
            value = (total_time - intervals[i - 1][0]) * current
            hist.append((intervals[i - 1][0], total_time, value))
            i += 1

    return hist


def get_total(hist):
    """
        Get total count of operations from histogram.
    """
    total = 0

    for h in hist:
        total += h[2]

    return total


def second_hist(hist, total_time, step):
    """
        Make histogram with 1 second intervals and count of oi operations on these intervals.
    """
    pos = 0
    hist2 = []

    for t in range(0, total_time + 1, step):

        # collect all intervals that intersect current [t, t + step] interval
        buf = [i for i in range(len(hist)) if (hist[i][0] >= t and hist[i][0] < t + step) or
                                                (hist[i][1] > t and hist[i][1] < t + step)]

        if len(buf) == 0:
            break

        total = 0
        # traverse all intervals and compute speed on this interval ,
        # multiply by length and add to total.
        for i in range(len(buf)):
            interval = (min(hist[buf[i]][1], t + step) -
                        max(hist[buf[i]][0], t))
            speed = hist[buf[i]][2] / (hist[buf[i]][1] - hist[buf[i]][0])
            total += interval * speed

        hist2.append(total)

    return hist2


if __name__ == '__main__':
    hist = make_histogram('/home/gstepanov/disk_perf_test_tool/fio_binaries', total_time=10)
    print get_total(hist)
    print second_hist(hist, total_time=10, step=1)