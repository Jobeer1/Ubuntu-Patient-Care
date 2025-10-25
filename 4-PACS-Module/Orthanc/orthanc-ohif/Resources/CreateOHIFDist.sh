#!/bin/bash

# SPDX-FileCopyrightText: 2023-2025 Sebastien Jodogne, ICTEAM UCLouvain, Belgium
# SPDX-License-Identifier: GPL-3.0-or-later

# OHIF plugin for Orthanc
# Copyright (C) 2023-2025 Sebastien Jodogne, ICTEAM UCLouvain, Belgium
#
# This program is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.



# This command-line script uses the "bun" tool to populate the "dist"
# folder of OHIF. It uses Docker to this end, in order to be usable on
# our CIS.

# sample command to create the tar.gz archive from OHIF github repo:
# git archive --format tar.gz --prefix Viewers-fix-video-auth-token/ -o ohif-fix-video-auth-token.tar.gz HEAD

set -ex

if [ "$1" = "" ]; then
    PACKAGE=Viewers-3.11.0
    # PACKAGE=Viewers-fix-video-auth-token
else
    PACKAGE=$1
fi

if [ -t 1 ]; then
    # TTY is available => use interactive mode
    DOCKER_FLAGS='-i'
fi

ROOT_DIR=`dirname $(readlink -f $0)`/..
IMAGE=orthanc-ohif-node

echo "Creating the distribution of OHIF from $PACKAGE"

if [ -e "${ROOT_DIR}/OHIF/dist/" ]; then
    echo "Target folder is already existing, aborting"
    exit -1
fi

if [ ! -f "${ROOT_DIR}/OHIF/${PACKAGE}.tar.gz" ]; then
    mkdir -p "${ROOT_DIR}/OHIF"
    ( cd ${ROOT_DIR}/OHIF && \
          wget https://orthanc.uclouvain.be/downloads/third-party-downloads/OHIF/${PACKAGE}.tar.gz )
fi

mkdir -p ${ROOT_DIR}/OHIF/dist/

( cd ${ROOT_DIR}/Resources/CreateOHIFDist && \
      docker build --no-cache -t ${IMAGE} . )

# sample manual command: docker run -it --rm -v ./Resources/CreateOHIFDist/build.sh:/source/build.sh -v ./OHIF/Viewers-3.11.0-beta.9.tar.gz:/source/Viewers-3.11.0-beta.9.tar.gz -v ./OHIF/dist/:/target orthanc-ohif-node bash

docker run -t ${DOCKER_FLAGS} --rm \
       --user $(id -u):$(id -g) \
       -v ${ROOT_DIR}/Resources/CreateOHIFDist/build.sh:/source/build.sh:ro \
       -v ${ROOT_DIR}/OHIF/${PACKAGE}.tar.gz:/source/${PACKAGE}.tar.gz:ro \
       -v ${ROOT_DIR}/OHIF/dist/:/target:rw \
       ${IMAGE} \
       bash /source/build.sh ${PACKAGE}
