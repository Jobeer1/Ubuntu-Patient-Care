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

mkdir /tmp/source-writeable

cp /source/CMakeLists.txt /tmp/source-writeable/

cp -r /source/CodeAnalysis /tmp/source-writeable/
cp -r /source/Resources /tmp/source-writeable/
cp -r /source/Sources /tmp/source-writeable/

mkdir /tmp/build
cd /tmp/build

wget https://orthanc.uclouvain.be/downloads/third-party-downloads/Python/python-3.9.13-win32.zip
unzip python-3.9.13-win32.zip

if [ "$1" == "Release" ]; then
    LIBRARY_NAME=python39.lib
else
    LIBRARY_NAME=python39_d.lib
fi

cmake /tmp/source-writeable/ \
      -DCMAKE_BUILD_TYPE=$1 \
      -DSTATIC_BUILD=ON \
      -DUSE_LEGACY_BOOST=ON \
      -DPYTHON_VERSION=3.9 \
      -DPYTHON_LIBRARY_NAME=${LIBRARY_NAME} \
      -DPYTHON_WINDOWS_ROOT=/tmp/build/python-3.9.13-win32/ \
      -DCMAKE_TOOLCHAIN_FILE=/source/Resources/Orthanc/Toolchains/MinGW-W64-Toolchain32.cmake \
      -DCMAKE_INSTALL_PREFIX=/target 

make -j`nproc`

if [ "$1" == "Release" ]; then
    i686-w64-mingw32-strip ./libOrthancPython.dll
fi

make install
