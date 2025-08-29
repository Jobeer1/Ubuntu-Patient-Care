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


if len(sys.argv) < 2:
    print('Must provide a path to Orthanc binaries')
    exit(-1)


TMP = '/tmp/OrthancTest'
TMP_ORTHANC = os.path.join(TMP, 'orthanc')
TMP_STORESCP = os.path.join(TMP, 'storescp')

CONFIG = os.path.join(TMP, 'orthanc', 'Configuration.json')
ORTHANC = Toolbox.DefineOrthanc()

if os.path.exists(TMP):
    print('Temporary path already exists: %s' % TMP)
    exit(-1)

os.mkdir(TMP)
os.mkdir(TMP_ORTHANC)
os.mkdir(TMP_STORESCP)


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
            # Orthanc is still in its startup process, wait for it to
            # become available
            time.sleep(0.05)


def CreateStorescpConfiguration(acceptedSyntaxes):
    with open(os.path.join(TMP_STORESCP, 'config'), 'w') as f:
        f.write('[[TransferSyntaxes]]\n')

        f.write('[Accepted]\n')
        for i in range(len(acceptedSyntaxes)):
            f.write('TransferSyntax%d = %s\n' % (i + 1, acceptedSyntaxes[i]))

        f.write('[[PresentationContexts]]\n')
        f.write('[StorageSCP]\n')

        # These strings correspond to the SOP class UIDs of the DICOM
        # instances in folder "../Database/TransferSyntaxes/"
        SOP_CLASS_UIDS = [
            '1.2.840.10008.5.1.4.1.1.2',
            '1.2.840.10008.5.1.4.1.1.4',
            '1.2.840.10008.5.1.4.1.1.6',
            '1.2.840.10008.5.1.4.1.1.6.1',
            '1.2.840.10008.5.1.4.1.1.7',
        ]
        
        for i in range(len(SOP_CLASS_UIDS)):
            f.write('PresentationContext%d = %s\\Accepted\n' % (i + 1, SOP_CLASS_UIDS[i]))

        f.write('[[Profiles]]\n')
        f.write('[Default]\n')
        f.write('PresentationContexts = StorageSCP\n')
            

def TestStore(config, storescpArgs, tests):
    config['DicomModalities'] = {
        'storescp' : [ 'STORESCP', 'localhost', 2000 ]
    }
    
    with open(CONFIG, 'w') as f:
        f.write(json.dumps(config))

    FNULL = open(os.devnull, 'w')  # Emulates "subprocess.DEVNULL" on Python 2.7
    process1 = subprocess.Popen(
        sys.argv[1:] + [ CONFIG, '--no-jobs' ], #, '--trace-dicom' ],
        cwd = TMP_ORTHANC,
        #stdout=FNULL, 
        stderr=FNULL,
        #shell=True
        )

    process2 = subprocess.Popen(
        [ 'storescp', '-p', '2000' ] + storescpArgs,
        cwd = TMP_STORESCP,
        #stdout=FNULL, 
        #stderr=FNULL, 
        #shell=True
        )

    success = True

    try:
        for test in tests:
            DropOrthanc()
            for f in os.listdir(TMP_STORESCP):
                os.remove(os.path.join(TMP_STORESCP, f))

            i = Toolbox.UploadInstance(ORTHANC, test[0]) ['ID']       
            
            try:
                Toolbox.DoPost(ORTHANC, '/modalities/storescp/store', {
                    'Resources' : [ i ],
                    'Synchronous' : True,
                })
            except:
                if test[1] != None:
                    print('INTERNAL ERROR on: %s' % test[0])
                    success = False
                    continue

            f = os.listdir(TMP_STORESCP)
            if len(f) > 1:
                print('INTERNAL ERROR')
                success = False
            elif len(f) == 0:
                if test[1] != None:
                    print('No file was received by storescp! %s' % test[0])
                    success = False
            else:
                if test[1] == None:
                    print('No file should have been received by storescp! %s' % test[0])
                    success = False
                else:
                    with open(os.path.join(TMP_STORESCP, f[0]), 'rb') as f:
                        ts = Toolbox.GetTransferSyntax(f.read())

                    if ts != test[1]:
                        print('TRANSFER SYNTAX MISMATCH: observed %s vs. expected %s' % (ts, test[1]))
                        success = False
                
    except Exception as e:
        print('EXCEPTION: %s' % e)
        success = False

    process1.terminate()
    process2.terminate()
    
    process1.wait()
    process2.wait()

    return success


def Assert(b):
    if not b:
        raise Exception('Bad result')



##
## Each test specifies: The input DICOM instance, and the expected
## transfer syntax as received by storescp
##


print('==== TEST 1 ====')
Assert(TestStore(
    {
        'DicomScuPreferredTransferSyntax' : '1.2.840.10008.1.2.1',  # Little Endian Explicit
    },
    [ '+xa' ],  # storescp accepts any transfer syntax
                # (DicomScuPreferredTransferSyntax has no effect)
    [
        ('TransferSyntaxes/1.2.840.10008.1.2.dcm', '1.2.840.10008.1.2'),
        ('TransferSyntaxes/1.2.840.10008.1.2.1.dcm', '1.2.840.10008.1.2.1'),
        ('TransferSyntaxes/1.2.840.10008.1.2.2.dcm', '1.2.840.10008.1.2.2'),
        ('TransferSyntaxes/1.2.840.10008.1.2.4.51.dcm', '1.2.840.10008.1.2.4.51'),
        ('TransferSyntaxes/1.2.840.10008.1.2.4.70.dcm', '1.2.840.10008.1.2.4.70'),
    ]))


print('==== TEST 2 ====')
Assert(TestStore(
    {
        'DicomScuPreferredTransferSyntax' : '1.2.840.10008.1.2.2',  # Big Endian
    },
    [ '+xa' ],  # storescp accepts any transfer syntax
                # (DicomScuPreferredTransferSyntax has no effect)
    [
        ('TransferSyntaxes/1.2.840.10008.1.2.dcm', '1.2.840.10008.1.2'),
        ('TransferSyntaxes/1.2.840.10008.1.2.1.dcm', '1.2.840.10008.1.2.1'),
        ('TransferSyntaxes/1.2.840.10008.1.2.2.dcm', '1.2.840.10008.1.2.2'),
        ('TransferSyntaxes/1.2.840.10008.1.2.4.51.dcm', '1.2.840.10008.1.2.4.51'),
        ('TransferSyntaxes/1.2.840.10008.1.2.4.70.dcm', '1.2.840.10008.1.2.4.70'),
    ]))


print('==== TEST 3 ====')
Assert(TestStore(
    {
        'DicomScuPreferredTransferSyntax' : '1.2.840.10008.1.2.4.70',  # JPEG baseline 12bpp
    },
    [ '+xa' ],  # storescp accepts any transfer syntax
                # (DicomScuPreferredTransferSyntax has no effect)
    [
        ('TransferSyntaxes/1.2.840.10008.1.2.dcm', '1.2.840.10008.1.2'),
        ('TransferSyntaxes/1.2.840.10008.1.2.1.dcm', '1.2.840.10008.1.2.1'),
        ('TransferSyntaxes/1.2.840.10008.1.2.2.dcm', '1.2.840.10008.1.2.2'),
        ('TransferSyntaxes/1.2.840.10008.1.2.4.51.dcm', '1.2.840.10008.1.2.4.51'),
        ('TransferSyntaxes/1.2.840.10008.1.2.4.70.dcm', '1.2.840.10008.1.2.4.70'),
    ]))


print('==== TEST 4 ====')
Assert(TestStore(
    {
        'DicomScuPreferredTransferSyntax' : '1.2.840.10008.1.2.1',  # Little Endian Explicit
    },
    [ ],  # storescp only accepts uncompressed transfer syntaxes
    [
        ('TransferSyntaxes/1.2.840.10008.1.2.dcm', '1.2.840.10008.1.2'),
        ('TransferSyntaxes/1.2.840.10008.1.2.1.dcm', '1.2.840.10008.1.2.1'),
        ('TransferSyntaxes/1.2.840.10008.1.2.2.dcm', '1.2.840.10008.1.2.2'),
        ('TransferSyntaxes/1.2.840.10008.1.2.4.51.dcm', '1.2.840.10008.1.2.1'),
        ('TransferSyntaxes/1.2.840.10008.1.2.4.70.dcm', '1.2.840.10008.1.2.1'),
    ]))


print('==== TEST 5 ====')
Assert(TestStore(
    {
        # Defaults to "1.2.840.10008.1.2.1", Little Endian Explicit
        # (was Little Endian Implicit in Orthanc between 1.7.0 and 1.8.2)
    },
    [ ],  # storescp only accepts uncompressed transfer syntaxes
    [
        ('TransferSyntaxes/1.2.840.10008.1.2.dcm', '1.2.840.10008.1.2'),
        ('TransferSyntaxes/1.2.840.10008.1.2.1.dcm', '1.2.840.10008.1.2.1'),
        ('TransferSyntaxes/1.2.840.10008.1.2.2.dcm', '1.2.840.10008.1.2.2'),
        ('TransferSyntaxes/1.2.840.10008.1.2.4.51.dcm', '1.2.840.10008.1.2.1'),
        ('TransferSyntaxes/1.2.840.10008.1.2.4.70.dcm', '1.2.840.10008.1.2.1'),
    ]))


print('==== TEST 6 ====')
Assert(TestStore(
    {
        'DicomScuPreferredTransferSyntax' : '1.2.840.10008.1.2',  # Little Endian Implicit
    },
    [ ],  # storescp only accepts uncompressed transfer syntaxes
    [
        ('TransferSyntaxes/1.2.840.10008.1.2.dcm', '1.2.840.10008.1.2'),
        ('TransferSyntaxes/1.2.840.10008.1.2.1.dcm', '1.2.840.10008.1.2.1'),
        ('TransferSyntaxes/1.2.840.10008.1.2.2.dcm', '1.2.840.10008.1.2.2'),
        ('TransferSyntaxes/1.2.840.10008.1.2.4.51.dcm', '1.2.840.10008.1.2'),
        ('TransferSyntaxes/1.2.840.10008.1.2.4.70.dcm', '1.2.840.10008.1.2'),
    ]))


print('==== TEST 7 ====')
Assert(TestStore(
    {
        'DicomScuPreferredTransferSyntax' : '1.2.840.10008.1.2.2',  # Big Endian
    },
    [ ],  # storescp only accepts uncompressed transfer syntaxes
    [
        ('TransferSyntaxes/1.2.840.10008.1.2.dcm', '1.2.840.10008.1.2'),
        ('TransferSyntaxes/1.2.840.10008.1.2.1.dcm', '1.2.840.10008.1.2.1'),
        ('TransferSyntaxes/1.2.840.10008.1.2.2.dcm', '1.2.840.10008.1.2.2'),
        ('TransferSyntaxes/1.2.840.10008.1.2.4.51.dcm', '1.2.840.10008.1.2.2'),
        ('TransferSyntaxes/1.2.840.10008.1.2.4.70.dcm', '1.2.840.10008.1.2.2'),
    ]))


print('==== TEST 8 ====')
Assert(TestStore(
    {
        'DicomScuPreferredTransferSyntax' : '1.2.840.10008.1.2.4.70'
    },
    [ ],  # storescp only accepts uncompressed transfer syntaxes,
          # Little Endian Explicit will be chosed by Orthanc (was
          # Little Endian Implicit in Orthanc between 1.7.0 and 1.8.2)
    [
        ('TransferSyntaxes/1.2.840.10008.1.2.dcm', '1.2.840.10008.1.2'),
        ('TransferSyntaxes/1.2.840.10008.1.2.1.dcm', '1.2.840.10008.1.2.1'),
        ('TransferSyntaxes/1.2.840.10008.1.2.2.dcm', '1.2.840.10008.1.2.2'),
        ('TransferSyntaxes/1.2.840.10008.1.2.4.51.dcm', '1.2.840.10008.1.2.1'),
        ('TransferSyntaxes/1.2.840.10008.1.2.4.70.dcm', '1.2.840.10008.1.2.1'),
    ]))


print('==== TEST 9 ====')
Assert(TestStore(
    {
        'DicomScuPreferredTransferSyntax' : '1.2.840.10008.1.2.4.70'
    },
    [ '+xi' ],  # storescp only accepts Little Endian Implicit (1.2.840.10008.1.2)
    [
        ('TransferSyntaxes/1.2.840.10008.1.2.dcm', '1.2.840.10008.1.2'),
        ('TransferSyntaxes/1.2.840.10008.1.2.1.dcm', '1.2.840.10008.1.2'),
        ('TransferSyntaxes/1.2.840.10008.1.2.2.dcm', '1.2.840.10008.1.2'),
        ('TransferSyntaxes/1.2.840.10008.1.2.4.51.dcm', '1.2.840.10008.1.2'),
        ('TransferSyntaxes/1.2.840.10008.1.2.4.70.dcm', '1.2.840.10008.1.2'),
    ]))


print('==== TEST 10 ====')
CreateStorescpConfiguration([
    '1.2.840.10008.1.2.4.70',
])
Assert(TestStore(
    {
        'DicomScuPreferredTransferSyntax' : '1.2.840.10008.1.2.4.70'
    },
    [ '-xf', 'config', 'Default' ],  # storescp only accepts "1.2.840.10008.1.2.4.70"
    [
        ('TransferSyntaxes/1.2.840.10008.1.2.dcm', '1.2.840.10008.1.2.4.70'),
        ('TransferSyntaxes/1.2.840.10008.1.2.1.dcm', '1.2.840.10008.1.2.4.70'),
        ('TransferSyntaxes/1.2.840.10008.1.2.2.dcm', '1.2.840.10008.1.2.4.70'),
        ('TransferSyntaxes/1.2.840.10008.1.2.4.51.dcm', '1.2.840.10008.1.2.4.70'),
        ('TransferSyntaxes/1.2.840.10008.1.2.4.70.dcm', '1.2.840.10008.1.2.4.70'),
    ]))


print('==== TEST 11 ====')
CreateStorescpConfiguration([
    '1.2.840.10008.1.2.4.57',
])
Assert(TestStore(
    {
        'DicomScuPreferredTransferSyntax' : '1.2.840.10008.1.2.4.70'
    },
    [ '-xf', 'config', 'Default' ],
    [
        ('TransferSyntaxes/1.2.840.10008.1.2.4.57.dcm', '1.2.840.10008.1.2.4.57'),

        # All the transfers below will be rejected by storescp
        ('TransferSyntaxes/1.2.840.10008.1.2.dcm', None),
        ('TransferSyntaxes/1.2.840.10008.1.2.1.dcm', None),
        ('TransferSyntaxes/1.2.840.10008.1.2.2.dcm', None),
        ('TransferSyntaxes/1.2.840.10008.1.2.4.51.dcm', None),
        ('TransferSyntaxes/1.2.840.10008.1.2.4.70.dcm', None),
    ]))


print('==== TEST 12 ====')
CreateStorescpConfiguration([
    '1.2.840.10008.1.2.4.70',
    '1.2.840.10008.1.2.1',
])
Assert(TestStore(
    {
        'DicomScuPreferredTransferSyntax' : '1.2.840.10008.1.2.4.70'
    },
    [ '-xf', 'config', 'Default' ],
    [
        ('TransferSyntaxes/1.2.840.10008.1.2.dcm', '1.2.840.10008.1.2.4.70'),
        ('TransferSyntaxes/1.2.840.10008.1.2.1.dcm', '1.2.840.10008.1.2.1'),
        ('TransferSyntaxes/1.2.840.10008.1.2.2.dcm', '1.2.840.10008.1.2.4.70'),
        ('TransferSyntaxes/1.2.840.10008.1.2.4.51.dcm', '1.2.840.10008.1.2.4.70'),
        ('TransferSyntaxes/1.2.840.10008.1.2.4.70.dcm', '1.2.840.10008.1.2.4.70'),
    ]))


print('==== TEST 13 ====')
CreateStorescpConfiguration([
    '1.2.840.10008.1.2.4.90',
    '1.2.840.10008.1.2.1',
])
Assert(TestStore(
    {
        # The built-in DCMTK transcoder of Orthanc cannot transcode to
        # JPEG2k, so the fallback "1.2.840.10008.1.2.1" transfer
        # syntax will be used if transcoding is needed
        'DicomScuPreferredTransferSyntax' : '1.2.840.10008.1.2.4.90'
    },
    [ '-xf', 'config', 'Default' ],
    [
        ('TransferSyntaxes/1.2.840.10008.1.2.dcm', '1.2.840.10008.1.2.1'),
        ('TransferSyntaxes/1.2.840.10008.1.2.1.dcm', '1.2.840.10008.1.2.1'),
        ('TransferSyntaxes/1.2.840.10008.1.2.2.dcm', '1.2.840.10008.1.2.1'),
        ('TransferSyntaxes/1.2.840.10008.1.2.4.51.dcm', '1.2.840.10008.1.2.1'),
        ('TransferSyntaxes/1.2.840.10008.1.2.4.90.dcm', '1.2.840.10008.1.2.4.90'),
    ]))


print('Success!')
