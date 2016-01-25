#!/bin/bash

set -e
set -x

cd /tmp

if [ -d venv ]; then
exit 0
fi

apt-get update
apt-get -y install git python-pip virtualenv

mkdir venv
cd venv
virtualenv .

cd /tmp
git clone http://github.com/openstack/oslo.messaging
source venv/bin/activate
apt-get -y install python-scipy libblas-dev liblapack-dev libatlas-base-dev gfortran
pip install numpy scipy eventlet PyYAML oslo.messaging petname redis zmq pika_pool
cd oslo.messaging
python setup.py install
