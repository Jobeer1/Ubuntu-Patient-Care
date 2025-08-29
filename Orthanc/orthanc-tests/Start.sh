#!/bin/bash

# Without Docker on Ubuntu 18.04:
#
# (1) Compile Orthanc 0.8.6:
#   $ cd $HOME/Releases/
#   $ hg clone -u Orthanc-0.8.6 https://orthanc.uclouvain.be/hg/orthanc/ Orthanc-0.8.6
#   $ mkdir $HOME/Releases/Orthanc-0.8.6/Build
#   $ cd $HOME/Releases/Orthanc-0.8.6/Build
#   $ cmake .. -DCMAKE_BUILD_TYPE=Release -DSTATIC_BUILD=ON
#   $ make -j4 UnitTests Orthanc
#
# (2) Run the integration tests using Orthanc 0.8.6:
#   $ rm -rf /tmp/OrthancStorage ; python ./Tests/Run.py --orthanc=$HOME/Releases/Orthanc-0.8.6/Build/Orthanc --force
#

set -ex

sudo docker run --rm -t -i -p 5000:5000 -p 5001:5001 \
     -v `pwd`:/tmp/tests:ro \
     --entrypoint python jodogne/orthanc-tests \
     /tmp/tests/Tests/Run.py --docker $*
