#!/bin/bash

set -e
set -x

if [ -d /tmp/venv ]; then
exit 0
fi

apt-get update
apt-get -y install git python-pip virtualenv

cd /tmp
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
git fetch https://review.openstack.org/openstack/oslo.messaging refs/changes/78/273478/1 && git cherry-pick FETCH_HEAD
