#!/bin/bash

set -ex

apt-get -y update 
apt-get install -y libgdcm-tools 
/docker-entrypoint.sh /tmp/orthanc.json
