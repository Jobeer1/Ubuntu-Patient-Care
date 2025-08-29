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

BUILD_TYPE=$1
DEBIAN_VERSION=$2
PYTHON_VERSION=$3
USER_ID=$4
GROUP_ID=$5

# Create the same user and group than the one who is running the
# "./docker-{distro}-compile.sh" script on the hosting system (*)
groupadd -g ${GROUP_ID} -r orthanc
useradd -u ${USER_ID} -r -g orthanc orthanc

# This line is needed since the release of Debian 13 (trixie)
if [ "${DEBIAN_VERSION}" = "buster" ]; then
    sed -i s/deb.debian.org/archive.debian.org/g /etc/apt/sources.list
fi

if [ "${DEBIAN_VERSION}" = "bullseye" ]; then
    MERCURIAL_PACKAGES=python
else
    MERCURIAL_PACKAGES=mercurial
fi

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get -y install nano build-essential unzip cmake pkg-config libpython3-dev curl python3-pystache ${MERCURIAL_PACKAGES}
apt-get -y clean
rm -rf /var/lib/apt/lists/*


if [ "${DEBIAN_VERSION}" = "bullseye" ]; then
   # On Bullseye, we get "stat: cannot statx
   # '/usr/share/mercurial/hgext.rc': Operation not permitted" if
   # installing the "mercurial" package using apt-get. As a consequence,
   # we manually install Mercurial from sources.
   MERCURIAL=mercurial-5.4.1
   cd /tmp
   curl https://www.mercurial-scm.org/release/${MERCURIAL}.tar.gz > ${MERCURIAL}.tar.gz
   tar xvf ${MERCURIAL}.tar.gz
   export PATH=${PATH}:/tmp/${MERCURIAL}/
fi


mkdir /tmp/source-writeable

cp /source/CMakeLists.txt /tmp/source-writeable/

cp -r /source/CodeAnalysis /tmp/source-writeable/
cp -r /source/Resources /tmp/source-writeable/
cp -r /source/Sources /tmp/source-writeable/

mkdir /tmp/build
cd /tmp/build

cmake /tmp/source-writeable/ \
      -DCMAKE_BUILD_TYPE=${BUILD_TYPE} \
      -DPYTHON_VERSION=${PYTHON_VERSION} \
      -DSTATIC_BUILD=ON \
      -DCMAKE_INSTALL_PREFIX=/target 

make -j`nproc`

if [ "$1" == "Release" ]; then
    strip ./libOrthancPython.so
fi

# Copy the installation to the host filesystem, using the
# newly-created user "orthanc" (*) that corresponds to the user who is
# running "./debian-{distro}-compile.sh" script. This allows to avoid
# files owned by the "root" user on the host filesystem.
su -c "cp /tmp/build/libOrthancPython.so /target" orthanc
su -c "cp /tmp/build/orthanc.pyi /target" orthanc
