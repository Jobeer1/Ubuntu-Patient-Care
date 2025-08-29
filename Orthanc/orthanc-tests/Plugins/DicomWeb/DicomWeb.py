#!/usr/bin/python

# Orthanc - A Lightweight, RESTful DICOM Store
# Copyright (C) 2012-2016 Sebastien Jodogne, Medical Physics
# Department, University Hospital of Liege, Belgium
# Copyright (C) 2017-2023 Osimis S.A., Belgium
# Copyright (C) 2024-2025 Orthanc Team SRL, Belgium
# Copyright (C) 2021-2025 Sebastien Jodogne, ICTEAM UCLouvain, Belgium
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


import os
import sys
import email
import uuid

from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'Tests'))
from Toolbox import *


def _AttachPart(body, path, contentType, boundary):
    with open(path, 'rb') as f:
        body += bytearray('--%s\r\n' % boundary, 'ascii')
        body += bytearray('Content-Type: %s\r\n\r\n' % contentType, 'ascii')
        body += f.read()
        body += bytearray('\r\n', 'ascii')


def SendStowRaw(orthanc, uri, dicom, partsContentType='application/dicom'):
    # We do not use Python's "email" package, as it uses LF (\n) for line
    # endings instead of CRLF (\r\n) for binary messages, as required by
    # RFC 1341
    # http://stackoverflow.com/questions/3086860/how-do-i-generate-a-multipart-mime-message-with-correct-crlf-in-python
    # https://www.w3.org/Protocols/rfc1341/7_2_Multipart.html

    # Create a multipart message whose body contains all the input DICOM files
    boundary = str(uuid.uuid4())  # The boundary is a random UUID
    body = bytearray()

    if isinstance(dicom, list):
        for i in range(dicom):
            _AttachPart(body, dicom[i], partsContentType, boundary)
    else:
        _AttachPart(body, dicom, partsContentType, boundary)

    # Closing boundary
    body += bytearray('--%s--' % boundary, 'ascii')

    # Do the HTTP POST request to the STOW-RS server
    headers = {
        'Content-Type' : 'multipart/related; type=application/dicom; boundary=%s' % boundary,
        'Accept' : 'application/json',
    }

    (response, content) = DoPostRaw(orthanc, uri, body, headers = headers)

    return (response.status, DecodeJson(content))


def SendStow(orthanc, uri, dicom, partsContentType='application/dicom'):
    (status, content) = SendStowRaw(orthanc, uri, dicom, partsContentType)
    if not (status in [ 200 ]):
        raise Exception('Bad status: %d' % status)
    else:
        return content


def DoGetMultipart(orthanc, uri, headers = {}, returnHeaders = False):
    answer = DoGetRaw(orthanc, uri, headers = headers)

    header = ''
    for i in answer[0]:
        header += '%s: %s\r\n' % (i, answer[0][i])

    b = bytearray()
    b.extend(header.encode('ascii'))
    b.extend(b'\r\n')
    b.extend(answer[1])
        
    if (sys.version_info >= (3, 0)):
        msg = email.message_from_bytes(b)
    else:
        msg = email.message_from_string(b)
        
    if not msg.is_multipart():
        raise Exception('Not a multipart message')
    
    result = []

    for part in msg.walk():
        payload = part.get_payload(decode = True)
        if payload != None:
            if returnHeaders:
                h = {}
                for (key, value) in part.items():
                    h[key] = value
                result.append((payload, h))
            else:
                result.append(payload)

    return result
