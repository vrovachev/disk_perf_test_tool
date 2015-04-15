import argparse
import logging
import socket
import sys
import tempfile
import os
import array
import fcntl
import paramiko

from urlparse import urlparse
import struct
from nodes.node import Node
from utils import parse_creds
from fuel_rest_api import KeystoneAuth, Cluster
from scripts.agent import get_ip_by_interface

tmp_file = tempfile.NamedTemporaryFile().name
openrc_path = tempfile.NamedTemporaryFile().name
logger = logging.getLogger("io-perf-tool")



def get_cluster_id(cluster_name, conn):
    clusters = conn.do("get", path="/api/clusters")
    for cluster in clusters:
        if cluster['name'] == cluster_name:
            return cluster['id']


def discover_fuel_nodes(fuel_url, creds, cluster_name):
    username, tenant_name, password = parse_creds(creds)
    creds = {"username": username,
             "tenant_name": tenant_name,
             "password": password}

    fuel = KeystoneAuth(fuel_url, creds, headers=None, echo=None,)
    cluster_id = get_cluster_id(cluster_name, fuel)
    cluster = Cluster(fuel, id=cluster_id)
    nodes = [node for node in cluster.get_nodes()]
    ips = [node.get_ip() for node in nodes]
    roles = [node.get_roles() for node in nodes]

    host = urlparse(fuel_url).hostname
    openrc_dict = cluster.get_openrc()

    nodes, to_clean = run_agent(ips, roles, host, tmp_file)
    nodes = [Node(node[0], node[1]) for node in nodes]

    return nodes, to_clean, openrc_dict


def discover_fuel_nodes_clean(fuel_url, ssh_creds, nodes, base_port=12345):
    admin_ip = urlparse(fuel_url).hostname
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=admin_ip, port=ssh_creds["port"],
                password=ssh_creds["password"], username=ssh_creds["username"])

    command = "python /tmp/agent.py --clean=True --ext_ip=" + \
              admin_ip + " --base_port=" \
              + str(base_port) + " --ports"

    for node in nodes:
        ip = urlparse(node[0]).hostname
        command += " " + ip

    (stdin, stdout, stderr) = ssh.exec_command(command)
    for line in stdout.readlines():
        print line


def send_all_files(sftp, path):
    files = [f for f in os.listdir(path) if
                  os.path.isfile(os.path.join(path, f))]

    files = filter(lambda path: path.endswith('.py'), files)
    for f in files: 
        sftp.put(os.path.join(path, f),
             os.path.join("/tmp/sensors/", f))


def run_agent(ip_addresses, roles, host, tmp_name, password="test37", port=22,
              base_port=12345):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=host, port=port, password=password, username="root")
    sftp = ssh.open_sftp()
    ssh.exec_command('mkdir /tmp/sensors')
    sftp.put(os.path.join(os.path.dirname(__file__), 'agent.py'),
             "/tmp/agent.py")
    sensors_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                               'sensors')
    send_all_files(sftp, sensors_dir)


    fuel_id_rsa_path = tmp_name
    sftp.get('/root/.ssh/id_rsa', fuel_id_rsa_path)
    os.chmod(fuel_id_rsa_path, 0o700)
    ip = get_ip_by_interface('eth0')

    command = "python /tmp/agent.py --udp_url=udp://" + ip + ":5669 --base_port=" + \
              str(base_port) + " --ext_ip=" \
              + host + " --ports"

    for address in ip_addresses:
        command += " " + address

    (stdin, stdout, stderr) = ssh.exec_command(command)
    node_port_mapping = {}

    for line in stderr.readlines():
        print line

    for line in stdout.readlines():
        results = line.split(' ')

        if len(results) != 2:
            continue

        node, port = results
        node_port_mapping[node] = port

    nodes = []
    nodes_to_clean = []

    for i in range(len(ip_addresses)):
        ip = ip_addresses[i]
        role = roles[i]
        port = node_port_mapping[ip]

        nodes_to_clean.append(("ssh://root@" + ip + ":" +
                               port.rstrip('\n')
                               + ":" + fuel_id_rsa_path, role))

        nodes.append(("ssh://root@" + host + ":" + port.rstrip('\n')
                      + ":" + fuel_id_rsa_path, role))

    ssh.close()
    logger.info('Files has been transferred successfully to Fuel node, ' \
                'agent has been launched')
    logger.info("Nodes : " + str(nodes))

    return nodes, nodes_to_clean


def parse_command_line(argv):
    parser = argparse.ArgumentParser(
        description="Connect to fuel master and setup ssh agent")
    parser.add_argument(
        "--fuel_url", required=True)
    parser.add_argument(
        "--cluster_name", required=True)
    parser.add_argument(
        "--iface", default="eth1")
    parser.add_argument(
        "--creds", default="admin:admin@admin")

    return parser.parse_args(argv)


def main(argv):
    args = parse_command_line(argv)

    nodes, to_clean, _ = discover_fuel_nodes(args.fuel_url,
                                          args.creds, args.cluster_name)
    discover_fuel_nodes_clean(args.fuel_url, {"username": "root",
                                              "password": "test37",
                                              "port": 22}, to_clean)


if __name__ == "__main__":
    main(sys.argv[1:])
