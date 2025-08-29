#!/bin/bash

# Cloud storage plugins for Orthanc
# Copyright (C) 2020-2023 Osimis S.A., Belgium
# Copyright (C) 2024-2025 Orthanc Team SRL, Belgium
# Copyright (C) 2021-2025 Sebastien Jodogne, ICTEAM UCLouvain, Belgium
#
# This program is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License
# as published by the Free Software Foundation, either version 3 of
# the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.


set -ex


if [ "$1" != "Debug" -a "$1" != "Release" ]; then
    echo "Please provide build type as first argument: Debug or Release"
    exit -1
fi

if [ "$2" != "i686" -a "$2" != "x86_64" ]; then
    echo "Please provide architecture as second argument: i686 or x86_64"
    exit -1
fi


##
## Prepare a Docker container with mingw
##

if [ -t 1 ]; then
    # TTY is available => use interactive mode
    DOCKER_FLAGS='-i'
fi

ROOT_DIR=`dirname $(readlink -f $0)`/..
IMAGE=orthanc-aws-mingw
TARGET=${ROOT_DIR}/mingw-binaries-$2/

if [ -e "${TARGET}" ]; then
    echo "Target folder is already existing, aborting"
    exit -1
fi

mkdir -p ${TARGET}

( cd ${ROOT_DIR}/Aws/mingw-compile && \
      docker build -t ${IMAGE} . )


##
## Build
##

docker run -t ${DOCKER_FLAGS} --rm \
       --user $(id -u):$(id -g) \
       -v ${ROOT_DIR}/:/source:ro \
       -v ${TARGET}:/target:rw \
       ${IMAGE} \
       bash /source/Aws/mingw-compile/build.sh $1 $2

ls -lR ${TARGET}
