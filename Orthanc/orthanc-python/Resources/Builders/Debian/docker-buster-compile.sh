#!/bin/bash

# SPDX-FileCopyrightText: 2020-2023 Osimis S.A., 2024-2025 Orthanc Team SRL, 2021-2025 Sebastien Jodogne, ICTEAM UCLouvain
# SPDX-License-Identifier: AGPL-3.0-or-later

##
## Python plugin for Orthanc
## Copyright (C) 2020-2023 Osimis S.A., Belgium
## Copyright (C) 2024-2025 Orthanc Team SRL, Belgium
## Copyright (C) 2021-2025 Sebastien Jodogne, ICTEAM UCLouvain, Belgium
##
## This program is free software: you can redistribute it and/or
## modify it under the terms of the GNU Affero General Public License
## as published by the Free Software Foundation, either version 3 of
## the License, or (at your option) any later version.
##
## This program is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## Affero General Public License for more details.
##
## You should have received a copy of the GNU Affero General Public License
## along with this program. If not, see <http://www.gnu.org/licenses/>.
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

ROOT_DIR=`dirname $(readlink -f $0)`/../../..

mkdir -p ${ROOT_DIR}/docker-build-buster/

docker pull debian:buster-slim

docker run -t ${DOCKER_FLAGS} --rm \
    -v ${ROOT_DIR}:/source:ro \
    -v ${ROOT_DIR}/docker-build-buster:/target:rw \
    debian:buster-slim \
    bash /source/Resources/Builders/Debian/docker-internal.sh $1 buster 3.7 $(id -u) $(id -g)

ls -lR ${ROOT_DIR}/docker-build-buster/
