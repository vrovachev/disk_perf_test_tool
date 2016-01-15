#!/bin/bash

set -e
set -x

OMGPATN=/tmp

mkdir -p "$OMGPATN"
cd "$OMGPATN"

if [ -d venv ]; then
exit 0
fi

apt-get update
apt-get -y install git python-pip python-virtualenv

mkdir venv
cd venv
virtualenv .

cd "$OMGPATN"
git clone http://github.com/openstack/oslo.messaging
source venv/bin/activate
apt-get -y install python-scipy libblas-dev liblapack-dev libatlas-base-dev gfortran
pip install numpy scipy eventlet PyYAML oslo.messaging petname
cd oslo.messaging
python setup.py install
