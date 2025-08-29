#!/usr/bin/python3
# -*- coding: utf-8 -*-


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



# You must add the following to the configuration file:
#
#  "DicomWeb" : {
#    "Servers" : {
#      "sample" : [ "http://localhost:8042/dicom-web/", "alice", "orthanctest" ]
#    }
#  }



import argparse
import copy
import os
import pprint
import pydicom
import re
import sys
import unittest
import xml.dom.minidom
import time
from PIL import ImageChops
from io import BytesIO
from DicomWeb import *

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'Tests'))
from Toolbox import *


##
## Parse the command-line arguments
##

parser = argparse.ArgumentParser(description = 'Run the integration tests for the DICOMweb plugin.')

parser.add_argument('--server', 
                    default = 'localhost',
                    help = 'Address of the Orthanc server to test')
parser.add_argument('--rest',
                    type = int,
                    default = 8042,
                    help = 'Port to the REST API')
parser.add_argument('--username',
                    default = 'alice',
                    help = 'Username to the REST API')
parser.add_argument('--password',
                    default = 'orthanctest',
                    help = 'Password to the REST API')
parser.add_argument('--wado',
                    default = '/wado',
                    help = 'Path to the WADO API')
parser.add_argument('--dicomweb',
                    default = '/dicom-web/',
                    help = 'Path to the DICOMweb API')
parser.add_argument('--force', help = 'Do not warn the user',
                    action = 'store_true')
parser.add_argument('options', metavar = 'N', nargs = '*',
                    help='Arguments to Python unittest')

args = parser.parse_args()


##
## Configure the testing context
##

if not args.force:
    print("""
WARNING: This test will remove all the content of your
Orthanc instance running on %s!

Are you sure ["yes" to go on]?""" % args.server)

    if sys.stdin.readline().strip() != 'yes':
        print('Aborting...')
        exit(0)


ORTHANC = DefineOrthanc(server = args.server,
                        username = args.username,
                        password = args.password,
                        restPort = args.rest)


##
## The tests
##


def UploadAndGetWadoPath(dicom):
    i = UploadInstance(ORTHANC, dicom) ['ID']
    study = DoGet(ORTHANC, '/instances/%s/tags?simplify' % i) ['StudyInstanceUID']
    series = DoGet(ORTHANC, '/instances/%s/tags?simplify' % i) ['SeriesInstanceUID']
    instance = DoGet(ORTHANC, '/instances/%s/tags?simplify' % i) ['SOPInstanceUID']
    return '/studies/%s/series/%s/instances/%s' % (study, series, instance)
    


class Orthanc(unittest.TestCase):
    def setUp(self):
        if (sys.version_info >= (3, 0)):
            # Remove annoying warnings about unclosed socket in Python 3
            import warnings
            warnings.simplefilter("ignore", ResourceWarning)

        #print("In test: ", self._testMethodName)
            
        DropOrthanc(ORTHANC)

    def test_wado_dicom(self):
        UploadInstance(ORTHANC, 'Brainix/Flair/IM-0001-0001.dcm')

        SIZE = 169478
        INSTANCE = '1.3.46.670589.11.0.0.11.4.2.0.8743.5.5396.2006120114314079549'
        SERIES = '1.3.46.670589.11.0.0.11.4.2.0.8743.5.5396.2006120114285654497'
        STUDY = '2.16.840.1.113669.632.20.1211.10000357775'

        self.assertRaises(Exception, lambda: DoGet(ORTHANC, args.wado))
        self.assertRaises(Exception, lambda: DoGet(ORTHANC, args.wado + '?requestType=WADO'))
        self.assertRaises(Exception, lambda: DoGet(ORTHANC, args.wado + '?objectUID=%s' % INSTANCE))

        dicom = DoGet(ORTHANC, args.wado + '?contentType=application/dicom&requestType=WADO&objectUID=%s' % INSTANCE)
        self.assertEqual(SIZE, len(dicom))

        dicom = DoGet(ORTHANC, args.wado + '?contentType=application/dicom&requestType=WADO&objectUID=%s&seriesUID=%s' % (INSTANCE, SERIES))
        self.assertEqual(SIZE, len(dicom))

        dicom = DoGet(ORTHANC, args.wado + '?contentType=application/dicom&requestType=WADO&objectUID=%s&seriesUID=%s&studyUID=%s' % (INSTANCE, SERIES, STUDY))
        self.assertEqual(SIZE, len(dicom))

        dicom = DoGet(ORTHANC, args.wado + '?contentType=application/dicom&requestType=WADO&objectUID=%s&seriesUID=%s' % (INSTANCE, SERIES))
        self.assertEqual(SIZE, len(dicom))

        dicom = DoGet(ORTHANC, args.wado + '?contentType=application/dicom&requestType=WADO&objectUID=%s&studyUID=%s' % (INSTANCE, STUDY))
        self.assertEqual(SIZE, len(dicom))

        self.assertRaises(Exception, lambda: DoGet(ORTHANC, args.wado + '?requestType=WADO&objectUID=%s&seriesUID=nope' % INSTANCE))
        self.assertRaises(Exception, lambda: DoGet(ORTHANC, args.wado + '?requestType=WADO&objectUID=%s&studyUID=nope' % INSTANCE))
        self.assertRaises(Exception, lambda: DoGet(ORTHANC, args.wado + '?requestType=WADO&objectUID=%s&seriesUID=nope&studyUID=nope' % INSTANCE))

    def test_wado_image(self):
        UploadInstance(ORTHANC, 'Phenix/IM-0001-0001.dcm')
        INSTANCE = '1.2.840.113704.7.1.1.6632.1127829031.2'

        im = GetImage(ORTHANC, args.wado + '?requestType=WADO&objectUID=%s' % INSTANCE)
        self.assertEqual('JPEG', im.format)
        self.assertEqual('L', im.mode)
        self.assertEqual(512, im.size[0])
        self.assertEqual(358, im.size[1])

        im = GetImage(ORTHANC, args.wado + '?contentType=image/jpg&requestType=WADO&objectUID=%s' % INSTANCE)
        self.assertEqual('JPEG', im.format)

        im = GetImage(ORTHANC, args.wado + '?contentType=image/png&requestType=WADO&objectUID=%s' % INSTANCE)
        self.assertEqual('PNG', im.format)
        self.assertEqual('L', im.mode)
        self.assertEqual(512, im.size[0])
        self.assertEqual(358, im.size[1])

    def test_stow(self):
        self.assertEqual(0, len(DoGet(ORTHANC, '/instances')))
        SendStow(ORTHANC, args.dicomweb + '/studies', GetDatabasePath('Phenix/IM-0001-0001.dcm'))
        self.assertEqual(1, len(DoGet(ORTHANC, '/instances')))
        a = SendStow(ORTHANC, args.dicomweb + '/studies', GetDatabasePath('Phenix/IM-0001-0001.dcm'))
        self.assertEqual(1, len(DoGet(ORTHANC, '/instances')))

        if IsPluginVersionAtLeast(ORTHANC, "dicom-web", 1, 19, 0):
            self.assertEqual(3, len(a))  # DICOM_TAG_FAILED_SOP_SEQUENCE has been removed in 1.19
        else:
            self.assertEqual(4, len(a))

        # Specific character set
        self.assertTrue('00080005' in a)
        self.assertEqual('CS', a['00080005']['vr'])

        self.assertTrue(a['00081190']['Value'][0].endswith('studies/2.16.840.1.113669.632.20.1211.10000098591'))
        self.assertEqual('UR', a['00081190']['vr'])
        
        if IsPluginVersionAtLeast(ORTHANC, "dicom-web", 1, 19, 0):
            self.assertNotIn('00081198', a)  # No errors => the DICOM_TAG_FAILED_SOP_SEQUENCE shall not be present
        else:
            self.assertFalse('Value' in a['00081198'])  # No error => empty sequence
            self.assertEqual('SQ', a['00081198']['vr'])

        self.assertEqual(1, len(a['00081199']['Value']))  # 1 success
        self.assertEqual('SQ', a['00081199']['vr'])

        b = a['00081199']['Value'][0]

        # Referenced SOP class UID
        self.assertEqual('UI', b['00081150']['vr'])
        self.assertEqual(1, len(b['00081150']['Value']))
        self.assertEqual('1.2.840.10008.5.1.4.1.1.2', b['00081150']['Value'][0])

        # Referenced SOP instance UID
        self.assertEqual('UI', b['00081155']['vr'])
        self.assertEqual(1, len(b['00081155']['Value']))
        self.assertEqual('1.2.840.113704.7.1.1.6632.1127829031.2', b['00081155']['Value'][0])

        # Retrieve URL
        self.assertEqual('UR', b['00081190']['vr'])
        self.assertEqual(1, len(b['00081190']['Value']))
        self.assertTrue(b['00081190']['Value'][0].
                        endswith('series/1.2.840.113704.1.111.5692.1127828999.2/instances/1.2.840.113704.7.1.1.6632.1127829031.2'))

        # Remove the "http://localhost:8042" prefix
        url = a['00081190']['Value'][0]
        url = re.sub(r'(http|https)://[^/]+(/.*)', r'\2', url)

        # Get the content-length of all the multiparts of this WADO-RS
        # request (prevent transcoding by setting transfer-syntax to
        # "*", necessary since release 1.5 of the DICOMweb plugin)
        b = DoGet(ORTHANC, url, headers = {
            'Accept' : 'multipart/related;type=application/dicom;transfer-syntax=*'
        }).decode('utf-8', 'ignore')
        parts = re.findall(r'^Content-Length:\s*(\d+)\s*', b, re.IGNORECASE | re.MULTILINE)
        self.assertEqual(1, len(parts))
        self.assertEqual(os.path.getsize(GetDatabasePath('Phenix/IM-0001-0001.dcm')), int(parts[0]))

    def test_stow_like_dcm4chee(self):
        # https://discourse.orthanc-server.org/t/orthanc-dicomweb-stowrs-server-request-response-compatibility/5763

        self.assertEqual(0, len(DoGet(ORTHANC, '/instances')))
        a = SendStow(ORTHANC, args.dicomweb + '/studies', GetDatabasePath('Phenix/IM-0001-0001.dcm'), 'application/dicom;transfer-syntax=1.2.840.10008.1.2.1')
        self.assertEqual(1, len(DoGet(ORTHANC, '/instances')))

        self.assertNotIn('00081198', a)  # No errors => the DICOM_TAG_FAILED_SOP_SEQUENCE shall not be present


        
    def test_server_get(self):
        try:
            DoDelete(ORTHANC, '/dicom-web/servers/google')  # If "AllWindowsStart.sh" is used
        except:
            pass

        try:
            DoDelete(ORTHANC, '/dicom-web/servers/hello')  # If "test_add_server" fails
        except:
            pass

        UploadInstance(ORTHANC, 'Knee/T1/IM-0001-0001.dcm')

        self.assertEqual(1, len(DoGet(ORTHANC, '/dicom-web/servers')))
        self.assertTrue('sample' in DoGet(ORTHANC, '/dicom-web/servers'))

        serversReadback = DoGet(ORTHANC, '/dicom-web/servers?expand')
        self.assertEqual('http://localhost:8042/dicom-web/', serversReadback['sample']['Url'])
        self.assertEqual('alice', serversReadback['sample']['Username'])

        sample = DoGet(ORTHANC, '/dicom-web/servers/sample')
        self.assertEqual(5, len(sample))
        self.assertTrue('stow' in sample)
        self.assertTrue('retrieve' in sample)
        self.assertTrue('get' in sample)
        self.assertTrue('wado' in sample)  # New in 0.7
        self.assertTrue('qido' in sample)  # New in 0.7

        # application/dicom+xml
        self.assertEqual(2, len(re.findall('^--', DoGet(ORTHANC, '/dicom-web/studies',
                                                        headers = { 'Accept' : 'application/dicom+xml' }),
                                           re.MULTILINE)))
        self.assertEqual(2, len(re.findall('^--', DoPost
                                           (ORTHANC, '/dicom-web/servers/sample/get',
                                            { 'Uri' : '/studies',
                                              'HttpHeaders' : { 'Accept' : 'application/dicom+xml' }
                                            }), re.MULTILINE)))

        # application/dicom+json
        self.assertEqual(1, len(DoGet(ORTHANC, '/dicom-web/studies',
                                      headers = { 'Accept' : 'application/dicom+json' })))
        self.assertEqual(1, len(DoPost(ORTHANC, '/dicom-web/servers/sample/get',
                                       { 'Uri' : '/studies',
                                         'HttpHeaders' : { 'Accept' : 'application/dicom+json' }})))

        # application/json
        self.assertEqual(1, len(DoGet(ORTHANC, '/dicom-web/studies',
                                      headers = { 'Accept' : 'application/json' })))
        self.assertEqual(1, len(DoPost(ORTHANC, '/dicom-web/servers/sample/get',
                                       { 'Uri' : '/studies',
                                         'HttpHeaders' : { 'Accept' : 'application/json' }})))

        # application/dicom+json is the default as of OrthancDicomWeb-0.5
        self.assertEqual(1, len(DoGet(ORTHANC, '/dicom-web/studies')))
        self.assertEqual(1, len(DoPost(ORTHANC, '/dicom-web/servers/sample/get',
                                       { 'Uri' : '/studies' })))


    def test_server_stow(self):
        # UploadInstance(ORTHANC, 'Knee/T1/IM-0001-0001.dcm')

        # self.assertRaises(Exception, lambda: 
        #                   DoPost(ORTHANC, '/dicom-web/servers/sample/stow',
        #                          { 'Resources' : [ 'nope' ],
        #                            'Synchronous' : True }))  # inexisting resource

        # if IsPluginVersionAtLeast(ORTHANC, "dicom-web", 1, 18, 0):
        #     l = 4   # "Server" has been added
        # else:
        #     l = 3   # For >= 1.10.1

        # # study
        # r = DoPost(ORTHANC, '/dicom-web/servers/sample/stow',
        #                                { 'Resources' : [ '0a9b3153-2512774b-2d9580de-1fc3dcf6-3bd83918' ],
        #                                  'Synchronous' : True })

        # self.assertEqual(l, len(r))
        # self.assertEqual("0a9b3153-2512774b-2d9580de-1fc3dcf6-3bd83918", r['Resources']['Studies'][0])
        # if IsPluginVersionAtLeast(ORTHANC, "dicom-web", 1, 18, 0):
        #     self.assertEqual("sample", r['Server'])

        # # series
        # r = DoPost(ORTHANC, '/dicom-web/servers/sample/stow',
        #                                { 'Resources' : [ '6de73705-c4e65c1b-9d9ea1b5-cabcd8e7-f15e4285' ],
        #                                  'Synchronous' : True })
        # self.assertEqual(l, len(r))
        # self.assertEqual("6de73705-c4e65c1b-9d9ea1b5-cabcd8e7-f15e4285", r['Resources']['Series'][0])

        # # instances
        # r = DoPost(ORTHANC, '/dicom-web/servers/sample/stow',
        #                                { 'Resources' : [ 'c8df6478-d7794217-0f11c293-a41237c9-31d98357' ],
        #                                  'Synchronous' : True })
        # self.assertEqual(l, len(r))
        # self.assertEqual("c8df6478-d7794217-0f11c293-a41237c9-31d98357", r['Resources']['Instances'][0])

        # # altogether
        # r = DoPost(ORTHANC, '/dicom-web/servers/sample/stow',
        #                                { 'Resources' : [ 
        #                                    'ca29faea-b6a0e17f-067743a1-8b778011-a48b2a17',
        #                                    '0a9b3153-2512774b-2d9580de-1fc3dcf6-3bd83918',
        #                                    '6de73705-c4e65c1b-9d9ea1b5-cabcd8e7-f15e4285',
        #                                    'c8df6478-d7794217-0f11c293-a41237c9-31d98357' ],
        #                                  'Synchronous' : True })
        # # pprint.pprint(r)
        # self.assertEqual(l, len(r))
        # self.assertEqual("ca29faea-b6a0e17f-067743a1-8b778011-a48b2a17", r['Resources']['Patients'][0])
        # self.assertEqual("0a9b3153-2512774b-2d9580de-1fc3dcf6-3bd83918", r['Resources']['Studies'][0])
        # self.assertEqual("6de73705-c4e65c1b-9d9ea1b5-cabcd8e7-f15e4285", r['Resources']['Series'][0])
        # self.assertEqual("c8df6478-d7794217-0f11c293-a41237c9-31d98357", r['Resources']['Instances'][0])


        if IsPluginVersionAtLeast(ORTHANC, "dicom-web", 1, 20, 0):
            a = UploadInstance(ORTHANC, 'Brainix/Epi/IM-0001-0001.dcm')
            b = UploadInstance(ORTHANC, 'Brainix/Epi/IM-0001-0002.dcm')

            # study
            r = DoPost(ORTHANC, '/dicom-web/servers/sample/stow',
                                        { 'Resources' : [ a['ParentStudy'] ],
                                          'Synchronous' : True })

            self.assertEqual(1, len(r['Resources']['Studies']))
            self.assertNotIn('Series', r['Resources'])
            self.assertEqual(2, len(r['Resources']['Instances']))
            self.assertEqual(a['ParentStudy'], r['Resources']['Studies'][0])
            self.assertIn(a['ID'], r['Resources']['Instances'])
            self.assertIn(b['ID'], r['Resources']['Instances'])

            # series
            r = DoPost(ORTHANC, '/dicom-web/servers/sample/stow',
                                        { 'Resources' : [ a['ParentSeries'] ],
                                          'Synchronous' : True })

            self.assertEqual(1, len(r['Resources']['Series']))
            self.assertNotIn('Studies', r['Resources'])
            self.assertEqual(2, len(r['Resources']['Instances']))
            self.assertEqual(a['ParentSeries'], r['Resources']['Series'][0])
            self.assertIn(a['ID'], r['Resources']['Instances'])
            self.assertIn(b['ID'], r['Resources']['Instances'])



    def test_server_retrieve(self):
        COUNT = 'ReceivedInstancesCount'
        #COUNT = 'Instances'  # In version <= 0.6

        UploadInstance(ORTHANC, 'Knee/T1/IM-0001-0001.dcm')
        UploadInstance(ORTHANC, 'Knee/T1/IM-0001-0002.dcm')
        UploadInstance(ORTHANC, 'Knee/T2/IM-0001-0001.dcm')

        self.assertRaises(Exception, lambda: 
                          DoPost(ORTHANC, '/dicom-web/servers/sample/retrieve',
                                 { 'Resources' : [ { 'Study' : 'nope' } ]}))  # inexisting resource

        t = DoPost(ORTHANC, '/dicom-web/servers/sample/retrieve',
                   { 'Resources' : [ { 'Study' : '2.16.840.1.113669.632.20.121711.10000160881' } ] })
        self.assertEqual(3, int(t[COUNT]))

        # Missing "Study" field
        self.assertRaises(Exception, lambda: 
                          DoPost(ORTHANC, '/dicom-web/servers/sample/retrieve',
                                 { 'Resources' : [ { 'Series' : '1.3.46.670589.11.17521.5.0.3124.2008081908564160709' } ]}))

        t = DoPost(ORTHANC, '/dicom-web/servers/sample/retrieve',
                   { 'Resources' : [ { 'Study' : '2.16.840.1.113669.632.20.121711.10000160881',
                                       'Series' : '1.3.46.670589.11.17521.5.0.3124.2008081908564160709' } ] })
        self.assertEqual(2, int(t[COUNT]))

        t = DoPost(ORTHANC, '/dicom-web/servers/sample/retrieve',
                   { 'Resources' : [ { 'Study' : '2.16.840.1.113669.632.20.121711.10000160881',
                                       'Series' : '1.3.46.670589.11.17521.5.0.3124.2008081909090037350' } ] })
        self.assertEqual(1, int(t[COUNT]))

        t = DoPost(ORTHANC, '/dicom-web/servers/sample/retrieve',
                   { 'Resources' : [ { 'Study' : '2.16.840.1.113669.632.20.121711.10000160881',
                                       'Series' : '1.3.46.670589.11.17521.5.0.3124.2008081909090037350' },
                                     { 'Study' : '2.16.840.1.113669.632.20.121711.10000160881',
                                       'Series' : '1.3.46.670589.11.17521.5.0.3124.2008081908564160709' } ] })
        self.assertEqual(3, int(t[COUNT]))

        t = DoPost(ORTHANC, '/dicom-web/servers/sample/retrieve',
                   { 'Resources' : [ { 'Study' : '2.16.840.1.113669.632.20.121711.10000160881',
                                       'Series' : '1.3.46.670589.11.17521.5.0.3124.2008081909090037350',
                                       'Instance' : '1.3.46.670589.11.17521.5.0.3124.2008081909113806560' } ] })
        self.assertEqual(1, int(t[COUNT]))

        
    def test_bitbucket_issue_53(self):
        # DICOMWeb plugin support for "limit" and "offset" parameters in QIDO-RS
        # https://orthanc.uclouvain.be/bugs/show_bug.cgi?id=53
        
        UploadInstance(ORTHANC, 'Brainix/Flair/IM-0001-0001.dcm')
        UploadInstance(ORTHANC, 'Knee/T1/IM-0001-0001.dcm')

        brainix = '2.16.840.1.113669.632.20.1211.10000357775'
        knee = '2.16.840.1.113669.632.20.121711.10000160881'

        a = DoGet(ORTHANC, '/dicom-web/studies',
                  headers = { 'accept' : 'application/json' })
        self.assertEqual(2, len(a))

        b = []
        a = DoGet(ORTHANC, '/dicom-web/studies?limit=1',
                  headers = { 'accept' : 'application/json' })
        self.assertEqual(1, len(a))
        b.append(a[0]['0020000D']['Value'][0])

        a = DoGet(ORTHANC, '/dicom-web/studies?limit=1&offset=1',
                  headers = { 'accept' : 'application/json' })
        self.assertEqual(1, len(a))
        b.append(a[0]['0020000D']['Value'][0])

        self.assertTrue(brainix in b)
        self.assertTrue(knee in b)


    def test_bitbucket_issue_111(self):
        # Wrong serialization of empty values
        # https://orthanc.uclouvain.be/bugs/show_bug.cgi?id=111
        # https://bitbucket.org/sjodogne/orthanc-dicomweb/issues/3

        # According to the standard, section F.2.5
        # (http://dicom.nema.org/medical/dicom/current/output/chtml/part18/sect_F.2.5.html),
        # null values behave as follows: If an attribute is present in
        # DICOM but empty (i.e., Value Length is 0), it shall be
        # preserved in the DICOM JSON attribute object containing no
        # "Value", "BulkDataURI" or "InlineBinary".
        # https://orthanc.uclouvain.be/bugs/show_bug.cgi?id=111

        UploadInstance(ORTHANC, 'Issue111.dcm')

        # Test WADO-RS
        a = DoGet(ORTHANC, '/dicom-web/studies/1.2.276.0.7230010.3.1.2.8323329.30185.1551199973.371589/metadata')
        self.assertEqual(1, len(a))
        self.assertTrue('00080050' in a[0])  # AccessionNumber is null
        self.assertEqual(1, len(a[0]['00080050']))  # 'vr' is the only field to be present
        self.assertEqual('SH', a[0]['00080050']['vr'])

        # Test QIDO-RS
        a = DoGet(ORTHANC, '/dicom-web/studies')
        self.assertEqual(1, len(a))
        self.assertTrue('00080050' in a[0])  # AccessionNumber is null
        self.assertEqual(1, len(a[0]['00080050']))  # 'vr' is the only field to be present
        self.assertEqual('SH', a[0]['00080050']['vr'])


    # this test fails if SeriesMetadata = "MainDicomTags" (this is expected since the reference json is the full json)
    def test_wado_hierarchy(self):
        if IsOrthancVersionAbove(ORTHANC, 1, 12, 5) and DoGet(ORTHANC, '/system')['ApiVersion'] >= 26:  # reference file has been updated
            def CheckJson(uri, headers = {}):
                with open(GetDatabasePath('DummyCT.json'), 'r') as f:
                    expected = json.loads(f.read())
                    actual = DoGet(ORTHANC, uri, headers)
                    self.assertEqual(1, len(actual))
                    AssertAlmostEqualRecursive(self, expected, actual[0])

            UploadInstance(ORTHANC, 'DummyCT.dcm')
            study = '1.2.840.113619.2.176.2025.1499492.7391.1171285944.390'
            series = '1.2.840.113619.2.176.2025.1499492.7391.1171285944.394'
            instance = '1.2.840.113619.2.176.2025.1499492.7040.1171286242.109'

            URI = '/dicom-web/studies/%s/series/%s/instances/%s/metadata'
            self.assertRaises(Exception, lambda: DoGet(ORTHANC, URI % (study, series, instance),
                                                    headers = { 'accept' : 'application/nope' }))

            CheckJson(URI % (study, series, instance), headers = { 'accept' : 'application/dicom+json' })
            CheckJson('/dicom-web/studies/%s/series/%s/metadata' % (study, series))
            CheckJson('/dicom-web/studies/%s/metadata' % study)

            self.assertRaises(Exception, lambda: DoGet(ORTHANC, URI % ('nope', series, instance)))
            self.assertRaises(Exception, lambda: DoGet(ORTHANC, URI % (study, 'nope', instance)))
            self.assertRaises(Exception, lambda: DoGet(ORTHANC, URI % (study, series, 'nope')))
            self.assertRaises(Exception, lambda: DoGet(ORTHANC, '/dicom-web/studies/%s/series/%s/metadata' % ('nope', series)))
            self.assertRaises(Exception, lambda: DoGet(ORTHANC, '/dicom-web/studies/%s/series/%s/metadata' % (study, 'nope')))
            self.assertRaises(Exception, lambda: DoGet(ORTHANC, '/dicom-web/studies/%s/metadata' % 'nope'))


    def test_wado_pixel_data(self):
        orthanc = UploadInstance(ORTHANC, 'Issue29.dcm') ['ID']
        a = DoGet(ORTHANC, '/dicom-web/instances')
        self.assertEqual(1, len(a))
        url = a[0]['00081190']['Value'][0]

        prefix = 'http://%s:%s' % (args.server, args.rest)
        self.assertTrue(url.startswith(prefix))

        b = DoGet(ORTHANC, url[len(prefix):] + '/metadata')
        self.assertEqual('OB', b[0]['7FE00010']['vr'])
        self.assertEqual(2, len(b[0]['7FE00010']))
        self.assertTrue('BulkDataURI' in b[0]['7FE00010'])

        url = b[0]['7FE00010']['BulkDataURI']
        self.assertTrue(url.startswith(prefix))

        p = DoGetMultipart(ORTHANC, url[len(prefix):])

        self.assertEqual(2, len(p))  # There are 2 fragments in this image
        self.assertEqual(4, len(p[0]))
        self.assertEqual(114486, len(p[1]))

        
    def test_wado_hierarchy_bulk(self):
        def CheckBulk(value, bulk):
            self.assertEqual(2, len(value))
            self.assertTrue('BulkDataURI' in value)
            self.assertTrue('vr' in value)
            self.assertEqual(value['BulkDataURI'], bulk)

        orthanc = UploadInstance(ORTHANC, 'PrivateTags.dcm') ['ID']
        study = '1.2.840.113619.2.115.147416.1094281639.0.29'
        series = '1.2.840.113619.2.115.147416.1094281639.0.30'
        sop = '1.2.840.113619.2.115.147416.1094281639.0.38'

        # WARNING: This test will fail on Orthanc <= 1.5.5, because
        # the following fix was not included yet:
        # https://orthanc.uclouvain.be/hg/orthanc/rev/b88937ef597b
        
        a = DoGet(ORTHANC, '/dicom-web/studies/%s/metadata' % study)
        self.assertEqual(1, len(a))

        BASE_URI = '/dicom-web/studies/%s/series/%s/instances/%s/bulk' % (study, series, sop)
        BASE_URL = 'http://%s:%s%s' % (args.server, args.rest, BASE_URI)

        self.assertEqual(2, len(a[0]['60031010']['Value']))
        CheckBulk(a[0]['60031010']['Value'][0]['60031011'], '%s/60031010/1/60031011' % BASE_URL)
        CheckBulk(a[0]['60031010']['Value'][1]['60031011'], '%s/60031010/2/60031011' % BASE_URL)
        CheckBulk(a[0]['7FE00010'], '%s/7fe00010' % BASE_URL)

        b = DoGetRaw(ORTHANC, '/instances/%s/content/6003-1010/0/6003-1011' % orthanc) [1]
        c = DoGetMultipart(ORTHANC, '%s/60031010/1/60031011' % BASE_URI)

        self.assertEqual(12288, len(b))
        self.assertEqual(1, len(c))
        self.assertEqual(b, c[0])


    def test_bitbucket_issue_112(self):
        # Wrong serialization of number values
        # https://orthanc.uclouvain.be/bugs/show_bug.cgi?id=112
        # https://bitbucket.org/sjodogne/orthanc-dicomweb/issues/4/
        
        UploadInstance(ORTHANC, 'DummyCT.dcm')
        study = '1.2.840.113619.2.176.2025.1499492.7391.1171285944.390'

        # This is the WADO-RS testing
        a = DoGet(ORTHANC, '/dicom-web/studies/%s/metadata' % study)
        self.assertEqual(1, len(a))
        self.assertEqual('IS', a[0]['00180091']['vr'])  # EchoTrainLength

        if (sys.version_info >= (3, 0)):
            types = (int)
        else:
            types = (int, long)
        
        b = a[0]['00180091']['Value'][0]
        self.assertTrue(isinstance(b, types))
        self.assertEqual(10, b)

        # This is the QIDO-RS testing
        a = DoGet(ORTHANC, '/dicom-web/studies')
        self.assertEqual(1, len(a))
        self.assertEqual('IS', a[0]['00201208']['vr'])  # Number of Study Related Instances

        b = a[0]['00201208']['Value'][0]
        self.assertTrue(isinstance(b, types))
        self.assertEqual(1, b)


    def test_bitbucket_issue_113(self):
        # Wrong serialization of PN VR
        # https://orthanc.uclouvain.be/bugs/show_bug.cgi?id=113
        # https://bitbucket.org/sjodogne/orthanc-dicomweb/issues/2/

        # Make sure UTF-8 encoding is used
        self.assertEqual('Utf8', DoPut(ORTHANC, '/tools/default-encoding', 'Utf8'))
        
        UploadInstance(ORTHANC, 'Encodings/DavidClunie/SCSX1')
        study = '1.3.6.1.4.1.5962.1.2.0.1175775771.5711.0'

        # This is the WADO-RS testing
        a = DoGet(ORTHANC, '/dicom-web/studies/%s/metadata' % study)
        self.assertEqual(1, len(a))

        pn = a[0]['00100010']  # Patient name
        self.assertEqual('PN', pn['vr'])
        self.assertEqual(1, len(pn['Value']))
        self.assertEqual('Wang^XiaoDong', pn['Value'][0]['Alphabetic'])
        self.assertEqual(u'王^小東', pn['Value'][0]['Ideographic'])

        # This is the QIDO-RS testing
        a = DoGet(ORTHANC, '/dicom-web/studies')
        self.assertEqual(1, len(a))

        pn = a[0]['00100010']  # Patient name
        self.assertEqual('PN', pn['vr'])
        self.assertEqual(1, len(pn['Value']))
        self.assertEqual('Wang^XiaoDong', pn['Value'][0]['Alphabetic'])
        self.assertEqual(u'王^小東', pn['Value'][0]['Ideographic'])

        # new derivated test added later
        if IsPluginVersionAtLeast(ORTHANC, "dicom-web", 1, 18, 0):
            a = DoGet(ORTHANC, '/dicom-web/studies?StudyInstanceUID=1.3.6.1.4.1.5962.1.2.0.1175775771.5711.0')
            self.assertEqual(1, len(a))
            pn = a[0]['00100010']  # Patient name
            self.assertEqual('PN', pn['vr'])
            self.assertEqual(1, len(pn['Value']))
            self.assertEqual('Wang^XiaoDong', pn['Value'][0]['Alphabetic'])     # before 1.18, one of the 2 values was empty !
            self.assertEqual(u'王^小東', pn['Value'][0]['Ideographic'])


    def test_bitbucket_issue_96(self):
        # WADO-RS RetrieveFrames rejects valid accept headers
        # https://orthanc.uclouvain.be/bugs/show_bug.cgi?id=96
        # https://bitbucket.org/sjodogne/orthanc-dicomweb/issues/5/
        
        UploadInstance(ORTHANC, 'Brainix/Epi/IM-0001-0001.dcm')

        a = DoGet(ORTHANC, '/dicom-web/instances')
        self.assertEqual(1, len(a))
        self.assertEqual(256, a[0]['00280010']['Value'][0]) # Rows
        self.assertEqual(256, a[0]['00280011']['Value'][0]) # Columns
        self.assertEqual(16, a[0]['00280100']['Value'][0])  # Bits allocated

        url = a[0]['00081190']['Value'][0]

        prefix = 'http://%s:%s' % (args.server, args.rest)
        self.assertTrue(url.startswith(prefix))
        uri = url[len(prefix):]

        self.assertRaises(Exception, lambda: DoGetMultipart(ORTHANC, '%s/frames/%d' % (uri, 0)))
        self.assertRaises(Exception, lambda: DoGetMultipart(ORTHANC, '%s/frames/%d' % (uri, 2)))

        b = DoGetMultipart(ORTHANC, '%s/frames/%d' % (uri, 1))
        self.assertEqual(1, len(b))
        self.assertEqual(256 * 256 * 2, len(b[0]))
        self.assertEqual('ce394eb4d4de4eeef348436108101f3b', ComputeMD5(b[0]))
        
        c = DoGetMultipart(ORTHANC, '%s/frames/%d' % (uri, 1),
                           headers = { 'Accept' : 'multipart/related; type=application/octet-stream' })
        self.assertEqual(1, len(c))
        self.assertEqual(b[0], c[0])
        self.assertEqual('ce394eb4d4de4eeef348436108101f3b', ComputeMD5(c[0]))

        c = DoGetMultipart(ORTHANC, '%s/frames/%d' % (uri, 1),
                           headers = { 'Accept' : 'multipart/related; type="application/octet-stream"' })
        self.assertEqual(1, len(c))
        self.assertEqual(b[0], c[0])
        self.assertEqual('ce394eb4d4de4eeef348436108101f3b', ComputeMD5(c[0]))

        self.assertRaises(Exception, lambda: DoGetMultipart(ORTHANC, '%s/frames/%d' % (uri, 1),
                                                            headers = { 'Accept' : 'multipart/related; type="nope"' }))

        self.assertRaises(Exception, lambda: DoGetMultipart(ORTHANC, '%s/frames/%d' % (uri, 1),
                                                            headers = { 'Accept' : 'multipart/related; type=nope' }))

        self.assertRaises(Exception, lambda: DoGetMultipart(ORTHANC, '%s/frames/%d' % (uri, 1),
                                                            headers = { 'Accept' : 'nope' }))


    def test_bugzilla_219(self):
        # WADO-RS RetrieveFrames shall transcode ExplicitBigEndian to ExplicitLittleEndian
        # https://orthanc.uclouvain.be/bugs/show_bug.cgi?id=219
        
        if IsPluginVersionAtLeast(ORTHANC, "dicom-web", 1, 17, 0):

            UploadInstance(ORTHANC, 'TransferSyntaxes/1.2.840.10008.1.2.2.dcm')

            r = DoGetMultipart(ORTHANC, '/dicom-web/studies/1.2.840.113619.2.21.848.246800003.0.1952805748.3/series/1.2.840.113619.2.21.24680000.700.0.1952805748.3.0/instances/1.2.840.1136190195280574824680000700.3.0.1.19970424140438/frames/1', {}, True )
            self.assertIn('transfer-syntax=1.2.840.10008.1.2.1', r[0][1]['Content-Type'])


    def test_qido_fields(self):
        UploadInstance(ORTHANC, 'DummyCT.dcm')

        a = DoGet(ORTHANC, '/dicom-web/studies')
        self.assertEqual(1, len(a))
        self.assertFalse('00280010' in a[0])   # Rows

        a = DoGet(ORTHANC, '/dicom-web/studies?includefield=Rows')
        self.assertEqual(1, len(a))
        self.assertTrue('00280010' in a[0])
        self.assertEqual(512, a[0]['00280010']['Value'][0])

        a = DoGet(ORTHANC, '/dicom-web/studies?Rows=128')
        self.assertEqual(0, len(a))

        a = DoGet(ORTHANC, '/dicom-web/studies?Rows=512')
        self.assertEqual(1, len(a))
        self.assertTrue('00280010' in a[0])
        self.assertEqual(512, a[0]['00280010']['Value'][0])

        if IsPluginVersionAtLeast(ORTHANC, "dicom-web", 1, 17, 0):
            a = DoGet(ORTHANC, '/dicom-web/studies/1.2.840.113619.2.176.2025.1499492.7391.1171285944.390/series/1.2.840.113619.2.176.2025.1499492.7391.1171285944.394/instances?includefield=00081140')
            self.assertEqual(1, len(a))
            self.assertTrue('00081140' in a[0])
            self.assertEqual(2, len(a[0]['00081140']['Value']))
            self.assertEqual('1.2.840.113619.2.176.2025.1499492.7040.1171286241.719', a[0]['00081140']['Value'][0]['00081155']['Value'][0])


        
    def test_stow_errors(self):
        def CheckSequences(a, expectFailedSopSequence):
            if IsPluginVersionAtLeast(ORTHANC, "dicom-web", 1, 19, 0) and not expectFailedSopSequence:
                self.assertEqual(2, len(a))
                self.assertNotIn('00081198', a)
            else:
                self.assertEqual(3, len(a))
                self.assertTrue('00081198' in a)
                self.assertEqual('SQ', a['00081198']['vr'])

            self.assertTrue('00080005' in a)
            self.assertTrue('00081199' in a)
            self.assertEqual('CS', a['00080005']['vr'])
            self.assertEqual('SQ', a['00081199']['vr'])
        
        # Pushing an instance to a study that is not its parent
        (status, a) = SendStowRaw(ORTHANC, args.dicomweb + '/studies/nope', GetDatabasePath('Phenix/IM-0001-0001.dcm'))
        self.assertEqual(409, status)
        CheckSequences(a, True)

        self.assertFalse('Value' in a['00081199'])  # No success instance
        
        self.assertEqual(1, len(a['00081198']['Value']))  # One failed instance
        self.assertEqual('1.2.840.10008.5.1.4.1.1.2',
                         a['00081198']['Value'][0]['00081150']['Value'][0])
        self.assertEqual('1.2.840.113704.7.1.1.6632.1127829031.2',
                         a['00081198']['Value'][0]['00081155']['Value'][0])
        self.assertEqual(0x0110,  # Processing failure
                         a['00081198']['Value'][0]['00081197']['Value'][0])

        # Pushing an instance with missing tags
        (status, a) = SendStowRaw(ORTHANC, args.dicomweb + '/studies', GetDatabasePath('Issue111.dcm'))
        self.assertEqual(400, status)
        CheckSequences(a, False) # No failed instance, as tags are missing

        self.assertFalse('Value' in a['00081199'])  # No success instance

        # Pushing a file that is not in the DICOM format
        (status, a) = SendStowRaw(ORTHANC, args.dicomweb + '/studies', GetDatabasePath('Issue111.dump'))
        self.assertEqual(400, status)
        CheckSequences(a, False) # No failed instance, as non-DICOM

        self.assertFalse('Value' in a['00081199'])  # No success instance

        # Pushing a DICOM instance with only SOP class and instance UID
        (status, a) = SendStowRaw(ORTHANC, args.dicomweb + '/studies', GetDatabasePath('Issue196.dcm'))
        self.assertEqual(400, status)
        CheckSequences(a, True)

        self.assertFalse('Value' in a['00081199'])  # No success instance

        self.assertEqual(1, len(a['00081198']['Value']))  # One failed instance
        self.assertEqual('1.2.840.10008.5.1.4.1.1.4',
                         a['00081198']['Value'][0]['00081150']['Value'][0])
        self.assertEqual('1.2.840.113619.2.176.2025.1499492.7040.1171286242.109',
                         a['00081198']['Value'][0]['00081155']['Value'][0])
        self.assertEqual(0xC000,  # Error: Cannot understand (cannot understand certain Data Elements)
                         a['00081198']['Value'][0]['00081197']['Value'][0])


    def test_allowed_methods(self):
        self.assertEqual(0, len(DoGet(ORTHANC, '/dicom-web/studies')))

        e = DoPutRaw(ORTHANC, '/dicom-web/studies')
        self.assertEqual(405, int(e[0]['status']))
        self.assertEqual('GET,POST', e[0]['allow'])

        e = DoDeleteRaw(ORTHANC, '/dicom-web/studies')
        self.assertEqual(405, int(e[0]['status']))
        self.assertEqual('GET,POST', e[0]['allow'])


    def test_add_server(self):
        try:
            DoDelete(ORTHANC, '/dicom-web/servers/hello')
        except:
            pass
        
        try:
            DoDelete(ORTHANC, '/dicom-web/servers/google')  # If "AllWindowsStart.sh" is used
        except:
            pass
        
        l = DoGet(ORTHANC, '/dicom-web/servers')
        self.assertEqual(1, len(l))
        self.assertTrue('sample' in l)

        url = 'http://localhost:8042/dicom-web/'
        DoPut(ORTHANC, '/dicom-web/servers/hello', {
            'Url': url,
            'HttpHeaders' : {
                'Hello' : 'World'
            },
            'Username' : 'bob',
            'Password' : 'password',
            'UserProperty' : 'Test',
            'HasDelete' : True,
            'Timeout' : 66  # New in 1.6
            })

        l = DoGet(ORTHANC, '/dicom-web/servers')
        self.assertEqual(2, len(l))
        self.assertTrue('sample' in l)        
        self.assertTrue('hello' in l)        

        o = DoGet(ORTHANC, '/dicom-web/servers/sample')
        self.assertEqual(5, len(o))
        self.assertTrue('stow' in o)
        self.assertTrue('retrieve' in o)
        self.assertTrue('get' in o)
        self.assertTrue('wado' in o)  # New in 0.7
        self.assertTrue('qido' in o)  # New in 0.7

        o = DoGet(ORTHANC, '/dicom-web/servers/hello')
        self.assertEqual(6, len(o))
        self.assertTrue('stow' in o)
        self.assertTrue('retrieve' in o)
        self.assertTrue('get' in o)
        self.assertTrue('wado' in o)  # New in 0.7
        self.assertTrue('qido' in o)  # New in 0.7
        self.assertTrue('delete' in o)  # New in 0.7

        s = DoGet(ORTHANC, '/dicom-web/servers?expand')
        self.assertEqual(8, len(s['hello']))
        self.assertEqual(url, s['hello']['Url'])
        self.assertEqual('bob', s['hello']['Username'])
        self.assertEqual(None, s['hello']['Password'])
        self.assertFalse(s['hello']['Pkcs11'])
        self.assertEqual(1, len(s['hello']['HttpHeaders']))
        self.assertTrue('Hello' in s['hello']['HttpHeaders'])
        self.assertEqual('Test', s['hello']['UserProperty'])
        self.assertEqual('1', s['hello']['HasDelete'])
        self.assertEqual(66, s['hello']['Timeout'])  # New in 1.6 (interpreted as a string in <= 1.5)
        
        DoDelete(ORTHANC, '/dicom-web/servers/hello')

        
    def test_bitbucket_issue_143(self):
        # WADO-RS metadata request returns "500 Internal Server Error"
        # instead of "404 Not Found" for missing instance
        # https://orthanc.uclouvain.be/bugs/show_bug.cgi?id=143
        UploadInstance(ORTHANC, 'Issue143.dcm')

        e = DoGetRaw(ORTHANC, '/dicom-web/studies/1.2.840.113619.2.55.3.671756986.106.1316467036.460/series/1.2.840.113619.2.55.3.671756986.106.1316467036.465/instances/0.0.0.0.0/metadata')
        self.assertEqual(404, int(e[0]['status']))
        
        DoGet(ORTHANC, '/dicom-web/studies/1.3.6.1.4.1.34261.90254037371867.41912.1553085024.2/series/1.3.6.1.4.1.34261.90254037371867.41912.1553085024.3/instances/1.2.276.0.7230010.3.1.4.253549293.36648.1555586123.754/metadata')

        e = DoGetRaw(ORTHANC, '/dicom-web/studies/0.0.0.0.0/series/1.3.6.1.4.1.34261.90254037371867.41912.1553085024.3/instances/1.2.276.0.7230010.3.1.4.253549293.36648.1555586123.754/metadata')
        self.assertEqual(404, int(e[0]['status']))

        e = DoGetRaw(ORTHANC, '/dicom-web/studies/1.3.6.1.4.1.34261.90254037371867.41912.1553085024.2/series/0.0.0.0.0/instances/1.2.276.0.7230010.3.1.4.253549293.36648.1555586123.754/metadata')
        self.assertEqual(404, int(e[0]['status']))

        e = DoGetRaw(ORTHANC, '/dicom-web/studies/0.0.0.0.0/series/0.0.0.0.0/instances/0.0.0.0.0/metadata')
        self.assertEqual(404, int(e[0]['status']))


    def test_encodings_qido(self):
        # The "DefaultEncoding" condifuration option is set to "UTF8"
        # in the integration tests, so all the QIDO-RS requests must
        # lead to a "ISO_IR 192" specific character set
        def GetPatientName(dicom, onlyAlphabetic):
            i = UploadInstance(ORTHANC, dicom) ['ID']
            j = DoGet(ORTHANC, '/instances/%s/tags?simplify' % i) ['StudyInstanceUID']
            qido = DoGet(ORTHANC, '/dicom-web/studies?0020000D=%s' % j)
            self.assertEqual(1, len(qido))
            self.assertEqual('CS', qido[0]['00080005']['vr'])
            self.assertEqual('ISO_IR 192', qido[0]['00080005']['Value'][0])
            if onlyAlphabetic:
                self.assertEqual(1, len(qido[0]['00100010']['Value'][0]))
            else:
                self.assertEqual(3, len(qido[0]['00100010']['Value'][0]))
            return qido[0]['00100010']['Value'][0]

        # Make sure UTF-8 encoding is used
        self.assertEqual('Utf8', DoPut(ORTHANC, '/tools/default-encoding', 'Utf8'))

        # Check out "test_issue_95_encodings" in "../../Tests/Tests.py"

        self.assertEqual(u'Buc^Jérôme', GetPatientName('Encodings/DavidClunie/SCSFREN', True) ['Alphabetic'])
        self.assertEqual(u'Äneas^Rüdiger', GetPatientName('Encodings/DavidClunie/SCSGERM', True)['Alphabetic'])
        self.assertEqual(u'Διονυσιος', GetPatientName('Encodings/DavidClunie/SCSGREEK', True)['Alphabetic'])
        self.assertEqual(u'Люкceмбypг', GetPatientName('Encodings/DavidClunie/SCSRUSS', True)['Alphabetic'])
        self.assertEqual(u'שרון^דבורה', GetPatientName('Encodings/DavidClunie/SCSHBRW', True)['Alphabetic'])
        self.assertEqual(u'قباني^لنزار', GetPatientName('Encodings/DavidClunie/SCSARAB', True)['Alphabetic'])

        self.assertEqual(u'Hong^Gildong', GetPatientName('Encodings/DavidClunie/SCSI2', False)['Alphabetic'])
        self.assertEqual(u'洪^吉洞', GetPatientName('Encodings/DavidClunie/SCSI2', False)['Ideographic'])
        self.assertEqual(u'홍^길동', GetPatientName('Encodings/DavidClunie/SCSI2', False)['Phonetic'])
        self.assertEqual(u'Wang^XiaoDong', GetPatientName('Encodings/DavidClunie/SCSX2', False)['Alphabetic'])
        self.assertEqual(u'王^小东', GetPatientName('Encodings/DavidClunie/SCSX2', False)['Ideographic'])
        self.assertEqual(u'', GetPatientName('Encodings/DavidClunie/SCSX2', False)['Phonetic'])
        self.assertEqual(u'Wang^XiaoDong', GetPatientName('Encodings/DavidClunie/SCSX1', False)['Alphabetic'])
        self.assertEqual(u'王^小東', GetPatientName('Encodings/DavidClunie/SCSX1', False)['Ideographic'])
        self.assertEqual(u'', GetPatientName('Encodings/DavidClunie/SCSX1', False)['Phonetic'])
        self.assertEqual(u'Yamada^Tarou', GetPatientName('Encodings/DavidClunie/SCSH31', False)['Alphabetic'])
        self.assertEqual(u'山田^太郎', GetPatientName('Encodings/DavidClunie/SCSH31', False)['Ideographic'])
        self.assertEqual(u'やまだ^たろう', GetPatientName('Encodings/DavidClunie/SCSH31', False)['Phonetic'])
        self.assertEqual(u'ﾔﾏﾀﾞ^ﾀﾛｳ', GetPatientName('Encodings/DavidClunie/SCSH32', False)['Alphabetic'])

        # TODO - Not supported yet by the Orthanc core as of 1.5.7
        #self.assertEqual(u'山田^太郎', GetPatientName('Encodings/DavidClunie/SCSH32')['Ideographic'])
        #self.assertEqual(u'やまだ^たろう', GetPatientName('Encodings/DavidClunie/SCSH32')['Phonetic'])


    def test_encodings_wado_metadata(self):
        # If querying the instance metadata, the "DefaultEncoding"
        # configuration is not used, but the actual encoding
        def GetEncoding(dicom, length):
            qido = DoGet(ORTHANC, '/dicom-web/%s/metadata' % UploadAndGetWadoPath(dicom))
            self.assertEqual(1, len(qido))
            self.assertEqual(length, len(qido[0]['00080005']['Value']))
            self.assertEqual('CS', qido[0]['00080005']['vr'])
            return qido[0]['00080005']['Value']

        self.assertEqual('ISO_IR 100', GetEncoding('Encodings/DavidClunie/SCSFREN', 1)[0])
        self.assertEqual('ISO_IR 100', GetEncoding('Encodings/DavidClunie/SCSGERM', 1)[0])
        self.assertEqual('ISO_IR 126', GetEncoding('Encodings/DavidClunie/SCSGREEK', 1)[0])
        self.assertEqual('ISO_IR 144', GetEncoding('Encodings/DavidClunie/SCSRUSS', 1)[0])
        self.assertEqual('ISO_IR 138', GetEncoding('Encodings/DavidClunie/SCSHBRW', 1)[0])
        self.assertEqual('ISO_IR 127', GetEncoding('Encodings/DavidClunie/SCSARAB', 1)[0])
        self.assertEqual('ISO 2022 IR 149', GetEncoding('Encodings/DavidClunie/SCSI2', 1)[0])
        self.assertEqual('GB18030', GetEncoding('Encodings/DavidClunie/SCSX2', 1)[0])
        self.assertEqual('ISO_IR 192', GetEncoding('Encodings/DavidClunie/SCSX1', 1)[0])
        self.assertEqual('ISO 2022 IR 87', GetEncoding('Encodings/DavidClunie/SCSH31', 1)[0])
        self.assertEqual('ISO 2022 IR 13', GetEncoding('Encodings/DavidClunie/SCSH32', 2)[0])
        self.assertEqual('ISO 2022 IR 87', GetEncoding('Encodings/DavidClunie/SCSH32', 2)[1])


    def test_rendered(self):
        def RenderFrame(path, i):
            return DoPost(ORTHANC, '/dicom-web/servers/sample/get', {
                'Uri' : '%s/frames/%d/rendered' % (path, i)
            })

        # This image has 76 frames
        path = UploadAndGetWadoPath('Multiframe.dcm')

        self.assertRaises(Exception, lambda: RenderFrame(path, 0))

        frame1 = RenderFrame(path, 1)        
        im = UncompressImage(frame1)
        self.assertEqual("L", im.mode)
        self.assertEqual(512, im.size[0])
        self.assertEqual(512, im.size[1])

        im = UncompressImage(RenderFrame(path, 76))
        self.assertEqual("L", im.mode)
        self.assertEqual(512, im.size[0])
        self.assertEqual(512, im.size[1])

        self.assertRaises(Exception, lambda: RenderFrame(path, 77))

        defaultFrame = DoPost(ORTHANC, '/dicom-web/servers/sample/get', {
            'Uri' : '%s/rendered' % path
        })

        self.assertEqual(len(frame1), len(defaultFrame))
        self.assertEqual(frame1, defaultFrame)


        # This image has 1 frame
        path = UploadAndGetWadoPath('Phenix/IM-0001-0001.dcm')

        self.assertRaises(Exception, lambda: RenderFrame(path, 0))
        self.assertRaises(Exception, lambda: RenderFrame(path, 2))

        frame1 = RenderFrame(path, 1)
        im = UncompressImage(frame1)
        self.assertEqual("L", im.mode)
        self.assertEqual(512, im.size[0])
        self.assertEqual(358, im.size[1])

        defaultFrame = DoPost(ORTHANC, '/dicom-web/servers/sample/get', {
            'Uri' : '%s/rendered' % path
        })

        self.assertEqual(len(frame1), len(defaultFrame))
        self.assertEqual(frame1, defaultFrame)


    def test_qido_parent_attributes(self):
        UploadInstance(ORTHANC, 'Brainix/Flair/IM-0001-0001.dcm')
        study = '2.16.840.1.113669.632.20.1211.10000357775'
        series = '1.3.46.670589.11.0.0.11.4.2.0.8743.5.5396.2006120114285654497'
        instance = '1.3.46.670589.11.0.0.11.4.2.0.8743.5.5396.2006120114314079549'

        a = DoGet(ORTHANC, '/dicom-web/studies')
        self.assertEqual(1, len(a))
        self.assertFalse('00080018' in a[0])  # SOPInstanceUID
        self.assertFalse('0020000E' in a[0])  # SeriesInstanceUID
        self.assertEqual(study, a[0]['0020000D']['Value'][0])
        self.assertEqual('BRAINIX', a[0]['00100010']['Value'][0]['Alphabetic'])

        a = DoGet(ORTHANC, '/dicom-web/studies?0020000D=%s' % study)
        self.assertEqual(1, len(a))
        self.assertFalse('00080018' in a[0])  # SOPInstanceUID
        self.assertFalse('0020000E' in a[0])  # SeriesInstanceUID
        self.assertEqual(study, a[0]['0020000D']['Value'][0])
        self.assertEqual('BRAINIX', a[0]['00100010']['Value'][0]['Alphabetic'])
        
        a = DoGet(ORTHANC, '/dicom-web/series')
        self.assertEqual(1, len(a))
        self.assertFalse('00080018' in a[0])
        self.assertEqual(study, a[0]['0020000D']['Value'][0])
        self.assertEqual(series, a[0]['0020000E']['Value'][0])
        self.assertEqual('MR', a[0]['00080060']['Value'][0])
        self.assertEqual('BRAINIX', a[0]['00100010']['Value'][0]['Alphabetic'])

        a = DoGet(ORTHANC, '/dicom-web/instances')
        self.assertEqual(1, len(a))
        self.assertEqual(study, a[0]['0020000D']['Value'][0])
        self.assertEqual(series, a[0]['0020000E']['Value'][0])
        self.assertEqual(instance, a[0]['00080018']['Value'][0])
        self.assertEqual('MR', a[0]['00080060']['Value'][0])
        self.assertEqual('BRAINIX', a[0]['00100010']['Value'][0]['Alphabetic'])

        a = DoGet(ORTHANC, '/dicom-web/studies/%s/series' % study)
        self.assertEqual(1, len(a))
        self.assertFalse('00080018' in a[0])
        self.assertEqual(study, a[0]['0020000D']['Value'][0])
        self.assertEqual(series, a[0]['0020000E']['Value'][0])
        self.assertEqual('MR', a[0]['00080060']['Value'][0])
        self.assertEqual('BRAINIX', a[0]['00100010']['Value'][0]['Alphabetic'])

        a = DoGet(ORTHANC, '/dicom-web/studies/%s/series/%s/instances' % (study, series))
        self.assertEqual(1, len(a))
        self.assertEqual(study, a[0]['0020000D']['Value'][0])
        self.assertEqual(series, a[0]['0020000E']['Value'][0])
        self.assertEqual(instance, a[0]['00080018']['Value'][0])
        self.assertEqual('MR', a[0]['00080060']['Value'][0])
        self.assertEqual('BRAINIX', a[0]['00100010']['Value'][0]['Alphabetic'])

        # "If {StudyInstanceUID} is not specified, all Study-level
        # attributes specified in Table 6.7.1-2" => Here,
        # {StudyInstanceUID} *is* specified, so we must *not* get the
        # PatientName.
        # http://dicom.nema.org/medical/dicom/2019a/output/html/part18.html#table_6.7.1-2a
        a = DoGet(ORTHANC, '/dicom-web/series?0020000D=%s' % study)
        self.assertEqual(1, len(a))
        self.assertFalse('00100010' in a[0])  # PatientName
        self.assertEqual(study, a[0]['0020000D']['Value'][0])
        self.assertEqual(series, a[0]['0020000E']['Value'][0])
        self.assertEqual('MR', a[0]['00080060']['Value'][0])

        # if we ask explicitely for the Patient and Study tags, we must get it
        a = DoGet(ORTHANC, '/dicom-web/series?0020000D=%s&includefield=00100010&includefield=00080020' % study)
        self.assertEqual(1, len(a))
        self.assertTrue('00100010' in a[0])  # PatientName
        self.assertTrue('00080020' in a[0])  # StudyDate

        # if {StudyInstanceUID} *is not* specified, we must get the PatientName
        a = DoGet(ORTHANC, '/dicom-web/series')
        self.assertTrue('00100010' in a[0])  # PatientName

        # http://dicom.nema.org/medical/dicom/2019a/output/html/part18.html#table_6.7.1-2b
        a = DoGet(ORTHANC, '/dicom-web/instances?0020000D=%s' % study)
        self.assertEqual(1, len(a))
        self.assertFalse('00100010' in a[0])  # PatientName
        self.assertEqual(study, a[0]['0020000D']['Value'][0])
        self.assertEqual(series, a[0]['0020000E']['Value'][0])
        self.assertEqual('MR', a[0]['00080060']['Value'][0])
        
        a = DoGet(ORTHANC, '/dicom-web/instances?0020000E=%s' % series)
        self.assertEqual(1, len(a))
        self.assertFalse('00080060' in a[0])  # Modality
        self.assertEqual(study, a[0]['0020000D']['Value'][0])
        self.assertEqual(series, a[0]['0020000E']['Value'][0])
        self.assertEqual('BRAINIX', a[0]['00100010']['Value'][0]['Alphabetic'])
        
        a = DoGet(ORTHANC, '/dicom-web/instances?0020000D=%s&0020000E=%s' % (study, series))
        self.assertEqual(1, len(a))
        self.assertFalse('00100010' in a[0])  # PatientName
        self.assertFalse('00080060' in a[0])  # Modality
        self.assertEqual(study, a[0]['0020000D']['Value'][0])
        self.assertEqual(series, a[0]['0020000E']['Value'][0])

        # if we ask explicitely for the Patient and Study tags, we must get it
        a = DoGet(ORTHANC, '/dicom-web/instances?0020000D=%s&includefield=00100010&includefield=00080020' % study)
        self.assertEqual(1, len(a))
        self.assertTrue('00100010' in a[0])  # PatientName
        self.assertTrue('00080020' in a[0])  # StudyDate

        # if {StudyInstanceUID} *is not* specified, we must get all Study, Series and Patient tags
        a = DoGet(ORTHANC, '/dicom-web/instances')
        self.assertTrue('00100010' in a[0])  # PatientName
        self.assertTrue('00080020' in a[0])  # StudyDate
        self.assertTrue('00080060' in a[0])  # Modality


    #@unittest.skip("Skip this test on GDCM 2.8.4")
    def test_bitbucket_issue_164(self):
        # WARNING - This makes GDCM 2.8.4 crash
        # https://orthanc.uclouvain.be/bugs/show_bug.cgi?id=164
        UploadInstance(ORTHANC, 'Issue164.dcm')

        p = DoGetMultipart(ORTHANC, 'dicom-web/studies/1.2.276.0.26.1.1.1.2.2020.45.52293.1506048/series/1.2.276.0.26.1.1.1.2.2020.45.52293.6384450/instances/1.2.276.0.26.1.1.1.2.2020.45.52366.2551599.179568640/frames/5')
        self.assertEqual(1, len(p))
        self.assertEqual(743 * 975 * 3, len(p[0]))

        metadata = DoGet(ORTHANC, 'dicom-web/studies/1.2.276.0.26.1.1.1.2.2020.45.52293.1506048/series/1.2.276.0.26.1.1.1.2.2020.45.52293.6384450/instances/1.2.276.0.26.1.1.1.2.2020.45.52366.2551599.179568640/metadata')
        self.assertEqual("YBR_FULL_422", metadata[0]['00280004']['Value'][0])

        # TODO
        # # starting from X.XX.X, Orthanc won't convert YBR to RGB anymore -> new checksum (https://discourse.orthanc-server.org/t/orthanc-convert-ybr-to-rgb-but-does-not-change-metadata/3533)
        # if IsOrthancVersionAbove(ORTHANC, 1, XX, 1):
        #     expectedDcmtkChecksum = '7535a11e7da0fa590c467ac9d323c5c1'
        # else:
        expectedDcmtkChecksum = 'b3662c4bfa24a0c73abb08548c63319b'

        if HasGdcmPlugin(ORTHANC):
            self.assertTrue(ComputeMD5(p[0]) in [
                'b952d67da9ff004b0adae3982e89d620', # GDCM >= 3.0
                expectedDcmtkChecksum  # Fallback to DCMTK
                ])
        else:
            self.assertEqual(expectedDcmtkChecksum, ComputeMD5(p[0]))  # DCMTK


    def test_bitbucket_issue_168(self):
        # "Plugins can't read private tags from the configuration
        # file" This test will fail if DCMTK <= 3.6.1 (e.g. on Ubuntu
        # 16.04), or if Orthanc <= 1.5.8
        # https://orthanc.uclouvain.be/bugs/show_bug.cgi?id=168

        UploadInstance(ORTHANC, 'Issue168.dcm')

        a = DoGet(ORTHANC, '/dicom-web/studies')
        self.assertEqual(1, len(a))
        self.assertFalse('00090010' in a[0])
        self.assertFalse('00091001' in a[0])
        self.assertEqual('20170404', a[0]['00080020']['Value'][0])

        a = DoGet(ORTHANC, '/dicom-web/studies?includefield=00091001')
        self.assertEqual(1, len(a))
        self.assertFalse('00090010' in a[0])
        self.assertTrue('00091001' in a[0])   # This fails if DCMTK <= 3.6.1
        self.assertEqual('DS', a[0]['00091001']['vr'])
        self.assertEqual(1, len(a[0]['00091001']['Value']))
        if IsOrthancVersionAbove(ORTHANC, 1, 12, 5) and DoGet(ORTHANC, '/system')['ApiVersion'] >= 26:
            self.assertEqual("98.41", a[0]['00091001']['Value'][0])
        else:
            self.assertAlmostEqual(98.41, a[0]['00091001']['Value'][0])

        a = DoGet(ORTHANC, '/dicom-web/studies?00090010=Lunit&includefield=00091001')
        self.assertEqual(1, len(a))
        self.assertTrue('00090010' in a[0])
        self.assertEqual('LO', a[0]['00090010']['vr'])
        self.assertEqual(1, len(a[0]['00090010']['Value']))
        self.assertEqual('Lunit', a[0]['00090010']['Value'][0])
        self.assertTrue('00091001' in a[0])
        self.assertEqual('DS', a[0]['00091001']['vr'])
        self.assertEqual(1, len(a[0]['00091001']['Value']))
        if IsOrthancVersionAbove(ORTHANC, 1, 12, 5) and DoGet(ORTHANC, '/system')['ApiVersion'] >= 26:
            self.assertEqual("98.41", a[0]['00091001']['Value'][0])
        else:
            self.assertAlmostEqual(98.41, a[0]['00091001']['Value'][0])
        
        a = DoGet(ORTHANC, '/dicom-web/studies?00090010=Lunit2&includefield=00091001')
        self.assertEqual(0, len(a))


    def test_rendered_studies_series(self):
        i = UploadInstance(ORTHANC, 'Phenix/IM-0001-0001.dcm') ['ID']
        study = DoGet(ORTHANC, '/instances/%s/tags?simplify' % i) ['StudyInstanceUID']
        series = DoGet(ORTHANC, '/instances/%s/tags?simplify' % i) ['SeriesInstanceUID']
        instance = DoGet(ORTHANC, '/instances/%s/tags?simplify' % i) ['SOPInstanceUID']

        a = DoPost(ORTHANC, '/dicom-web/servers/sample/get', {
            'Uri' : '/studies/%s/series/%s/instances/%s/rendered' % (study, series, instance)
        })
        
        im = UncompressImage(a)
        self.assertEqual("L", im.mode)
        self.assertEqual(512, im.size[0])
        self.assertEqual(358, im.size[1])

        b = DoPost(ORTHANC, '/dicom-web/servers/sample/get', {
            'Uri' : '/studies/%s/series/%s/rendered' % (study, series)
        })
        
        self.assertEqual(len(a), len(b))
        self.assertEqual(a, b)

        c = DoPost(ORTHANC, '/dicom-web/servers/sample/get', {
            'Uri' : '/studies/%s/rendered' % study
        })
        
        self.assertEqual(len(a), len(c))
        self.assertEqual(a, c)

        if IsPluginVersionAtLeast(ORTHANC, "dicom-web", 1, 20, 0):
            # test with 2 instances: https://discourse.orthanc-server.org/t/thumbnail-orthanc-stone-viewer-issue/5827/3
            i = UploadInstance(ORTHANC, 'Brainix/Epi/IM-0001-0001.dcm') ['ID']
            UploadInstance(ORTHANC, 'Brainix/Epi/IM-0001-0002.dcm') ['ID']

            study = DoGet(ORTHANC, '/instances/%s/tags?simplify' % i) ['StudyInstanceUID']
            series = DoGet(ORTHANC, '/instances/%s/tags?simplify' % i) ['SeriesInstanceUID']
            instance = DoGet(ORTHANC, '/instances/%s/tags?simplify' % i) ['SOPInstanceUID']

            a = DoPost(ORTHANC, '/dicom-web/servers/sample/get', {
                'Uri' : '/studies/%s/series/%s/instances/%s/rendered' % (study, series, instance)
            })
            
            im = UncompressImage(a)
            self.assertEqual("L", im.mode)
            self.assertEqual(256, im.size[0])
            self.assertEqual(256, im.size[1])

            b = DoPost(ORTHANC, '/dicom-web/servers/sample/get', {
                'Uri' : '/studies/%s/series/%s/rendered' % (study, series)
            })
            
            self.assertEqual(len(a), len(b))
            self.assertEqual(a, b)

            c = DoPost(ORTHANC, '/dicom-web/servers/sample/get', {
                'Uri' : '/studies/%s/rendered' % study
            })
            
            self.assertEqual(len(a), len(c))
            self.assertEqual(a, c)



    def test_multiple_mime_accept_wado_rs(self):
        # "Multiple MIME type Accept Headers for Wado-RS"
        # https://groups.google.com/forum/#!msg/orthanc-users/P3B6J9abZpE/syn5dnW2AwAJ

        UploadInstance(ORTHANC, 'DummyCT.dcm')
        study = '1.2.840.113619.2.176.2025.1499492.7391.1171285944.390'

        self.assertEqual(1, len(DoGet(ORTHANC, '/dicom-web/studies/%s/metadata' % study)))
        
        self.assertEqual(1, len(DoGet(ORTHANC, '/dicom-web/studies/%s/metadata' % study,
                                      headers = { 'Accept' : 'application/json, application/dicom+json' })))
        
        self.assertEqual(1, len(DoGet(ORTHANC, '/dicom-web/studies/%s/metadata' % study,
                                      headers = { 'Accept' : 'application/json' })))
        
        self.assertEqual(1, len(DoGet(ORTHANC, '/dicom-web/studies/%s/metadata' % study,
                                      headers = { 'Accept' : 'application/dicom+json' })))
        
        self.assertEqual(1, len(DoGet(ORTHANC, '/dicom-web/studies/%s/metadata' % study,
                                      headers = { 'Accept' : 'toto, application/dicom+json' })))
        
        self.assertEqual(1, len(DoGet(ORTHANC, '/dicom-web/studies/%s/metadata' % study,
                                      headers = { 'Accept' : 'application/json, tata' })))
        
        self.assertRaises(Exception, lambda: DoGet(ORTHANC, '/dicom-web/studies/%s/metadata' % study,
                                                   headers = { 'Accept' : 'toto' }))
        
        self.assertRaises(Exception, lambda: DoGet(ORTHANC, '/dicom-web/studies/%s/metadata' % study,
                                                   headers = { 'Accept' : 'toto, tata' }))

        # https://groups.google.com/d/msg/orthanc-users/9o5kItsMQI0/Og6B27YyBgAJ
        self.assertEqual(1, len(DoGetMultipart(ORTHANC, '/dicom-web/studies/%s/metadata' % study,
                                               headers = { 'Accept' : 'multipart/related;type=application/dicom+xml' })))

        self.assertEqual(1, len(DoGet(ORTHANC, '/dicom-web/studies/%s/metadata' % study,
                                      headers = { 'Accept' : 'application/json, application/dicom+xml' })))

        self.assertEqual(1, len(DoGet(ORTHANC, '/dicom-web/studies/%s/metadata' % study,
                                      headers = { 'Accept' : 'application/dicom+xml, application/json' })))



    def test_bitbucket_issue_56(self):
        # "Case-insensitive matching over accents" => DICOMweb part
        # from AlexanderM on 2020-03-20
        # https://orthanc.uclouvain.be/bugs/show_bug.cgi?id=56
        UploadInstance(ORTHANC, 'Issue56-NoPixelData.dcm')

        self.assertEqual(1, len(DoPost(ORTHANC, '/tools/find', {
            'Level' : 'Patient',
            'Query' : {
                'PatientName' : 'Гусева*',
            },
        })))

        self.assertEqual(1, len(DoPost(ORTHANC, '/tools/find', {
            'Level' : 'Patient',
            'Query' : {
                'PatientName' : 'гусева*',
            },
        })))

        self.assertEqual(1, len(DoGet(ORTHANC, u'/dicom-web/studies?PatientName=Гусева*',
                                      headers = { 'accept' : 'application/json' })))

        # This line is the issue
        self.assertEqual(1, len(DoGet(ORTHANC, u'/dicom-web/studies?PatientName=гусева*',
                                      headers = { 'accept' : 'application/json' })))


    def test_frames_transcoding(self):
        ACCEPT = {
            '1.2.840.10008.1.2' : 'multipart/related; type=application/octet-stream; transfer-syntax=1.2.840.10008.1.2',
            '1.2.840.10008.1.2.1' : 'multipart/related; type=application/octet-stream; transfer-syntax=1.2.840.10008.1.2.1',
            '1.2.840.10008.1.2.4.50' : 'multipart/related; type=image/jpeg; transfer-syntax=1.2.840.10008.1.2.4.50',
            '1.2.840.10008.1.2.4.51' : 'multipart/related; type=image/jpeg; transfer-syntax=1.2.840.10008.1.2.4.51',
            '1.2.840.10008.1.2.4.57' : 'multipart/related; type=image/jpeg; transfer-syntax=1.2.840.10008.1.2.4.57',
            '1.2.840.10008.1.2.4.70' : 'multipart/related; type=image/jpeg; transfer-syntax=1.2.840.10008.1.2.4.70',
            }

        uri = 'dicom-web%s' % UploadAndGetWadoPath('TransferSyntaxes/1.2.840.10008.1.2.4.50.dcm')
        truthRGB = Image.open(GetDatabasePath('TransferSyntaxes/1.2.840.10008.1.2.4.50.png'))

        # TODO
        # # starting from X.XX.X, Orthanc won't convert YBR to RGB anymore -> new checksum (https://discourse.orthanc-server.org/t/orthanc-convert-ybr-to-rgb-but-does-not-change-metadata/3533)
        # with open(GetDatabasePath('TransferSyntaxes/1.2.840.10008.1.2.4.50.YBR.raw'), 'rb') as f:  
        #     truthRawYbr = f.read()

        # first test: no transcoding since we accept the JPEG transfer syntax
        a = DoGetMultipart(ORTHANC, '%s/frames/1' % uri,
                           headers = { 'Accept' : ACCEPT['1.2.840.10008.1.2.4.50'] },
                           returnHeaders = True)
        self.assertEqual(1, len(a))
        self.assertEqual(2, len(a[0]))
        self.assertEqual('%s%s/frames/1' % (ORTHANC['Url'], uri),
                         a[0][1]['Content-Location'])
        self.assertEqual(ACCEPT['1.2.840.10008.1.2.4.50'],
                         'multipart/related; type=%s' % a[0][1]['Content-Type'])
        self.assertEqual(53476, len(a[0][0]))
        self.assertEqual('142fdb8a1dc2aa7e6b8952aa294a6e22', ComputeMD5(a[0][0]))

        # second test: no accept header -> defaults to raw explicit
        a = DoGetMultipart(ORTHANC, '%s/frames/1' % uri)
        self.assertEqual(1, len(a))
        self.assertEqual(480 * 640 * 3, len(a[0]))

        # Orthanc is now returning the YBR image instead of the RGB
        # TODO
        # # starting from X.XX.X, Orthanc won't convert YBR to RGB anymore -> new checksum (https://discourse.orthanc-server.org/t/orthanc-convert-ybr-to-rgb-but-does-not-change-metadata/3533)
        # if IsOrthancVersionAbove(ORTHANC, 1, XX, 1) and not HasGdcmPlugin(ORTHANC):
        #     # GetMaxImageDifference does not work with YBR images -> strict comparison with the output of dcmdjpeg
        #     self.assertEqual('d4aacc6c7758c7c968a4fc8d59b041d5', ComputeMD5(a[0]))
        # else:
        # http://effbot.org/zone/pil-comparing-images.htm
        img = Image.frombytes('RGB', [ 640, 480 ], a[0])
        self.assertLessEqual(GetMaxImageDifference(img, truthRGB), 2)

        ACCEPT2 = copy.deepcopy(ACCEPT)
        if HasGdcmPlugin(ORTHANC):
            IS_GDCM = True
            ACCEPT2['1.2.840.10008.1.2.1'] = 'multipart/related; type=application/octet-stream'
            del ACCEPT2['1.2.840.10008.1.2']
        else:
            if not IsOrthancVersionAbove(ORTHANC, 1, 12, 1):
                self.assertEqual('dfdc79f5070926bbb8ac079ee91f5b91', ComputeMD5(a[0]))
            IS_GDCM = False

        a = DoGetMultipart(ORTHANC, '%s/frames/1' % uri,
                           headers = { 'Accept' : ACCEPT2['1.2.840.10008.1.2.1'] })
        self.assertEqual(1, len(a))
        self.assertEqual(480 * 640 * 3, len(a[0]))

        # TODO
        # # starting from X.XX.X, Orthanc won't convert YBR to RGB anymore -> new checksum (https://discourse.orthanc-server.org/t/orthanc-convert-ybr-to-rgb-but-does-not-change-metadata/3533)
        # if IsOrthancVersionAbove(ORTHANC, 1, XX, X) and not HasGdcmPlugin(ORTHANC):
        #     # GetMaxImageDifference does not work with YBR images -> strict comparison with the output of dcmdjpeg
        #     self.assertEqual('d4aacc6c7758c7c968a4fc8d59b041d5', ComputeMD5(a[0]))
        # else:
        # http://effbot.org/zone/pil-comparing-images.htm
        img = Image.frombytes('RGB', [ 640, 480 ], a[0])
        self.assertLessEqual(GetMaxImageDifference(img, truthRGB), 2)

        # TODO:  if not IS_GDCM and not IsOrthancVersionAbove(ORTHANC, 1, XX, X):
        if not IS_GDCM:
            self.assertEqual('dfdc79f5070926bbb8ac079ee91f5b91', ComputeMD5(a[0]))


        # Test download using the same transfer syntax
        RESULTS = {
            '1.2.840.10008.1.2' : 'f54c7ea520ab3ec32b6303581ecd262f',
            '1.2.840.10008.1.2.1' : '4b350b9353a93c747917c7c3bf9b8f44',
            '1.2.840.10008.1.2.4.50' : '142fdb8a1dc2aa7e6b8952aa294a6e22',
            '1.2.840.10008.1.2.4.51' : '8b37945d75f9d2899ed868bdba429a0d',
            '1.2.840.10008.1.2.4.57' : '75c84823eddb560d127b1d24c9406f30',
            '1.2.840.10008.1.2.4.70' : '2c35726328f0200396e583a0038b0269',
        }

        if IS_GDCM:
            # This file was failing with GDCM, as it has 2 fragments,
            # and only the first one was returned => the MD5 below is BAD
            #RESULTS['1.2.840.10008.1.2.4.51'] = '901963a322a817946b074f9ed0afa060'
            pass
            
        for syntax in ACCEPT2:
            uri = '/dicom-web%s' % UploadAndGetWadoPath('TransferSyntaxes/%s.dcm' % syntax)
            a = DoGetMultipart(ORTHANC, '%s/frames/1' % uri,
                               headers = { 'Accept' : ACCEPT2[syntax] })
            self.assertEqual(1, len(a))
            self.assertEqual(RESULTS[syntax], ComputeMD5(a[0]))

        # Test transcoding to all the possible transfer syntaxes
        uri = 'dicom-web%s' % UploadAndGetWadoPath('KarstenHilbertRF.dcm')
        for syntax in ACCEPT2:
            a = DoGetMultipart(ORTHANC, '%s/frames/1' % uri,
                               headers = { 'Accept' : ACCEPT2[syntax] },
                               returnHeaders = True)
            self.assertEqual(1, len(a))
            self.assertEqual(2, len(a[0]))
            self.assertEqual('%s%s/frames/1' % (ORTHANC['Url'], uri),
                             a[0][1]['Content-Location'])
            self.assertEqual(ACCEPT[syntax],
                             'multipart/related; type=%s' % a[0][1]['Content-Type'])
            if IS_GDCM:  # !!! NOTE: these tests might fail if GDCM is not used to transcode ALL transfer syntaxes.  And, from v1.8, the default configuration handles only JP2K 
                self.assertEqual({
                    '1.2.840.10008.1.2' : '1c8cebde0c74450ce4dfb75dd52ddad7',
                    '1.2.840.10008.1.2.1' : '1c8cebde0c74450ce4dfb75dd52ddad7',
                    '1.2.840.10008.1.2.4.50' : 'f4d145e5f33fbd39375ce0f91453d6cc',
                    '1.2.840.10008.1.2.4.51' : 'f4d145e5f33fbd39375ce0f91453d6cc',
                    '1.2.840.10008.1.2.4.57' : 'dc55800ce1a8ac556c266cdb26d75757',
                    '1.2.840.10008.1.2.4.70' : 'dc55800ce1a8ac556c266cdb26d75757',
                    } [syntax], ComputeMD5(a[0][0]))
            else:
                self.assertEqual({
                    '1.2.840.10008.1.2' : '1c8cebde0c74450ce4dfb75dd52ddad7',
                    '1.2.840.10008.1.2.1' : '1c8cebde0c74450ce4dfb75dd52ddad7',
                    '1.2.840.10008.1.2.4.50' : '0a0ab74fe7c68529bdd416fc9e5e742a',
                    '1.2.840.10008.1.2.4.51' : '33d1ab2fe169c5b5ba932a9bbc3c6306',
                    '1.2.840.10008.1.2.4.57' : '3d21c969da846ca41e0498a0dcfad061',
                    '1.2.840.10008.1.2.4.70' : '49d5353c8673208629847ad45a855557',
                    } [syntax], ComputeMD5(a[0][0]))


        # JPEG image with many fragments for 2 frames        
        uri = '/dicom-web%s' % UploadAndGetWadoPath('LenaTwiceWithFragments.dcm')

        a = DoGetMultipart(ORTHANC, '%s/frames/1' % uri,
                           headers = { 'Accept' : ACCEPT['1.2.840.10008.1.2.4.50'] })
        self.assertEqual(1, len(a))
        self.assertEqual(69214, len(a[0]))
        self.assertEqual('0eaf36d4881c513ca70b6684bfaa5b08', ComputeMD5(a[0]))
        
        b = DoGetMultipart(ORTHANC, '%s/frames/2' % uri,
                           headers = { 'Accept' : ACCEPT['1.2.840.10008.1.2.4.50'] })
        self.assertEqual(1, len(b))
        self.assertEqual(a[0], b[0])
        
        b = DoGetMultipart(ORTHANC, '%s/frames/1,2' % uri,
                           headers = { 'Accept' : ACCEPT['1.2.840.10008.1.2.4.50'] })
        self.assertEqual(2, len(b))
        self.assertEqual(a[0], b[0])
        self.assertEqual(a[0], b[1])


    def test_wado_transcoding(self):
        uri = '/dicom-web%s' % UploadAndGetWadoPath('TransferSyntaxes/1.2.840.10008.1.2.4.50.dcm')

        compressedSize = os.path.getsize(GetDatabasePath('TransferSyntaxes/1.2.840.10008.1.2.4.50.dcm'))

        self.assertRaises(Exception, lambda: DoGetMultipart(ORTHANC, '%s' % uri,
                                                            headers = { 'Accept' : 'nope' }))

        # Up to release 1.5 of the DICOMweb plugin, if no
        # transfer-syntax was specified, no transcoding occured. This
        # was because of an undefined behavior up to DICOM
        # 2016b. Starting with DICOM 2016c, the standard explicitly
        # states that the image should be transcoded to Little Endian
        # Explicit.
        a = DoGetMultipart(ORTHANC, '%s' % uri,
                           headers = { })
        self.assertEqual(1, len(a))
        self.assertEqual('1.2.840.10008.1.2.1', GetTransferSyntax(a[0]))
        self.assertTrue(10 * compressedSize < len(a[0]))
        uncompressedSize = len(a[0])
        
        a = DoGetMultipart(ORTHANC, '%s' % uri,
                           headers = { 'Accept' : 'multipart/related' })
        self.assertEqual(1, len(a))
        self.assertEqual('1.2.840.10008.1.2.1', GetTransferSyntax(a[0]))
        self.assertEqual(uncompressedSize, len(a[0]))

        a = DoGetMultipart(ORTHANC, '%s' % uri,
                           headers = { 'Accept' : 'multipart/related; type=application/dicom' })
        self.assertEqual(1, len(a))
        self.assertEqual('1.2.840.10008.1.2.1', GetTransferSyntax(a[0]))
        self.assertEqual(uncompressedSize, len(a[0]))

        a = DoGetMultipart(ORTHANC, '%s' % uri,
                           headers = { 'Accept' : 'multipart/related; type=application/dicom; transfer-syntax=*' })
        self.assertEqual(1, len(a))
        self.assertEqual('1.2.840.10008.1.2.4.50', GetTransferSyntax(a[0]))
        self.assertEqual(compressedSize, len(a[0]))

        # Use source transfer syntax
        a = DoGetMultipart(ORTHANC, '%s' % uri,
                           headers = { 'Accept' : 'multipart/related; type=application/dicom; transfer-syntax=1.2.840.10008.1.2.4.50' })
        self.assertEqual(1, len(a))
        self.assertEqual('1.2.840.10008.1.2.4.50', GetTransferSyntax(a[0]))
        self.assertEqual(compressedSize, len(a[0]))

        a = DoGetMultipart(ORTHANC, '%s' % uri,
                           headers = { 'Accept' : 'multipart/related; type=application/dicom; transfer-syntax=1.2.840.10008.1.2.1' })
        self.assertEqual(1, len(a))
        self.assertEqual('1.2.840.10008.1.2.1', GetTransferSyntax(a[0]))
        self.assertEqual(uncompressedSize, len(a[0]))

        # Transcoding
        a = DoGetMultipart(ORTHANC, '%s' % uri,
                           headers = { 'Accept' : 'multipart/related; type=application/dicom; transfer-syntax=1.2.840.10008.1.2.4.57' })
        self.assertEqual(1, len(a))
        self.assertEqual('1.2.840.10008.1.2.4.57', GetTransferSyntax(a[0]))
        self.assertNotEqual(compressedSize, len(a[0]))
        self.assertNotEqual(uncompressedSize, len(a[0]))

        
    def test_compare_wado_uri_and_rs(self):
        # https://groups.google.com/d/msg/orthanc-users/mKgr2QAKTCU/R7u4I1LvBAAJ

        # Image "2020-08-12-Christopher.dcm" corresponds to the result of:
        #  $ gdcmconv --raw 1.2.840.113704.9.1000.16.2.20190613104005642000100010001.dcm 2020-08-12-Christopher.dcm
        # Image "2020-08-12-Christopher.png" corresponds to "2.png"
        
        i = UploadInstance(ORTHANC, '2020-08-12-Christopher.dcm') ['ID']
        STUDY = '1.2.840.113704.9.1000.16.0.20190613103939444'
        SERIES = '1.2.840.113704.9.1000.16.1.2019061310394289000010001'
        INSTANCE = '1.2.840.113704.9.1000.16.2.20190613104005642000100010001'

        with open(GetDatabasePath('2020-08-12-Christopher.png'), 'rb') as f:
            truth = UncompressImage(f.read())
        
        im1 = GetImage(ORTHANC, args.wado + '?requestType=WADO&objectUID=%s&contentType=image/jpg' % INSTANCE)
        self.assertEqual('JPEG', im1.format)
        
        im2 = GetImage(ORTHANC, args.wado + '?requestType=WADO&objectUID=%s&contentType=image/png' % INSTANCE)
        self.assertEqual('PNG', im2.format)
        
        im3 = GetImage(ORTHANC, '/dicom-web/studies/%s/series/%s/instances/%s/frames/1/rendered?window=200,800,linear' % (STUDY, SERIES, INSTANCE))
        self.assertEqual('JPEG', im3.format)

        im4 = GetImage(ORTHANC, '/dicom-web/studies/%s/series/%s/instances/%s/rendered?window=200,800,linear' % (STUDY, SERIES, INSTANCE),
                       headers = { 'Accept' : 'image/png' })
        self.assertEqual('PNG', im4.format)

        im5 = GetImage(ORTHANC, '/instances/%s/rendered' % i, { 'Accept' : 'image/jpeg' })
        self.assertEqual('JPEG', im5.format)

        im6 = GetImage(ORTHANC, '/instances/%s/rendered' % i)
        self.assertEqual('PNG', im6.format)

        for im in [ truth, im1, im2, im3, im4, im5, im6 ]:
            self.assertEqual('L', im.mode)
            self.assertEqual(512, im.size[0])
            self.assertEqual(512, im.size[1])

        # The following fails in DICOMweb plugin <= 1.2, as "/rendered"
        # was redirecting to the "/preview" route of Orthanc
        # http://effbot.org/zone/pil-comparing-images.htm
        self.assertLess(ImageChops.difference(im1, im3).getextrema() [1], 10)
        self.assertLess(ImageChops.difference(im2, im4).getextrema() [1], 2)
        self.assertLess(ImageChops.difference(im3, im5).getextrema() [1], 10)
        self.assertLess(ImageChops.difference(im4, im6).getextrema() [1], 2)
        self.assertTrue(ImageChops.difference(im1, im5).getbbox() is None)
        self.assertTrue(ImageChops.difference(im2, im6).getbbox() is None)

        bbox = ImageChops.difference(im2, truth).getbbox()
        if bbox != None:
            # Tolerance of just 1 pixel of difference (needed on Windows)
            #print(im2.getpixel((238,275)))   # => 255
            #print(truth.getpixel((238,275))) # => 254
            self.assertLessEqual(abs(bbox[2] - bbox[0]), 1)
            self.assertLessEqual(abs(bbox[3] - bbox[1]), 1)


    def test_issue_195(self):
        # This fails on Orthanc <= 1.9.2
        # https://orthanc.uclouvain.be/bugs/show_bug.cgi?id=195
        a = UploadInstance(ORTHANC, 'Issue195.dcm') ['ID']
        b = DoGet(ORTHANC, 'dicom-web/studies/1.2.276.0.7230010.3.1.2.8323329.13188.1620309604.848733/series/1.2.276.0.7230010.3.1.3.8323329.13188.1620309604.848734/instances/1.2.276.0.7230010.3.1.4.8323329.13188.1620309604.848735/metadata',
                  headers = { 'Accept' : 'application/dicom+json' })

        self.assertEqual(1, len(b))
        self.assertEqual(5, len(b[0]))
        
        # The expected result can be found by typing "dcm2json Database/Issue195.dcm"
        self.assertEqual(2, len(b[0]["00080018"]))
        self.assertEqual("UI", b[0]["00080018"]["vr"])
        self.assertEqual("1.2.276.0.7230010.3.1.4.8323329.13188.1620309604.848735",
                         b[0]["00080018"]["Value"][0])

        self.assertEqual(2, len(b[0]["0020000D"]))
        self.assertEqual("UI", b[0]["0020000D"]["vr"])
        self.assertEqual("1.2.276.0.7230010.3.1.2.8323329.13188.1620309604.848733",
                         b[0]["0020000D"]["Value"][0])

        self.assertEqual(2, len(b[0]["0020000E"]))
        self.assertEqual("UI", b[0]["0020000E"]["vr"])
        self.assertEqual("1.2.276.0.7230010.3.1.3.8323329.13188.1620309604.848734",
                         b[0]["0020000E"]["Value"][0])

        self.assertEqual(1, len(b[0]["00081030"]))  # Case of an empty value
        self.assertEqual("LO", b[0]["00081030"]["vr"])

        self.assertEqual(2, len(b[0]["0008103E"]))
        self.assertEqual("LO", b[0]["0008103E"]["vr"])
        self.assertEqual("Hello1", b[0]["0008103E"]["Value"][0])


        DoDelete(ORTHANC, 'instances/%s' % a)
        a = UploadInstance(ORTHANC, 'Issue195-bis.dcm') ['ID']
        URI = 'dicom-web/studies/1.2.276.0.7230010.3.1.2.8323329.6792.1625504071.652468/series/1.2.276.0.7230010.3.1.3.8323329.6792.1625504071.652469/instances/1.2.276.0.7230010.3.1.4.8323329.6792.1625504071.652470'
        b = DoGet(ORTHANC, '%s/metadata' % URI,
                  headers = { 'Accept' : 'application/dicom+json' })
        
        self.assertEqual(1, len(b))
        self.assertEqual(5, len(b[0]))

        # The expected result can be found by typing "dcm2json ../../Database/Issue195-bis.dcm"
        self.assertEqual(2, len(b[0]["00080018"]))
        self.assertEqual("UI", b[0]["00080018"]["vr"])
        self.assertEqual("1.2.276.0.7230010.3.1.4.8323329.6792.1625504071.652470",
                         b[0]["00080018"]["Value"][0])

        self.assertEqual(2, len(b[0]["0020000D"]))
        self.assertEqual("UI", b[0]["0020000D"]["vr"])
        self.assertEqual("1.2.276.0.7230010.3.1.2.8323329.6792.1625504071.652468",
                         b[0]["0020000D"]["Value"][0])

        self.assertEqual(2, len(b[0]["0020000E"]))
        self.assertEqual("UI", b[0]["0020000E"]["vr"])
        self.assertEqual("1.2.276.0.7230010.3.1.3.8323329.6792.1625504071.652469",
                         b[0]["0020000E"]["Value"][0])

        self.assertEqual(2, len(b[0]["00084567"]))
        self.assertEqual("UN", b[0]["00084567"]["vr"])
        self.assertEqual('http://%s:%s%s' % (args.server, args.rest, '/%s/bulk/00084567' % URI),
                         b[0]["00084567"]["BulkDataURI"])

        c = DoGet(ORTHANC, '%s/bulk/00084567' % URI)
        self.assertTrue('Content-Length: 2\r\n' in c)
        index = c.find('\r\n\r\n')
        self.assertEqual(0x42, ord(c[index + 4]))
        self.assertEqual(0x00, ord(c[index + 5]))

        # Case of an empty value, fails in Orthanc <= 1.9.2 because of issue #195
        self.assertEqual(1, len(b[0]["00084565"]))
        self.assertEqual("UN", b[0]["00084565"]["vr"])
        
        


    def test_multiframe_windowing(self):
        # Fixed in DICOMweb 1.7
        def GetLinear(x, c, w):
            # http://dicom.nema.org/MEDICAL/dicom/2019a/output/chtml/part03/sect_C.11.2.html#sect_C.11.2.1.2.1
            ymin = 0.0
            ymax = 255.0
            if float(x) <= float(c) - 0.5 - (float(w) - 1.0) / 2.0:
                return ymin
            elif float(x) > float(c) - 0.5 + (float(w) - 1.0) / 2.0 :
                return ymax
            else:
                return ((float(x) - (float(c) - 0.5)) / (float(w) - 1.0) + 0.5) * (ymax - ymin) + ymin

        def GetLinearExact(x, c, w):
            # http://dicom.nema.org/MEDICAL/dicom/2019a/output/chtml/part03/sect_C.11.2.html#sect_C.11.2.1.3.2
            ymin = 0.0
            ymax = 255.0
            if float(x) <= float(c) - float(w) / 2.0:
                return ymin
            elif float(x) > float(c) + float(w) / 2.0:
                return ymax
            else:
                return (float(x) - float(c)) / float(w) * (ymax- ymin) + ymin

        def GetSigmoid(x, c, w):
            # http://dicom.nema.org/MEDICAL/dicom/2019a/output/chtml/part03/sect_C.11.2.html#sect_C.11.2.1.3.1
            ymin = 0.0
            ymax = 255.0
            return (ymax - ymin) / (1.0 + math.exp(-4 * (float(x) - float(c)) / float(w)))

        self.assertAlmostEqual(GetLinear(10, 0, 100), 154.54545454545456)
        self.assertAlmostEqual(GetLinear(-1000, 2048, 4096), 0)
        self.assertAlmostEqual(GetLinear(5096, 2048, 4096), 255)
        self.assertAlmostEqual(GetLinear(333, 2048, 4096), 20.7362637362637)
        self.assertAlmostEqual(GetLinear(16, 127, 256), 17)

        self.assertAlmostEqual(GetLinearExact(-1000, 2048, 4096), 0)
        self.assertAlmostEqual(GetLinearExact(5096, 2048, 4096), 255)
        self.assertAlmostEqual(GetLinearExact(150, 127, 256), 22.91015625)

        self.assertAlmostEqual(GetSigmoid(150, 127, 256), 150.166728345797)

        UploadInstance(ORTHANC, 'MultiframeWindowing.dcm')
        STUDY = '1.2.840.113619.2.176.2025.1499492.7391.1175285944.390'
        SERIES = '1.2.840.113619.2.176.2025.1499492.7391.1175285944.394'
        INSTANCE = '1.2.840.113619.2.176.2025.1499492.7040.1175286242.109'

        im = GetImage(ORTHANC, '/dicom-web/studies/%s/series/%s/instances/%s/frames/1/rendered?window=127,256,linear' % (STUDY, SERIES, INSTANCE))
        self.assertLessEqual(abs(GetLinear(0x00, 127, 256) - im.getpixel((0, 0))), 1)
        self.assertLessEqual(abs(GetLinear(0x10, 127, 256) - im.getpixel((1, 0))), 1)
        self.assertLessEqual(abs(GetLinear(0x20, 127, 256) - im.getpixel((0, 1))), 1.1)
        self.assertLessEqual(abs(GetLinear(0x30, 127, 256) - im.getpixel((1, 1))), 1.1)

        im = GetImage(ORTHANC, '/dicom-web/studies/%s/series/%s/instances/%s/frames/1/rendered?window=0,256,linear-exact' % (STUDY, SERIES, INSTANCE))
        self.assertLessEqual(abs(GetLinearExact(0x00, 0, 256) - im.getpixel((0, 0))), 1)
        self.assertLessEqual(abs(GetLinearExact(0x10, 0, 256) - im.getpixel((1, 0))), 1)
        self.assertLessEqual(abs(GetLinearExact(0x20, 0, 256) - im.getpixel((0, 1))), 1.2)
        self.assertLessEqual(abs(GetLinearExact(0x30, 0, 256) - im.getpixel((1, 1))), 1.2)

        im = GetImage(ORTHANC, '/dicom-web/studies/%s/series/%s/instances/%s/frames/1/rendered?window=127,256,sigmoid' % (STUDY, SERIES, INSTANCE))
        self.assertLessEqual(abs(GetSigmoid(0x00, 127, 256) - im.getpixel((0, 0))), 3)
        self.assertLessEqual(abs(GetSigmoid(0x10, 127, 256) - im.getpixel((1, 0))), 1)
        self.assertLessEqual(abs(GetSigmoid(0x20, 127, 256) - im.getpixel((0, 1))), 1)
        self.assertLessEqual(abs(GetSigmoid(0x30, 127, 256) - im.getpixel((1, 1))), 1)

        im = GetImage(ORTHANC, '/dicom-web/studies/%s/series/%s/instances/%s/frames/1/rendered?window=16,128,linear' % (STUDY, SERIES, INSTANCE))
        self.assertLessEqual(abs(GetLinear(0x00, 16, 128) - im.getpixel((0, 0))), 1)
        self.assertLessEqual(abs(GetLinear(0x10, 16, 128) - im.getpixel((1, 0))), 1)
        self.assertLessEqual(abs(GetLinear(0x20, 16, 128) - im.getpixel((0, 1))), 2)
        self.assertLessEqual(abs(GetLinear(0x30, 16, 128) - im.getpixel((1, 1))), 2)

        im = GetImage(ORTHANC, '/dicom-web/studies/%s/series/%s/instances/%s/frames/2/rendered?window=127,256,linear' % (STUDY, SERIES, INSTANCE))
        ri = 100.0
        rs = 1.0
        self.assertLessEqual(abs(GetLinear(0x00 * rs + ri, 127, 256) - im.getpixel((0, 0))), 1)
        self.assertLessEqual(abs(GetLinear(0x10 * rs + ri, 127, 256) - im.getpixel((1, 0))), 1)
        self.assertLessEqual(abs(GetLinear(0x20 * rs + ri, 127, 256) - im.getpixel((0, 1))), 1)
        self.assertLessEqual(abs(GetLinear(0x30 * rs + ri, 127, 256) - im.getpixel((1, 1))), 1)

        im = GetImage(ORTHANC, '/dicom-web/studies/%s/series/%s/instances/%s/frames/3/rendered?window=127,256,linear' % (STUDY, SERIES, INSTANCE))
        ri = 0.0
        rs = 2.0
        self.assertLessEqual(abs(GetLinear(0x00 * rs + ri, 127, 256) - im.getpixel((0, 0))), 1)
        self.assertLessEqual(abs(GetLinear(0x10 * rs + ri, 127, 256) - im.getpixel((1, 0))), 1.1)
        self.assertLessEqual(abs(GetLinear(0x20 * rs + ri, 127, 256) - im.getpixel((0, 1))), 1)
        self.assertLessEqual(abs(GetLinear(0x30 * rs + ri, 127, 256) - im.getpixel((1, 1))), 1)

        im = GetImage(ORTHANC, '/dicom-web/studies/%s/series/%s/instances/%s/frames/4/rendered?window=127,256,linear' % (STUDY, SERIES, INSTANCE))
        ri = 100.0
        rs = 2.0
        self.assertLessEqual(abs(GetLinear(0x00 * rs + ri, 127, 256) - im.getpixel((0, 0))), 1)
        self.assertLessEqual(abs(GetLinear(0x10 * rs + ri, 127, 256) - im.getpixel((1, 0))), 1)
        self.assertLessEqual(abs(GetLinear(0x20 * rs + ri, 127, 256) - im.getpixel((0, 1))), 1)
        self.assertLessEqual(abs(GetLinear(0x30 * rs + ri, 127, 256) - im.getpixel((1, 1))), 1)


    def test_forwarded_headers(self):
        study = UploadInstance(ORTHANC, 'ColorTestImageJ.dcm')['ParentStudy']
        studyId = DoGet(ORTHANC, '/studies/%s' % study)['MainDicomTags']['StudyInstanceUID']

        m = DoGet(ORTHANC, '/dicom-web/studies/%s/metadata' % studyId)
        self.assertIn(ORTHANC['Url'], m[0][u'7FE00010']['BulkDataURI'])

        m = DoGet(ORTHANC, '/dicom-web/studies/%s/metadata' % studyId, headers= {
            'host': 'my-domain'
        })
        self.assertIn("http://my-domain/dicom-web", m[0][u'7FE00010']['BulkDataURI'])

        m = DoGet(ORTHANC, '/dicom-web/studies/%s/metadata' % studyId, headers= {
            'forwarded': 'host=my-domain;proto=https'
        })
        self.assertIn("https://my-domain/dicom-web", m[0][u'7FE00010']['BulkDataURI'])

        if IsPluginVersionAtLeast(ORTHANC, "dicom-web", 1, 13, 1):
            m = DoGet(ORTHANC, '/dicom-web/studies/%s/metadata' % studyId, headers= {
                'X-Forwarded-Host': 'my-domain',
                'X-Forwarded-Proto': 'https'
            })
            self.assertIn("https://my-domain/dicom-web", m[0][u'7FE00010']['BulkDataURI'])


    def test_full_mode_cache(self):
        study = UploadInstance(ORTHANC, 'ColorTestImageJ.dcm')['ParentStudy']
        studyId = DoGet(ORTHANC, '/studies/%s' % study)['MainDicomTags']['StudyInstanceUID']
        
        # wait for the StableSeries to happen to pre-compute the series/metadata
        time.sleep(4)

        m = DoGet(ORTHANC, '/dicom-web/studies/%s/metadata' % studyId)
        self.assertIn(ORTHANC['Url'], m[0][u'7FE00010']['BulkDataURI'])


    def test_issue_216(self):
        study = UploadInstance(ORTHANC, 'ColorTestImageJ.dcm')['ParentStudy']
        studyUid = DoGet(ORTHANC, '/studies/%s' % study)['MainDicomTags']['StudyInstanceUID']

        m = DoGet(ORTHANC, '/dicom-web/studies/%s/metadata' % studyUid, headers = {
            'accept': 'image/webp, */*;q=0.8, text/html, application/xhtml+xml, application/xml;q=0.9'
        })
        self.assertEqual(1, len(m))
        self.assertEqual(studyUid, m[0]['0020000D']['Value'][0])

        m = DoGet(ORTHANC, '/dicom-web/studies/%s/metadata' % studyUid, headers = {
            'accept': 'text/html, application/xhtml+xml, application/xml, image/webp, */*;q=0.8'
        })
        self.assertEqual(1, len(m))
        self.assertEqual(studyUid, m[0]['0020000D']['Value'][0])

        if IsPluginVersionAtLeast(ORTHANC, "dicom-web", 1, 13, 1) and IsOrthancVersionAbove(ORTHANC, 1, 12, 1):
            # This fails on DICOMweb <= 1.13 because of the "; q=.2",
            # since multiple accepts were not supported
            # https://orthanc.uclouvain.be/bugs/show_bug.cgi?id=216
            m = DoGet(ORTHANC, '/dicom-web/studies/%s/metadata' % studyUid, headers = {
                'accept': 'text/html, image/gif, image/jpeg, */*; q=.2, */*; q=.2'
            })
            self.assertEqual(1, len(m))
            self.assertEqual(studyUid, m[0]['0020000D']['Value'][0])

            # This fails on Orthanc <= 1.12.0 because of the ";q=0.9"
            m = DoGet(ORTHANC, '/dicom-web/studies/%s/metadata' % studyUid, headers = {
                'accept': 'text/html, application/xhtml+xml, application/xml;q=0.9, image/webp, */*;q=0.8'
            })
            self.assertEqual(1, len(m))
            self.assertEqual(studyUid, m[0]['0020000D']['Value'][0])


    def test_accept_negotiation(self):
        def CheckBadRequest(uri, accept):
            response = DoGetRaw(ORTHANC, uri, headers = {
                'accept': accept
            })
            self.assertEqual(int(response[0]['status']), 400)

        def CheckIsJson(uri, accept):
            if accept != None:
                response = DoGetRaw(ORTHANC, uri, headers = {
                    'accept': accept
                })
            else:
                response = DoGetRaw(ORTHANC, uri)
            self.assertEqual(int(response[0]['status']), 200)
            self.assertEqual(response[0]['content-type'], 'application/dicom+json')
            json.loads(response[1])

        def CheckIsXml(uri, accept):
            response = DoGetMultipart(ORTHANC, uri, headers = {
                'accept': accept
            }, returnHeaders = True)
            self.assertEqual(1, len(response))
            self.assertEqual(2, len(response[0]))
            self.assertEqual('application/dicom+xml', response[0][1]['Content-Type'])
            xml.dom.minidom.parseString(response[0][0])

        def CheckIsDicom(uri, accept):
            if accept != None:
                response = DoGetMultipart(ORTHANC, uri, headers = {
                    'accept': accept
                }, returnHeaders = True)
            else:
                response = DoGetMultipart(ORTHANC, uri, returnHeaders = True)
            self.assertEqual(1, len(response))
            self.assertEqual(2, len(response[0]))
            self.assertEqual('application/dicom', response[0][1]['Content-Type'])
            pydicom.dcmread(BytesIO(response[0][0]), force=True)

        def CheckIsBulk(uri, accept):
            if accept != None:
                response = DoGetMultipart(ORTHANC, uri, headers = {
                    'accept': accept
                }, returnHeaders = True)
            else:
                response = DoGetMultipart(ORTHANC, uri,  returnHeaders = True)
            self.assertEqual(1, len(response))
            self.assertEqual(2, len(response[0]))
            self.assertEqual('application/octet-stream', response[0][1]['Content-Type'])
            self.assertTrue(len(response[0][0]) > 1)

        study = UploadInstance(ORTHANC, 'ColorTestImageJ.dcm')['ParentStudy']
        studyUid = DoGet(ORTHANC, '/studies/%s' % study)['MainDicomTags']['StudyInstanceUID']

        CheckIsJson('/dicom-web/studies/%s/metadata' % studyUid, None)
        CheckBadRequest('/dicom-web/studies/%s/metadata' % studyUid, 'application/nope')
        CheckIsJson('/dicom-web/studies/%s/metadata' % studyUid, 'application/json')
        CheckIsJson('/dicom-web/studies/%s/metadata' % studyUid, 'application/dicom+json')
        CheckBadRequest('/dicom-web/studies/%s/metadata' % studyUid, 'multipart/related')
        CheckIsXml('/dicom-web/studies/%s/metadata' % studyUid, 'multipart/related; type=application/dicom+xml')
        CheckIsXml('/dicom-web/studies/%s/metadata' % studyUid, 'multipart/related; type="application/dicom+xml"')
        CheckBadRequest('/dicom-web/studies/%s/metadata' % studyUid, 'multipart/related; type="application/nope"')
        CheckBadRequest('/dicom-web/studies/%s/metadata' % studyUid, 'multipart/related; type=application/dicom+xml; transfer-syntax=nope')

        CheckBadRequest('/dicom-web/studies/%s' % studyUid, 'multipart/nope')
        CheckIsDicom('/dicom-web/studies/%s' % studyUid, None)
        CheckIsDicom('/dicom-web/studies/%s' % studyUid, 'multipart/related')
        CheckIsDicom('/dicom-web/studies/%s' % studyUid, 'multipart/related; type=application/dicom')
        CheckIsDicom('/dicom-web/studies/%s' % studyUid, 'multipart/related; type="application/dicom"')
        CheckBadRequest('/dicom-web/studies/%s' % studyUid, 'multipart/related; type=application/nope')
        CheckIsDicom('/dicom-web/studies/%s' % studyUid, 'multipart/related; transfer-syntax=*')
        CheckIsDicom('/dicom-web/studies/%s' % studyUid, 'multipart/related; type=application/dicom; transfer-syntax=*')
        CheckBadRequest('/dicom-web/studies/%s' % studyUid, 'multipart/related; transfer-syntax=nope')
        CheckIsDicom('/dicom-web/studies/%s' % studyUid, 'multipart/related; type=application/dicom; transfer-syntax=1.2.840.10008.1.2.1')

        uri = '/dicom-web/studies/%s/series/%s/instances/%s/bulk/0010,0010' % (
            studyUid, '1.3.12.2.1107.5.99.2.1255.30000007020811545343700000012',
            '1.2.276.0.7230010.3.1.4.2455711835.6056.1170936079.1')
        CheckIsBulk(uri, None)
        CheckBadRequest(uri, 'multipart/nope')
        CheckIsBulk(uri, 'multipart/related')
        CheckIsBulk(uri, 'multipart/related;type=application/octet-stream')
        CheckIsBulk(uri, 'multipart/related;   type =  "application/octet-stream"  ')
        CheckBadRequest(uri, 'multipart/related;   type =  "  application/octet-stream"  ')
        CheckBadRequest(uri, 'multipart/related;type=application/nope')
        CheckBadRequest(uri, 'multipart/related;range=')


try:
    print('\nStarting the tests...')
    unittest.main(argv = [ sys.argv[0] ] + args.options)

finally:
    print('\nDone')
