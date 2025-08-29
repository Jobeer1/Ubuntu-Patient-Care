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


set -e

if [ "$#" -ne 1 ]; then
    echo "Illegal number of parameters: Must provide the target folder"
    exit -1
fi

# Determine the absolute path to the directory containing the script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

TARGET=$1
echo "Will publish libraries in folder: ${TARGET}"

mkdir -p ${TARGET}

VERSION=`grep "set(PLUGIN_VERSION" ${DIR}/../../CMakeLists.txt | cut -d '"' -f 2`
echo "Version of the Python plugin: ${VERSION}"

set -x


## Windows 32

bash ${DIR}/MinGW32-Python2.7/docker-compile.sh Release
cp ${DIR}/../../docker-build/lib/libOrthancPython.dll ${TARGET}/OrthancPython-Win32-Python2.7-${VERSION}.dll

bash ${DIR}/MinGW32-Python3.7/docker-compile.sh Release
cp ${DIR}/../../docker-build/lib/libOrthancPython.dll ${TARGET}/OrthancPython-Win32-Python3.7-${VERSION}.dll

bash ${DIR}/MinGW32-Python3.8/docker-compile.sh Release
cp ${DIR}/../../docker-build/lib/libOrthancPython.dll ${TARGET}/OrthancPython-Win32-Python3.8-${VERSION}.dll

bash ${DIR}/MinGW32-Python3.9/docker-compile.sh Release
cp ${DIR}/../../docker-build/lib/libOrthancPython.dll ${TARGET}/OrthancPython-Win32-Python3.9-${VERSION}.dll

bash ${DIR}/MinGW32-Python3.10/docker-compile.sh Release
cp ${DIR}/../../docker-build/lib/libOrthancPython.dll ${TARGET}/OrthancPython-Win32-Python3.10-${VERSION}.dll

bash ${DIR}/MinGW32-Python3.11/docker-compile.sh Release
cp ${DIR}/../../docker-build/lib/libOrthancPython.dll ${TARGET}/OrthancPython-Win32-Python3.11-${VERSION}.dll

bash ${DIR}/MinGW32-Python3.12/docker-compile.sh Release
cp ${DIR}/../../docker-build/lib/libOrthancPython.dll ${TARGET}/OrthancPython-Win32-Python3.12-${VERSION}.dll

bash ${DIR}/MinGW32-Python3.13/docker-compile.sh Release
cp ${DIR}/../../docker-build/lib/libOrthancPython.dll ${TARGET}/OrthancPython-Win32-Python3.13-${VERSION}.dll


## Windows 64

bash ${DIR}/MinGW64-Python2.7/docker-compile.sh Release
cp ${DIR}/../../docker-build/lib/libOrthancPython.dll ${TARGET}/OrthancPython-Win64-Python2.7-${VERSION}.dll

bash ${DIR}/MinGW64-Python3.7/docker-compile.sh Release
cp ${DIR}/../../docker-build/lib/libOrthancPython.dll ${TARGET}/OrthancPython-Win64-Python3.7-${VERSION}.dll

bash ${DIR}/MinGW64-Python3.8/docker-compile.sh Release
cp ${DIR}/../../docker-build/lib/libOrthancPython.dll ${TARGET}/OrthancPython-Win64-Python3.8-${VERSION}.dll

bash ${DIR}/MinGW64-Python3.9/docker-compile.sh Release
cp ${DIR}/../../docker-build/lib/libOrthancPython.dll ${TARGET}/OrthancPython-Win64-Python3.9-${VERSION}.dll

bash ${DIR}/MinGW64-Python3.10/docker-compile.sh Release
cp ${DIR}/../../docker-build/lib/libOrthancPython.dll ${TARGET}/OrthancPython-Win64-Python3.10-${VERSION}.dll

bash ${DIR}/MinGW64-Python3.11/docker-compile.sh Release
cp ${DIR}/../../docker-build/lib/libOrthancPython.dll ${TARGET}/OrthancPython-Win64-Python3.11-${VERSION}.dll

bash ${DIR}/MinGW64-Python3.12/docker-compile.sh Release
cp ${DIR}/../../docker-build/lib/libOrthancPython.dll ${TARGET}/OrthancPython-Win64-Python3.12-${VERSION}.dll

bash ${DIR}/MinGW64-Python3.13/docker-compile.sh Release
cp ${DIR}/../../docker-build/lib/libOrthancPython.dll ${TARGET}/OrthancPython-Win64-Python3.13-${VERSION}.dll
