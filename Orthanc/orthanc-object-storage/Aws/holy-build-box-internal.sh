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


set -e

# Activate Holy Build Box environment.
source /hbb_exe/activate

set -ex

mkdir /tmp/build
cd /tmp/build

# Holy Build Box defines LDFLAGS as "-L/hbb_exe/lib
# -static-libstdc++". The "-L/hbb_exe/lib" option results in linking
# errors "undefined reference" to `std::__once_callable',
# 'std::__once_call' and '__once_proxy'.
export LDFLAGS=-static-libstdc++
unset LDPATHFLAGS
unset SHLIB_LDFLAGS
unset LD_LIBRARY_PATH
unset LIBRARY_PATH

mkdir -p /tmp/source-writeable/Aws

cp -r /source/Common /tmp/source-writeable/
cp -r /source/UnitTestsSources /tmp/source-writeable/
cp /source/Aws/* /tmp/source-writeable/Aws/ || true  # Ignore error about omitting directories

cmake /tmp/source-writeable/Aws/ \
      -DORTHANC_FRAMEWORK_VERSION=1.12.3 \
      -DORTHANC_FRAMEWORK_SOURCE=web \
      -DCMAKE_BUILD_TYPE=$1 -DSTATIC_BUILD=ON

# Use only 2 processes (not `nproc`), as this is a very heavy compilation
# make -j2

make -j`nproc --all`

./UnitTests

if [ "$1" == "Release" ]; then
    strip ./libOrthancAwsS3Storage.so
fi

cp ./libOrthancAwsS3Storage.so /target/
cp ./UnitTests /target/
