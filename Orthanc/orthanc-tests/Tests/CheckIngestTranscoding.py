#!/usr/bin/env python3

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


import json
import os
import subprocess
import sys
import time
import Toolbox
import pprint

if len(sys.argv) < 2:
    print('Must provide a path to Orthanc binaries')
    exit(-1)


TMP = '/tmp/OrthancTest'
CONFIG = os.path.join(TMP, 'Configuration.json')
ORTHANC = Toolbox.DefineOrthanc()

if os.path.exists(TMP):
    print('Temporary path already exists: %s' % TMP)
    exit(-1)

os.mkdir(TMP)


def DropOrthanc():
    while True:
        try:
            instances = Toolbox.DoGet(ORTHANC, '/instances')
            if len(instances) == 0:
                break
            else:
                for i in instances:
                    Toolbox.DoDelete(ORTHANC, '/instances/%s' % i)
        except:
            time.sleep(0.05)
    


def TestTranscoding(config, tests):
    with open(CONFIG, 'w') as f:
        f.write(json.dumps(config))
    
    process = subprocess.Popen(
        sys.argv[1:] + [ CONFIG ],
        cwd = TMP,
        #stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE, 
        #shell=True
        )

    success = True

    try:
        for test in tests:
            DropOrthanc()
            print(test[0])
            with open(Toolbox.GetDatabasePath(test[0]), 'rb') as f:
                Toolbox.DoPost(ORTHANC, '/instances', f.read(), 'application/dicom')

            instances = Toolbox.DoGet(ORTHANC, '/instances')
            if len(instances) != 1:
                print('BAD NUMBER OF INSTANCES')
                success = False
                break

            metadata = Toolbox.DoGet(ORTHANC, '/instances/%s/metadata?expand' % instances[0])
            if not 'TransferSyntax' in metadata:
                print('NO METADATA')
                success = False
                break

            if metadata['TransferSyntax'] != test[1]:
                print('TRANSFER SYNTAX MISMATCH: %s vs %s' % (metadata['TransferSyntax'], test[1]))
                success = False

            if len(test) >= 3:
                tags = Toolbox.DoGet(ORTHANC, "/instances/%s/tags?simplify" % instances[0])
                if tags["PhotometricInterpretation"] != test[2]:
                    print('Invalid PhotometricInterpretation: %s' % tags["PhotometricInterpretation"])
                    success = False
                    break;
                if len(test) >= 5:
                    resp, content = Toolbox.DoGetRaw(ORTHANC, "/instances/%s/frames/0/raw" % instances[0])
                    if resp['content-type'] != test[3]:
                        print('Invalid Content-Type: %s' % resp['content-type'])
                        success = False
                    if resp['content-length'] != str(test[4]):
                        print('Invalid Content-Length: %s' % resp['content-length'])
                        success = False
                    # pprint.pprint(resp)


    except:
        success = False
            
    process.terminate()
    process.wait()

    return success


def Assert(b):
    if not b:
        raise Exception('Bad result')


print('==== TEST 1 ====')  # No transcoding by default
Assert(TestTranscoding({ }, [
    ('TransferSyntaxes/1.2.840.10008.1.2.1.dcm', '1.2.840.10008.1.2.1'),
    ('TransferSyntaxes/1.2.840.10008.1.2.2.dcm', '1.2.840.10008.1.2.2'),
    ('TransferSyntaxes/1.2.840.10008.1.2.4.51.dcm', '1.2.840.10008.1.2.4.51'),
    ('TransferSyntaxes/1.2.840.10008.1.2.4.50.dcm', '1.2.840.10008.1.2.4.50', 'YBR_FULL_422', 'image/jpeg', 53476),
]))

print('==== TEST 2 ====')
Assert(TestTranscoding({
    'IngestTranscoding' : '1.2.840.10008.1.2.1',
}, [
    ('TransferSyntaxes/1.2.840.10008.1.2.1.dcm', '1.2.840.10008.1.2.1'),
    ('TransferSyntaxes/1.2.840.10008.1.2.2.dcm', '1.2.840.10008.1.2.1'),
    ('TransferSyntaxes/1.2.840.10008.1.2.4.51.dcm', '1.2.840.10008.1.2.1'),
    ('TransferSyntaxes/1.2.840.10008.1.2.4.50.dcm', '1.2.840.10008.1.2.1', 'RGB', 'application/octet-stream', 921600),  # We expect YBR to become RGB with transcoding to raw
]))

print('==== TEST 3 ====')
Assert(TestTranscoding({
    'IngestTranscoding' : '1.2.840.10008.1.2.1',
    'IngestTranscodingOfUncompressed' : True,
    'IngestTranscodingOfCompressed' : True,
}, [
    ('TransferSyntaxes/1.2.840.10008.1.2.1.dcm', '1.2.840.10008.1.2.1'),
    ('TransferSyntaxes/1.2.840.10008.1.2.2.dcm', '1.2.840.10008.1.2.1'),
    ('TransferSyntaxes/1.2.840.10008.1.2.4.51.dcm', '1.2.840.10008.1.2.1'),
    ('TransferSyntaxes/1.2.840.10008.1.2.4.50.dcm', '1.2.840.10008.1.2.1', 'RGB'),  # We expect YBR to become RGB with transcoding to raw
]))

print('==== TEST 4 ====')
Assert(TestTranscoding({
    'IngestTranscoding' : '1.2.840.10008.1.2.1',
    'IngestTranscodingOfUncompressed' : True,
    'IngestTranscodingOfCompressed' : False,
}, [
    ('TransferSyntaxes/1.2.840.10008.1.2.1.dcm', '1.2.840.10008.1.2.1'),
    ('TransferSyntaxes/1.2.840.10008.1.2.2.dcm', '1.2.840.10008.1.2.1'),
    ('TransferSyntaxes/1.2.840.10008.1.2.4.51.dcm', '1.2.840.10008.1.2.4.51'),
    ('TransferSyntaxes/1.2.840.10008.1.2.4.50.dcm', '1.2.840.10008.1.2.4.50', 'YBR_FULL_422'),
]))

print('==== TEST 5 ====')
Assert(TestTranscoding({
    'IngestTranscoding' : '1.2.840.10008.1.2.1',
    'IngestTranscodingOfUncompressed' : False,
    'IngestTranscodingOfCompressed' : True,
}, [
    ('TransferSyntaxes/1.2.840.10008.1.2.1.dcm', '1.2.840.10008.1.2.1'),
    ('TransferSyntaxes/1.2.840.10008.1.2.2.dcm', '1.2.840.10008.1.2.2'),
    ('TransferSyntaxes/1.2.840.10008.1.2.4.51.dcm', '1.2.840.10008.1.2.1'),
    ('TransferSyntaxes/1.2.840.10008.1.2.4.50.dcm', '1.2.840.10008.1.2.1', 'RGB'),  # We expect YBR to become RGB with transcoding to raw
]))

print('==== TEST 6 ====')
Assert(TestTranscoding({
    'IngestTranscoding' : '1.2.840.10008.1.2.1',
    'IngestTranscodingOfUncompressed' : False,
    'IngestTranscodingOfCompressed' : False,
}, [
    ('TransferSyntaxes/1.2.840.10008.1.2.1.dcm', '1.2.840.10008.1.2.1'),
    ('TransferSyntaxes/1.2.840.10008.1.2.2.dcm', '1.2.840.10008.1.2.2'),
    ('TransferSyntaxes/1.2.840.10008.1.2.4.51.dcm', '1.2.840.10008.1.2.4.51'),
    ('TransferSyntaxes/1.2.840.10008.1.2.4.50.dcm', '1.2.840.10008.1.2.4.50', 'YBR_FULL_422'),
]))

print('==== TEST 7 ====')
Assert(TestTranscoding({
    'IngestTranscoding' : '1.2.840.10008.1.2.4.51',
    'IngestTranscodingOfUncompressed' : True,
    'IngestTranscodingOfCompressed' : True,
}, [
    ('TransferSyntaxes/1.2.840.10008.1.2.1.dcm', '1.2.840.10008.1.2.4.51'),
    ('TransferSyntaxes/1.2.840.10008.1.2.4.51.dcm', '1.2.840.10008.1.2.4.51'),
    ('TransferSyntaxes/1.2.840.10008.1.2.4.57.dcm', '1.2.840.10008.1.2.4.51'),
    ('TransferSyntaxes/1.2.840.10008.1.2.4.50.dcm', '1.2.840.10008.1.2.4.51', 'YBR_FULL_422'),
]))

print('==== TEST 8 ====')
Assert(TestTranscoding({
    'IngestTranscoding' : '1.2.840.10008.1.2.4.51',
    'IngestTranscodingOfUncompressed' : True,
    'IngestTranscodingOfCompressed' : False,
}, [
    ('TransferSyntaxes/1.2.840.10008.1.2.1.dcm', '1.2.840.10008.1.2.4.51'),
    ('TransferSyntaxes/1.2.840.10008.1.2.4.51.dcm', '1.2.840.10008.1.2.4.51'),
    ('TransferSyntaxes/1.2.840.10008.1.2.4.57.dcm', '1.2.840.10008.1.2.4.57'),
    ('TransferSyntaxes/1.2.840.10008.1.2.4.50.dcm', '1.2.840.10008.1.2.4.50', 'YBR_FULL_422'),
]))

print('==== TEST 9 ====')
Assert(TestTranscoding({
    'IngestTranscoding' : '1.2.840.10008.1.2.4.51',
    'IngestTranscodingOfUncompressed' : False,
    'IngestTranscodingOfCompressed' : True,
}, [
    ('TransferSyntaxes/1.2.840.10008.1.2.1.dcm', '1.2.840.10008.1.2.1'),
    ('TransferSyntaxes/1.2.840.10008.1.2.4.51.dcm', '1.2.840.10008.1.2.4.51'),
    ('TransferSyntaxes/1.2.840.10008.1.2.4.57.dcm', '1.2.840.10008.1.2.4.51'),
    ('TransferSyntaxes/1.2.840.10008.1.2.4.50.dcm', '1.2.840.10008.1.2.4.51', 'YBR_FULL_422'),
]))

print('==== TEST 10 ====')
Assert(TestTranscoding({
    'IngestTranscoding' : '1.2.840.10008.1.2.4.51',
    'IngestTranscodingOfUncompressed' : False,
    'IngestTranscodingOfCompressed' : False,
}, [
    ('TransferSyntaxes/1.2.840.10008.1.2.1.dcm', '1.2.840.10008.1.2.1'),
    ('TransferSyntaxes/1.2.840.10008.1.2.4.51.dcm', '1.2.840.10008.1.2.4.51'),
    ('TransferSyntaxes/1.2.840.10008.1.2.4.57.dcm', '1.2.840.10008.1.2.4.57'),
    ('TransferSyntaxes/1.2.840.10008.1.2.4.50.dcm', '1.2.840.10008.1.2.4.50', 'YBR_FULL_422'),
]))


print('Success!')
