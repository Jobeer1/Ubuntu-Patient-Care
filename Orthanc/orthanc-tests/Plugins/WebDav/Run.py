#!/usr/bin/python3

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


# Note about easywebdav: This test is compatible with version 1.2.0 of
# the "python3-easywebdav" package in Ubuntu/Debian. Beware that this
# package includes a patch that is not available in the upstream
# version of easywebdav:
# https://salsa.debian.org/python-team/packages/python-easywebdav/-/blob/master/debian/patches/python3.patch

import argparse
import easywebdav
import io
import os
import pprint
import re
import sys
import unittest

# https://stackoverflow.com/a/49336105/881731
if ((3, 0) <= sys.version_info <= (3, 9)):
    from urllib.parse import unquote
elif ((2, 0) <= sys.version_info <= (2, 9)):
    from urlparse import unquote

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'Tests'))
from Toolbox import *


##
## Parse the command-line arguments
##

parser = argparse.ArgumentParser(description = 'Run the integration tests for the WebDAV server.')

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

WEBDAV = easywebdav.connect(args.server,
                            port = args.rest,
                            username = args.username,
                            password = args.password)


##
## The tests
##


def ListFiles(path, recursive):
    result = [ ]
    for i in WEBDAV.ls(path):
        if i.name == path:
            pass
        elif i.contenttype == '':
            if recursive:
                result += ListFiles(i.name + '/', True)
        else:
            result.append(i.name)
    return result


def GetFileInfo(path):
    for i in WEBDAV.ls(path[0 : path.rfind('/')]):
        if i.name == path:
            return i
    raise Exception('Cannot find: %s' % path)


def DownloadFile(path):
    with tempfile.NamedTemporaryFile(delete = False) as f:
        f.close()
        WEBDAV.download(path, f.name)
        with open(f.name, 'rb') as g:
            result = g.read()
        os.unlink(f.name)
        return result
    

class Orthanc(unittest.TestCase):
    def setUp(self):
        if (sys.version_info >= (3, 0)):
            # Remove annoying warnings about unclosed socket in Python 3
            import warnings
            warnings.simplefilter("ignore", ResourceWarning)

        DropOrthanc(ORTHANC)

        
    def test_root(self):
        self.assertEqual(6, len(WEBDAV.ls('/webdav/')))
        for i in WEBDAV.ls('/webdav/'):
            self.assertTrue(i.name in [
                '/webdav/',
                '/webdav/by-dates',
                '/webdav/by-patients',
                '/webdav/by-studies',
                '/webdav/by-uids',
                '/webdav/uploads'
            ])
            self.assertEqual(0, i.size)
            self.assertEqual('', i.contenttype)

        patients = WEBDAV.ls('/webdav/by-patients/')
        self.assertEqual(1, len(patients))
        self.assertEqual(patients[0].name, '/webdav/by-patients/')
        self.assertEqual(0, patients[0].size)
        self.assertEqual('', patients[0].contenttype)

        self.assertRaises(Exception, lambda: WEBDAV.delete('/webdav/nope'))
        self.assertRaises(Exception, lambda: WEBDAV.delete('/webdav/by-uids'))


    def test_upload(self):
        self.assertEqual(0, len(ListFiles('/webdav/uploads/', True)))

        uploads = WEBDAV.ls('/webdav/uploads/')
        for i in uploads:
            self.assertEqual(i.contenttype, '')  # Only folders are allowed
        
        self.assertEqual(0, len(DoGet(ORTHANC, '/studies')))
        WEBDAV.upload(GetDatabasePath('DummyCT.dcm'), '/webdav/uploads/DummyCT.dcm')

        while len(ListFiles('/webdav/uploads/', True)) > 1:
            time.sleep(0.1)
        time.sleep(0.1)  # Give some more delay to be sure that the store has succeeded (necessary for Wine)
        
        instances = DoGet(ORTHANC, '/instances?expand')
        self.assertEqual(1, len(instances))
        self.assertEqual('1.2.840.113619.2.176.2025.1499492.7040.1171286242.109',
                         instances[0]['MainDicomTags']['SOPInstanceUID'])

        
    def test_upload_folders(self):
        self.assertEqual(0, len(ListFiles('/webdav/uploads/', True)))
        self.assertEqual(0, len(DoGet(ORTHANC, '/studies')))

        try:
            WEBDAV.mkdir('/webdav/uploads/a')
        except:
            pass
        try:
            WEBDAV.mkdir('/webdav/uploads/b')
        except:
            pass

        WEBDAV.upload(GetDatabasePath('DummyCT.dcm'), '/webdav/uploads/a/DummyCT.dcm')
        WEBDAV.upload(GetDatabasePath('ColorTestMalaterre.dcm'), '/webdav/uploads/b/ColorTestMalaterre.dcm')
        
        while len(ListFiles('/webdav/uploads/', True)) > 1:
            time.sleep(0.1)
        time.sleep(0.1)  # Give some more delay to be sure that the store has succeeded (necessary for Wine)
        
        self.assertEqual(2, len(DoGet(ORTHANC, '/instances')))


    def test_by_uids(self):
        self.assertEqual(1, len(WEBDAV.ls('/webdav/by-uids/')))
        self.assertEqual(0, len(ListFiles('/webdav/by-uids/', True)))
        self.assertEqual(0, len(DoGet(ORTHANC, '/instances')))

        i = UploadInstance(ORTHANC, 'DummyCT.dcm')['ID']
        tags = DoGet(ORTHANC, '/instances/%s/tags?simplify' % i)
        studyUid = tags['StudyInstanceUID']
        seriesUid = tags['SeriesInstanceUID']
        sopUid = tags['SOPInstanceUID']

        self.assertEqual(0, len(ListFiles('/webdav/by-uids/', False)))
        self.assertEqual(1, len(ListFiles('/webdav/by-uids/%s/' % studyUid, False)))
        self.assertEqual(2, len(ListFiles('/webdav/by-uids/%s/%s/' % (studyUid, seriesUid), False)))

        content = ListFiles('/webdav/by-uids/', True)
        self.assertEqual(3, len(content))
        self.assertTrue(('/webdav/by-uids/%s/study.json' % studyUid) in content)
        self.assertTrue(('/webdav/by-uids/%s/%s/series.json' % (studyUid, seriesUid)) in content)
        self.assertTrue(('/webdav/by-uids/%s/%s/%s.dcm' % (studyUid, seriesUid, sopUid)) in content)

        # Deleting the virtual files "study|series.json" has no
        # effect, but is needed for recursive DELETE in some file explorers
        WEBDAV.delete('/webdav/by-uids/%s/study.json' % studyUid)
        WEBDAV.delete('/webdav/by-uids/%s/%s/series.json' % (studyUid, seriesUid))

        info = GetFileInfo('/webdav/by-uids/%s/study.json' % studyUid)
        self.assertEqual(info.contenttype, 'application/json')
        
        info = GetFileInfo('/webdav/by-uids/%s/%s/series.json' % (studyUid, seriesUid))
        self.assertEqual(info.contenttype, 'application/json')
        
        info = GetFileInfo('/webdav/by-uids/%s/%s/%s.dcm' % (studyUid, seriesUid, sopUid))
        self.assertEqual(info.contenttype, 'application/dicom')
        self.assertEqual(info.size, os.stat(GetDatabasePath('DummyCT.dcm')).st_size)

        a = DownloadFile('/webdav/by-uids/%s/%s/%s.dcm' % (studyUid, seriesUid, sopUid))
        self.assertEqual(len(a), info.size)

        with open(GetDatabasePath('DummyCT.dcm'), 'rb') as f:
            self.assertEqual(a, f.read())

        self.assertEqual(studyUid, json.loads(DownloadFile('/webdav/by-uids/%s/study.json' % studyUid))
                         ['MainDicomTags']['StudyInstanceUID'])

        self.assertEqual(seriesUid, json.loads(DownloadFile('/webdav/by-uids/%s/%s/series.json' % (studyUid, seriesUid)))
                         ['MainDicomTags']['SeriesInstanceUID'])

        self.assertEqual(1, len(DoGet(ORTHANC, '/instances')))
        WEBDAV.delete('/webdav/by-uids/%s/%s/%s.dcm' % (studyUid, seriesUid, sopUid))
        self.assertEqual(0, len(DoGet(ORTHANC, '/instances')))
        self.assertEqual(0, len(ListFiles('/webdav/by-uids/', True)))


    def test_by_patients(self):
        self.assertEqual(0, len(ListFiles('/webdav/by-dates/', True)))
        self.assertEqual(0, len(ListFiles('/webdav/by-patients/', True)))
        self.assertEqual(0, len(ListFiles('/webdav/by-studies/', True)))
        self.assertEqual(0, len(ListFiles('/webdav/by-uids/', True)))

        self.assertEqual(1, len(WEBDAV.ls('/webdav/by-patients/')))
        self.assertEqual(0, len(DoGet(ORTHANC, '/instances')))

        i = UploadInstance(ORTHANC, 'DummyCT.dcm')['ID']
        tags = DoGet(ORTHANC, '/instances/%s/tags?simplify' % i)
        patient = '%s - %s' % (tags['PatientID'], tags['PatientName'])
        study = '%s - %s' % (tags['StudyDate'], tags['StudyDescription'])
        series = '%s - %s' % (tags['Modality'], tags['SeriesDescription'])
        self.assertEqual('ozp00SjY2xG - KNIX', patient)
        self.assertEqual('20070101 - Knee (R)', study)
        self.assertEqual('MR - AX.  FSE PD', series)

        self.assertEqual(1, len(ListFiles('/webdav/by-dates/', True)))
        self.assertEqual(1, len(ListFiles('/webdav/by-patients/', True)))
        self.assertEqual(1, len(ListFiles('/webdav/by-studies/', True)))
        self.assertEqual(3, len(ListFiles('/webdav/by-uids/', True)))
        
        self.assertEqual(0, len(ListFiles('/webdav/by-patients/', False)))
        self.assertEqual(2, len(WEBDAV.ls('/webdav/by-patients/')))
        self.assertEqual(0, len(ListFiles('/webdav/by-patients/%s' % patient, False)))
        self.assertEqual(2, len(WEBDAV.ls('/webdav/by-patients/%s' % patient)))
        self.assertEqual(0, len(ListFiles('/webdav/by-patients/%s/%s' % (patient, study), False)))
        self.assertEqual(2, len(WEBDAV.ls('/webdav/by-patients/%s/%s' % (patient, study))))

        folder = '/webdav/by-patients/%s/%s/%s' % (patient, study, series)
        self.assertEqual(1, len(ListFiles(folder, False)))
        self.assertEqual(2, len(WEBDAV.ls(folder)))
        self.assertEqual('%s/%s.dcm' % (folder, i), unquote(ListFiles(folder, False) [0]))

        files = ListFiles('/webdav/by-patients/', True)
        self.assertEqual(1, len(files))
        self.assertEqual('%s/%s.dcm' % (folder, i), unquote(files[0]))
        
        a = DownloadFile('%s/%s.dcm' % (folder, i))
        with open(GetDatabasePath('DummyCT.dcm'), 'rb') as f:
            self.assertEqual(a, f.read())

        self.assertEqual(1, len(DoGet(ORTHANC, '/instances')))
        WEBDAV.delete('%s/%s.dcm' % (folder, i))
        self.assertEqual(0, len(DoGet(ORTHANC, '/instances')))

        self.assertEqual(0, len(ListFiles('/webdav/by-dates/', True)))
        self.assertEqual(0, len(ListFiles('/webdav/by-patients/', True)))
        self.assertEqual(0, len(ListFiles('/webdav/by-studies/', True)))
        self.assertEqual(0, len(ListFiles('/webdav/by-uids/', True)))


    def test_by_studies(self):
        self.assertEqual(0, len(ListFiles('/webdav/by-studies/', True)))
        self.assertEqual(1, len(WEBDAV.ls('/webdav/by-patients/')))
        self.assertEqual(0, len(DoGet(ORTHANC, '/instances')))

        i = UploadInstance(ORTHANC, 'DummyCT.dcm')['ID']
        tags = DoGet(ORTHANC, '/instances/%s/tags?simplify' % i)
        study = '%s - %s - %s' % (tags['PatientID'], tags['PatientName'], tags['StudyDescription'])
        series = '%s - %s' % (tags['Modality'], tags['SeriesDescription'])
        self.assertEqual('ozp00SjY2xG - KNIX - Knee (R)', study)
        self.assertEqual('MR - AX.  FSE PD', series)

        self.assertEqual(0, len(ListFiles('/webdav/by-studies/', False)))
        self.assertEqual(2, len(WEBDAV.ls('/webdav/by-studies/')))
        self.assertEqual(0, len(ListFiles('/webdav/by-studies/%s' % study, False)))
        self.assertEqual(2, len(WEBDAV.ls('/webdav/by-studies/%s' % study)))

        folder = '/webdav/by-studies/%s/%s' % (study, series)
        self.assertEqual(1, len(ListFiles(folder, False)))
        self.assertEqual(2, len(WEBDAV.ls(folder)))
        self.assertEqual('%s/%s.dcm' % (folder, i), unquote(ListFiles(folder, False) [0]))

        files = ListFiles('/webdav/by-studies/', True)
        self.assertEqual(1, len(files))
        self.assertEqual('%s/%s.dcm' % (folder, i), unquote(files[0]))

        a = DownloadFile('%s/%s.dcm' % (folder, i))
        with open(GetDatabasePath('DummyCT.dcm'), 'rb') as f:
            self.assertEqual(a, f.read())

        self.assertEqual(1, len(DoGet(ORTHANC, '/instances')))
        WEBDAV.delete('%s/%s.dcm' % (folder, i))
        self.assertEqual(0, len(DoGet(ORTHANC, '/instances')))
        self.assertEqual(0, len(ListFiles('/webdav/by-studies/', True)))


    def test_by_dates(self):
        self.assertEqual(0, len(ListFiles('/webdav/by-dates/', True)))
        self.assertEqual(1, len(WEBDAV.ls('/webdav/by-patients/')))
        self.assertEqual(0, len(DoGet(ORTHANC, '/instances')))

        i = UploadInstance(ORTHANC, 'DummyCT.dcm')['ID']
        tags = DoGet(ORTHANC, '/instances/%s/tags?simplify' % i)
        year = tags['StudyDate'][0:4]
        month = tags['StudyDate'][4:6]
        study = '%s - %s - %s' % (tags['PatientID'], tags['PatientName'], tags['StudyDescription'])
        series = '%s - %s' % (tags['Modality'], tags['SeriesDescription'])
        self.assertEqual('ozp00SjY2xG - KNIX - Knee (R)', study)
        self.assertEqual('MR - AX.  FSE PD', series)

        self.assertEqual(0, len(ListFiles('/webdav/by-dates/', False)))
        self.assertEqual(2, len(WEBDAV.ls('/webdav/by-dates/')))
        self.assertEqual(0, len(ListFiles('/webdav/by-dates/%s' % year, False)))
        self.assertEqual(2, len(WEBDAV.ls('/webdav/by-dates/%s' % year)))
        self.assertEqual(0, len(ListFiles('/webdav/by-dates/%s/%s-%s' % (year, year, month), False)))
        self.assertEqual(2, len(WEBDAV.ls('/webdav/by-dates/%s/%s-%s' % (year, year, month))))

        folder = '/webdav/by-dates/%s/%s-%s/%s/%s' % (year, year, month, study, series)
        self.assertEqual(1, len(ListFiles(folder, False)))
        self.assertEqual(2, len(WEBDAV.ls(folder)))
        self.assertEqual('%s/%s.dcm' % (folder, i), unquote(ListFiles(folder, False) [0]))

        files = ListFiles('/webdav/by-dates/', True)
        self.assertEqual(1, len(files))
        self.assertEqual('%s/%s.dcm' % (folder, i), unquote(files[0]))
        
        a = DownloadFile('%s/%s.dcm' % (folder, i))
        with open(GetDatabasePath('DummyCT.dcm'), 'rb') as f:
            self.assertEqual(a, f.read())

        self.assertEqual(1, len(DoGet(ORTHANC, '/instances')))
        WEBDAV.delete('%s/%s.dcm' % (folder, i))
        self.assertEqual(0, len(DoGet(ORTHANC, '/instances')))
        self.assertEqual(0, len(ListFiles('/webdav/by-dates/', True)))


    def test_delete_folder(self):
        # These deletes should have no effect
        UploadInstance(ORTHANC, 'DummyCT.dcm')
        self.assertEqual(1, len(DoGet(ORTHANC, '/instances')))
        WEBDAV.delete('/webdav/by-uids/1.2.840.113619.2.176.2025.1499492.7391.1171285944.390/study.json')
        WEBDAV.delete('/webdav/by-uids/1.2.840.113619.2.176.2025.1499492.7391.1171285944.390/1.2.840.113619.2.176.2025.1499492.7391.1171285944.394/series.json')
        WEBDAV.delete('/webdav/by-dates/2007/2007-02')
        WEBDAV.delete('/webdav/by-dates/2006')
        self.assertEqual(1, len(DoGet(ORTHANC, '/instances')))

        for path in [
                '/webdav/by-uids/1.2.840.113619.2.176.2025.1499492.7391.1171285944.390/1.2.840.113619.2.176.2025.1499492.7391.1171285944.394/1.2.840.113619.2.176.2025.1499492.7040.1171286242.109.dcm',
                '/webdav/by-patients/ozp00SjY2xG - KNIX/20070101 - Knee (R)/MR - AX.  FSE PD/66a662ce-7430e543-bad44d47-0dc5a943-ec7a538d.dcm',
                '/webdav/by-studies/ozp00SjY2xG - KNIX - Knee (R)/MR - AX.  FSE PD/66a662ce-7430e543-bad44d47-0dc5a943-ec7a538d.dcm',
                '/webdav/by-dates/2007/2007-01/ozp00SjY2xG - KNIX - Knee (R)/MR - AX.  FSE PD/66a662ce-7430e543-bad44d47-0dc5a943-ec7a538d.dcm',
                ]:
            tokens = path.split('/')
            for i in range(4, len(tokens) + 1):
                p = '/'.join(tokens[0:i])
                UploadInstance(ORTHANC, 'DummyCT.dcm')
                self.assertEqual(1, len(DoGet(ORTHANC, '/instances')))        
                WEBDAV.delete(p)
                self.assertEqual(0, len(DoGet(ORTHANC, '/instances')))


    def test_upload_zip(self):
        f = BytesIO()
        with zipfile.ZipFile(f, 'w') as z:
            z.writestr('hello/world/invalid.txt', 'Hello world')
            with open(GetDatabasePath('DummyCT.dcm'), 'rb') as g:
                c = g.read()
                z.writestr('hello/world/dicom1.dcm', c)
                z.writestr('hello/world/dicom2.dcm', c)

        f.seek(0)
        archive = f.read()
        
        self.assertEqual(0, len(DoGet(ORTHANC, '/studies')))

        with tempfile.NamedTemporaryFile(delete = True) as f:
            f.close()
            with open(f.name, 'wb') as g:
                g.write(archive)
            WEBDAV.upload(f.name, '/webdav/uploads/DummyCT.zip')
            os.unlink(f.name)

        while len(ListFiles('/webdav/uploads/', True)) > 1:
            time.sleep(0.1)
        time.sleep(0.1)  # Give some more delay to be sure that the store has succeeded (necessary for Wine)
        
        instances = DoGet(ORTHANC, '/instances')
        self.assertEqual(1, len(instances))
        self.assertEqual('66a662ce-7430e543-bad44d47-0dc5a943-ec7a538d', instances[0])
                
        
try:
    print('\nStarting the tests...')
    unittest.main(argv = [ sys.argv[0] ] + args.options)

finally:
    print('\nDone')
