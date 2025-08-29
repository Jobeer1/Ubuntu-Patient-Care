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

if [ "$2" = "i686"  ]; then
    TOOLCHAIN=MinGW-W64-Toolchain32.cmake
elif [ "$2" = "x86_64"  ]; then
    TOOLCHAIN=MinGW-W64-Toolchain64.cmake
else
    exit -1
fi


mkdir /tmp/aws
mkdir /tmp/aws/Aws/
mkdir /tmp/aws/Build/

# Ignore possible build directories in "Aws" folder
find /source/Aws/ -type f -maxdepth 1 | while read f
do
    cp "$f" /tmp/aws/Aws/
done

cp -r /source/Common /tmp/aws/
cp -r /source/UnitTestsSources /tmp/aws/

cd /tmp/aws/Build/
cmake ../Aws -DCMAKE_BUILD_TYPE=Release -DUSE_VCPKG_PACKAGES=OFF -DSTATIC_BUILD=ON \
      -DCMAKE_TOOLCHAIN_FILE=/source/Common/Resources/Orthanc/Toolchains/${TOOLCHAIN}
make -j`nproc --all`

cp ./libOrthancAwsS3Storage.dll /target
cp ./UnitTests.exe /target
