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


##
## This script compiles cross-distribution Linux binaries thanks to
## Holy Build Box: https://github.com/phusion/holy-build-box
##
## The ideal solution would be to use Linux Standard Base
## (LSB). Unfortunately, the LSB C++ compiler is a pre-4.8 gcc that
## does not feature full C++11 capabilities, which prevents compiling
## AWS SDK.
##

set -ex

if [ "$1" != "Debug" -a "$1" != "Release" ]; then
    echo "Please provide build type: Debug or Release"
    exit -1
fi

if [ -t 1 ]; then
    # TTY is available => use interactive mode
    DOCKER_FLAGS='-i'
fi

ROOT_DIR=`dirname $(readlink -f $0)`/..

DOCKER_IMAGE=phusion/holy-build-box-64:3.0.5

mkdir -p ${ROOT_DIR}/holy-build-box

# Mapping "/etc/passwd" and "/etc/group" is necessary, otherwise git
# fails with error: "fatal: unable to look up current user in the
# passwd file: no such user"
docker run -t ${DOCKER_FLAGS} --rm \
       --user $(id -u):$(id -g) \
       -v /etc/passwd:/etc/passwd:ro \
       -v /etc/group:/etc/group:ro \
       -v ${ROOT_DIR}:/source:ro \
       -v ${ROOT_DIR}/holy-build-box:/target:rw \
       ${DOCKER_IMAGE} \
       bash /source/Aws/holy-build-box-internal.sh $1

ls -lR ${ROOT_DIR}/holy-build-box/
