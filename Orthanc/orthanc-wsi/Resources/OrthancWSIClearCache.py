#!/usr/bin/env python3

# Orthanc - A Lightweight, RESTful DICOM Store
# Copyright (C) 2012-2016 Sebastien Jodogne, Medical Physics
# Department, University Hospital of Liege, Belgium
# Copyright (C) 2017-2023 Osimis S.A., Belgium
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


import base64
import httplib2
import json
import os
import sys

if len(sys.argv) != 3 and len(sys.argv) != 5:
    print("""
Script to reinitialize the cache of the whole-slide imaging plugin for
Orthanc. Please make sure that Orthanc is running before starting this
script.

Usage: %s [hostname] [HTTP port]
Usage: %s [hostname] [HTTP port] [username] [password]
For instance: %s 127.0.0.1 8042
""" % (sys.argv[0], sys.argv[0], sys.argv[0]))
    exit(-1)


METADATA = [
    4200,  # For versions <= 0.7 of the plugin
    4201,  # For versions >= 1.0 of the plugin
]


def RunHttpRequest(uri, method, ignore_errors, body = None):
    http = httplib2.Http()
    headers = { }

    if len(sys.argv) == 5:
        username = sys.argv[4]
        password = sys.argv[5]

        # h.add_credentials(username, password)

        # This is a custom reimplementation of the
        # "Http.add_credentials()" method for Basic HTTP Access
        # Authentication (for some weird reason, this method does not
        # always work)
        # http://en.wikipedia.org/wiki/Basic_access_authentication
        headers['authorization'] = 'Basic ' + base64.b64encode(username + ':' + password)       

    url = 'http://%s:%d/%s' % (sys.argv[1], int(sys.argv[2]), uri)
    resp, content = http.request(url, method,
                                 body = body,
                                 headers = headers)

    if not ignore_errors and resp.status != 200:
        raise Exception('Cannot %s on URL %s, HTTP status %d '
                        '(Is Orthanc running? Is there a password?)' % 
                        (method, url, resp.status))
    else:
        return content.decode('utf8')


for instance in json.loads(RunHttpRequest('/instances', 'GET', ignore_errors = False)):
    print('Clearing cache for instance %s' % instance)
    for metadata in METADATA:
        RunHttpRequest('/instances/%s/metadata/%s' % (instance, metadata), 'DELETE', ignore_errors = True)

print('The WSI cache was successfully cleared')
