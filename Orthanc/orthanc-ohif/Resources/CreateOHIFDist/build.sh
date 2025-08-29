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

set -ex

if [ "$1" = "" ]; then
    echo "Please provide the source package of OHIF"
    exit -1
fi

cd /tmp/
tar xvf /source/$1.tar.gz

cd /tmp/$1
bun pm cache rm
bun install --frozen-lockfile

APP_CONFIG=config/default.js QUICK_BUILD=true PUBLIC_URL=./ bun run show:config
APP_CONFIG=config/default.js QUICK_BUILD=true PUBLIC_URL=./ bun run build

# patch files where the PUBLIC_URL was not taken into account
# Note that, for the microscopy, this is currently not working: https://github.com/OHIF/Viewers/issues/4906
sed -i "s|'/dicom-microscopy-viewer/dicomMicroscopyViewer.min.js|'./dicom-microscopy-viewer/dicomMicroscopyViewer.min.js|g" /tmp/$1/platform/app/dist/app.bundle.*.js
sed -i 's|"/dicom-microscopy-viewer|"./dicom-microscopy-viewer|g' /tmp/$1/platform/app/dist/dicom-microscopy-viewer/dicomMicroscopyViewer.min.js
sed -i 's|"/dicom-microscopy-viewer|"./dicom-microscopy-viewer|g' /tmp/$1/platform/app/dist/dicom-microscopy-viewer/index.worker.min.worker.js
sed -i 's|"/assets/android-chrome-|"./assets/android-chrome-|g' /tmp/$1/platform/app/dist/manifest.json

cp -r /tmp/$1/platform/app/dist/* /target
