#!/usr/bin/env python3

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


import argparse
import requests

parser = argparse.ArgumentParser(description = 'Clear the cache of the OHIF plugin (for "dicom-json" data source).')
parser.add_argument('--url',
                    default = 'http://localhost:8042',
                    help = 'URL to the REST API of the Orthanc server')
parser.add_argument('--username',
                    default = 'orthanc',
                    help = 'Username to the REST API')
parser.add_argument('--password',
                    default = 'orthanc',
                    help = 'Password to the REST API')

args = parser.parse_args()

auth = requests.auth.HTTPBasicAuth(args.username, args.password)

METADATA = '4202'

for instance in requests.get('%s/instances' % args.url, auth=auth).json():
    if METADATA in requests.get('%s/instances/%s/metadata' % (args.url, instance), auth=auth).json():
        requests.delete('%s/instances/%s/metadata/%s' % (args.url, instance, METADATA), auth=auth)
