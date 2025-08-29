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


import Toolbox
import json
import os
import subprocess
import sys
import time
import zipfile
import multiprocessing
import threading
import queue


if len(sys.argv) != 3:
    print('Must provide a path to Orthanc binaries and to a sample ZIP archive with one DICOM study')
    exit(-1)

if not os.path.isfile(sys.argv[1]):
    raise Exception('Inexistent path: %s' % sys.argv[1])
    
if not os.path.isfile(sys.argv[2]):
    raise Exception('Inexistent path: %s' % sys.argv[2])
    

TMP = '/tmp/OrthancTest'
CONFIG = os.path.join(TMP, 'Configuration.json')

if os.path.exists(TMP):
    print('Temporary path already exists: %s' % TMP)
    exit(-1)

os.mkdir(TMP)


ORTHANC = Toolbox.DefineOrthanc(username = 'orthanc',
                                password = 'orthanc')


def GetArchive(config, testFunction):
    with open(CONFIG, 'w') as f:
        f.write(json.dumps(config))
    
    process = subprocess.Popen(
        [ sys.argv[1], CONFIG, '--no-jobs' ],
        cwd = TMP,
        #stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE, 
        #shell=True
        )

    #time.sleep(1)

    while True:
        try:
            system = Toolbox.DoGet(ORTHANC, '/system')
            break
        except:
            time.sleep(0.1)

    try:
        with open(sys.argv[2], 'rb') as f:
            Toolbox.DoPost(ORTHANC, '/instances', f.read())

        studies = Toolbox.DoGet(ORTHANC, '/studies')
        if len(studies) != 1:
            raise Exception('More than one study is available in Orthanc')

        testFunction(ORTHANC, studies[0])

    finally:
        process.terminate()
        process.wait()


def Assert(b):
    if not b:
        raise Exception('Bad result')


for streaming in [ False, True, None ]:
    if streaming == True:
        suffix = 'with streaming'
        config = { 'SynchronousZipStream' : True }
    elif streaming == False:
        suffix = 'without streaming'
        config = { 'SynchronousZipStream' : False }
    else:
        suffix = 'default streaming'
        config = { }


    print('==== SIMPLE TEST - %s ====' % suffix)
    def test(ORTHANC, study):
        instances = Toolbox.DoGet(ORTHANC, '/instances')
        z = Toolbox.ParseArchive(Toolbox.DoGet(ORTHANC, '/studies/%s/archive' % study))
        Assert(len(instances) == len(z.namelist()))   

    GetArchive(config, test)


    print('==== CANCEL SERVER JOB - %s ====' % suffix)
    def TestCancelServerJob(ORTHANC, study):
        def CheckCorruptedArchive(queue):
            try:
                z = Toolbox.DoGet(ORTHANC, '/studies/%s/archive' % study)
                Assert(streaming == True or streaming == None)

                try:
                    #if (sys.version_info >= (3, 0)):
                    #    z = bytearray(z, 'utf-8')
                    Toolbox.ParseArchive(z)
                    print('error, got valid archive')
                    queue.put(False)  # The archive is not corrupted as expected
                except zipfile.BadZipfile as e:
                    print('ok, got corrupted archive')
                    queue.put(True)

            except Exception as e:
                Assert(streaming == False)
                Assert(e.args[0] == 500)  # HTTP status code 500
                print('ok, got none archive')
                queue.put(True)

        def cancel():
            while True:
                j = Toolbox.DoGet(ORTHANC, '/jobs?expand')
                Assert(len(j) <= 1)
                if len(j) == 1:
                    Assert(j[0]['State'] == 'Running')
                    Toolbox.DoPost(ORTHANC, '/jobs/%s/cancel' % j[0]['ID'], {})
                    return
                time.sleep(.01)

        q = queue.Queue()
        t1 = threading.Thread(target=cancel)
        t2 = threading.Thread(target=CheckCorruptedArchive, args=(q,))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        Assert(q.get() == True)

    GetArchive(config, TestCancelServerJob)


    print('==== CANCEL HTTP CLIENT - %s ====' % suffix)
    def TestCancelHttpClient(ORTHANC, study):
        def DownloadArchive(queue):
            z = Toolbox.DoGet(ORTHANC, '/studies/%s/archive' % study)
            queue.put('success')

        q = multiprocessing.Queue()
        p = multiprocessing.Process(target=DownloadArchive, args=(q, ))
        p.start()
        time.sleep(0.05)
        p.terminate()
        p.join()
        Assert(q.qsize() == 0)

        while True:
            j = Toolbox.DoGet(ORTHANC, '/jobs?expand')
            Assert(len(j) == 1)
            if j[0]['State'] == 'Running':
                continue
            else:
                if streaming == False:
                    # The sending of the temporary file is *not* part
                    # of the job in this case
                    Assert(j[0]['State'] == 'Success')
                else:
                    Assert(j[0]['State'] == 'Failure')
                    Assert(j[0]['ErrorCode'] == 14)  # Cannot write to file
                break
        
    GetArchive(config, TestCancelHttpClient)
        

print('Success!')
