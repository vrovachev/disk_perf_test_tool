# BLOCK_SIZES = "1k 4k 64k 256k 1m"
# OPERATIONS="randwrite write randread read"
# SYNC_TYPES="s a d"
# REPEAT_COUNT="3"
# CONCURRENCES="1 8 64"

from utils import ssize_to_kb

SYNC_FACTOR = "x500"
DIRECT_FACTOR = "x10000"
ASYNC_FACTOR = "r2"


def make_list(x):
    if not isinstance(x, (list, tuple)):
        return [x]
    return x

HDD_SIZE_KB = 45 * 1000 * 1000


def make_load(sizes, opers, sync_types, concurrence, test_file="results.txt",
              tester_type='iozone', repeat_count=3, iosizes=["4k", "64k", "2m"]):

    iodepth = 1
    for conc in make_list(concurrence):
        for bsize in make_list(sizes):
            for iosize in iosizes:
                if bsize <= iosize:
                    for oper in make_list(opers):
                        # filter out too slow options
                        if bsize in "1k 4k":
                            continue

                        # filter out sync reads
                        if oper in "read randread":
                            continue

                        size_sync_opts = "--iosize {0}".format(iosize)

                        # size_sync_opts = get_file_size_opts(sync_type)

                        io_opts = "--type {0} ".format(tester_type)
                        io_opts += "-a {0} ".format(oper)
                        io_opts += "--iodepth {0} ".format(iodepth)
                        io_opts += "--blocksize {0} ".format(bsize)
                        io_opts += size_sync_opts + " "
                        io_opts += "--concurrency {0}".format(conc) + " "
                        io_opts += "--binary-path {0}".format(tester_type) + " "
                        io_opts += "--test-file {0}".format(test_file) + " "

                        for i in range(repeat_count):
                            if len(sync_types) != 0:
                                for sync_type in sync_types:
                                    yield io_opts + "--sync {0}".format(sync_type)
                            else:
                                yield io_opts


sizes = "4k 64k 2m".split()
opers = "randwrite write randread read".split()
concurrence = "1 8 64".split()

with open("commands.txt", "w+") as f:
    for io_opts in make_load(sizes=sizes, concurrence=concurrence,
                        sync_types=[], opers=opers, tester_type="fio", repeat_count=1):
        f.write(io_opts + "\n")
