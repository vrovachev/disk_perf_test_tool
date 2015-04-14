import argparse
import subprocess
import sys
import socket
import struct
import array
import fcntl
from sensors.protocol import create_protocol


def get_all_interfaces():
    max_possible = 128  # arbitrary. raise if needed.
    bytes = max_possible * 32
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    names = array.array('B', '\0' * bytes)
    outbytes = struct.unpack('iL', fcntl.ioctl(
        s.fileno(),
        0x8912,  # SIOCGIFCONF
        struct.pack('iL', bytes, names.buffer_info()[0])
    ))[0]
    namestr = names.tostring()
    lst = []
    for i in range(0, outbytes, 40):
        name = namestr[i:i+16].split('\0', 1)[0]
        ip = namestr[i+20:i+24]
        lst.append((name, ip))
    return lst


def format_ip(addr):
    return str(ord(addr[0])) + '.' + \
        str(ord(addr[1])) + '.' + \
        str(ord(addr[2])) + '.' + \
        str(ord(addr[3]))


def get_ip_by_interface(interface_name):
    interfaces = get_all_interfaces()

    for iface in interfaces:
        if iface[0] == interface_name:
            return format_ip(iface[1])


def forward_udp(dest, sources):
    sources = [create_protocol(source, receiver=True) for source in sources]
    sender = create_protocol(dest)

    while True:
        [sender.send(source.recv(1)) for source in sources]


def find_interface_by_ip(ext_ip):
    ifs = get_all_interfaces()
    for i in ifs:
        ip = format_ip(i[1])

        if ip == ext_ip:
            return str(i[0])

    print "External ip doesnt corresponds to any of available interfaces"
    return None


def make_tunnels(ips, ext_ip, base_port=12345, delete=False):
    node_port = {}

    if delete is True:
        mode = "-D"
    else:
        mode = "-A"

    iface = find_interface_by_ip(ext_ip)

    for ip in ips:
        p = subprocess.Popen(["iptables -t nat " + mode + " PREROUTING " +
                              "-p tcp -i " + iface + "  --dport "
                              + str(base_port) +
                              " -j DNAT --to " + str(ip) + ":22"],
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,
                             shell=True)

        out, err = p.communicate()

        if out is not None:
            print out

        if err is not None:
            print err

        node_port[ip] = base_port
        base_port += 1

    return node_port


def parse_command_line(argv):
    parser = argparse.ArgumentParser(description=
                                     "Connect to fuel master "
                                     "and setup ssh agent")
    parser.add_argument(
        "--base_port", type=int, required=True)

    parser.add_argument(
        "--ext_ip", type=str, required=True)

    parser.add_argument(
        "--clean", type=bool, default=False)

    parser.add_argument(
        "--udp_url", type=str   , default=False)

    parser.add_argument(
        "--ports", type=str, nargs='+')

    return parser.parse_args(argv)


def main(argv):
    arg_object = parse_command_line(argv)
    mapping = make_tunnels(arg_object.ports,
                           ext_ip=arg_object.ext_ip,
                           base_port=arg_object.base_port,
                           delete=arg_object.clean)

    if arg_object.clean is False:
        for k in mapping:
            print k + " " + str(mapping[k])

    ips = [mapping[k] for k in mapping]
    urls = ['udp://' + ip + ':5669' for ip in ips]
    forward_udp(arg_object.udp_url, urls)


if __name__ == "__main__":
    main(sys.argv[1:])
