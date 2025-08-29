#!/usr/bin/env python
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


import base64
import bz2
import copy
import io
import numpy
import pprint
import shutil
import tempfile
import unittest
import time
import os

from PIL import ImageChops
from Toolbox import *
from xml.dom import minidom
from datetime import datetime

_LOCAL = None
_REMOTE = None
_DOCKER = False


def SetOrthancParameters(local, remote, withinDocker):
    global _LOCAL, _REMOTE, _DOCKER
    _LOCAL = local
    _REMOTE = remote
    _DOCKER = withinDocker

    
def ExtractDicomTags(rawDicom, tags):
    with tempfile.NamedTemporaryFile(delete = True) as f:
        f.write(rawDicom)
        f.flush()
        data = subprocess.check_output([ FindExecutable('dcm2xml'), f.name ])

    result = []
    for tag in tags:
        match = re.search('<element[^>]+name="%s">([^>]*)</element>' % tag, data)
        if match == None:
            result.append('')
        else:
            result.append(match.group(1))

    return result


def CompareLists(a, b):
    if len(a) != len(b):
        return False

    for i in range(len(a)):
        d = a[i] - b[i]
        if abs(d) >= 0.51:  # Add some tolerance for rounding errors
            return False

    return True


def CompareTags(a, b, tagsToIgnore):
    for i in tagsToIgnore:
        if i in a:
            del a[i]
        if i in b:
            del b[i]

    if a.keys() == b.keys():
        return True
    else:
        print('Mismatch in tags: %s' % str(set(a.keys()) ^ set(b.keys())))
        return False


def CallFindScu(args):
    p = subprocess.Popen([ FindExecutable('findscu'), 
                           '-P', '-aec', _REMOTE['DicomAet'], '-aet', _LOCAL['DicomAet'],
                           _REMOTE['Server'], str(_REMOTE['DicomPort']) ] + args,
                         stderr=subprocess.PIPE)
    return p.communicate()[1]


def GetMoveScuCommand():
    return [ 
        FindExecutable('movescu'), 
        '--move', _LOCAL['DicomAet'],      # Target AET (i.e. storescp)
        '--call', _REMOTE['DicomAet'],     # Called AET (i.e. Orthanc)
        '--aetitle', _LOCAL['DicomAet'],   # Calling AET (i.e. storescp)
        _REMOTE['Server'], 
        str(_REMOTE['DicomPort'])  
        ]


def IsDicomUntilPixelDataStored(orthanc):
    # This function detects whether the "StorageCompression" option is
    # "true", OR the storage area does not support read-range

    if IsOrthancVersionAbove(orthanc, 1, 9, 1):
        i = UploadInstance(orthanc, 'ColorTestMalaterre.dcm') ['ID']
        a = DoGet(orthanc, '/instances/%s/metadata/PixelDataOffset' % i)
        if a != 0x03a0:
            raise Exception('Internal error')

        a = DoGet(orthanc, '/instances/%s/attachments' % i)
        if len(a) != 1 and len(a) != 2 or not 'dicom' in a:
            raise Exception('Internal error')

        DoDelete(orthanc, '/instances/%s' % i)

        if len(a) == 1:
            return False
        elif 'dicom-until-pixel-data' in a:
            return True
        else:
            raise Exception('Internal error')
        
    else:
        return False


def CallMoveScu(args):
    try:
        subprocess.check_call(GetMoveScuCommand() + args,
                              stderr = subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        # The error code "69" corresponds to "EXITCODE_CMOVE_ERROR",
        # that has been introduced in DCMTK 3.6.2. This error code is
        # expected by some tests that try and C-MOVE non-existing
        # DICOM instances.
        # https://groups.google.com/d/msg/orthanc-users/DCRc5NeSCbM/DG-pSWj-BwAJ
        if e.returncode != 69:
            raise e


def GenerateTestSequence():
    return [
        {
            'StudyDescription': 'Hello^',
            'ReferencedStudySequence' : [
                {
                    'StudyDescription': 'Toto',
                    },
                {
                    'StudyDescription': 'Tata',
                    },
                ]
            },
        {
            'StudyDescription': 'Sébastien^',
            'StudyDate' : '19700202',
            }
        ]


class Orthanc(unittest.TestCase):
    def setUp(self):
        if (sys.version_info >= (3, 0)):
            # Remove annoying warnings about unclosed socket in Python 3
            import warnings
            warnings.simplefilter("ignore", ResourceWarning)

        print('running : %s' % self.id())

        DropOrthanc(_LOCAL)
        DropOrthanc(_REMOTE)
        UninstallLuaCallbacks(_REMOTE)

        # Reset stuff possibly set by some integration tests
        DoPut(_REMOTE, '/tools/default-encoding', 'Latin1')
        if IsOrthancVersionAbove(_REMOTE, 1, 9, 0):
            DoPut(_REMOTE, '/tools/accepted-transfer-syntaxes', [ '1.2.840.10008.1.*' ])
            DoPut(_REMOTE, '/tools/unknown-sop-class-accepted', '0')

        for i in [ 'toto', 'tata' ]:
            if i in DoGet(_REMOTE, '/modalities'):
                DoDelete(_REMOTE, '/modalities/%s' % i)
            if i in DoGet(_REMOTE, '/peers'):
                DoDelete(_REMOTE, '/peers/%s' % i)
        
        #print("%s: In test %s" % (datetime.now(), self._testMethodName))
        
    def AssertSameImages(self, truth, url):
        im = GetImage(_REMOTE, url)
        self.assertTrue(CompareLists(truth, im.getdata()))


    def test_system(self):
        self.assertTrue('Version' in DoGet(_REMOTE, '/system'))
        self.assertEqual('0', DoGet(_REMOTE, '/statistics')['TotalDiskSize'])
        self.assertEqual('0', DoGet(_REMOTE, '/statistics')['TotalUncompressedSize'])

        systemInfo = DoGet(_REMOTE, '/system')

        if IsOrthancVersionAbove(_REMOTE, 1, 11, 0):
            self.assertIn("MainDicomTags", systemInfo)
            self.assertIn("Patient", systemInfo["MainDicomTags"])
            self.assertIn("Study", systemInfo["MainDicomTags"])
            self.assertIn("Series", systemInfo["MainDicomTags"])
            self.assertIn("Instance", systemInfo["MainDicomTags"])

        if IsOrthancVersionAbove(_REMOTE, 1, 12, 0):
            self.assertIn("UserMetadata", systemInfo)
            self.assertEqual(1098, systemInfo['UserMetadata']['my-metadata'] )

        if systemInfo["Version"] == "mainline":
            print("Skipping version checks since you're currently in mainline")
            return

        if not IsOrthancVersionAbove(_LOCAL, 0, 8, 7):
            self.assertTrue(IsOrthancVersionAbove(_LOCAL, 0, 8, 6))
            self.assertFalse(IsOrthancVersionAbove(_LOCAL, 0, 8, 7))
            self.assertTrue(IsOrthancVersionAbove(_LOCAL, 0, 7, 6))
            self.assertFalse(IsOrthancVersionAbove(_LOCAL, 0, 9, 6))
            self.assertFalse(IsOrthancVersionAbove(_LOCAL, 1, 8, 6))



    def test_upload(self):
        self.assertEqual('0', DoGet(_REMOTE, '/statistics')['TotalDiskSize'])
        self.assertEqual('0', DoGet(_REMOTE, '/statistics')['TotalUncompressedSize'])

        sizeDummyCT = 2472
        sizeOverwrite = 2476
        instance = '66a662ce-7430e543-bad44d47-0dc5a943-ec7a538d'

        # This file has *no* pixel data => "dicom-until-pixel-data" is not created
        u = UploadInstance(_REMOTE, 'DummyCT.dcm')
        isCompressed = (DoGet(_REMOTE, '/instances/%s/attachments/dicom/is-compressed' % u['ID']) != 0)
        self.assertEqual(instance, u['ID'])
        self.assertEqual('Success', u['Status'])

        if True:
            # New test for Orthanc 1.4.3
            self.assertEqual('f2635388-f01d497a-15f7c06b-ad7dba06-c4c599fe', u['ParentSeries'])
            self.assertEqual('b9c08539-26f93bde-c81ab0d7-bffaf2cb-a4d0bdd0', u['ParentStudy'])
            self.assertEqual('6816cb19-844d5aee-85245eba-28e841e6-2414fae2', u['ParentPatient'])

        if IsOrthancVersionAbove(_REMOTE, 1, 9, 1):
            self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/instances/%s/attachments/dicom-as-json' % instance))
            self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/instances/%s/attachments/dicom-until-pixel-data' % instance))
            j = 0
        else:
            self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/instances/%s/attachments/dicom-until-pixel-data' % instance))
            j = int(DoGet(_REMOTE, '/instances/%s/attachments/dicom-as-json/size' % instance))

        if IsOrthancVersionAbove(_REMOTE, 1, 10, 0):
            attachmentInfo = DoGet(_REMOTE, '/instances/%s/attachments/dicom/info' % instance)

            if isCompressed:
                self.assertGreater(sizeDummyCT, attachmentInfo['CompressedSize'])
            else:
                self.assertEqual(sizeDummyCT, attachmentInfo['CompressedSize'])

            self.assertEqual(sizeDummyCT, attachmentInfo['UncompressedSize'])
            self.assertIn('Uuid', attachmentInfo)
            self.assertEqual(1, attachmentInfo['ContentType'])


            if IsOrthancVersionAbove(_REMOTE, 1, 12, 7):
                resp, content = DoGetRaw(_REMOTE, '/instances/%s/attachments/dicom/data?filename=toto.dcm' % instance)
                self.assertEqual('filename="toto.dcm"', resp['content-disposition'])


        s = sizeDummyCT + j

        if isCompressed:
            self.assertGreater(s, int(DoGet(_REMOTE, '/statistics')['TotalDiskSize']))
        else:
            self.assertEqual(s, int(DoGet(_REMOTE, '/statistics')['TotalDiskSize']))
            
        self.assertEqual(s, int(DoGet(_REMOTE, '/statistics')['TotalUncompressedSize']))

        u = UploadInstance(_REMOTE, 'DummyCT.dcm')
        self.assertEqual(1, len(DoGet(_REMOTE, '/patients')))
        self.assertEqual(1, len(DoGet(_REMOTE, '/studies')))
        self.assertEqual(1, len(DoGet(_REMOTE, '/series')))
        self.assertEqual(1, len(DoGet(_REMOTE, '/instances')))

        if isCompressed:
            self.assertGreater(s, int(DoGet(_REMOTE, '/statistics')['TotalDiskSize']))
        else:
            self.assertEqual(s, int(DoGet(_REMOTE, '/statistics')['TotalDiskSize']))
            
        self.assertEqual(s, int(DoGet(_REMOTE, '/statistics')['TotalUncompressedSize']))

        i = DoGet(_REMOTE, '/instances/%s/simplified-tags' % instance)
        self.assertEqual('20070101', i['StudyDate'])
        self.assertEqual('KNIX', i['PatientName'])

        if IsOrthancVersionAbove(_REMOTE, 1, 4, 2):
            # Overwriting
            self.assertEqual('Success', u['Status'])
        else:
            self.assertEqual('AlreadyStored', u['Status'])

        u = UploadInstance(_REMOTE, 'DummyCT-overwrite.dcm')
        self.assertEqual(1, len(DoGet(_REMOTE, '/patients')))
        self.assertEqual(1, len(DoGet(_REMOTE, '/studies')))
        self.assertEqual(1, len(DoGet(_REMOTE, '/series')))
        self.assertEqual(1, len(DoGet(_REMOTE, '/instances')))

        if IsOrthancVersionAbove(_REMOTE, 1, 4, 2):
            # Overwriting
            self.assertEqual('Success', u['Status'])
            if IsOrthancVersionAbove(_REMOTE, 1, 9, 1):
                j2 = 0
            else:
                j2 = int(DoGet(_REMOTE, '/instances/%s/attachments/dicom-as-json/size' % instance))
                self.assertNotEqual(j, j2)
            s2 = sizeOverwrite + j2
            self.assertNotEqual(s, s2)
            if isCompressed:
                self.assertGreater(s2, int(DoGet(_REMOTE, '/statistics')['TotalDiskSize']))
            else:
                self.assertEqual(s2, int(DoGet(_REMOTE, '/statistics')['TotalDiskSize']))
                
            self.assertEqual(s2, int(DoGet(_REMOTE, '/statistics')['TotalUncompressedSize']))
            i = DoGet(_REMOTE, '/instances/%s/simplified-tags' % instance)
            self.assertEqual('ANOTHER', i['PatientName'])
        else:
            self.assertEqual('AlreadyStored', u['Status'])
            self.assertEqual(s, int(DoGet(_REMOTE, '/statistics')['TotalDiskSize']))
            self.assertEqual(s, int(DoGet(_REMOTE, '/statistics')['TotalUncompressedSize']))

    def test_upload_2(self):
        i = UploadInstance(_REMOTE, 'DummyCT.dcm')['ID']
        instance = DoGet(_REMOTE, '/instances/%s' % i)
        self.assertEqual(i, instance['ID'])
        self.assertEqual('1.2.840.113619.2.176.2025.1499492.7040.1171286242.109',
                         instance['MainDicomTags']['SOPInstanceUID'])

        series = DoGet(_REMOTE, '/series/%s' % instance['ParentSeries'])
        self.assertEqual('1.2.840.113619.2.176.2025.1499492.7391.1171285944.394', 
                         series['MainDicomTags']['SeriesInstanceUID'])

        study = DoGet(_REMOTE, '/studies/%s' % series['ParentStudy'])
        self.assertEqual('1.2.840.113619.2.176.2025.1499492.7391.1171285944.390',
                         study['MainDicomTags']['StudyInstanceUID'])

        patient = DoGet(_REMOTE, '/patients/%s' % study['ParentPatient'])
        self.assertEqual('ozp00SjY2xG',
                         patient['MainDicomTags']['PatientID'])

        dicom = DoGet(_REMOTE, '/instances/%s/file' % instance['ID'])
        self.assertEqual(2472, len(dicom))
        self.assertEqual('3e29b869978b6db4886355a2b1132124', ComputeMD5(dicom))
        self.assertEqual(1, len(DoGet(_REMOTE, '/instances/%s/frames' % i)))
        self.assertEqual('TWINOW', DoGet(_REMOTE, '/instances/%s/simplified-tags' % i)['StationName'])
        self.assertEqual('TWINOW', DoGet(_REMOTE, '/instances/%s/tags' % i)['0008,1010']['Value'])
        self.assertEqual('TWINOW', DoGet(_REMOTE, '/instances/%s/tags?simplify' % i)['StationName'])
        self.assertEqual('TWINOW', DoGet(_REMOTE, '/instances/%s/tags?short' % i)['0008,1010'])


    def test_images(self):
        i = UploadInstance(_REMOTE, 'Phenix/IM-0001-0001.dcm')['ID']
        self.assertEqual(1, len(DoGet(_REMOTE, '/instances/%s/frames' % i)))

        im = GetImage(_REMOTE, '/instances/%s/preview' % i)
        self.assertEqual("L", im.mode)
        self.assertEqual(512, im.size[0])
        self.assertEqual(358, im.size[1])

        im = GetImage(_REMOTE, '/instances/%s/image-uint8' % i)
        self.assertEqual("L", im.mode)
        self.assertEqual(512, im.size[0])
        self.assertEqual(358, im.size[1])

        im = GetImage(_REMOTE, '/instances/%s/image-uint16' % i)
        self.assertEqual(512, im.size[0])
        self.assertEqual(358, im.size[1])

        im = GetImage(_REMOTE, '/instances/%s/frames/0/preview' % i)
        self.assertEqual("L", im.mode)
        self.assertEqual(512, im.size[0])
        self.assertEqual(358, im.size[1])

        im = GetImage(_REMOTE, '/instances/%s/frames/0/image-uint8' % i)
        self.assertEqual("L", im.mode)
        self.assertEqual(512, im.size[0])
        self.assertEqual(358, im.size[1])

        im = GetImage(_REMOTE, '/instances/%s/frames/0/image-uint16' % i)
        self.assertEqual(512, im.size[0])
        self.assertEqual(358, im.size[1])

        # This is Little Endian Explicit
        self.assertEqual('1.2.840.10008.1.2.1', DoGet(_REMOTE, '/instances/%s/header?simplify' % i)['TransferSyntaxUID'])

    def test_images_implicit_vr(self):
        if IsOrthancVersionAbove(_REMOTE, 1, 10, 2):
            i = UploadInstance(_REMOTE, 'Implicit-vr-us-palette.dcm')['ID']

            im = GetImage(_REMOTE, '/instances/%s/preview' % i)
            self.assertEqual("RGB", im.mode)
            self.assertEqual(800, im.size[0])
            self.assertEqual(600, im.size[1])

        
    def test_hierarchy(self):
        UploadFolder(_REMOTE, 'Brainix/Epi')
        UploadFolder(_REMOTE, 'Brainix/Flair')
        UploadFolder(_REMOTE, 'Knee/T1')
        UploadFolder(_REMOTE, 'Knee/T2')

        p = DoGet(_REMOTE, '/patients')
        s = DoGet(_REMOTE, '/studies')
        t = DoGet(_REMOTE, '/series')
        self.assertEqual(2, len(p))
        self.assertEqual(2, len(s))
        self.assertEqual(4, len(t))
        self.assertEqual(94, len(DoGet(_REMOTE, '/instances')))

        brainixPatient = '16738bc3-e47ed42a-43ce044c-a3414a45-cb069bd0'
        brainixStudy = '27f7126f-4f66fb14-03f4081b-f9341db2-53925988'
        brainixEpi = '2ac1316d-3e432022-62eabff2-c59f5475-9b1ac3f8'
        brainixFlair = '1e2c125c-411b8e86-3f4fe68e-a7584dd3-c6da78f0'

        kneePatient = 'ca29faea-b6a0e17f-067743a1-8b778011-a48b2a17'
        kneeStudy = '0a9b3153-2512774b-2d9580de-1fc3dcf6-3bd83918'
        kneeT1 = '6de73705-c4e65c1b-9d9ea1b5-cabcd8e7-f15e4285'
        kneeT2 = 'bbf7a453-0d34251a-03663b55-46bb31b9-ffd74c59'

        self.assertTrue(brainixPatient in p)
        self.assertTrue(kneePatient in p)
        self.assertTrue(brainixStudy in s)
        self.assertTrue(kneeStudy in s)
        self.assertTrue(brainixEpi in t)
        self.assertTrue(brainixFlair in t)
        self.assertTrue(kneeT1 in t)
        self.assertTrue(kneeT2 in t)

        self.assertEqual(44, len(DoGet(_REMOTE, '/patients/%s/instances' % brainixPatient)))
        self.assertEqual(2, len(DoGet(_REMOTE, '/patients/%s/series' % brainixPatient)))
        self.assertEqual(1, len(DoGet(_REMOTE, '/patients/%s/studies' % brainixPatient)))

        self.assertEqual(50, len(DoGet(_REMOTE, '/patients/%s/instances' % kneePatient)))
        self.assertEqual(2, len(DoGet(_REMOTE, '/patients/%s/series' % kneePatient)))
        self.assertEqual(1, len(DoGet(_REMOTE, '/patients/%s/studies' % kneePatient)))

        self.assertEqual(2, len(DoGet(_REMOTE, '/studies/%s/series' % brainixStudy)))
        self.assertEqual(44, len(DoGet(_REMOTE, '/studies/%s/instances' % brainixStudy)))

        self.assertEqual(2, len(DoGet(_REMOTE, '/studies/%s/series' % kneeStudy)))
        self.assertEqual(50, len(DoGet(_REMOTE, '/studies/%s/instances' % kneeStudy)))

        self.assertEqual(22, len(DoGet(_REMOTE, '/series/%s/instances' % brainixEpi)))
        self.assertEqual(22, len(DoGet(_REMOTE, '/series/%s/instances' % brainixFlair)))
        self.assertEqual(24, len(DoGet(_REMOTE, '/series/%s/instances' % kneeT1)))
        self.assertEqual(26, len(DoGet(_REMOTE, '/series/%s/instances' % kneeT2)))

        for patient in p:
            for study in DoGet(_REMOTE, '/patients/%s/studies' % patient):
                self.assertEqual(patient, study['ParentPatient'])
                for series in DoGet(_REMOTE, '/studies/%s/series' % study['ID']):
                    self.assertEqual(study['ID'], series['ParentStudy'])
                    self.assertEqual('Unknown', series['Status'])
                    for instance in DoGet(_REMOTE, '/series/%s/instances' % series['ID']):
                        self.assertEqual(series['ID'], instance['ParentSeries'])

                        if not IsOrthancVersionAbove(_REMOTE, 1, 9, 1):
                            # The "dicom-as-json" attachment was removed in Orthanc 1.9.1
                            self.assertEqual(json.dumps(DoGet(_REMOTE, '/instances/%s/attachments/dicom-as-json/data' % instance['ID'])),
                                             json.dumps(DoGet(_REMOTE, '/instances/%s/tags' % instance['ID'])))


        r = DoDelete(_REMOTE, "/studies/%s" % brainixStudy)['RemainingAncestor']
        self.assertEqual(1, len(DoGet(_REMOTE, '/patients')))
        self.assertEqual(1, len(DoGet(_REMOTE, '/studies')))
        self.assertEqual(2, len(DoGet(_REMOTE, '/series')))
        self.assertEqual(50, len(DoGet(_REMOTE, '/instances')))
        self.assertEqual(None, r)

        r = DoDelete(_REMOTE, "/series/%s" % kneeT2)['RemainingAncestor']
        self.assertEqual(1, len(DoGet(_REMOTE, '/patients')))
        self.assertEqual(1, len(DoGet(_REMOTE, '/studies')))
        self.assertEqual(1, len(DoGet(_REMOTE, '/series')))
        self.assertEqual(24, len(DoGet(_REMOTE, '/instances')))
        self.assertEqual('Study', r['Type'])
        self.assertEqual(kneeStudy, r['ID'])

        r = DoDelete(_REMOTE, "/instances/%s" % DoGet(_REMOTE, '/instances')[0])['RemainingAncestor']
        self.assertEqual(1, len(DoGet(_REMOTE, '/patients')))
        self.assertEqual(1, len(DoGet(_REMOTE, '/studies')))
        self.assertEqual(1, len(DoGet(_REMOTE, '/series')))
        self.assertEqual(23, len(DoGet(_REMOTE, '/instances')))
        self.assertEqual('Series', r['Type'])
        self.assertEqual(kneeT1, r['ID'])

        r = DoDelete(_REMOTE, "/patients/%s" % kneePatient)['RemainingAncestor']
        self.assertEqual(0, len(DoGet(_REMOTE, '/patients')))
        self.assertEqual(0, len(DoGet(_REMOTE, '/studies')))
        self.assertEqual(0, len(DoGet(_REMOTE, '/series')))
        self.assertEqual(0, len(DoGet(_REMOTE, '/instances')))
        self.assertEqual(None, r)

        DropOrthanc(_REMOTE)
        self.assertEqual('0', DoGet(_REMOTE, '/statistics')['TotalDiskSize'])
        self.assertEqual('0', DoGet(_REMOTE, '/statistics')['TotalUncompressedSize'])

    def test_delete_cascade(self):
        # make sure deleting the last instance of a study deletes the series, study and patient

        self.assertEqual(0, len(DoGet(_REMOTE, '/instances')))  # make sure orthanc is empty when starting the test
        a = UploadInstance(_REMOTE, 'DummyCT.dcm')['ID']
        self.assertEqual(1, len(DoGet(_REMOTE, '/instances')))
        self.assertEqual(1, len(DoGet(_REMOTE, '/series')))
        self.assertEqual(1, len(DoGet(_REMOTE, '/studies')))
        self.assertEqual(1, len(DoGet(_REMOTE, '/patients')))

        DoDelete(_REMOTE, '/instances/%s' % a)        

        self.assertEqual(0, len(DoGet(_REMOTE, '/instances')))
        self.assertEqual(0, len(DoGet(_REMOTE, '/series')))
        self.assertEqual(0, len(DoGet(_REMOTE, '/studies')))
        self.assertEqual(0, len(DoGet(_REMOTE, '/patients')))


    def test_delete_cascade_with_multiple_instances(self):
        # make sure deleting the last instance of a study deletes the series, study and patient

        self.assertEqual(0, len(DoGet(_REMOTE, '/instances')))  # make sure orthanc is empty when starting the test
        a = UploadInstance(_REMOTE, 'Knix/Loc/IM-0001-0001.dcm')
        b = UploadInstance(_REMOTE, 'Knix/Loc/IM-0001-0002.dcm')

        self.assertEqual(2, len(DoGet(_REMOTE, '/instances')))
        self.assertEqual(1, len(DoGet(_REMOTE, '/series')))
        self.assertEqual(1, len(DoGet(_REMOTE, '/studies')))
        self.assertEqual(1, len(DoGet(_REMOTE, '/patients')))

        DoDelete(_REMOTE, '/instances/%s' % b['ID'])        

        self.assertEqual(1, len(DoGet(_REMOTE, '/instances')))
        self.assertEqual(1, len(DoGet(_REMOTE, '/series')))
        self.assertEqual(1, len(DoGet(_REMOTE, '/studies')))
        self.assertEqual(1, len(DoGet(_REMOTE, '/patients')))

        DoDelete(_REMOTE, '/instances/%s' % a['ID'])        

        self.assertEqual(0, len(DoGet(_REMOTE, '/instances')))
        self.assertEqual(0, len(DoGet(_REMOTE, '/series')))
        self.assertEqual(0, len(DoGet(_REMOTE, '/studies')))
        self.assertEqual(0, len(DoGet(_REMOTE, '/patients')))

    def test_multiframe(self):
        i = UploadInstance(_REMOTE, 'Multiframe.dcm')['ID']
        self.assertEqual(76, len(DoGet(_REMOTE, '/instances/%s/frames' % i)))

        im = GetImage(_REMOTE, '/instances/%s/frames/0/preview' % i)
        self.assertEqual("L", im.mode)
        self.assertEqual(512, im.size[0])
        self.assertEqual(512, im.size[1])
  
        DoGet(_REMOTE, '/instances/%s/frames/0/image-uint8' % i)
        DoGet(_REMOTE, '/instances/%s/frames/0/image-uint16' % i)
        DoGet(_REMOTE, '/instances/%s/frames/75/preview' % i)
        self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/instances/%s/frames/aaa/preview' % i))
        self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/instances/%s/frames/76/preview' % i))


    def test_changes(self):
        # Check emptiness
        c = DoGet(_REMOTE, '/changes')
        self.assertEqual(0, len(c['Changes']))
        #self.assertEqual(0, c['Last'])   # Not true anymore for Orthanc >= 1.5.2
        self.assertTrue(c['Done'])
        c = DoGet(_REMOTE, '/changes?last')
        self.assertEqual(0, len(c['Changes']))
        #self.assertEqual(0, c['Last'])   # Not true anymore for Orthanc >= 1.5.2
        self.assertTrue(c['Done'])

        # Add 1 instance
        i = UploadInstance(_REMOTE, 'Brainix/Flair/IM-0001-0001.dcm')['ID']
        c = DoGet(_REMOTE, '/changes')
        begin = c['Last']
        self.assertEqual(4, len(c['Changes']))
        self.assertTrue(c['Done'])
        self.assertEqual(c['Changes'][-1]['Seq'], c['Last'])

        # Check the order in which the creation events are reported
        self.assertEqual(c['Changes'][0]['ChangeType'], 'NewInstance')
        self.assertEqual(c['Changes'][1]['ChangeType'], 'NewSeries')
        self.assertEqual(c['Changes'][2]['ChangeType'], 'NewStudy')
        self.assertEqual(c['Changes'][3]['ChangeType'], 'NewPatient')

        c = DoGet(_REMOTE, '/changes?last')
        self.assertEqual(1, len(c['Changes']))
        self.assertEqual(begin, c['Last'])
        self.assertTrue(c['Done'])
        c = DoGet(_REMOTE, '/changes?limit=1&since=' + str(begin - 1))
        self.assertEqual(1, len(c['Changes']))
        self.assertEqual(begin, c['Last'])
        self.assertTrue(c['Done'])
        c = DoGet(_REMOTE, '/changes?limit=1&since=' + str(begin - 2))
        self.assertEqual(1, len(c['Changes']))
        self.assertEqual(begin - 1, c['Last'])
        self.assertFalse(c['Done'])
        c = DoGet(_REMOTE, '/changes?limit=1&since=' + str(begin - 3))
        self.assertEqual(1, len(c['Changes']))
        self.assertEqual(begin - 2, c['Last'])
        self.assertFalse(c['Done'])

        UploadFolder(_REMOTE, 'Knee/T1')
        UploadFolder(_REMOTE, 'Knee/T2')
        since = begin
        countPatients = 0
        countStudies = 0
        countSeries = 0
        countInstances = 0
        completed = 0
        while True:
            c = DoGet(_REMOTE, '/changes', { 'since' : since, 'limit' : 1000 })
            since = c['Last']
            for i in c['Changes']:
                # We have set StableAge to 1 -> we might have StabeStudy but this is not sure -> detect only the 'New' events

                if i['ResourceType'] == 'Instance' and i['ChangeType'] == 'NewInstance':
                    countInstances += 1
                if i['ResourceType'] == 'Patient' and i['ChangeType'] == 'NewPatient':
                    countPatients += 1
                if i['ResourceType'] == 'Study' and i['ChangeType'] == 'NewStudy':
                    countStudies += 1
                if i['ResourceType'] == 'Series' and i['ChangeType'] == 'NewSeries':
                    countSeries += 1
                if i['ChangeType'] == 'CompletedSeries':
                    completed += 1
                self.assertTrue('ID' in i)
                self.assertTrue('Path' in i)
                self.assertTrue('Seq' in i)
            if c['Done']:
                break
        # we count only the events since before the upload of 2 Knee series !
        self.assertEqual(50, countInstances)
        self.assertEqual(1, countPatients)
        self.assertEqual(1, countStudies)
        self.assertEqual(2, countSeries)
        self.assertEqual(0, completed)


    def test_changes_extended(self):
        if IsOrthancVersionAbove(_REMOTE, 1, 12, 5) and HasExtendedChanges(_REMOTE):
            # Check emptiness
            c = DoGet(_REMOTE, '/changes')
            self.assertEqual(0, len(c['Changes']))
            #self.assertEqual(0, c['Last'])   # Not true anymore for Orthanc >= 1.5.2
            self.assertTrue(c['Done'])
            c = DoGet(_REMOTE, '/changes?last')
            self.assertEqual(0, len(c['Changes']))
            #self.assertEqual(0, c['Last'])   # Not true anymore for Orthanc >= 1.5.2
            self.assertTrue(c['Done'])

            # Add 1 instance
            i = UploadInstance(_REMOTE, 'Brainix/Flair/IM-0001-0001.dcm')['ID']
            c = DoGet(_REMOTE, '/changes')
            begin = c['Last']
            self.assertEqual(4, len(c['Changes']))
            self.assertTrue(c['Done'])
            self.assertEqual(c['Changes'][-1]['Seq'], c['Last'])

            # Check the order in which the creation events are reported
            self.assertEqual(c['Changes'][0]['ChangeType'], 'NewInstance')
            self.assertEqual(c['Changes'][1]['ChangeType'], 'NewSeries')
            self.assertEqual(c['Changes'][2]['ChangeType'], 'NewStudy')
            self.assertEqual(c['Changes'][3]['ChangeType'], 'NewPatient')

            c = DoGet(_REMOTE, '/changes?type=NewInstance')
            self.assertEqual(1, len(c['Changes']))
            self.assertEqual(begin-3, c['Last'])

            c = DoGet(_REMOTE, '/changes?type=NewPatient')
            self.assertEqual(1, len(c['Changes']))
            self.assertEqual(begin, c['Last'])

            c = DoGet(_REMOTE, '/changes?type=NewPatient;NewInstance')
            self.assertEqual(2, len(c['Changes']))
            self.assertEqual(begin, c['Last'])

            UploadFolder(_REMOTE, 'Knee/T1')
            UploadFolder(_REMOTE, 'Knee/T2')

            # Request the 1000 first NewInstance changes  -> all 50 shall be reported
            c = DoGet(_REMOTE, '/changes', { 'type': 'NewInstance', 'since' : begin, 'limit' : 1000 })
            self.assertEqual(50, len(c['Changes']))
            self.assertLess(begin, c['Changes'][0]['Seq'])
            self.assertTrue(c['Done'])   #w e have got them all so it's DONE
            lastFrom1000NewInstances = c['Last']
            firstFrom1000NewInstances = c['First']
            self.assertLess(firstFrom1000NewInstances, lastFrom1000NewInstances)

            # Only the 10 first NewInstance changes  -> only 10 shall be reported
            c = DoGet(_REMOTE, '/changes', { 'type': 'NewInstance', 'since' : begin, 'limit' : 10 })
            self.assertEqual(10, len(c['Changes']))
            self.assertFalse(c['Done'])
            lastFrom10firstNewInstances = c['Last']
            firstFrom10firstNewInstances = c['First']
            self.assertLess(firstFrom10firstNewInstances, lastFrom10firstNewInstances)
            self.assertLess(lastFrom10firstNewInstances, lastFrom1000NewInstances)
            self.assertEqual(firstFrom10firstNewInstances, firstFrom1000NewInstances)

            # between begin and begin+10 with a max of 10 and a filter -> less than 10 NewInstance since there are other changes in this range
            c = DoGet(_REMOTE, '/changes', { 'type': 'NewInstance', 'since' : begin, 'to': begin+10, 'limit' : 10 })
            self.assertLess(len(c['Changes']), 10)
            self.assertTrue(c['Done'])  # we have received ALL NewInstance that are between since and to so we consider it's done
            lastFrom10SubsetNewInstances = c['Last']
            firstFrom10SubsetNewInstances = c['First']
            self.assertLess(firstFrom10SubsetNewInstances, lastFrom10SubsetNewInstances)
            self.assertLess(lastFrom10SubsetNewInstances, lastFrom10firstNewInstances)
            self.assertEqual(firstFrom10SubsetNewInstances, firstFrom1000NewInstances)

            # test with only 'to' -> all 50 NewInstance shall be reported
            c = DoGet(_REMOTE, '/changes', { 'type': 'NewInstance', 'to': lastFrom1000NewInstances, 'limit' : 50 })
            self.assertEqual(lastFrom1000NewInstances, c['Changes'][-1]['Seq'])
            self.assertEqual(50, len(c['Changes']))
            self.assertFalse(c['Done'])  # Done can not be used when working in reverse direction
            lastFrom50Reverse = c['Last']
            firstFrom50Reverse = c['First']
            self.assertLess(firstFrom50Reverse, lastFrom50Reverse)
            self.assertEqual(lastFrom50Reverse, lastFrom1000NewInstances)
            self.assertEqual(firstFrom50Reverse, firstFrom1000NewInstances)

            # test with only 'to' and limit to 10 NewInstance changes
            c = DoGet(_REMOTE, '/changes', { 'type': 'NewInstance', 'to': lastFrom1000NewInstances, 'limit' : 10 })
            self.assertEqual(lastFrom1000NewInstances, c['Changes'][-1]['Seq'])
            self.assertEqual(10, len(c['Changes']))
            self.assertFalse(c['Done'])  # Done can not be used when working in reverse direction
            lastFrom10Reverse = c['Last']
            firstFrom10Reverse = c['First']
            self.assertLess(firstFrom10Reverse, lastFrom10Reverse)
            self.assertEqual(lastFrom10Reverse, lastFrom1000NewInstances)
            self.assertLessEqual(firstFrom50Reverse, firstFrom10Reverse)


    def test_archive(self):
        UploadInstance(_REMOTE, 'Knee/T1/IM-0001-0001.dcm')
        UploadInstance(_REMOTE, 'Knee/T2/IM-0001-0003.dcm')
        kneePatient = 'ca29faea-b6a0e17f-067743a1-8b778011-a48b2a17'
        kneeStudy = DoGet(_REMOTE, '/studies')[0]
        kneeSeries = DoGet(_REMOTE, '/series')[0]

        z, resp = GetArchive(_REMOTE, '/patients/%s/archive' % kneePatient)
        self.assertEqual(2, len(z.namelist()))
        if IsOrthancVersionAbove(_REMOTE, 1, 12, 6):
            self.assertIn('887 KNEE/A10003245599 IRM DU GENOU/MR T1W_aTSE/MR000001.dcm', z.namelist())
            self.assertIn('887 KNEE/A10003245599 IRM DU GENOU/MR T2W_TSE/MR000003.dcm', z.namelist())
        else:
            self.assertIn('887 KNEE/A10003245599 IRM DU GENOU/MR T1W_aTSE/MR000000.dcm', z.namelist())

        z, resp = GetArchive(_REMOTE, '/studies/%s/archive' % kneeStudy)
        self.assertEqual(2, len(z.namelist()))
        if IsOrthancVersionAbove(_REMOTE, 1, 12, 6):
            self.assertIn('887 KNEE/A10003245599 IRM DU GENOU/MR T1W_aTSE/MR000001.dcm', z.namelist())
            self.assertIn('887 KNEE/A10003245599 IRM DU GENOU/MR T2W_TSE/MR000003.dcm', z.namelist())
        else:
            self.assertIn('887 KNEE/A10003245599 IRM DU GENOU/MR T1W_aTSE/MR000000.dcm', z.namelist())

        z, resp = GetArchive(_REMOTE, '/series/%s/archive' % kneeSeries)
        self.assertEqual(1, len(z.namelist()))
        if IsOrthancVersionAbove(_REMOTE, 1, 12, 6):
            self.assertIn('887 KNEE/A10003245599 IRM DU GENOU/MR T1W_aTSE/MR000001.dcm', z.namelist())
        else:
            self.assertIn('887 KNEE/A10003245599 IRM DU GENOU/MR T1W_aTSE/MR000000.dcm', z.namelist())

        UploadInstance(_REMOTE, 'Brainix/Flair/IM-0001-0001.dcm')
        brainixPatient = '16738bc3-e47ed42a-43ce044c-a3414a45-cb069bd0'
        brainixStudy = '27f7126f-4f66fb14-03f4081b-f9341db2-53925988'

        z, resp = GetArchive(_REMOTE, '/patients/%s/archive' % kneePatient)
        self.assertEqual(2, len(z.namelist()))

        # archive with 2 patients
        z = PostArchive(_REMOTE, '/tools/create-archive', {
            'Resources' : [ brainixPatient, kneePatient ]
            })
        self.assertEqual(3, len(z.namelist()))
        if IsOrthancVersionAbove(_REMOTE, 1, 12, 6):
            self.assertIn('5Yp0E BRAINIX/0 IRM crbrale neurocrne/MR sT2WFLAIR/MR000001.dcm', z.namelist())
            self.assertIn('887 KNEE/A10003245599 IRM DU GENOU/MR T1W_aTSE/MR000001.dcm', z.namelist())
        else:
            self.assertIn('5Yp0E BRAINIX/0 IRM crbrale neurocrne/MR sT2WFLAIR/MR000000.dcm', z.namelist())
            self.assertIn('887 KNEE/A10003245599 IRM DU GENOU/MR T1W_aTSE/MR000000.dcm', z.namelist())

        z = PostArchive(_REMOTE, '/patients/%s/archive' % kneePatient, {
            'Synchronous' : True
            })
        self.assertEqual(2, len(z.namelist()))

        # archive with 2 studies
        z = PostArchive(_REMOTE, '/tools/create-archive', {
            'Resources' : [ brainixStudy, kneeStudy ]
            })
        self.assertEqual(3, len(z.namelist()))
        if IsOrthancVersionAbove(_REMOTE, 1, 12, 6):
            self.assertIn('5Yp0E BRAINIX/0 IRM crbrale neurocrne/MR sT2WFLAIR/MR000001.dcm', z.namelist())
            self.assertIn('887 KNEE/A10003245599 IRM DU GENOU/MR T1W_aTSE/MR000001.dcm', z.namelist())
        else:
            self.assertIn('5Yp0E BRAINIX/0 IRM crbrale neurocrne/MR sT2WFLAIR/MR000000.dcm', z.namelist())
            self.assertIn('887 KNEE/A10003245599 IRM DU GENOU/MR T1W_aTSE/MR000000.dcm', z.namelist())

        # archive with 1 patient & 1 study
        z = PostArchive(_REMOTE, '/tools/create-archive', {
            'Resources' : [ brainixPatient, kneeStudy ]
            })
        self.assertEqual(3, len(z.namelist()))
        if IsOrthancVersionAbove(_REMOTE, 1, 12, 6):
            self.assertIn('5Yp0E BRAINIX/0 IRM crbrale neurocrne/MR sT2WFLAIR/MR000001.dcm', z.namelist())
            self.assertIn('887 KNEE/A10003245599 IRM DU GENOU/MR T1W_aTSE/MR000001.dcm', z.namelist())
        else:
            self.assertIn('5Yp0E BRAINIX/0 IRM crbrale neurocrne/MR sT2WFLAIR/MR000000.dcm', z.namelist())
            self.assertIn('887 KNEE/A10003245599 IRM DU GENOU/MR T1W_aTSE/MR000000.dcm', z.namelist())


    def test_archive_with_patient_ids_collision(self):
        if IsOrthancVersionAbove(_REMOTE, 1, 12, 2):
            # one PatientID: COMMON
            # 2 PatientName: HELLO & WORLD

            hello = UploadInstance(_REMOTE, 'PatientIdsCollision/Image1.dcm')
            world = UploadInstance(_REMOTE, 'PatientIdsCollision/Image2.dcm')
            helloStudy = hello['ParentStudy']
            worldStudy = world['ParentStudy']
            helloPatient = hello['ParentPatient']
            worldPatient = world['ParentPatient']

            self.assertEqual(helloPatient, worldPatient)

            # when downloading the Patient, we do not really know what PatientName we will get in the zip
            z, resp = GetArchive(_REMOTE, '/patients/%s/archive' % helloPatient)
            self.assertEqual(2, len(z.namelist()))

            # when downloading studies individually, we want to have the PatientName that appears in the study
            z, resp = GetArchive(_REMOTE, '/studies/%s/archive' % helloStudy)
            self.assertEqual(1, len(z.namelist()))
            self.assertIn('COMMON HELLO/HELLO SERIES/Unknown Series/00000000.dcm', z.namelist())

            z, resp = GetArchive(_REMOTE, '/studies/%s/archive' % worldStudy)
            self.assertEqual(1, len(z.namelist()))
            self.assertIn('COMMON WORLD/WORLD SERIES/Unknown Series/00000000.dcm', z.namelist())



    def test_media_archive(self):
        UploadInstance(_REMOTE, 'Knee/T1/IM-0001-0001.dcm')
        UploadInstance(_REMOTE, 'Knee/T2/IM-0001-0001.dcm')

        z, resp = GetArchive(_REMOTE, '/patients/%s/media' % DoGet(_REMOTE, '/patients')[0])
        self.assertEqual(3, len(z.namelist()))
        self.assertTrue('IMAGES/IM0' in z.namelist())
        self.assertTrue('IMAGES/IM1' in z.namelist())
        self.assertTrue('DICOMDIR' in z.namelist())

        try:
            os.remove('/tmp/DICOMDIR')
        except:
            # The file does not exist
            pass

        z.extract('DICOMDIR', '/tmp')
        a = subprocess.check_output([ FindExecutable('dciodvfy'), '/tmp/DICOMDIR' ],
                                    stderr = subprocess.STDOUT).split('\n')
        self.assertEqual(3, len(a))
        self.assertTrue(a[0].startswith('Warning'))
        self.assertEqual('BasicDirectory', a[1])
        self.assertEqual('', a[2])

        a = subprocess.check_output([ FindExecutable('dcentvfy'), '/tmp/DICOMDIR' ],
                                    stderr = subprocess.STDOUT).split('\n')
        self.assertEqual(1, len(a))
        self.assertEqual('', a[0])

        a = subprocess.check_output([ FindExecutable('dcm2xml'), '/tmp/DICOMDIR' ])
        self.assertTrue(re.search('1.3.46.670589.11.17521.5.0.3124.2008081908590448738', a) != None)
        self.assertTrue(re.search('1.3.46.670589.11.17521.5.0.3124.2008081909113806560', a) != None)

        os.remove('/tmp/DICOMDIR')


    def test_protection(self):
        UploadInstance(_REMOTE, 'Knee/T1/IM-0001-0001.dcm')
        UploadInstance(_REMOTE, 'Brainix/Flair/IM-0001-0001.dcm')
        self.assertEqual(2, len(DoGet(_REMOTE, '/patients')))
        a = DoGet(_REMOTE, '/patients')[0]
        b = DoGet(_REMOTE, '/patients')[1]
        self.assertEqual(0, DoGet(_REMOTE, '/patients/%s/protected' % a))
        DoPut(_REMOTE, '/patients/%s/protected' % a, '0', 'text/plain')
        self.assertEqual(0, DoGet(_REMOTE, '/patients/%s/protected' % a))
        DoPut(_REMOTE, '/patients/%s/protected' % a, '1', 'text/plain')
        self.assertEqual(1, DoGet(_REMOTE, '/patients/%s/protected' % a))

        if IsOrthancVersionAbove(_REMOTE, 1, 12, 8):
            p = DoGet(_REMOTE, '/patients/%s' % a)
            self.assertIn('IsProtected', p)
            self.assertTrue(p['IsProtected'])

        DoPut(_REMOTE, '/patients/%s/protected' % a, '0', 'text/plain')
        self.assertEqual(0, DoGet(_REMOTE, '/patients/%s/protected' % a))

        if IsOrthancVersionAbove(_REMOTE, 1, 12, 8):
            p = DoGet(_REMOTE, '/patients/%s' % a)
            self.assertIn('IsProtected', p)
            self.assertFalse(p['IsProtected'])

    def test_raw_tags(self):
        i = UploadInstance(_REMOTE, 'PrivateTags.dcm')['ID']

        dicom = DoGet(_REMOTE, '/instances/%s/file' % i)
        self.assertEqual('1a7c56cb02d6e742cc9c856a8ac182e3', ComputeMD5(dicom))

        s = '/instances/%s/content/' % i

        self.assertEqual('LOGIQBOOK', DoGet(_REMOTE, s + '0008-1010').strip())
        self.assertRaises(Exception, lambda: DoGet(_REMOTE, s + '0008-1011'))

        self.assertEqual('Abdomen', DoGet(_REMOTE, s + '7fe1-1001/0/7fe1-1008/0/7fe1-1057').strip())
        self.assertEqual('cla_3c', DoGet(_REMOTE, s + '7fe1-1001/0/7fe1-1008/8/7fe1-1057').strip())

        UploadInstance(_REMOTE, 'Brainix/Epi/IM-0001-0001.dcm')
        UploadInstance(_REMOTE, 'Brainix/Flair/IM-0001-0001.dcm')
        UploadInstance(_REMOTE, 'Knee/T1/IM-0001-0001.dcm')
        UploadInstance(_REMOTE, 'Knee/T2/IM-0001-0001.dcm')

        for i in DoGet(_REMOTE, '/instances'):
            aid = DoGet(_REMOTE, '/instances/%s' % i)['MainDicomTags']['SOPInstanceUID']
            self.assertEqual(aid, DoGet(_REMOTE, '/instances/%s/content/0008-0018' % i).replace(chr(0), ''))


    def test_raw_tags_mdn(self):
        # Bug reported by Cyril Paulus
        i = UploadInstance(_REMOTE, 'PrivateMDNTags.dcm')['ID']
        self.assertAlmostEqual(0.000027, DoGet(_REMOTE, '/instances/%s/content/7053-1000' % i))


    def test_modify_instance(self):
        i = UploadInstance(_REMOTE, 'PrivateTags.dcm')['ID']
        modified = DoPost(_REMOTE, '/instances/%s/modify' % i,
                          json.dumps({
                    "Replace" : {
                        "PatientName" : "hello",
                        #"PatientID" : "world"
                        },
                    "Remove" : [ "StationName" ],
                    "RemovePrivateTags" : True
                    }),
                          'application/json')
        j = DoPost(_REMOTE, '/instances', modified, 'application/dicom')['ID']

        self.assertNotEqual('hello', DoGet(_REMOTE, '/instances/%s/content/0010-0010' % i).strip())
        #self.assertNotEqual('world', DoGet(_REMOTE, '/instances/%s/content/0010-0020' % i).strip())
        self.assertEqual('LOGIQBOOK', DoGet(_REMOTE, '/instances/%s/content/0008-1010' % i).strip())
        DoGet(_REMOTE, '/instances/%s/content/6003-1010' % i)  # Some private tag

        self.assertEqual('hello', DoGet(_REMOTE, '/instances/%s/content/0010-0010' % j).strip())
        #self.assertEqual('world', DoGet(_REMOTE, '/instances/%s/content/0010-0020' % j).strip())
        self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/instances/%s/content/0008-1010' % j))
        self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/instances/%s/content/6003-1010' % j))


    def test_modify_series(self):
        # Upload 4 images from the same series
        for i in range(4):
            UploadInstance(_REMOTE, 'Brainix/Epi/IM-0001-000%d.dcm' % (i + 1))

        origSeries = DoGet(_REMOTE, '/series')[0]
        newSeries = DoPost(_REMOTE, '/series/%s/modify' % origSeries,
                           '{"Replace":{"PatientName":"Jodogne"}}',
                           'application/json')['ID']

        self.assertEqual(origSeries, DoGet(_REMOTE, '/series/%s' % newSeries)['ModifiedFrom'])
        instances = DoGet(_REMOTE, '/series/%s' % newSeries)['Instances']
        self.assertEqual(4, len(instances))
        for i in instances:
            j = DoGet(_REMOTE, '/instances/%s' % i)['ModifiedFrom']
            self.assertEqual(newSeries, DoGet(_REMOTE, '/instances/%s' % i)['ParentSeries'])
            self.assertEqual(origSeries, DoGet(_REMOTE, '/instances/%s' % j)['ParentSeries'])

            self.assertEqual('Jodogne', DoGet(_REMOTE, '/instances/%s/content/0010-0010' % i).strip())
            self.assertNotEqual('Jodogne', DoGet(_REMOTE, '/instances/%s/content/0010-0010' % j).strip())


    def test_modify_study(self):
        # Upload 4 images from the 2 series of the same study
        for i in range(4):
            UploadInstance(_REMOTE, 'Brainix/Flair/IM-0001-000%d.dcm' % (i + 1))
            UploadInstance(_REMOTE, 'Brainix/Epi/IM-0001-000%d.dcm' % (i + 1))

        origStudy = DoGet(_REMOTE, '/studies')[0]
        newStudy = DoPost(_REMOTE, '/studies/%s/modify' % origStudy,
                          '{"Replace":{"PatientName":"Jodogne"}}',
                          'application/json')['ID']

        self.assertEqual(origStudy, DoGet(_REMOTE, '/studies/%s' % newStudy)['ModifiedFrom'])
        series = DoGet(_REMOTE, '/studies/%s' % newStudy)['Series']
        self.assertEqual(2, len(series))
        for s in series:
            ss = DoGet(_REMOTE, '/series/%s' % s)['ModifiedFrom']
            self.assertEqual(newStudy, DoGet(_REMOTE, '/series/%s' % s)['ParentStudy'])
            self.assertEqual(origStudy, DoGet(_REMOTE, '/series/%s' % ss)['ParentStudy'])

            instances = DoGet(_REMOTE, '/series/%s' % s)['Instances']
            for i in instances:
                j = DoGet(_REMOTE, '/instances/%s' % i)['ModifiedFrom']
                self.assertEqual(s, DoGet(_REMOTE, '/instances/%s' % i)['ParentSeries'])
                self.assertEqual(ss, DoGet(_REMOTE, '/instances/%s' % j)['ParentSeries'])

                self.assertEqual('Jodogne', DoGet(_REMOTE, '/instances/%s/content/0010-0010' % i).strip())
                self.assertNotEqual('Jodogne', DoGet(_REMOTE, '/instances/%s/content/0010-0010' % j).strip())


    def test_anonymize_series(self):
        # Upload 4 images from the same series
        for i in range(4):
            UploadInstance(_REMOTE, 'Brainix/Epi/IM-0001-000%d.dcm' % (i + 1))

        origSeries = DoGet(_REMOTE, '/series')[0]
        newSeries = DoPost(_REMOTE, '/series/%s/anonymize' % origSeries,
                           '{}',
                           'application/json')['ID']

        self.assertEqual(origSeries, DoGet(_REMOTE, '/series/%s' % newSeries)['AnonymizedFrom'])
        instances = DoGet(_REMOTE, '/series/%s' % newSeries)['Instances']
        self.assertEqual(4, len(instances))
        for i in instances:
            j = DoGet(_REMOTE, '/instances/%s' % i)['AnonymizedFrom']
            self.assertEqual(newSeries, DoGet(_REMOTE, '/instances/%s' % i)['ParentSeries'])
            self.assertEqual(origSeries, DoGet(_REMOTE, '/instances/%s' % j)['ParentSeries'])

            DoGet(_REMOTE, '/instances/%s/content/0008-1010' % j)
            self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/instances/%s/content/0008-1010' % i))


    def test_anonymize_study(self):
        # Upload 4 images from the 2 series of the same study
        for i in range(4):
            UploadInstance(_REMOTE, 'Brainix/Flair/IM-0001-000%d.dcm' % (i + 1))
            UploadInstance(_REMOTE, 'Brainix/Epi/IM-0001-000%d.dcm' % (i + 1))

        origStudy = DoGet(_REMOTE, '/studies')[0]
        newStudy = DoPost(_REMOTE,'/studies/%s/anonymize' % origStudy,
                          '{"Replace":{"PatientName":"Jodogne"}}',
                          'application/json')['ID']

        self.assertEqual(origStudy, DoGet(_REMOTE, '/studies/%s' % newStudy)['AnonymizedFrom'])
        series = DoGet(_REMOTE, '/studies/%s' % newStudy)['Series']
        self.assertEqual(2, len(series))
        for s in series:
            ss = DoGet(_REMOTE, '/series/%s' % s)['AnonymizedFrom']
            self.assertEqual(newStudy, DoGet(_REMOTE, '/series/%s' % s)['ParentStudy'])
            self.assertEqual(origStudy, DoGet(_REMOTE, '/series/%s' % ss)['ParentStudy'])

            instances = DoGet(_REMOTE, '/series/%s' % s)['Instances']
            for i in instances:
                j = DoGet(_REMOTE, '/instances/%s' % i)['AnonymizedFrom']
                self.assertEqual(s, DoGet(_REMOTE, '/instances/%s' % i)['ParentSeries'])
                self.assertEqual(ss, DoGet(_REMOTE, '/instances/%s' % j)['ParentSeries'])

                self.assertEqual('Jodogne', DoGet(_REMOTE, '/instances/%s/content/0010-0010' % i).strip())
                self.assertNotEqual('Jodogne', DoGet(_REMOTE, '/instances/%s/content/0010-0010' % j).strip())



    def test_storescu(self):
        # Check emptiness
        e = DoGet(_REMOTE, '/exports')
        self.assertEqual(0, len(e['Exports']))
        self.assertEqual(0, e['Last'])
        self.assertTrue(e['Done'])
        e = DoGet(_REMOTE, '/exports?last')
        self.assertEqual(0, len(e['Exports']))
        self.assertEqual(0, e['Last'])
        self.assertTrue(e['Done'])

        # Add 1 instance
        i = UploadInstance(_REMOTE, 'DummyCT.dcm')['ID']
        self.assertEqual(0, len(DoGet(_LOCAL, '/patients')))

        # Export the instance
        j = DoPost(_REMOTE, '/modalities/orthanctest/store', str(i), 'text/plain')  # instance
        self.assertEqual(1, len(DoGet(_LOCAL, '/patients')))
        self.assertEqual(1, len(DoGet(_LOCAL, '/studies')))
        self.assertEqual(1, len(DoGet(_LOCAL, '/series')))
        self.assertEqual(1, len(DoGet(_LOCAL, '/instances')))

        e = DoGet(_REMOTE, '/exports')
        self.assertEqual(1, len(e['Exports']))
        self.assertTrue(e['Done'])
        self.assertEqual(e['Exports'][-1]['Seq'], e['Last'])
        e = DoGet(_REMOTE, '/exports?limit=1')
        self.assertEqual(1, len(e['Exports']))
        self.assertTrue(e['Done'])
        self.assertEqual(e['Exports'][-1]['Seq'], e['Last'])
        e = DoGet(_REMOTE, '/exports?last')
        self.assertEqual(1, len(e['Exports']))
        self.assertTrue(e['Done'])
        self.assertEqual(e['Exports'][-1]['Seq'], e['Last'])
        seqInstance = e['Last']

        # Export the series
        j = DoPost(_REMOTE, '/modalities/orthanctest/store', 'f2635388-f01d497a-15f7c06b-ad7dba06-c4c599fe', 'text/plain')

        e = DoGet(_REMOTE, '/exports')
        self.assertEqual(2, len(e['Exports']))
        self.assertTrue(e['Done'])
        self.assertEqual(e['Exports'][-1]['Seq'], e['Last'])
        seqSeries = e['Last']
        self.assertNotEqual(seqInstance, seqSeries)
        e = DoGet(_REMOTE, '/exports?limit=1&since=0')
        self.assertEqual(1, len(e['Exports']))
        self.assertFalse(e['Done'])
        self.assertEqual(e['Exports'][-1]['Seq'], seqInstance)
        e = DoGet(_REMOTE, '/exports?limit=1&since=' + str(seqInstance))
        self.assertEqual(1, len(e['Exports']))
        self.assertTrue(e['Done'])
        self.assertEqual(e['Exports'][-1]['Seq'], seqSeries)
        e = DoGet(_REMOTE, '/exports?last')
        self.assertEqual(1, len(e['Exports']))
        self.assertTrue(e['Done'])
        self.assertEqual(e['Exports'][-1]['Seq'], seqSeries)

        # Export the study
        j = DoPost(_REMOTE, '/modalities/orthanctest/store', 'b9c08539-26f93bde-c81ab0d7-bffaf2cb-a4d0bdd0', 'text/plain')
        seqStudy = DoGet(_REMOTE, '/exports')['Last']

        # Export the patient
        j = DoPost(_REMOTE, '/modalities/orthanctest/store', '6816cb19-844d5aee-85245eba-28e841e6-2414fae2', 'text/plain')
        self.assertEqual(1, len(DoGet(_LOCAL, '/patients')))
        self.assertEqual(1, len(DoGet(_LOCAL, '/studies')))
        self.assertEqual(1, len(DoGet(_LOCAL, '/series')))
        self.assertEqual(1, len(DoGet(_LOCAL, '/instances')))

        e = DoGet(_REMOTE, '/exports')
        self.assertEqual(4, len(e['Exports']))
        self.assertTrue(e['Done'])
        self.assertEqual(e['Exports'][-1]['Seq'], e['Last'])
        seqPatient = e['Last']
        self.assertNotEqual(seqInstance, seqSeries)
        self.assertNotEqual(seqSeries, seqStudy)
        self.assertNotEqual(seqStudy, seqPatient)
        self.assertTrue(seqInstance < seqSeries)
        self.assertTrue(seqSeries < seqStudy)
        self.assertTrue(seqStudy < seqPatient)
        e = DoGet(_REMOTE, '/exports?limit=1&since=0')
        self.assertEqual(1, len(e['Exports']))
        self.assertFalse(e['Done'])
        self.assertEqual(e['Exports'][-1]['Seq'], seqInstance)
        e = DoGet(_REMOTE, '/exports?limit=1&since=' + str(seqInstance))
        self.assertEqual(1, len(e['Exports']))
        self.assertFalse(e['Done'])
        self.assertEqual(e['Exports'][-1]['Seq'], seqSeries)
        e = DoGet(_REMOTE, '/exports?limit=1&since=' + str(seqSeries))
        self.assertEqual(1, len(e['Exports']))
        self.assertFalse(e['Done'])
        self.assertEqual(e['Exports'][-1]['Seq'], seqStudy)
        e = DoGet(_REMOTE, '/exports?limit=1&since=' + str(seqStudy))
        self.assertEqual(1, len(e['Exports']))
        self.assertTrue(e['Done'])
        self.assertEqual(e['Exports'][-1]['Seq'], seqPatient)
        e = DoGet(_REMOTE, '/exports?last')
        self.assertEqual(1, len(e['Exports']))
        self.assertTrue(e['Done'])
        self.assertEqual(e['Exports'][-1]['Seq'], seqPatient)


        # Check the content of the logged information
        e = DoGet(_REMOTE, '/exports')['Exports']

        if 'PatientID' in e[0]:
            # Since Orthanc 0.8.6
            patient = 'PatientID'
            study = 'StudyInstanceUID'
            series = 'SeriesInstanceUID'
            instance = 'SOPInstanceUID'
        else:
            # Up to Orthanc 0.8.5
            patient = 'PatientId'
            study = 'StudyInstanceUid'
            series = 'SeriesInstanceUid'
            instance = 'SopInstanceUid'

        for k in range(4):
            self.assertTrue('Date' in e[k])
            self.assertTrue('Seq' in e[k])
            self.assertEqual('orthanctest', e[k]['RemoteModality'])

        self.assertEqual(10, len(e[0]))
        self.assertEqual('Instance', e[0]['ResourceType'])
        self.assertEqual('66a662ce-7430e543-bad44d47-0dc5a943-ec7a538d', e[0]['ID'])
        self.assertEqual('/instances/66a662ce-7430e543-bad44d47-0dc5a943-ec7a538d', e[0]['Path'])
        self.assertEqual('1.2.840.113619.2.176.2025.1499492.7040.1171286242.109', e[0][instance])
        self.assertEqual('1.2.840.113619.2.176.2025.1499492.7391.1171285944.394', e[0][series])
        self.assertEqual('1.2.840.113619.2.176.2025.1499492.7391.1171285944.390', e[0][study])
        self.assertEqual('ozp00SjY2xG', e[0][patient])

        self.assertEqual(9, len(e[1]))
        self.assertEqual('Series', e[1]['ResourceType'])
        self.assertEqual('f2635388-f01d497a-15f7c06b-ad7dba06-c4c599fe', e[1]['ID'])
        self.assertEqual('/series/f2635388-f01d497a-15f7c06b-ad7dba06-c4c599fe', e[1]['Path'])
        self.assertEqual('1.2.840.113619.2.176.2025.1499492.7391.1171285944.394', e[1][series])
        self.assertEqual('1.2.840.113619.2.176.2025.1499492.7391.1171285944.390', e[1][study])
        self.assertEqual('ozp00SjY2xG', e[1][patient])

        self.assertEqual(8, len(e[2]))
        self.assertEqual('Study', e[2]['ResourceType'])
        self.assertEqual('b9c08539-26f93bde-c81ab0d7-bffaf2cb-a4d0bdd0', e[2]['ID'])
        self.assertEqual('/studies/b9c08539-26f93bde-c81ab0d7-bffaf2cb-a4d0bdd0', e[2]['Path'])
        self.assertEqual('1.2.840.113619.2.176.2025.1499492.7391.1171285944.390', e[2][study])
        self.assertEqual('ozp00SjY2xG', e[2][patient])

        self.assertEqual(7, len(e[3]))
        self.assertEqual('Patient', e[3]['ResourceType'])
        self.assertEqual('6816cb19-844d5aee-85245eba-28e841e6-2414fae2', e[3]['ID'])
        self.assertEqual('/patients/6816cb19-844d5aee-85245eba-28e841e6-2414fae2', e[3]['Path'])
        self.assertEqual('ozp00SjY2xG', e[3][patient])

        DropOrthanc(_REMOTE)
        self.assertEqual(0, len(DoGet(_REMOTE, '/exports')['Exports']))


    def test_store_peer(self):
        self.assertEqual(0, len(DoGet(_LOCAL, '/exports')['Exports']))
        self.assertEqual(0, len(DoGet(_REMOTE, '/exports')['Exports']))

        i = UploadInstance(_REMOTE, 'DummyCT.dcm')['ID']
        self.assertEqual(0, len(DoGet(_LOCAL, '/patients')))
        self.assertEqual(1, len(DoGet(_REMOTE, '/patients')))

        j = DoPost(_REMOTE, '/peers/peer/store', str(i), 'text/plain')
        self.assertEqual(1, len(DoGet(_LOCAL, '/patients')))
        self.assertEqual(1, len(DoGet(_REMOTE, '/patients')))

        self.assertEqual(1, len(DoGet(_REMOTE, '/exports')['Exports']))

        DropOrthanc(_REMOTE)
        self.assertEqual(0, len(DoGet(_REMOTE, '/exports')['Exports']))


    def test_bulk_storescu(self):
        self.assertEqual(0, len(DoGet(_LOCAL, '/patients')))
        
        a = UploadInstance(_REMOTE, 'Knee/T1/IM-0001-0001.dcm')
        b = UploadInstance(_REMOTE, 'Knee/T2/IM-0001-0001.dcm')

        j = DoPost(_REMOTE, '/modalities/orthanctest/store', [ a['ID'], b['ID'] ], 'application/json')
        self.assertEqual(2, len(DoGet(_LOCAL, '/instances')))

        DropOrthanc(_LOCAL)

        # Send using patient's UUID
        self.assertEqual(0, len(DoGet(_LOCAL, '/instances')))
        j = DoPost(_REMOTE, '/modalities/orthanctest/store', 
                   [ 'ca29faea-b6a0e17f-067743a1-8b778011-a48b2a17' ], 'application/json')
        self.assertEqual(2, len(DoGet(_LOCAL, '/instances')))
        

    def test_color(self):
        i = UploadInstance(_REMOTE, 'ColorTestMalaterre.dcm')['ID']
        im = GetImage(_REMOTE, '/instances/%s/preview' % i)
        self.assertEqual("RGB", im.mode)
        self.assertEqual(41, im.size[0])
        self.assertEqual(41, im.size[1])

        # http://effbot.org/zone/pil-comparing-images.htm
        truth = Image.open(GetDatabasePath('ColorTestMalaterre.png'))
        self.assertTrue(ImageChops.difference(im, truth).getbbox() is None)


    def test_faking_ruby_put(self):
        UploadInstance(_REMOTE, 'Knee/T1/IM-0001-0001.dcm')
        UploadInstance(_REMOTE, 'Brainix/Flair/IM-0001-0001.dcm')
        self.assertEqual(2, len(DoGet(_REMOTE, '/patients')))
        a = DoGet(_REMOTE, '/patients')[0]
        b = DoGet(_REMOTE, '/patients')[1]
        self.assertEqual(0, DoGet(_REMOTE, '/patients/%s/protected' % a))
        DoGet(_REMOTE, '/patients/%s/protected' % a, data = { '_method' : 'PUT' }, body = '0')
        self.assertEqual(0, DoGet(_REMOTE, '/patients/%s/protected' % a))
        DoGet(_REMOTE, '/patients/%s/protected' % a, data = { '_method' : 'PUT' }, body = '1')
        self.assertEqual(1, DoGet(_REMOTE, '/patients/%s/protected' % a))
        DoGet(_REMOTE, '/patients/%s/protected' % a, data = { '_method' : 'PUT' }, body = '0')
        self.assertEqual(0, DoGet(_REMOTE, '/patients/%s/protected' % a))


    def test_faking_ruby_delete(self):
        UploadInstance(_REMOTE, 'Knee/T1/IM-0001-0001.dcm')
        UploadInstance(_REMOTE, 'Brainix/Flair/IM-0001-0001.dcm')
        self.assertEqual(2, len(DoGet(_REMOTE, '/patients')))
        a = DoGet(_REMOTE, '/patients')[0]
        b = DoGet(_REMOTE, '/patients')[1]
        DoGet(_REMOTE, '/patients/%s' % a, data = { '_method' : 'DELETE' })
        self.assertEqual(1, len(DoGet(_REMOTE, '/patients')))
        DoGet(_REMOTE, '/patients/%s' % b, data = { '_method' : 'DELETE' })
        self.assertEqual(0, len(DoGet(_REMOTE, '/patients')))


    def test_faking_google_put(self):
        UploadInstance(_REMOTE, 'Knee/T1/IM-0001-0001.dcm')
        UploadInstance(_REMOTE, 'Brainix/Flair/IM-0001-0001.dcm')
        self.assertEqual(2, len(DoGet(_REMOTE, '/patients')))
        a = DoGet(_REMOTE, '/patients')[0]
        b = DoGet(_REMOTE, '/patients')[1]
        self.assertEqual(0, DoGet(_REMOTE, '/patients/%s/protected' % a))
        DoPost(_REMOTE, '/patients/%s/protected' % a, headers = { 'X-HTTP-Method-Override' : 'PUT' }, data = '0')
        self.assertEqual(0, DoGet(_REMOTE, '/patients/%s/protected' % a))
        DoPost(_REMOTE, '/patients/%s/protected' % a, headers = { 'X-HTTP-Method-Override' : 'PUT' }, data = '1')
        self.assertEqual(1, DoGet(_REMOTE, '/patients/%s/protected' % a))
        DoPost(_REMOTE, '/patients/%s/protected' % a, headers = { 'X-HTTP-Method-Override' : 'PUT' }, data = '0')
        self.assertEqual(0, DoGet(_REMOTE, '/patients/%s/protected' % a))


    def test_faking_google_delete(self):
        UploadInstance(_REMOTE, 'Knee/T1/IM-0001-0001.dcm')
        UploadInstance(_REMOTE, 'Brainix/Flair/IM-0001-0001.dcm')
        self.assertEqual(2, len(DoGet(_REMOTE, '/patients')))
        a = DoGet(_REMOTE, '/patients')[0]
        b = DoGet(_REMOTE, '/patients')[1]
        DoPost(_REMOTE, '/patients/%s' % a, headers = { 'X-HTTP-Method-Override' : 'DELETE' })
        self.assertEqual(1, len(DoGet(_REMOTE, '/patients')))
        DoPost(_REMOTE, '/patients/%s' % b, headers = { 'X-HTTP-Method-Override' : 'DELETE' })
        self.assertEqual(0, len(DoGet(_REMOTE, '/patients')))


    def test_lua(self):
        self.assertEqual(42, DoPost(_REMOTE, '/tools/execute-script', 'print(42)'))
        self.assertTrue(IsDefinedInLua(_REMOTE, 'PrintRecursive'))
        self.assertFalse(IsDefinedInLua(_REMOTE, 'HelloWorld'))


    def test_metadata(self):
        UploadInstance(_REMOTE, 'Knee/T1/IM-0001-0001.dcm')
        p = DoGet(_REMOTE, '/patients')[0]
        i = DoGet(_REMOTE, '/instances')[0]
        series = DoGet(_REMOTE, '/series')[0]

        m = DoGet(_REMOTE, '/patients/%s/metadata' % p)
        if IsOrthancVersionAbove(_REMOTE, 1, 12, 9) and HasPostgresIndexPlugin(_REMOTE):
            self.assertEqual(3, len(m))
            self.assertTrue('MainDicomTagsSignature' in m)
            self.assertTrue('PatientRecyclingOrder' in m)
        elif IsOrthancVersionAbove(_REMOTE, 1, 11, 0):
            self.assertEqual(2, len(m))
            self.assertTrue('MainDicomTagsSignature' in m)
        else:
            self.assertEqual(1, len(m))

        self.assertTrue('LastUpdate' in m)

        # The lines below failed on Orthanc <= 1.8.2
        self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/studies/%s/metadata' % p))
        self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/series/%s/metadata' % p))
        self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/instances/%s/metadata' % p))

        m = DoGet(_REMOTE, '/studies/%s/metadata' % DoGet(_REMOTE, '/studies')[0])
        if IsOrthancVersionAbove(_REMOTE, 1, 11, 0):
            self.assertEqual(2, len(m))
            self.assertTrue('MainDicomTagsSignature' in m)
        else:
            self.assertEqual(1, len(m))
        self.assertTrue('LastUpdate' in m)

        m = DoGet(_REMOTE, '/series/%s/metadata' % series)
        if IsOrthancVersionAbove(_REMOTE, 1, 12, 5):
            self.assertEqual(4, len(m))
            self.assertTrue('MainDicomSequences' in m)    # since RequestAttributeSequence is now in the MainDicomTags
        elif IsOrthancVersionAbove(_REMOTE, 1, 11, 0):
            self.assertEqual(3, len(m))
            self.assertTrue('MainDicomTagsSignature' in m)
        else:
            self.assertEqual(2, len(m))
        self.assertTrue('LastUpdate' in m)

        # New in Orthanc 1.9.0
        self.assertTrue('RemoteAET' in m)
        self.assertEqual(DoGet(_REMOTE, '/series/%s/metadata/RemoteAET' % series), '')  # None, received by REST API

        m = DoGet(_REMOTE, '/instances/%s/metadata' % i)
        if IsOrthancVersionAbove(_REMOTE, 1, 11, 0):
            self.assertEqual(10, len(m))
        elif IsOrthancVersionAbove(_REMOTE, 1, 9, 1):
            self.assertEqual(9, len(m))
        else:
            self.assertEqual(8, len(m))

        if IsOrthancVersionAbove(_REMOTE, 1, 11, 0):
            self.assertTrue('MainDicomTagsSignature' in m)

        if IsOrthancVersionAbove(_REMOTE, 1, 9, 1):
            self.assertTrue('PixelDataOffset' in m)  # New in Orthanc 1.9.1
            self.assertEqual(int(DoGet(_REMOTE, '/instances/%s/metadata/PixelDataOffset' % i)), 0x0c78)

        self.assertTrue('IndexInSeries' in m)
        self.assertTrue('ReceptionDate' in m)
        self.assertTrue('RemoteAET' in m)
        self.assertTrue('Origin' in m)
        self.assertTrue('TransferSyntax' in m)
        self.assertTrue('SopClassUid' in m)
        self.assertTrue('RemoteIP' in m)
        self.assertTrue('HttpUsername' in m)
        self.assertEqual(DoGet(_REMOTE, '/instances/%s/metadata/IndexInSeries' % i), 1)
        self.assertEqual(DoGet(_REMOTE, '/instances/%s/metadata/Origin' % i), 'RestApi')
        self.assertEqual(DoGet(_REMOTE, '/instances/%s/metadata/RemoteAET' % i), '')  # None, received by REST API
        self.assertEqual(DoGet(_REMOTE, '/instances/%s/metadata/TransferSyntax' % i), '1.2.840.10008.1.2.4.91')  # JPEG2k
        self.assertEqual(DoGet(_REMOTE, '/instances/%s/metadata/SopClassUid' % i), '1.2.840.10008.5.1.4.1.1.4')

        # Play with custom metadata
        (headers, body) = DoPutRaw(_REMOTE, '/patients/%s/metadata/5555' % p, 'coucou')
        self.assertEqual('200', headers['status'])
        self.assertEqual('', body)

        if IsOrthancVersionAbove(_REMOTE, 1, 9, 2):
            self.assertEqual('"0-%s"' % ComputeMD5('coucou'), headers['etag'])
        else:
            self.assertFalse('ETag' in headers)
            self.assertFalse('etag' in headers)
            
        m = DoGet(_REMOTE, '/patients/%s/metadata' % p)
        if IsOrthancVersionAbove(_REMOTE, 1, 12, 9) and HasPostgresIndexPlugin(_REMOTE):
            self.assertEqual(4, len(m))
            self.assertTrue('MainDicomTagsSignature' in m)
            self.assertTrue('PatientRecyclingOrder' in m)
        elif IsOrthancVersionAbove(_REMOTE, 1, 11, 0):
            self.assertEqual(3, len(m))
            self.assertTrue('MainDicomTagsSignature' in m)
        else:
            self.assertEqual(2, len(m))
        self.assertTrue('LastUpdate' in m)
        self.assertTrue('5555' in m)
        self.assertEqual('coucou', DoGet(_REMOTE, '/patients/%s/metadata/5555' % p))

        if IsOrthancVersionAbove(_REMOTE, 1, 9, 2):
            DoPut(_REMOTE, '/patients/%s/metadata/5555' % p, 'hello', headers = {
                'If-Match' : headers['etag']
            })
        else:
            DoPut(_REMOTE, '/patients/%s/metadata/5555' % p, 'hello')

        (headers, body) = DoGetRaw(_REMOTE, '/patients/%s/metadata/5555' % p)
        self.assertEqual('200', headers['status'])
        self.assertEqual('hello', body)

        if IsOrthancVersionAbove(_REMOTE, 1, 9, 2):
            DoDelete(_REMOTE, '/patients/%s/metadata/5555' % p, headers = {
                'If-Match' : headers['etag']
            })
        else:
            DoDelete(_REMOTE, '/patients/%s/metadata/5555' % p)
            
        m = DoGet(_REMOTE, '/patients/%s/metadata' % p)
        if IsOrthancVersionAbove(_REMOTE, 1, 12, 9) and HasPostgresIndexPlugin(_REMOTE):
            self.assertEqual(3, len(m))
            self.assertTrue('MainDicomTagsSignature' in m)
            self.assertTrue('PatientRecyclingOrder' in m)
        elif IsOrthancVersionAbove(_REMOTE, 1, 11, 0):
            self.assertEqual(2, len(m))
            self.assertTrue('MainDicomTagsSignature' in m)
        else:
            self.assertEqual(1, len(m))
        self.assertTrue('LastUpdate' in m)


    def test_statistics(self):
        # Upload 16 instances
        for i in range(4):
            UploadInstance(_REMOTE, 'Brainix/Flair/IM-0001-000%d.dcm' % (i + 1))
            UploadInstance(_REMOTE, 'Brainix/Epi/IM-0001-000%d.dcm' % (i + 1))
            UploadInstance(_REMOTE, 'Knee/T1/IM-0001-000%d.dcm' % (i + 1))
            UploadInstance(_REMOTE, 'Knee/T2/IM-0001-000%d.dcm' % (i + 1))

        s = DoGet(_REMOTE, '/statistics')
        self.assertEqual(16, s['CountInstances'])
        self.assertEqual(2, s['CountPatients'])
        self.assertEqual(2, s['CountStudies'])
        self.assertEqual(4, s['CountSeries'])
        d = int(s['TotalUncompressedSize'])

        e = 0
        for patient in DoGet(_REMOTE, '/patients'):
            s = DoGet(_REMOTE, '/patients/%s/statistics' % patient)
            self.assertEqual(8, s['CountInstances'])
            self.assertEqual(1, s['CountStudies'])
            self.assertEqual(2, s['CountSeries'])
            e += int(s['UncompressedSize'])

        for study in DoGet(_REMOTE, '/studies'):
            s = DoGet(_REMOTE, '/studies/%s/statistics' % study)
            self.assertEqual(8, s['CountInstances'])
            self.assertEqual(2, s['CountSeries'])
            e += int(s['UncompressedSize'])

        for series in DoGet(_REMOTE, '/series'):
            s = DoGet(_REMOTE, '/series/%s/statistics' % series)
            self.assertEqual(4, s['CountInstances'])
            e += int(s['UncompressedSize'])

        self.assertEqual(3 * d, e)


    def test_custom_attachment(self):
        u = UploadInstance(_REMOTE, 'Brainix/Flair/IM-0001-0001.dcm') ['ID']

        patient = DoGet(_REMOTE, '/patients')[0]
        instance = DoGet(_REMOTE, '/instances')[0]
        size = int(DoGet(_REMOTE, '/patients/%s/statistics' % patient)['DiskSize'])
        self.assertEqual(size, int(DoGet(_REMOTE, '/statistics')['TotalDiskSize']))
        
        self.assertEqual(0, len(DoGet(_REMOTE, '/patients/%s/attachments' % patient)))
        self.assertTrue('dicom' in DoGet(_REMOTE, '/instances/%s/attachments' % instance))

        if IsOrthancVersionAbove(_REMOTE, 1, 9, 1):
            if IsDicomUntilPixelDataStored(_REMOTE):
                self.assertEqual(2, len(DoGet(_REMOTE, '/instances/%s/attachments' % instance)))
                self.assertTrue('dicom-until-pixel-data' in DoGet(_REMOTE, '/instances/%s/attachments' % instance))

                # New in Orthanc 1.10.0
                a = DoGet(_REMOTE, '/instances/%s/attachments?full' % instance)
                self.assertEqual(2, len(a))
                self.assertEqual(1, a['dicom'])
                self.assertEqual(3, a['dicom-until-pixel-data'])

            else:
                self.assertEqual(1, len(DoGet(_REMOTE, '/instances/%s/attachments' % instance)))

                # New in Orthanc 1.10.0
                a = DoGet(_REMOTE, '/instances/%s/attachments?full' % instance)
                self.assertEqual(1, len(a))
                self.assertEqual(1, a['dicom'])
        else:
            self.assertEqual(2, len(DoGet(_REMOTE, '/instances/%s/attachments' % instance)))
            self.assertTrue('dicom-as-json' in DoGet(_REMOTE, '/instances/%s/attachments' % instance))

            # New in Orthanc 1.10.0
            self.assertRaises(Exception, lambda: DoGet(
                _REMOTE, '/instances/%s/attachments?full' % instance))

        self.assertRaises(Exception, lambda: DoPut(_REMOTE, '/patients/%s/attachments/22' % patient, 'hello'))
        hello = 'hellohellohellohellohellohellohellohellohello'
        DoPut(_REMOTE, '/patients/%s/attachments/1025' % patient, hello)
        self.assertEqual(int(DoGet(_REMOTE, '/patients/%s/statistics' % patient)['DiskSize']),
                         int(DoGet(_REMOTE, '/statistics')['TotalDiskSize']))
        self.assertEqual(int(DoGet(_REMOTE, '/patients/%s/statistics' % patient)['DiskSize']),
                         size + int(DoGet(_REMOTE, '/patients/%s/attachments/1025/compressed-size' % patient)))

        DoPut(_REMOTE, '/patients/%s/attachments/1026' % patient, 'world')
        self.assertEqual(int(DoGet(_REMOTE, '/patients/%s/statistics' % patient)['DiskSize']),
                         int(DoGet(_REMOTE, '/statistics')['TotalDiskSize']))
        self.assertEqual(int(DoGet(_REMOTE, '/patients/%s/statistics' % patient)['DiskSize']),
                         size + 
                         int(DoGet(_REMOTE, '/patients/%s/attachments/1025/compressed-size' % patient)) +
                         int(DoGet(_REMOTE, '/patients/%s/attachments/1026/compressed-size' % patient)))

        self.assertEqual(2, len(DoGet(_REMOTE, '/patients/%s/attachments' % patient)))
        self.assertEqual(hello, DoGet(_REMOTE, '/patients/%s/attachments/1025/data' % patient))
        self.assertEqual('world', DoGet(_REMOTE, '/patients/%s/attachments/1026/data' % patient))
        DoPost(_REMOTE, '/patients/%s/attachments/1025/verify-md5' % patient)
        DoPost(_REMOTE, '/patients/%s/attachments/1026/verify-md5' % patient)
        DoPut(_REMOTE, '/patients/%s/attachments/1026' % patient, 'world2', headers = {
            'If-Match' : '0-%s' % ComputeMD5('world'),
        })

        (headers, body) = DoGetRaw(_REMOTE, '/patients/%s/attachments/1026/data' % patient)
        self.assertEqual('200', headers['status'])
        self.assertEqual('world2', body)

        self.assertRaises(Exception, lambda: DoDelete(_REMOTE, '/instances/%s/attachments/dicom' % instance))
        DoDelete(_REMOTE, '/patients/%s/attachments/1025' % patient, headers = {
            'If-Match' : '0-%s' % ComputeMD5(hello),
        })
        self.assertEqual(int(DoGet(_REMOTE, '/patients/%s/statistics' % patient)['DiskSize']),
                         int(DoGet(_REMOTE, '/statistics')['TotalDiskSize']))
        self.assertEqual(int(DoGet(_REMOTE, '/patients/%s/statistics' % patient)['DiskSize']),
                         size + int(DoGet(_REMOTE, '/patients/%s/attachments/1026/compressed-size' % patient)))

        self.assertEqual(1, len(DoGet(_REMOTE, '/patients/%s/attachments' % patient)))
        
        if IsOrthancVersionAbove(_REMOTE, 1, 9, 2):
            DoDelete(_REMOTE, '/patients/%s/attachments/1026' % patient, headers = {
                'If-Match' : headers['etag']
            })
        else:
            self.assertFalse('etag' in headers)
            DoDelete(_REMOTE, '/patients/%s/attachments/1026' % patient)
            
        self.assertEqual(0, len(DoGet(_REMOTE, '/patients/%s/attachments' % patient)))

        self.assertEqual(int(DoGet(_REMOTE, '/patients/%s/statistics' % patient)['DiskSize']), size)
        self.assertEqual(size, int(DoGet(_REMOTE, '/statistics')['TotalDiskSize']))


    def test_incoming_storescu(self):
        self.assertEqual(0, len(DoGet(_REMOTE, '/patients')))
        subprocess.check_call([ FindExecutable('storescu'),
                                _REMOTE['Server'], str(_REMOTE['DicomPort']),
                                GetDatabasePath('ColorTestImageJ.dcm') ])
        self.assertEqual(1, len(DoGet(_REMOTE, '/patients')))

        i = DoGet(_REMOTE, '/instances')
        self.assertEqual(1, len(i))
        m = DoGet(_REMOTE, '/instances/%s/metadata' % i[0])

        if IsOrthancVersionAbove(_REMOTE, 1, 11, 0):
            self.assertEqual(10, len(m))
        elif IsOrthancVersionAbove(_REMOTE, 1, 9, 1):
            self.assertEqual(9, len(m))
        else:
            self.assertEqual(8, len(m))

        if IsOrthancVersionAbove(_REMOTE, 1, 11, 0):
            self.assertTrue('MainDicomTagsSignature' in m)  # New in Orthanc 1.11.0

        if IsOrthancVersionAbove(_REMOTE, 1, 9, 1):
            self.assertTrue('PixelDataOffset' in m)  # New in Orthanc 1.9.1
            self.assertEqual(2242, DoGet(_REMOTE, '/instances/%s/metadata/PixelDataOffset' % i[0]))

        self.assertTrue('IndexInSeries' in m)
        self.assertTrue('ReceptionDate' in m)
        self.assertTrue('RemoteAET' in m)
        self.assertTrue('Origin' in m)
        self.assertTrue('TransferSyntax' in m)
        self.assertTrue('SopClassUid' in m)
        self.assertTrue('RemoteIP' in m)
        self.assertTrue('CalledAET' in m)
        self.assertEqual(DoGet(_REMOTE, '/instances/%s/metadata/IndexInSeries' % i[0]), 1)
        self.assertEqual(DoGet(_REMOTE, '/instances/%s/metadata/Origin' % i[0]), 'DicomProtocol')
        self.assertEqual(DoGet(_REMOTE, '/instances/%s/metadata/RemoteAET' % i[0]), 'STORESCU')
        self.assertEqual(DoGet(_REMOTE, '/instances/%s/metadata/TransferSyntax' % i[0]), '1.2.840.10008.1.2.1')
        self.assertEqual(DoGet(_REMOTE, '/instances/%s/metadata/SopClassUid' % i[0]), '1.2.840.10008.5.1.4.1.1.7')

        series = DoGet(_REMOTE, '/series')[0]
        m = DoGet(_REMOTE, '/series/%s/metadata' % series)
        if IsOrthancVersionAbove(_REMOTE, 1, 12, 5):
            self.assertEqual(4, len(m))
            self.assertTrue('MainDicomSequences' in m)    # since RequestAttributeSequence is now in the MainDicomTags
        elif IsOrthancVersionAbove(_REMOTE, 1, 11, 0):
            self.assertEqual(3, len(m))
            self.assertTrue('MainDicomTagsSignature' in m)
        else:
            self.assertEqual(2, len(m))
        self.assertTrue('LastUpdate' in m)
        self.assertTrue('RemoteAET' in m)
        self.assertEqual(DoGet(_REMOTE, '/series/%s/metadata/RemoteAET' % series), 'STORESCU')
        self.assertEqual(DoGet(_REMOTE, '/series/%s/metadata/LastUpdate' % series),
                         DoGet(_REMOTE, '/instances/%s/metadata/ReceptionDate' % i[0]))


    def test_incoming_findscu(self):
        UploadInstance(_REMOTE, 'Multiframe.dcm')
        UploadInstance(_REMOTE, 'ColorTestImageJ.dcm')

        i = CallFindScu([ '-k', '0008,0052=PATIENT', '-k', '0010,0010' ])
        patientNames = re.findall('\(0010,0010\).*?\[(.*?)\]', i)
        self.assertEqual(2, len(patientNames))
        self.assertTrue('Test Patient BG ' in patientNames)
        self.assertTrue('Anonymized' in patientNames)

        i = CallFindScu([ '-k', '0008,0052=PATIENT', '-k', '0010,0010=*' ])
        patientNames = re.findall('\(0010,0010\).*?\[(.*?)\]', i)
        self.assertEqual(2, len(patientNames))
        self.assertTrue('Test Patient BG ' in patientNames)
        self.assertTrue('Anonymized' in patientNames)

        i = CallFindScu([ '-k', '0008,0052=SERIES', '-k', '0008,0021' ])
        series = re.findall('\(0008,0021\).*?\[\s*(.*?)\s*\]', i)
        self.assertEqual(2, len(series))
        self.assertTrue('20070208' in series)
        self.assertTrue('19980312' in series)
        
        i = CallFindScu([ '-k', '0008,0052=SERIES', '-k', '0008,0021', '-k', 'Modality=MR\\XA' ])
        series = re.findall('\(0008,0021\).*?\[\s*(.*?)\s*\]', i)
        self.assertEqual(1, len(series))
        self.assertTrue('19980312' in series)
        
        i = CallFindScu([ '-k', '0008,0052=SERIES', '-k', 'PatientName=Anonymized' ])
        series = re.findall('\(0010,0010\).*?\[\s*(.*?)\s*\]', i)
        self.assertEqual(1, len(series))

        # Test the "CaseSentitivePN" flag (false by default)
        i = CallFindScu([ '-k', '0008,0052=SERIES', '-k', 'PatientName=anonymized' ])
        series = re.findall('\(0010,0010\).*?\[\s*(.*?)\s*\]', i)
        self.assertEqual(1, len(series))

        # Test range search (buggy if Orthanc <= 0.9.6)
        i = CallFindScu([ '-k', '0008,0052=STUDY', '-k', 'StudyDate=19980312-' ])
        studies = re.findall('\(0008,0020\).*?\[\s*(.*?)\s*\]', i)
        self.assertEqual(2, len(studies))
        self.assertTrue('20070208' in studies)
        self.assertTrue('19980312' in studies)
        i = CallFindScu([ '-k', '0008,0052=STUDY', '-k', 'StudyDate=19980312-19980312' ])
        studies = re.findall('\(0008,0020\).*?\[\s*(.*?)\s*\]', i)
        self.assertEqual(1, len(studies))
        self.assertTrue('19980312' in studies)
        i = CallFindScu([ '-k', '0008,0052=STUDY', '-k', 'StudyDate=-19980312' ])
        studies = re.findall('\(0008,0020\).*?\[\s*(.*?)\s*\]', i)
        self.assertEqual(1, len(studies))
        self.assertTrue('19980312' in studies)

        # Test that "Retrieve AE Title (0008,0054)" is present, which
        # was *not* the case in Orthanc <= 1.7.2
        i = CallFindScu([ '-k', '0008,0052=INSTANCE' ])
        instances = re.findall('\(0008,0054\).*?\[\s*(.*?)\s*\]', i)
        self.assertEqual(2, len(instances))
        self.assertEqual('ORTHANC', instances[0].strip())
        self.assertEqual('ORTHANC', instances[1].strip())
        

    def test_incoming_findscu_2(self):
        # This test fails if "LookupMode_DatabaseOnly" is used
        # (sequences are not available in this mode, and only main
        # DICOM tags are returned)
        UploadInstance(_REMOTE, 'Multiframe.dcm')
        UploadInstance(_REMOTE, 'ColorTestImageJ.dcm')

        # Test returning sequence values (only since Orthanc 0.9.5)
        i = CallFindScu([ '-k', '0008,0052=SERIES', '-k', '0008,2112' ])  # "ColorTestImageJ" has this sequence tag
        sequences = re.findall('\(0008,2112\)', i)
        self.assertEqual(1, len(sequences))

        # Test returning a non-main DICOM tag,
        # "SecondaryCaptureDeviceID" (0018,1010), whose value is
        # "MEDPC" in "ColorTestImageJ.dcm"
        i = CallFindScu([ '-k', '0008,0052=SERIES', '-k', '0018,1010' ])
        tags = re.findall('\(0018,1010\).*MEDPC', i)
        self.assertEqual(1, len(tags))

        
    def test_incoming_findscu_3(self):
        # This test fails if "LookupMode_DatabaseOnly" or
        # "LookupMode_DiskOnAnswer" is used, as
        # "SecondaryCaptureDeviceID" (0018,1010) is not a main DICOM
        # tag, as thus a constraint cannot be applied to it
        UploadInstance(_REMOTE, 'ColorTestImageJ.dcm')

        i = CallFindScu([ '-k', '0008,0052=SERIES', '-k', '0018,1010=MEDPC' ])
        sequences = re.findall('\(0018,1010\)', i)
        self.assertEqual(1, len(sequences))

        
    def test_incoming_movescu(self):
        UploadInstance(_REMOTE, 'Multiframe.dcm')

        # No matching patient, so no job is created
        self.assertEqual(0, len(DoGet(_LOCAL, '/patients')))
        CallMoveScu([ '--patient', '-k', '0008,0052=PATIENT', '-k', 'PatientID=none' ])        
        self.assertEqual(0, len(DoGet(_LOCAL, '/patients')))

        # 1 Matching patient, track the job
        self.assertTrue(MonitorJob(_REMOTE, lambda: CallMoveScu([
            '--patient',
            '-k', '0008,0052=PATIENT',
            '-k', 'PatientID=12345678'
        ])))
        self.assertEqual(1, len(DoGet(_LOCAL, '/patients')))


    def test_findscu(self):
        i = UploadInstance(_REMOTE, 'DummyCT.dcm')['ID']
        j = UploadInstance(_REMOTE, 'Issue22.dcm')['ID']
        k = UploadInstance(_REMOTE, 'ColorTestImageJ.dcm')['ID']
        DoPost(_REMOTE, '/modalities/orthanctest/store', str(i), 'text/plain')
        
        # Test the "find-patient" level
        p = DoPost(_REMOTE, '/modalities/orthanctest/find-patient', { })
        self.assertEqual(1, len(p))
        self.assertEqual('ozp00SjY2xG', p[0]['PatientID'])
        
        # Test wildcards constraints. The "LO" value representation
        # for PatientID is always case-sensitive, but the "PN" for
        # PatientName might depend on the implementation:
        # "GenerateConfigurationForTests.py" will force it to be case
        # insensitive (which was the default until Orthanc 0.8.6).
        p = DoPost(_REMOTE, '/modalities/orthanctest/find-patient', { 'PatientName' : 'K*' })
        self.assertEqual(1, len(p))
        
        p = DoPost(_REMOTE, '/modalities/orthanctest/find-patient', { 'PatientName' : 'k*' })
        self.assertEqual(1, len(p))
        
        p = DoPost(_REMOTE, '/modalities/orthanctest/find-patient', { 'PatientID' : 'ozp*' })
        self.assertEqual(1, len(p))
        
        p = DoPost(_REMOTE, '/modalities/orthanctest/find-patient', { 'PatientID' : 'o?p*' })
        self.assertEqual(1, len(p))
        
        p = DoPost(_REMOTE, '/modalities/orthanctest/find-patient', { 'PatientID' : '0?q*' })
        self.assertEqual(0, len(p))
        
        p = DoPost(_REMOTE, '/modalities/orthanctest/find-patient', { 'PatientName' : 'B*' })
        self.assertEqual(0, len(p))
        
        p = DoPost(_REMOTE, '/modalities/orthanctest/find-patient', { 'PatientName' : 'b*' })
        self.assertEqual(0, len(p))
        
        DoPost(_REMOTE, '/modalities/orthanctest/store', str(j), 'text/plain')
        DoPost(_REMOTE, '/modalities/orthanctest/store', str(k), 'text/plain')
        DoPost(_REMOTE, '/modalities/orthanctest/find-patient', { })
        self.assertEqual(3, len(DoPost(_REMOTE, '/modalities/orthanctest/find-patient', { })))
        
        p = DoPost(_REMOTE, '/modalities/orthanctest/find-patient', { 'PatientName' : 'A*' })
        self.assertEqual(2, len(p))

        # Test the "find-study" level. This is the instance "ColorTestImageJ.dcm"
        s = DoPost(_REMOTE, '/modalities/orthanctest/find-study', { 'PatientID' : 'B9uTHKOZ' })
        self.assertEqual(1, len(s))
        self.assertEqual('20070208', s[0]['StudyDate'])
        
        # Test range searches
        t = DoPost(_REMOTE, '/modalities/orthanctest/find-study', { 'PatientID' : 'B9uTHKOZ',
                                                                    'StudyDate' : '-20070101' })
        self.assertEqual(0, len(t))
        
        t = DoPost(_REMOTE, '/modalities/orthanctest/find-study', { 'PatientID' : 'B9uTHKOZ',
                                                                    'StudyDate' : '20090101-' })
        self.assertEqual(0, len(t))
        
        t = DoPost(_REMOTE, '/modalities/orthanctest/find-study', { 'PatientID' : 'B9uTHKOZ',
                                                                    'StudyDate' : '20070101-' })
        self.assertEqual(1, len(t))
        
        t = DoPost(_REMOTE, '/modalities/orthanctest/find-study', { 'PatientID' : 'B9uTHKOZ',
                                                                    'StudyDate' : '-20090101' })
        self.assertEqual(1, len(t))
        
        t = DoPost(_REMOTE, '/modalities/orthanctest/find-study', { 'PatientID' : 'B9uTHKOZ',
                                                                    'StudyDate' : '20070207-20070207' })
        self.assertEqual(0, len(t))
        
        t = DoPost(_REMOTE, '/modalities/orthanctest/find-study', { 'PatientID' : 'B9uTHKOZ',
                                                                    'StudyDate' : '20070208-20070208' })
        self.assertEqual(1, len(t))
        
        t = DoPost(_REMOTE, '/modalities/orthanctest/find-study', { 'PatientID' : 'B9uTHKOZ',
                                                                    'StudyDate' : '20070209-20070209' })
        self.assertEqual(0, len(t))
        
        # Test the ModalitiesInStudy tag
        t = DoPost(_REMOTE, '/modalities/orthanctest/find-study', {
            'PatientID' : 'B9uTHKOZ', 
            'ModalitiesInStudy' : 'US' })
        self.assertEqual(0, len(t))

        t = DoPost(_REMOTE, '/modalities/orthanctest/find-study', {
            'PatientID' : 'B9uTHKOZ', 
            'ModalitiesInStudy' : 'CT' })
        self.assertEqual(1, len(t))

        t = DoPost(_REMOTE, '/modalities/orthanctest/find-study', {
            'PatientID' : 'B9uTHKOZ', 
            'ModalitiesInStudy' : 'US\\CT' })
        self.assertEqual(1, len(t))

        t = DoPost(_REMOTE, '/modalities/orthanctest/find-study', {
            'PatientID' : 'B9uTHKOZ', 
            'ModalitiesInStudy' : '' })
        self.assertEqual(1, len(t))

        # Test the "find-series" level
        t = DoPost(_REMOTE, '/modalities/orthanctest/find-series', {
            'PatientID' : 'B9uTHKOZ', 
            'StudyInstanceUID' : s[0]['StudyInstanceUID'] })
        self.assertEqual(1, len(t))

        # Test "\" separator
        t = DoPost(_REMOTE, '/modalities/orthanctest/find-series', {
            'PatientID' : 'B9uTHKOZ', 
            'StudyInstanceUID' : s[0]['StudyInstanceUID'],
            'Modality' : 'MR\\CT\\US' })
        self.assertEqual(1, len(t))

        t = DoPost(_REMOTE, '/modalities/orthanctest/find-series', {
            'PatientID' : 'B9uTHKOZ', 
            'StudyInstanceUID' : s[0]['StudyInstanceUID'],
            'Modality' : 'MR\\US' })
        self.assertEqual(0, len(t))


    def test_update_modalities(self):
        self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/modalities/toto'))
        self.assertRaises(Exception, lambda: DoDelete(_REMOTE, '/modalities/toto'))
        DoPut(_REMOTE, '/modalities/toto', [ "STORESCP", "localhost", 2000 ])
        DoPut(_REMOTE, '/modalities/tata', [ "STORESCP", "localhost", 2000, 'MedInria' ]) # check backward compatiblity with obsolete manufacturer
        DoDelete(_REMOTE, '/modalities/tata')
        DoPut(_REMOTE, '/modalities/tata', [ "STORESCP", "localhost", 2000, 'GenericNoUniversalWildcard' ])
        DoDelete(_REMOTE, '/modalities/tata')
        DoPut(_REMOTE, '/modalities/tata', [ "STORESCP", "localhost", 2000, 'GenericNoWildcardInDates' ])
        modalitiesReadback = DoGet(_REMOTE, '/modalities?expand')
        self.assertEqual('STORESCP', modalitiesReadback['tata']['AET'])
        self.assertEqual('localhost', modalitiesReadback['tata']['Host'])
        self.assertEqual(2000, modalitiesReadback['tata']['Port'])
        self.assertEqual('GenericNoWildcardInDates', modalitiesReadback['tata']['Manufacturer'])
        self.assertRaises(Exception, lambda: DoPut(_REMOTE, '/modalities/toto', [ "STORESCP", "localhost", 2000, 'InvalidManufacturerName' ]))
        self.assertTrue('store' in DoGet(_REMOTE, '/modalities/toto'))
        self.assertTrue('store' in DoGet(_REMOTE, '/modalities/tata'))

        # New in Orthanc 1.8.1
        self.assertTrue('configuration' in DoGet(_REMOTE, '/modalities/tata'))
        self.assertEqual(modalitiesReadback['tata'], DoGet(_REMOTE, '/modalities/tata/configuration'))
        
        DoDelete(_REMOTE, '/modalities/toto')
        DoDelete(_REMOTE, '/modalities/tata')
        self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/modalities/toto'))
        self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/modalities/tata'))

        if IsOrthancVersionAbove(_REMOTE, 1, 12, 2):
            self.assertEqual(DoGet(_REMOTE, '/modalities?expand'), DoGet(_REMOTE, '/modalities?expand=true'))
            self.assertEqual(DoGet(_REMOTE, '/modalities'), DoGet(_REMOTE, '/modalities?expand=false'))



    def test_update_peers(self):
        # curl -X PUT http://localhost:8042/peers/toto -d '["http://localhost:8042/"]' -v
        self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/peers/toto'))
        self.assertRaises(Exception, lambda: DoDelete(_REMOTE, '/peers/toto'))
        DoPut(_REMOTE, '/peers/toto', [ 'http://localhost:8042/' ])
        DoPut(_REMOTE, '/peers/tata', { 'Url': 'http://localhost:8042/',
                                        'Username': 'user',
                                        'Password' : 'pass',
                                        'RemoteSelf' : 'self' })
        self.assertTrue('tata' in DoGet(_REMOTE, '/peers'))
        peersReadback = DoGet(_REMOTE, '/peers?expand')
        self.assertEqual('http://localhost:8042/', peersReadback['tata']['Url'])
        self.assertEqual('user', peersReadback['tata']['Username'])

        if IsOrthancVersionAbove(_REMOTE, 1, 5, 4):
            self.assertEqual(None, peersReadback['tata']['Password']) # make sure no sensitive data is included
            self.assertFalse(peersReadback['tata']['Pkcs11']) # make sure no sensitive data is included
            self.assertEqual('self', peersReadback['tata']['RemoteSelf'])
        else:
            self.assertFalse('Password' in peersReadback['tata']) # make sure no sensitive data is included
            self.assertFalse('Pkcs11' in peersReadback['tata']) # make sure no sensitive data is included
            self.assertFalse('RemoteSelf' in peersReadback['tata'])

        self.assertFalse('CertificateFile' in peersReadback['tata']) # make sure no sensitive data is included
        self.assertFalse('CertificateKeyFile' in peersReadback['tata']) # make sure no sensitive data is included
        self.assertFalse('CertificateKeyPassword' in peersReadback['tata']) # make sure no sensitive data is included

        self.assertRaises(Exception, lambda: DoPut(_REMOTE, '/peers/toto', [ 'http://localhost:8042/', 'a' ]))
        self.assertRaises(Exception, lambda: DoPut(_REMOTE, '/peers/toto', [ 'http://localhost:8042/', 'a', 'b', 'c' ]))
        self.assertTrue('store' in DoGet(_REMOTE, '/peers/toto'))
        self.assertTrue('store' in DoGet(_REMOTE, '/peers/tata'))

        # New in Orthanc 1.8.1
        self.assertTrue('configuration' in DoGet(_REMOTE, '/peers/tata'))
        self.assertEqual(peersReadback['tata'], DoGet(_REMOTE, '/peers/tata/configuration'))

        DoDelete(_REMOTE, '/peers/toto')
        DoDelete(_REMOTE, '/peers/tata')
        self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/peers/toto'))
        self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/peers/tata'))

        if IsOrthancVersionAbove(_REMOTE, 1, 12, 2):
            self.assertEqual(DoGet(_REMOTE, '/peers?expand'), DoGet(_REMOTE, '/peers?expand=true'))
            self.assertEqual(DoGet(_REMOTE, '/peers'), DoGet(_REMOTE, '/peers?expand=false'))



    def test_mesterhazy_modification(self):
        # When I modify a series ( eg. curl
        # http://localhost:8042/series/uidhere/modify -X POST -d
        # '{"Replace":{"SeriesDate":"19990101"}}' ) the modified
        # series is added to a new Study, instead of the existing
        # Study. Fixed in Orthanc 0.7.5

        u = UploadInstance(_REMOTE, 'DummyCT.dcm')
        study = 'b9c08539-26f93bde-c81ab0d7-bffaf2cb-a4d0bdd0'
        series = 'f2635388-f01d497a-15f7c06b-ad7dba06-c4c599fe'

        modified = DoPost(_REMOTE, '/series/%s/modify' % series,
                          json.dumps({ "Replace" : { "SeriesDate" : "19990101" }}))

        self.assertEqual(study, DoGet(_REMOTE, '/series/%s' % modified['ID']) ['ParentStudy'])


    def test_create(self):
        payload = {
            'PatientName' : 'Jodogne',
            'Modality' : 'CT',
            'SOPClassUID' : '1.2.840.10008.5.1.4.1.1.1',
            'PixelData' : 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg==' # red dot in RGBA
            }

        if IsOrthancVersionAbove(_REMOTE, 1, 12, 5):
            payload['TimeRange'] = '3.12\\4.12'                      # https://discourse.orthanc-server.org/t/multiplicity-on-dicom-tags/5144

        i = DoPost(_REMOTE, '/tools/create-dicom',
                   json.dumps(payload))

        self.assertEqual('Jodogne', DoGet(_REMOTE, '/instances/%s/content/PatientName' % i['ID']).strip())
        self.assertEqual('CT', DoGet(_REMOTE, '/instances/%s/content/Modality' % i['ID']).strip())
        tags = DoGet(_REMOTE, '/instances/%s/tags?simplify' % i['ID'])
        if IsOrthancVersionAbove(_REMOTE, 1, 12, 5):
            self.assertIn("3.12", tags["TimeRange"])
            self.assertIn("4.12", tags["TimeRange"])
            self.assertIn("\\", tags["TimeRange"])

        png = GetImage(_REMOTE, '/instances/%s/preview' % i['ID'])
        self.assertEqual((5, 5), png.size)

        j = DoGet(_REMOTE, i['Path'])
        self.assertEqual('Instance', j['Type'])
        self.assertEqual(j['ID'], i['ID'])


    def test_pilates(self):
        # "SCU failed error when accessing orthanc with osirix" by
        # Pilates Agentur (Mar 10, 2014 at 9:33 PM)
        i = UploadInstance(_REMOTE, 'PilatesArgenturGEUltrasoundOsiriX.dcm')['ID']
        self.assertEqual(0, len(DoGet(_LOCAL, '/patients')))
        j = DoPost(_REMOTE, '/modalities/orthanctest/store', str(i), 'text/plain')
        self.assertEqual(1, len(DoGet(_LOCAL, '/patients')))


    def test_shared_tags(self):
        a = UploadInstance(_REMOTE, 'Knee/T1/IM-0001-0001.dcm')['ID']
        b = UploadInstance(_REMOTE, 'Knee/T1/IM-0001-0002.dcm')['ID']
        p = DoGet(_REMOTE, '/patients')[0]
        
        self.assertTrue('0010,0010' in DoGet(_REMOTE, '/patients/%s/shared-tags' % p))
        self.assertTrue('PatientName' in DoGet(_REMOTE, '/patients/%s/shared-tags?simplify' % p))
        self.assertTrue('0010,0010' in DoGet(_REMOTE, '/patients/%s/shared-tags?short' % p))

        self.assertEqual('KNEE', DoGet(_REMOTE, '/patients/%s/shared-tags' % p)['0010,0010']['Value'])
        self.assertEqual('KNEE', DoGet(_REMOTE, '/patients/%s/shared-tags?simplify' % p)['PatientName'])
        self.assertEqual('KNEE', DoGet(_REMOTE, '/patients/%s/shared-tags?short' % p)['0010,0010'])
        
        self.assertTrue('0008,1030' in DoGet(_REMOTE, '/patients/%s/shared-tags' % p))
        self.assertTrue('StudyDescription' in DoGet(_REMOTE, '/patients/%s/shared-tags?simplify' % p))
        self.assertTrue('0008,103e' in DoGet(_REMOTE, '/patients/%s/shared-tags' % p))
        self.assertTrue('SeriesDescription' in DoGet(_REMOTE, '/patients/%s/shared-tags?simplify' % p))
        self.assertFalse('0008,0018' in DoGet(_REMOTE, '/patients/%s/shared-tags' % p))
        self.assertFalse('SOPInstanceUID' in DoGet(_REMOTE, '/patients/%s/shared-tags?simplify' % p))

        self.assertTrue('0008,0018' in DoGet(_REMOTE, '/instances/%s/tags' % a))
        self.assertTrue('SOPInstanceUID' in DoGet(_REMOTE, '/instances/%s/tags?simplify' % a))


    def test_modules(self):
        a = UploadInstance(_REMOTE, 'Knee/T1/IM-0001-0001.dcm')['ID']
        p = DoGet(_REMOTE, '/patients')[0]
        s = DoGet(_REMOTE, '/studies')[0]
        t = DoGet(_REMOTE, '/series')[0]
        
        self.assertTrue('0010,0010' in DoGet(_REMOTE, '/patients/%s/module' % p))
        self.assertTrue('PatientName' in DoGet(_REMOTE, '/patients/%s/module?simplify' % p))
        self.assertTrue('0010,0010' in DoGet(_REMOTE, '/studies/%s/module-patient' % s))
        self.assertTrue('PatientName' in DoGet(_REMOTE, '/studies/%s/module-patient?simplify' % s))
        self.assertTrue('0008,1030' in DoGet(_REMOTE, '/studies/%s/module' % s))
        self.assertTrue('StudyDescription' in DoGet(_REMOTE, '/studies/%s/module?simplify' % s))
        self.assertTrue('0008,103e' in DoGet(_REMOTE, '/series/%s/module' % t))
        self.assertTrue('SeriesDescription' in DoGet(_REMOTE, '/series/%s/module?simplify' % t))
        self.assertTrue('0008,0018' in DoGet(_REMOTE, '/instances/%s/module' % a))
        self.assertTrue('SOPInstanceUID' in DoGet(_REMOTE, '/instances/%s/module?simplify' % a))


    def test_auto_directory(self):
        a = UploadInstance(_REMOTE, 'Knee/T1/IM-0001-0001.dcm')['ID']
        self.assertTrue('now' in DoGet(_REMOTE, '/tools'))
        self.assertTrue('dicom-conformance' in DoGet(_REMOTE, '/tools'))
        self.assertTrue('invalidate-tags' in DoGet(_REMOTE, '/tools'))
        self.assertTrue(len(DoGet(_REMOTE, '/tools/dicom-conformance')) > 1000)
        self.assertTrue('orthanctest' in DoGet(_REMOTE, '/modalities'))
        self.assertTrue('echo' in DoGet(_REMOTE, '/modalities/orthanctest'))
        self.assertTrue('find' in DoGet(_REMOTE, '/modalities/orthanctest'))
        self.assertTrue('find-instance' in DoGet(_REMOTE, '/modalities/orthanctest'))
        self.assertTrue('find-patient' in DoGet(_REMOTE, '/modalities/orthanctest'))
        self.assertTrue('find-series' in DoGet(_REMOTE, '/modalities/orthanctest'))
        self.assertTrue('find-study' in DoGet(_REMOTE, '/modalities/orthanctest'))
        self.assertTrue('store' in DoGet(_REMOTE, '/modalities/orthanctest'))
        self.assertTrue('store' in DoGet(_REMOTE, '/peers/peer'))
        self.assertTrue('matlab' in DoGet(_REMOTE, '/instances/%s/frames/0' % a))
        self.assertTrue('raw' in DoGet(_REMOTE, '/instances/%s/frames/0' % a))
        self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/tools/nope'))
        self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/nope'))
        self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/nope/nope.html'))
        self.assertEqual(404, DoGetRaw(_REMOTE, '/nope')[0].status)
        self.assertEqual(404, DoGetRaw(_REMOTE, '/nope/nope.html')[0].status)


    def test_echo(self):
        DoPost(_REMOTE, '/modalities/orthanctest/echo')
        DoPost(_REMOTE, '/modalities/orthanctest/echo', '{}')

        # The following was not working in Orthanc 1.7.0 -> 1.8.1
        DoPost(_REMOTE, '/modalities/orthanctest/echo', '')
        self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/modalities/nope/echo'))

        # New in Orthanc 1.8.1
        DoPost(_REMOTE, '/tools/dicom-echo', [
            _REMOTE['DicomAet'], _REMOTE['Server'], _REMOTE['DicomPort'] ])
        DoPost(_REMOTE, '/tools/dicom-echo', DoGet(_REMOTE, '/modalities/orthanctest/configuration'))

        # Use the 'CheckFind' new option in Orthanc 1.8.1
        DoPost(_REMOTE, '/modalities/self/echo', { 'CheckFind' : True })
        DoPost(_REMOTE, '/tools/dicom-echo', {
            'AET' : _REMOTE['DicomAet'],
            'Host' : _REMOTE['Server'],
            'Port' : _REMOTE['DicomPort'],
            'CheckFind' : True
            })
        

    def test_xml(self):
        json = DoGet(_REMOTE, '/tools', headers = { 'accept' : 'application/json' })
        xml = minidom.parseString(DoGet(_REMOTE, '/tools', headers = { 'accept' : 'application/xml' }))
        items = xml.getElementsByTagName('root')[0].getElementsByTagName('item') 
        self.assertEqual(len(items), len(json))

        self.assertTrue('dicom-conformance' in json)

        ok = False
        for i in items:
            if i.childNodes[0].data == 'dicom-conformance':
                ok = True
        self.assertTrue(ok)


    def test_googlecode_issue_16(self):
        i = UploadInstance(_REMOTE, 'Issue16.dcm')['ID']
        t = DoGet(_REMOTE, '/instances/%s/tags?simplify' % i)['FrameIncrementPointer']
        self.assertEqual('0018,1063', t)


    def test_googlecode_issue_22(self):
        s = UploadInstance(_REMOTE, 'Issue22.dcm')['ID']
        a = [
            "f804691f62197040438f4627c6b994f1",  # Frame 0
            "c69eee9a51eea3e8611e82e578897254",
            "315666be83e2d0111c77bc0996d84901",
            "3e27aa959d911172c48a1436443c72b1",
            "958642c9e7e9d232d3869faff546058c",
            "5e7ea8e3e4230cae707d143481355c59",
            "eda37f83558d858a596175aed8b2ad47",
            "486713bd2895c4ecbe0e97715ac7f80a",
            "091ef729eb169e67da8a0faa9631f9a8",
            "5aa2b8c7ffe0a483efaa8e12417686ca",
            "e2f39e85896fe58876654b94cd0b5013",
            "6fd2129e4950abbe1be053bc814d5da8",
            "c3331a8ba7a757f3d423735ab7fa81f9",
            "746f808582156734dd6b6fdfd3a0b72c",
            "8075ea2b227a70c60ea6b7b75a6bb190",
            "806b8b3e300c615099c11a5ec23465aa",
            "7c836aa298ba6eef96434579af631a11",
            "a0357dc9f4f72d73a885c33d7c287446",
            "f25ba3be1cc7d7fad95706adc199ea7d",
            "8b114c526b8cbed6cad8a3248b7b480c",
            "44e6670f127e612a2b4aa60a0d207698",
            "b8945f90fe02facf2ace24ca1ecbe0a5",
            "95c796c2fa8f59018b15cf2987b1f79b",
            "ce0a51ab30224205b44920221dc27351",  # Frame 23
            ]

        self.assertEqual(24, len(DoGet(_REMOTE, '/instances/%s/frames' % s)))
        self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/instances/%s/frames/24/preview' % s))

        for i in range(len(a)):
            self.assertEqual(a[i], ComputeMD5(DoGet(_REMOTE, '/instances/%s/frames/%d/preview' % (s, i))))


    def test_googlecode_issue_19(self):
        # This is an image with "YBR_FULL" photometric interpretation, it is not supported by Orthanc
        # gdcmconv -i /home/jodogne/DICOM/GdcmDatabase/US_DataSet/HDI5000_US/3EAF5E01 -w -o Issue19.dcm

        a = UploadInstance(_REMOTE, 'Issue19.dcm')['ID']
        if not HasGdcmPlugin(_REMOTE):
            self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/instances/941ad3c8-05d05b88-560459f9-0eae0e20-6cddd533/preview'))


    def test_googlecode_issue_37(self):
        # Same test for issues 35 and 37. Fixed in Orthanc 0.9.1
        u = UploadInstance(_REMOTE, 'Beaufix/IM-0001-0001.dcm')['ID']

        a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Series',
                                             'CaseSensitive' : True,
                                             'Query' : { 'StationName' : 'SMR4-MP3' }})
        self.assertEqual(1, len(a))

        if IsOrthancVersionAbove(_REMOTE, 1, 12, 5):
            a = DoPost(_REMOTE, '/tools/count-resources', { 'Level' : 'Series',
                                                            'CaseSensitive' : False,
                                                            'Query' : { 'StationName' : 'SMR4-MP3' }})
            self.assertEqual(1, len(a))
            self.assertEqual(1, a['Count'])


    def test_rest_find(self):
        def CheckFind(query, expectedAnswers, shouldThrow = False):
            
            if not shouldThrow:
                a = DoPost(_REMOTE, '/tools/find', query)
                self.assertEqual(expectedAnswers, len(a))
                return a
            else:
                self.assertRaises(Exception, lambda: DoPost(_REMOTE, '/tools/find', query))

            

        def CheckCount(query, expectedAnswers, shouldThrow = False):
            if not shouldThrow:
                b = DoPost(_REMOTE, '/tools/count-resources', query)
                self.assertEqual(1, len(b))
                self.assertEqual(expectedAnswers, b['Count'])
                return b
            else:
                self.assertRaises(Exception, lambda: DoPost(_REMOTE, '/tools/count-resources', query))

            


        # Upload 12 instances
        for i in range(3):
            UploadInstance(_REMOTE, 'Brainix/Flair/IM-0001-000%d.dcm' % (i + 1))
            UploadInstance(_REMOTE, 'Brainix/Epi/IM-0001-000%d.dcm' % (i + 1))
            UploadInstance(_REMOTE, 'Knee/T1/IM-0001-000%d.dcm' % (i + 1))
            UploadInstance(_REMOTE, 'Knee/T2/IM-0001-000%d.dcm' % (i + 1))


        query = { 'Level' : 'Study',
                  'CaseSensitive' : True,
                  'Query' : {
                      'PatientName' : '*NE*',
                      'StudyDate': '20080819'
                  }}
        CheckFind(query, 1)
        CheckCount(query, 1, True) # tools/count does not support CaseSensitive

        query = { 'Level' : 'Study',
                  'CaseSensitive' : False,
                  'Query' : {
                      'PatientName' : '*NE*',
                      'StudyDate': '20080819'
                  }}
        CheckFind(query, 1)
        CheckCount(query, 1)

        query = { 'Level' : 'Study',
                  'CaseSensitive' : False,
                  'Query' : {
                      'PatientName' : '*NE*',
                      'StudyDate': '20080819'
                  },
                  'Since' : 1
                  }
        if HasExtendedFind(_REMOTE): # usage of 'Since' is not reliable without ExtendedFind
            CheckFind(query, 0)
            CheckCount(query, 1) # Since is ignored in tools/count-resources

        query = { 'Level' : 'Study',
                  'CaseSensitive' : True,
                  'Query' : {
                      'PatientName' : '*NE*',
                      'PatientBirthDate': '20080101-20081231',
                      'PatientSex': '0000'
                  }}
        CheckFind(query, 1)
        CheckCount(query, 1, True) # tools/count-resources does not support CaseSensitive

        query = { 'Level' : 'Study',
                  'CaseSensitive' : True,
                  'Query' : {
                      'PatientName' : '*NE*',
                      'PatientBirthDate': '20080101-20081231',
                      'PatientSex': '0000'
                  },
                  'Since': 1}
        if HasExtendedFind(_REMOTE): # usage of 'Since' is not reliable without ExtendedFind
            CheckFind(query, 0, True)  # 'CaseSensitive' can not be combined with 'Since'
            CheckCount(query, 0, True) # tools/count-resources does not support CaseSensitive

        query = { 'Level' : 'Study',
                  'CaseSensitive' : True,
                  'Query' : {
                      'PatientName' : '*ne*',
                      'PatientBirthDate': '20080101-20081231',
                      'PatientSex': '0000'
                  }
                }
        CheckFind(query, 0)

        query = { 'Level' : 'Study',
                  'CaseSensitive' : True,
                  'Query' : {
                      'PatientName' : '*ne*',
                      'PatientBirthDate': '20080101-20081231',
                      'PatientSex': '0000'
                  },
                  'Since': 1}
        CheckFind(query, 0, True)  # 'CaseSensitive' can not be combined with 'Since' when searching for lower case (because the DicomIdentifiers are stored in UPPERCASE)

        query = { 'Level' : 'Series',
                  'CaseSensitive' : True,
                  'Query' : {
                      'StudyInstanceUID' : '2.16.840.1.113669.632.20.121711.10000160881'
                  }}
        CheckFind(query, 2)
        CheckCount(query, 2, True) # tools/count-resources does not support CaseSensitive

        query = { 'Level' : 'Instance',
                  'CaseSensitive' : True,
                  'Query' : {
                      'StudyInstanceUID' : '2.16.840.1.113669.632.20.121711.10000160881',
                      'SeriesInstanceUID': '1.3.46.670589.11.17521.5.0.3124.2008081908564160709'
                  }}
        CheckFind(query, 3)
        CheckCount(query, 3, True) # tools/count-resources does not support CaseSensitive

        query = { 'Level' : 'Series',
                  'CaseSensitive' : True,
                  'Query' : {
                      'StudyDate' : '20080818-20080820',
                      'Modality': 'MR'
                  }}
        CheckFind(query, 2)
        CheckCount(query, 2, True) # tools/count-resources does not support CaseSensitive

        query = { 'Level' : 'Study',
                  'CaseSensitive' : True,
                  'Query' : {
                      'StudyDate' : '20080818-',
                      'ModalitiesInStudy': 'MR'
                  }}
        CheckFind(query, 1)

        query = { 'Level' : 'Study',
                  'CaseSensitive' : False,
                  'Query' : {
                      'StudyDate' : '20080818-',
                      'ModalitiesInStudy': 'MR'
                  }, 
                  'Since': 1}

        if HasExtendedFind(_REMOTE): # usage of 'Since' is not reliable without ExtendedFind
            CheckFind(query, 0)
            CheckCount(query, 1) # Since is ignored in tools/count-resources

        query = { 'Level' : 'Patient',
                  'CaseSensitive' : False,
                  'Query' : { 'PatientName' : 'BRAINIX' }}
        CheckFind(query, 1)
        CheckCount(query, 1)

        query = { 'Level' : 'Patient',
                  'CaseSensitive' : False,
                  'Query' : { 'PatientName' : 'BRAINIX\\KNEE\\NOPE' }}
        CheckFind(query, 2)
        CheckCount(query, 2)

        query = { 'Level' : 'Patient',
                  'CaseSensitive' : False,
                  'Query' : { 'PatientName' : '*n*' }}
        CheckFind(query, 2)
        CheckCount(query, 2)

        query = { 'Level' : 'Patient',
                  'CaseSensitive' : True,
                  'Query' : { 'PatientName' : '*n*' }}
        CheckFind(query, 0)
        CheckCount(query, 0, True)   # "CaseSensitive" is not available in "/tools/count-resources"

        query = { 'Expand' : True,
                  'Level' : 'Patient',
                  'CaseSensitive' : False,
                  'Query' : { 'PatientName' : '*ne*' }}
        a = CheckFind(query, 1)
        self.assertEqual('20080822', a[0]['MainDicomTags']['PatientBirthDate'])

        query = { 'Level' : 'Patient',
                  'CaseSensitive' : True,
                  'Query' : { 'PatientName' : '*ne*' }}
        CheckFind(query, 0)

        query = { 'Level' : 'Study',
                  'CaseSensitive' : True,
                  'Query' : { 'PatientName' : '*NE*' }}
        CheckFind(query, 1)

        query = { 'Level' : 'Series',
                  'CaseSensitive' : True,
                  'Query' : { 'PatientName' : '*NE*' }}
        CheckFind(query, 2)

        query = { 'Level' : 'Instance',
                  'CaseSensitive' : True,
                  'Query' : { 'PatientName' : '*NE*' }}
        CheckFind(query, 6)

        query = { 'Level' : 'Patient', 'Query' : { }}
        CheckFind(query, 2)

        query = { 'Level' : 'Study', 'Query' : { }}
        CheckFind(query, 2)

        query = { 'Level' : 'Series', 'Query' : { }}
        CheckFind(query, 4)

        query = { 'Level' : 'Instance', 'Query' : { }}
        CheckFind(query, 12)

        query = { 'Level' : 'Study',
                  'Expand' : True,
                  'Query' : { 'StudyDate' : '20061201-20061201' }}
        a = CheckFind(query, 1)
        self.assertEqual('BRAINIX', a[0]['PatientMainDicomTags']['PatientName'])

        query = { 'Level' : 'Study',
                  'Expand' : True,
                  'Query' : { 'StudyDate' : '20061201-20091201' }}
        a = CheckFind(query, 2)
        for i in range(2):
            self.assertTrue(a[i]['PatientMainDicomTags']['PatientName'] in ['BRAINIX', 'KNEE'])

        query = { 'Level' : 'Study',
                  'Query' : { 'StudyDate' : '20061202-20061202' }}
        CheckFind(query, 0)

        query = { 'Level' : 'Study',
                  'Expand' : True,
                  'Query' : { 'StudyDate' : '-20061201' }}
        a = CheckFind(query, 1)
        self.assertEqual('BRAINIX', a[0]['PatientMainDicomTags']['PatientName'])

        query = { 'Level' : 'Study',
                  'Expand' : True,
                  'Query' : { 'StudyDate' : '-20051201' }}
        CheckFind(query, 0)

        query = { 'Level' : 'Study',
                  'Expand' : True,
                  'Query' : { 'StudyDate' : '20061201-' }}
        a = CheckFind(query, 2)
        for i in range(2):
            self.assertTrue(a[i]['PatientMainDicomTags']['PatientName'] in ['BRAINIX', 'KNEE'])

        query = { 'Level' : 'Study',
                  'Expand' : True,
                  'Query' : { 'StudyDate' : '20061202-' }}
        a = CheckFind(query, 1)
        self.assertEqual('KNEE', a[0]['PatientMainDicomTags']['PatientName'])

        query = { 'Level' : 'Study',
                  'Expand' : True,
                  'Query' : { 'StudyDate' : '20080819-' }}
        a = CheckFind(query, 1)
        self.assertEqual('KNEE', a[0]['PatientMainDicomTags']['PatientName'])

        query = { 'Level' : 'Study',
                  'Expand' : True,
                  'Query' : { 'StudyDate' : '20080820-' }}
        CheckFind(query, 0)

        query = { 'Level' : 'Series',
                  'Expand' : True,
                  'Query' : { 'PatientPosition' : 'HFS' }}
        CheckFind(query, 2, False)   # "PatientPosition" is not a main DICOM tag, so unavailable in "/tools/count-resources"

        query = { 'Level' : 'Series',
                  'Expand' : False,
                  'Query' : { 'PatientPosition' : 'HFS' }}
        CheckFind(query, 2, False)   # "PatientPosition" is not a main DICOM tag, so unavailable in "/tools/count-resources"
        

    def test_rest_query_retrieve(self):
        self.assertEqual(0, len(DoGet(_REMOTE, '/patients')))

        # Upload 8 instances
        for i in range(2):
            UploadInstance(_REMOTE, 'Brainix/Flair/IM-0001-000%d.dcm' % (i + 1))
            UploadInstance(_REMOTE, 'Brainix/Epi/IM-0001-000%d.dcm' % (i + 1))
            UploadInstance(_REMOTE, 'Knee/T1/IM-0001-000%d.dcm' % (i + 1))
            UploadInstance(_REMOTE, 'Knee/T2/IM-0001-000%d.dcm' % (i + 1))

        self.assertEqual(2, len(DoGet(_REMOTE, '/patients')))
        for p in DoGet(_REMOTE, '/patients'):
            DoPost(_REMOTE, '/modalities/orthanctest/store', p)
            DoDelete(_REMOTE, '/patients/%s' % p)

        for q in DoGet(_REMOTE, '/queries'):
            DoDelete(_REMOTE, '/queries/%s' % q)

        self.assertEqual(0, len(DoGet(_REMOTE, '/patients')))
        self.assertEqual(0, len(DoGet(_REMOTE, '/queries')))

        if not IsOrthancVersionAbove(_LOCAL, 1, 11, 2):  # TODO: check why this works with 0.8.6 and not with more recent versions
            a = DoPost(_REMOTE, '/modalities/orthanctest/query', { 'Level' : 'Series',
                                                                'Query' : { 
                                                                    'PatientName' : '*NE*',
                                                                    'StudyDate' : '*',
                                                                }})['ID']
            self.assertEqual(1, len(DoGet(_REMOTE, '/queries')))

            b = DoGet(_REMOTE, '/queries/%s' % a)
            self.assertTrue('answers' in b)
            self.assertTrue('level' in b)
            self.assertTrue('modality' in b)
            self.assertTrue('query' in b)
            self.assertTrue('retrieve' in b)
            self.assertEqual('Series', DoGet(_REMOTE, '/queries/%s/level' % a))
            self.assertEqual('orthanctest', DoGet(_REMOTE, '/queries/%s/modality' % a))
            
            q = DoGet(_REMOTE, '/queries/%s/query?simplify' % a)
            self.assertEqual(2, len(q))
            self.assertTrue('PatientName' in q)
            self.assertTrue('StudyDate' in q)
            self.assertEqual('*NE*', q['PatientName'])
            self.assertEqual('*', q['StudyDate'])

            self.assertEqual(2, len(DoGet(_REMOTE, '/queries/%s/answers' % a)))

            s = DoGet(_REMOTE, '/queries/%s/answers/0' % a)
            self.assertTrue('content' in s)
            self.assertTrue('retrieve' in s)

            s = DoGet(_REMOTE, '/queries/%s/answers/0/content?simplify' % a)
            self.assertEqual('887', s['PatientID'])
            self.assertEqual('2.16.840.1.113669.632.20.121711.10000160881', s['StudyInstanceUID'])

            self.assertEqual(0, len(DoGet(_REMOTE, '/patients')))
            DoPost(_REMOTE, '/queries/%s/answers/0/retrieve' % a, 'ORTHANC')
            self.assertEqual(1, len(DoGet(_REMOTE, '/patients')))
            self.assertEqual(1, len(DoGet(_REMOTE, '/studies')))
            self.assertEqual(1, len(DoGet(_REMOTE, '/series')))
            self.assertEqual(2, len(DoGet(_REMOTE, '/instances')))

            DoPost(_REMOTE, '/queries/%s/answers/1/retrieve' % a, 'ORTHANC', 'application/json') # make sure the issue #36 is fixed (query/retrieve Rest API: /retrieve route shall accept application/json content type)
            self.assertEqual(1, len(DoGet(_REMOTE, '/patients')))
            self.assertEqual(1, len(DoGet(_REMOTE, '/studies')))
            self.assertEqual(2, len(DoGet(_REMOTE, '/series')))
            self.assertEqual(4, len(DoGet(_REMOTE, '/instances')))

            # New in Orthanc 1.4.3
            s = DoGet(_REMOTE, '/queries/%s/answers?expand&simplify' % a)
            self.assertEqual(2, len(s))
            for i in range(2):
                self.assertEqual('SERIES', s[i]['QueryRetrieveLevel'])
                self.assertEqual('887', s[i]['PatientID'])
                self.assertEqual('2.16.840.1.113669.632.20.121711.10000160881', s[i]['StudyInstanceUID'])
            
            DoDelete(_REMOTE, '/queries/%s' % a)
            self.assertEqual(0, len(DoGet(_REMOTE, '/queries')))


    def test_parent(self):
        u = UploadInstance(_REMOTE, 'DummyCT.dcm')['ID']
        patient = '6816cb19-844d5aee-85245eba-28e841e6-2414fae2'
        study = 'b9c08539-26f93bde-c81ab0d7-bffaf2cb-a4d0bdd0'
        series = 'f2635388-f01d497a-15f7c06b-ad7dba06-c4c599fe'
        instance = '66a662ce-7430e543-bad44d47-0dc5a943-ec7a538d'
        self.assertEqual(instance, u)

        a = DoGet(_REMOTE, '/studies/%s/patient' % study)
        self.assertEqual('Patient', a['Type'])
        self.assertEqual(patient, a['ID'])
        
        a = DoGet(_REMOTE, '/series/%s/patient' % series)
        self.assertEqual('Patient', a['Type'])
        self.assertEqual(patient, a['ID'])
        
        a = DoGet(_REMOTE, '/series/%s/study' % series)
        self.assertEqual('Study', a['Type'])
        self.assertEqual(study, a['ID'])
        
        a = DoGet(_REMOTE, '/instances/%s/patient' % instance)
        self.assertEqual('Patient', a['Type'])
        self.assertEqual(patient, a['ID'])
        
        a = DoGet(_REMOTE, '/instances/%s/study' % instance)
        self.assertEqual('Study', a['Type'])
        self.assertEqual(study, a['ID'])
        
        a = DoGet(_REMOTE, '/instances/%s/series' % instance)
        self.assertEqual('Series', a['Type'])
        self.assertEqual(series, a['ID'])
        

    def test_shanon(self):
        def Anonymize(instance, replacements = {}):
            return DoPost(_REMOTE, '/instances/%s/anonymize' % instance, {
                'Replace' : replacements,
                'Force' : True,
            }, 'application/json')

        self.assertEqual(0, len(DoGet(_REMOTE, '/instances')))
        u = UploadInstance(_REMOTE, 'DummyCT.dcm')['ID']
        self.assertEqual(1, len(DoGet(_REMOTE, '/instances')))

        tags = [ 'PatientID', 'StudyInstanceUID', 'SeriesInstanceUID', 'SOPInstanceUID', 'DeidentificationMethod' ]
        ids = [ 'ozp00SjY2xG',
                '1.2.840.113619.2.176.2025.1499492.7391.1171285944.390',
                '1.2.840.113619.2.176.2025.1499492.7391.1171285944.394',
                '1.2.840.113619.2.176.2025.1499492.7040.1171286242.109' ]

        a = ExtractDicomTags(Anonymize(u), tags)
        for i in range(4):
            self.assertNotEqual(ids[i], a[i])
        self.assertTrue(a[4].startswith('Orthanc'))

        a = ExtractDicomTags(Anonymize(u, { 'PatientName' : 'toto' }), tags)
        for i in range(4):
            self.assertNotEqual(ids[i], a[i])
        self.assertNotIn('PS 3.15', a[4])

        a = ExtractDicomTags(Anonymize(u, { 'SOPInstanceUID' : 'instance' }), tags)
        self.assertEqual('instance', a[3])
        self.assertNotIn('PS 3.15', a[4])

        a = ExtractDicomTags(Anonymize(u, { 'SeriesInstanceUID' : 'series' }), tags)
        self.assertEqual('series', a[2])
        self.assertNotIn('PS 3.15', a[4])

        a = ExtractDicomTags(Anonymize(u, { 'StudyInstanceUID' : 'study' }), tags)
        self.assertEqual('study', a[1])
        self.assertNotIn('PS 3.15', a[4])

        a = ExtractDicomTags(Anonymize(u, { 'PatientID' : 'patient' }), tags)
        self.assertEqual('patient', a[0])
        self.assertNotIn('PS 3.15', a[4])

        a = ExtractDicomTags(Anonymize(u, { 'PatientID' : 'patient',
                                            'StudyInstanceUID' : 'study',
                                            'SeriesInstanceUID' : 'series',
                                            'SOPInstanceUID' : 'instance' }), tags)
        self.assertEqual('patient', a[0])
        self.assertNotIn('PS 3.15', a[4])

        self.assertEqual(1, len(DoGet(_REMOTE, '/instances')))


    def test_shanon_2(self):
        def Modify(instance, replacements = {}):
            return DoPost(_REMOTE, '/instances/%s/modify' % instance, {
                'Replace' : replacements,
                'Force': True,
            }, 'application/json')

        self.assertEqual(0, len(DoGet(_REMOTE, '/instances')))
        u = UploadInstance(_REMOTE, 'DummyCT.dcm')['ID']
        self.assertEqual(1, len(DoGet(_REMOTE, '/instances')))

        tags = [ 'PatientID', 'StudyInstanceUID', 'SeriesInstanceUID', 'SOPInstanceUID', 'DeidentificationMethod' ]
        ids = [ 'ozp00SjY2xG',
                '1.2.840.113619.2.176.2025.1499492.7391.1171285944.390',
                '1.2.840.113619.2.176.2025.1499492.7391.1171285944.394',
                '1.2.840.113619.2.176.2025.1499492.7040.1171286242.109' ]

        a = ExtractDicomTags(Modify(u), tags)
        self.assertEqual(ids[0], a[0])
        self.assertEqual(ids[1], a[1])
        self.assertEqual(ids[2], a[2])
        self.assertNotEqual(ids[3], a[3])
        self.assertEqual(0, len(a[4]))

        a = ExtractDicomTags(Modify(u, { 'SOPInstanceUID' : 'instance' }), tags)
        self.assertEqual(ids[0], a[0])
        self.assertEqual(ids[1], a[1])
        self.assertEqual(ids[2], a[2])
        self.assertEqual('instance', a[3])

        a = ExtractDicomTags(Modify(u, { 'SeriesInstanceUID' : 'series' }), tags)
        self.assertEqual(ids[0], a[0])
        self.assertEqual(ids[1], a[1])
        self.assertEqual('series', a[2])
        self.assertNotEqual(ids[3], a[3])

        a = ExtractDicomTags(Modify(u, { 'StudyInstanceUID' : 'study' }), tags)
        self.assertEqual(ids[0], a[0])
        self.assertEqual('study', a[1])
        self.assertNotEqual(ids[2], a[2])
        self.assertNotEqual(ids[3], a[3])

        a = ExtractDicomTags(Modify(u, { 'PatientID' : 'patient' }), tags)
        self.assertEqual('patient', a[0])
        self.assertNotEqual(ids[1], a[1])
        self.assertNotEqual(ids[2], a[2])
        self.assertNotEqual(ids[3], a[3])

        a = ExtractDicomTags(Modify(u, { 'PatientID' : 'patient',
                                         'StudyInstanceUID' : 'study',
                                         'SeriesInstanceUID' : 'series',
                                         'SOPInstanceUID' : 'instance' }), tags)
        self.assertEqual('patient', a[0])
        self.assertEqual('study', a[1])
        self.assertEqual('series', a[2])
        self.assertEqual('instance', a[3])

        self.assertEqual(1, len(DoGet(_REMOTE, '/instances')))
        

    def test_instances_tags(self):
        a = UploadInstance(_REMOTE, 'Knee/T1/IM-0001-0001.dcm')['ID']
        b = UploadInstance(_REMOTE, 'Knee/T2/IM-0001-0001.dcm')['ID']
        #a = UploadInstance(_REMOTE, 'Cardiac/MR.X.1.2.276.0.7230010.3.1.4.2831157719.2256.1336386937.676343')['ID']
        #b = UploadInstance(_REMOTE, 'Cardiac/MR.X.1.2.276.0.7230010.3.1.4.2831157719.2256.1336386925.676329')['ID']

        i = DoGet(_REMOTE, '/patients/%s/instances-tags?simplify' % DoGet(_REMOTE, '/patients')[0])
        self.assertEqual(2, len(i))
        self.assertEqual('887', i[i.keys()[0]]['PatientID'])
        self.assertEqual('887', i[i.keys()[1]]['PatientID'])

        i = DoGet(_REMOTE, '/studies/%s/instances-tags?simplify' % DoGet(_REMOTE, '/studies')[0])
        self.assertEqual(2, len(i))
        self.assertEqual('887', i[i.keys()[0]]['PatientID'])
        self.assertEqual('887', i[i.keys()[1]]['PatientID'])

        self.assertEqual(2, len(DoGet(_REMOTE, '/series')))
        i = DoGet(_REMOTE, '/series/%s/instances-tags?simplify' % DoGet(_REMOTE, '/series')[0])
        self.assertEqual(1, len(i))
        self.assertEqual('887', i[i.keys()[0]]['PatientID'])
        
        i = DoGet(_REMOTE, '/series/%s/instances-tags?simplify' % DoGet(_REMOTE, '/series')[1])
        self.assertEqual(1, len(i))
        self.assertEqual('887', i[i.keys()[0]]['PatientID'])

        i = DoGet(_REMOTE, '/series/%s/instances-tags?short' % DoGet(_REMOTE, '/series')[1])
        self.assertEqual(1, len(i))
        self.assertEqual('887', i[i.keys()[0]]['0010,0020'])


    def test_lookup(self):
        a = DoPost(_REMOTE, '/tools/lookup', 'ozp00SjY2xG')
        self.assertEqual(0, len(a))

        UploadInstance(_REMOTE, 'DummyCT.dcm')

        a = DoPost(_REMOTE, '/tools/lookup', 'ozp00SjY2xG')
        self.assertEqual(1, len(a))
        self.assertEqual('Patient', a[0]['Type'])
        self.assertEqual('6816cb19-844d5aee-85245eba-28e841e6-2414fae2', a[0]['ID'])
        self.assertEqual('/patients/%s' % a[0]['ID'], a[0]['Path'])
        
        a = DoPost(_REMOTE, '/tools/lookup', '1.2.840.113619.2.176.2025.1499492.7391.1171285944.390')
        self.assertEqual(1, len(a))
        self.assertEqual('Study', a[0]['Type'])
        self.assertEqual('b9c08539-26f93bde-c81ab0d7-bffaf2cb-a4d0bdd0', a[0]['ID'])
        self.assertEqual('/studies/%s' % a[0]['ID'], a[0]['Path'])
        
        a = DoPost(_REMOTE, '/tools/lookup', '1.2.840.113619.2.176.2025.1499492.7391.1171285944.394')
        self.assertEqual(1, len(a))
        self.assertEqual('Series', a[0]['Type'])
        self.assertEqual('f2635388-f01d497a-15f7c06b-ad7dba06-c4c599fe', a[0]['ID'])
        self.assertEqual('/series/%s' % a[0]['ID'], a[0]['Path'])
        
        a = DoPost(_REMOTE, '/tools/lookup', '1.2.840.113619.2.176.2025.1499492.7040.1171286242.109')
        self.assertEqual(1, len(a))
        self.assertEqual('Instance', a[0]['Type'])
        self.assertEqual('66a662ce-7430e543-bad44d47-0dc5a943-ec7a538d', a[0]['ID'])
        self.assertEqual('/instances/%s' % a[0]['ID'], a[0]['Path'])

        DropOrthanc(_REMOTE)
        a = DoPost(_REMOTE, '/tools/lookup', '3113719P')
        self.assertEqual(0, len(a))


    def test_autorouting(self):
        knee1 = 'Knee/T1/IM-0001-0001.dcm'
        knee2 = 'Knee/T2/IM-0001-0002.dcm'
        other = 'Brainix/Flair/IM-0001-0001.dcm'

        # Check that this version is >= 0.8.0
        self.assertTrue(IsDefinedInLua(_REMOTE, '_InitializeJob'))
        self.assertTrue('orthanctest' in DoGet(_REMOTE, '/modalities'))

        UploadInstance(_REMOTE, knee1)
        self.assertEqual(0, len(DoGet(_LOCAL, '/instances')))

        DropOrthanc(_REMOTE)
        DropOrthanc(_LOCAL)
        InstallLuaScriptFromPath(_REMOTE, 'Lua/Autorouting.lua')
        UploadInstance(_REMOTE, knee1)
        UploadInstance(_REMOTE, knee2)
        UploadInstance(_REMOTE, other)
        WaitEmpty(_REMOTE)
        UninstallLuaCallbacks(_REMOTE)
        self.assertEqual(3, len(DoGet(_LOCAL, '/instances')))

        DropOrthanc(_REMOTE)
        DropOrthanc(_LOCAL)
        InstallLuaScriptFromPath(_REMOTE, 'Lua/AutoroutingConditional.lua')
        UploadInstance(_REMOTE, knee1)
        UploadInstance(_REMOTE, knee2)
        UploadInstance(_REMOTE, other)
        WaitEmpty(_REMOTE)
        UninstallLuaCallbacks(_REMOTE)
        self.assertEqual(2, len(DoGet(_LOCAL, '/instances')))
        
        DropOrthanc(_REMOTE)
        DropOrthanc(_LOCAL)
        InstallLuaScriptFromPath(_REMOTE, 'Lua/AutoroutingModification.lua')
        UploadInstance(_REMOTE, knee1)
        WaitEmpty(_REMOTE)
        UninstallLuaCallbacks(_REMOTE)
        i = DoGet(_LOCAL, '/instances')
        self.assertEqual(1, len(i))
        
        with tempfile.NamedTemporaryFile(delete = True) as f:
            f.write(DoGet(_LOCAL, '/instances/%s/file' % i[0]))
            f.flush()
            routed = subprocess.check_output([ FindExecutable('dcm2xml'), f.name ])
            self.assertEqual('My Medical Device', re.search('"StationName">(.*?)<', routed).group(1).strip())
            self.assertEqual(None, re.search('"MilitaryRank"', routed))
            self.assertEqual(None, re.search('"0051,0010"', routed))  # A private tag


    def test_storescu_rf(self):
        i = UploadInstance(_REMOTE, 'KarstenHilbertRF.dcm')['ID']
        self.assertEqual(0, len(DoGet(_LOCAL, '/instances')))
        j = DoPost(_REMOTE, '/modalities/orthanctest/store', str(i), 'text/plain')
        self.assertEqual(1, len(DoGet(_LOCAL, '/instances')))


    def test_anonymize_instance(self):
        def AnonymizeAndUpload(instanceId, parameters):
            return DoPost(_REMOTE, '/instances', DoPost(_REMOTE, '/instances/%s/anonymize' % instanceId, parameters,
                                               'application/json'), 'application/dicom')['ID']

        def ModifyAndUpload(instanceId, parameters):
            return DoPost(_REMOTE, '/instances', DoPost(_REMOTE, '/instances/%s/modify' % instanceId, parameters,
                                               'application/json'), 'application/dicom')['ID']

        a = UploadInstance(_REMOTE, 'PrivateMDNTags.dcm')['ID']
        s1 = DoGet(_REMOTE, '/instances/%s/content/PatientName' % a)
        s2 = DoGet(_REMOTE, '/instances/%s/content/00e1-10c2' % a)  # Some private tag
        s3 = DoGet(_REMOTE, '/instances/%s/content/StudyDescription' % a)
        s4 = DoGet(_REMOTE, '/instances/%s/content/SeriesDescription' % a)
        s5 = DoGet(_REMOTE, '/instances/%s/content/InstitutionName' % a)
        
        b = AnonymizeAndUpload(a, '{}')
        self.assertNotEqual(s1, DoGet(_REMOTE, '/instances/%s/content/PatientName' % b))
        self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/instances/%s/content/00e1-10c2' % b))
        
        # Keep private tag (only OK since Orthanc 0.8.0)
        b = AnonymizeAndUpload(a, '{"Keep":["00e1-10c2"]}')  
        self.assertNotEqual(s1, DoGet(_REMOTE, '/instances/%s/content/PatientName' % b))
        self.assertEqual(s2, DoGet(_REMOTE, '/instances/%s/content/00e1-10c2' % b))
        
        b = AnonymizeAndUpload(a, '{"Keep":["00e1,10c2","PatientName"]}')
        self.assertEqual(s1, DoGet(_REMOTE, '/instances/%s/content/PatientName' % b))
        self.assertEqual(s2, DoGet(_REMOTE, '/instances/%s/content/00e1-10c2' % b))
        
        b = AnonymizeAndUpload(a, '{"Keep":["PatientName"],"Replace":{"00e1,10c2":"Hello"}}')
        self.assertEqual(s1, DoGet(_REMOTE, '/instances/%s/content/PatientName' % b))
        self.assertTrue(DoGet(_REMOTE, '/instances/%s/content/00e1-10c2' % b).startswith('Hello'))

        # Examples from the Wiki
        b = AnonymizeAndUpload(a, '{"Replace":{"PatientName":"hello","0010-0020":"world"},"Keep":["StudyDescription", "SeriesDescription"],"KeepPrivateTags": true,"Force":true}')
        self.assertEqual('hello', DoGet(_REMOTE, '/instances/%s/content/0010-0010' % b).strip())
        self.assertEqual('world', DoGet(_REMOTE, '/instances/%s/content/PatientID' % b).strip())
        self.assertEqual(s3, DoGet(_REMOTE, '/instances/%s/content/0008,1030' % b))
        self.assertEqual(s4, DoGet(_REMOTE, '/instances/%s/content/0008,103e' % b))
        self.assertEqual(s4, DoGet(_REMOTE, '/instances/%s/content/0008-103E' % b))
        self.assertEqual(s2, DoGet(_REMOTE, '/instances/%s/content/00e1-10c2' % b))
        DoGet(_REMOTE, '/instances/%s/content/InstitutionName' % a)
        self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/instances/%s/content/InstitutionName' % b))

        b = ModifyAndUpload(a, '{"Replace":{"PatientName":"hello","PatientID":"world"},"Remove":["InstitutionName"],"RemovePrivateTags": true,"Force":true}')
        self.assertEqual('hello', DoGet(_REMOTE, '/instances/%s/content/0010-0010' % b).strip())
        self.assertEqual('world', DoGet(_REMOTE, '/instances/%s/content/PatientID' % b).strip())
        self.assertEqual(s3, DoGet(_REMOTE, '/instances/%s/content/0008,1030' % b))
        self.assertEqual(s4, DoGet(_REMOTE, '/instances/%s/content/0008,103e' % b))
        self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/instances/%s/content/00e1-10c2' % b))
        self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/instances/%s/content/InstitutionName' % b))

        b = ModifyAndUpload(a, '{"Replace":{"PatientName":"hello","PatientID":"world"},"Force":true}')
        self.assertEqual('hello', DoGet(_REMOTE, '/instances/%s/content/0010-0010' % b).strip())
        self.assertEqual('world', DoGet(_REMOTE, '/instances/%s/content/PatientID' % b).strip())
        self.assertEqual(s2, DoGet(_REMOTE, '/instances/%s/content/00e1,10c2' % b))
        self.assertEqual(s3, DoGet(_REMOTE, '/instances/%s/content/0008,1030' % b))
        self.assertEqual(s4, DoGet(_REMOTE, '/instances/%s/content/0008-103E' % b))
        self.assertEqual(s5, DoGet(_REMOTE, '/instances/%s/content/InstitutionName' % b))


        # Test modify non-existing
        i = DoPost(_REMOTE, '/tools/create-dicom',
                   json.dumps({
                    'PatientName' : 'Jodogne',
                    'Modality' : 'CT',
                    }))['ID']

        self.assertEqual('Jodogne', DoGet(_REMOTE, '/instances/%s/content/PatientName' % i).strip())
        self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/instances/%s/content/StudyDescription' % i))
        self.assertEqual('CT', DoGet(_REMOTE, '/instances/%s/content/Modality' % i).strip())

        b = ModifyAndUpload(i, '{"Replace":{"StudyDescription":"hello","Modality":"world"}}')
        self.assertEqual('Jodogne', DoGet(_REMOTE, '/instances/%s/content/PatientName' % b).strip())
        self.assertEqual('hello', DoGet(_REMOTE, '/instances/%s/content/StudyDescription' % b).strip())
        self.assertEqual('world', DoGet(_REMOTE, '/instances/%s/content/Modality' % b).strip())


    def test_incoming_jpeg(self):
        # since this test fails regularly on CI, enable verbosity
        DoPut(_REMOTE, '/tools/log-level', 'verbose')

        def storescu(image, acceptUnknownSopClassUid, expectSuccess = True, retries = 1):
            if acceptUnknownSopClassUid:
                tmp = [ '-xf', GetDatabasePath('UnknownSopClassUid.cfg'), 'Default' ]
            else:
                tmp = [ '-xs' ]

            while retries > 0:
                retries -= 1
                with open(os.devnull, 'w') as FNULL:
                    try:
                        subprocess.check_call([ FindExecutable('storescu') ] + tmp +
                                            [ _REMOTE['Server'], str(_REMOTE['DicomPort']),
                                                GetDatabasePath(image) ],
                                            stderr = FNULL)

                        if expectSuccess:
                            return
                    except subprocess.CalledProcessError as e:
                        print('storescu failed with error code: %s' % str(e.returncode))
                        if not expectSuccess:
                            raise e

        self.assertEqual(0, len(DoGet(_REMOTE, '/patients')))

        if IsOrthancVersionAbove(_REMOTE, 1, 9, 0):
            a = DoPut(_REMOTE, '/tools/accepted-transfer-syntaxes', [
                '1.2.840.10008.1.2', '1.2.840.10008.1.2.1', '1.2.840.10008.1.2.2'
            ])
            self.assertTrue('1.2.840.10008.1.2' in a)
            self.assertTrue('1.2.840.10008.1.2.1' in a)
            self.assertTrue('1.2.840.10008.1.2.2' in a)
            self.assertEqual(3, len(a))
            self.assertRaises(Exception, lambda: DoPut(_REMOTE, '/tools/unknown-sop-class-accepted', 'nope'))
            DoPut(_REMOTE, '/tools/unknown-sop-class-accepted', '0')
            self.assertEqual(0, DoGet(_REMOTE, '/tools/unknown-sop-class-accepted'))
        else:
            InstallLuaScriptFromPath(_REMOTE, 'Lua/TransferSyntaxDisable.lua')
        
        # the following line regularly fails on CI because storescu still returns 0 although the C-Store fails -> that's why we have implemented retries
        self.assertRaises(Exception, lambda: storescu('Knix/Loc/IM-0001-0001.dcm', False, False, 3))
        self.assertRaises(Exception, lambda: storescu('UnknownSopClassUid.dcm', True, False, 3))
        self.assertEqual(0, len(DoGet(_REMOTE, '/patients')))

        if IsOrthancVersionAbove(_REMOTE, 1, 9, 0):
            a = DoPut(_REMOTE, '/tools/accepted-transfer-syntaxes', '*', 'text/plain')
            self.assertGreaterEqual(42, len(a))
            DoPut(_REMOTE, '/tools/unknown-sop-class-accepted', 'true')
            self.assertEqual(1, DoGet(_REMOTE, '/tools/unknown-sop-class-accepted'))
        else:
            InstallLuaScriptFromPath(_REMOTE, 'Lua/TransferSyntaxEnable.lua')

        DoPost(_REMOTE, '/tools/execute-script', "print('All special transfer syntaxes are now accepted')")
        storescu('Knix/Loc/IM-0001-0001.dcm', False)
        storescu('UnknownSopClassUid.dcm', True)
        self.assertEqual(2, len(DoGet(_REMOTE, '/patients')))

        # set back normal verbosity
        DoPut(_REMOTE, '/tools/log-level', 'default')

    def test_storescu_jpeg(self):
        self.assertEqual(0, len(DoGet(_REMOTE, '/exports')['Exports']))

        knixStudy = 'b9c08539-26f93bde-c81ab0d7-bffaf2cb-a4d0bdd0'
        i = UploadInstance(_REMOTE, 'Knix/Loc/IM-0001-0001.dcm')['ID']

        # This is JPEG lossless
        self.assertEqual('1.2.840.10008.1.2.4.70', DoGet(_REMOTE, '/instances/%s/header' % i)['0002,0010']['Value'])
        self.assertEqual('1.2.840.10008.1.2.4.70', DoGet(_REMOTE, '/instances/%s/header?simplify' % i)['TransferSyntaxUID'])
        self.assertEqual('1.2.840.10008.1.2.4.70', DoGet(_REMOTE, '/instances/%s/header?short' % i)['0002,0010'])

        UploadInstance(_REMOTE, 'Knix/Loc/IM-0001-0002.dcm')
        UploadInstance(_REMOTE, 'Knix/Loc/IM-0001-0003.dcm')

        a = UploadInstance(_REMOTE, 'Brainix/Flair/IM-0001-0001.dcm')['ID']
        b = UploadInstance(_REMOTE, 'ColorTestImageJ.dcm')['ID']
        self.assertEqual(0, len(DoGet(_LOCAL, '/instances')))
        DoPost(_REMOTE, '/modalities/orthanctest/store', [ knixStudy, a, b ])
        self.assertEqual(5, len(DoGet(_LOCAL, '/instances')))

        self.assertEqual(3, len(DoGet(_REMOTE, '/exports')['Exports']))

        DropOrthanc(_REMOTE)
        self.assertEqual(0, len(DoGet(_REMOTE, '/exports')['Exports']))


    def test_pixel_data(self):
        jpeg = UploadInstance(_REMOTE, 'Knix/Loc/IM-0001-0001.dcm')['ID']
        color = UploadInstance(_REMOTE, 'ColorTestImageJ.dcm')['ID']
        phenix = UploadInstance(_REMOTE, 'Phenix/IM-0001-0001.dcm')['ID']
        
        phenixSize = 358 * 512 * 2
        colorSize = 1000 * 1000 * 3
        jpegSize = 51918

        self.assertEqual(1, len(DoGet(_REMOTE, '/instances/%s/content/7fe0-0010' % phenix)))
        self.assertEqual(1, len(DoGet(_REMOTE, '/instances/%s/content/7fe0-0010' % color)))
        self.assertEqual(2, len(DoGet(_REMOTE, '/instances/%s/content/7fe0-0010' % jpeg)))
        
        self.assertEqual(0, len(DoGet(_REMOTE, '/instances/%s/content/7fe0-0010/0' % jpeg)))
        self.assertEqual(jpegSize, len(DoGet(_REMOTE, '/instances/%s/content/7fe0-0010/1' % jpeg)))       

        self.assertEqual(phenixSize, len(DoGet(_REMOTE, '/instances/%s/content/7fe0-0010/0' % phenix)))
        self.assertEqual(colorSize, len(DoGet(_REMOTE, '/instances/%s/content/7fe0-0010/0' % color)))


    def test_decode_brainix(self):
        brainix = [
            UploadInstance(_REMOTE, 'Brainix/Epi/IM-0001-0001.dcm')['ID'], # (*)
            UploadInstance(_REMOTE, 'Formats/JpegLossless.dcm')['ID'],  # JPEG-LS, same as (*) (since Orthanc 0.7.6) => doesn't work on big-endian
            UploadInstance(_REMOTE, 'Formats/Jpeg.dcm')['ID'],  # JPEG, same as (*) (since Orthanc 0.7.6)
            ]
        h = '6fb11b932d535c2be04beabd99793ff8'
        maxValue = 426.0

        truth = Image.open(GetDatabasePath('Formats/Brainix.png'))
        for i in brainix:
            self.AssertSameImages(truth.getdata(), '/instances/%s/image-int16' % i)
            self.AssertSameImages(truth.getdata(), '/instances/%s/image-uint16' % i)

        truth2 = map(lambda x: min(255, x), truth.getdata())
        for i in brainix:
            self.AssertSameImages(truth2, '/instances/%s/image-uint8' % i)

        truth2 = map(lambda x: x * 255.0 / maxValue, truth.getdata())
        for i in brainix:
            self.AssertSameImages(truth2, '/instances/%s/preview' % i)

        for i in brainix:
            self.assertEqual(h, ComputeMD5(DoGet(_REMOTE, '/instances/%s/matlab' % i)))


    def test_decode_color(self):
        imagej = UploadInstance(_REMOTE, 'ColorTestImageJ.dcm')['ID']
        color = UploadInstance(_REMOTE, 'ColorTestMalaterre.dcm')['ID']

        for i in [ imagej, color ]:
            for j in [ 'image-uint8', 'image-uint16', 'image-int16' ]:
                self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/instances/%s/%s' % (i, j)))

        self.assertEqual('c14c687f7a1ea9fe022479fc87c67274', ComputeMD5(DoGet(_REMOTE, '/instances/%s/preview' % imagej)))
        self.assertEqual('a87d122918a56f803bcfe9d2586b9125', ComputeMD5(DoGet(_REMOTE, '/instances/%s/preview' % color)))

        self.assertEqual('30cc46bfa7aba77a40e4178f6184c25a', ComputeMD5(DoGet(_REMOTE, '/instances/%s/matlab' % imagej)))
        self.assertEqual('ff195005cef06b59666fd220a9b4cd9a', ComputeMD5(DoGet(_REMOTE, '/instances/%s/matlab' % color)))


    def test_decode_rf(self):
        rf = UploadInstance(_REMOTE, 'KarstenHilbertRF.dcm')['ID']
        truth = Image.open(GetDatabasePath('Formats/KarstenHilbertRF.png'))

        self.AssertSameImages(truth.getdata(), '/instances/%s/image-uint8' % rf)
        self.AssertSameImages(truth.getdata(), '/instances/%s/image-uint16' % rf)
        self.AssertSameImages(truth.getdata(), '/instances/%s/image-int16' % rf)
        self.AssertSameImages(truth.getdata(), '/instances/%s/preview' % rf)

        self.assertEqual('42254d70efd2f4a1b8f3455909689f0e', ComputeMD5(DoGet(_REMOTE, '/instances/%s/matlab' % rf)))


    def test_decode_multiframe(self):
        mf = UploadInstance(_REMOTE, 'Multiframe.dcm')['ID']

        # Test the first frame
        truth = Image.open(GetDatabasePath('Formats/Multiframe0.png'))
        self.AssertSameImages(truth.getdata(), '/instances/%s/image-uint8' % mf)
        self.AssertSameImages(truth.getdata(), '/instances/%s/image-uint16' % mf)
        self.AssertSameImages(truth.getdata(), '/instances/%s/image-int16' % mf)
        self.AssertSameImages(truth.getdata(), '/instances/%s/preview' % mf)
        self.assertEqual('9812b99d93bbcd4e7684ded089b5dfb3', ComputeMD5(DoGet(_REMOTE, '/instances/%s/matlab' % mf)))

        self.AssertSameImages(truth.getdata(), '/instances/%s/frames/0/image-uint16' % mf)

        # Test the last frame
        truth = Image.open(GetDatabasePath('Formats/Multiframe75.png'))
        self.AssertSameImages(truth.getdata(), '/instances/%s/frames/75/image-uint16' % mf)


    def test_decode_signed(self):
        signed = UploadInstance(_REMOTE, 'SignedCT.dcm')['ID']
        minValue = -2000
        maxValue = 4042

        truth = Image.open(GetDatabasePath('Formats/SignedCT.png'))
        self.AssertSameImages(truth.getdata(), '/instances/%s/image-int16' % signed)

        truth2 = map(lambda x: 0 if x >= 32768 else x, truth.getdata())
        self.AssertSameImages(truth2, '/instances/%s/image-uint16' % signed)

        truth3 = map(lambda x: 255 if x >= 256 else x, truth2)
        self.AssertSameImages(truth3, '/instances/%s/image-uint8' % signed)

        tmp = map(lambda x: x - 65536 if x >= 32768 else x, truth.getdata())
        tmp = map(lambda x: (255.0 * (x - minValue)) / (maxValue - minValue), tmp)
        self.AssertSameImages(tmp, '/instances/%s/preview' % signed)

        self.assertEqual('b57e6c872a3da50877c7da689b03a444', ComputeMD5(DoGet(_REMOTE, '/instances/%s/matlab' % signed)))


    def test_googlecode_issue_32(self):
        self.assertRaises(Exception, lambda: DoPut(_REMOTE, '/tools/default-encoding', 'nope'))
        self.assertEqual('Windows1251', DoPut(_REMOTE, '/tools/default-encoding', 'Windows1251'))
        self.assertEqual('Windows1251', DoGet(_REMOTE, '/tools/default-encoding'))
        
        f = UploadInstance(_REMOTE, 'Issue32.dcm')['ID']
        tags = DoGet(_REMOTE, '/instances/%s/tags?simplify' % f)
        self.assertEqual(u'Рентгенография', tags['SeriesDescription'])
        self.assertEqual(u'Таз', tags['BodyPartExamined'])
        self.assertEqual(u'Прямая', tags['ViewPosition'])

        # Replay the same test using Latin1 as default encoding: This must fail
        self.assertEqual('Latin1', DoPut(_REMOTE, '/tools/default-encoding', 'Latin1'))

        DoDelete(_REMOTE, '/instances/%s' % f)
        f = UploadInstance(_REMOTE, 'Issue32.dcm')['ID']
        tags = DoGet(_REMOTE, '/instances/%s/tags?simplify' % f)
        self.assertNotEqual(u'Рентгенография', tags['SeriesDescription'])

        
    def test_encodings(self):
        # Latin-1 (ISO_IR 100)
        brainix = UploadInstance(_REMOTE, 'Brainix/Epi/IM-0001-0001.dcm')['ID']
        tags = DoGet(_REMOTE, '/instances/%s/tags?simplify' % brainix)
        self.assertEqual(u'IRM cérébrale, neuro-crâne', tags['StudyDescription'])

        # Latin-2 (ISO_IR 101)
        a = UploadInstance(_REMOTE, 'MarekLatin2.dcm')['ID']
        i = DoGet(_REMOTE, '/instances/%s/simplified-tags' % a)
        # dcm2xml MarekLatin2.dcm | iconv -f latin2 -t utf-8 | xmllint --format -
        self.assertEqual('Imię i Nazwisko osoby opisującej', 
                         i['ContentSequence'][4]['ConceptNameCodeSequence'][0]['CodeMeaning'].encode('utf-8'))
        

    def test_storescu_custom_aet(self):
        # This tests a feature introduced in Orthanc 0.9.1: "Custom
        # setting of the local AET during C-Store SCU (both in Lua and
        # in the REST API)."
        # https://groups.google.com/forum/#!msg/orthanc-users/o5qMULformU/wZjW2iSaMcAJ

        self.assertEqual(0, len(DoGet(_LOCAL, '/patients')))
        
        a = UploadInstance(_REMOTE, 'Knee/T1/IM-0001-0001.dcm')
        b = UploadInstance(_REMOTE, 'Knee/T1/IM-0001-0002.dcm')
        c = UploadInstance(_REMOTE, 'Knee/T1/IM-0001-0003.dcm')

        j = DoPost(_REMOTE, '/modalities/orthanctest/store', {
            'LocalAet' : 'YOP',
            'Resources' : [ a['ID'], b['ID'] ]
        })

        self.assertEqual(2, len(DoGet(_LOCAL, '/instances')))
        self.assertEqual('YOP', DoGet(_LOCAL, '/instances/%s/metadata/RemoteAET' % a['ID']))

        DropOrthanc(_LOCAL)
        self.assertEqual(0, len(DoGet(_LOCAL, '/instances')))

        j = DoPost(_REMOTE, '/modalities/orthanctest/store', {
            'Resources' : [ c['ID'] ]
        })

        self.assertEqual(1, len(DoGet(_LOCAL, '/instances')))
        self.assertEqual('ORTHANC', DoGet(_LOCAL, '/instances/%s/metadata/RemoteAET' % c['ID']))

        DropOrthanc(_REMOTE)        
        DropOrthanc(_LOCAL)        

        InstallLuaScriptFromPath(_REMOTE, 'Lua/AutoroutingChangeAet.lua')
        DoPost(_REMOTE, '/tools/execute-script', 'aet = "HELLO"', 'application/lua')

        self.assertEqual(0, len(DoGet(_LOCAL, '/instances')))
        UploadInstance(_REMOTE, 'Knee/T1/IM-0001-0001.dcm')
        WaitEmpty(_REMOTE)
        self.assertEqual(1, len(DoGet(_LOCAL, '/instances')))
        self.assertEqual('HELLO', DoGet(_LOCAL, '/instances/%s/metadata/RemoteAET' % a['ID']))

        DoPost(_REMOTE, '/tools/execute-script', 'aet = nill', 'application/lua')
        UploadInstance(_REMOTE, 'Knee/T1/IM-0001-0002.dcm')
        WaitEmpty(_REMOTE)
        self.assertEqual(2, len(DoGet(_LOCAL, '/instances')))
        self.assertEqual('ORTHANC', DoGet(_LOCAL, '/instances/%s/metadata/RemoteAET' % b['ID']))

    def test_resources_since_limit(self):
        # Upload 16 instances
        for i in range(4):
            UploadInstance(_REMOTE, 'Brainix/Flair/IM-0001-000%d.dcm' % (i + 1))
            UploadInstance(_REMOTE, 'Brainix/Epi/IM-0001-000%d.dcm' % (i + 1))
            UploadInstance(_REMOTE, 'Knee/T1/IM-0001-000%d.dcm' % (i + 1))
            UploadInstance(_REMOTE, 'Knee/T2/IM-0001-000%d.dcm' % (i + 1))

        self.assertEqual(2, len(DoGet(_REMOTE, '/patients')))
        self.assertEqual(2, len(DoGet(_REMOTE, '/studies')))
        self.assertEqual(4, len(DoGet(_REMOTE, '/series')))
        self.assertEqual(16, len(DoGet(_REMOTE, '/instances')))

        self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/patients&since=10' % i))
        self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/patients&limit=10' % i))

        if IsOrthancVersionAbove(_REMOTE, 1, 12, 5): # with ExtendedFind, the limit=0 means no-limit like in /tools/find
            self.assertEqual(2, len(DoGet(_REMOTE, '/patients?since=0&limit=0')))
            self.assertEqual(1, len(DoGet(_REMOTE, '/patients?since=1&limit=0')))
            self.assertEqual(0, len(DoGet(_REMOTE, '/patients?since=2&limit=0')))
            self.assertEqual(0, len(DoGet(_REMOTE, '/patients?since=3&limit=0')))
        else:
            self.assertEqual(0, len(DoGet(_REMOTE, '/patients?since=0&limit=0')))
            self.assertEqual(0, len(DoGet(_REMOTE, '/patients?since=1&limit=0')))
            self.assertEqual(0, len(DoGet(_REMOTE, '/patients?since=2&limit=0')))
            self.assertEqual(0, len(DoGet(_REMOTE, '/patients?since=3&limit=0')))
        self.assertEqual(2, len(DoGet(_REMOTE, '/patients?since=0&limit=100')))
        self.assertEqual(2, len(DoGet(_REMOTE, '/studies?since=0&limit=100')))
        self.assertEqual(4, len(DoGet(_REMOTE, '/series?since=0&limit=100')))
        self.assertEqual(16, len(DoGet(_REMOTE, '/instances?since=0&limit=100')))
        self.assertEqual(1, len(DoGet(_REMOTE, '/patients?since=1&limit=100')))
        self.assertEqual(0, len(DoGet(_REMOTE, '/patients?since=2&limit=100')))
        self.assertEqual(0, len(DoGet(_REMOTE, '/patients?since=3&limit=100')))
        self.assertEqual(1, len(DoGet(_REMOTE, '/studies?since=1&limit=100')))
        self.assertEqual(3, len(DoGet(_REMOTE, '/series?since=1&limit=100')))
        self.assertEqual(2, len(DoGet(_REMOTE, '/series?since=2&limit=100')))
        self.assertEqual(1, len(DoGet(_REMOTE, '/series?since=3&limit=100')))
        self.assertEqual(0, len(DoGet(_REMOTE, '/series?since=4&limit=100')))
        self.assertEqual(0, len(DoGet(_REMOTE, '/series?since=100&limit=100')))
        self.assertEqual(15, len(DoGet(_REMOTE, '/instances?since=1&limit=100')))

        for limit in [ 1, 2, 3, 7, 16, 17 ]:
            s = {}
            since = 0
            while True:
                t = DoGet(_REMOTE, '/instances?since=%d&limit=%d' % (since, limit))
                if len(t) == 0:
                    break

                since += len(t)
                for i in t:
                    s[i] = None

            self.assertEqual(16, len(s))
            for instance in DoGet(_REMOTE, '/instances'):
                self.assertTrue(instance in s)


    def test_create_pdf(self):
        # Upload 4 instances
        brainixInstance = UploadInstance(_REMOTE, 'Brainix/Flair/IM-0001-0001.dcm')['ID']
        UploadInstance(_REMOTE, 'Brainix/Epi/IM-0001-0001.dcm')
        UploadInstance(_REMOTE, 'Knee/T1/IM-0001-0001.dcm')
        UploadInstance(_REMOTE, 'Knee/T2/IM-0001-0001.dcm')
        
        brainixPatient = '16738bc3-e47ed42a-43ce044c-a3414a45-cb069bd0'
        brainixStudy = '27f7126f-4f66fb14-03f4081b-f9341db2-53925988'
        brainixEpi = '2ac1316d-3e432022-62eabff2-c59f5475-9b1ac3f8'

        with open(GetDatabasePath('HelloWorld.pdf'), 'rb') as f:
            pdf = f.read()

        i = DoPost(_REMOTE, '/tools/create-dicom',
                   json.dumps({
                       'Tags' : {
                           'PatientName' : 'Jodogne',
                           'Modality' : 'CT',
                       },
                       'Content' : 'data:application/pdf;base64,' + base64.b64encode(pdf)
                   }))

        self.assertEqual('Jodogne', DoGet(_REMOTE, '/instances/%s/content/PatientName' % i['ID']).strip())
        self.assertEqual('1.2.840.10008.5.1.4.1.1.104.1', DoGet(_REMOTE, '/instances/%s/content/SOPClassUID' % i['ID']).strip('\x00'))
        self.assertEqual('WSD', DoGet(_REMOTE, '/instances/%s/content/ConversionType' % i['ID']).strip())
        self.assertEqual('application/pdf', DoGet(_REMOTE, '/instances/%s/content/MIMETypeOfEncapsulatedDocument' % i['ID']).strip())

        # In Orthanc <= 1.9.7, the "CT" would have been replaced by "OT"
        # https://groups.google.com/g/orthanc-users/c/eNSddNrQDtM/m/wc1HahimAAAJ
        self.assertEqual('CT', DoGet(_REMOTE, '/instances/%s/content/Modality' % i['ID']).strip())

        b = DoGet(_REMOTE, '/instances/%s/content/0042-0011' % i['ID'])
        self.assertEqual(len(b), len(pdf) + 1)
        self.assertEqual(ComputeMD5(b), ComputeMD5(pdf + '\0'))

        self.assertRaises(Exception, lambda: DoPost(_REMOTE, '/tools/create-dicom',
                                                    json.dumps({
                                                        'Parent' : brainixPatient,
                                                        'Tags' : {
                                                            'PatientName' : 'Jodogne',
                                                        }
                                                    })))

        i = DoPost(_REMOTE, '/tools/create-dicom',
                   json.dumps({
                       'Parent' : brainixPatient,
                       'Tags' : { 'StudyDescription' : 'PDF^Patient' },
                       'Content' : 'data:application/pdf;base64,' + base64.b64encode(pdf)
                   }))
        
        self.assertEqual(brainixPatient, DoGet(_REMOTE, '/instances/%s/patient' % i['ID'])['ID'])
        self.assertEqual('1.2.840.10008.5.1.4.1.1.104.1', DoGet(_REMOTE, '/instances/%s/content/SOPClassUID' % i['ID']).strip('\x00'))
        self.assertEqual('OT', DoGet(_REMOTE, '/instances/%s/content/Modality' % i['ID']).strip('\x00'))
        self.assertEqual('WSD', DoGet(_REMOTE, '/instances/%s/content/ConversionType' % i['ID']).strip())
        self.assertEqual('application/pdf', DoGet(_REMOTE, '/instances/%s/content/MIMETypeOfEncapsulatedDocument' % i['ID']).strip())

        i = DoPost(_REMOTE, '/tools/create-dicom',
                   json.dumps({
                       'Parent' : brainixStudy,
                       'Tags' : { 'SeriesDescription' : 'PDF^Study' },
                       'Content' : 'data:application/pdf;base64,' + base64.b64encode(pdf)
                   }))
        
        self.assertEqual(brainixStudy, DoGet(_REMOTE, '/instances/%s/study' % i['ID'])['ID'])

        i = DoPost(_REMOTE, '/tools/create-dicom',
                   json.dumps({
                       'Parent' : brainixEpi,
                       'Tags' : { 'SpecificCharacterSet' : 'ISO_IR 13' },
                       'Content' : 'data:application/pdf;base64,' + base64.b64encode(pdf)
                   }))
        
        self.assertEqual(brainixEpi, DoGet(_REMOTE, '/instances/%s/series' % i['ID'])['ID'])

        b = DoGet(_REMOTE, '/instances/%s/pdf' % i['ID'])
        self.assertEqual(len(b), len(pdf))
        self.assertEqual(ComputeMD5(b), ComputeMD5(pdf))

        self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/instances/%s/pdf' % brainixInstance))


    def test_create_series(self):
        i = DoPost(_REMOTE, '/tools/create-dicom',
                   json.dumps({
                    'Tags' : {
                        'SpecificCharacterSet' : 'ISO_IR 100',
                        'PatientName' : 'Sébastien Jodogne',
                        'Modality' : 'CT',
                        },
                    'Content' : [
                        {
                            'Content': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg==', # red dot in RGBA
                            'Tags' : { 'ImageComments' : 'Tutu' }
                            },
                        'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAoUlEQVQ4jZ2SWw3EIBREjwUsYAELa2EtoAULFUCyXAtroRZqoRbox254BdLC/DZnZjoXWJFgCDg8egW2CBEhEnDzyRk+Ecxz2KP/0AL8S99T+jQccAVs22qKwAuPuq0uyNg9cPLh3am+pe/dkHLZtqJHj6vXJrZ7nvzvxxgemXgUwnGfXqpee09mUwp8m022OYP6bLF7mVuVe0y/umxinsAXRd9z0k1ubWsAAAAASUVORK5CYII=',
                        ]
                    }))

        s = DoGet(_REMOTE, i['Path'])
        self.assertEqual('Series', s['Type'])
        self.assertEqual(s['ID'], i['ID'])
        self.assertEqual(2, len(s['Instances']))
        self.assertEqual(2, s['ExpectedNumberOfInstances'])
        self.assertEqual('Complete', s['Status'])

        a = DoGet(_REMOTE, '/instances/%s/tags?simplify' % s['Instances'][0])
        b = DoGet(_REMOTE, '/instances/%s/tags?simplify' % s['Instances'][1])
        self.assertTrue('ImageComments' in a or 'ImageComments' in b)
        if 'ImageComments' in a:
            self.assertEqual('Tutu', a['ImageComments'])
        else:
            self.assertEqual('Tutu', b['ImageComments'])

        patient = DoGet(_REMOTE, '/instances/%s/patient' % s['Instances'][0])
        self.assertEqual(patient['MainDicomTags']['PatientName'].encode('utf-8'),
                         'Sébastien Jodogne')


    def test_create_binary(self):
        binary = ''.join(map(chr, range(256)))
        encoded = 'data:application/octet-stream;base64,' + base64.b64encode(binary)
        tags = {
            'PatientName' : 'Jodogne',
            '8899-8899' : encoded
        }

        i = DoPost(_REMOTE, '/tools/create-dicom',
                   json.dumps({
                       'Tags' : tags,
                       'PrivateCreator' : 'TestBinary',
                   }))

        self.assertEqual('Jodogne', DoGet(_REMOTE, '/instances/%s/content/PatientName' % i['ID']).strip())
        self.assertEqual(binary, DoGet(_REMOTE, '/instances/%s/content/8899-8899' % i['ID']).strip())

        i = DoPost(_REMOTE, '/tools/create-dicom',
                   json.dumps({
                       'InterpretBinaryTags' : False,
                       'Tags' : tags,
                       'PrivateCreator' : 'TestBinary',
                   }))

        self.assertEqual('Jodogne', DoGet(_REMOTE, '/instances/%s/content/PatientName' % i['ID']).strip())
        self.assertEqual(encoded, DoGet(_REMOTE, '/instances/%s/content/8899-8899' % i['ID'])[0:-1])


    def test_patient_ids_collision(self):
        # Upload 3 instances from 3 different studies, but with the
        # same PatientID
        for i in range(3):
            UploadInstance(_REMOTE, 'PatientIdsCollision/Image%d.dcm' % (i + 1))

        a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Patient',
                                             'Query' : { 'PatientName' : '*' }})
        self.assertEqual(1, len(a))
        self.assertEqual('COMMON', DoGet(_REMOTE, '/patients/%s' % a[0]) ['MainDicomTags']['PatientID'])

        a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Study',
                                             'CaseSensitive' : True,
                                             'Query' : { 'PatientName' : 'FOO\\HELLO' }})
        self.assertEqual(2, len(a))

        a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Series',
                                             'CaseSensitive' : False,
                                             'Query' : { 'PatientName' : 'Foo' }})
        self.assertEqual(1, len(a))
        self.assertEqual('FOO^SERIES', DoGet(_REMOTE, '/series/%s/study' % a[0]) ['MainDicomTags']['StudyDescription'])
        self.assertEqual('FOO', DoGet(_REMOTE, '/series/%s/study' % a[0]) ['PatientMainDicomTags']['PatientName'])
        self.assertEqual('COMMON', DoGet(_REMOTE, '/series/%s/study' % a[0]) ['PatientMainDicomTags']['PatientID'])

        a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Study',
                                             'Query' : { 'PatientName' : '*' }})
        self.assertEqual(3, len(a))
        d = map(lambda x: DoGet(_REMOTE, '/studies/%s' % x) ['MainDicomTags']['StudyDescription'], a)
        self.assertTrue('FOO^SERIES' in d)
        self.assertTrue('HELLO^SERIES' in d)
        self.assertTrue('WORLD^SERIES' in d)

        d = map(lambda x: DoGet(_REMOTE, '/studies/%s' % x) ['PatientMainDicomTags']['PatientID'], a)
        self.assertEqual(1, len(set(d)))
        self.assertEqual('COMMON', d[0])

        for i in a:
            d = DoGet(_REMOTE, '/studies/%s' % i) ['MainDicomTags']['StudyDescription']
            p = DoGet(_REMOTE, '/studies/%s' % i) ['PatientMainDicomTags']['PatientName']
            self.assertEqual('%s^SERIES' % p, d)


    def test_bitbucket_issue_4(self):
        UploadInstance(_REMOTE, 'Brainix/Epi/IM-0001-0001.dcm')
        UploadInstance(_REMOTE, 'Brainix/Epi/IM-0001-0002.dcm')
        UploadInstance(_REMOTE, 'Brainix/Epi/IM-0001-0003.dcm')
        UploadInstance(_REMOTE, 'Formats/Jpeg.dcm')
        UploadInstance(_REMOTE, 'Formats/JpegLossless.dcm')
        UploadInstance(_REMOTE, 'Formats/Rle.dcm')
       
        self.assertEqual(0, len(DoGet(_LOCAL, '/instances')))
        self.assertEqual(6, len(DoGet(_REMOTE, '/instances')))

        p = DoGet(_REMOTE, '/patients')
        self.assertEqual(2, len(p))
        i1 = map(lambda x: x['ID'], DoGet(_REMOTE, '/patients/%s/instances' % p[0]))
        i2 = map(lambda x: x['ID'], DoGet(_REMOTE, '/patients/%s/instances' % p[1]))
        self.assertEqual(3, len(i1))
        self.assertEqual(3, len(i2))

        j = DoPost(_REMOTE, '/modalities/orthanctest/store', i2[0:1] + i1 + i2[1:3])

        self.assertEqual(6, len(DoGet(_LOCAL, '/instances')))


    def test_create_sequence(self):
        i = DoPost(_REMOTE, '/tools/create-dicom',
                   json.dumps({
                    'Tags' : {
                        'SpecificCharacterSet': 'ISO_IR 100',  # Encode using Latin1
                        'PatientName': 'Jodogne^',
                        'ReferencedStudySequence': GenerateTestSequence(),
                    }
                   }))['ID']

        self.assertEqual('Jodogne^', DoGet(_REMOTE, '/instances/%s/content/PatientName' % i))
        self.assertEqual('Hello^', DoGet(_REMOTE, '/instances/%s/content/ReferencedStudySequence/0/StudyDescription' % i))
        self.assertEqual('Toto', DoGet(_REMOTE, '/instances/%s/content/ReferencedStudySequence/0/ReferencedStudySequence/0/StudyDescription' % i))
        self.assertEqual('Tata', DoGet(_REMOTE, '/instances/%s/content/ReferencedStudySequence/0/ReferencedStudySequence/1/StudyDescription' % i))
        self.assertEqual(u'Sébastien^'.encode('latin-1'),
                         DoGet(_REMOTE, '/instances/%s/content/ReferencedStudySequence/1/StudyDescription' % i))


    def test_modify_sequence(self):
        i = UploadInstance(_REMOTE, 'PrivateTags.dcm')['ID']
        self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/instances/%s/content/ReferencedStudySequence' % i))

        j = DoPost(_REMOTE, '/instances/%s/modify' % i,
                   json.dumps({
                    "Replace" : {
                        "PatientName" : "hello",
                        'ReferencedStudySequence': GenerateTestSequence(),
                        },
                    }),
                   'application/json')
        j = DoPost(_REMOTE, '/instances', j, 'application/dicom')['ID']
        DoDelete(_REMOTE, '/instances/%s' % i)

        self.assertEqual(2, len(DoGet(_REMOTE, '/instances/%s/content/ReferencedStudySequence' % j)))


    def test_compression(self):
        i = UploadInstance(_REMOTE, 'DummyCT.dcm')['ID']

        aa = DoGet(_REMOTE, '/instances/%s/attachments/' % i)
        if IsOrthancVersionAbove(_REMOTE, 1, 9, 1):
            # This file has *no* pixel data, so "dicom-until-pixel-data" is not stored
            self.assertEqual(1, len(aa))
            self.assertTrue('dicom' in aa)
        else:
            self.assertEqual(2, len(aa))
            self.assertTrue('dicom' in aa)
            self.assertTrue('dicom-as-json' in aa)
            
        data = DoGetRaw(_REMOTE, '/instances/%s/attachments/dicom/data' % i)[1]

        # If "StorageCompression" is enabled in the Orthanc to be
        # tested, uncompress the attachment before running the test
        if DoGet(_REMOTE, '/instances/%s/attachments/dicom/is-compressed' % i) != 0:
            DoPost(_REMOTE, '/instances/%s/attachments/dicom/uncompress' % i)
 
        cs = int(DoGet(_REMOTE, '/statistics')['TotalDiskSize'])
        us = int(DoGet(_REMOTE, '/statistics')['TotalUncompressedSize'])
        size = int(DoGet(_REMOTE, '/instances/%s/attachments/dicom/size' % i))
        md5 = DoGet(_REMOTE, '/instances/%s/attachments/dicom/md5' % i)
        self.assertEqual(data, DoGetRaw(_REMOTE, '/instances/%s/attachments/dicom/compressed-data' % i)[1])
        self.assertEqual(md5, DoGet(_REMOTE, '/instances/%s/attachments/dicom/compressed-md5' % i))
        self.assertEqual(size, int(DoGet(_REMOTE, '/instances/%s/attachments/dicom/compressed-size' % i)))

        ops = DoGet(_REMOTE, '/instances/%s/attachments/dicom' % i)
        self.assertTrue('compress' in ops)
        self.assertTrue('uncompress' in ops)
        self.assertTrue('is-compressed' in ops)
        self.assertEqual(0, DoGet(_REMOTE, '/instances/%s/attachments/dicom/is-compressed' % i))
        DoPost(_REMOTE, '/instances/%s/attachments/dicom/verify-md5' % i)

        # Re-compress the attachment
        DoPost(_REMOTE, '/instances/%s/attachments/dicom/compress' % i)
        DoPost(_REMOTE, '/instances/%s/attachments/dicom/verify-md5' % i)
        self.assertEqual(1, DoGet(_REMOTE, '/instances/%s/attachments/dicom/is-compressed' % i))
        self.assertGreater(cs, int(DoGet(_REMOTE, '/statistics')['TotalDiskSize']))
        self.assertEqual(us, int(DoGet(_REMOTE, '/statistics')['TotalUncompressedSize']))
        self.assertGreater(len(data), len(DoGetRaw(_REMOTE, '/instances/%s/attachments/dicom/compressed-data' % i)[1]))
        self.assertGreater(size, int(DoGet(_REMOTE, '/instances/%s/attachments/dicom/compressed-size' % i)))
        self.assertEqual(size, int(DoGet(_REMOTE, '/instances/%s/attachments/dicom/size' % i)))
        self.assertEqual(md5, DoGet(_REMOTE, '/instances/%s/attachments/dicom/md5' % i))
        self.assertNotEqual(md5, DoGet(_REMOTE, '/instances/%s/attachments/dicom/compressed-md5' % i))

        DoPost(_REMOTE, '/instances/%s/attachments/dicom/uncompress' % i)
        DoPost(_REMOTE, '/instances/%s/attachments/dicom/verify-md5' % i)
        self.assertEqual(0, DoGet(_REMOTE, '/instances/%s/attachments/dicom/is-compressed' % i))
        self.assertEqual(data, DoGetRaw(_REMOTE, '/instances/%s/attachments/dicom/compressed-data' % i)[1])
        self.assertEqual(size, int(DoGet(_REMOTE, '/instances/%s/attachments/dicom/compressed-size' % i)))
        self.assertEqual(size, int(DoGet(_REMOTE, '/instances/%s/attachments/dicom/size' % i)))
        self.assertEqual(md5, DoGet(_REMOTE, '/instances/%s/attachments/dicom/md5' % i))
        self.assertEqual(md5, DoGet(_REMOTE, '/instances/%s/attachments/dicom/compressed-md5' % i))
        self.assertEqual(cs, int(DoGet(_REMOTE, '/statistics')['TotalDiskSize']))
        self.assertEqual(us, int(DoGet(_REMOTE, '/statistics')['TotalUncompressedSize']))


    def test_ordered_slices(self):
        i = UploadInstance(_REMOTE, 'Multiframe.dcm')['ID']
        s = DoGet(_REMOTE, '/instances/%s' % i)['ParentSeries']
        o = DoGet(_REMOTE, '/series/%s/ordered-slices' % s)
        self.assertEqual('Sequence', o['Type'])
        self.assertEqual(1, len(o['Dicom']))
        self.assertEqual('/instances/9e05eb0a-18b6268c-e0d36085-8ddab517-3b5aec02/file', o['Dicom'][0])
        self.assertEqual(76, len(o['Slices']))
        for j in range(76):
            self.assertEqual('/instances/9e05eb0a-18b6268c-e0d36085-8ddab517-3b5aec02/frames/%d' % j, o['Slices'][j])

        self.assertEqual(1, len(o['SlicesShort']))
        self.assertEqual('9e05eb0a-18b6268c-e0d36085-8ddab517-3b5aec02', o['SlicesShort'][0][0])
        self.assertEqual(0, o['SlicesShort'][0][1])
        self.assertEqual(76, o['SlicesShort'][0][2])

        i = UploadInstance(_REMOTE, 'Brainix/Epi/IM-0001-0001.dcm')['ID']
        j = UploadInstance(_REMOTE, 'Brainix/Epi/IM-0001-0002.dcm')['ID']
        k = UploadInstance(_REMOTE, 'Brainix/Epi/IM-0001-0003.dcm')['ID']
        s = DoGet(_REMOTE, '/instances/%s' % i)['ParentSeries']
        o = DoGet(_REMOTE, '/series/%s/ordered-slices' % s)

        self.assertEqual('Volume', o['Type'])
        self.assertEqual(3, len(o['Dicom']))
        self.assertEqual(3, len(o['Slices']))
        self.assertEqual('/instances/%s/file' % i, o['Dicom'][2])
        self.assertEqual('/instances/%s/file' % j, o['Dicom'][1])
        self.assertEqual('/instances/%s/file' % k, o['Dicom'][0])
        self.assertEqual('/instances/%s/frames/0' % i, o['Slices'][2])
        self.assertEqual('/instances/%s/frames/0' % j, o['Slices'][1])
        self.assertEqual('/instances/%s/frames/0' % k, o['Slices'][0])

        self.assertEqual(3, len(o['SlicesShort']))
        self.assertEqual(k, o['SlicesShort'][0][0])
        self.assertEqual(0, o['SlicesShort'][0][1])
        self.assertEqual(1, o['SlicesShort'][0][2])
        self.assertEqual(j, o['SlicesShort'][1][0])
        self.assertEqual(0, o['SlicesShort'][1][1])
        self.assertEqual(1, o['SlicesShort'][1][2])
        self.assertEqual(i, o['SlicesShort'][2][0])
        self.assertEqual(0, o['SlicesShort'][2][1])
        self.assertEqual(1, o['SlicesShort'][2][2])

        i = UploadInstance(_REMOTE, 'Beaufix/IM-0001-0001.dcm')['ID']
        j = UploadInstance(_REMOTE, 'Beaufix/IM-0001-0002.dcm')['ID']
        s = DoGet(_REMOTE, '/instances/%s' % i)['ParentSeries']
        o = DoGet(_REMOTE, '/series/%s/ordered-slices' % s)

        self.assertEqual('Sequence', o['Type'])
        self.assertEqual(2, len(o['Dicom']))
        self.assertEqual(2, len(o['Slices']))
        self.assertEqual('/instances/%s/file' % i, o['Dicom'][0])
        self.assertEqual('/instances/%s/file' % j, o['Dicom'][1])
        self.assertEqual('/instances/%s/frames/0' % i, o['Slices'][0])
        self.assertEqual('/instances/%s/frames/0' % j, o['Slices'][1])

        self.assertEqual(2, len(o['SlicesShort']))
        self.assertEqual(i, o['SlicesShort'][0][0])
        self.assertEqual(0, o['SlicesShort'][0][1])
        self.assertEqual(1, o['SlicesShort'][0][2])
        self.assertEqual(j, o['SlicesShort'][1][0])
        self.assertEqual(0, o['SlicesShort'][1][1])
        self.assertEqual(1, o['SlicesShort'][1][2])



    def test_incoming_movescu_accession(self):
        UploadInstance(_REMOTE, 'Knee/T1/IM-0001-0001.dcm')
        
        # No matching patient, so no job is created
        self.assertEqual(0, len(DoGet(_LOCAL, '/patients')))
        CallMoveScu([ '--study', '-k', '0008,0052=STUDY', '-k', 'AccessionNumber=nope' ])
        self.assertEqual(0, len(DoGet(_LOCAL, '/patients')))
        CallMoveScu([ '--study', '-k', '0008,0052=PATIENT', '-k', 'AccessionNumber=A10003245599' ])
        self.assertEqual(0, len(DoGet(_LOCAL, '/patients')))

        # 1 Matching patient, track the job
        self.assertTrue(MonitorJob(_REMOTE, lambda: CallMoveScu([
            '--study',
            '-k', '0008,0052=STUDY',
            '-k', 'AccessionNumber=A10003245599'
        ])))
        
        self.assertEqual(1, len(DoGet(_LOCAL, '/patients')))


    def test_dicom_to_json(self):
        i = UploadInstance(_REMOTE, 'PrivateMDNTags.dcm')['ID']
        j = UploadInstance(_REMOTE, 'PrivateTags.dcm')['ID']

        t = DoGet(_REMOTE, '/instances/%s/tags?simplify' % i)
        with open(GetDatabasePath('PrivateMDNTagsSimplify.json'), 'r') as f:
            self.assertTrue(CompareTags(t, json.loads(f.read()), [
                # Tags for compatibility with DCMTK 3.6.0
                'RETIRED_OtherPatientIDs',
                'OtherPatientIDs',
                'ACR_NEMA_2C_VariablePixelDataGroupLength',
            ]))

        t = DoGet(_REMOTE, '/instances/%s/tags' % i)
        with open(GetDatabasePath('PrivateMDNTagsFull.json'), 'r') as f:
            self.assertTrue(CompareTags(t, json.loads(f.read()), [ 
            ]))

        t = DoGet(_REMOTE, '/instances/%s/tags?simplify' % j)
        with open(GetDatabasePath('PrivateTagsSimplify.json'), 'r') as f:
            self.assertTrue(CompareTags(t, json.loads(f.read()), [
            ]))


        # NB: To get the actual value of the "tags" JSON file, use the
        # following command:
        # $ curl http://alice:orthanctest@localhost:8042/instances/d29ead49-43e8601d-72f1e922-7de676ee-ea77c2b4/tags
        t = DoGet(_REMOTE, '/instances/%s/tags' % j)
        with open(GetDatabasePath('PrivateTagsFull.json'), 'r') as f:
            a = json.loads(f.read())

            # Starting with Orthanc 1.9.1, the DICOM-as-JSON
            # reports are truncated starting with PixelData
            if IsOrthancVersionAbove(_REMOTE, 1, 9, 1):
                self.assertFalse('7fe1,0010' in t)
                self.assertFalse('7fe1,1001' in t)
                del a['7fe1,0010']
                del a['7fe1,1001']
            else:
                self.assertTrue('7fe1,0010' in t)
                self.assertTrue('7fe1,1001' in t)
                
            aa = json.dumps(a).replace('2e+022', '2e+22')
            tt = (json.dumps(t)
                  .replace('2e+022', '2e+22')
                  # The "IllegalPrivatePixelSequence" tag was introduced in DCMTK 3.6.6 dictionary
                  .replace('IllegalPrivatePixelSequence', 'Unknown Tag & Data'))
            self.assertEqual(aa, tt)


    def test_batch_archive(self):
        UploadInstance(_REMOTE, 'Knee/T1/IM-0001-0001.dcm')
        UploadInstance(_REMOTE, 'Knee/T1/IM-0001-0002.dcm')
        UploadInstance(_REMOTE, 'Knee/T2/IM-0001-0001.dcm')
        UploadInstance(_REMOTE, 'Knee/T2/IM-0001-0002.dcm')
        UploadInstance(_REMOTE, 'Brainix/Epi/IM-0001-0001.dcm')
        UploadInstance(_REMOTE, 'Brainix/Epi/IM-0001-0002.dcm')
        UploadInstance(_REMOTE, 'Brainix/Flair/IM-0001-0001.dcm')
        UploadInstance(_REMOTE, 'Brainix/Flair/IM-0001-0002.dcm')

        s = DoPost(_REMOTE, '/tools/create-archive', [ ])
        z = zipfile.ZipFile(StringIO(s), "r")
        self.assertEqual(0, len(z.namelist()))
       
        # One patient
        s = DoPost(_REMOTE, '/tools/create-archive', [ 'ca29faea-b6a0e17f-067743a1-8b778011-a48b2a17' ])
        z = zipfile.ZipFile(StringIO(s), "r")
        self.assertEqual(4, len(z.namelist()))

        # One patient + twice its study + one series from other patient
        s = DoPost(_REMOTE, '/tools/create-archive', [ 
            'ca29faea-b6a0e17f-067743a1-8b778011-a48b2a17',
            '0a9b3153-2512774b-2d9580de-1fc3dcf6-3bd83918',
            '1e2c125c-411b8e86-3f4fe68e-a7584dd3-c6da78f0'
        ])
        z = zipfile.ZipFile(StringIO(s), "r")
        self.assertEqual(6, len(z.namelist()))        

        # One patient + one series + one instance
        s = DoPost(_REMOTE, '/tools/create-archive', [ 
            'ca29faea-b6a0e17f-067743a1-8b778011-a48b2a17',
            '1e2c125c-411b8e86-3f4fe68e-a7584dd3-c6da78f0',
            '1d429ccb-bdcc78a1-7d129d6a-ba4966ed-fe4dbd87'
        ])
        z = zipfile.ZipFile(StringIO(s), "r")
        self.assertEqual(7, len(z.namelist()))

        if IsOrthancVersionAbove(_REMOTE, 1, 12, 2):
            s = DoGet(_REMOTE, '/tools/create-archive?resources=ca29faea-b6a0e17f-067743a1-8b778011-a48b2a17,1e2c125c-411b8e86-3f4fe68e-a7584dd3-c6da78f0,1d429ccb-bdcc78a1-7d129d6a-ba4966ed-fe4dbd87')
            z = zipfile.ZipFile(StringIO(s), "r")
            self.assertEqual(7, len(z.namelist()))



    def test_decode_brainix_as_jpeg(self):
        i = UploadInstance(_REMOTE, 'Brainix/Epi/IM-0001-0001.dcm')['ID']

        j = GetImage(_REMOTE, '/instances/%s/preview' % i)
        self.assertEqual('PNG', j.format)
        self.assertEqual(j.size[0], 256)
        self.assertEqual(j.size[1], 256)

        j = GetImage(_REMOTE, '/instances/%s/preview' % i, headers = { 'Accept' : '*/*' })
        self.assertEqual('PNG', j.format)

        j = GetImage(_REMOTE, '/instances/%s/preview' % i, headers = { 'Accept' : 'image/*' })
        self.assertEqual('PNG', j.format)

        j = GetImage(_REMOTE, '/instances/%s/preview' % i, headers = { 'Accept' : 'image/png' })
        self.assertEqual('PNG', j.format)

        j = GetImage(_REMOTE, '/instances/%s/preview' % i, headers = { 'Accept' : 'image/jpeg' })
        self.assertEqual('JPEG', j.format)
        self.assertEqual(j.size[0], 256)
        self.assertEqual(j.size[1], 256)

        a = len(DoGet(_REMOTE, '/instances/%s/preview?quality=50' % i, headers = { 'Accept' : 'image/jpeg' }))
        b = len(DoGet(_REMOTE, '/instances/%s/preview' % i, headers = { 'Accept' : 'image/jpeg' }))
        self.assertLess(a, b)

        j = GetImage(_REMOTE, '/instances/%s/image-uint8' % i, headers = { 'Accept' : 'image/jpeg' })
        self.assertEqual('JPEG', j.format)

        # 16bit encoding is not supported with JPEG
        self.assertRaises(Exception, lambda: GetImage(_REMOTE, '/instances/%s/image-uint16' % i, headers = { 'Accept' : 'image/jpeg' }))
        self.assertRaises(Exception, lambda: GetImage(_REMOTE, '/instances/%s/image-int16' % i, headers = { 'Accept' : 'image/jpeg' }))

        # No matching content type
        self.assertRaises(Exception, lambda: GetImage(_REMOTE, '/instances/%s/preview' % i, headers = { 'Accept' : 'application/pdf' }))



    def test_media_encodings(self):
        ascii = UploadInstance(_REMOTE, 'Knee/T1/IM-0001-0001.dcm')['ID']
        latin1 = UploadInstance(_REMOTE, 'Brainix/Epi/IM-0001-0001.dcm')['ID']
        latin2 = UploadInstance(_REMOTE, 'MarekLatin2.dcm')['ID']

        tmp = DoPost(_REMOTE, '/tools/create-media', [ascii,latin1,latin2])
        z = zipfile.ZipFile(StringIO(tmp), "r")

        self.assertEqual(4, len(z.namelist()))
        self.assertTrue('IMAGES/IM0' in z.namelist())
        self.assertTrue('IMAGES/IM1' in z.namelist())
        self.assertTrue('IMAGES/IM2' in z.namelist())
        self.assertTrue('DICOMDIR' in z.namelist())

        try:
            os.remove('/tmp/DICOMDIR')
        except:
            # The file does not exist
            pass

        z.extract('DICOMDIR', '/tmp')
        a = subprocess.check_output([ FindExecutable('dciodvfy'), '/tmp/DICOMDIR' ],
                                    stderr = subprocess.STDOUT).split('\n')

        a = subprocess.check_output([ FindExecutable('dcentvfy'), '/tmp/DICOMDIR' ],
                                    stderr = subprocess.STDOUT).split('\n')
        self.assertEqual(1, len(a))
        self.assertEqual('', a[0])

        a = subprocess.check_output([ FindExecutable('dcm2xml'), '/tmp/DICOMDIR' ])
        self.assertTrue(re.search('1.3.46.670589.11.17521.5.0.3124.2008081908590448738', a) != None)
        self.assertTrue(re.search('1.3.46.670589.11.0.0.11.4.2.0.8743.5.5396.2006120114333648576', a) != None)
        self.assertTrue(re.search('1.2.826.0.1.3680043.2.1569.1.4.323026757.1700.1399452091.57', a) != None)

        os.remove('/tmp/DICOMDIR')


    def test_findscu_counters(self):
        UploadInstance(_REMOTE, 'Comunix/Ct/IM-0001-0001.dcm')
        UploadInstance(_REMOTE, 'Comunix/Pet/IM-0001-0001.dcm')
        UploadInstance(_REMOTE, 'Comunix/Pet/IM-0001-0002.dcm')

        i = CallFindScu([ '-k', '0008,0052=PATIENT', '-k', 'NumberOfPatientRelatedStudies' ])
        s = re.findall('\(0020,1200\).*?\[(.*?)\]', i)
        self.assertEqual(1, len(s))
        self.assertTrue('1 ' in s)

        i = CallFindScu([ '-k', '0008,0052=PATIENT', '-k', 'NumberOfPatientRelatedSeries' ])
        s = re.findall('\(0020,1202\).*?\[(.*?)\]', i)
        self.assertEqual(1, len(s))
        self.assertTrue('2 ' in s)

        i = CallFindScu([ '-k', '0008,0052=PATIENT', '-k', 'NumberOfPatientRelatedInstances' ])
        s = re.findall('\(0020,1204\).*?\[(.*?)\]', i)
        self.assertEqual(1, len(s))
        self.assertTrue('3 ' in s)

        i = CallFindScu([ '-k', '0008,0052=STUDY', '-k', 'NumberOfStudyRelatedSeries' ])
        s = re.findall('\(0020,1206\).*?\[(.*?)\]', i)
        self.assertEqual(1, len(s))
        self.assertTrue('2 ' in s)

        i = CallFindScu([ '-k', '0008,0052=STUDY', '-k', 'NumberOfStudyRelatedInstances' ])
        s = re.findall('\(0020,1208\).*?\[(.*?)\]', i)
        self.assertEqual(1, len(s))
        self.assertTrue('3 ' in s)

        i = CallFindScu([ '-k', '0008,0052=SERIES', '-k', 'NumberOfSeriesRelatedInstances' ])
        s = re.findall('\(0020,1209\).*?\[(.*?)\]', i)
        self.assertEqual(2, len(s))
        self.assertTrue('1 ' in s)
        self.assertTrue('2 ' in s)

        i = CallFindScu([ '-k', '0008,0052=STUDY', '-k', 'ModalitiesInStudy' ])
        s = re.findall('\(0008,0061\).*?\[(.*?)\]', i)
        self.assertEqual(1, len(s))
        t = map(lambda x: x.strip(), s[0].split('\\'))
        self.assertTrue('PT' in t)
        self.assertTrue('CT' in t)

        i = CallFindScu([ '-k', '0008,0052=STUDY', '-k', 'SOPClassesInStudy' ])
        s = re.findall('\(0008,0062\).*?\[(.*?)\]', i)
        self.assertEqual(1, len(s))
        t = map(lambda x: x.strip('\x00'), s[0].split('\\'))
        self.assertTrue('1.2.840.10008.5.1.4.1.1.2' in t)
        self.assertTrue('1.2.840.10008.5.1.4.1.1.128' in t)


    def test_decode_transfer_syntax(self):
        def Check(t, md5):
            i = UploadInstance(_REMOTE, 'TransferSyntaxes/%s.dcm' % t)['ID']

            if t != '1.2.840.10008.1.2':  # This file has no meta header
                transferSyntax = DoGet(_REMOTE, '/instances/%s/metadata/TransferSyntax' % i)
                self.assertEqual(t, transferSyntax)

            if md5 == None:
                self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/instances/%s/preview' % i))
            else:
                m = ComputeMD5(DoGet(_REMOTE, '/instances/%s/preview' % i))
                self.assertEqual(m, md5)

        Check('1.2.840.10008.1.2.1', 'fae08d5415c4c0cd2cdbae4522408631')
        Check('1.2.840.10008.1.2.2', 'f3d9784768b8feb54d6a50b6d5c37682')
        Check('1.2.840.10008.1.2.4.51', 'ccbe75909fe5c9f7361b48416a53fc41')
        Check('1.2.840.10008.1.2.4.57', '7bbefe11d976b1be4e568915c6a82fc3')
        Check('1.2.840.10008.1.2.4.70', '7132cfbc457305b04b59787030c785d2')
        Check('1.2.840.10008.1.2.5', '6ff51ae525d362e0d04f550a64075a0e')  # RLE, supported since Orthanc 1.0.1
        Check('1.2.840.10008.1.2', 'd54aed9f67a100984b42942cc2e9939b')

        # The 3 checks below don't work on big-endian
        Check('1.2.840.10008.1.2.4.50', '496326046974eea718dbc16b997c646b')  # TODO - Doesn't work with GDCM 3.0.7 alone
        Check('1.2.840.10008.1.2.4.80', '6ff51ae525d362e0d04f550a64075a0e')
        Check('1.2.840.10008.1.2.4.81', '801579ae7cbf28e604ea74f2c99fa2ca')

        # JPEG2k image, not supported without GDCM plugin
        if not HasGdcmPlugin(_REMOTE):
            Check('1.2.840.10008.1.2.4.90', None)
            Check('1.2.840.10008.1.2.4.91', None)


    def test_raw_frame(self):
        s = UploadInstance(_REMOTE, 'Issue22.dcm')['ID']
        self.assertEqual(24, len(DoGet(_REMOTE, '/instances/%s/frames' % s)))
        a = DoGet(_REMOTE, '/instances/%s/frames/0/raw' % s)
        self.assertEqual(512 * 512 * 2, len(a))
        self.assertEqual(512 * 512 * 2, len(DoGet(_REMOTE, '/instances/%s/frames/23/raw' % s)))
        self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/instances/%s/frames/24/raw' % s))
        self.assertEqual('1914287dc4d958eca21fdaacfb3482fa', ComputeMD5(a))

        s = UploadInstance(_REMOTE, 'Multiframe.dcm')['ID']
        self.assertEqual(76, len(DoGet(_REMOTE, '/instances/%s/frames' % s)))
        self.assertEqual(186274, len(DoGet(_REMOTE, '/instances/%s/frames/0/raw' % s)))
        self.assertEqual(189424, len(DoGet(_REMOTE, '/instances/%s/frames/75/raw' % s)))
        self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/instances/%s/frames/76/raw' % s))
        im = GetImage(_REMOTE, '/instances/%s/frames/0/raw' % s)
        self.assertEqual("L", im.mode)
        self.assertEqual(512, im.size[0])
        self.assertEqual(512, im.size[1])

        # Test an image with 2 JPEG frames spread over multiple fragments
        s = UploadInstance(_REMOTE, 'LenaTwiceWithFragments.dcm')['ID']
        self.assertEqual(2, len(DoGet(_REMOTE, '/instances/%s/frames' % s)))
        a = DoGet(_REMOTE, '/instances/%s/frames/0/raw' % s)
        b = DoGet(_REMOTE, '/instances/%s/frames/1/raw' % s)
        self.assertEqual(69214, len(a))
        self.assertEqual(ComputeMD5(a), ComputeMD5(b))
        self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/instances/%s/frames/2/raw' % s))
        im = GetImage(_REMOTE, '/instances/%s/frames/0/raw' % s)
        self.assertEqual("RGB", im.mode)
        self.assertEqual(512, im.size[0])
        self.assertEqual(512, im.size[1])
        im = GetImage(_REMOTE, '/instances/%s/frames/0/preview' % s)  # TODO - Doesn't work with GDCM 3.0.7 alone
        self.assertEqual("RGB", im.mode)
        self.assertEqual(512, im.size[0])
        self.assertEqual(512, im.size[1])



    def test_rest_movescu(self):
        self.assertEqual(0, len(DoGet(_REMOTE, '/patients')))

        # Upload 4 instances
        UploadInstance(_REMOTE, 'Brainix/Flair/IM-0001-0001.dcm')
        UploadInstance(_REMOTE, 'Brainix/Flair/IM-0001-0002.dcm')
        UploadInstance(_REMOTE, 'Brainix/Epi/IM-0001-0001.dcm')
        UploadInstance(_REMOTE, 'Knee/T2/IM-0001-0001.dcm')

        self.assertEqual(2, len(DoGet(_REMOTE, '/patients')))
        for p in DoGet(_REMOTE, '/patients'):
            DoPost(_REMOTE, '/modalities/orthanctest/store', p)
            DoDelete(_REMOTE, '/patients/%s' % p)

        self.assertEqual(0, len(DoGet(_REMOTE, '/patients')))

        # Move instance Brainix/Flair/IM-0001-0001.dcm
        DoPost(_REMOTE, '/modalities/orthanctest/move', { 
            'Level' : 'Instance',
            'Resources' : [
                { 
                    'StudyInstanceUID' : '2.16.840.1.113669.632.20.1211.10000357775',
                    'SeriesInstanceUID' : '1.3.46.670589.11.0.0.11.4.2.0.8743.5.5396.2006120114285654497',
                    'SOPInstanceUID' : '1.3.46.670589.11.0.0.11.4.2.0.8743.5.5396.2006120114314079549',
                }
            ]})

        # Move series Brainix/Flair/*
        self.assertEqual(1, len(DoGet(_REMOTE, '/patients')))
        self.assertEqual(1, len(DoGet(_REMOTE, '/studies')))
        self.assertEqual(1, len(DoGet(_REMOTE, '/series')))
        self.assertEqual(1, len(DoGet(_REMOTE, '/instances')))

        if IsOrthancVersionAbove(_REMOTE, 1, 11, 1):
            # Reset and test asynchronous C-Move at instance level
            for p in DoGet(_REMOTE, '/patients'):
                DoDelete(_REMOTE, '/patients/%s' % p)

            DoPost(_REMOTE, '/modalities/orthanctest/move', { 
                        'Level' : 'Instance',
                        'Resources' : [
                            { 
                                'StudyInstanceUID' : '2.16.840.1.113669.632.20.1211.10000357775',
                                'SeriesInstanceUID' : '1.3.46.670589.11.0.0.11.4.2.0.8743.5.5396.2006120114285654497',
                                'SOPInstanceUID' : '1.3.46.670589.11.0.0.11.4.2.0.8743.5.5396.2006120114314079549',
                            }
                        ],
                        'Asynchronous': True
                        })

            job = MonitorJob2(_REMOTE, lambda: DoPost
                            (_REMOTE, '/modalities/orthanctest/move', { 
                        'Level' : 'Instance',
                        'Resources' : [
                            { 
                                'StudyInstanceUID' : '2.16.840.1.113669.632.20.1211.10000357775',
                                'SeriesInstanceUID' : '1.3.46.670589.11.0.0.11.4.2.0.8743.5.5396.2006120114285654497',
                                'SOPInstanceUID' : '1.3.46.670589.11.0.0.11.4.2.0.8743.5.5396.2006120114314079549',
                            }
                        ],
                        'Asynchronous': True
                        }))

            self.assertNotEqual(None, job)

            # check the job was successfull
            self.assertEqual(1, len(DoGet(_REMOTE, '/patients')))
            self.assertEqual(1, len(DoGet(_REMOTE, '/studies')))
            self.assertEqual(1, len(DoGet(_REMOTE, '/series')))
            self.assertEqual(1, len(DoGet(_REMOTE, '/instances')))

            # check the job content
            jobContent = DoGet(_REMOTE, '/jobs/%s' % job)['Content']
            self.assertEqual('2.16.840.1.113669.632.20.1211.10000357775', jobContent['Query'][0]['0020,000d'])
            self.assertEqual('1.3.46.670589.11.0.0.11.4.2.0.8743.5.5396.2006120114285654497', jobContent['Query'][0]['0020,000e'])
            self.assertEqual('1.3.46.670589.11.0.0.11.4.2.0.8743.5.5396.2006120114314079549', jobContent['Query'][0]['0008,0018'])

        # Reset and test synchronous C-Move at series level
        for p in DoGet(_REMOTE, '/patients'):
            DoDelete(_REMOTE, '/patients/%s' % p)

        DoPost(_REMOTE, '/modalities/orthanctest/move', { 'Level' : 'Series',
                                                          'Resources' : [
                    { 
                        'StudyInstanceUID' : '2.16.840.1.113669.632.20.1211.10000357775',
                        'SeriesInstanceUID' : '1.3.46.670589.11.0.0.11.4.2.0.8743.5.5396.2006120114285654497',
                        }
                    ]})
        self.assertEqual(1, len(DoGet(_REMOTE, '/patients')))
        self.assertEqual(1, len(DoGet(_REMOTE, '/studies')))
        self.assertEqual(1, len(DoGet(_REMOTE, '/series')))
        self.assertEqual(2, len(DoGet(_REMOTE, '/instances')))

        if IsOrthancVersionAbove(_REMOTE, 1, 11, 1):
            # Reset and test asynchronous C-Move at series level with additional PatientID filter
            for p in DoGet(_REMOTE, '/patients'):
                DoDelete(_REMOTE, '/patients/%s' % p)

            job = MonitorJob2(_REMOTE, lambda: DoPost
                            (_REMOTE, '/modalities/orthanctest/move', { 
                        'Level' : 'Series',
                        'Resources' : [
                            { 
                                'PatientID' : '5Yp0E',
                                'StudyInstanceUID' : '2.16.840.1.113669.632.20.1211.10000357775',
                                'SeriesInstanceUID' : '1.3.46.670589.11.0.0.11.4.2.0.8743.5.5396.2006120114285654497',
                            }
                        ],
                        'Asynchronous': True
                        }))

            self.assertNotEqual(None, job)

            # check the job was successfull
            self.assertEqual(1, len(DoGet(_REMOTE, '/patients')))
            self.assertEqual(1, len(DoGet(_REMOTE, '/studies')))
            self.assertEqual(1, len(DoGet(_REMOTE, '/series')))
            self.assertEqual(2, len(DoGet(_REMOTE, '/instances')))

            # check the job content
            jobContent = DoGet(_REMOTE, '/jobs/%s' % job)['Content']
            self.assertEqual('2.16.840.1.113669.632.20.1211.10000357775', jobContent['Query'][0]['0020,000d'])
            self.assertEqual('1.3.46.670589.11.0.0.11.4.2.0.8743.5.5396.2006120114285654497', jobContent['Query'][0]['0020,000e'])
            self.assertEqual('5Yp0E', jobContent['Query'][0]['0010,0020'])

        # Move series Brainix/Epi/*
        DoPost(_REMOTE, '/modalities/orthanctest/move', { 'Level' : 'Series',
                                                          'Resources' : [
                    { 
                        'StudyInstanceUID' : '2.16.840.1.113669.632.20.1211.10000357775',
                        'SeriesInstanceUID' : '1.3.46.670589.11.0.0.11.4.2.0.8743.5.5396.2006120114314125550',
                        }
                    ]})
        self.assertEqual(1, len(DoGet(_REMOTE, '/patients')))
        self.assertEqual(1, len(DoGet(_REMOTE, '/studies')))
        self.assertEqual(2, len(DoGet(_REMOTE, '/series')))
        self.assertEqual(3, len(DoGet(_REMOTE, '/instances')))

        if IsOrthancVersionAbove(_REMOTE, 1, 11, 1):
            # Move study Knee asynchronously
            job = MonitorJob2(_REMOTE, lambda: DoPost
                            (_REMOTE, '/modalities/orthanctest/move', { 
                        'Level' : 'Study',
                        'Resources' : [
                            { 
                                'StudyInstanceUID' : '2.16.840.1.113669.632.20.121711.10000160881'
                            }
                        ],
                        'Asynchronous': True
                        }))

            self.assertNotEqual(None, job)

            # check the job was successfull
            self.assertEqual(2, len(DoGet(_REMOTE, '/patients')))
            self.assertEqual(2, len(DoGet(_REMOTE, '/studies')))
            self.assertEqual(3, len(DoGet(_REMOTE, '/series')))
            self.assertEqual(4, len(DoGet(_REMOTE, '/instances')))

            # check the job content
            jobContent = DoGet(_REMOTE, '/jobs/%s' % job)['Content']
            self.assertEqual('2.16.840.1.113669.632.20.121711.10000160881', jobContent['Query'][0]['0020,000d'])

        # Reset
        for p in DoGet(_REMOTE, '/patients'):
            DoDelete(_REMOTE, '/patients/%s' % p)

        self.assertEqual(0, len(DoGet(_REMOTE, '/patients')))


        if IsOrthancVersionAbove(_REMOTE, 1, 11, 1):
            # Move all at once asynchronously at PatientLevel
            job = MonitorJob2(_REMOTE, lambda: DoPost(_REMOTE, '/modalities/orthanctest/move', 
                { 
                    'Level' : 'Patient',
                    'Resources' : [
                        { 
                            'PatientID' : '5Yp0E',
                        },
                        { 
                            'PatientID': '887',
                            'PatientName' : 'KNEE',
                        }
                    ],
                    'Synchronous': False
                    }))

            self.assertEqual(2, len(DoGet(_REMOTE, '/patients')))
            self.assertEqual(2, len(DoGet(_REMOTE, '/studies')))
            self.assertEqual(3, len(DoGet(_REMOTE, '/series')))
            self.assertEqual(4, len(DoGet(_REMOTE, '/instances')))



    def test_reconstruct_json(self):
        self.assertEqual(0, len(DoGet(_REMOTE, '/patients')))

        instance = UploadInstance(_REMOTE, 'DummyCT.dcm')['ID']
        first = DoGet(_REMOTE, '/instances/%s/tags' % instance)

        self.assertEqual('TWINOW', first['0008,1010']['Value'])

        if IsOrthancVersionAbove(_REMOTE, 1, 9, 1):
            self.assertEqual(1, len(DoGet(_REMOTE, '/instances/%s/attachments' % instance)))
        else:
            self.assertEqual(2, len(DoGet(_REMOTE, '/instances/%s/attachments' % instance)))

        # Cannot delete the "DICOM" attachment
        self.assertRaises(Exception, lambda: DoDelete(_REMOTE, '/instances/%s/attachments/dicom' % instance))

        # Can delete the "DICOM as JSON" attachment
        if not IsOrthancVersionAbove(_REMOTE, 1, 9, 1):
            r = DoDelete(_REMOTE, '/instances/%s/attachments/dicom-as-json' % instance)
            self.assertTrue(type(r) is dict and len(r) == 0)

        # Only the "DICOM" attachment subsists
        self.assertEqual(1, len(DoGet(_REMOTE, '/instances/%s/attachments' % instance)))

        # Cannot manually reconstruct the "DICOM as JSON" attachment
        self.assertRaises(Exception, lambda: DoPut(_REMOTE, '/patients/%s/attachments/dicom-as-json' % patient, 'hello'))

        # Transparently reconstruct the "DICOM as JSON" attachment
        self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/instances/%s/attachments/dicom-as-json' % instance))
        second = DoGet(_REMOTE, '/instances/%s/tags' % instance)
        self.assertEqual(str(first), str(second))

        if IsOrthancVersionAbove(_REMOTE, 1, 9, 1):
            self.assertEqual(1, len(DoGet(_REMOTE, '/instances/%s/attachments' % instance)))
        else:
            self.assertEqual(2, len(DoGet(_REMOTE, '/instances/%s/attachments' % instance)))
            third = DoGet(_REMOTE, '/instances/%s/attachments/dicom-as-json/data' % instance)
            self.assertEqual(str(first), str(third))


    def test_reconstruct_json2(self):
        self.assertEqual(0, len(DoGet(_REMOTE, '/patients')))

        a = UploadInstance(_REMOTE, 'Brainix/Flair/IM-0001-0001.dcm')['ID']
        b = UploadInstance(_REMOTE, 'Knee/T2/IM-0001-0001.dcm')['ID']

        self.assertEqual('BRAINIX', DoGet(_REMOTE, '/instances/%s/tags?simplify' % a)['PatientName'])
        self.assertEqual('KNEE', DoGet(_REMOTE, '/instances/%s/tags?simplify' % b)['PatientName'])

        aa = DoGet(_REMOTE, '/instances/%s/attachments' % a)
        bb = DoGet(_REMOTE, '/instances/%s/attachments' % b)

        if not IsOrthancVersionAbove(_REMOTE, 1, 9, 1):
            self.assertEqual(2, len(aa))
            self.assertEqual(aa, bb)
            self.assertTrue('dicom' in aa)
            self.assertTrue('dicom-as-json' in aa)
        elif IsDicomUntilPixelDataStored(_REMOTE):
            self.assertEqual(2, len(aa))
            self.assertEqual(aa, bb)
            self.assertTrue('dicom' in aa)
            self.assertTrue('dicom-until-pixel-data' in aa)
        else:
            self.assertEqual(1, len(aa))
            self.assertEqual(aa, bb)
            self.assertTrue('dicom' in aa)

        # In Orthanc <= 1.9.0, this call deletes "dicom-as-json"
        DoPost(_REMOTE, '/tools/invalidate-tags', '', 'text/plain')

        if IsOrthancVersionAbove(_REMOTE, 1, 9, 1) and IsDicomUntilPixelDataStored(_REMOTE):
            self.assertEqual(2, len(DoGet(_REMOTE, '/instances/%s/attachments' % a)))
            self.assertEqual(2, len(DoGet(_REMOTE, '/instances/%s/attachments' % b)))
        else:
            self.assertEqual(1, len(DoGet(_REMOTE, '/instances/%s/attachments' % a)))
            self.assertEqual(1, len(DoGet(_REMOTE, '/instances/%s/attachments' % b)))

        # In Orthanc <= 1.9.0, this call reconstructs "dicom-as-json"
        self.assertEqual('BRAINIX', DoGet(_REMOTE, '/instances/%s/tags?simplify' % a)['PatientName'])
        self.assertEqual('KNEE', DoGet(_REMOTE, '/instances/%s/tags?simplify' % b)['PatientName'])

        if IsOrthancVersionAbove(_REMOTE, 1, 9, 1) and not IsDicomUntilPixelDataStored(_REMOTE):
            self.assertEqual(1, len(DoGet(_REMOTE, '/instances/%s/attachments' % a)))
            self.assertEqual(1, len(DoGet(_REMOTE, '/instances/%s/attachments' % b)))
        else:
            self.assertEqual(2, len(DoGet(_REMOTE, '/instances/%s/attachments' % a)))
            self.assertEqual(2, len(DoGet(_REMOTE, '/instances/%s/attachments' % b)))


    def test_private_tags(self):
        i = UploadInstance(_REMOTE, 'PrivateMDNTags.dcm')['ID']
        t = DoGet(_REMOTE, '/instances/%s/tags?simplify' % i)
        self.assertEqual('1.2.840.113704.1.111.6320.1342451261.21', t['PET-CT Multi Modality Name'])
        self.assertEqual('p37s0_na_ctac.img', t['Original Image Filename'])


    def test_findscu_encoding(self):
        # Check out ../Database/Encodings/Generate.sh
        TEST = u'Test-éüäöòДΘĝדصķћ๛ﾈİ'
        ENCODINGS = {
            'Arabic' :   [ 'ISO_IR 127' ], 
            'Ascii' :    [ 'ISO_IR 6' ],   # More accurately, ISO 646
            'Cyrillic' : [ 'ISO_IR 144' ], 
            'Greek' :    [ 'ISO_IR 126' ], 
            'Hebrew' :   [ 'ISO_IR 138' ],
            'Japanese' : [ 'ISO_IR 13', 'shift-jis' ],
            'Latin1' :   [ 'ISO_IR 100' ],
            'Latin2' :   [ 'ISO_IR 101' ], 
            'Latin3' :   [ 'ISO_IR 109' ],
            'Latin4' :   [ 'ISO_IR 110' ], 
            'Latin5' :   [ 'ISO_IR 148' ], 
            'Thai' :     [ 'ISO_IR 166', 'tis-620' ],
            'Utf8' :     [ 'ISO_IR 192' ],
        }

        for name in ENCODINGS.iterkeys():
            if len(ENCODINGS[name]) == 1:
                ENCODINGS[name].append(name.lower())

        UploadInstance(_REMOTE, 'Encodings/Lena-utf8.dcm')
        
        for name in ENCODINGS.iterkeys():
            self.assertEqual(name, DoPut(_REMOTE, '/tools/default-encoding', name))
            self.assertEqual(name, DoGet(_REMOTE, '/tools/default-encoding'))

            i = CallFindScu([ '-k', '0008,0052=STUDY', 
                              '-k', 'SpecificCharacterSet',  
                              '-k', 'PatientName' ])

            characterSet = re.findall('\(0008,0005\).*?\[(.*?)\]', i)
            self.assertEqual(1, len(characterSet))
            self.assertEqual(ENCODINGS[name][0], characterSet[0].strip())

            patientName = re.findall('\(0010,0010\).*?\[(.*?)\]', i)
            self.assertEqual(1, len(patientName))

            expected = TEST.encode(ENCODINGS[name][1], 'ignore')
            self.assertEqual(expected, patientName[0].strip())


        #for master in ENCODINGS:
        for master in [ 'Latin1', 'Utf8', 'Cyrillic' ]:  # Shortcut to speedup tests
            self.assertEqual(master, DoPut(_REMOTE, '/tools/default-encoding', master))
            self.assertEqual(master, DoGet(_REMOTE, '/tools/default-encoding'))

            for name in ENCODINGS:
                DropOrthanc(_REMOTE)
                UploadInstance(_REMOTE, 'Encodings/Lena-%s.dcm' % ENCODINGS[name][1])

                i = CallFindScu([ '-k', '0008,0052=STUDY', 
                                  '-k', 'PatientID', 
                                  '-k', 'SpecificCharacterSet',  
                                  '-k', 'PatientName' ])
                i = i.decode(ENCODINGS[master][1])

                characterSet = re.findall('\(0008,0005\).*?\[(.*?)\]', i)
                self.assertEqual(1, len(characterSet))
                self.assertEqual(ENCODINGS[master][0], characterSet[0].strip())

                patientId = re.findall('\(0010,0020\).*?\[(.*?)\]', i)
                self.assertEqual(1, len(patientId))
                self.assertEqual(ENCODINGS[name][1], patientId[0].strip())

                patientName = re.findall('\(0010,0010\).*?\[(.*?)\]', i)
                self.assertEqual(1, len(patientName))

                tmp = ENCODINGS[name][1]
                expected = TEST.encode(tmp, 'ignore').decode(tmp)
                tmp = ENCODINGS[master][1]
                expected = expected.encode(tmp, 'ignore').decode(tmp)

                self.assertEqual(expected, patientName[0].strip())


                a = DoPost(_REMOTE, '/tools/find', { 'Expand' : True,
                                                     'Level' : 'Study',
                                                     'Query' : { }})
                self.assertEqual(1, len(a))

                tmp = ENCODINGS[name][1]
                self.assertEqual(TEST.encode(tmp, 'ignore').decode(tmp), a[0]["PatientMainDicomTags"]["PatientName"])


    def test_reconstruct(self):
        def CompareMainDicomTag(expected, instance, level, tag):
            self.assertEqual(expected, DoGet(_REMOTE, '/instances/%s/%s' % (instance, level))['MainDicomTags'][tag].strip())

        originalInstanceId = UploadInstance(_REMOTE, 'DummyCT.dcm')['ID']

        studies = DoGet(_REMOTE, '/studies/')
        self.assertEqual(1, len(DoGet(_REMOTE, '/patients/')))
        self.assertEqual(1, len(studies))
        self.assertEqual(1, len(DoGet(_REMOTE, '/series/')))
        self.assertEqual(1, len(DoGet(_REMOTE, '/instances/')))

        modified = DoPost(_REMOTE, '/studies/%s/modify' % studies[0], {
            "Replace" : {
                "StudyDescription" : "hello",
                "SeriesDescription" : "world",
                "SOPClassUID" : "test",
                "SOPInstanceUID" : "myid",
            },
            "Keep" : [ "StudyInstanceUID", "SeriesInstanceUID" ],
            "Force" : True
        })

        instances = DoGet(_REMOTE, '/instances/')
        self.assertEqual(1, len(DoGet(_REMOTE, '/patients/')))
        self.assertEqual(1, len(DoGet(_REMOTE, '/studies/')))
        self.assertEqual(1, len(DoGet(_REMOTE, '/series/')))
        self.assertEqual(2, len(instances))

        modifiedInstanceId = instances[0] if instances[1] == originalInstanceId else instances[1]

        # in 1.11.3, we have added an automatic reconstruction at the end of the modification
        if not IsOrthancVersionAbove(_REMOTE, 1, 11, 3):
            CompareMainDicomTag('Knee (R)', originalInstanceId, 'study', 'StudyDescription')
            CompareMainDicomTag('AX.  FSE PD', originalInstanceId, 'series', 'SeriesDescription')
            CompareMainDicomTag('1.2.840.113619.2.176.2025.1499492.7040.1171286242.109', originalInstanceId, '', 'SOPInstanceUID')
            CompareMainDicomTag('myid', modifiedInstanceId, '', 'SOPInstanceUID')
            self.assertEqual('1.2.840.10008.5.1.4.1.1.4', DoGet(_REMOTE, '/instances/%s/metadata/SopClassUid' % originalInstanceId).strip())
            self.assertEqual('test', DoGet(_REMOTE, '/instances/%s/metadata/SopClassUid' % modifiedInstanceId).strip())

            if IsOrthancVersionAbove(_REMOTE, 1, 11, 0):
                # metadata before reconstruct
                mba = DoGet(_REMOTE, '/instances/%s/metadata?expand' % originalInstanceId)
                mbb = DoGet(_REMOTE, '/instances/%s/metadata?expand' % originalInstanceId)

            # reconstruct by taking the new instance as the reference -> should repopulate study fields from this instance tags
            DoPost(_REMOTE, '/instances/%s/reconstruct' % modifiedInstanceId, {})

        CompareMainDicomTag('hello', originalInstanceId, 'study', 'StudyDescription')
        CompareMainDicomTag('world', originalInstanceId, 'series', 'SeriesDescription')
        CompareMainDicomTag('1.2.840.113619.2.176.2025.1499492.7040.1171286242.109', originalInstanceId, '', 'SOPInstanceUID')

        if not IsOrthancVersionAbove(_REMOTE, 1, 11, 3):
            if IsOrthancVersionAbove(_REMOTE, 1, 11, 0):
                # metadata after reconstruct should have been preserved
                maa = DoGet(_REMOTE, '/instances/%s/metadata?expand' % originalInstanceId)
                mab = DoGet(_REMOTE, '/instances/%s/metadata?expand' % originalInstanceId)

                self.assertEqual(mba, maa)
                self.assertEqual(mbb, mab)


    @unittest.skip("httpbin.org is down as of 2022-12-22")  # TODO
    def test_httpClient_lua(self):
        retries = 4
        result = ''
        
        with open(GetDatabasePath('Lua/HttpClient.lua'), 'r') as f:
            scriptContent = f.read()
            # retry since this test sometimes fails if httpbin.org is unresponsive
            while retries > 0 and not ('OK' in result):
                print("Executing lua script HttpClient.lua")
                result = DoPost(_REMOTE, '/tools/execute-script', scriptContent, 'application/lua')
                retries -= 1

        self.assertIn('OK', result)


    def test_bitbucket_issue_44(self):
        # https://bugs.orthanc-server.com/show_bug.cgi?id=44
        UploadInstance(_REMOTE, 'Issue44/Monochrome1.dcm')
        UploadInstance(_REMOTE, 'Issue44/Monochrome2.dcm')

        # dcmcjpeg +ua +eb Monochrome1.dcm Monochrome1-Jpeg.dcm
        UploadInstance(_REMOTE, 'Issue44/Monochrome1-Jpeg.dcm')

        # dcmcjpeg +ua Monochrome1.dcm Monochrome1-JpegLS.dcm
        UploadInstance(_REMOTE, 'Issue44/Monochrome1-JpegLS.dcm')

        monochrome1 = 'bcdd600a-a6a9c522-5f0a6e84-8657c9f3-b76e59b7'
        monochrome1_jpeg = '9df82121-208a2da8-0038674a-3d7a773b-b7008cd2'
        monochrome1_jpegls = '0486d1a2-9165573f-b1976b20-e927b016-6b8d67ab'
        monochrome2 = 'f00947b7-f61f7164-c93414d1-c6fbda6a-9e92ed20'

        for i in [ monochrome1, monochrome1_jpeg, monochrome1_jpegls ]:
            im = GetImage(_REMOTE, '/instances/%s/preview' % i)
            self.assertEqual("L", im.mode)
            self.assertEqual(2010, im.size[0])
            self.assertEqual(2446, im.size[1])

            # This is the chest image, with MONOCHROME1. Raw background is
            # white (255), should be rendered as black (0) => invert
            if i == monochrome1_jpeg:
                # Add some tolerance because of JPEG destructive compression
                self.assertGreater(10, im.getpixel((0,0)))
            else:
                self.assertEqual(0, im.getpixel((0,0)))

        im = GetImage(_REMOTE, '/instances/%s/preview' % monochrome2)
        self.assertEqual("L", im.mode)
        self.assertEqual(1572, im.size[0])
        self.assertEqual(2010, im.size[1])
        
        # This is the key image, with MONOCHROME2. Raw background is
        # white (255), should be rendered as white (255)
        self.assertEqual(255, im.getpixel((0,0)))


    def test_bitbucket_issue_42(self):
        # https://bugs.orthanc-server.com/show_bug.cgi?id=42
        # This test fails on DCMTK 3.6.0, but succeeds in DCMTK 3.6.1 snapshots and DCMTK 3.6.2
        UploadInstance(_REMOTE, 'Issue42.dcm')['ID']
        modified = DoPost(_REMOTE,
                          '/patients/da128605-e040d0c4-310615d2-3475da63-df2d1ef4/modify',
                          '{"Replace":{"PatientID":"Hello","PatientName":"Sample patient name"},"Force":true}',
                          'application/json')
        self.assertTrue('PatientID' in modified)


    def test_rest_find_limit(self):
        # Check the "Since" and "Limit" parameters in URI "/tools/find"
        # Related to issue 53: https://bugs.orthanc-server.com/show_bug.cgi?id=53
        
        # Upload 6 instances
        brainix = []
        knee = []
        for i in range(2):
            brainix.append(UploadInstance(_REMOTE, 'Brainix/Flair/IM-0001-000%d.dcm' % (i + 1)) ['ID'])
            brainix.append(UploadInstance(_REMOTE, 'Brainix/Epi/IM-0001-000%d.dcm' % (i + 1)) ['ID'])
            knee.append(UploadInstance(_REMOTE, 'Knee/T1/IM-0001-000%d.dcm' % (i + 1)) ['ID'])

        # Check using BRAINIX
        # The tests below correspond to "isSimpleLookup_ == true" in "ResourceFinder"
        a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Instance',
                                             'Query' : { 'PatientName' : 'B*' },
                                             'Limit' : 10 })
        self.assertEqual(4, len(a))

        a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Instance',
                                             'Query' : { 'PatientName' : 'B*' },
                                             'Limit' : 4 })
        self.assertEqual(4, len(a))

        if HasExtendedFind(_REMOTE):  # usage of since is not reliable without ExtendedFind
            a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Instance',
                                                'Query' : { 'PatientName' : 'B*' },
                                                'Since' : 2,
                                                'Limit' : 4 })
            self.assertEqual(2, len(a))

        a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Instance',
                                             'Query' : { 'PatientName' : 'B*' },
                                             'Limit' : 3 })
        self.assertEqual(3, len(a))

        a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Instance',
                                             'Query' : { 'PatientName' : 'B*' },
                                             'Limit' : 0 })  # This is an arbitrary convention
        self.assertEqual(4, len(a))

        if HasExtendedFind(_REMOTE):  # usage of since is not reliable without ExtendedFind
            b = []
            for i in range(4):
                a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Instance',
                                                    'Query' : { 'PatientName' : 'B*' },
                                                    'Limit' : 1,
                                                    'Since' : i })
                self.assertEqual(1, len(a))
                b.append(a[0])

            # Check whether the two sets are equal through symmetric difference
            self.assertEqual(0, len(set(b) ^ set(brainix)))

            a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Instance',
                                                'Query' : { 'PatientName' : 'B*' },
                                                'Limit' : 1,
                                                'Since' : 4 })
            self.assertEqual(0, len(a))

        # Check using KNEE
        a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Instance',
                                             'Query' : { 'PatientName' : 'K*' },
                                             'Limit' : 10 })
        self.assertEqual(2, len(a))

        a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Instance',
                                             'Query' : { 'PatientName' : 'K*' },
                                             'Limit' : 2 })
        self.assertEqual(2, len(a))

        if HasExtendedFind(_REMOTE):  # usage of since is not reliable without ExtendedFind
            b = []
            for i in range(2):
                a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Instance',
                                                    'Query' : { 'PatientName' : 'K*' },
                                                    'Limit' : 1,
                                                    'Since' : i })
                self.assertEqual(1, len(a))
                b.append(a[0])

            self.assertEqual(0, len(set(b) ^ set(knee)))

        # Now test "isSimpleLookup_ == false"
        a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Series',
                                             'Query' : { 'PatientPosition' : '*' }})
        self.assertEqual(3, len(a))

        # TODO: remove these tests for good once 1.12.5 is out
        # if not HasExtendedFind(_REMOTE):  # once you have ExtendedFind, usage of Limit and Since is forbidden when filtering on tags that are not in DB because that's just impossible to use on real life DB !


        #     b = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Series',
        #                                         'Query' : { 'PatientPosition' : '*' },
        #                                         'Limit' : 0})
        #     self.assertEqual(3, len(b))
        #     self.assertEqual(a[0], b[0])
        #     self.assertEqual(a[1], b[1])
        #     self.assertEqual(a[2], b[2])

        #     b = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Series',
        #                                         'Query' : { 'PatientPosition' : '*' },
        #                                         'Limit' : 1})
        #     self.assertEqual(1, len(b))
        #     self.assertEqual(a[0], b[0])

        #     b = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Series',
        #                                         'Query' : { 'PatientPosition' : '*' },
        #                                         'Since' : 0,
        #                                         'Limit' : 1})
        #     self.assertEqual(1, len(b))
        #     self.assertEqual(a[0], b[0])

        #     b = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Series',
        #                                         'Query' : { 'PatientPosition' : '*' },
        #                                         'Since' : 0,
        #                                         'Limit' : 3})
        #     self.assertEqual(3, len(b))
        #     self.assertEqual(a[0], b[0])
        #     self.assertEqual(a[1], b[1])
        #     self.assertEqual(a[2], b[2])

        #     b = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Series',
        #                                         'Query' : { 'PatientPosition' : '*' },
        #                                         'Since' : 0,
        #                                         'Limit' : 4})
        #     self.assertEqual(3, len(b))
        #     self.assertEqual(a[0], b[0])
        #     self.assertEqual(a[1], b[1])
        #     self.assertEqual(a[2], b[2])

        #     b = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Series',
        #                                         'Query' : { 'PatientPosition' : '*' },
        #                                         'Since' : 1,
        #                                         'Limit' : 1})
        #     self.assertEqual(1, len(b))
        #     self.assertEqual(a[1], b[0])

        #     b = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Series',
        #                                         'Query' : { 'PatientPosition' : '*' },
        #                                         'Since' : 1,
        #                                         'Limit' : 2})
        #     self.assertEqual(2, len(b))
        #     self.assertEqual(a[1], b[0])
        #     self.assertEqual(a[2], b[1])

        #     b = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Series',
        #                                         'Query' : { 'PatientPosition' : '*' },
        #                                         'Since' : 1,
        #                                         'Limit' : 3})
        #     self.assertEqual(2, len(b))
        #     self.assertEqual(a[1], b[0])
        #     self.assertEqual(a[2], b[1])

        #     b = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Series',
        #                                         'Query' : { 'PatientPosition' : '*' },
        #                                         'Since' : 2,
        #                                         'Limit' : 1})
        #     self.assertEqual(1, len(b))
        #     self.assertEqual(a[2], b[0])

        #     b = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Series',
        #                                         'Query' : { 'PatientPosition' : '*' },
        #                                         'Since' : 2,
        #                                         'Limit' : 2})
        #     self.assertEqual(1, len(b))
        #     self.assertEqual(a[2], b[0])

        #     b = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Series',
        #                                         'Query' : { 'PatientPosition' : '*' },
        #                                         'Since' : 3,
        #                                         'Limit' : 1})
        #     self.assertEqual(0, len(b))

        #     b = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Series',
        #                                         'Query' : { 'PatientPosition' : '*' },
        #                                         'Since' : 3,
        #                                         'Limit' : 10})
        #     self.assertEqual(0, len(b))


    def test_bitbucket_issue_46(self):
        # "PHI remaining after anonymization"
        # https://bugs.orthanc-server.com/show_bug.cgi?id=46

        def GetAnonymizedTags(study, version):
            anonymized = DoPost(_REMOTE, '/studies/%s/anonymize' % study,
                                { 'DicomVersion' : version },
                                'application/json') ['ID']
            a = DoGet(_REMOTE, '/studies/%s/instances' % anonymized)
            self.assertEqual(1, len(a))

            instance = a[0]['ID']
            
            return (instance, DoGet(_REMOTE, '/instances/%s/tags' % instance))

        UploadInstance(_REMOTE, 'Issue44/Monochrome1.dcm')
        origStudy = '6068a14b-d4df27af-9ec22145-538772d8-74f228ff'

        # Add the 0032,1033 (Requesting Service) and the 0010,1060
        # (Patient's Mother's Birth Name) tags
        newStudy = DoPost(_REMOTE, '/studies/%s/modify' % origStudy,
                          '{"Replace":{"0010,1060":"OSIMIS","0032,1033":"MOTHER"}}',
                          'application/json')['ID']

        # Use Table E.1-1 from PS 3.15-2008
        # https://raw.githubusercontent.com/jodogne/dicom-specification/master/2008/08_15pu.pdf
        (instance, tags) = GetAnonymizedTags(newStudy, "2008")
        self.assertTrue('0032,1033' in tags)
        self.assertTrue('0010,1060' in tags)

        # Use Table E.1-1 from PS 3.15-2011 (only if Orthanc >= 1.2.1)
        # https://raw.githubusercontent.com/jodogne/dicom-specification/master/2008/08_15pu.pdf
        (instance, tags) = GetAnonymizedTags(newStudy, "2017c")
        self.assertFalse('0032,1033' in tags)
        self.assertFalse('0010,1060' in tags)

        t = {}
        for (key, value) in tags.iteritems():
            t[value['Name']] = value['Value']

        self.assertEqual('', t['StudyDate'])  # Type 1 tag => cleared
        self.assertEqual('', t['StudyTime'])  # Type 1 tag => cleared
        self.assertEqual('', t['PatientSex']) # Type 1 tag => cleared
        self.assertFalse('SeriesDate' in t)   # Type 3 tag => null
        self.assertFalse('SeriesTime' in t)   # Type 3 tag => null

        with tempfile.NamedTemporaryFile(delete = True) as f:
            # Run "dciodvfy" on the anonymized file to be sure it is still valid
            f.write(DoGet(_REMOTE, '/instances/%s/file' % instance))
            f.flush()
            subprocess.check_output([ FindExecutable('dciodvfy'), f.name ],
                                    stderr = subprocess.STDOUT).split('\n')


    def test_bitbucket_issue_55(self):
        def Run(modify, query):
            self.assertEqual(1, len(DoGet(_REMOTE, '/instances')))

            operation = 'modify' if modify else 'anonymize'
            
            self.assertRaises(Exception, lambda: DoPost(
                _REMOTE, '/studies/%s/%s' % (study, operation), query))
            self.assertEqual(1, len(DoGet(_REMOTE, '/instances')))

            query["Force"] = True
            a = DoPost(_REMOTE, '/studies/%s/%s' % (study, operation), query)['Path']
            self.assertEqual(2, len(DoGet(_REMOTE, '/instances')))
            DoDelete(_REMOTE, a)
                         
            self.assertEqual(1, len(DoGet(_REMOTE, '/instances')))
        
        UploadInstance(_REMOTE, 'DummyCT.dcm')
        study = 'b9c08539-26f93bde-c81ab0d7-bffaf2cb-a4d0bdd0'

        Run(True, { "Replace" : { "StudyInstanceUID" : "world" } })
        Run(True, { "Replace" : { "SeriesInstanceUID" : "world" } })
        Run(True, { "Replace" : { "SOPInstanceUID" : "world" } })

        Run(False, { "Keep" : [ "StudyInstanceUID" ]})
        Run(False, { "Keep" : [ "SeriesInstanceUID" ]})
        Run(False, { "Keep" : [ "SOPInstanceUID" ]})

        Run(False, { "Replace" : { "StudyInstanceUID" : "world" } })
        Run(False, { "Replace" : { "SeriesInstanceUID" : "world" } })
        Run(False, { "Replace" : { "SOPInstanceUID" : "world" } })


    def test_bitbucket_issue_56(self):
        # Case-insensitive matching over accents. This test assumes
        # that the "CaseSensitivePN" configuration option of Orthanc
        # is set to "false" (default value).
        # https://bugs.orthanc-server.com/show_bug.cgi?id=56

        def Check(name, expected, expectedSensitive):
            a = CallFindScu([ '-k', '0008,0005=ISO_IR 192',  # Use UTF-8
                              '-k', '0008,0052=PATIENT',
                              '-k', 'PatientName=%s' % name ])
            patientNames = re.findall('\(0010,0010\).*?\[(.*?)\]', a)
            self.assertEqual(expected, len(patientNames))

            a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Patient',
                                                 'CaseSensitive' : False,
                                                 'Query' : { 'PatientName' : name }})
            self.assertEqual(expected, len(a))

            a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Patient',
                                                 'CaseSensitive' : True,
                                                 'Query' : { 'PatientName' : name }})
            self.assertEqual(expectedSensitive, len(a))

        # SpecificCharacterSet = ISO_IR 100 (Latin1), PatientName=Test-éüäöò
        UploadInstance(_REMOTE, 'Encodings/Lena-latin1.dcm')

        # WildcardConstraint
        Check('TeSt*', 1, 0)
        Check('TeSt-a*', 0, 0)
        Check('TeSt-É*', 1, 0)
        Check('TeSt-é*', 1, 0)
        Check('Test-é*', 1, 1)

        # ListConstraint
        Check('Test-éüäöò\\nope', 1, 1)
        Check('Test-ÉÜÄÖÒ\\nope', 1, 0)

        # ValueConstraint
        Check('Test-éüäöò', 1, 1)
        Check('Test-ÉÜÄÖÒ', 1, 0)

        
    def test_gbk_alias(self):
        # https://groups.google.com/d/msg/orthanc-users/WMM8LMbjpUc/02-1f_yFCgAJ
        # This test fails on Orthanc <= 1.3.0
        i = UploadInstance(_REMOTE, '2017-09-19-GBK-Tumashu.dcm')['ID']
        tags = DoGet(_REMOTE, '/instances/%s/tags?simplify' % i)
        self.assertEqual(tags['PatientName'], u'徐浩凯')
        self.assertEqual(tags['InstitutionName'], u'灌云县疾病预防控制中心')

        
    def test_long_tag(self):
        i = UploadInstance(_REMOTE, 'DummyCTWithLongTag.dcm')['ID']
        series = 'f2635388-f01d497a-15f7c06b-ad7dba06-c4c599fe'

        tags = DoGet(_REMOTE, '/instances/%s/tags' % i)
        self.assertTrue('0018,1020' in tags)
        self.assertEqual('SoftwareVersions', tags['0018,1020']['Name'])
        self.assertEqual('TooLong', tags['0018,1020']['Type'])
        self.assertEqual(None, tags['0018,1020']['Value'])

        tags = DoGet(_REMOTE, '/instances/%s/tags?ignore-length=0018-1020' % i)
        self.assertTrue('0018,1020' in tags)
        self.assertEqual('SoftwareVersions', tags['0018,1020']['Name'])
        self.assertEqual('String', tags['0018,1020']['Type'])
        self.assertTrue(tags['0018,1020']['Value'].startswith('Lorem ipsum dolor sit amet'))

        tags = DoGet(_REMOTE, '/instances/%s/tags?simplify' % i)
        self.assertTrue('SoftwareVersions' in tags)
        self.assertEqual(None, tags['SoftwareVersions'])
        self.assertTrue('HeartRate' in tags)
        self.assertEqual(474, int(tags['HeartRate']))

        tags = DoGet(_REMOTE, '/instances/%s/simplified-tags' % i)
        self.assertTrue('SoftwareVersions' in tags)
        self.assertEqual(None, tags['SoftwareVersions'])

        tags = DoGet(_REMOTE, '/instances/%s/tags?simplify&ignore-length=0018-1020' % i)
        self.assertTrue('SoftwareVersions' in tags)
        self.assertTrue(tags['SoftwareVersions'].startswith('Lorem ipsum dolor sit amet'))

        tags = DoGet(_REMOTE, '/instances/%s/tags?simplify&ignore-length=SoftwareVersions' % i)
        self.assertTrue('SoftwareVersions' in tags)
        self.assertTrue(tags['SoftwareVersions'].startswith('Lorem ipsum dolor sit amet'))

        tags = DoGet(_REMOTE, '/series/%s/instances-tags' % series)
        self.assertEqual(1, len(tags))
        self.assertTrue(i in tags.keys())
        self.assertTrue('0018,1020' in tags[i])
        self.assertEqual('TooLong', tags[i]['0018,1020']['Type'])

        tags = DoGet(_REMOTE, '/series/%s/instances-tags?ignore-length=SoftwareVersions' % series)
        self.assertEqual(1, len(tags))
        self.assertTrue(i in tags.keys())
        self.assertTrue('0018,1020' in tags[i])
        self.assertEqual('String', tags[i]['0018,1020']['Type'])
        self.assertTrue(tags[i]['0018,1020']['Value'].startswith('Lorem ipsum dolor sit amet'))


    def test_extended_media(self):
        UploadInstance(_REMOTE, 'Knee/T1/IM-0001-0001.dcm')

        z, resp = GetArchive(_REMOTE, '/patients/%s/media?extended' % DoGet(_REMOTE, '/patients')[0])
        self.assertEqual(2, len(z.namelist()))
        self.assertTrue('IMAGES/IM0' in z.namelist())
        self.assertTrue('DICOMDIR' in z.namelist())

        try:
            os.remove('/tmp/DICOMDIR')
        except:
            # The file does not exist
            pass

        z.extract('DICOMDIR', '/tmp')
        a = subprocess.check_output([ FindExecutable('dciodvfy'), '/tmp/DICOMDIR' ],
                                    stderr = subprocess.STDOUT).split('\n')
        self.assertEqual(5, len(a))
        self.assertTrue(a[0].startswith('Warning'))
        self.assertEqual('BasicDirectory', a[1])
        self.assertTrue('not present in standard DICOM IOD' in a[2])
        self.assertTrue('not present in standard DICOM IOD' in a[3])
        self.assertEqual('', a[4])

        a = subprocess.check_output([ FindExecutable('dcentvfy'), '/tmp/DICOMDIR' ],
                                    stderr = subprocess.STDOUT).split('\n')
        self.assertEqual(1, len(a))
        self.assertEqual('', a[0])

        a = subprocess.check_output([ FindExecutable('dcm2xml'), '/tmp/DICOMDIR' ])
        self.assertTrue(re.search('1.3.46.670589.11.17521.5.0.3124.2008081908590448738', a) != None)

        # Check the presence of the series description (extended tag)
        self.assertTrue(re.search('T1W_aTSE', a) != None)

        os.remove('/tmp/DICOMDIR')


    def test_anonymize_relationships_1(self):
        UploadInstance(_REMOTE, 'Knee/T1/IM-0001-0001.dcm')
        UploadInstance(_REMOTE, 'Knee/T1/IM-0001-0002.dcm')
        study = '0a9b3153-2512774b-2d9580de-1fc3dcf6-3bd83918'
        
        anonymized = DoPost(_REMOTE, '/studies/%s/anonymize' % study,
                            '{}',
                            'application/json')['ID']
        
        a = DoGet(_REMOTE, '/studies/%s/instances' % study)
        self.assertEqual(2, len(a))
        a1 = a[0]['ID']
        a2 = a[1]['ID']
        
        b = DoGet(_REMOTE, '/studies/%s/instances' % anonymized)
        self.assertEqual(2, len(b))
        b1 = b[0]['ID']
        b2 = b[1]['ID']
        
        SEQUENCE = '/instances/%s/content/ReferencedImageSequence'
        SOP = '/instances/%s/content/ReferencedImageSequence/%d/ReferencedSOPInstanceUID'
        CLASS = '/instances/%s/content/ReferencedImageSequence/%d/ReferencedSOPClassUID'
        FRAME = '/instances/%s/content/FrameOfReferenceUID'

        self.assertEqual(DoGet(_REMOTE, FRAME % a1), 
                         DoGet(_REMOTE, FRAME % a2))
        self.assertEqual(DoGet(_REMOTE, FRAME % b1), 
                         DoGet(_REMOTE, FRAME % b2))
        self.assertNotEqual(DoGet(_REMOTE, FRAME % a1),
                            DoGet(_REMOTE, FRAME % b1))
        self.assertNotEqual(DoGet(_REMOTE, FRAME % a2),
                            DoGet(_REMOTE, FRAME % b2))

        self.assertEqual(3, len(DoGet(_REMOTE, SEQUENCE % a1)))
        self.assertEqual(3, len(DoGet(_REMOTE, SEQUENCE % a2)))
        self.assertEqual(3, len(DoGet(_REMOTE, SEQUENCE % b1)))
        self.assertEqual(3, len(DoGet(_REMOTE, SEQUENCE % b2)))

        for i in range(3):
            self.assertEqual(DoGet(_REMOTE, SOP % (a1, i)),
                             DoGet(_REMOTE, SOP % (a2, i)))
            self.assertEqual(DoGet(_REMOTE, SOP % (b1, i)),
                             DoGet(_REMOTE, SOP % (b2, i)))
            self.assertNotEqual(DoGet(_REMOTE, SOP % (a1, i)),
                                DoGet(_REMOTE, SOP % (b1, i)))
            self.assertNotEqual(DoGet(_REMOTE, SOP % (a2, i)),
                                DoGet(_REMOTE, SOP % (b2, i)))
            self.assertEqual(DoGet(_REMOTE, CLASS % (a1, i)),
                             DoGet(_REMOTE, CLASS % (b1, i)))
            self.assertEqual(DoGet(_REMOTE, CLASS % (a2, i)),
                             DoGet(_REMOTE, CLASS % (b2, i)))


    def test_anonymize_relationships_2(self):
        UploadInstance(_REMOTE, 'Comunix/Ct/IM-0001-0001.dcm')
        UploadInstance(_REMOTE, 'Comunix/Ct/IM-0001-0002.dcm')
        study = '6c65289b-db2fcb71-7eaf73f4-8e12470c-a4d6d7cf'
        
        anonymized = DoPost(_REMOTE, '/studies/%s/anonymize' % study,
                            '{}',
                            'application/json')['ID']
        
        a = DoGet(_REMOTE, '/studies/%s/instances' % study)
        self.assertEqual(2, len(a))
        a1 = a[0]['ID']
        a2 = a[1]['ID']
        
        b = DoGet(_REMOTE, '/studies/%s/instances' % anonymized)
        self.assertEqual(2, len(b))
        b1 = b[0]['ID']
        b2 = b[1]['ID']
        
        SEQUENCE = '/instances/%s/content/SourceImageSequence'
        SOP = '/instances/%s/content/SourceImageSequence/%d/ReferencedSOPInstanceUID'
        CLASS = '/instances/%s/content/SourceImageSequence/%d/ReferencedSOPClassUID'

        self.assertEqual(1, len(DoGet(_REMOTE, SEQUENCE % a1)))
        self.assertEqual(1, len(DoGet(_REMOTE, SEQUENCE % a2)))
        self.assertEqual(1, len(DoGet(_REMOTE, SEQUENCE % b1)))
        self.assertEqual(1, len(DoGet(_REMOTE, SEQUENCE % b2)))
        self.assertEqual(DoGet(_REMOTE, SOP % (a1, 0)),
                         DoGet(_REMOTE, SOP % (a2, 0)))
        self.assertEqual(DoGet(_REMOTE, SOP % (b1, 0)),
                         DoGet(_REMOTE, SOP % (b2, 0)))
        self.assertNotEqual(DoGet(_REMOTE, SOP % (a1, 0)),
                            DoGet(_REMOTE, SOP % (b1, 0)))
        self.assertNotEqual(DoGet(_REMOTE, SOP % (a2, 0)),
                            DoGet(_REMOTE, SOP % (b2, 0)))
        self.assertEqual(DoGet(_REMOTE, CLASS % (a1, 0)),
                         DoGet(_REMOTE, CLASS % (b1, 0)))
        self.assertEqual(DoGet(_REMOTE, CLASS % (a2, 0)),
                         DoGet(_REMOTE, CLASS % (b2, 0)))


    def test_anonymize_relationships_3(self):
        sr1 = UploadInstance(_REMOTE, 'HierarchicalAnonymization/StructuredReports/IM0')['ID']
        mr1 = UploadInstance(_REMOTE, 'HierarchicalAnonymization/StructuredReports/IM631')['ID']
        study = 'ef351eb2-c1147229-062736b8-35a151e3-e32d526b'
        
        anonymized = DoPost(_REMOTE, '/studies/%s/anonymize' % study,
                            { "Keep" : [ "ContentSequence" ] }) ['ID']
                
        a = DoGet(_REMOTE, '/studies/%s/instances' % anonymized)
        self.assertEqual(2, len(a))

        if DoGet(_REMOTE, '/instances/%s/content/Modality' % a[0]['ID']) == 'SR':
            sr2 = a[0]['ID']
            mr2 = a[1]['ID']
        else:
            sr2 = a[1]['ID']
            mr2 = a[0]['ID']
            
        self.assertEqual(DoGet(_REMOTE, '/instances/%s/content/Modality' % sr1),
                         DoGet(_REMOTE, '/instances/%s/content/Modality' % sr2))
        self.assertEqual(DoGet(_REMOTE, '/instances/%s/content/Modality' % mr1),
                         DoGet(_REMOTE, '/instances/%s/content/Modality' % mr2))

        mrUid1 = DoGet(_REMOTE, '/instances/%s' % mr1)['MainDicomTags']['SOPInstanceUID']
        mrUid2 = DoGet(_REMOTE, '/instances/%s' % mr2)['MainDicomTags']['SOPInstanceUID']
        mrSeries1 = DoGet(_REMOTE, '/instances/%s/content/SeriesInstanceUID' % mr1).strip('\x00')
        mrSeries2 = DoGet(_REMOTE, '/instances/%s/content/SeriesInstanceUID' % mr2).strip('\x00')
        mrStudy1 = DoGet(_REMOTE, '/instances/%s/content/StudyInstanceUID' % mr1).strip('\x00')
        mrStudy2 = DoGet(_REMOTE, '/instances/%s/content/StudyInstanceUID' % mr2).strip('\x00')

        PATH1 = '/instances/%s/content/CurrentRequestedProcedureEvidenceSequence'
        PATH2 = PATH1 + '/0/ReferencedSeriesSequence'
        PATH3 = PATH2 + '/0/ReferencedSOPSequence'
        PATH4 = PATH3 + '/0/ReferencedSOPInstanceUID'
        PATH5 = PATH3 + '/0/ReferencedSOPClassUID'

        self.assertEqual(1, len(DoGet(_REMOTE, PATH1 % sr1)))
        self.assertEqual(1, len(DoGet(_REMOTE, PATH2 % sr1)))
        self.assertEqual(1, len(DoGet(_REMOTE, PATH3 % sr1)))
        self.assertEqual(DoGet(_REMOTE, PATH4 % sr1), mrUid1)
        self.assertEqual(mrSeries1, DoGet(_REMOTE, (PATH2 + '/0/SeriesInstanceUID') % sr1).strip('\x00'))
        self.assertEqual(mrStudy1, DoGet(_REMOTE, (PATH1 + '/0/StudyInstanceUID') % sr1).strip('\x00'))

        self.assertEqual(1, len(DoGet(_REMOTE, PATH1 % sr2)))
        self.assertEqual(1, len(DoGet(_REMOTE, PATH2 % sr2)))
        self.assertEqual(1, len(DoGet(_REMOTE, PATH3 % sr2)))
        self.assertEqual(DoGet(_REMOTE, PATH5 % sr1), DoGet(_REMOTE, PATH5 % sr2))

        self.assertEqual(mrUid2, DoGet(_REMOTE, PATH4 % sr2).strip('\x00'))
        self.assertEqual(mrSeries2, DoGet(_REMOTE, (PATH2 + '/0/SeriesInstanceUID') % sr2).strip('\x00'))
        self.assertEqual(mrStudy2, DoGet(_REMOTE, (PATH1 + '/0/StudyInstanceUID') % sr2).strip('\x00'))

        content1 = DoGet(_REMOTE, '/instances/%s/tags?simplify' % sr1) ['ContentSequence']
        content2 = DoGet(_REMOTE, '/instances/%s/tags?simplify' % sr2) ['ContentSequence']
        self.assertEqual(str(content1), str(content2))


    def test_bitbucket_issue_94(self):
        # "a simple instance modification should not modify FrameOfReferenceUID + ..."
        # https://bugs.orthanc-server.com/show_bug.cgi?id=94
        i = UploadInstance(_REMOTE, 'Issue94.dcm')['ID']

        source = DoGet(_REMOTE, '/instances/%s/attachments/dicom/data' % i)

        modified = DoPost(_REMOTE, '/instances/%s/modify' % i,
                          { "Replace" : {"PatientID" : "toto"}, "Force": True})

        anonymized = DoPost(_REMOTE, '/instances/%s/anonymize' % i)

        a = ExtractDicomTags(source, [ 'FrameOfReferenceUID' ])
        self.assertEqual(1, len(a))
        
        b = ExtractDicomTags(modified, [ 'FrameOfReferenceUID' ])
        self.assertEqual(1, len(b))
        
        c = ExtractDicomTags(anonymized, [ 'FrameOfReferenceUID' ])
        self.assertEqual(1, len(c))
        
        self.assertEqual(a, b)     # Modified DICOM
        self.assertNotEqual(a, c)  # Anonymized DICOM


    def test_metadata_origin(self):
        # Upload using the REST API
        i = UploadInstance(_REMOTE, 'Knee/T1/IM-0001-0001.dcm')['ID']
        self.assertEqual('RestApi', DoGet(_REMOTE, '/instances/%s/metadata/Origin' % i))
        self.assertEqual('', DoGet(_REMOTE, '/instances/%s/metadata/RemoteAET' % i))
        self.assertNotEqual('', DoGet(_REMOTE, '/instances/%s/metadata/RemoteIP' % i))
        self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/instances/%s/metadata/CalledAET' % i))

        # "HttpUsername" is empty iff "AuthenticationEnabled" is "false"
        self.assertTrue(DoGet(_REMOTE, '/instances/%s/metadata/HttpUsername' % i) in [ '', 'alice' ])
        
        m = DoGet(_REMOTE, '/instances/%s/metadata?expand' % i)
        self.assertEqual('RestApi', m['Origin'])
        self.assertEqual('', m['RemoteAET'])
        self.assertNotEqual('', m['RemoteIP'])
        self.assertFalse('CalledAET' in m)
        self.assertTrue('HttpUsername' in m)
        self.assertTrue(m['HttpUsername'] in [ '', 'alice' ])

        self.assertEqual('1.2.840.10008.1.2.4.91', m['TransferSyntax'])
        self.assertEqual('1.2.840.10008.5.1.4.1.1.4', m['SopClassUid'])
        self.assertEqual('1', m['IndexInSeries'])
        self.assertTrue('ReceptionDate' in m)

        DoDelete(_REMOTE, '/instances/%s' % i)

        # Upload using the DICOM protocol
        subprocess.check_call([ FindExecutable('storescu'),
                                _REMOTE['Server'], str(_REMOTE['DicomPort']),
                                GetDatabasePath('Knee/T1/IM-0001-0001.dcm'),
                                '-xw' ])  # Propose JPEG2000
        self.assertEqual('DicomProtocol', DoGet(_REMOTE, '/instances/%s/metadata/Origin' % i))
        self.assertEqual('STORESCU', DoGet(_REMOTE, '/instances/%s/metadata/RemoteAET' % i))
        self.assertNotEqual('', DoGet(_REMOTE, '/instances/%s/metadata/RemoteIP' % i))
        self.assertEqual('ANY-SCP', DoGet(_REMOTE, '/instances/%s/metadata/CalledAET' % i))
        self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/instances/%s/metadata/HttpUsername' % i))

        m = DoGet(_REMOTE, '/instances/%s/metadata?expand' % i)
        self.assertEqual('DicomProtocol', m['Origin'])
        self.assertEqual('STORESCU', m['RemoteAET'])
        self.assertNotEqual('', m['RemoteIP'])
        self.assertEqual('ANY-SCP', m['CalledAET'])
        self.assertFalse('HttpUsername' in m)

        self.assertEqual('1.2.840.10008.1.2.4.91', m['TransferSyntax'])
        self.assertEqual('1.2.840.10008.5.1.4.1.1.4', m['SopClassUid'])
        self.assertEqual('1', m['IndexInSeries'])
        self.assertTrue('ReceptionDate' in m)


    def test_lua_deadlock(self):
        # Rana Asim Wajid (2018-07-14): "It does seem that the issue
        # is with the lua script I'm using for conversion of images to
        # JPEG2000. When the script is used with 1.4.0 the first
        # instance appears to be stored and then everything just
        # halts, ie Orthanc wont respond to anything after that."
        # https://groups.google.com/d/msg/orthanc-users/Rc-Beb42xc8/JUgdzrmCAgAJ
        InstallLuaScriptFromPath(_REMOTE, 'Lua/Jpeg2000Conversion.lua')

        subprocess.check_call([ FindExecutable('storescu'),
                                _REMOTE['Server'], str(_REMOTE['DicomPort']),
                                GetDatabasePath('Brainix/Flair/IM-0001-0001.dcm'),
                                GetDatabasePath('Brainix/Flair/IM-0001-0002.dcm'),
                                ])

        instances = DoGet(_REMOTE, '/instances')
        self.assertEqual(2, len(instances))

        t1 = DoGet(_REMOTE, '/instances/%s/metadata/TransferSyntax' % instances[0])
        t2 = DoGet(_REMOTE, '/instances/%s/metadata/TransferSyntax' % instances[1])
        self.assertEqual('1.2.840.10008.1.2.4.90', t1)   # this will fail if libgdcm-tools is not installed
        self.assertEqual(t1, t2);


    def test_find_group_length(self):
        # Orthanc <= 1.4.1 fails to answer C-FIND queries that contain
        # one of the Generic Group Length tags (*, 0x0000)
        a = UploadInstance(_REMOTE, 'Brainix/Flair/IM-0001-0001.dcm')['ID']
        result = CallFindScu([ '-k', '0008,0052=STUDY', '-k', '0008,0000=80' ])
        self.assertFalse('UnableToProcess' in result)
        self.assertFalse('E:' in result)


    def test_split(self):
        UploadInstance(_REMOTE, 'Knee/T1/IM-0001-0001.dcm')
        UploadInstance(_REMOTE, 'Knee/T2/IM-0001-0001.dcm')
        knee1Sop = '1.3.46.670589.11.17521.5.0.3124.2008081908590448738'
        knee2Sop = '1.3.46.670589.11.17521.5.0.3124.2008081909113806560'
        study = '0a9b3153-2512774b-2d9580de-1fc3dcf6-3bd83918'
        t1 = '6de73705-c4e65c1b-9d9ea1b5-cabcd8e7-f15e4285'
        t2 = 'bbf7a453-0d34251a-03663b55-46bb31b9-ffd74c59'

        self.assertEqual(1, len(DoGet(_REMOTE, '/studies')))
        self.assertEqual(2, len(DoGet(_REMOTE, '/series')))

        info = DoGet(_REMOTE, '/studies/%s' % study)
        self.assertTrue('ReferringPhysicianName' in info['MainDicomTags'])
            
        job = MonitorJob2(_REMOTE, lambda: DoPost
                          (_REMOTE, '/studies/%s/split' % study, {
                              'Series' : [ t2 ],
                              'Replace' : { 'PatientName' : 'Hello' },
                              'Remove' : [ 'ReferringPhysicianName' ],
                              'KeepSource' : False,
                              'Asynchronous' : True
                          }))

        self.assertNotEqual(None, job)

        studies = set(DoGet(_REMOTE, '/studies'))
        self.assertEqual(2, len(studies))

        series = set(DoGet(_REMOTE, '/series'))
        self.assertEqual(2, len(series))
        self.assertTrue(t1 in series)

        study2 = DoGet(_REMOTE, '/jobs/%s' % job)['Content']['TargetStudy']
        self.assertTrue(study in studies)
        self.assertTrue(study2 in studies)

        info = DoGet(_REMOTE, '/studies/%s' % study2)
        self.assertTrue('Hello', info['PatientMainDicomTags']['PatientName'])
        self.assertFalse('ReferringPhysicianName' in info['MainDicomTags'])

        sopInstanceUids = set()
        for i in DoGet(_REMOTE, '/instances?expand'):
            sopInstanceUids.add(i['MainDicomTags']['SOPInstanceUID'])

        self.assertTrue(knee1Sop in sopInstanceUids)

        # Fails if Orthanc <= 1.5.7
        self.assertFalse(knee2Sop in sopInstanceUids)  # Because "KeepSource" is False

        # One original instance is kept, another one is added because of the split
        self.assertEqual(2, len(sopInstanceUids))

        
    def test_merge(self):
        UploadInstance(_REMOTE, 'Knee/T1/IM-0001-0001.dcm')
        UploadInstance(_REMOTE, 'Brainix/Flair/IM-0001-0001.dcm')
        kneeSop = '1.3.46.670589.11.17521.5.0.3124.2008081908590448738'
        brainixSop = '1.3.46.670589.11.0.0.11.4.2.0.8743.5.5396.2006120114314079549'
        knee = '0a9b3153-2512774b-2d9580de-1fc3dcf6-3bd83918'
        t1 = '6de73705-c4e65c1b-9d9ea1b5-cabcd8e7-f15e4285'
        brainix = '27f7126f-4f66fb14-03f4081b-f9341db2-53925988'
        flair = '1e2c125c-411b8e86-3f4fe68e-a7584dd3-c6da78f0'

        self.assertEqual(2, len(DoGet(_REMOTE, '/studies')))
        self.assertEqual(2, len(DoGet(_REMOTE, '/series')))

        job = MonitorJob2(_REMOTE, lambda: DoPost
                          (_REMOTE, '/studies/%s/merge' % knee, {
                              'Resources' : [ brainix ],
                              'KeepSource' : True,
                              'Synchronous' : False
                          }))

        self.assertNotEqual(None, job)

        studies = set(DoGet(_REMOTE, '/studies'))
        self.assertEqual(2, len(studies))
        self.assertTrue(knee in studies)
        self.assertTrue(brainix in studies)

        series = set(DoGet(_REMOTE, '/studies/%s' % knee)['Series'])
        self.assertTrue(t1 in series)
        series.remove(t1)
        self.assertEqual(1, len(series))

        instances = DoGet(_REMOTE, '/series/%s' % list(series)[0])['Instances']
        self.assertEqual(1, len(instances))
        merged = DoGet(_REMOTE, '/instances/%s/tags?simplify' % instances[0])

        instances = DoGet(_REMOTE, '/series/%s' % t1)['Instances']
        self.assertEqual(1, len(instances))
        a = DoGet(_REMOTE, '/instances/%s/tags?simplify' % instances[0])

        instances = DoGet(_REMOTE, '/series/%s' % flair)['Instances']
        self.assertEqual(1, len(instances))
        b = DoGet(_REMOTE, '/instances/%s/tags?simplify' % instances[0])

        tags = DoGet(_REMOTE, '/studies/%s' % knee)
        
        for key in tags['PatientMainDicomTags']:
            self.assertEqual(a[key], merged[key])
            if (key in b and key != 'PatientSex'):
                self.assertNotEqual(a[key], b[key])
        
        for key in tags['MainDicomTags']:
            # Not in the patient/study module
            if (not key in [ 'InstitutionName',
                             'RequestingPhysician',
                             'RequestedProcedureDescription', ]):
                self.assertEqual(a[key], merged[key])
                if (key in b):
                    self.assertNotEqual(a[key], b[key])

        sopInstanceUids = set()
        for i in DoGet(_REMOTE, '/instances?expand'):
            sopInstanceUids.add(i['MainDicomTags']['SOPInstanceUID'])

        self.assertTrue(kneeSop in sopInstanceUids)
        self.assertTrue(brainixSop in sopInstanceUids)

        # Fails if Orthanc <= 1.5.7
        # The 2 original instances are kept, another one is added because of the merge
        self.assertEqual(3, len(sopInstanceUids))
 

    def test_async_archive(self):
        # Testing the asynchronous generation of archives/medias (new
        # in Orthanc 1.4.3)
        UploadInstance(_REMOTE, 'Knee/T1/IM-0001-0001.dcm')
        UploadInstance(_REMOTE, 'Knee/T2/IM-0001-0001.dcm')

        kneeT1 = '6de73705-c4e65c1b-9d9ea1b5-cabcd8e7-f15e4285'
        kneeT2 = 'bbf7a453-0d34251a-03663b55-46bb31b9-ffd74c59'

        job = MonitorJob2(_REMOTE, lambda: DoPost
                          (_REMOTE, '/series/%s/archive' % kneeT1, {
                              'Synchronous' : False,
                              'Filename': 'toto.zip'
                          }))

        z, resp = GetArchive(_REMOTE, '/jobs/%s/archive' % job)
        self.assertEqual(1, len(z.namelist()))
        self.assertFalse('DICOMDIR' in z.namelist())
        if IsOrthancVersionAbove(_REMOTE, 1, 12, 7):
            self.assertEqual('filename="toto.zip"', resp['content-disposition'])

        info = DoGet(_REMOTE, '/jobs/%s' % job)
        self.assertEqual(0, info['Content']['ArchiveSizeMB'])  # New in Orthanc 1.8.1
        self.assertEqual(1, info['Content']['InstancesCount'])
        self.assertEqual(0, info['Content']['UncompressedSizeMB'])
        
        job2 = MonitorJob2(_REMOTE, lambda: DoPost
                           (_REMOTE, '/series/%s/media' % kneeT1, {
                               'Synchronous' : False
                           }))

        # The archive from the first job has been replaced by the
        # archive from second job (as MediaArchiveSize == 1)
        self.assertRaises(Exception, lambda: GetArchive(_REMOTE, '/jobs/%s/archive' % job))

        z, resp = GetArchive(_REMOTE, '/jobs/%s/archive' % job2)
        self.assertEqual(2, len(z.namelist()))
        self.assertTrue('DICOMDIR' in z.namelist())

        info = DoGet(_REMOTE, '/jobs/%s' % job2)
        self.assertEqual(0, info['Content']['ArchiveSizeMB'])  # New in Orthanc 1.8.1
        self.assertEqual(1, info['Content']['InstancesCount'])
        self.assertEqual(0, info['Content']['UncompressedSizeMB'])

        job = MonitorJob2(_REMOTE, lambda: DoPost
                          (_REMOTE, '/tools/create-archive', {
                              'Synchronous' : False,
                              'Resources' : [ kneeT1, kneeT2 ],
                          }))

        z, resp = GetArchive(_REMOTE, '/jobs/%s/archive' % job)
        self.assertEqual(2, len(z.namelist()))
        self.assertFalse('DICOMDIR' in z.namelist())
        
        info = DoGet(_REMOTE, '/jobs/%s' % job)
        self.assertEqual(0, info['Content']['ArchiveSizeMB'])  # New in Orthanc 1.8.1
        self.assertEqual(2, info['Content']['InstancesCount'])
        self.assertEqual(0, info['Content']['UncompressedSizeMB'])

        job = MonitorJob2(_REMOTE, lambda: DoPost
                          (_REMOTE, '/tools/create-media', {
                              'Synchronous' : False,
                              'Resources' : [ kneeT1, kneeT2 ],
                          }))

        z, resp = GetArchive(_REMOTE, '/jobs/%s/archive' % job)
        self.assertEqual(3, len(z.namelist()))
        self.assertTrue('DICOMDIR' in z.namelist())

        self.assertEqual(0, info['Content']['ArchiveSizeMB'])  # New in Orthanc 1.8.1
        self.assertEqual(2, info['Content']['InstancesCount'])
        self.assertEqual(0, info['Content']['UncompressedSizeMB'])
        
        
    def test_archive_job_delete_output(self):
        if IsOrthancVersionAbove(_REMOTE, 1, 12, 1):
            UploadInstance(_REMOTE, 'Knee/T1/IM-0001-0001.dcm')
            UploadInstance(_REMOTE, 'Knee/T2/IM-0001-0001.dcm')

            kneeT1 = '6de73705-c4e65c1b-9d9ea1b5-cabcd8e7-f15e4285'
            kneeT2 = 'bbf7a453-0d34251a-03663b55-46bb31b9-ffd74c59'

            job = MonitorJob2(_REMOTE, lambda: DoPost
                            (_REMOTE, '/series/%s/archive' % kneeT1, {
                                'Synchronous' : False
                            }))

            z, resp = GetArchive(_REMOTE, '/jobs/%s/archive' % job)
            # delete the output
            DoDelete(_REMOTE, '/jobs/%s/archive' % job)
            # make sure it is not available anymore afterwards
            self.assertRaises(Exception, lambda: GetArchive(_REMOTE, '/jobs/%s/archive' % job))

            # repeat with another resource/job
            job = MonitorJob2(_REMOTE, lambda: DoPost
                            (_REMOTE, '/series/%s/archive' % kneeT2, {
                                'Synchronous' : False
                            }))
            z, resp = GetArchive(_REMOTE, '/jobs/%s/archive' % job)
            # delete the output
            DoDelete(_REMOTE, '/jobs/%s/archive' % job)
            # make sure it is not available anymore afterwards
            self.assertRaises(Exception, lambda: GetArchive(_REMOTE, '/jobs/%s/archive' % job))
            # job is still available
            DoGet(_REMOTE, '/jobs/%s' % job)

            if IsOrthancVersionAbove(_REMOTE, 1, 12, 2):
                # delete the job itself
                DoDelete(_REMOTE, '/jobs/%s' % job)
                self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/jobs/%s' % job))

                # test deletion of jobs in history
                job = MonitorJob2(_REMOTE, lambda: DoPost
                                (_REMOTE, '/series/%s/archive' % kneeT2, {
                                    'Synchronous' : False
                                }))
                z, resp = GetArchive(_REMOTE, '/jobs/%s/archive' % job)
                # delete the job itself
                DoDelete(_REMOTE, '/jobs/%s' % job)
                # make sure it is not available anymore afterwards (and its output is not available either)
                self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/jobs/%s' % job))
                self.assertRaises(Exception, lambda: GetArchive(_REMOTE, '/jobs/%s/archive' % job))


    def test_queries_hierarchy(self):
        UploadInstance(_REMOTE, 'Knee/T1/IM-0001-0001.dcm')
        UploadInstance(_REMOTE, 'Brainix/Flair/IM-0001-0001.dcm')

        tags = {
            'NumberOfPatientRelatedInstances' : '',
            'NumberOfPatientRelatedSeries' : '',
            'NumberOfPatientRelatedStudies' : '',
            'NumberOfStudyRelatedInstances' : '',
            'NumberOfStudyRelatedSeries' : '',
            'NumberOfSeriesRelatedInstances' : '',
        }

        tags2 = copy.copy(tags)
        tags2['PatientID'] = '887'  # Only consider the "Knee" patient

        patient = DoPost(_REMOTE, '/modalities/self/query', {
            'Level' : 'Patient',
            'Query' : tags2
        }) ['ID']

        study = DoPost(_REMOTE, '/modalities/self/query', {
            'Level' : 'Study',
            'Query' : tags2
        }) ['ID']

        series = DoPost(_REMOTE, '/modalities/self/query', {
            'Level' : 'Series',
            'Query' : tags2
        }) ['ID']

        instance = DoPost(_REMOTE, '/modalities/self/query', {
            'Level' : 'Instance',
            'Query' : tags2
        }) ['ID']

        p = DoGet(_REMOTE, '/queries/%s/answers?expand&simplify' % patient)
        self.assertEqual(1, len(p))
        self.assertEqual('887', p[0]['PatientID'])
        self.assertEqual('1', p[0]['NumberOfPatientRelatedInstances'])
        self.assertEqual('1', p[0]['NumberOfPatientRelatedSeries'])
        self.assertEqual('1', p[0]['NumberOfPatientRelatedStudies'])
        self.assertFalse('NumberOfStudyRelatedInstances' in p[0])
        self.assertFalse('NumberOfStudyRelatedSeries' in p[0])
        self.assertFalse('NumberOfSeriesRelatedInstances' in p[0])
        
        p = DoGet(_REMOTE, '/queries/%s/answers?expand&simplify' % study)
        self.assertEqual(1, len(p))
        self.assertEqual('2.16.840.1.113669.632.20.121711.10000160881', p[0]['StudyInstanceUID'])
        self.assertEqual('1', p[0]['NumberOfStudyRelatedInstances'])
        self.assertEqual('1', p[0]['NumberOfStudyRelatedSeries'])
        self.assertFalse('NumberOfPatientRelatedInstances' in p[0])
        self.assertFalse('NumberOfPatientRelatedSeries' in p[0])
        self.assertFalse('NumberOfPatientRelatedInstances' in p[0])
        self.assertFalse('NumberOfSeriesRelatedInstances' in p[0])

        p = DoGet(_REMOTE, '/queries/%s/answers?expand&simplify' % series)
        self.assertEqual(1, len(p))
        self.assertEqual('1.3.46.670589.11.17521.5.0.3124.2008081908564160709', p[0]['SeriesInstanceUID'])
        self.assertEqual('1', p[0]['NumberOfSeriesRelatedInstances'])
        self.assertFalse('NumberOfPatientRelatedInstances' in p[0])
        self.assertFalse('NumberOfPatientRelatedSeries' in p[0])
        self.assertFalse('NumberOfPatientRelatedInstances' in p[0])
        self.assertFalse('NumberOfStudyRelatedInstances' in p[0])
        self.assertFalse('NumberOfStudyRelatedSeries' in p[0])

        p = DoGet(_REMOTE, '/queries/%s/answers?expand&simplify' % instance)
        self.assertEqual(1, len(p))
        self.assertEqual('1.3.46.670589.11.17521.5.0.3124.2008081908590448738', p[0]['SOPInstanceUID'])

        j = DoPost(_REMOTE, '/queries/%s/answers/0/query-studies' % patient,
                   { 'Query' : tags }) ['ID']
        self.assertEqual(DoGet(_REMOTE, '/queries/%s/answers?expand&simplify' % j),
                         DoGet(_REMOTE, '/queries/%s/answers?expand&simplify' % study))

        j = DoPost(_REMOTE, '/queries/%s/answers/0/query-series' % patient,
                   { 'Query' : tags }) ['ID']
        self.assertEqual(DoGet(_REMOTE, '/queries/%s/answers?expand&simplify' % j),
                         DoGet(_REMOTE, '/queries/%s/answers?expand&simplify' % series))
        
        j = DoPost(_REMOTE, '/queries/%s/answers/0/query-instances' % patient,
                   { 'Query' : tags }) ['ID']
        self.assertEqual(DoGet(_REMOTE, '/queries/%s/answers?expand&simplify' % j),
                         DoGet(_REMOTE, '/queries/%s/answers?expand&simplify' % instance))
        
        j = DoPost(_REMOTE, '/queries/%s/answers/0/query-series' % study,
                   { 'Query' : tags }) ['ID']
        self.assertEqual(DoGet(_REMOTE, '/queries/%s/answers?expand&simplify' % j),
                         DoGet(_REMOTE, '/queries/%s/answers?expand&simplify' % series))
        
        j = DoPost(_REMOTE, '/queries/%s/answers/0/query-instances' % study,
                   { 'Query' : tags }) ['ID']
        self.assertEqual(DoGet(_REMOTE, '/queries/%s/answers?expand&simplify' % j),
                         DoGet(_REMOTE, '/queries/%s/answers?expand&simplify' % instance))
        
        j = DoPost(_REMOTE, '/queries/%s/answers/0/query-instances' % series,
                   { 'Query' : tags }) ['ID']
        self.assertEqual(DoGet(_REMOTE, '/queries/%s/answers?expand&simplify' % j),
                         DoGet(_REMOTE, '/queries/%s/answers?expand&simplify' % instance))
        

    def test_dicom_disk_size(self):
        dicomSize = 0

        a = UploadInstance(_REMOTE, 'Brainix/Flair/IM-0001-0001.dcm') ['ID']
        isCompressed = (DoGet(_REMOTE, '/instances/%s/attachments/dicom/is-compressed' % a) != 0)

        for i in range(2):
            p = 'Knee/T%d/IM-0001-0001.dcm' % (i + 1)
            UploadInstance(_REMOTE, p)
            dicomSize += os.path.getsize(GetDatabasePath(p))

        s = DoGet(_REMOTE, '/patients/ca29faea-b6a0e17f-067743a1-8b778011-a48b2a17/statistics')  # Consider Knee patient
        self.assertEqual(2, s['CountInstances'])
        self.assertEqual(2, s['CountSeries'])
        self.assertEqual(1, s['CountStudies'])

        self.assertEqual(dicomSize, int(s['DicomUncompressedSize']))
        
        if isCompressed:
            self.assertGreater(dicomSize, int(s['DicomDiskSize']))
            self.assertGreater(s['UncompressedSize'], s['DiskSize'])
            self.assertLess(dicomSize, int(s['UncompressedSize']))
        else:
            self.assertEqual(dicomSize, int(s['DicomDiskSize']))
            self.assertEqual(s['UncompressedSize'], s['DiskSize'])
            if IsOrthancVersionAbove(_REMOTE, 1, 9, 1):
                if IsDicomUntilPixelDataStored(_REMOTE):
                    self.assertLess(dicomSize, int(s['UncompressedSize']))
                else:
                    self.assertEqual(dicomSize, int(s['UncompressedSize']))
            else:
                # In Orthanc <= 1.9.0, there is the "dicom-as-json"
                # attachment in addition to the DICOM file
                self.assertLess(dicomSize, int(s['UncompressedSize']))
                

    def test_changes_2(self):
        # More consistent behavior since Orthanc 1.5.2
        # https://groups.google.com/d/msg/orthanc-users/QhzB6vxYeZ0/YxabgqpfBAAJ

        # Make sure that this is not the first change
        self.assertEqual(0, len(DoGet(_REMOTE, '/instances')))
        a = UploadInstance(_REMOTE, 'DummyCT.dcm')['ID']
        self.assertEqual(1, len(DoGet(_REMOTE, '/instances')))
        DoDelete(_REMOTE, '/instances/%s' % a)        

        # No more instance, but there were previous changes
        self.assertEqual(0, len(DoGet(_REMOTE, '/instances')))
        
        c = DoGet(_REMOTE, '/changes')
        self.assertEqual(0, len(c['Changes']))
        self.assertTrue(c['Done'])
        seq = c['Last']

        c = DoGet(_REMOTE, '/changes?last')
        self.assertEqual(0, len(c['Changes']))
        self.assertTrue(c['Done'])
        self.assertEqual(seq, c['Last'])

        c = DoGet(_REMOTE, '/changes?since=%d' % (seq + 1000))
        self.assertEqual(0, len(c['Changes']))
        self.assertTrue(c['Done'])
        self.assertEqual(seq, c['Last'])

        # Add one instance
        UploadInstance(_REMOTE, 'DummyCT.dcm')
        self.assertEqual(1, len(DoGet(_REMOTE, '/instances')))

        c = DoGet(_REMOTE, '/changes')
        self.assertEqual(4, len(c['Changes']))
        self.assertTrue(c['Done'])
        self.assertEqual(seq + 4, c['Last'])

        c = DoGet(_REMOTE, '/changes?last')
        self.assertEqual(1, len(c['Changes']))
        self.assertTrue(c['Done'])
        self.assertEqual(seq + 4, c['Last'])

        c = DoGet(_REMOTE, '/changes?since=%d' % (seq + 1000))
        self.assertEqual(0, len(c['Changes']))
        self.assertTrue(c['Done'])
        self.assertEqual(seq + 4, c['Last'])

        # Add, then delete, one user-defined metadata: This triggers 2
        # changes of type "UpdatedMetadata"
        i = DoGet(_REMOTE, '/instances') [0]
        DoPut(_REMOTE, '/instances/%s/metadata/4000' % i, 'hello', 'text/plain')

        (headers, body) = DoGetRaw(_REMOTE, '/instances/%s/metadata/4000' % i)
        self.assertEqual('200', headers['status'])
        self.assertEqual('hello', body)

        c = DoGet(_REMOTE, '/changes?last')
        self.assertEqual(1, len(c['Changes']))
        self.assertTrue(c['Done'])
        self.assertEqual(seq + 5, c['Last'])
        self.assertEqual('UpdatedMetadata', c['Changes'][0]['ChangeType'])

        if IsOrthancVersionAbove(_REMOTE, 1, 9, 2):
            DoDelete(_REMOTE, '/instances/%s/metadata/4000' % i, headers = {
                'If-Match' : headers['etag']
            })
        else:
            self.assertFalse('etag' in headers)
            DoDelete(_REMOTE, '/instances/%s/metadata/4000' % i)
            
        c = DoGet(_REMOTE, '/changes?last')
        self.assertEqual(1, len(c['Changes']))
        self.assertTrue(c['Done'])
        self.assertEqual(seq + 6, c['Last'])
        self.assertEqual('UpdatedMetadata', c['Changes'][0]['ChangeType'])
        
        # Remove the uploaded instance
        DoDelete(_REMOTE, '/instances/%s' % a)
        self.assertEqual(0, len(DoGet(_REMOTE, '/instances')))

        c = DoGet(_REMOTE, '/changes')
        self.assertEqual(0, len(c['Changes']))
        self.assertTrue(c['Done'])
        self.assertEqual(seq + 6, c['Last'])

        c = DoGet(_REMOTE, '/changes?last')
        self.assertEqual(0, len(c['Changes']))
        self.assertTrue(c['Done'])
        self.assertEqual(seq + 6, c['Last'])

        c = DoGet(_REMOTE, '/changes?since=%d' % (seq + 1000))
        self.assertEqual(0, len(c['Changes']))
        self.assertTrue(c['Done'])
        self.assertEqual(seq + 6, c['Last'])
        

    def test_bitbucket_issue_124(self):
        a = UploadInstance(_REMOTE, 'Issue124.dcm')['ID']
        s = DoGet(_REMOTE, '/instances/%s/series' % a)['ID']

        z, resp = GetArchive(_REMOTE, '/series/%s/media' % s)
        self.assertEqual(2, len(z.namelist()))


    def test_invalid_findscp(self):
        UploadInstance(_REMOTE, 'DummyCT.dcm')
        findscu = CallFindScu([ '-S', '-k', '8,52=IMAGE', '-k', '8,16', '-k', '2,2' ])
        self.assertEqual(0, len(re.findall('\(0002,0002\)', findscu)))


    def test_bitbucket_issue_90(self):
        def CountDicomResults(sex):
            a = CallFindScu([ '-S', '-k', '8,52=STUDY', '-k', sex ])
            return len(re.findall('\(0010,0040\)', a))

        def CountRestResults(sex):
            a = DoPost(_REMOTE, '/tools/find',
                       { 'Level' : 'Study', 'Query' : { 'PatientSex' : sex } })
            return len(a)

        # Just like the "CR000000.dcm" of the issue, the test image
        # "DummyCT.dcm" has the tag PatientSex (0010,0040) unset
        UploadInstance(_REMOTE, 'DummyCT.dcm')

        # Test that the behavior of DICOM vs. REST API is consistent on missing tags

        # In wildcard constraints, the patient sex must be set for a match to occur
        self.assertEqual(0, CountDicomResults('PatientSex=*'))
        self.assertEqual(0, CountRestResults('*'))

        # In single-valued constraints, the patient sex must be set
        self.assertEqual(0, CountDicomResults('PatientSex=F'))
        self.assertEqual(0, CountDicomResults('PatientSex=M'))
        self.assertEqual(0, CountRestResults('F'))
        self.assertEqual(0, CountRestResults('M'))

        # Empty constraints are only used to ask the actual value of
        # the tag to be added to the *answer*. The tag should not used
        # as a filter in such a situation.
        self.assertEqual(1, CountDicomResults('PatientSex'))
        self.assertEqual(1, CountDicomResults('PatientSex='))
        self.assertEqual(1, CountRestResults(''))   # This check fails on Orthanc <= 1.5.2 (issue 90)


    def test_rest_modalities_in_study(self):
        # Tests a regression that is present in Orthanc 1.5.2 and 1.5.3
        # https://groups.google.com/d/msg/orthanc-users/7lZyG3wpx-M/uOXzAzVCFwAJ
        UploadInstance(_REMOTE, 'ColorTestImageJ.dcm')

        a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Study',
                                             'Query' : { 'ModalitiesInStudy' : 'US' }})
        self.assertEqual(0, len(a))

        a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Study',
                                             'Query' : { 'ModalitiesInStudy' : 'US\\CT' }})
        self.assertEqual(1, len(a))

        a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Study',
                                             'Query' : { 'ModalitiesInStudy' : 'CT' }})
        self.assertEqual(1, len(a))


    def test_series_status(self):
        def HasCompletedInChanges():
            for c in DoGet(_REMOTE, '/changes?limit=1000&since=0')['Changes']:
                if c['ChangeType'] == 'CompletedSeries':
                    return True;

            return False
        
        UploadInstance(_REMOTE, 'Knix/Loc/IM-0001-0001.dcm')
        series = '8ea120d7-5057d919-837dfbcc-ccd04e0f-7f3a94aa'
        self.assertEqual('Unknown', DoGet(_REMOTE, '/series/%s' % series)['Status'])
        self.assertFalse(HasCompletedInChanges())

        series = 'ce25ecb6-ed79d004-5ae43ca7-3fc89bc5-67511614'

        for i in range(3):
            UploadInstance(_REMOTE, 'Series/Lena-%d.dcm' % (i + 1))
            self.assertEqual('Missing', DoGet(_REMOTE, '/series/%s' % series)['Status'])
            self.assertFalse(HasCompletedInChanges())

        UploadInstance(_REMOTE, 'Series/Lena-4.dcm')
        self.assertEqual('Complete', DoGet(_REMOTE, '/series/%s' % series)['Status'])
        self.assertTrue(HasCompletedInChanges())

        DoDelete(_REMOTE, '/changes')
        self.assertFalse(HasCompletedInChanges())

        UploadInstance(_REMOTE, 'Series/Lena-5.dcm')
        self.assertEqual('Inconsistent', DoGet(_REMOTE, '/series/%s' % series)['Status'])
        self.assertFalse(HasCompletedInChanges())
            

    def test_dicomweb(self):
        if IsOrthancVersionAbove(_LOCAL, 1, 12, 5) and DoGet(_REMOTE, '/system')['ApiVersion'] >= 26:  # the references have changed with 1.12.5 -> we don't want to keep 2 references
            def Compare(dicom, reference):
                a = UploadInstance(_REMOTE, dicom) ['ID']
                b = DoGet(_REMOTE, '/instances/%s/file' % a,
                        headers = { 'Accept' : 'application/dicom+json' })
                with open(GetDatabasePath(reference), 'rb') as c:
                    d = json.load(c)
                    AssertAlmostEqualRecursive(self, d, b)
                        
            Compare('DummyCT.dcm', 'DummyCT.json')
            Compare('MarekLatin2.dcm', 'MarekLatin2.json')
            Compare('HierarchicalAnonymization/StructuredReports/IM0',
                    'HierarchicalAnonymization/StructuredReports/IM0.json')


    def test_issue_95_encodings(self):
        # https://bugs.orthanc-server.com/show_bug.cgi?id=95
        # Check out image: "../Database/Encodings/DavidClunie/charsettests.screenshot.png"

        # Very useful tool: "file2" from package "file-kanji"

        def GetPatientName(dicom):
            i = UploadInstance(_REMOTE, dicom) ['ID']
            j = DoGet(_REMOTE, '/instances/%s/tags?simplify' % i)
            return j['PatientName']
        
        def ComparePatientName(name, dicom):
            self.assertEqual(name, GetPatientName(dicom))

        # gdcmraw -t 10,10 -i SCSFREN -o /tmp/tag && uconv -f ISO-IR-100 -t UTF-8 /tmp/tag && echo
        ComparePatientName(u'Buc^Jérôme', 'Encodings/DavidClunie/SCSFREN')

        # gdcmraw -t 10,10 -i SCSI2 -o /tmp/tag && uconv -f KOREAN -t UTF-8 /tmp/tag && echo
        ComparePatientName(u'Hong^Gildong=洪^吉洞=홍^길동', 'Encodings/DavidClunie/SCSI2')  # Since Orthanc 1.5.5
        
        # gdcmraw -t 10,10 -i SCSX2 -o /tmp/tag && uconv -f GB18030 -t UTF-8 /tmp/tag && echo
        ComparePatientName(u'Wang^XiaoDong=王^小东=', 'Encodings/DavidClunie/SCSX2')

        # gdcmraw -t 10,10 -i SCSX1 -o /tmp/tag && cat /tmp/tag && echo
        ComparePatientName(u'Wang^XiaoDong=王^小東=', 'Encodings/DavidClunie/SCSX1')

        # gdcmraw -t 10,10 -i SCSH31 -o /tmp/tag && uconv -f JIS -t UTF-8 /tmp/tag && echo
        ComparePatientName(u'Yamada^Tarou=山田^太郎=やまだ^たろう', 'Encodings/DavidClunie/SCSH31')

        # gdcmraw -t 10,10 -i SCSGERM -o /tmp/tag && uconv -f ISO-IR-100 -t UTF-8 /tmp/tag && echo
        ComparePatientName(u'Äneas^Rüdiger', 'Encodings/DavidClunie/SCSGERM')

        # gdcmraw -t 10,10 -i SCSGREEK -o /tmp/tag && uconv -f ISO-IR-126 -t UTF-8 /tmp/tag && echo
        ComparePatientName(u'Διονυσιος', 'Encodings/DavidClunie/SCSGREEK')

        # gdcmraw -t 10,10 -i SCSRUSS -o /tmp/tag && uconv -f ISO-IR-144 -t UTF-8 /tmp/tag && echo
        ComparePatientName(u'Люкceмбypг', 'Encodings/DavidClunie/SCSRUSS')

        # gdcmraw -t 10,10 -i SCSHBRW -o /tmp/tag && uconv -f ISO-IR-138 -t UTF-8 /tmp/tag && echo
        # NB: Hebrew is a right-to-left encoding, copying/pasting from
        # Linux console into Emacs automatically reverse the string
        ComparePatientName(u'שרון^דבורה', 'Encodings/DavidClunie/SCSHBRW')

        # gdcmraw -t 10,10 -i SCSARAB -o /tmp/tag && uconv -f ISO-IR-127 -t UTF-8 /tmp/tag && echo
        # NB: Right-to-left as for Hebrew (SCSHBRW), and the Ubuntu console can't display such
        # characters by default, but copy/paste works with Emacs
        ComparePatientName(u'قباني^لنزار', 'Encodings/DavidClunie/SCSARAB')

        # SCSH32: This SpecificCharacterSet is composed of 2
        # codepages: "ISO 2022 IR 13" (i.e. "SHIFT_JIS") until the
        # first equal, then "ISO 2022 IR 87" (i.e. "JIS") for the
        # remainer. Orthanc only takes into consideration the first
        # codepage: This is a limitation.
        # gdcmraw -t 10,10 -i SCSH32 -o /tmp/tag && cut -d '=' -f 1 /tmp/tag | uconv -f SHIFT_JIS -t UTF-8
        self.assertTrue(GetPatientName('Encodings/DavidClunie/SCSH32').startswith(u'ﾔﾏﾀﾞ^ﾀﾛｳ='))


    def test_findscu_missing_tags(self):
        # dcmodify -e Rows DummyCTInvalidRows.dcm -gst -gse -gin
        UploadInstance(_REMOTE, 'DummyCT.dcm')
        UploadInstance(_REMOTE, 'DummyCTInvalidRows.dcm')

        i = CallFindScu([ '-k', '0008,0052=IMAGES', '-k', 'PatientName', '-k', 'Rows', '-k', 'Columns' ])

        # We have 2 instances...
        patientNames = re.findall('\(0010,0010\).*?\[(.*?)\]', i)
        self.assertEqual(2, len(patientNames))
        self.assertEqual('KNIX', patientNames[0])
        self.assertEqual('KNIX', patientNames[1])

        columns = re.findall('\(0028,0011\) US ([0-9]+)', i)
        self.assertEqual(2, len(columns))
        self.assertEqual('512', columns[0])
        self.assertEqual('512', columns[1])
        
        # ...but only 1 value for the "Rows" tag
        rows = re.findall('\(0028,0010\) US ([0-9]+)', i)
        self.assertEqual(1, len(rows))
        self.assertEqual('512', rows[0])



    def test_bitbucket_issue_131(self):
        # "Orthanc PACS silently fails to C-MOVE due to duplicate
        # StudyInstanceUID in it's database."
        # https://bugs.orthanc-server.com/show_bug.cgi?id=131

        # Insert 2 instances, with the same StudyInstanceUID, but with
        # different patient IDs. Orthanc will create 2 distincts
        # patients, and the hierarchy of resources above the two
        # instances will be fully disjoint.
        UploadInstance(_REMOTE, 'PatientIdsCollision/Issue131-a.dcm')
        UploadInstance(_REMOTE, 'PatientIdsCollision/Issue131-b.dcm')

        self.assertEqual(2, len(DoGet(_REMOTE, '/patients')))
        self.assertEqual(2, len(DoGet(_REMOTE, '/studies')))

        a = DoPost(_REMOTE, '/modalities/self/query', {
            'Level' : 'Study',
            'Query' : {"PatientID": "A" }})['ID']

        # 1 study is matched
        self.assertEqual(1, len(DoGet(_REMOTE, '/queries/%s/answers' % a)))

        self.assertEqual(0, len(DoGet(_LOCAL, '/instances')))
        WaitAllNewJobsDone(_REMOTE, lambda: DoPost
                           (_REMOTE, '/queries/%s/retrieve' % a,
                            '{"TargetAet":"ORTHANCTEST","Synchronous":false}'))

        # The two studies are matched, as we made the request at the
        # Study level, thus the shared StudyInstanceUID is used as the key
        self.assertEqual(2, len(DoGet(_LOCAL, '/instances')))


        # Match the 2 studies
        a = DoPost(_REMOTE, '/modalities/self/query', {
            'Level' : 'Study',
            'Query' : {"StudyInstanceUID": "2.25.123" }})['ID']
        self.assertEqual(2, len(DoGet(_REMOTE, '/queries/%s/answers' % a)))
        DropOrthanc(_LOCAL)
        self.assertEqual(0, len(DoGet(_LOCAL, '/instances')))
        WaitAllNewJobsDone(_REMOTE, lambda: DoPost
                           (_REMOTE, '/queries/%s/retrieve' % a,
                            '{"TargetAet":"ORTHANCTEST","Synchronous":false}'))
        self.assertEqual(2, len(DoGet(_LOCAL, '/instances')))

        
        # Same test, at the patient level => only 1 instance is transfered
        a = DoPost(_REMOTE, '/modalities/self/query', {
            'Level' : 'Patient',
            'Query' : {"PatientID": "A" }})['ID']
        self.assertEqual(1, len(DoGet(_REMOTE, '/queries/%s/answers' % a)))
        DropOrthanc(_LOCAL)
        self.assertEqual(0, len(DoGet(_LOCAL, '/instances')))
        WaitAllNewJobsDone(_REMOTE, lambda: DoPost
                           (_REMOTE, '/queries/%s/retrieve' % a,
                            '{"TargetAet":"ORTHANCTEST","Synchronous":false}'))
        self.assertEqual(1, len(DoGet(_LOCAL, '/instances')))
        

        # Same test, at the series level => only 1 instance is transfered
        a = DoPost(_REMOTE, '/modalities/self/query', {
            'Level' : 'Series',
            'Query' : {"PatientID": "A" }})['ID']
        self.assertEqual(1, len(DoGet(_REMOTE, '/queries/%s/answers' % a)))
        DropOrthanc(_LOCAL)
        self.assertEqual(0, len(DoGet(_LOCAL, '/instances')))
        WaitAllNewJobsDone(_REMOTE, lambda: DoPost
                           (_REMOTE, '/queries/%s/retrieve' % a,
                            '{"TargetAet":"ORTHANCTEST","Synchronous":false}'))
        self.assertEqual(1, len(DoGet(_LOCAL, '/instances')))
        

    def test_bitbucket_issue_136(self):
        UploadInstance(_REMOTE, 'Issue137.dcm')
        i = CallFindScu([ '-k', '0008,0052=STUDY', '-k', '0010,0010', '-k', '0028,0010', '-k', '0040,0275' ])
        patientNames = re.findall('\(0010,0010\).*?\[(.*?)\]', i)
        self.assertEqual(1, len(patientNames))
        self.assertEqual('John Doe', patientNames[0])


    def test_anonymize_relationships_4(self):
        # https://groups.google.com/d/msg/orthanc-users/UkcsqyTpszE/bXUpzU0vAAAJ
        sr1 = UploadInstance(_REMOTE, 'HierarchicalAnonymization/2019-03-28/CR000000.dcm')['ID']
        mr1 = UploadInstance(_REMOTE, 'HierarchicalAnonymization/2019-03-28/PR000000.dcm')['ID']
        study = '0c923249-d52121a9-2b7167f7-6b85534f-0943697e'
        
        anonymized = DoPost(_REMOTE, '/studies/%s/anonymize' % study, '{}',
                            'application/json')['ID']
        series = DoGet(_REMOTE, '/studies/%s/series' % anonymized)
        self.assertEqual(2, len(series))

        cr = list(filter(lambda x: x['MainDicomTags']['Modality'] == 'CR', series))
        pr = list(filter(lambda x: x['MainDicomTags']['Modality'] == 'PR', series))
        self.assertEqual(1, len(cr))
        self.assertEqual(1, len(pr))
        self.assertEqual(1, len(cr[0]['Instances']))
        self.assertEqual(1, len(pr[0]['Instances']))

        crinstance = DoGet(_REMOTE, '/instances/%s' % cr[0]['Instances'][0])
        tags = DoGet(_REMOTE, '/instances/%s/tags?short' % pr[0]['Instances'][0])

        self.assertEqual(tags['0008,1115'][0]['0008,1140'][0]['0008,1155'],
                         crinstance['MainDicomTags']['SOPInstanceUID'])
        self.assertEqual(tags['0008,1115'][0]['0008,1140'][0]['0008,1150'],
                         '1.2.840.10008.5.1.4.1.1.1')  # SOP class for CR Image Storage

        # This fails on Orthanc <= 1.5.6
        self.assertEqual(tags['0008,1115'][0]['0020,000e'],
                         cr[0]['MainDicomTags']['SeriesInstanceUID'])


    def test_anonymize_relationships_5(self):
        ct1 = UploadInstance(_REMOTE, 'HierarchicalAnonymization/RTH/CT01.dcm')
        rt1 = UploadInstance(_REMOTE, 'HierarchicalAnonymization/RTH/RT.dcm')
        oStudyId = ct1['ParentStudy']
        oCtInstanceId = ct1['ID']
        oRtInstanceId = rt1['ID']

        oCtTags = DoGet(_REMOTE, '/instances/%s/tags?simplify' % oCtInstanceId)
        oRtTags = DoGet(_REMOTE, '/instances/%s/tags?simplify' % oRtInstanceId)

        # first validate the relationships in the source data
        oStudyUID = oCtTags['StudyInstanceUID']
        oRtSeriesUID = oRtTags['SeriesInstanceUID']
        oRtInstanceUID = oRtTags['SOPInstanceUID']
        oRtFrameOfReferenceUID = oRtTags['ReferencedFrameOfReferenceSequence'][0]['FrameOfReferenceUID']
        oCtSeriesUID = oCtTags['SeriesInstanceUID']
        oCtInstanceUID = oCtTags['SOPInstanceUID']
        oCtFrameOfReferenceUID = oCtTags['FrameOfReferenceUID']

        oContourSequenceCount = len(oRtTags['ROIContourSequence'][0]['ContourSequence'])
        self.assertEqual(oCtFrameOfReferenceUID, oRtFrameOfReferenceUID)
        self.assertEqual(oStudyUID, oRtTags['ReferencedFrameOfReferenceSequence'][0]['RTReferencedStudySequence'][0]['ReferencedSOPInstanceUID'])
        self.assertEqual(oCtSeriesUID, oRtTags['ReferencedFrameOfReferenceSequence'][0]['RTReferencedStudySequence'][0]['RTReferencedSeriesSequence'][0]['SeriesInstanceUID'])
        self.assertEqual(oCtInstanceUID, oRtTags['ReferencedFrameOfReferenceSequence'][0]['RTReferencedStudySequence'][0]['RTReferencedSeriesSequence'][0]['ContourImageSequence'][0]['ReferencedSOPInstanceUID'])
        self.assertEqual(oCtInstanceUID, oRtTags['ROIContourSequence'][0]['ContourSequence'][oContourSequenceCount-1]['ContourImageSequence'][0]['ReferencedSOPInstanceUID'])

        ### anonymize

        aStudyId = DoPost(_REMOTE, '/studies/%s/anonymize' % oStudyId, '{}',
                            'application/json')['ID']

        ### validate

        aSeries = DoGet(_REMOTE, '/studies/%s/series' % aStudyId)
        self.assertEqual(2, len(aSeries))

        aCt = list(filter(lambda x: x['MainDicomTags']['Modality'] == 'CT', aSeries))
        aRt = list(filter(lambda x: x['MainDicomTags']['Modality'] == 'RTSTRUCT', aSeries))
        aCtInstanceId = aCt[0]['Instances'][0]
        aRtInstanceId = aRt[0]['Instances'][0]
        aCtTags = DoGet(_REMOTE, '/instances/%s/tags?simplify' % aCtInstanceId)
        aRtTags = DoGet(_REMOTE, '/instances/%s/tags?simplify' % aRtInstanceId)

        # now validate the relationships in the anonymized data
        aStudyUID = aCtTags['StudyInstanceUID']
        aRtSeriesUID = aRtTags['SeriesInstanceUID']
        aRtInstanceUID = aRtTags['SOPInstanceUID']
        aRtFrameOfReferenceUID = aRtTags['ReferencedFrameOfReferenceSequence'][0]['FrameOfReferenceUID']
        aCtSeriesUID = aCtTags['SeriesInstanceUID']
        aCtInstanceUID = aCtTags['SOPInstanceUID']
        aCtFrameOfReferenceUID = aCtTags['FrameOfReferenceUID']

        aContourSequenceCount = len(aRtTags['ROIContourSequence'][0]['ContourSequence'])
        # make sure all UIDs have been updated
        self.assertNotEqual(oStudyUID, aStudyUID)
        self.assertNotEqual(oRtSeriesUID, aRtSeriesUID)
        self.assertNotEqual(oRtInstanceUID, aRtInstanceUID)
        self.assertNotEqual(oRtFrameOfReferenceUID, aRtFrameOfReferenceUID)
        self.assertNotEqual(oCtSeriesUID, aCtSeriesUID)
        self.assertNotEqual(oCtInstanceUID, aCtInstanceUID)
        self.assertNotEqual(oCtFrameOfReferenceUID, aCtFrameOfReferenceUID)

        # validate the relationships
        self.assertEqual(oContourSequenceCount, aContourSequenceCount)
        self.assertEqual(aCtFrameOfReferenceUID, aRtFrameOfReferenceUID)
        self.assertEqual(aStudyUID, aRtTags['ReferencedFrameOfReferenceSequence'][0]['RTReferencedStudySequence'][0]['ReferencedSOPInstanceUID'])
        self.assertEqual(aCtSeriesUID, aRtTags['ReferencedFrameOfReferenceSequence'][0]['RTReferencedStudySequence'][0]['RTReferencedSeriesSequence'][0]['SeriesInstanceUID'])
        self.assertEqual(aCtInstanceUID, aRtTags['ReferencedFrameOfReferenceSequence'][0]['RTReferencedStudySequence'][0]['RTReferencedSeriesSequence'][0]['ContourImageSequence'][0]['ReferencedSOPInstanceUID'])
        self.assertEqual(aCtInstanceUID, aRtTags['ROIContourSequence'][0]['ContourSequence'][aContourSequenceCount-1]['ContourImageSequence'][0]['ReferencedSOPInstanceUID'])

    def test_anonymize_relationships_5b(self):
        # same test as previous one but, this time, we force the StudyInstanceUID
        ct1 = UploadInstance(_REMOTE, 'HierarchicalAnonymization/RTH/CT01.dcm')
        rt1 = UploadInstance(_REMOTE, 'HierarchicalAnonymization/RTH/RT.dcm')
        oStudyId = ct1['ParentStudy']
        oCtInstanceId = ct1['ID']
        oRtInstanceId = rt1['ID']

        oCtTags = DoGet(_REMOTE, '/instances/%s/tags?simplify' % oCtInstanceId)
        oRtTags = DoGet(_REMOTE, '/instances/%s/tags?simplify' % oRtInstanceId)

        ### anonymize while forcing the StudyInstanceUID

        aStudyId = DoPost(_REMOTE, '/studies/%s/anonymize' % oStudyId, '{ "Replace" : { "StudyInstanceUID" : "1.2.3.4"}, "Force": true}',
                            'application/json')['ID']

        ### validate

        aSeries = DoGet(_REMOTE, '/studies/%s/series' % aStudyId)
        self.assertEqual(2, len(aSeries))

        aCt = list(filter(lambda x: x['MainDicomTags']['Modality'] == 'CT', aSeries))
        aRt = list(filter(lambda x: x['MainDicomTags']['Modality'] == 'RTSTRUCT', aSeries))
        aCtInstanceId = aCt[0]['Instances'][0]
        aRtInstanceId = aRt[0]['Instances'][0]
        aCtTags = DoGet(_REMOTE, '/instances/%s/tags?simplify' % aCtInstanceId)
        aRtTags = DoGet(_REMOTE, '/instances/%s/tags?simplify' % aRtInstanceId)

        self.assertEqual("1.2.3.4", aCtTags['StudyInstanceUID'])
        self.assertEqual("1.2.3.4", aRtTags['StudyInstanceUID'])
        self.assertEqual("1.2.3.4", aRtTags['ReferencedFrameOfReferenceSequence'][0]['RTReferencedStudySequence'][0]['ReferencedSOPInstanceUID'])
        

    def test_bitbucket_issue_140(self):
        # "Modifying private tags with REST API changes VR from LO to
        # UN." This test fails if DCMTK <= 3.6.1 (e.g. fails on Ubuntu 16.04).
        # https://bugs.orthanc-server.com/show_bug.cgi?id=140
        source = UploadInstance(_REMOTE, 'Issue140.dcm') ['ID']
        series = DoGet(_REMOTE, '/instances/%s' % source) ['ParentSeries']

        target = DoPost(_REMOTE, '/series/%s/modify' % series, {
            'Replace' : { 'RadioButton3' : 'aaabbbccc' },
            'PrivateCreator' : 'RadioLogic',  # <= the trick is here
        }, 'application/json') ['ID']

        instances = DoGet(_REMOTE, '/series/%s/instances' % target)
        self.assertEqual(1, len(instances))

        tags = DoGet(_REMOTE, '/instances/%s/tags' % source)
        t = tags['4321,1012']
        self.assertEqual('String', t['Type'])
        self.assertEqual('RadioButton3', t['Name'])
        self.assertEqual('RadioLogic', t['PrivateCreator'])
        self.assertEqual('jklmopq', t['Value'])

        tags = DoGet(_REMOTE, '/instances/%s/tags' % instances[0]['ID'])
        t = tags['4321,1012']
        self.assertEqual('String', t['Type'])   # This fails if DCMTK <= 3.6.1
        self.assertEqual('RadioButton3', t['Name'])
        self.assertEqual('RadioLogic', t['PrivateCreator'])
        self.assertEqual('aaabbbccc', t['Value'])


    def test_find_normalize(self):
        # https://groups.google.com/d/msg/orthanc-users/AIwooGjsh94/YL28MNY4AgAJ
        
        UploadInstance(_REMOTE, 'Knee/T1/IM-0001-0001.dcm')

        a = DoPost(_REMOTE, '/modalities/self/query', {
            'Level' : 'Instance',
            'Query' : { 'Rows' : '42' }
        }) ['ID']

        b = DoGet(_REMOTE, '/queries/%s/answers?expand&simplify' % a)
        self.assertEqual(1, len(b))
        self.assertFalse('Rows' in b[0])

        a = DoPost(_REMOTE, '/modalities/self/query', {
            'Level' : 'Instance',
            'Query' : { 'Rows' : '42' },
            'Normalize' : False
        }) ['ID']

        b = DoGet(_REMOTE, '/queries/%s/answers' % a)
        self.assertEqual(0, len(b))

        a = DoPost(_REMOTE, '/modalities/self/query', {
            'Level' : 'Instance',
            'Query' : { 'Rows' : '512' },
            'Normalize' : False
        }) ['ID']

        b = DoGet(_REMOTE, '/queries/%s/answers?expand&simplify' % a)
        self.assertEqual(1, len(b))
        self.assertTrue('Rows' in b[0])
        self.assertEqual('512', b[0]['Rows'])

        a = DoPost(_REMOTE, '/modalities/self/query', {
            'Level' : 'Instance',
            'Query' : { 'Rows' : '' },
            'Normalize' : False
        }) ['ID']

        b = DoGet(_REMOTE, '/queries/%s/answers?expand&simplify' % a)
        self.assertEqual(1, len(b))
        self.assertTrue('Rows' in b[0])
        self.assertEqual('512', b[0]['Rows'])

        self.assertRaises(Exception, lambda: DoPost(
            _REMOTE, '/modalities/self/query', {
                'Level' : 'Instance',
                'Query' : { 'Rows' : '*' },  # Out-of-range value
                'Normalize' : False
            }))


    def test_bitbucket_issue_141(self):
        # https://bugs.orthanc-server.com/show_bug.cgi?id=141
        a = UploadInstance(_REMOTE, 'Issue141.dcm') ['ID']
        study = '494c8037-b237f263-d8f15075-c8cb2280-daf39bd1'

        with open(GetDatabasePath('HelloWorld.pdf'), 'rb') as f:
            pdf = f.read()

        b = DoPost(_REMOTE, '/tools/create-dicom', {
                'Parent' : study,
                'Tags' : {},
                'Content' : 'data:application/pdf;base64,' + base64.b64encode(pdf)
                }) ['ID']
        
        tagsA = DoGet(_REMOTE, '/instances/%s/tags?short' % a)
        tagsB = DoGet(_REMOTE, '/instances/%s/tags?short' % b)
        self.assertEqual(tagsA['0008,0005'], tagsB['0008,0005'])
        self.assertEqual(tagsA['0008,1030'], tagsB['0008,1030'])


    def test_modifying_missing_patientid(self):
        # https://groups.google.com/d/msg/orthanc-users/aphG_h1AHVg/rfOTtTPTAgAJ
        UploadInstance(_REMOTE, '2019-06-17-VedranZdesic.dcm')
        DoPost(_REMOTE, '/studies/0c4aca1d-c107a241-6659d6aa-594c674a-a468b94a/modify', {})


    def test_log_level(self):
        # https://bugs.orthanc-server.com/show_bug.cgi?id=65
        original = DoGet(_REMOTE, '/tools/log-level')
        
        DoPut(_REMOTE, '/tools/log-level', 'default')
        self.assertEqual('default', DoGet(_REMOTE, '/tools/log-level'))
        DoGet(_REMOTE, '/system')

        DoPut(_REMOTE, '/tools/log-level', 'verbose')
        self.assertEqual('verbose', DoGet(_REMOTE, '/tools/log-level'))
        DoGet(_REMOTE, '/system')

        DoPut(_REMOTE, '/tools/log-level', 'trace')
        self.assertEqual('trace', DoGet(_REMOTE, '/tools/log-level'))
        DoGet(_REMOTE, '/system')

        self.assertRaises(Exception, lambda: DoPut(_REMOTE, '/tools/log-level', 'nope'))
        
        # Switch back to the original log level
        DoPut(_REMOTE, '/tools/log-level', original)


    def test_upload_compressed(self):
        # New in Orthanc 1.6.0
        with open(GetDatabasePath('DummyCT.dcm.gz'), 'rb') as f:
            d = f.read()

        self.assertRaises(Exception, lambda: DoPost(_REMOTE, '/instances', d, 'application/dicom'))
        
        self.assertRaises(Exception, lambda: DoPost(_REMOTE, '/instances', d, 'application/dicom',
                                                    headers = { 'Content-Encoding' : 'nope' }))
        
        a = DoPost(_REMOTE, '/instances', d, 'application/dicom',
                   headers = { 'Content-Encoding' : 'gzip' })
        self.assertEqual('66a662ce-7430e543-bad44d47-0dc5a943-ec7a538d', a['ID'])
        
        
    def test_study_series_find_inconsistency(self):
        # https://groups.google.com/forum/#!topic/orthanc-users/bLv6Z11COy0

        def CountAnswers(query):
            a = DoPost(_REMOTE, 'modalities/self/query', query)
            return len(DoGet(_REMOTE, '%s/answers' % a['Path']))

        # This instance has "SeriesDescription" (0008,103e) tag, but no
        # "ProtocolName" (0018,1030). Both of those tags are part of
        # the "main DICOM tags" of Orthanc.
        UploadInstance(_REMOTE, 'Issue137.dcm')

        
        self.assertEqual(1, CountAnswers({
            'Level' : 'Study',
        }))

        self.assertEqual(1, CountAnswers({
            'Level' : 'Series',
        }))

        
        ##
        ## "SeriesDescription" is present, and has VR "CS" => wildcard is allowed
        ## http://dicom.nema.org/medical/dicom/2019e/output/chtml/part04/sect_C.2.2.2.4.html
        ##

        # At the study level, the "SeriesDescription" tag is not allowed, but
        # is wiped out by the normalization
        self.assertEqual(0, CountAnswers({
            'Level' : 'Study',
            'Query' : {
                'SeriesDescription' : 'NOPE'
            },
            'Normalize' : False
        }))
        self.assertEqual(0, CountAnswers({
            # This test fails on Orthanc <= 1.5.8
            'Level' : 'Study',
            'Query' : {
                'ImageComments' : '*'  # Wildcard matching => no match, as the tag is absent
            },
            'Normalize' : False
        }))
        self.assertEqual(1, CountAnswers({
            'Level' : 'Study',
            'Query' : {
                'ImageComments' : ''
            },
            'Normalize' : False
        }))
        self.assertEqual(1, CountAnswers({
            'Level' : 'Study',
            'Query' : {
                'SeriesDescription' : 'THIS^VALUE^IS^WIPED^OUT'
            },
            'Normalize' : True
        }))
        self.assertEqual(1, CountAnswers({
            'Level' : 'Study',
            'Query' : {
                'ImageComments' : '*'  # Matches, as wiped out by the normalization
            },
            'Normalize' : True
        }))
        self.assertEqual(1, CountAnswers({
            'Level' : 'Study',
            'Query' : {
                'ImageComments' : ''
            },
            'Normalize' : True
        }))

        for normalize in [ True, False ]:
            # At the series level, the "SeriesDescription" tag is allowed, and
            # normalization has no effect

            # "Universal matching" will match all entities, including
            # those with the missing tag
            # http://dicom.nema.org/medical/dicom/2019e/output/chtml/part04/sect_C.2.2.2.3.html
            self.assertEqual(1, CountAnswers({
                'Level' : 'Series',
                'Query' : {
                    'SeriesDescription' : ''  # Universal matching
                },
                'Normalize' : normalize,
            }))
            # "Universal matching" will match all entities, including
            # those with the missing tag
            # http://dicom.nema.org/medical/dicom/2019e/output/chtml/part04/sect_C.2.2.2.3.html
            self.assertEqual(1, CountAnswers({
                'Level' : 'Series',
                'Query' : {
                    'SeriesDescription' : '*'  # Wildcard matching
                },
                'Normalize' : normalize,
            }))
            self.assertEqual(1, CountAnswers({
                'Level' : 'Series',
                'Query' : {
                    'SeriesDescription' : '*model*'  # The actual value is "STL model: intraop Report"
                },
                'Normalize' : normalize,
            }))
            self.assertEqual(0, CountAnswers({
                'Level' : 'Series',
                'Query' : {
                    'SeriesDescription' : '*MISMATCHED^VALUE*'
                },
                'Normalize' : normalize,
            }))

            # Universal matching matches any instance, even if the
            # query is at the study-level, and thus if "SeriesDescription"
            # makes no sense
            self.assertEqual(1, CountAnswers({
                'Level' : 'Study',
                'Query' : {
                    'SeriesDescription' : ''  # Universal matching
                },
                'Normalize' : normalize,
            }))
        


        ##
        ## "ProtocolName" is absent, and has VR "CS" => wildcard is allowed
        ##

        # At the study level, the "ProtocolName" tag is not allowed, but
        # is wiped out by the normalization
        self.assertEqual(0, CountAnswers({
            'Level' : 'Study',
            'Query' : {
                'ProtocolName' : 'NOPE'
            },
            'Normalize' : False
        }))
        self.assertEqual(0, CountAnswers({
            'Level' : 'Study',
            'Query' : {
                'ProtocolName' : '*'  # Wildcard matching => no match, as the tag is absent
            },
            'Normalize' : False
        }))
        self.assertEqual(1, CountAnswers({
            'Level' : 'Study',
            'Query' : {
                'ProtocolName' : 'THIS^VALUE^IS^WIPED^OUT'
            },
            'Normalize' : True
        }))
        self.assertEqual(1, CountAnswers({
            'Level' : 'Study',
            'Query' : {
                'ProtocolName' : '*'  # Matches, as wiped out by the normalization
            },
            'Normalize' : True
        }))

        for normalize in [ True, False ]:
            # At the series level, the "ProtocolName" tag is allowed, and
            # normalization has no effect

            self.assertEqual(1, CountAnswers({
                'Level' : 'Series',
                'Query' : {
                    'ProtocolName' : ''  # Universal matching
                },
                'Normalize' : normalize,
            }))
            self.assertEqual(0, CountAnswers({
                'Level' : 'Series',
                'Query' : {
                    'ProtocolName' : '*'  # Wildcard matching => no match, as the tag is absent
                },
                'Normalize' : normalize,
            }))
            self.assertEqual(0, CountAnswers({
                'Level' : 'Series',
                'Query' : {
                    'ProtocolName' : '*MISMATCHED^VALUE*'
                },
                'Normalize' : normalize,
            }))

            self.assertEqual(1, CountAnswers({
                'Level' : 'Study',
                'Query' : {
                    'ProtocolName' : '' # Universal matching
                },
                'Normalize' : normalize,
            }))
            

        ##
        ## "StudyInstanceUID" is present, and has VR "UI" => wildcard is not allowed
        ##

        for level in [ 'Study', 'Series' ] :
            for normalize in [ True, False ]:
                self.assertEqual(1, CountAnswers({
                    'Level' : level,
                    'Query' : {
                        'StudyInstanceUID' : ''  # Universal matching
                    },
                    'Normalize' : normalize,
                }))
                self.assertEqual(0, CountAnswers({
                    'Level' : level,
                    'Query' : {
                        'StudyInstanceUID' : 'MISMATCHED^VALUE'
                    },
                    'Normalize' : normalize,
                }))
                self.assertEqual(1, CountAnswers({
                    'Level' : level,
                    'Query' : {
                        'StudyInstanceUID' : '4.5.6'  # This is the actual value
                    },
                    'Normalize' : normalize,
                }))

                # Wildcard matching is not allowed for this VR
                # This test fails on Orthanc <= 1.5.8
                self.assertRaises(Exception, lambda: CountAnswers({
                    'Level' : level,
                    'Query' : {
                        'StudyInstanceUID' : '*'
                    },
                    'Normalize' : normalize,
                }))


    def test_rendered(self):
        # New in Orthanc 1.6.0
        i = UploadInstance(_REMOTE, 'ColorTestMalaterre.dcm')['ID']
        im = GetImage(_REMOTE, '/instances/%s/rendered' % i)
        self.assertEqual("RGB", im.mode)
        self.assertEqual(41, im.size[0])
        self.assertEqual(41, im.size[1])

        # http://effbot.org/zone/pil-comparing-images.htm
        truth = Image.open(GetDatabasePath('ColorTestMalaterre.png'))
        self.assertTrue(ImageChops.difference(im, truth).getbbox() is None)

        im = GetImage(_REMOTE, '/instances/%s/rendered?width=10' % i)
        self.assertEqual("RGB", im.mode)
        self.assertEqual(10, im.size[0])
        self.assertEqual(10, im.size[1])
        
        im = GetImage(_REMOTE, '/instances/%s/rendered?height=10' % i)
        self.assertEqual("RGB", im.mode)
        self.assertEqual(10, im.size[0])
        self.assertEqual(10, im.size[1])
                
        im = GetImage(_REMOTE, '/instances/%s/rendered?height=128' % i)
        self.assertEqual("RGB", im.mode)
        self.assertEqual(128, im.size[0])
        self.assertEqual(128, im.size[1])
                
        im = GetImage(_REMOTE, '/instances/%s/rendered?height=10&smooth=0' % i)
        self.assertEqual("RGB", im.mode)
        self.assertEqual(10, im.size[0])
        self.assertEqual(10, im.size[1])
                
        im = GetImage(_REMOTE, '/instances/%s/rendered?height=10&smooth=1' % i)
        self.assertEqual("RGB", im.mode)
        self.assertEqual(10, im.size[0])
        self.assertEqual(10, im.size[1])
                
        im = GetImage(_REMOTE, '/instances/%s/rendered?height=5&width=10' % i)
        self.assertEqual("RGB", im.mode)
        self.assertEqual(5, im.size[0])
        self.assertEqual(5, im.size[1])

        
        # Grayscale image
        i = UploadInstance(_REMOTE, 'Brainix/Flair/IM-0001-0001.dcm')['ID']
        im = GetImage(_REMOTE, '/instances/%s/rendered' % i)
        self.assertEqual("L", im.mode)
        self.assertEqual(288, im.size[0])
        self.assertEqual(288, im.size[1])
        self.assertEqual(0, im.getpixel((0, 0)))

        # Those are the original windowing parameters that are written
        # inside the DICOM file
        im2 = GetImage(_REMOTE, '/instances/%s/rendered?window-center=248.009544468547&window-width=431.351843817788' % i)
        self.assertEqual("L", im2.mode)
        self.assertEqual(288, im2.size[0])
        self.assertEqual(288, im2.size[1])
        self.assertTrue(ImageChops.difference(im, im2).getbbox() is None)        

        im = GetImage(_REMOTE, '/instances/%s/rendered?width=512&smooth=0' % i)
        self.assertEqual("L", im.mode)
        self.assertEqual(512, im.size[0])
        self.assertEqual(512, im.size[1])

        im = GetImage(_REMOTE, '/instances/%s/rendered?width=10&smooth=0' % i)
        self.assertEqual("L", im.mode)
        self.assertEqual(10, im.size[0])
        self.assertEqual(10, im.size[1])

        im = GetImage(_REMOTE, '/instances/%s/rendered?width=10&smooth=1' % i)
        self.assertEqual("L", im.mode)
        self.assertEqual(10, im.size[0])
        self.assertEqual(10, im.size[1])

        im = GetImage(_REMOTE, '/instances/%s/rendered?width=1&window-center=-1000' % i)
        self.assertEqual("L", im.mode)
        self.assertEqual(1, im.size[0])
        self.assertEqual(1, im.size[1])
        self.assertEqual(255, im.getpixel((0, 0)))

        im = GetImage(_REMOTE, '/instances/%s/rendered?width=1&window-center=1000' % i)
        self.assertEqual("L", im.mode)
        self.assertEqual(1, im.size[0])
        self.assertEqual(1, im.size[1])
        self.assertEqual(0, im.getpixel((0, 0)))

        
        # Test monochrome 1
        i = UploadInstance(_REMOTE, 'Issue44/Monochrome1.dcm')['ID']
        im = GetImage(_REMOTE, '/instances/%s/rendered' % i)
        self.assertEqual("L", im.mode)
        self.assertEqual(2010, im.size[0])
        self.assertEqual(2446, im.size[1])
        self.assertEqual(0, im.getpixel((0, 0)))
        im = GetImage(_REMOTE, '/instances/%s/rendered?width=20' % i)
        self.assertEqual("L", im.mode)
        self.assertEqual(20, im.size[0])
        self.assertEqual(24, im.size[1])
        im = GetImage(_REMOTE, '/instances/%s/rendered?height=24' % i)
        self.assertEqual("L", im.mode)
        self.assertEqual(20, im.size[0])
        self.assertEqual(24, im.size[1])
        im = GetImage(_REMOTE, '/instances/%s/rendered?width=10&height=24' % i)
        self.assertEqual("L", im.mode)
        self.assertEqual(10, im.size[0])
        self.assertEqual(12, im.size[1])
        im = GetImage(_REMOTE, '/instances/%s/rendered?width=40&height=24' % i)
        self.assertEqual("L", im.mode)
        self.assertEqual(20, im.size[0])
        self.assertEqual(24, im.size[1])


    def test_bitbucket_issue_154(self):
        # "Matching against list of UID-s by C-MOVE"
        # https://bugs.orthanc-server.com/show_bug.cgi?id=154
        a = UploadInstance(_REMOTE, 'Issue154-d1.dcm') ['ID']
        b = UploadInstance(_REMOTE, 'Issue154-d2.dcm') ['ID']

        study = '1.2.826.0.1.3680043.8.498.35214236271657363033644818354280454731'
        series1 = '1.2.826.0.1.3680043.8.498.12243321927795467590791662266352305113'
        series2 = '1.2.826.0.1.3680043.8.498.43769499931624584079690260699536473555'

        # C-FIND is working on list of UIDs
        i = CallFindScu([ '-k', 'QueryRetrieveLevel=SERIES',
                          '-k', 'StudyInstanceUID=%s' % study,
                          '-k', 'SeriesInstanceUID=%s\\%s' % (series1, series2) ])
        series = re.findall('\(0020,000e\).*?\[(.*?)\]', i)
        self.assertEqual(2, len(series))
        self.assertTrue(series1 in series)
        self.assertTrue(series2 in series)
        
        # Individual retrieval is working in Orthanc < 1.6.0
        self.assertEqual(0, len(DoGet(_LOCAL, '/instances')))
        self.assertTrue(MonitorJob(_REMOTE, lambda: CallMoveScu([
            '--study', '-k', 'QueryRetrieveLevel=SERIES',
            '-k', 'StudyInstanceUID=%s' % study,
            '-k', 'SeriesInstanceUID=%s' % series1,
            ])))
        self.assertTrue(MonitorJob(_REMOTE, lambda: CallMoveScu([
            '--study', '-k', 'QueryRetrieveLevel=SERIES',
            '-k', 'StudyInstanceUID=%s' % study,
            '-k', 'SeriesInstanceUID=%s' % series2,
            ])))
        self.assertEqual(2, len(DoGet(_LOCAL, '/instances')))

        DropOrthanc(_LOCAL)

        # But list matching is working only in Orthanc >= 1.6.0
        self.assertEqual(0, len(DoGet(_LOCAL, '/instances')))
        self.assertTrue(MonitorJob(_REMOTE, lambda: CallMoveScu([
            '--study', '-k', 'QueryRetrieveLevel=SERIES',
            '-k', 'StudyInstanceUID=%s' % study,
            '-k', 'SeriesInstanceUID=%s\\%s' % (series1, series2),
            ])))
        self.assertEqual(2, len(DoGet(_LOCAL, '/instances')))


    def test_storage_commitment_api(self):
        # Storage commitment is available since Orthanc 1.6.0

        def WaitTransaction(uid):
            while True:
                s = DoGet(_REMOTE, '/storage-commitment/%s' % uid)
                if s['Status'] != 'Pending':
                    return s
                else:
                    time.sleep(0.01)
        
        instance = UploadInstance(_REMOTE, 'DummyCT.dcm')
        sopClassUid = '1.2.840.10008.5.1.4.1.1.4'
        sopInstanceUid = '1.2.840.113619.2.176.2025.1499492.7040.1171286242.109'

        # Against self
        transaction = DoPost(_REMOTE, '/modalities/self/storage-commitment', {
            "DicomInstances" : [ [ sopClassUid, sopInstanceUid ] ],
        }) ['ID']
        self.assertTrue(transaction.startswith('2.25.'))

        result = WaitTransaction(transaction)
        self.assertEqual('ORTHANC', result['RemoteAET'])
        self.assertEqual('Success', result['Status'])
        self.assertEqual(1, len(result['Success']))
        self.assertEqual(0, len(result['Failures']))
        self.assertEqual(sopClassUid, result['Success'][0]['SOPClassUID'])
        self.assertEqual(sopInstanceUid, result['Success'][0]['SOPInstanceUID'])
        
        tmp = DoPost(_REMOTE, '/modalities/self/storage-commitment', {
            "DicomInstances" : [
                { 'SOPClassUID' : sopClassUid,
                  'SOPInstanceUID' : sopInstanceUid },
            ],
        })
        self.assertEqual(tmp['Path'], '/storage-commitment/%s' % tmp['ID'])
        self.assertEqual(result, WaitTransaction(transaction))

        tmp = DoPost(_REMOTE, '/modalities/self/storage-commitment', {
            "Resources" : [
                instance['ID'],
                instance['ParentSeries'],
                instance['ParentStudy'],
                instance['ParentPatient'],
            ]
        })
        self.assertEqual(tmp['Path'], '/storage-commitment/%s' % tmp['ID'])
        self.assertEqual(result, WaitTransaction(transaction))

        
        transaction = DoPost(_REMOTE, '/modalities/self/storage-commitment', {
            "DicomInstances" : [
                [ 'nope', 'nope2' ],
                [ sopClassUid, sopInstanceUid ],
            ],
        }) ['ID']
        self.assertTrue(transaction.startswith('2.25.'))

        result = WaitTransaction(transaction)
        self.assertEqual('ORTHANC', result['RemoteAET'])
        self.assertEqual('Failure', result['Status'])
        self.assertEqual(1, len(result['Success']))
        self.assertEqual(1, len(result['Failures']))
        self.assertEqual(sopClassUid, result['Success'][0]['SOPClassUID'])
        self.assertEqual(sopInstanceUid, result['Success'][0]['SOPInstanceUID'])
        self.assertEqual('nope', result['Failures'][0]['SOPClassUID'])
        self.assertEqual('nope2', result['Failures'][0]['SOPInstanceUID'])
        self.assertEqual(274, result['Failures'][0]['FailureReason'])

        # Cannot remove items from a failed storage commitment transaction
        self.assertRaises(Exception, lambda:
                          DoPost(_REMOTE, '/storage-commitment/%s/remove' % transaction))
        
        
        # Against Orthanc 0.8.6, that does not support storage commitment
        if not IsOrthancVersionAbove(_LOCAL, 1, 11, 2):  # don't know which specific version the behaviour changed but this fails with 0.8.6
            self.assertRaises(Exception, lambda:
                            DoPost(_REMOTE, '/modalities/orthanctest/storage-commitment', {
                                "DicomInstances" : [
                                    [ sopClassUid, sopInstanceUid ],
                                ]
                            }))



    def test_storage_commitment_store(self):
        # Storage commitment is available since Orthanc 1.6.0

        def WaitTransaction(uid):
            while True:
                s = DoGet(_REMOTE, '/storage-commitment/%s' % uid)
                if s['Status'] != 'Pending':
                    return s
                else:
                    time.sleep(0.01)

        i = UploadInstance(_REMOTE, 'DummyCT.dcm')['ID']
        self.assertEqual(1, len(DoGet(_REMOTE, '/instances')))
        self.assertEqual(0, len(DoGet(_LOCAL, '/instances')))

        # The Orthanc 0.8.6 from "_LOCAL" does not support storage commitment
        if not IsOrthancVersionAbove(_LOCAL, 1, 11, 2):  # don't know which specific version the behaviour changed but this fails with 0.8.6
            self.assertRaises(Exception, lambda: DoPost(_REMOTE, '/modalities/orthanctest/store', {
                'Resources' : [ i ],
                'StorageCommitment' : True,
                }))

        j = DoPost(_REMOTE, '/modalities/orthanctest/store', {
            'Resources' : [ i ],
            'StorageCommitment' : False,
            })
        self.assertEqual(1, len(DoGet(_LOCAL, '/instances')))

        j = DoPost(_REMOTE, '/modalities/self/store', {
            'Resources' : [ i ],
            'StorageCommitment' : True,
            })

        transaction = j['StorageCommitmentTransactionUID']
        self.assertTrue(transaction.startswith('2.25.'))

        result = WaitTransaction(transaction)
        self.assertEqual('ORTHANC', result['RemoteAET'])
        self.assertEqual('Success', result['Status'])
        self.assertEqual(1, len(result['Success']))
        self.assertEqual(0, len(result['Failures']))
        self.assertEqual('1.2.840.10008.5.1.4.1.1.4', result['Success'][0]['SOPClassUID'])
        self.assertEqual('1.2.840.113619.2.176.2025.1499492.7040.1171286242.109',
                         result['Success'][0]['SOPInstanceUID'])

        self.assertEqual(1, len(DoGet(_REMOTE, '/instances')))
        DoPost(_REMOTE, '/storage-commitment/%s/remove' % transaction)
        self.assertEqual(0, len(DoGet(_REMOTE, '/instances')))


    def test_store_straight(self):  # New in Orthanc 1.6.1
        self.assertEqual(0, len(DoGet(_LOCAL, '/instances')))
        self.assertEqual(0, len(DoGet(_REMOTE, '/instances')))

        with open(GetDatabasePath('DummyCT.dcm'), 'rb') as f:
            dicom = f.read()

        self.assertRaises(Exception, lambda: DoPost(
            _REMOTE, '/modalities/orthanctest/store-straight', 'nope', 'nope'))

        answer = DoPost(_REMOTE, '/modalities/orthanctest/store-straight', dicom, 'nope')

        self.assertEqual('1.2.840.10008.5.1.4.1.1.4',
                         answer['SOPClassUID'])
        self.assertEqual('1.2.840.113619.2.176.2025.1499492.7040.1171286242.109',
                         answer['SOPInstanceUID'])
        
        self.assertEqual(1, len(DoGet(_LOCAL, '/instances')))
        self.assertEqual(0, len(DoGet(_REMOTE, '/instances')))


    def test_storescu_transcoding(self):  # New in Orthanc 1.7.0       
        # Add a RLE-encoded DICOM file
        i = UploadInstance(_REMOTE, 'TransferSyntaxes/1.2.840.10008.1.2.5.dcm')['ID']
        self.assertEqual(0, len(DoGet(_LOCAL, '/instances')))
        self.assertEqual(1, len(DoGet(_REMOTE, '/instances')))
        rleSize = len(DoGet(_REMOTE, '/instances/%s/file' % i))

        # Export the instance, with transcoding: "_REMOTE" is the
        # Orthanc server being tested
        try:
            DoDelete(_REMOTE, '/modalities/toto')
        except:
            pass

        params = DoGet(_REMOTE, '/modalities?expand') ['orthanctest']
        DoPut(_REMOTE, '/modalities/toto', params)
        DoPost(_REMOTE, '/modalities/toto/store', str(i), 'text/plain')
        j = DoGet(_LOCAL, '/instances')
        self.assertEqual(1, len(j))
        uncompressedSize = len(DoGet(_LOCAL, '/instances/%s/file' % j[0]))
        self.assertTrue(uncompressedSize > rleSize / 2)

        # Export, with transcoding disabled => this fails with 0.8.6 but not with more recent versions
        params['AllowTranscoding'] = False
        DoPut(_REMOTE, '/modalities/toto', params)
        if not IsOrthancVersionAbove(_LOCAL, 1, 11, 2):  # don't know which specific version the behaviour changed but this fails with 0.8.6
            self.assertRaises(Exception, lambda: DoPost(_REMOTE, '/modalities/toto/store', str(i), 'text/plain'))
        else:
            DoPost(_REMOTE, '/modalities/toto/store', str(i), 'text/plain')
        DoDelete(_REMOTE, '/modalities/toto')


    def test_bitbucket_issue_169(self):
        with open(GetDatabasePath('Issue169.dcm.bz2'), 'rb') as f:
            dicom = bz2.decompress(f.read())

        self.assertEqual('1.2.840.10008.1.2.1', GetTransferSyntax(dicom))

        self.assertEqual(44350560, len(dicom))
        i = DoPost(_REMOTE, '/instances', dicom, 'application/dicom') ['ID']
        
        tags = DoGet(_REMOTE, '/instances/%s/tags' % i)
        self.assertEqual('NORMAL', tags['1337,1001']['Value'])
        
        self.assertEqual(0, len(DoGet(_LOCAL, '/instances')))
        DoPost(_REMOTE, '/modalities/orthanctest/store', str(i), 'text/plain')
        j = DoGet(_LOCAL, '/instances')
        self.assertEqual(1, len(j))

        # In Orthanc <= 1.6.1, transfer syntax changed from "Explicit
        # VR Little Endian" (1.2.840.10008.1.2.1) to "Implicit VR
        # Little Endian" (1.2.840.10008.1.2)
        self.assertEqual('1.2.840.10008.1.2.1', GetTransferSyntax(
            DoGet(_LOCAL, '/instances/%s/file' % j[0])))

        # In Orthanc <= 1.6.1, the value of the private tags was lost
        # because of this transcoding
        tags = DoGet(_LOCAL, '/instances/%s/tags' % j[0])
        self.assertEqual('NORMAL', tags['1337,1001']['Value'])


    def test_modify_transcode_instance(self):
        i = UploadInstance(_REMOTE, 'KarstenHilbertRF.dcm')['ID']
        self.assertEqual('1.2.840.10008.1.2.1', GetTransferSyntax(
            DoGet(_REMOTE, '/instances/%s/file' % i)))

        a = ExtractDicomTags(DoGet(_REMOTE, '/instances/%s/file' % i), [ 'SOPInstanceUID' ]) [0]
        self.assertTrue(len(a) > 20)

        SYNTAXES = [
            '1.2.840.10008.1.2',        
            '1.2.840.10008.1.2.1',
            '1.2.840.10008.1.2.2',
            '1.2.840.10008.1.2.4.50',
            '1.2.840.10008.1.2.4.51',
            '1.2.840.10008.1.2.4.57',
            '1.2.840.10008.1.2.4.70',
        ]

        if IsOrthancVersionAbove(_REMOTE, 1, 12, 7):
            SYNTAXES.append('1.2.840.10008.1.2.1.99')  # Deflated Explicit VR Little Endian (cannot be decoded in debug mode if Orthanc is statically linked against DCMTK 3.6.5)


        if HasGdcmPlugin(_REMOTE):
            SYNTAXES = SYNTAXES + [
                '1.2.840.10008.1.2.4.80',  # This makes DCMTK 3.6.2 crash
                '1.2.840.10008.1.2.4.81',  # This makes DCMTK 3.6.2 crash
                '1.2.840.10008.1.2.4.90',  # JPEG2k, unavailable without GDCM
                '1.2.840.10008.1.2.4.91',  # JPEG2k, unavailable without GDCM
            ]
        
        for syntax in SYNTAXES:
            transcoded = DoPost(_REMOTE, '/instances/%s/modify' % i, {
                'Transcode' : syntax,
                'Keep' : [ 'SOPInstanceUID' ],
                'Force' : True,
                })
            
            self.assertEqual(syntax, GetTransferSyntax(transcoded))

            b = ExtractDicomTags(transcoded, [ 'SOPInstanceUID' ]) [0]
            self.assertTrue(len(b) > 20)
            if syntax in [ '1.2.840.10008.1.2.4.50',
                           '1.2.840.10008.1.2.4.51',
                           '1.2.840.10008.1.2.4.81',
                           '1.2.840.10008.1.2.4.91' ]:
                # Lossy transcoding: The SOP instance UID must have changed
                self.assertNotEqual(a, b)
            else:
                self.assertEqual(a, b)

        if IsOrthancVersionAbove(_REMOTE, 1, 12, 7) and HasExtendedFind(_REMOTE):
            transcoded = DoPost(_REMOTE, '/instances/%s/modify' % i, {
                'Transcode' : '1.2.840.10008.1.2.4.50',
                'LossyQuality': 40
                })
            ratio40 = ExtractDicomTags(transcoded, [ 'LossyImageCompressionRatio' ]) [0]

            transcoded = DoPost(_REMOTE, '/instances/%s/modify' % i, {
                'Transcode' : '1.2.840.10008.1.2.4.50',
                'LossyQuality': 80
                })
            ratio80 = ExtractDicomTags(transcoded, [ 'LossyImageCompressionRatio' ]) [0]
            self.assertGreater(ratio40, ratio80)


    def test_archive_transcode(self):
        info = UploadInstance(_REMOTE, 'KarstenHilbertRF.dcm')

        # GET on "/media"
        z, resp = GetArchive(_REMOTE, '/patients/%s/media' % info['ParentPatient'])
        self.assertEqual(2, len(z.namelist()))
        self.assertEqual('1.2.840.10008.1.2.1', GetTransferSyntax(z.read('IMAGES/IM0')))

        self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/patients/%s/media?transcode=nope' % info['ParentPatient']))

        z, resp = GetArchive(_REMOTE, '/patients/%s/media?transcode=1.2.840.10008.1.2.4.50' % info['ParentPatient'])
        self.assertEqual('1.2.840.10008.1.2.4.50', GetTransferSyntax(z.read('IMAGES/IM0')))

        z, resp = GetArchive(_REMOTE, '/studies/%s/media?transcode=1.2.840.10008.1.2.4.51' % info['ParentStudy'])
        self.assertEqual('1.2.840.10008.1.2.4.51', GetTransferSyntax(z.read('IMAGES/IM0')))

        z, resp = GetArchive(_REMOTE, '/series/%s/media?transcode=1.2.840.10008.1.2.4.57' % info['ParentSeries'])
        self.assertEqual('1.2.840.10008.1.2.4.57', GetTransferSyntax(z.read('IMAGES/IM0')))

        if IsOrthancVersionAbove(_REMOTE, 1, 12, 7) and HasExtendedFind(_REMOTE):
            z40, resp40 = GetArchive(_REMOTE, '/patients/%s/media?transcode=1.2.840.10008.1.2.4.50&lossy-quality=40' % info['ParentPatient'])
            z80, resp80 = GetArchive(_REMOTE, '/patients/%s/media?transcode=1.2.840.10008.1.2.4.50&lossy-quality=80' % info['ParentPatient'])

            size40 = sum([zinfo.file_size for zinfo in z40.filelist])
            size80 = sum([zinfo.file_size for zinfo in z80.filelist])
            self.assertLess(size40, size80)


        # POST on "/media"
        self.assertRaises(Exception, lambda: PostArchive(
            _REMOTE, '/patients/%s/media' % info['ParentPatient'], { 'Transcode' : 'nope' }))

        z = PostArchive(_REMOTE, '/patients/%s/media' % info['ParentPatient'], {
            'Transcode' : '1.2.840.10008.1.2.4.50',
            })
        self.assertEqual('1.2.840.10008.1.2.4.50', GetTransferSyntax(z.read('IMAGES/IM0')))

        z = PostArchive(_REMOTE, '/studies/%s/media' % info['ParentStudy'], {
            'Transcode' : '1.2.840.10008.1.2.4.51',
            })
        self.assertEqual('1.2.840.10008.1.2.4.51', GetTransferSyntax(z.read('IMAGES/IM0')))

        z = PostArchive(_REMOTE, '/series/%s/media' % info['ParentSeries'], {
            'Transcode' : '1.2.840.10008.1.2.4.57',
            })
        self.assertEqual('1.2.840.10008.1.2.4.57', GetTransferSyntax(z.read('IMAGES/IM0')))

        if IsOrthancVersionAbove(_REMOTE, 1, 12, 7) and HasExtendedFind(_REMOTE):
            z40 = PostArchive(_REMOTE, '/series/%s/media' % info['ParentSeries'], {
                'Transcode' : '1.2.840.10008.1.2.4.50',
                'LossyQuality': 40
                })
            z80 = PostArchive(_REMOTE, '/series/%s/media' % info['ParentSeries'], {
                'Transcode' : '1.2.840.10008.1.2.4.50',
                'LossyQuality': 80
                })

            size40 = sum([zinfo.file_size for zinfo in z40.filelist])
            size80 = sum([zinfo.file_size for zinfo in z80.filelist])
            self.assertLess(size40, size80)

        
        # GET on "/archive"
        z, resp = GetArchive(_REMOTE, '/patients/%s/archive' % info['ParentPatient'])
        self.assertEqual(1, len(z.namelist()))
        self.assertEqual('1.2.840.10008.1.2.1', GetTransferSyntax(z.read(z.namelist()[0])))

        self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/patients/%s/archive?transcode=nope' % info['ParentPatient']))

        z, resp = GetArchive(_REMOTE, '/patients/%s/archive?transcode=1.2.840.10008.1.2' % info['ParentPatient'])
        self.assertEqual('1.2.840.10008.1.2', GetTransferSyntax(z.read(z.namelist()[0])))

        z, resp = GetArchive(_REMOTE, '/studies/%s/archive?transcode=1.2.840.10008.1.2.2' % info['ParentStudy'])
        self.assertEqual('1.2.840.10008.1.2.2', GetTransferSyntax(z.read(z.namelist()[0])))

        z, resp = GetArchive(_REMOTE, '/series/%s/archive?transcode=1.2.840.10008.1.2.4.70' % info['ParentSeries'])
        self.assertEqual('1.2.840.10008.1.2.4.70', GetTransferSyntax(z.read(z.namelist()[0])))

        if IsOrthancVersionAbove(_REMOTE, 1, 12, 7) and HasExtendedFind(_REMOTE):
            z40, resp40 = GetArchive(_REMOTE, '/patients/%s/archive?transcode=1.2.840.10008.1.2.4.50&lossy-quality=40' % info['ParentPatient'])
            z80, resp80 = GetArchive(_REMOTE, '/patients/%s/archive?transcode=1.2.840.10008.1.2.4.50&lossy-quality=80' % info['ParentPatient'])

            size40 = sum([zinfo.file_size for zinfo in z40.filelist])
            size80 = sum([zinfo.file_size for zinfo in z80.filelist])
            self.assertLess(size40, size80)


        # POST on "/archive"
        self.assertRaises(Exception, lambda: PostArchive(
            _REMOTE, '/patients/%s/archive' % info['ParentPatient'], { 'Transcode' : 'nope' }))

        z = PostArchive(_REMOTE, '/patients/%s/archive' % info['ParentPatient'], {
            'Transcode' : '1.2.840.10008.1.2.4.50',
            })
        self.assertEqual('1.2.840.10008.1.2.4.50', GetTransferSyntax(z.read(z.namelist()[0])))

        z = PostArchive(_REMOTE, '/studies/%s/archive' % info['ParentStudy'], {
            'Transcode' : '1.2.840.10008.1.2.4.51',
            })
        self.assertEqual('1.2.840.10008.1.2.4.51', GetTransferSyntax(z.read(z.namelist()[0])))

        z = PostArchive(_REMOTE, '/series/%s/archive' % info['ParentSeries'], {
            'Transcode' : '1.2.840.10008.1.2.4.57',
            })
        self.assertEqual('1.2.840.10008.1.2.4.57', GetTransferSyntax(z.read(z.namelist()[0])))
        
        if IsOrthancVersionAbove(_REMOTE, 1, 12, 7) and HasExtendedFind(_REMOTE):
            z40 = PostArchive(_REMOTE, '/series/%s/archive' % info['ParentSeries'], {
                'Transcode' : '1.2.840.10008.1.2.4.50',
                'LossyQuality': 40
                })
            z80 = PostArchive(_REMOTE, '/series/%s/archive' % info['ParentSeries'], {
                'Transcode' : '1.2.840.10008.1.2.4.50',
                'LossyQuality': 80
                })

            size40 = sum([zinfo.file_size for zinfo in z40.filelist])
            size80 = sum([zinfo.file_size for zinfo in z80.filelist])
            self.assertLess(size40, size80)


        # "/tools/create-*"
        z = PostArchive(_REMOTE, '/tools/create-archive', {
            'Resources' : [ info['ParentStudy'] ],
            'Transcode' : '1.2.840.10008.1.2.4.50',
            })
        self.assertEqual(1, len(z.namelist()))
        self.assertEqual('1.2.840.10008.1.2.4.50', GetTransferSyntax(z.read(z.namelist()[0])))

        z = PostArchive(_REMOTE, '/tools/create-media', {
            'Resources' : [ info['ParentStudy'] ],
            'Transcode' : '1.2.840.10008.1.2.4.51',
            })
        self.assertEqual(2, len(z.namelist()))
        self.assertEqual('1.2.840.10008.1.2.4.51', GetTransferSyntax(z.read('IMAGES/IM0')))

        z = PostArchive(_REMOTE, '/tools/create-media-extended', {
            'Resources' : [ info['ParentStudy'] ],
            'Transcode' : '1.2.840.10008.1.2.4.57',
            })
        self.assertEqual(2, len(z.namelist()))
        self.assertEqual('1.2.840.10008.1.2.4.57', GetTransferSyntax(z.read('IMAGES/IM0')))

        if IsOrthancVersionAbove(_REMOTE, 1, 12, 2):
            z, resp = GetArchive(_REMOTE, '/tools/create-archive?resources=%s&transcode=1.2.840.10008.1.2.4.50' % info['ParentStudy'])
            self.assertEqual(1, len(z.namelist()))
            self.assertEqual('1.2.840.10008.1.2.4.50', GetTransferSyntax(z.read(z.namelist()[0])))

            z, resp = GetArchive(_REMOTE, '/tools/create-media?resources=%s&transcode=1.2.840.10008.1.2.4.51' % info['ParentStudy'])
            self.assertEqual(2, len(z.namelist()))
            self.assertEqual('1.2.840.10008.1.2.4.51', GetTransferSyntax(z.read('IMAGES/IM0')))

            z, resp = GetArchive(_REMOTE, '/tools/create-media-extended?resources=%s&transcode=1.2.840.10008.1.2.4.57&filename=toto.zip' % info['ParentStudy'])
            self.assertEqual(2, len(z.namelist()))
            self.assertEqual('1.2.840.10008.1.2.4.57', GetTransferSyntax(z.read('IMAGES/IM0')))
            if IsOrthancVersionAbove(_REMOTE, 1, 12, 7):
                self.assertEqual('filename="toto.zip"', resp['content-disposition'])

        if IsOrthancVersionAbove(_REMOTE, 1, 12, 7) and HasExtendedFind(_REMOTE):
            z40 = PostArchive(_REMOTE, '/tools/create-archive', {
                'Resources' : [ info['ParentStudy'] ],
                'Transcode' : '1.2.840.10008.1.2.4.50',
                'LossyQuality': 40
                })
            z80 = PostArchive(_REMOTE, '/tools/create-archive', {
                'Resources' : [ info['ParentStudy'] ],
                'Transcode' : '1.2.840.10008.1.2.4.50',
                'LossyQuality': 80
                })
                
            size40 = sum([zinfo.file_size for zinfo in z40.filelist])
            size80 = sum([zinfo.file_size for zinfo in z80.filelist])
            self.assertLess(size40, size80)

            z40 = PostArchive(_REMOTE, '/tools/create-media', {
                'Resources' : [ info['ParentStudy'] ],
                'Transcode' : '1.2.840.10008.1.2.4.50',
                'LossyQuality': 40
                })
            z80 = PostArchive(_REMOTE, '/tools/create-media', {
                'Resources' : [ info['ParentStudy'] ],
                'Transcode' : '1.2.840.10008.1.2.4.50',
                'LossyQuality': 80
                })
                
            size40 = sum([zinfo.file_size for zinfo in z40.filelist])
            size80 = sum([zinfo.file_size for zinfo in z80.filelist])
            self.assertLess(size40, size80)

            z40 = PostArchive(_REMOTE, '/tools/create-media-extended', {
                'Resources' : [ info['ParentStudy'] ],
                'Transcode' : '1.2.840.10008.1.2.4.50',
                'LossyQuality': 40
                })
            z80 = PostArchive(_REMOTE, '/tools/create-media-extended', {
                'Resources' : [ info['ParentStudy'] ],
                'Transcode' : '1.2.840.10008.1.2.4.50',
                'LossyQuality': 80
                })
                
            size40 = sum([zinfo.file_size for zinfo in z40.filelist])
            size80 = sum([zinfo.file_size for zinfo in z80.filelist])
            self.assertLess(size40, size80)

            z40, resp = GetArchive(_REMOTE, '/tools/create-archive?resources=%s&transcode=1.2.840.10008.1.2.4.50&lossy-quality=40' % info['ParentStudy'])
            z80, resp = GetArchive(_REMOTE, '/tools/create-archive?resources=%s&transcode=1.2.840.10008.1.2.4.50&lossy-quality=80' % info['ParentStudy'])
            size40 = sum([zinfo.file_size for zinfo in z40.filelist])
            size80 = sum([zinfo.file_size for zinfo in z80.filelist])
            self.assertLess(size40, size80)


    def test_download_file_transcode(self):
        if IsOrthancVersionAbove(_REMOTE, 1, 12, 2):

            info = UploadInstance(_REMOTE, 'TransferSyntaxes/1.2.840.10008.1.2.1.dcm')
            # self.assertEqual('1.2.840.10008.1.2.1', GetTransferSyntax(
            #     DoGet(_REMOTE, '/instances/%s/file' % info['ID'])))

            # self.assertEqual('1.2.840.10008.1.2.4.50', GetTransferSyntax(
            #     DoGet(_REMOTE, '/instances/%s/file?transcode=1.2.840.10008.1.2.4.50' % info['ID'])))

            if IsOrthancVersionAbove(_REMOTE, 1, 12, 7):
                # resp, content = DoGetRaw(_REMOTE, '/instances/%s/file?filename=toto.dcm' % info['ID'])
                # self.assertEqual('filename="toto.dcm"', resp['content-disposition'])

                # resp, content = DoGetRaw(_REMOTE, '/instances/%s/file?transcode=1.2.840.10008.1.2.4.50&filename=toto.dcm' % info['ID'])
                # self.assertEqual('filename="toto.dcm"', resp['content-disposition'])

                # resp, content = DoGetRaw(_REMOTE, '/instances/%s/file?filename="toto".dcm' % info['ID'])
                # self.assertEqual('filename="\"toto\".dcm"', resp['content-disposition'])

                resp, content40 = DoGetRaw(_REMOTE, '/instances/%s/file?transcode=1.2.840.10008.1.2.4.50&lossy-quality=40' % info['ID'])
                resp, content80 = DoGetRaw(_REMOTE, '/instances/%s/file?transcode=1.2.840.10008.1.2.4.50&lossy-quality=80' % info['ID'])
                self.assertLess(len(content40), len(content80))


    def test_modify_keep_source(self):
        # https://groups.google.com/d/msg/orthanc-users/CgU-Wg8vDio/BY5ZWcDEAgAJ
        i = UploadInstance(_REMOTE, 'DummyCT.dcm')
        self.assertEqual(1, len(DoGet(_REMOTE, '/studies')))

        j = DoPost(_REMOTE, '/studies/%s/modify' % i['ParentStudy'], {
            'Replace' : {
                'StationName' : 'TEST',
                },
            'KeepSource' : True,
        })

        s = DoGet(_REMOTE, '/studies')
        self.assertEqual(2, len(s))
        self.assertTrue(i['ParentStudy'] in s)
        self.assertTrue(j['ID'] in s)

        DoDelete(_REMOTE, '/studies/%s' % j['ID'])
        self.assertEqual(1, len(DoGet(_REMOTE, '/studies')))

        j = DoPost(_REMOTE, '/studies/%s/modify' % i['ParentStudy'], {
            'Replace' : {
                'StationName' : 'TEST',
                },
            'KeepSource' : False,
        })

        s = DoGet(_REMOTE, '/studies')
        self.assertEqual(1, len(s))
        self.assertFalse(i['ParentStudy'] in s)
        self.assertTrue(j['ID'] in s)


    def test_modify_transcode_study(self):
        i = UploadInstance(_REMOTE, 'KarstenHilbertRF.dcm')
        self.assertEqual('1.2.840.10008.1.2.1', GetTransferSyntax(
            DoGet(_REMOTE, '/instances/%s/file' % i['ID'])))

        self.assertEqual(1, len(DoGet(_REMOTE, '/instances')))
        j = DoPost(_REMOTE, '/studies/%s/modify' % i['ParentStudy'], {
            'Transcode' : '1.2.840.10008.1.2.4.50',
            'KeepSource' : False
            })

        k = DoGet(_REMOTE, '/instances')
        self.assertEqual(1, len(k))
        self.assertEqual(i['ID'], DoGet(_REMOTE, '/instances/%s/metadata?expand' % k[0]) ['ModifiedFrom'])       
        self.assertEqual('1.2.840.10008.1.2.4.50', GetTransferSyntax(
            DoGet(_REMOTE, '/instances/%s/file' % k[0])))
        

    def test_modify_need_force_to_change_uids(self):
        def Modify(level, resourceId, replaceTags, force, keepSource):
            return DoPost(_REMOTE, '/%s/%s/modify' % (level, resourceId), {
                'Replace' : replaceTags,
                'Force': force,
                'KeepSource' : keepSource
                })
        
        self.assertEqual(0, len(DoGet(_REMOTE, '/studies')))

        i = UploadInstance(_REMOTE, 'DummyCT.dcm')
        self.assertEqual(1, len(DoGet(_REMOTE, '/studies')))

        # can not change the StudyInstanceUID unless you force it
        self.assertRaises(Exception, lambda: Modify('studies', i['ParentStudy'], {'StudyInstanceUID': '1.2'}, force=False, keepSource=True))
        Modify('studies', i['ParentStudy'], {'StudyInstanceUID': '1.2'}, force=True, keepSource=True)

        # can not change the SeriesInstanceUID unless you force it
        self.assertRaises(Exception, lambda: Modify('series', i['ParentSeries'], {'SeriesInstanceUID': '1.2'}, force=False, keepSource=True))
        Modify('series', i['ParentSeries'], {'SeriesInstanceUID': '1.2'}, force=True, keepSource=True)

        # can not change the SOPInstanceUID unless you force it
        self.assertRaises(Exception, lambda: Modify('instances', i['ID'], {'SOPInstanceUID': '1.2'}, force=False, keepSource=True))
        Modify('instances', i['ID'], {'SOPInstanceUID': '1.2'}, force=True, keepSource=True)


        # can not change the PatientID of a study unless you force it
        self.assertRaises(Exception, lambda: Modify('studies', i['ParentStudy'], {'PatientID': 'NEW'}, force=False, keepSource=True))
        self.assertRaises(Exception, lambda: Modify('series', i['ParentSeries'], {'StudyInstanceUID': '1.3'}, force=False, keepSource=True))
        self.assertRaises(Exception, lambda: Modify('instances', i['ID'], {'SeriesInstanceUID': '1.2'}, force=False, keepSource=True))

        if IsOrthancVersionAbove(_REMOTE, 1, 11, 3):
            # this was forbidden even with Force=true till 1.11.2 included
            Modify('studies', i['ParentStudy'], {'PatientID': 'NEW'}, force=True, keepSource=True)
            Modify('series', i['ParentSeries'], {'StudyInstanceUID': '1.3'}, force=True, keepSource=True)
            Modify('instances', i['ID'], {'SeriesInstanceUID': '1.2'}, force=True, keepSource=True)


    def test_modify_study_module_reconstruction(self):
        if IsOrthancVersionAbove(_REMOTE, 1, 11, 3):
            def UploadAndModify(level, resourceId, replaceTags, force, keepSource, dropOrthanc=True):

                if dropOrthanc:
                    DropOrthanc(_REMOTE)
    
                UploadFolder(_REMOTE, 'Knee/T1')
                UploadFolder(_REMOTE, 'Knee/T2')
    
                if dropOrthanc:
                    self.assertEqual(1, len(DoGet(_REMOTE, '/studies')))

                modifyResponse = DoPost(_REMOTE, '/%s/%s/modify' % (level, resourceId), {
                    'Replace' : replaceTags,
                    'Force': force,
                    'KeepSource' : keepSource
                    })
                modifiedResource = DoGet(_REMOTE, '/%s/%s' % (level, modifyResponse['ID']))
                return (modifyResponse, modifiedResource)

            kneeSeriesT1 = '6de73705-c4e65c1b-9d9ea1b5-cabcd8e7-f15e4285'
            kneeSeriesT2 = 'bbf7a453-0d34251a-03663b55-46bb31b9-ffd74c59'
            kneeStudy = '0a9b3153-2512774b-2d9580de-1fc3dcf6-3bd83918'
            kneePatient = 'ca29faea-b6a0e17f-067743a1-8b778011-a48b2a17'
            kneeStudyInstanceUID = '2.16.840.1.113669.632.20.121711.10000160881'
            kneeSeriesInstanceUIDT1 = '1.3.46.670589.11.17521.5.0.3124.2008081908564160709'
            kneeSeriesInstanceUIDT2 = '1.3.46.670589.11.17521.5.0.3124.2008081909090037350'

            ####### study level tests #######

            # modify study description and make sure the MainDicomTags are updated
            modifyResponse, modifiedResource = UploadAndModify('studies', kneeStudy, replaceTags={
                'StudyInstanceUID': kneeStudyInstanceUID, 
                'StudyDescription': 'TOTO'
                }, force=True, keepSource=True)
            self.assertEqual(kneeStudy, modifyResponse['ID'])
            self.assertEqual('TOTO', modifiedResource['MainDicomTags']['StudyDescription'])

            # modify patient name at study level and make sure the PatientMainDicomTags are updated + the patient has been updated
            modifyResponse, modifiedResource = UploadAndModify('studies', kneeStudy, replaceTags={
                'StudyInstanceUID': kneeStudyInstanceUID, 
                'PatientName': 'TOTO'
                }, force=True, keepSource=True)
            self.assertEqual(kneeStudy, modifyResponse['ID'])
            self.assertEqual('TOTO', modifiedResource['PatientMainDicomTags']['PatientName'])
            patient = DoGet(_REMOTE, '/patients/%s' % kneePatient)
            self.assertEqual('TOTO', patient['MainDicomTags']['PatientName'])

            # modify patient name and patient id at study level and make sure the PatientMainDicomTags are updated + a new patient has been created + the old one does not exist anymore
            modifyResponse, modifiedResource = UploadAndModify('studies', kneeStudy, replaceTags={
                'StudyInstanceUID': kneeStudyInstanceUID, 
                'PatientID': 'TOTO_ID',
                'PatientName': 'TOTO'
                }, force=True, keepSource=True)
            self.assertNotEqual(kneeStudy, modifyResponse['ID'])  # the study has changed since the PatientID has changed
            self.assertEqual('TOTO', modifiedResource['PatientMainDicomTags']['PatientName'])
            self.assertEqual('TOTO_ID', modifiedResource['PatientMainDicomTags']['PatientID'])
            patient = DoGet(_REMOTE, '/patients/%s' % modifyResponse['PatientID'])
            self.assertEqual('TOTO', patient['MainDicomTags']['PatientName'])
            self.assertEqual('TOTO_ID', patient['MainDicomTags']['PatientID'])

            ####### series level tests #######
            # modify series description and make sure the MainDicomTags are updated
            modifyResponse, modifiedResource = UploadAndModify('series', kneeStudy, replaceTags={
                'SeriesInstanceUID': kneeSeriesInstanceUIDT1,
                'StudyInstanceUID': kneeStudyInstanceUID,
                'SeriesDescription': 'TOTO'
                }, force=True, keepSource=True)
            self.assertEqual(kneeSeriesT1, modifyResponse['ID'])
            self.assertEqual('TOTO', modifiedResource['MainDicomTags']['SeriesDescription'])
            self.assertEqual(kneeStudy, modifyResponse['ParentResources'][0])


    def test_rename_patient_with_multiple_studies(self):
        if IsOrthancVersionAbove(_REMOTE, 1, 11, 3):

            patientOrthancId = '5436938e-7ae68340-5ea6ad3c-4e6e09bd-1bd335de'
            patientDicomId = 'TEST_1'
            patientName = 'Test'
            study1234 = '72de3b86-da4b2556-bb33f32f-d1d84f80-fb017059'
            study2345 = '3594f32b-dcf60e81-58252b67-66222714-c09fca81'

            DropOrthanc(_REMOTE)
            UploadFolder(_REMOTE, 'PatientWith2studies')

            # each sub-test is in a dedicated 'if' for clarity

            if True:
                # it shall be impossible to rename a patient when modifying a study if that patient already has other studies
                self.assertRaises(Exception, lambda: DoPost(_REMOTE, '/%s/%s/modify' % ('studies', study1234), {
                    'Replace' : {'PatientName': "TOTO"},
                    'Force': True,
                    'KeepSource' : True
                    }))

            if True:
                # rename the patient (at patient level)
                modifyResponse = DoPost(_REMOTE, '/%s/%s/modify' % ('patients', patientOrthancId), {
                    'Replace' : {
                        'PatientName': 'TOTO'
                    },
                    'Force': True,
                    'KeepSource' : False
                    })
                modifiedPatient = DoGet(_REMOTE, '/%s/%s' % ('patients', modifyResponse['ID']))
                # make sure the patient name has been edited at patient level
                self.assertEqual('TOTO', modifiedPatient['MainDicomTags']['PatientName'])

                # there should only be 2 studies since we have set KeepSource=False
                self.assertEqual(2, len(modifiedPatient['Studies']))
                modifiedStudy1 = DoGet(_REMOTE, '/%s/%s' % ('studies', modifiedPatient['Studies'][0]))
                modifiedStudy2 = DoGet(_REMOTE, '/%s/%s' % ('studies', modifiedPatient['Studies'][1]))
                self.assertEqual('TOTO', modifiedStudy1['PatientMainDicomTags']['PatientName'])
                self.assertEqual('TOTO', modifiedStudy2['PatientMainDicomTags']['PatientName'])

            if True:
                # rename the patient (at patient level) and don't keep sources and preserve StudyInstanceUID
                DropOrthanc(_REMOTE)
                UploadFolder(_REMOTE, 'PatientWith2studies')

                # rename the patient (at patient level) and don't keep sources and preserve StudyInstanceUID, SeriesInstanceUID
                modifyResponse = DoPost(_REMOTE, '/%s/%s/modify' % ('patients', patientOrthancId), {
                    'Replace' : {
                        'PatientName': 'TOTO'
                    },
                    'Keep': ['StudyInstanceUID', 'SeriesInstanceUID'],
                    'Force': True,
                    'KeepSource' : False
                    })
                modifiedPatient = DoGet(_REMOTE, '/%s/%s' % ('patients', modifyResponse['ID']))
                # make sure tha patient name has been edited at patient level
                self.assertEqual('TOTO', modifiedPatient['MainDicomTags']['PatientName'])

                # there should only be 2 studies since we have set KeepSource=False
                self.assertEqual(2, len(modifiedPatient['Studies']))
                modifiedStudy1 = DoGet(_REMOTE, '/%s/%s' % ('studies', modifiedPatient['Studies'][0]))
                modifiedStudy2 = DoGet(_REMOTE, '/%s/%s' % ('studies', modifiedPatient['Studies'][1]))
                # the StudyInstanceUID shall not have changed
                self.assertIn(modifiedStudy1['MainDicomTags']['StudyInstanceUID'], ['1.2.3', '2.3.4'])
                self.assertIn(modifiedStudy2['MainDicomTags']['StudyInstanceUID'], ['1.2.3', '2.3.4'])
                # the DB model of parent shall have been reconstructed
                self.assertEqual('TOTO', modifiedStudy1['PatientMainDicomTags']['PatientName'])
                self.assertEqual('TOTO', modifiedStudy2['PatientMainDicomTags']['PatientName'])

            if True:
                # it shall not be possible to keep all dicom UID and have KeepSource at False since the modified instances 
                # would have the same orthanc ids as the source ids -> they would be deleted
                self.assertRaises(Exception, lambda: DoPost(_REMOTE, '/%s/%s/modify' % ('patients', study1234), {
                    'Replace' : {'PatientName': "TOTO"},
                    'Force': True,
                    'Keep': ['StudyInstanceUID', 'SeriesInstanceUID', 'SOPInstanceUID'],
                    'KeepSource' : False
                    }))

            if True:
                # rename the patient (at patient level) and don't keep sources and preserve all DicomID
                DropOrthanc(_REMOTE)
                UploadFolder(_REMOTE, 'PatientWith2studies')

                # rename the patient (at patient level) and don't keep sources and preserve StudyInstanceUID
                modifyResponse = DoPost(_REMOTE, '/%s/%s/modify' % ('patients', patientOrthancId), {
                    'Replace' : {
                        'PatientName': 'TOTO'
                    },
                    'Keep': ['StudyInstanceUID', 'SeriesInstanceUID', 'SOPInstanceUID'],
                    'Force': True,
                    'KeepSource' : True
                    })
                modifiedPatient = DoGet(_REMOTE, '/%s/%s' % ('patients', modifyResponse['ID']))
                # make sure tha patient name has been edited at patient level
                self.assertEqual('TOTO', modifiedPatient['MainDicomTags']['PatientName'])

                # there should only be 2 studies since we have set KeepSource=False
                self.assertEqual(2, len(modifiedPatient['Studies']))
                modifiedStudy1 = DoGet(_REMOTE, '/%s/%s' % ('studies', modifiedPatient['Studies'][0]))
                modifiedStudy2 = DoGet(_REMOTE, '/%s/%s' % ('studies', modifiedPatient['Studies'][1]))
                # the StudyInstanceUID shall not have changed
                self.assertIn(modifiedStudy1['MainDicomTags']['StudyInstanceUID'], ['1.2.3', '2.3.4'])
                self.assertIn(modifiedStudy2['MainDicomTags']['StudyInstanceUID'], ['1.2.3', '2.3.4'])
                # the DB model of parent shall have been reconstructed
                self.assertEqual('TOTO', modifiedStudy1['PatientMainDicomTags']['PatientName'])
                self.assertEqual('TOTO', modifiedStudy2['PatientMainDicomTags']['PatientName'])


            if True:
                # try to attach the knee study to an existing patient
                DropOrthanc(_REMOTE)
                UploadFolder(_REMOTE, 'PatientWith2studies')
                UploadFolder(_REMOTE, 'Knee/T1')

                kneeStudy = '0a9b3153-2512774b-2d9580de-1fc3dcf6-3bd83918'

                # try to change the PatientID at study level.  This only works if we specify all Patient Tags and if they are identical to the existing Patient in DB
                
                # this should fail if only specifying the PatientID
                self.assertRaises(Exception, lambda: DoPost(_REMOTE, '/%s/%s/modify' % ('studies', kneeStudy), {
                    'Replace' : {
                        'PatientID': 'TEST_1'
                    },
                    'Force': True,
                    'KeepSource' : False
                    }))

                # this should fail if specifying all tags but one of them is not correct
                self.assertRaises(Exception, lambda: DoPost(_REMOTE, '/%s/%s/modify' % ('studies', kneeStudy), {
                    'Replace' : {
                        'PatientID': 'TEST_1',
                        'PatientName': 'Test',
                        'PatientBirthDate': '19000101',
                        'PatientSex': 'F'  # this is wrong !
                    },
                    'Force': True,
                    'KeepSource' : False
                    }))

                # this should fail if specifying a tag that is not defined in DB for that patient
                self.assertRaises(Exception, lambda: DoPost(_REMOTE, '/%s/%s/modify' % ('studies', kneeStudy), {
                    'Replace' : {
                        'PatientID': 'TEST_1',
                        'PatientName': 'Test',
                        'PatientBirthDate': '19000101',
                        'PatientSex': 'M',
                        '0010,1000': 'TUTU'  # this does not exist in DB
                    },
                    'Force': True,
                    'KeepSource' : False
                    }))

                # this should now work with all correct tags
                modifyResponse = DoPost(_REMOTE, '/%s/%s/modify' % ('studies', kneeStudy), {
                    'Replace' : {
                        'PatientID': 'TEST_1',
                        'PatientName': 'Test',
                        'PatientBirthDate': '19000101',
                        'PatientSex': 'M'
                    },
                    'Force': True,
                    'KeepSource' : False
                    })
                modifiedStudy = DoGet(_REMOTE, '/%s/%s' % ('studies', modifyResponse['ID']))
                self.assertEqual('Test', modifiedStudy['PatientMainDicomTags']['PatientName'])
                patient = DoGet(_REMOTE, '/%s/%s' % ('patients', patientOrthancId))
                # make sure tha patient name remains the same at patient level
                self.assertEqual('Test', patient['MainDicomTags']['PatientName'])


            if True:
                # try to edit patient in Knee (only study from this patient)
                DropOrthanc(_REMOTE)
                UploadFolder(_REMOTE, 'PatientWith2studies')
                UploadFolder(_REMOTE, 'Knee/T1')

                kneeStudy = '0a9b3153-2512774b-2d9580de-1fc3dcf6-3bd83918'
                originalKneePatientId = 'ca29faea-b6a0e17f-067743a1-8b778011-a48b2a17'

                originalKneePatient = DoGet(_REMOTE, '/%s/%s' % ('patients', originalKneePatientId))

                # try to change the PatientName and StudyDescription at study level.
                modifyResponse = DoPost(_REMOTE, '/%s/%s/modify' % ('studies', kneeStudy), {
                    'Replace' : {
                        'PatientName': 'Test Knee',
                        'StudyDescription': 'Knee study'
                    },
                    'Keep': ['StudyInstanceUID'],
                    'Force': True,
                    'KeepSource' : False
                    })
                modifiedStudy = DoGet(_REMOTE, '/%s/%s' % ('studies', modifyResponse['ID']))
                self.assertEqual('Test Knee', modifiedStudy['PatientMainDicomTags']['PatientName'])
                # reload the patient, it shall have been updated as well (and kept the same ID since we did not change the PatientID)
                modifiedPatient = DoGet(_REMOTE, '/%s/%s' % ('patients', originalKneePatientId))
                self.assertEqual('Test Knee', modifiedPatient['MainDicomTags']['PatientName'])

                # try to change the PatientID and PatientName and StudyDescription at study level.  Since we use a new PatientID, we can modify its name too
                modifyResponse = DoPost(_REMOTE, '/%s/%s/modify' % ('studies', kneeStudy), {
                    'Replace' : {
                        'PatientName': 'Test Knee 2',
                        'PatientID': 'TEST_KNEE_2',
                        'StudyDescription': 'Knee study 2'
                    },
                    'Force': True,
                    'KeepSource' : False
                    })
                modifiedStudy = DoGet(_REMOTE, '/%s/%s' % ('studies', modifyResponse['ID']))
                self.assertEqual('Test Knee 2', modifiedStudy['PatientMainDicomTags']['PatientName'])
                self.assertEqual('Knee study 2', modifiedStudy['MainDicomTags']['StudyDescription'])
                # reload the patient, now, its orthanc id has changed
                modifiedPatient = DoGet(_REMOTE, '/%s/%s' % ('patients', modifiedStudy['ParentPatient']))
                self.assertEqual('Test Knee 2', modifiedPatient['MainDicomTags']['PatientName'])
                # the previous patient shall not exist anymore
                self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/%s/%s' % ('patients', originalKneePatientId)))

    def test_store_peer_transcoding(self):
        i = UploadInstance(_REMOTE, 'KarstenHilbertRF.dcm')['ID']

        SYNTAXES = [
            '1.2.840.10008.1.2',        
            '1.2.840.10008.1.2.1',
            '1.2.840.10008.1.2.2',
            '1.2.840.10008.1.2.4.50',
            '1.2.840.10008.1.2.4.51',
            '1.2.840.10008.1.2.4.57',
            '1.2.840.10008.1.2.4.70',
        ]

        if IsOrthancVersionAbove(_REMOTE, 1, 12, 7):
            SYNTAXES.append('1.2.840.10008.1.2.1.99')  # Deflated Explicit VR Little Endian (cannot be decoded in debug mode if Orthanc is statically linked against DCMTK 3.6.5)



        if HasGdcmPlugin(_REMOTE):
            SYNTAXES = SYNTAXES + [
                '1.2.840.10008.1.2.4.80',  # This makes DCMTK 3.6.2 crash
                '1.2.840.10008.1.2.4.81',  # This makes DCMTK 3.6.2 crash
                '1.2.840.10008.1.2.4.90',  # JPEG2k, unavailable without GDCM
                '1.2.840.10008.1.2.4.91',  # JPEG2k, unavailable without GDCM
            ]

        for syntax in SYNTAXES:
            body = {
                'Resources' : [ i ],
            }

            if syntax != '1.2.840.10008.1.2.1':
                body['Transcode'] = syntax
            
            self.assertEqual(0, len(DoGet(_LOCAL, '/instances')))
            self.assertEqual(1, len(DoGet(_REMOTE, '/instances')))
            DoPost(_REMOTE, '/peers/peer/store', body, 'text/plain')
            self.assertEqual(1, len(DoGet(_LOCAL, '/instances')))
            self.assertEqual(1, len(DoGet(_REMOTE, '/instances')))
            self.assertEqual(syntax, GetTransferSyntax(
                DoGet(_LOCAL, '/instances/%s/file' % DoGet(_LOCAL, '/instances') [0])))

            DropOrthanc(_LOCAL)

        
    def test_getscu(self):
        def CleanTarget():
            if os.path.isdir('/tmp/GETSCU'):
                shutil.rmtree('/tmp/GETSCU')
            os.makedirs('/tmp/GETSCU')
        
        env = {}
        if _DOCKER:
            # This is "getscu" from DCMTK 3.6.5 compiled using LSB,
            # and running in a GNU/Linux distribution running DCMTK
            # 3.6.0. Tell "getscu" where it can find the DICOM dictionary.
            env['DCMDICTPATH'] = os.environ.get('DCMDICTPATH', '/usr/share/libdcmtk2/dicom.dic')

        # no transcoding required
        UploadInstance(_REMOTE, 'Brainix/Flair/IM-0001-0001.dcm')['ID']

        CleanTarget()

        subprocess.check_call([
            FindExecutable('getscu'),
            _REMOTE['Server'], 
            str(_REMOTE['DicomPort']),
            '-aec', 'ORTHANC',
            '-aet', 'ORTHANCTEST', # pretend to be the other orthanc
            '-k', '0020,000d=2.16.840.1.113669.632.20.1211.10000357775',
            '-k', '0008,0052=STUDY',
            '--output-directory', '/tmp/GETSCU/' 
        ], env = env)

        f1 = '/tmp/GETSCU/MR.1.3.46.670589.11.0.0.11.4.2.0.8743.5.5396.2006120114314079549'
        self.assertTrue(os.path.isfile(f1))
        with open(f1, 'rb') as f:
            self.assertEqual('1.2.840.10008.1.2.1', GetTransferSyntax(f.read(), encoding='ISO-8859-1'))

        CleanTarget()

        # transcoding required
        UploadInstance(_REMOTE, 'TransferSyntaxes/1.2.840.10008.1.2.4.50.dcm')

        subprocess.check_call([
            FindExecutable('getscu'),
            _REMOTE['Server'], 
            str(_REMOTE['DicomPort']),
            '-aec', 'ORTHANC',
            '-aet', 'ORTHANCTEST', # pretend to be the other orthanc
            '-k', '0020,000d=2.16.840.1.113669.632.20.1211.10000357775\\1.2.840.113663.1298.6234813.1.298.20000329.1115122',
            '-k', '0008,0052=STUDY',
            '--output-directory', '/tmp/GETSCU/' 
        ], env = env)

        self.assertTrue(os.path.isfile(f1))
        with open(f1, 'rb') as f:
            self.assertEqual('1.2.840.10008.1.2.1', GetTransferSyntax(f.read(), encoding='ISO-8859-1'))

        # This file is transcoded from "1.2.840.10008.1.2.4.50" to "1.2.840.10008.1.2.1"
        # (LittleEndianExplicit is proposed by default by "getscu")
        f2 = '/tmp/GETSCU/US.1.2.840.113663.1298.1.3.715.20000329.1115326'
        self.assertTrue(os.path.isfile(f2))
        with open(f2, 'rb') as f:
            self.assertEqual('1.2.840.10008.1.2.1', GetTransferSyntax(f.read()))


    def test_findscu_truncation(self):
        # https://groups.google.com/forum/#!msg/orthanc-users/FkckWAHvso8/UbRBAhQ5CwAJ
        # Fixed by: https://orthanc.uclouvain.be/hg/orthanc/rev/2724977419fb
        UploadInstance(_REMOTE, 'Multiframe.dcm')
        UploadInstance(_REMOTE, 'ColorTestImageJ.dcm')

        study = '1.3.46.670589.7.5.8.80001255161.20000323.151537.1'
        
        i = CallFindScu([ '-k', '0008,0052=STUDY', '-k', 'StudyInstanceUID' ])
        result = re.findall('\(0020,000d\).*?\[(.*?)\]', i)
        self.assertEqual(2, len(result))

        # The "StudyInstanceUID" is set as a list of 5 times the same
        # study, leading to a string of 249 characters
        i = CallFindScu([ '-k', '0008,0052=STUDY', '-k',
                          'StudyInstanceUID=%s\\%s\\%s\\%s\\%s' % (( study, ) * 5) ])
        result = re.findall('\(0020,000d\).*?\[(.*?)\]', i)
        self.assertEqual(1, len(result))
        
        # The "StudyInstanceUID" is set as a list of 6 times the same
        # study, leading to a string of 299 characters. In Orthanc <=
        # 1.7.2, this is above the value of ORTHANC_MAXIMUM_TAG_LENGTH
        # == 256, and is thus wiped out by C-FIND SCP. As a
        # consequence, Orthanc <= 1.7.2 doesn't apply the filter on
        # "StudyInstanceUID" and returns all the available
        # studies (i.e. 2). This issue was fixed in Orthanc 1.7.3.
        i = CallFindScu([ '-k', '0008,0052=STUDY', '-k',
                          'StudyInstanceUID=%s\\%s\\%s\\%s\\%s\\%s' % (( study, ) * 6) ])
        result = re.findall('\(0020,000d\).*?\[(.*?)\]', i)
        self.assertEqual(1, len(result))


    def test_store_compressed(self):
        with open(GetDatabasePath('DummyCT.dcm'), 'rb') as f:
            dicom = f.read()
            i = DoPost(_REMOTE, '/instances', dicom) ['ID']
            sourceSize = len(dicom)
        
        self.assertEqual(0, len(DoGet(_LOCAL, '/instances')))
        self.assertEqual(1, len(DoGet(_REMOTE, '/instances')))

        # Sending to the local Orthanc 0.8.6 server, without compression: OK
        jobId = MonitorJob2(_REMOTE, lambda: DoPost(
            _REMOTE, '/peers/peer/store', {
                'Resources' : [ i ],
                'Synchronous' : False,
            }))

        job = DoGet(_REMOTE, '/jobs/%s' % jobId)
        self.assertFalse(job['Content']['Compress'])
        self.assertEqual('', job['Content']['Peer'][2])  # Password must not be reported
        self.assertEqual(str(sourceSize), job['Content']['Size'])

        self.assertEqual(1, len(DoGet(_LOCAL, '/instances')))
        DropOrthanc(_LOCAL)

        if not IsOrthancVersionAbove(_LOCAL, 1, 11, 2):  # don't know which specific version the behaviour changed but this fails with 0.8.6
            # Sending to the local Orthanc 0.8.6 server, with compression:
            # Not supported by Orthanc 0.8.6 => failure
            self.assertRaises(Exception, lambda: DoPost(_REMOTE, '/peers/peer/store', {
                'Resources' : [ i ],
                'Compress' : True,
            }))
            self.assertEqual(0, len(DoGet(_LOCAL, '/instances')))

            # Sending to the tested remote server, with compression: OK
            jobId = MonitorJob2(_REMOTE, lambda: DoPost(
                _REMOTE, '/peers/self/store', {
                    'Resources' : [ i ],
                    'Compress' : True,
                    'Synchronous' : False,
                }))

            job = DoGet(_REMOTE, '/jobs/%s' % jobId)
            self.assertTrue(job['Content']['Compress'])

            # Compression must have divided the size of the sent data at least twice
            self.assertLess(int(job['Content']['Size']), sourceSize / 2)


    def test_move_ambra(self):
        # "Orthanc + Ambra: Query/Retrieve" (2020-08-25)
        # https://groups.google.com/g/orthanc-users/c/yIUnZ9v9-Zs/m/GQPXiAOiCQAJ

        UploadInstance(_REMOTE, '2019-06-17-VedranZdesic.dcm')
        
        self.assertFalse(MonitorJob(_REMOTE, lambda: CallMoveScu([
            '--study',
            '-k', 'StudyInstanceUID='
        ])))
        
        self.assertFalse(MonitorJob(_REMOTE, lambda: CallMoveScu([
            '--study',
            '-k', 'AccessionNumber=',
        ])))
        
        self.assertFalse(MonitorJob(_REMOTE, lambda: CallMoveScu([
            '--study',
            '-k', 'AccessionNumber=',
            '-k', 'StudyInstanceUID='
        ])))
        
        self.assertEqual(0, len(DoGet(_LOCAL, '/instances')))
        self.assertTrue(MonitorJob(_REMOTE, lambda: CallMoveScu([
            '--study',
            '-k', 'AccessionNumber=CT16000988',
            '-k', 'StudyInstanceUID=',
        ])))
        self.assertEqual(1, len(DoGet(_LOCAL, '/instances')))
        DropOrthanc(_LOCAL)
        
        self.assertEqual(0, len(DoGet(_LOCAL, '/instances')))
        self.assertTrue(MonitorJob(_REMOTE, lambda: CallMoveScu([
            '--study',
            '-k', 'AccessionNumber=CT16000988',
            '-k', 'StudyInstanceUID=1.2.840.113619.2.278.3.4194965761.659.1468842739.39',
        ])))
        self.assertEqual(1, len(DoGet(_LOCAL, '/instances')))
        DropOrthanc(_LOCAL)

        # This fails on Orthanc <= 1.7.3
        self.assertEqual(0, len(DoGet(_LOCAL, '/instances')))
        self.assertTrue(MonitorJob(_REMOTE, lambda: CallMoveScu([
            '--study',
            '-k', 'AccessionNumber=',
            '-k', 'StudyInstanceUID=1.2.840.113619.2.278.3.4194965761.659.1468842739.39'
        ])))
        self.assertEqual(1, len(DoGet(_LOCAL, '/instances')))
        DropOrthanc(_LOCAL)


    def test_decode_elscint(self):
        # https://groups.google.com/g/orthanc-users/c/d9anAx6lSis/m/qEzm1x3PAAAJ
        a = UploadInstance(_REMOTE, '2020-09-12-ELSCINT1-PMSCT_RLE1.dcm')['ID']
        b = UploadInstance(_REMOTE, '2020-09-11-Christopher-ELSCINT1-Raw.dcm')['ID']
        
        im = GetImage(_REMOTE, '/instances/%s/frames/0/preview' % a)
        self.assertEqual("L", im.mode)
        self.assertEqual(512, im.size[0])
        self.assertEqual(512, im.size[1])

        im = GetImage(_REMOTE, '/instances/%s/frames/0/preview' % b)
        self.assertEqual("L", im.mode)
        self.assertEqual(512, im.size[0])
        self.assertEqual(512, im.size[1])

        # The two tests below fail on Orthanc <= 1.7.3
        raw = DoGet(_REMOTE, '/instances/%s/frames/0/raw' % a)
        self.assertEqual(512 * 512 * 2, len(raw))

        raw = DoGet(_REMOTE, '/instances/%s/frames/0/raw' % b)
        self.assertEqual(512 * 512 * 2, len(raw))
        

    def test_rest_modalities_in_study_2(self):
        # Problem reported by Alain Mazy on 2020-09-15
        UploadInstance(_REMOTE, 'Comunix/Ct/IM-0001-0001.dcm')
        UploadInstance(_REMOTE, 'Comunix/Pet/IM-0001-0001.dcm')

        i = CallFindScu([ '-k', '0008,0052=STUDY', '-k', '0020,000d=', '-k', '0008,0061=' ])
        modalitiesInStudy = re.findall('\(0008,0061\).*?\[(.*?)\]', i)
        self.assertEqual(1, len(modalitiesInStudy))
        self.assertEqual('CT\\PT ', modalitiesInStudy[0])
        
        for i in [ '', 'CT', 'PT', 'UX', 'UX\\MR', 'CT\\PT', 'UX\\PT', 'CT\\PT', 'UX\\CT\\PT' ]:
            # The empty string '' corresponds to universal matching.
            # The case where "i == 'CT'" failed in Orthanc <= 1.7.3.
            
            if i in [ 'UX', 'UX\\MR' ]:
                expected = 0
            else:
                expected = 1

            a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Study',
                                                 'Query' : { 'ModalitiesInStudy' : i }})
            self.assertEqual(expected, len(a))

            i = CallFindScu([ '-k', '0008,0052=STUDY', '-k', '0020,000d=', '-k', '0008,0061=%s' % i ])
            studyInstanceUid = re.findall('\(0020,000d\).*?\[(.*?)\]', i)
            self.assertEqual(expected, len(studyInstanceUid))
        

    def test_webdav(self):
        self.assertRaises(Exception, lambda: DoPropFind(_REMOTE, '/webdav/', 2))

        for suffix in [ '', '/' ]:
            f = DoPropFind(_REMOTE, '/webdav' + suffix, 0)
            self.assertEqual(1, len(f))
            self.assertTrue('/webdav/' in f.keys())
            self.assertTrue(f['/webdav/']['folder'])
            self.assertEqual('webdav', f['/webdav/']['displayname'])

            f = DoPropFind(_REMOTE, '/webdav' + suffix, 1)
            self.assertEqual(6, len(f))
            self.assertTrue(f['/webdav/']['folder'])
            self.assertEqual('webdav', f['/webdav/']['displayname'])
            
            for i in [ 'by-dates', 'by-patients', 'by-studies', 'by-uids', 'uploads' ]:
                self.assertTrue(f['/webdav/%s' % i]['folder'])
                self.assertEqual(i, f['/webdav/%s' % i]['displayname'])

                for depth in [ 0, 1 ]:
                    for suffix2 in [ '', '/' ]:
                        g = DoPropFind(_REMOTE, '/webdav/%s%s' % (i, suffix2), depth)

                        if i == 'uploads':
                            # Empty folders might still exist in "/uploads/"
                            self.assertTrue('/webdav/uploads/' in g)
                            self.assertEqual('uploads', g['/webdav/uploads/']['displayname'])
                            for j in g.items():
                                self.assertTrue(g.items()[0][1]['folder'])
                        else:
                            self.assertEqual(1, len(g))
                            self.assertEqual('/webdav/%s/' % i, g.items()[0][0])
                            self.assertTrue(g.items()[0][1]['folder'])
                            self.assertEqual(i, g.items()[0][1]['displayname'])
        
        self.assertEqual(0, len(DoGet(_REMOTE, '/patients')))
        with open(GetDatabasePath('DummyCT.dcm'), 'rb') as f:
            DoPut(_REMOTE, '/webdav/uploads/dummy', f.read(), 'text/plain')        

        while len(DoGet(_REMOTE, '/patients')) == 0:
            time.sleep(0.01)
        self.assertEqual(1, len(DoGet(_REMOTE, '/patients')))
            

    def test_log_categories(self):
        original = DoGet(_REMOTE, '/tools/log-level-http')
        
        DoPut(_REMOTE, '/tools/log-level-http', 'default')
        self.assertEqual('default', DoGet(_REMOTE, '/tools/log-level-http'))
        DoGet(_REMOTE, '/system')

        DoPut(_REMOTE, '/tools/log-level-http', 'verbose')
        self.assertEqual('verbose', DoGet(_REMOTE, '/tools/log-level-http'))
        DoGet(_REMOTE, '/system')

        DoPut(_REMOTE, '/tools/log-level-http', 'trace')
        self.assertEqual('trace', DoGet(_REMOTE, '/tools/log-level-http'))
        DoGet(_REMOTE, '/system')

        self.assertRaises(Exception, lambda: DoPut(_REMOTE, '/tools/log-level-http', 'nope'))
        
        # Switch back to the original log level
        DoPut(_REMOTE, '/tools/log-level-http', original)

        for c in [ 'generic', 'http', 'dicom', 'plugins', 'sqlite', 'lua', 'jobs' ]:
            DoPut(_REMOTE, '/tools/log-level-%s' % c, DoGet(_REMOTE, '/tools/log-level-%s' % c))

        self.assertRaises(Exception, lambda: DoPut(_REMOTE, '/tools/log-level-nope', 'default'))


    def test_upload_zip(self):
        f = StringIO()
        with zipfile.ZipFile(f, 'w') as z:
            z.writestr('hello/world/invalid.txt', 'Hello world')
            with open(GetDatabasePath('DummyCT.dcm'), 'rb') as g:
                c = g.read()
                z.writestr('hello/world/dicom1.dcm', c)
                z.writestr('hello/world/dicom2.dcm', c)

        f.seek(0)
        i = DoPost(_REMOTE, '/instances', f.read())

        self.assertEqual(2, len(i))
        self.assertEqual(i[0], i[1])
        self.assertEqual(6, len(i[0]))
        self.assertEqual('66a662ce-7430e543-bad44d47-0dc5a943-ec7a538d', i[0]['ID'])
        self.assertEqual('f2635388-f01d497a-15f7c06b-ad7dba06-c4c599fe', i[0]['ParentSeries'])
        self.assertEqual('b9c08539-26f93bde-c81ab0d7-bffaf2cb-a4d0bdd0', i[0]['ParentStudy'])
        self.assertEqual('6816cb19-844d5aee-85245eba-28e841e6-2414fae2', i[0]['ParentPatient'])
        self.assertEqual('/instances/66a662ce-7430e543-bad44d47-0dc5a943-ec7a538d', i[0]['Path'])

        # Both are "Success" (instead of one "AlreadyStored"), because "OverwriteInstance" is true
        self.assertEqual('Success', i[0]['Status']) 


    def test_transfer_syntax_no_metaheader(self):
        a = UploadInstance(_REMOTE, 'TransferSyntaxes/1.2.840.10008.1.2.dcm')['ID']
        m = DoGet(_REMOTE, '/instances/%s/metadata?expand' % a)
        self.assertEqual('1.2.840.10008.5.1.4.1.1.4', m['SopClassUid'])

        # This fails on Orthanc <= 1.8.1
        self.assertTrue('TransferSyntax' in m)
        self.assertEqual('1.2.840.10008.1.2', m['TransferSyntax'])


    def test_upload_multipart_1(self):
        # This tests the "Upload" button in Orthanc Explorer

        def EncodeChunk(data, boundary, filename):
            return (('--%s\r\n' +
                     'Content-Disposition  :   form-data  ; name ="files[]"   ; filename = "%s"  \r\n' +
                     '\r\n%s\r\n') % (boundary, filename, data))
        
        with open(GetDatabasePath('DummyCT.dcm'), 'rb') as f:
            dcm1 = f.read()

        with open(GetDatabasePath('ColorTestMalaterre.dcm'), 'rb') as f:
            dcm2 = f.read()

        self.assertEqual(0, len(DoGet(_REMOTE, '/instances')))
            
        boundary = '----WebKitFormBoundarypJDNQqJPoXiorRmQ'
        m = DoPost(_REMOTE, '/instances', (EncodeChunk(dcm1, boundary, 'DummyCT.dcm') +
                                           EncodeChunk(dcm2, boundary, 'ColorTestMalaterre.dcm') +
                                           '--' + boundary + '--'), headers = {
                       'Content-Type' : 'multipart/form-data   ;    boundary  =  %s  ' % boundary,
                       'X-Requested-With' : 'XMLHttpRequest',
                   })

        self.assertEqual(2, len(DoGet(_REMOTE, '/instances')))


    def test_upload_multipart_2(self):
        # This tests the "maxChunkSize" option of "jQuery File Upload
        # 5.12", whose source code can be found in:
        # "OrthancServer/OrthancExplorer/libs/jquery-file-upload/"

        def EncodeBody(data, boundary, filename):
            return (('--%s\r\n' +
                     'Content-Disposition: form-data; name="files[]"; filename="%s"\r\n' +
                     '\r\n%s\r\n--%s') % (boundary, filename, data, boundary))
        
        with open(GetDatabasePath('DummyCT.dcm'), 'rb') as f:
            dcm = f.read()

        with open(GetDatabasePath('ColorTestMalaterre.dcm'), 'rb') as f:
            dcm2 = f.read()

        boundary = '----WebKitFormBoundarypJDNQqJPoXiorRmQ'

        self.assertEqual(0, len(DoGet(_REMOTE, '/instances')))
        m = DoPost(_REMOTE, '/instances',
                   EncodeBody(dcm[0:1000], boundary, 'DummyCT.dcm'),
                   headers = {
                       'Content-Type' : 'multipart/form-data; boundary=%s' % boundary,
                       'X-Requested-With' : 'XMLHttpRequest',
                       'X-File-Name' : 'DummyCT.dcm',
                       'X-File-Size' : str(len(dcm)),
                   })

        self.assertEqual(0, len(DoGet(_REMOTE, '/instances')))
        m = DoPost(_REMOTE, '/instances',
                   EncodeBody(dcm[1000:2000], boundary, 'DummyCT.dcm'),
                   headers = {
                       'Content-Type' : 'multipart/form-data; boundary=%s' % boundary,
                       'X-Requested-With' : 'XMLHttpRequest',
                       'X-File-Name' : 'DummyCT.dcm',
                       'X-File-Size' : str(len(dcm)),
                   })
        self.assertEqual(0, len(DoGet(_REMOTE, '/instances')))
        
        m = DoPost(_REMOTE, '/instances',
                   EncodeBody(dcm2, boundary, 'ColorTestMalaterre.dcm'),
                   headers = {
                       'Content-Type' : 'multipart/form-data; boundary=%s' % boundary,
                       'X-Requested-With' : 'XMLHttpRequest',
                       'X-File-Name' : 'ColorTestMalaterre.dcm',
                       'X-File-Size' : str(len(dcm2)),
                   })

        self.assertEqual(1, len(DoGet(_REMOTE, '/instances')))

        # Upload the last chunk => the file is now entirely available
        m = DoPost(_REMOTE, '/instances',
                   EncodeBody(dcm[2000:len(dcm)], boundary, 'DummyCT.dcm'),
                   headers = {
                       'Content-Type' : 'multipart/form-data; boundary=%s' % boundary,
                       'X-Requested-With' : 'XMLHttpRequest',
                       'X-File-Name' : 'DummyCT.dcm',
                       'X-File-Size' : str(len(dcm)),
                   })
        
        self.assertEqual(2, len(DoGet(_REMOTE, '/instances')))


    def test_pixel_data_offset(self):
        # New in Orthanc 1.9.1
        def Check(path, offset):
            i = UploadInstance(_REMOTE, path) ['ID']
            metadata = DoGetRaw(_REMOTE, '/instances/%s/metadata/PixelDataOffset' % i) [1]
            self.assertEqual(offset, metadata)

        Check('ColorTestMalaterre.dcm', str(0x03a0))
        Check('TransferSyntaxes/1.2.840.10008.1.2.1.dcm', str(0x037c))
        Check('TransferSyntaxes/1.2.840.10008.1.2.2.dcm', str(0x03e8))  # Big endian
        Check('TransferSyntaxes/1.2.840.10008.1.2.4.50.dcm', str(0x04ac))
        Check('TransferSyntaxes/1.2.840.10008.1.2.4.51.dcm', str(0x072c))
        Check('TransferSyntaxes/1.2.840.10008.1.2.4.57.dcm', str(0x0620))
        Check('TransferSyntaxes/1.2.840.10008.1.2.4.70.dcm', str(0x065a))
        Check('TransferSyntaxes/1.2.840.10008.1.2.4.80.dcm', str(0x0b46))
        Check('TransferSyntaxes/1.2.840.10008.1.2.4.81.dcm', str(0x073e))
        Check('TransferSyntaxes/1.2.840.10008.1.2.4.90.dcm', str(0x0b66))
        Check('TransferSyntaxes/1.2.840.10008.1.2.4.91.dcm', str(0x19b8))
        Check('TransferSyntaxes/1.2.840.10008.1.2.5.dcm', str(0x0b0a))
        Check('TransferSyntaxes/1.2.840.10008.1.2.dcm', '')  # No valid DICOM preamble


    def test_peer_store_straight(self):
        self.assertEqual(0, len(DoGet(_LOCAL, '/exports')['Exports']))
        self.assertEqual(0, len(DoGet(_REMOTE, '/exports')['Exports']))

        peer = DoGet(_REMOTE, '/peers/peer/system')
        if not IsOrthancVersionAbove(_LOCAL, 0, 8, 6):
            self.assertEqual(3, len(peer))
            self.assertEqual(5, peer['DatabaseVersion'])
            self.assertEqual('MyOrthanc', peer['Name'])
            self.assertEqual('0.8.6', peer['Version'])            
        
        with open(GetDatabasePath('DummyCT.dcm'), 'rb') as f:
            j = DoPost(_REMOTE, '/peers/peer/store-straight', f.read(), 'application/dicom')

            # Remote server is Orthanc 0.8.6, thus "ParentPatient",
            # "ParentStudy", "ParentSeries" are not reported
            if not IsOrthancVersionAbove(_LOCAL, 1, 11, 2):  # don't know which specific version the behaviour changed but this fails with 0.8.6
                self.assertEqual(3, len(j))
            else:
                self.assertEqual(6, len(j))
            self.assertEqual('66a662ce-7430e543-bad44d47-0dc5a943-ec7a538d', j['ID'])
            self.assertEqual('/instances/66a662ce-7430e543-bad44d47-0dc5a943-ec7a538d', j['Path'])
            self.assertEqual('Success', j['Status'])

        self.assertEqual(1, len(DoGet(_LOCAL, '/patients')))
        self.assertEqual(0, len(DoGet(_REMOTE, '/patients')))


    def test_cp246(self):
        # This fails on Orthanc <= 1.9.0
        a = UploadInstance(_REMOTE, '2021-02-19-MalaterreCP246.dcm')['ID']
        self.assertEqual(1, len(DoGet(_REMOTE, '/instances')))

        tags = DoGet(_REMOTE, '/instances/%s/tags?short' % a)
        self.assertEqual('1.2.840.10008.5.1.4.1.1.128', tags['0008,0016'])
        self.assertEqual('1.3.12.2.1107.5.1.4.36085.2.0.517715415141633', tags['0008,0018'])
        self.assertEqual('1.2.840.113745.101000.1008000.38179.6792.6324567', tags['0020,000d'])
        self.assertEqual('1.3.12.2.1107.5.1.4.36085.2.0.517714246252254', tags['0020,000e'])

        study = DoGet(_REMOTE, '/instances/%s/study' % a)
        self.assertEqual(tags['0020,000d'], study['MainDicomTags']['StudyInstanceUID'])

        series = DoGet(_REMOTE, '/instances/%s/series' % a)
        self.assertEqual(tags['0020,000e'], series['MainDicomTags']['SeriesInstanceUID'])

        instance = DoGet(_REMOTE, '/instances/%s' % a)
        self.assertEqual(tags['0008,0018'], instance['MainDicomTags']['SOPInstanceUID'])


    def test_revisions_metadata(self):
        # This test fails on Orthanc <= 1.9.1 (support for revisions
        # was introduced in 1.9.2), or if configuration option
        # "CheckRevisions" is "False". Conventions for HTTP headers
        # related to revisions mimic CouchDB:
        # https://docs.couchdb.org/en/stable/api/document/common.html
        i = UploadInstance(_REMOTE, 'DummyCT.dcm') ['ID']
        
        (headers, body) = DoGetRaw(_REMOTE, '/instances/%s/metadata/TransferSyntax' % i)
        self.assertEqual('200', headers['status'])
        self.assertEqual('"0-%s"' % ComputeMD5('1.2.840.10008.1.2.4.70'), headers['etag'])
        self.assertEqual('1.2.840.10008.1.2.4.70', body)
        
        (headers, body) = DoGetRaw(_REMOTE, '/instances/%s/metadata/TransferSyntax' % i, headers = {
            'If-None-Match' : '"aaa"'
        })
        self.assertEqual('400', headers['status'])  # Bad header format

        (headers, body) = DoGetRaw(_REMOTE, '/instances/%s/metadata/TransferSyntax' % i, headers = {
            'If-None-Match' : '"aaa-bbb"'
        })
        self.assertEqual('400', headers['status'])  # Bad header format
        
        (headers, body) = DoGetRaw(_REMOTE, '/instances/%s/metadata/TransferSyntax' % i, headers = {
            'If-None-Match' : '"0-16de4d7060d0b9d102ef0fca8acc892a"'
        })
        self.assertEqual('304', headers['status'])  # Not modified
        self.assertEqual('"0-16de4d7060d0b9d102ef0fca8acc892a"', headers['etag'])
        self.assertEqual('', body)  # Body must be empty on 304 status
        
        (headers, body) = DoGetRaw(_REMOTE, '/instances/%s/metadata/TransferSyntax' % i, headers = {
            'If-None-Match' : '"1-16de4d7060d0b9d102ef0fca8acc892a"'  # Bad revision, good MD5
        })
        self.assertEqual('200', headers['status'])
        self.assertEqual('"0-16de4d7060d0b9d102ef0fca8acc892a"', headers['etag'])
        self.assertEqual('1.2.840.10008.1.2.4.70', body)
        
        (headers, body) = DoGetRaw(_REMOTE, '/instances/%s/metadata/TransferSyntax' % i, headers = {
            'If-None-Match' : '"0-aaa"'  # Good revision, bad MD5
        })
        self.assertEqual('200', headers['status'])
        self.assertEqual('"0-16de4d7060d0b9d102ef0fca8acc892a"', headers['etag'])
        self.assertEqual('1.2.840.10008.1.2.4.70', body)
        
        (headers, body) = DoDeleteRaw(_REMOTE, '/instances/%s/metadata/TransferSyntax' % i)
        self.assertEqual('403', headers['status'])  # Forbidden (system metadata)
        
        (headers, body) = DoPutRaw(_REMOTE, '/instances/%s/metadata/TransferSyntax' % i, 'hello')
        self.assertEqual('403', headers['status'])  # Forbidden (system metadata)
        
        (headers, body) = DoPutRaw(_REMOTE, '/instances/%s/metadata/1024' % i, 'hello')
        self.assertEqual('200', headers['status'])
        self.assertEqual('"0-%s"' % ComputeMD5('hello'), headers['etag'])
        
        (headers, body) = DoGetRaw(_REMOTE, '/instances/%s/metadata/1024' % i)
        self.assertEqual('200', headers['status'])
        self.assertEqual('"0-5d41402abc4b2a76b9719d911017c592"', headers['etag'])
        self.assertEqual('hello', body)
        
        (headers, body) = DoGetRaw(_REMOTE, '/instances/%s/metadata/1024' % i, headers = {
            'If-None-Match' : '"0-5d41402abc4b2a76b9719d911017c592"'
        })
        self.assertEqual('304', headers['status'])
        self.assertEqual('"0-5d41402abc4b2a76b9719d911017c592"', headers['etag'])
        self.assertEqual('', body)
        
        (headers, body) = DoGetRaw(_REMOTE, '/instances/%s/metadata/1024' % i, headers = {
            'If-None-Match' : '"1-tata"'
        })
        self.assertEqual('200', headers['status'])
        self.assertEqual('"0-5d41402abc4b2a76b9719d911017c592"', headers['etag'])
        self.assertEqual('hello', body)
        self.assertEqual('hello', DoGet(_REMOTE, '/instances/%s/metadata/1024' % i))
        
        (headers, body) = DoDeleteRaw(_REMOTE, '/instances/%s/metadata/1024' % i)
        self.assertEqual('409', headers['status'])  # No revision given, but "CheckRevisions" is True
        
        (headers, body) = DoDeleteRaw(_REMOTE, '/instances/%s/metadata/1024' % i, headers = {
            'If-Match' : '45-5d41402abc4b2a76b9719d911017c592'
        })
        self.assertEqual('409', headers['status'])  # Conflict, as bad revision
        
        (headers, body) = DoDeleteRaw(_REMOTE, '/instances/%s/metadata/1024' % i, headers = {
            'If-Match' : '0-tata'
        })
        self.assertEqual('409', headers['status'])  # Conflict, as bad MD5
        
        (headers, body) = DoDeleteRaw(_REMOTE, '/instances/%s/metadata/1024' % i, headers = {
            'If-Match' : '0-5d41402abc4b2a76b9719d911017c592'
        })
        self.assertEqual('200', headers['status'])

        (headers, body) = DoDeleteRaw(_REMOTE, '/instances/%s/metadata/1024' % i, headers = {
            'If-Match' : '0-5d41402abc4b2a76b9719d911017c592'
        })
        self.assertEqual('404', headers['status'])

        (headers, body) = DoGetRaw(_REMOTE, '/instances/%s/metadata/1024' % i)
        self.assertEqual('404', headers['status'])

        self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/instances/%s/metadata/1024' % i))

        (headers, body) = DoPutRaw(_REMOTE, '/instances/%s/metadata/1024' % i, 'hello')
        self.assertEqual('200', headers['status'])
        self.assertEqual('"0-5d41402abc4b2a76b9719d911017c592"', headers['etag'])

        (headers, body) = DoPutRaw(_REMOTE, '/instances/%s/metadata/1024' % i, 'hello')
        self.assertEqual('409', headers['status'])

        (headers, body) = DoGetRaw(_REMOTE, '/instances/%s/metadata/1024' % i, headers = {
            'If-None-Match' : '"0-5d41402abc4b2a76b9719d911017c592"'
        })
        self.assertEqual('304', headers['status'])  # Not modified
        self.assertEqual('"0-5d41402abc4b2a76b9719d911017c592"', headers['etag'])
        self.assertEqual('', body)  # Body must be empty on 304 status

        (headers, body) = DoPutRaw(_REMOTE, '/instances/%s/metadata/1024' % i, 'hello', headers = {
            'If-Match' : '0-5d41402abc4b2a76b9719d911017c592'            
        })
        self.assertEqual('200', headers['status'])
        self.assertEqual('"1-5d41402abc4b2a76b9719d911017c592"', headers['etag'])
        self.assertEqual('', body)
        
        (headers, body) = DoGetRaw(_REMOTE, '/instances/%s/metadata/1024' % i, headers = {
            'If-None-Match' : headers['etag']
        })

        if headers['status'] == '200':
            print("Your database backend doesn't store revisions")
            (headers, body) = DoPutRaw(_REMOTE, '/instances/%s/metadata/1024' % i, 'hello2', headers = {
                'If-Match' : '1-5d41402abc4b2a76b9719d911017c592'
            })
            self.assertEqual('409', headers['status'])

            (headers, body) = DoPutRaw(_REMOTE, '/instances/%s/metadata/1024' % i, 'hello2', headers = {
                'If-Match' : '0-5d41402abc4b2a76b9719d911017c592'
            })
            self.assertEqual('200', headers['status'])
            self.assertEqual('"1-6e809cbda0732ac4845916a59016f954"', headers['etag'])
            self.assertEqual('', body)

        elif headers['status'] == '304':  # Revisions are supported
            (headers, body) = DoPutRaw(_REMOTE, '/instances/%s/metadata/1024' % i, 'hello2', headers = {
                'If-Match' : '0-5d41402abc4b2a76b9719d911017c592'
            })
            self.assertEqual('409', headers['status'])

            (headers, body) = DoPutRaw(_REMOTE, '/instances/%s/metadata/1024' % i, 'hello2', headers = {
                'If-Match' : '1-5d41402abc4b2a76b9719d911017c592'
            })
            self.assertEqual('200', headers['status'])
            self.assertEqual('"2-6e809cbda0732ac4845916a59016f954"', headers['etag'])
            self.assertEqual('', body)
        
        else:
            raise Exception('Internal error')

        self.assertEqual('hello2', DoGet(_REMOTE, '/instances/%s/metadata/1024' % i))
        

    def test_revisions_attachments(self):
        # This test fails on Orthanc <= 1.9.1 (support for revisions
        # was introduced in 1.9.2), or if configuration option
        # "CheckRevisions" is "False". Conventions for HTTP headers
        # related to revisions mimic CouchDB:
        # https://docs.couchdb.org/en/stable/api/document/common.html
        i = UploadInstance(_REMOTE, 'DummyCT.dcm') ['ID']

        with open(GetDatabasePath('DummyCT.dcm'), 'rb') as f:
            md5 = ComputeMD5(f.read())
        
        # "/compress", "/uncompress" and "/verify-md5" are POST
        # methods, and are not affected by revisions
        for suffix in [ '', '/compressed-data', '/compressed-md5', '/compressed-size',
                        '/data', '/is-compressed', '/md5', '/size' ]:
            (headers, body) = DoGetRaw(_REMOTE, '/instances/%s/attachments/dicom/%s' % (i, suffix))
            self.assertEqual('200', headers['status'])
            self.assertEqual('"0-%s"' % md5, headers['etag'])

            (headers, body) = DoGetRaw(_REMOTE, '/instances/%s/attachments/dicom/%s' % (i, suffix), headers = {
                'If-None-Match' : '"0-3e29b869978b6db4886355a2b1132124"',
            })
            self.assertEqual('304', headers['status'])  # Not modified
            self.assertEqual('"0-3e29b869978b6db4886355a2b1132124"', headers['etag'])
            self.assertEqual('', body)  # Body must be empty on 304 status

            (headers, body) = DoGetRaw(_REMOTE, '/instances/%s/attachments/dicom/%s' % (i, suffix), headers = {
                'If-None-Match' : '"tata"',  # Invalid header
            })
            self.assertEqual('400', headers['status'])

            (headers, body) = DoGetRaw(_REMOTE, '/instances/%s/attachments/dicom/%s' % (i, suffix), headers = {
                'If-None-Match' : '"1-%s"' % md5, # Bad revision, good MD5
            })
            self.assertEqual('200', headers['status'])
            self.assertEqual('"0-3e29b869978b6db4886355a2b1132124"', headers['etag'])

            (headers, body) = DoGetRaw(_REMOTE, '/instances/%s/attachments/dicom/%s' % (i, suffix), headers = {
                'If-None-Match' : '"0-tata"' # Good revision, bad MD5
            })
            self.assertEqual('200', headers['status'])
            self.assertEqual('"0-3e29b869978b6db4886355a2b1132124"', headers['etag'])

        (headers, body) = DoDeleteRaw(_REMOTE, '/instances/%s/attachments/dicom' % i)
        self.assertEqual('403', headers['status'])  # Forbidden (system metadata)
        
        (headers, body) = DoPutRaw(_REMOTE, '/instances/%s/attachments/dicom' % i, 'hello')
        self.assertEqual('403', headers['status'])  # Forbidden (system metadata)
        
        (headers, body) = DoPutRaw(_REMOTE, '/instances/%s/attachments/1024' % i, 'hello')
        self.assertEqual('200', headers['status'])
        self.assertEqual('"0-%s"' % ComputeMD5('hello'), headers['etag'])
        
        (headers, body) = DoGetRaw(_REMOTE, '/instances/%s/attachments/1024/data' % i)
        self.assertEqual('200', headers['status'])
        self.assertEqual('"0-5d41402abc4b2a76b9719d911017c592"', headers['etag'])
        self.assertEqual('hello', body)
        
        (headers, body) = DoGetRaw(_REMOTE, '/instances/%s/attachments/1024/data' % i, headers = {
            'If-None-Match' : '"0-5d41402abc4b2a76b9719d911017c592"'
        })
        self.assertEqual('304', headers['status'])
        self.assertEqual('"0-5d41402abc4b2a76b9719d911017c592"', headers['etag'])
        self.assertEqual('', body)

        for h in [ '"1-5d41402abc4b2a76b9719d911017c592"', # Bad revision, good MD5
                   '"0-tata"']: # Good revision, bad MD5 
            (headers, body) = DoGetRaw(_REMOTE, '/instances/%s/attachments/1024/data' % i, headers = {
                'If-None-Match' : h
            })
            self.assertEqual('200', headers['status'])
            self.assertEqual('"0-5d41402abc4b2a76b9719d911017c592"', headers['etag'])
            self.assertEqual('hello', body)
        
        (headers, body) = DoGetRaw(_REMOTE, '/instances/%s/attachments/1024/data' % i, headers = {
            'If-None-Match' : 'tata'  # Bad header format
        })
        self.assertEqual('400', headers['status'])
        self.assertEqual('"0-5d41402abc4b2a76b9719d911017c592"', headers['etag'])

        self.assertEqual('hello', DoGet(_REMOTE, '/instances/%s/attachments/1024/data' % i))
        
        (headers, body) = DoDeleteRaw(_REMOTE, '/instances/%s/attachments/1024' % i)
        self.assertEqual('409', headers['status'])  # No revision given, but "CheckRevisions" is True
        
        (headers, body) = DoDeleteRaw(_REMOTE, '/instances/%s/attachments/1024' % i, headers = {
            'If-Match' : '45-5d41402abc4b2a76b9719d911017c592'
        })
        self.assertEqual('409', headers['status'])  # Conflict, as bad revision
        
        (headers, body) = DoDeleteRaw(_REMOTE, '/instances/%s/attachments/1024' % i, headers = {
            'If-Match' : '0-tata'
        })
        self.assertEqual('409', headers['status'])  # Conflict, as bad MD5
        
        (headers, body) = DoDeleteRaw(_REMOTE, '/instances/%s/attachments/1024' % i, headers = {
            'If-Match' : '0-5d41402abc4b2a76b9719d911017c592'
        })
        self.assertEqual('200', headers['status'])

        (headers, body) = DoDeleteRaw(_REMOTE, '/instances/%s/attachments/1024' % i, headers = {
            'If-Match' : '0-5d41402abc4b2a76b9719d911017c592'
        })
        self.assertEqual('404', headers['status'])

        (headers, body) = DoGetRaw(_REMOTE, '/instances/%s/attachments/1024/data' % i)
        self.assertEqual('404', headers['status'])

        self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/instances/%s/attachments/1024' % i))

        (headers, body) = DoPutRaw(_REMOTE, '/instances/%s/attachments/1024' % i, 'hello')
        self.assertEqual('200', headers['status'])
        self.assertEqual('"0-5d41402abc4b2a76b9719d911017c592"', headers['etag'])

        (headers, body) = DoPutRaw(_REMOTE, '/instances/%s/attachments/1024' % i, 'hello')
        self.assertEqual('409', headers['status'])

        (headers, body) = DoGetRaw(_REMOTE, '/instances/%s/attachments/1024/data' % i, headers = {
            'If-None-Match' : '"0-5d41402abc4b2a76b9719d911017c592"'
        })
        self.assertEqual('304', headers['status'])  # Not modified
        self.assertEqual('"0-5d41402abc4b2a76b9719d911017c592"', headers['etag'])
        self.assertEqual('', body)  # Body must be empty on 304 status

        (headers, body) = DoPutRaw(_REMOTE, '/instances/%s/attachments/1024' % i, 'hello', headers = {
            'If-Match' : '0-5d41402abc4b2a76b9719d911017c592'            
        })
        self.assertEqual('200', headers['status'])
        self.assertEqual('"1-5d41402abc4b2a76b9719d911017c592"', headers['etag'])
        self.assertEqual('{}', body)
        
        (headers, body) = DoGetRaw(_REMOTE, '/instances/%s/attachments/1024/data' % i, headers = {
            'If-None-Match' : headers['etag']
        })

        if headers['status'] == '200':
            print("Your database backend doesn't store revisions")
            (headers, body) = DoPutRaw(_REMOTE, '/instances/%s/attachments/1024' % i, 'hello2', headers = {
                'If-Match' : '1-5d41402abc4b2a76b9719d911017c592'
            })
            self.assertEqual('409', headers['status'])

            (headers, body) = DoPutRaw(_REMOTE, '/instances/%s/attachments/1024' % i, 'hello2', headers = {
                'If-Match' : '0-5d41402abc4b2a76b9719d911017c592'
            })
            self.assertEqual('200', headers['status'])
            self.assertEqual('"1-6e809cbda0732ac4845916a59016f954"', headers['etag'])
            self.assertEqual('{}', body)

        elif headers['status'] == '304':  # Revisions are supported
            (headers, body) = DoPutRaw(_REMOTE, '/instances/%s/attachments/1024' % i, 'hello2', headers = {
                'If-Match' : '0-5d41402abc4b2a76b9719d911017c592'
            })
            self.assertEqual('409', headers['status'])

            (headers, body) = DoPutRaw(_REMOTE, '/instances/%s/attachments/1024' % i, 'hello2', headers = {
                'If-Match' : '1-5d41402abc4b2a76b9719d911017c592'
            })
            self.assertEqual('200', headers['status'])
            self.assertEqual('"2-6e809cbda0732ac4845916a59016f954"', headers['etag'])
            self.assertEqual('{}', body)
        
        else:
            raise Exception('Internal error')

        self.assertEqual('hello2', DoGet(_REMOTE, '/instances/%s/attachments/1024/data' % i))


    def test_issue_195(self):
        # This fails on Orthanc <= 1.9.2
        # https://bugs.orthanc-server.com/show_bug.cgi?id=195
        a = UploadInstance(_REMOTE, 'Issue195.dcm')['ID']
        b = DoGet(_REMOTE, '/instances/%s/file' % a,
                  headers = { 'Accept' : 'application/dicom+json' })

        # The expected result can be found by typing "dcm2json Database/Issue195.dcm"
        self.assertEqual(5, len(b))
        self.assertEqual(2, len(b["00080018"]))
        self.assertEqual("UI", b["00080018"]["vr"])
        self.assertEqual("1.2.276.0.7230010.3.1.4.8323329.13188.1620309604.848735",
                         b["00080018"]["Value"][0])

        self.assertEqual(2, len(b["0020000D"]))
        self.assertEqual("UI", b["0020000D"]["vr"])
        self.assertEqual("1.2.276.0.7230010.3.1.2.8323329.13188.1620309604.848733",
                         b["0020000D"]["Value"][0])

        self.assertEqual(2, len(b["0020000E"]))
        self.assertEqual("UI", b["0020000E"]["vr"])
        self.assertEqual("1.2.276.0.7230010.3.1.3.8323329.13188.1620309604.848734",
                         b["0020000E"]["Value"][0])

        self.assertEqual(1, len(b["00081030"]))  # Case of an empty value
        self.assertEqual("LO", b["00081030"]["vr"])

        self.assertEqual(2, len(b["0008103E"]))
        self.assertEqual("LO", b["0008103E"]["vr"])
        self.assertEqual("Hello1", b["0008103E"]["Value"][0])

        a = UploadInstance(_REMOTE, 'Issue195-bis.dcm')['ID']
        b = DoGet(_REMOTE, '/instances/%s/file' % a,
                  headers = { 'Accept' : 'application/dicom+json' })

        # The expected result can be found by typing "dcm2json Database/Issue195-bis.dcm"
        self.assertEqual(5, len(b))
        self.assertEqual(2, len(b["00080018"]))
        self.assertEqual("UI", b["00080018"]["vr"])
        self.assertEqual("1.2.276.0.7230010.3.1.4.8323329.6792.1625504071.652470",
                         b["00080018"]["Value"][0])

        self.assertEqual(2, len(b["0020000D"]))
        self.assertEqual("UI", b["0020000D"]["vr"])
        self.assertEqual("1.2.276.0.7230010.3.1.2.8323329.6792.1625504071.652468",
                         b["0020000D"]["Value"][0])

        self.assertEqual(2, len(b["0020000E"]))
        self.assertEqual("UI", b["0020000E"]["vr"])
        self.assertEqual("1.2.276.0.7230010.3.1.3.8323329.6792.1625504071.652469",
                         b["0020000E"]["Value"][0])

        self.assertEqual(2, len(b["00084567"]))
        self.assertEqual("UN", b["00084567"]["vr"])

        # NB: "QgA=" corresponds to the base64 encoding of (uint16_t) 0x42 in little endian:
        #     $ echo -n 'QgA=' | base64 -d | hexdump -C
        self.assertEqual("QgA=", b["00084567"]["InlineBinary"])

        # Case of an empty value, fails in Orthanc <= 1.9.2 because of issue #195
        self.assertEqual(1, len(b["00084565"]))
        self.assertEqual("UN", b["00084565"]["vr"])


    def test_modify_attribute(self):
        # This fails on Orthanc <= 1.9.3 (not implemented)
        # https://groups.google.com/g/orthanc-users/c/1pzCqT-ByXg/m/VyIGK5i5BgAJ
        i = UploadInstance(_REMOTE, 'DummyCT.dcm') ['ID']
        
        tags = DoGet(_REMOTE, '/instances/%s/tags?short' % i)
        self.assertFalse('0020,9165' in tags)
        
        i = DoPost(_REMOTE, '/studies/b9c08539-26f93bde-c81ab0d7-bffaf2cb-a4d0bdd0/modify', {
            "Replace": {
                "0020,9165": "0020,9056",
            }
        })
        instances = DoGet(_REMOTE, '/studies/%s/instances' % i['ID'])
        self.assertEqual(1, len(instances))
        
        tags = DoGet(_REMOTE, '/instances/%s/tags?short' % instances[0]['ID'])
        self.assertTrue('0020,9165' in tags)
        self.assertEqual('0020,9056', tags['0020,9165'])


    def test_issue_146(self):
        # "Update Anonyization to 2019c"
        # https://bugs.orthanc-server.com/show_bug.cgi?id=146

        def GetTags(study, params):
            a = DoPost(_REMOTE, '/studies/%s/anonymize' % study, params) ['ID']
            b = DoGet(_REMOTE, '/studies/%s/instances' % a)
            self.assertEqual(1, len(b))
            return DoGet(_REMOTE, '/instances/%s/tags?short' % b[0]['ID'])
            
        
        UploadInstance(_REMOTE, 'Issue146.dcm')
        study = '7c950970-321e4ab0-28446c5f-f94850f1-5c44634b'

        self.assertRaises(Exception, lambda: GetTags(study, { 'DicomVersion' : 'nope' }))

        tags2008 = GetTags(study, { 'DicomVersion' : '2008' })
        tags2017c = GetTags(study, { 'DicomVersion' : '2017c' })
        tags2021b = GetTags(study, { 'DicomVersion' : '2021b' })
        tags2023b = GetTags(study, { 'DicomVersion' : '2023b' })
        tagsDefault = GetTags(study, {})
        tagsReplace = GetTags(study, { 'Replace' : { 'StationName': 'tutu' }})

        orthancVersion = DoGet(_REMOTE, '/system') ['Version']
        if orthancVersion.startswith('mainline-'):  # happens in unstable orthancteam/orthanc images
            orthancVersion = 'mainline'
            
        self.assertEqual('Orthanc %s - PS 3.15-2008 Table E.1-1' % orthancVersion, tags2008['0012,0063'])
        self.assertEqual('Orthanc %s - PS 3.15-2017c Table E.1-1 Basic Profile' % orthancVersion, tags2017c['0012,0063'])
        self.assertEqual('Orthanc %s - PS 3.15-2021b Table E.1-1 Basic Profile' % orthancVersion, tags2021b['0012,0063'])
        self.assertEqual('Orthanc %s - PS 3.15-2023b Table E.1-1 Basic Profile' % orthancVersion, tags2023b['0012,0063'])
        if IsOrthancVersionAbove(_REMOTE, 1, 12, 7):
            self.assertEqual('Orthanc %s' % orthancVersion, tagsReplace['0012,0063'])

        self.assertEqual(tagsDefault['0012,0063'], tags2023b['0012,0063'])

        self.assertEqual(len(tags2021b), len(tags2023b))
        self.assertNotEqual(tags2021b, tags2023b)

        for t in [ tags2008, tags2017c, tags2021b, tags2023b, tagsDefault ]:
            self.assertTrue(t['0010,0010'].startswith('Anonymized'))
            self.assertEqual('1.2.840.10008.5.1.4.1.1.4', t['0008,0016'])
            self.assertEqual(36, len(t['0010,0020']))  # Length of a UUID
            self.assertEqual('YES', t['0012,0062'])

        for t in [ tags2008 ]:
            self.assertEqual('20200101', t['0008,0020'])
            
        for t in [ tags2017c, tags2021b, tags2023b, tagsDefault ]:
            self.assertEqual('', t['0008,0020'])  # Study Date, anonymized between 2008 and 2017c
        
        for t in [ tags2008, tags2017c ]:
            self.assertEqual('HELLO^C', t['0050,0020'])
            self.assertEqual('HELLO^D', t['3006,0002'])
            
        for t in [ tags2021b, tags2023b, tagsDefault ]:
            self.assertFalse('0050,0020' in t)    # Device Description, anonymized between 2017c and 2019c
            self.assertEqual('', t['3006,0002'])  # StructureSetLabel, anonymized between 2019c and 2021b


    def test_anonymize_relationships_6(self):
        # 2020-10-20 (Salim Kanoun): "I think I have hit an
        # anonymization issue for the tag 0008,1250. This tags is a
        # sequence containing StudyUID / Series UID of related series.
        # [After anonymization,] this tag keep a reference of the
        # original Study/Series UID.
        # https://groups.google.com/g/orthanc-users/c/T0IokiActrI/m/L9K0vfscAAAJ
        UploadInstance(_REMOTE, '2020-11-16-SalimKanounAnonymization.dcm')

        tags = DoGet(_REMOTE, '/instances/%s/tags?short' % DoGet(_REMOTE, '/instances') [0])
        self.assertEqual('1.2.840.113619.6.95.31.0.3.4.1.3175.13.6054282',
                         tags['0008,1250'][0]['0020,000d'])
        self.assertEqual('1.3.12.2.1107.5.1.4.11047.30000019111306043635400005028',
                         tags['0008,1250'][0]['0020,000e'])

        a = DoGet(_REMOTE, '/studies')
        self.assertEqual(1, len(a))
        b = DoPost(_REMOTE, '/studies/%s/anonymize' % a[0], {}) ['ID']

        c = DoGet(_REMOTE, '/studies/%s/instances' % b)
        self.assertEqual(1, len(c))
        tags = DoGet(_REMOTE, '/instances/%s/tags?short' % c[0]['ID'])

        # In Orthanc <= 1.9.3, the two tests below failed
        self.assertNotEqual('1.2.840.113619.6.95.31.0.3.4.1.3175.13.6054282',
                            tags['0008,1250'][0]['0020,000d'])
        self.assertNotEqual('1.3.12.2.1107.5.1.4.11047.30000019111306043635400005028',
                            tags['0008,1250'][0]['0020,000e'])


    def test_modify_subsequences(self):
        # New in Orthanc 1.9.4 (cf. LSD-629)
        UploadInstance(_REMOTE, 'Issue22-NoPixelData.dcm')
        studies = DoGet(_REMOTE, '/studies')
        self.assertEqual(1, len(studies))

        def GetTags(study):
            instances = DoGet(_REMOTE, '/studies/%s/instances' % study)
            self.assertEqual(1, len(instances))
            return DoGet(_REMOTE, '/instances/%s/tags?short' % instances[0]['ID'])

        tags1 = GetTags(studies[0])

        a = DoPost(_REMOTE, '/studies/%s/modify' % studies[0], {
              'Replace' : {
                  'PatientName' : 'Hello1',
                  'DimensionIndexSequence[1].DimensionDescriptionLabel' : 'Hello2',
                  'DimensionIndexSequence[*].PatientName' : 'Hello3',
                  'ReferencedImageEvidenceSequence[2].ReferencedSeriesSequence[0].ReferencedSOPSequence[0].ReferencedSOPInstanceUID' : 'Hello4',
                  'DimensionOrganizationSequence[0].DimensionOrganizationUID' : '1.2.3.4',
              },
              'Remove' : [
                  'ReferencedPerformedProcedureStepSequence',
                  'PerformedProtocolCodeSequence[0].CodeValue',
                  'SharedFunctionalGroupsSequence[*].ReferencedImageSequence[*].ReferencedSOPInstanceUID',
                  'SharedFunctionalGroupsSequence[*].ReferencedImageSequence[1].ReferencedSOPClassUID',
                  'SharedFunctionalGroupsSequence[2].ReferencedImageSequence',  # Inexistent tag
              ]
            })
        tags2 = GetTags(a['ID'])

        self.assertEqual('Anonymized1', tags1['0010,0010'])
        self.assertEqual('Hello1', tags2['0010,0010'])

        self.assertEqual('Stack ID', tags1['0020,9222'][0]['0020,9421'])
        self.assertEqual('In-Stack Position Number', tags1['0020,9222'][1]['0020,9421'])
        self.assertEqual('Stack ID', tags2['0020,9222'][0]['0020,9421'])
        self.assertEqual('Hello2', tags2['0020,9222'][1]['0020,9421'])

        for i in range(3):
            self.assertFalse('0010,0010' in tags1['0020,9222'][i])
            self.assertEqual('Hello3', tags2['0020,9222'][i]['0010,0010'])

        self.assertEqual('1.3.46.670589.11.22237.5.20.1.1.7512.2014100814064168452',
                         tags1['0008,9092'][2]['0008,1115'][0]['0008,1199'][0]['0008,1155'])
        self.assertEqual('Hello4',
                         tags2['0008,9092'][2]['0008,1115'][0]['0008,1199'][0]['0008,1155'])
        self.assertEqual(tags1['0008,9092'][1]['0008,1115'][0]['0008,1199'][0]['0008,1155'],
                         tags2['0008,9092'][1]['0008,1115'][0]['0008,1199'][0]['0008,1155'])

        self.assertTrue('0008,1111' in tags1)
        self.assertFalse('0008,1111' in tags2)
        self.assertTrue('0008,0100' in tags1['0040,0260'][0])
        self.assertFalse('0008,0100' in tags2['0040,0260'][0])

        for i in range(3):
            self.assertTrue('0008,1155' in tags1['5200,9229'][0]['0008,1140'][i])
            self.assertFalse('0008,1155' in tags2['5200,9229'][0]['0008,1140'][i])
            self.assertTrue('0008,1150' in tags1['5200,9229'][0]['0008,1140'][i])

        self.assertTrue('0008,1150' in tags2['5200,9229'][0]['0008,1140'][0])
        self.assertFalse('0008,1150' in tags2['5200,9229'][0]['0008,1140'][1])
        self.assertTrue('0008,1150' in tags2['5200,9229'][0]['0008,1140'][2])

        self.assertEqual('1.3.46.670589.11.22237.5.0.11272.2014100816243076000',
                         tags1['0020,9221'][0]['0020,9164'])
        self.assertEqual('1.2.3.4', tags2['0020,9221'][0]['0020,9164'])

        a = DoPost(_REMOTE, '/studies/%s/anonymize' % studies[0], {
              'Replace' : {
                  'DimensionIndexSequence[1].DimensionDescriptionLabel' : 'Hello1',
                  'DimensionOrganizationSequence[0].DimensionOrganizationUID' : '1.2.3.4',
              },
              'Remove' : [
                  'SharedFunctionalGroupsSequence[*].ReferencedImageSequence[*].ReferencedSOPInstanceUID',  # 5200,9229
              ],
              'Keep' : [
                  'ReferencedImageEvidenceSequence',  # 0008,9092
                  'DimensionIndexSequence',  # 0020,9222
                  'PerFrameFunctionalGroupsSequence[*].2005,140f[*].SOPInstanceUID',  # 5200,9230
                  '(5200,9230)[*].2005,140f[*].(0008,0023)',  # Compatibility with Orthanc 1.9.4
                  '(5200,9230)[*].2005,140f[*].(0008,0033)',  # Compatibility with Orthanc 1.9.4
              ],
              'DicomVersion' : '2021b',
              'KeepPrivateTags' : True  # Compatibility with Orthanc 1.9.4
            })
        tags3 = GetTags(a['ID'])

        # UIDs
        for i in [ '0008,0018',
                   '0010,0020',
                   '0008,0018',
                   '0010,0020' ]:
            self.assertNotEqual(tags1[i], tags3[i])

        self.assertNotEqual(tags1['0020,9221'][0]['0020,9164'],
                            tags3['0020,9221'][0]['0020,9164'])

        self.assertNotEqual(tags1['5200,9229'][0]['2005,140e'][0]['0008,0014'],
                            tags3['5200,9229'][0]['2005,140e'][0]['0008,0014'])

        # http://dicom.nema.org/medical/dicom/current/output/chtml/part15/chapter_E.html#table_E.1-1
        # Removals (X)
        for i in [ '0008,0021',
                   '0008,002a',
                   '0008,0031',
                   '0008,1030',
                   '0008,103e',
                   '0008,1111',
                   '0010,21c0',
                   '0040,0006',
                   '0040,0241',
                   '0040,0244',
                   '0040,0245',
                   '0040,0250',
                   '0040,0251',
                   '0040,0253',
                   '0040,0254',
                   '0040,0555',
        ]:
            self.assertTrue(i in tags1)
            self.assertFalse(i in tags3)

        # Clearings (Z)
        for i in [ '0008,0020',
                   '0008,0023',
                   '0008,0030',
                   '0008,0033' ]:
            self.assertNotEqual('', tags1[i])
            self.assertEqual('', tags3[i])

        # Replace
        self.assertEqual('In-Stack Position Number', tags1['0020,9222'][1]['0020,9421'])
        self.assertEqual('Hello1', tags3['0020,9222'][1]['0020,9421'])        
        self.assertEqual('1.2.3.4', tags3['0020,9221'][0]['0020,9164'])
        
        # "Keep" on DimensionIndexSequence
        for i in range(3):
            self.assertEqual(tags1['0020,9222'][i]['0020,9164'],
                             tags3['0020,9222'][i]['0020,9164'])

        # "Keep" on ReferencedImageEvidenceSequence
        self.assertEqual(json.dumps(tags1['0008,9092']),
                         json.dumps(tags3['0008,9092']))

        # "Keep" on PerFrameFunctionalGroupsSequence
        self.assertEqual(json.dumps(tags1['5200,9230']),
                         json.dumps(tags3['5200,9230']))

        # "Remove" on SharedFunctionalGroupsSequence
        for i in range(3):
            self.assertTrue('0008,1155' in tags1['5200,9229'][0]['0008,1140'][i])
            self.assertFalse('0008,1155' in tags3['5200,9229'][0]['0008,1140'][i])


    def test_bulk_modify(self):
        # New in Orthanc 1.9.4

        def GetModified(lst, resourceType, expectedCount = None):
            m = map(lambda x: x['ID'], filter(lambda x: x['Type'] == resourceType, lst['Resources']))
            if expectedCount != None:
                self.assertEqual(expectedCount, len(m))
            return m
        
        instance = UploadInstance(_REMOTE, 'DummyCT.dcm') ['ID']
        series = DoGet(_REMOTE, '/series') [0]
        study = DoGet(_REMOTE, '/studies') [0]
        patient = DoGet(_REMOTE, '/patients') [0]

        a = DoPost(_REMOTE, '/tools/bulk-modify', {
            'Resources' : [ instance ]
            })

        self.assertNotEqual(instance, GetModified(a, 'Instance', 1) [0])
        self.assertEqual(series, GetModified(a, 'Series', 1) [0])
        self.assertEqual(study, GetModified(a, 'Study', 1) [0])
        self.assertEqual(patient, GetModified(a, 'Patient', 1) [0])

        b = DoPost(_REMOTE, '/tools/bulk-anonymize', {
            'Resources' : [ instance ]
            })

        self.assertNotEqual(instance, GetModified(b, 'Instance', 1) [0])
        self.assertNotEqual(series, GetModified(b, 'Series', 1) [0])
        self.assertNotEqual(study, GetModified(b, 'Study', 1) [0])
        self.assertNotEqual(patient, GetModified(b, 'Patient', 1) [0])
        
        self.assertEqual(3, len(DoGet(_REMOTE, '/instances')))
        self.assertEqual(2, len(DoGet(_REMOTE, '/series')))
        self.assertEqual(2, len(DoGet(_REMOTE, '/studies')))
        self.assertEqual(2, len(DoGet(_REMOTE, '/patients')))

        DoPost(_REMOTE, '/tools/bulk-delete', {
            'Resources' : GetModified(b, 'Patient', 1) + GetModified(a, 'Instance', 1)
            })
        
        knee1 = UploadInstance(_REMOTE, 'Knee/T1/IM-0001-0001.dcm') ['ID']
        knee2 = UploadInstance(_REMOTE, 'Knee/T2/IM-0001-0001.dcm') ['ID']
        brainix = UploadInstance(_REMOTE, 'Brainix/Flair/IM-0001-0001.dcm') ['ID']
        
        self.assertEqual(4, len(DoGet(_REMOTE, '/instances')))
        self.assertEqual(4, len(DoGet(_REMOTE, '/series')))
        self.assertEqual(3, len(DoGet(_REMOTE, '/studies')))
        self.assertEqual(3, len(DoGet(_REMOTE, '/patients')))

        a = DoPost(_REMOTE, '/tools/bulk-modify', {
            'Resources' : [ knee1, brainix ]
            })

        self.assertEqual(6, len(DoGet(_REMOTE, '/instances')))
        self.assertEqual(4, len(DoGet(_REMOTE, '/series')))
        self.assertEqual(3, len(DoGet(_REMOTE, '/studies')))
        self.assertEqual(3, len(DoGet(_REMOTE, '/patients')))

        for i in GetModified(a, 'Instance', 2):
            self.assertTrue(not i in [ instance, knee1, knee2, brainix ])
            self.assertTrue(DoGet(_REMOTE, '/instances/%s/metadata/ModifiedFrom' % i) in [ knee1, brainix ])

        b = GetModified(a, 'Series', 2)
        self.assertTrue(DoGet(_REMOTE, '/instances/%s/series' % knee1) ['ID'] in b)
        self.assertTrue(DoGet(_REMOTE, '/instances/%s/series' % brainix) ['ID'] in b)
        self.assertFalse(DoGet(_REMOTE, '/instances/%s/series' % knee2) ['ID'] in b)
        self.assertFalse(DoGet(_REMOTE, '/instances/%s/series' % instance) ['ID'] in b)
        
        b = GetModified(a, 'Study', 2)
        self.assertTrue(DoGet(_REMOTE, '/instances/%s/study' % knee1) ['ID'] in b)
        self.assertTrue(DoGet(_REMOTE, '/instances/%s/study' % brainix) ['ID'] in b)
        self.assertTrue(DoGet(_REMOTE, '/instances/%s/study' % knee2) ['ID'] in b)
        self.assertFalse(DoGet(_REMOTE, '/instances/%s/study' % instance) ['ID'] in b)

        b = GetModified(a, 'Patient', 2)
        self.assertTrue(DoGet(_REMOTE, '/instances/%s/patient' % knee1) ['ID'] in b)
        self.assertTrue(DoGet(_REMOTE, '/instances/%s/patient' % brainix) ['ID'] in b)
        self.assertTrue(DoGet(_REMOTE, '/instances/%s/patient' % knee2) ['ID'] in b)
        self.assertFalse(DoGet(_REMOTE, '/instances/%s/patient' % instance) ['ID'] in b)
        
        DoPost(_REMOTE, '/tools/bulk-delete', {
            'Resources' : GetModified(a, 'Instance', 2)
        })

        sourceInstances = DoGet(_REMOTE, '/instances')
        sourceSeries = DoGet(_REMOTE, '/series')
        sourceStudies = DoGet(_REMOTE, '/studies')
        sourcePatients = DoGet(_REMOTE, '/patients')
        self.assertEqual(4, len(sourceInstances))
        self.assertEqual(4, len(sourceSeries))
        self.assertEqual(3, len(sourceStudies))
        self.assertEqual(3, len(sourcePatients))

        a = DoPost(_REMOTE, '/tools/bulk-anonymize', {
            'Resources' : [ knee1, brainix ]
            })

        self.assertEqual(6, len(DoGet(_REMOTE, '/instances')))
        self.assertEqual(6, len(DoGet(_REMOTE, '/series')))
        self.assertEqual(5, len(DoGet(_REMOTE, '/studies')))
        self.assertEqual(5, len(DoGet(_REMOTE, '/patients')))

        for i in GetModified(a, 'Instance', 2):
            self.assertFalse(i in sourceInstances)
            self.assertTrue(DoGet(_REMOTE, '/instances/%s/metadata/AnonymizedFrom' % i) in [ knee1, brainix ])

        for i in GetModified(a, 'Series', 2):
            self.assertFalse(i in sourceSeries)
            self.assertTrue(DoGet(_REMOTE, '/series/%s/metadata/AnonymizedFrom' % i) in sourceSeries)

        for i in GetModified(a, 'Study', 2):
            self.assertFalse(i in sourceStudies)
            self.assertTrue(DoGet(_REMOTE, '/studies/%s/metadata/AnonymizedFrom' % i) in sourceStudies)

        for i in GetModified(a, 'Patient', 2):
            self.assertFalse(i in sourcePatients)
            self.assertTrue(DoGet(_REMOTE, '/patients/%s/metadata/AnonymizedFrom' % i) in sourcePatients)

        DoPost(_REMOTE, '/tools/bulk-delete', {
            'Resources' : GetModified(a, 'Patient', 2)
        })

        self.assertEqual(4, len(DoGet(_REMOTE, '/instances')))
        self.assertEqual(4, len(DoGet(_REMOTE, '/series')))
        self.assertEqual(3, len(DoGet(_REMOTE, '/studies')))
        self.assertEqual(3, len(DoGet(_REMOTE, '/patients')))

        DoPost(_REMOTE, '/tools/bulk-delete', {
            'Resources' : [ instance,
                            DoGet(_REMOTE, '/instances/%s/patient' % knee1) ['ID'],
                            DoGet(_REMOTE, '/instances/%s/series' % brainix) ['ID'] ]
        })

        self.assertEqual(0, len(DoGet(_REMOTE, '/instances')))
        self.assertEqual(0, len(DoGet(_REMOTE, '/series')))
        self.assertEqual(0, len(DoGet(_REMOTE, '/studies')))
        self.assertEqual(0, len(DoGet(_REMOTE, '/patients')))


    def test_dicom_to_json_format(self):
        # Test new output formats for DICOM tags introduced in 1.9.4
        instance = UploadInstance(_REMOTE, 'DummyCT.dcm') ['ID']
        patient = DoGet(_REMOTE, '/instances/%s/patient' % instance) ['ID']
        study = DoGet(_REMOTE, '/instances/%s/study' % instance) ['ID']
        series = DoGet(_REMOTE, '/instances/%s/series' % instance) ['ID']
        
        self.assertEqual('KNIX', DoGet(_REMOTE, '/instances/%s/tags' % instance) ['0010,0010']['Value'])
        self.assertEqual('KNIX', DoGet(_REMOTE, '/instances/%s/tags?simplify' % instance) ['PatientName'])
        self.assertEqual('KNIX', DoGet(_REMOTE, '/instances/%s/tags?short' % instance) ['0010,0010'])
        self.assertEqual('PatientName', DoGet(_REMOTE, '/instances/%s/tags?full' % instance) ['0010,0010']['Name'])
        self.assertEqual('KNIX', DoGet(_REMOTE, '/instances/%s/tags?full' % instance) ['0010,0010']['Value'])
        self.assertEqual('String', DoGet(_REMOTE, '/instances/%s/tags?full' % instance) ['0010,0010']['Type'])

        # Test "GetInstanceHeader()" in "OrthancRestResources.cpp"
        self.assertEqual('1.2.840.10008.1.2.4.70', DoGet(_REMOTE, '/instances/%s/header' % instance) ['0002,0010']['Value'])
        self.assertEqual('1.2.840.10008.1.2.4.70', DoGet(_REMOTE, '/instances/%s/header?simplify' % instance) ['TransferSyntaxUID'])
        self.assertEqual('1.2.840.10008.1.2.4.70', DoGet(_REMOTE, '/instances/%s/header?short' % instance) ['0002,0010'])
        self.assertEqual('TransferSyntaxUID', DoGet(_REMOTE, '/instances/%s/header?full' % instance) ['0002,0010']['Name'])
        self.assertEqual('1.2.840.10008.1.2.4.70', DoGet(_REMOTE, '/instances/%s/header?full' % instance) ['0002,0010']['Value'])
        self.assertEqual('String', DoGet(_REMOTE, '/instances/%s/header?full' % instance) ['0002,0010']['Type'])

        # Test "ListResources()" in "OrthancRestResources.cpp"
        self.assertEqual('KNIX', DoGet(_REMOTE, '/patients?expand') [0]['MainDicomTags']['PatientName'])
        self.assertEqual('KNIX', DoGet(_REMOTE, '/patients?expand&short') [0]['MainDicomTags']['0010,0010'])
        self.assertEqual('KNIX', DoGet(_REMOTE, '/patients?expand&full') [0]['MainDicomTags']['0010,0010']['Value'])
        self.assertEqual('PatientName', DoGet(_REMOTE, '/patients?expand&full') [0]['MainDicomTags']['0010,0010']['Name'])

        self.assertEqual('KNIX', DoGet(_REMOTE, '/studies?expand') [0]['PatientMainDicomTags']['PatientName'])
        self.assertEqual('KNIX', DoGet(_REMOTE, '/studies?expand&short') [0]['PatientMainDicomTags']['0010,0010'])
        self.assertEqual('KNIX', DoGet(_REMOTE, '/studies?expand&full') [0]['PatientMainDicomTags']['0010,0010']['Value'])
        self.assertEqual('PatientName', DoGet(_REMOTE, '/studies?expand&full') [0]['PatientMainDicomTags']['0010,0010']['Name'])

        self.assertEqual('20070101', DoGet(_REMOTE, '/studies?expand') [0]['MainDicomTags']['StudyDate'])
        self.assertEqual('20070101', DoGet(_REMOTE, '/studies?expand&short') [0]['MainDicomTags']['0008,0020'])
        self.assertEqual('20070101', DoGet(_REMOTE, '/studies?expand&full') [0]['MainDicomTags']['0008,0020']['Value'])
        self.assertEqual('StudyDate', DoGet(_REMOTE, '/studies?expand&full') [0]['MainDicomTags']['0008,0020']['Name'])

        self.assertEqual('20070101', DoGet(_REMOTE, '/series?expand') [0]['MainDicomTags']['SeriesDate'])
        self.assertEqual('20070101', DoGet(_REMOTE, '/series?expand&short') [0]['MainDicomTags']['0008,0021'])
        self.assertEqual('20070101', DoGet(_REMOTE, '/series?expand&full') [0]['MainDicomTags']['0008,0021']['Value'])
        self.assertEqual('SeriesDate', DoGet(_REMOTE, '/series?expand&full') [0]['MainDicomTags']['0008,0021']['Name'])

        self.assertEqual('20070101', DoGet(_REMOTE, '/instances?expand') [0]['MainDicomTags']['InstanceCreationDate'])
        self.assertEqual('20070101', DoGet(_REMOTE, '/instances?expand&short') [0]['MainDicomTags']['0008,0012'])
        self.assertEqual('20070101', DoGet(_REMOTE, '/instances?expand&full') [0]['MainDicomTags']['0008,0012']['Value'])
        self.assertEqual('InstanceCreationDate', DoGet(_REMOTE, '/instances?expand&full') [0]['MainDicomTags']['0008,0012']['Name'])

        # Test "GetSingleResource()" in "OrthancRestResources.cpp"
        self.assertEqual('KNIX', DoGet(_REMOTE, '/patients/%s' % patient) ['MainDicomTags']['PatientName'])
        self.assertEqual('KNIX', DoGet(_REMOTE, '/patients/%s?short' % patient) ['MainDicomTags']['0010,0010'])
        self.assertEqual('KNIX', DoGet(_REMOTE, '/patients/%s?full' % patient) ['MainDicomTags']['0010,0010']['Value'])
        self.assertEqual('PatientName', DoGet(_REMOTE, '/patients/%s?full' % patient) ['MainDicomTags']['0010,0010']['Name'])

        self.assertEqual('KNIX', DoGet(_REMOTE, '/studies/%s' % study) ['PatientMainDicomTags']['PatientName'])
        self.assertEqual('KNIX', DoGet(_REMOTE, '/studies/%s?short' % study) ['PatientMainDicomTags']['0010,0010'])
        self.assertEqual('KNIX', DoGet(_REMOTE, '/studies/%s?full' % study) ['PatientMainDicomTags']['0010,0010']['Value'])
        self.assertEqual('PatientName', DoGet(_REMOTE, '/studies/%s?full' % study) ['PatientMainDicomTags']['0010,0010']['Name'])

        self.assertEqual('20070101', DoGet(_REMOTE, '/studies/%s' % study) ['MainDicomTags']['StudyDate'])
        self.assertEqual('20070101', DoGet(_REMOTE, '/studies/%s?short' % study) ['MainDicomTags']['0008,0020'])
        self.assertEqual('20070101', DoGet(_REMOTE, '/studies/%s?full' % study) ['MainDicomTags']['0008,0020']['Value'])
        self.assertEqual('StudyDate', DoGet(_REMOTE, '/studies/%s?full' % study) ['MainDicomTags']['0008,0020']['Name'])

        self.assertEqual('20070101', DoGet(_REMOTE, '/series/%s' % series) ['MainDicomTags']['SeriesDate'])
        self.assertEqual('20070101', DoGet(_REMOTE, '/series/%s?short' % series) ['MainDicomTags']['0008,0021'])
        self.assertEqual('20070101', DoGet(_REMOTE, '/series/%s?full' % series) ['MainDicomTags']['0008,0021']['Value'])
        self.assertEqual('SeriesDate', DoGet(_REMOTE, '/series/%s?full' % series) ['MainDicomTags']['0008,0021']['Name'])

        self.assertEqual('20070101', DoGet(_REMOTE, '/instances/%s' % instance) ['MainDicomTags']['InstanceCreationDate'])
        self.assertEqual('20070101', DoGet(_REMOTE, '/instances/%s?short' % instance) ['MainDicomTags']['0008,0012'])
        self.assertEqual('20070101', DoGet(_REMOTE, '/instances/%s?full' % instance) ['MainDicomTags']['0008,0012']['Value'])
        self.assertEqual('InstanceCreationDate', DoGet(_REMOTE, '/instances/%s?full' % instance) ['MainDicomTags']['0008,0012']['Name'])

        # Test "Find()" in "OrthancRestResources.cpp"
        a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Study', 'Query' : {}, 'Expand' : True })
        self.assertEqual('20070101', a[0]['MainDicomTags']['StudyDate'])
        self.assertEqual('KNIX', a[0]['PatientMainDicomTags']['PatientName'])

        a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Study', 'Query' : {}, 'Expand' : True, 'Short' : True })
        self.assertEqual('20070101', a[0]['MainDicomTags']['0008,0020'])
        self.assertEqual('KNIX', a[0]['PatientMainDicomTags']['0010,0010'])

        a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Study', 'Query' : {}, 'Expand' : True, 'Full' : True })
        self.assertEqual('20070101', a[0]['MainDicomTags']['0008,0020']['Value'])
        self.assertEqual('KNIX', a[0]['PatientMainDicomTags']['0010,0010']['Value'])
        self.assertEqual('StudyDate', a[0]['MainDicomTags']['0008,0020']['Name'])
        self.assertEqual('PatientName', a[0]['PatientMainDicomTags']['0010,0010']['Name'])

        # Test "GetChildResources()" in "OrthancRestResources.cpp"
        self.assertEqual('20070101', DoGet(_REMOTE, '/patients/%s/studies' % patient) [0]['MainDicomTags']['StudyDate'])
        self.assertEqual('20070101', DoGet(_REMOTE, '/patients/%s/studies?short' % patient) [0]['MainDicomTags']['0008,0020'])
        self.assertEqual('20070101', DoGet(_REMOTE, '/patients/%s/studies?full' % patient) [0]['MainDicomTags']['0008,0020']['Value'])
        self.assertEqual('StudyDate', DoGet(_REMOTE, '/patients/%s/studies?full' % patient) [0]['MainDicomTags']['0008,0020']['Name'])

        self.assertEqual('20070101', DoGet(_REMOTE, '/patients/%s/series' % patient) [0]['MainDicomTags']['SeriesDate'])
        self.assertEqual('20070101', DoGet(_REMOTE, '/patients/%s/series?short' % patient) [0]['MainDicomTags']['0008,0021'])
        self.assertEqual('20070101', DoGet(_REMOTE, '/patients/%s/series?full' % patient) [0]['MainDicomTags']['0008,0021']['Value'])
        self.assertEqual('SeriesDate', DoGet(_REMOTE, '/patients/%s/series?full' % patient) [0]['MainDicomTags']['0008,0021']['Name'])

        self.assertEqual('20070101', DoGet(_REMOTE, '/patients/%s/instances' % patient) [0]['MainDicomTags']['InstanceCreationDate'])
        self.assertEqual('20070101', DoGet(_REMOTE, '/patients/%s/instances?short' % patient) [0]['MainDicomTags']['0008,0012'])
        self.assertEqual('20070101', DoGet(_REMOTE, '/patients/%s/instances?full' % patient) [0]['MainDicomTags']['0008,0012']['Value'])
        self.assertEqual('InstanceCreationDate', DoGet(_REMOTE, '/patients/%s/instances?full' % patient) [0]['MainDicomTags']['0008,0012']['Name'])

        self.assertEqual('20070101', DoGet(_REMOTE, '/studies/%s/series' % study) [0]['MainDicomTags']['SeriesDate'])
        self.assertEqual('20070101', DoGet(_REMOTE, '/studies/%s/series?short' % study) [0]['MainDicomTags']['0008,0021'])
        self.assertEqual('20070101', DoGet(_REMOTE, '/studies/%s/series?full' % study) [0]['MainDicomTags']['0008,0021']['Value'])
        self.assertEqual('SeriesDate', DoGet(_REMOTE, '/studies/%s/series?full' % study) [0]['MainDicomTags']['0008,0021']['Name'])

        self.assertEqual('20070101', DoGet(_REMOTE, '/studies/%s/instances' % study) [0]['MainDicomTags']['InstanceCreationDate'])
        self.assertEqual('20070101', DoGet(_REMOTE, '/studies/%s/instances?short' % study) [0]['MainDicomTags']['0008,0012'])
        self.assertEqual('20070101', DoGet(_REMOTE, '/studies/%s/instances?full' % study) [0]['MainDicomTags']['0008,0012']['Value'])
        self.assertEqual('InstanceCreationDate', DoGet(_REMOTE, '/studies/%s/instances?full' % study) [0]['MainDicomTags']['0008,0012']['Name'])

        self.assertEqual('20070101', DoGet(_REMOTE, '/series/%s/instances' % series) [0]['MainDicomTags']['InstanceCreationDate'])
        self.assertEqual('20070101', DoGet(_REMOTE, '/series/%s/instances?short' % series) [0]['MainDicomTags']['0008,0012'])
        self.assertEqual('20070101', DoGet(_REMOTE, '/series/%s/instances?full' % series) [0]['MainDicomTags']['0008,0012']['Value'])
        self.assertEqual('InstanceCreationDate', DoGet(_REMOTE, '/series/%s/instances?full' % series) [0]['MainDicomTags']['0008,0012']['Name'])

        # Test "GetParentResource()" in "OrthancRestResources.cpp"
        self.assertEqual('KNIX', DoGet(_REMOTE, '/instances/%s/patient' % instance) ['MainDicomTags']['PatientName'])
        self.assertEqual('KNIX', DoGet(_REMOTE, '/instances/%s/patient?short' % instance) ['MainDicomTags']['0010,0010'])
        self.assertEqual('KNIX', DoGet(_REMOTE, '/instances/%s/patient?full' % instance) ['MainDicomTags']['0010,0010']['Value'])
        self.assertEqual('PatientName', DoGet(_REMOTE, '/instances/%s/patient?full' % instance) ['MainDicomTags']['0010,0010']['Name'])

        self.assertEqual('20070101', DoGet(_REMOTE, '/instances/%s/study' % instance) ['MainDicomTags']['StudyDate'])
        self.assertEqual('20070101', DoGet(_REMOTE, '/instances/%s/study?short' % instance) ['MainDicomTags']['0008,0020'])
        self.assertEqual('20070101', DoGet(_REMOTE, '/instances/%s/study?full' % instance) ['MainDicomTags']['0008,0020']['Value'])
        self.assertEqual('StudyDate', DoGet(_REMOTE, '/instances/%s/study?full' % instance) ['MainDicomTags']['0008,0020']['Name'])

        self.assertEqual('20070101', DoGet(_REMOTE, '/instances/%s/series' % instance) ['MainDicomTags']['SeriesDate'])
        self.assertEqual('20070101', DoGet(_REMOTE, '/instances/%s/series?short' % instance) ['MainDicomTags']['0008,0021'])
        self.assertEqual('20070101', DoGet(_REMOTE, '/instances/%s/series?full' % instance) ['MainDicomTags']['0008,0021']['Value'])
        self.assertEqual('SeriesDate', DoGet(_REMOTE, '/instances/%s/series?full' % instance) ['MainDicomTags']['0008,0021']['Name'])

        self.assertEqual('KNIX', DoGet(_REMOTE, '/series/%s/patient' % series) ['MainDicomTags']['PatientName'])
        self.assertEqual('KNIX', DoGet(_REMOTE, '/series/%s/patient?short' % series) ['MainDicomTags']['0010,0010'])
        self.assertEqual('KNIX', DoGet(_REMOTE, '/series/%s/patient?full' % series) ['MainDicomTags']['0010,0010']['Value'])
        self.assertEqual('PatientName', DoGet(_REMOTE, '/series/%s/patient?full' % series) ['MainDicomTags']['0010,0010']['Name'])

        self.assertEqual('20070101', DoGet(_REMOTE, '/series/%s/study' % series) ['MainDicomTags']['StudyDate'])
        self.assertEqual('20070101', DoGet(_REMOTE, '/series/%s/study?short' % series) ['MainDicomTags']['0008,0020'])
        self.assertEqual('20070101', DoGet(_REMOTE, '/series/%s/study?full' % series) ['MainDicomTags']['0008,0020']['Value'])
        self.assertEqual('StudyDate', DoGet(_REMOTE, '/series/%s/study?full' % series) ['MainDicomTags']['0008,0020']['Name'])

        self.assertEqual('KNIX', DoGet(_REMOTE, '/studies/%s/patient' % study) ['MainDicomTags']['PatientName'])
        self.assertEqual('KNIX', DoGet(_REMOTE, '/studies/%s/patient?short' % study) ['MainDicomTags']['0010,0010'])
        self.assertEqual('KNIX', DoGet(_REMOTE, '/studies/%s/patient?full' % study) ['MainDicomTags']['0010,0010']['Value'])
        self.assertEqual('PatientName', DoGet(_REMOTE, '/studies/%s/patient?full' % study) ['MainDicomTags']['0010,0010']['Name'])

        # Test "GetChildInstancesTags()" in "OrthancRestResources.cpp"
        self.assertEqual('KNIX', DoGet(_REMOTE, '/patients/%s/instances-tags?simplify' % patient) [instance]['PatientName'])
        self.assertEqual('KNIX', DoGet(_REMOTE, '/patients/%s/instances-tags?short' % patient) [instance]['0010,0010'])
        self.assertEqual('KNIX', DoGet(_REMOTE, '/patients/%s/instances-tags' % patient) [instance]['0010,0010']['Value'])
        self.assertEqual('PatientName', DoGet(_REMOTE, '/patients/%s/instances-tags' % patient) [instance]['0010,0010']['Name'])
        
        self.assertEqual('KNIX', DoGet(_REMOTE, '/studies/%s/instances-tags?simplify' % study) [instance]['PatientName'])
        self.assertEqual('KNIX', DoGet(_REMOTE, '/studies/%s/instances-tags?short' % study) [instance]['0010,0010'])
        self.assertEqual('KNIX', DoGet(_REMOTE, '/studies/%s/instances-tags' % study) [instance]['0010,0010']['Value'])
        self.assertEqual('PatientName', DoGet(_REMOTE, '/studies/%s/instances-tags' % study) [instance]['0010,0010']['Name'])
        
        self.assertEqual('KNIX', DoGet(_REMOTE, '/series/%s/instances-tags?simplify' % series) [instance]['PatientName'])
        self.assertEqual('KNIX', DoGet(_REMOTE, '/series/%s/instances-tags?short' % series) [instance]['0010,0010'])
        self.assertEqual('KNIX', DoGet(_REMOTE, '/series/%s/instances-tags' % series) [instance]['0010,0010']['Value'])
        self.assertEqual('PatientName', DoGet(_REMOTE, '/series/%s/instances-tags' % series) [instance]['0010,0010']['Name'])

        # Test "GetSharedTags()" in "OrthancRestResources.cpp"
        self.assertEqual('KNIX', DoGet(_REMOTE, '/patients/%s/shared-tags?simplify' % patient) ['PatientName'])
        self.assertEqual('KNIX', DoGet(_REMOTE, '/patients/%s/shared-tags?short' % patient) ['0010,0010'])
        self.assertEqual('KNIX', DoGet(_REMOTE, '/patients/%s/shared-tags' % patient) ['0010,0010']['Value'])
        self.assertEqual('PatientName', DoGet(_REMOTE, '/patients/%s/shared-tags' % patient) ['0010,0010']['Name'])
        
        self.assertEqual('KNIX', DoGet(_REMOTE, '/studies/%s/shared-tags?simplify' % study) ['PatientName'])
        self.assertEqual('KNIX', DoGet(_REMOTE, '/studies/%s/shared-tags?short' % study) ['0010,0010'])
        self.assertEqual('KNIX', DoGet(_REMOTE, '/studies/%s/shared-tags' % study) ['0010,0010']['Value'])
        self.assertEqual('PatientName', DoGet(_REMOTE, '/studies/%s/shared-tags' % study) ['0010,0010']['Name'])
        
        self.assertEqual('KNIX', DoGet(_REMOTE, '/series/%s/shared-tags?simplify' % series) ['PatientName'])
        self.assertEqual('KNIX', DoGet(_REMOTE, '/series/%s/shared-tags?short' % series) ['0010,0010'])
        self.assertEqual('KNIX', DoGet(_REMOTE, '/series/%s/shared-tags' % series) ['0010,0010']['Value'])
        self.assertEqual('PatientName', DoGet(_REMOTE, '/series/%s/shared-tags' % series) ['0010,0010']['Name'])

        # Test "GetModule()" in "OrthancRestResources.cpp"
        self.assertEqual('KNIX', DoGet(_REMOTE, '/patients/%s/module' % patient) ['0010,0010']['Value'])
        self.assertEqual('KNIX', DoGet(_REMOTE, '/patients/%s/module?simplify' % patient) ['PatientName'])
        self.assertEqual('KNIX', DoGet(_REMOTE, '/patients/%s/module?short' % patient) ['0010,0010'])

        self.assertEqual('KNIX', DoGet(_REMOTE, '/studies/%s/module-patient' % study) ['0010,0010']['Value'])
        self.assertEqual('KNIX', DoGet(_REMOTE, '/studies/%s/module-patient?simplify' % study) ['PatientName'])
        self.assertEqual('KNIX', DoGet(_REMOTE, '/studies/%s/module-patient?short' % study) ['0010,0010'])

        self.assertEqual('Knee (R)', DoGet(_REMOTE, '/studies/%s/module' % study) ['0008,1030']['Value'])
        self.assertEqual('Knee (R)', DoGet(_REMOTE, '/studies/%s/module?simplify' % study) ['StudyDescription'])
        self.assertEqual('Knee (R)', DoGet(_REMOTE, '/studies/%s/module?short' % study) ['0008,1030'])

        self.assertEqual('AX.  FSE PD', DoGet(_REMOTE, '/series/%s/module' % series) ['0008,103e']['Value'])
        self.assertEqual('AX.  FSE PD', DoGet(_REMOTE, '/series/%s/module?simplify' % series) ['SeriesDescription'])
        self.assertEqual('AX.  FSE PD', DoGet(_REMOTE, '/series/%s/module?short' % series) ['0008,103e'])

        self.assertEqual('1.2.840.113619.2.176.2025.1499492.7040.1171286242.109',
                         DoGet(_REMOTE, '/instances/%s/module' % instance) ['0008,0018']['Value'])
        self.assertEqual('1.2.840.113619.2.176.2025.1499492.7040.1171286242.109',
                         DoGet(_REMOTE, '/instances/%s/module?simplify' % instance) ['SOPInstanceUID'])
        self.assertEqual('1.2.840.113619.2.176.2025.1499492.7040.1171286242.109',
                         DoGet(_REMOTE, '/instances/%s/module?short' % instance) ['0008,0018'])

        # Test "ListQueryAnswers()" in "OrthancRestModalities.cpp"
        a = DoPost(_REMOTE, '/modalities/self/query', { 'Level' : 'Study',
                                                        'Query' : { 'PatientID' : '*' }}) ['ID']

        self.assertEqual(1, len(DoGet(_REMOTE, '/queries/%s/answers' % a)))
        self.assertEqual('ozp00SjY2xG', DoGet(_REMOTE, '/queries/%s/answers?expand' % a) [0]['0010,0020']['Value'])
        self.assertEqual('PatientID', DoGet(_REMOTE, '/queries/%s/answers?expand' % a) [0]['0010,0020']['Name'])
        self.assertEqual('ozp00SjY2xG', DoGet(_REMOTE, '/queries/%s/answers?expand&simplify' % a) [0]['PatientID'])
        self.assertEqual('ozp00SjY2xG', DoGet(_REMOTE, '/queries/%s/answers?expand&short' % a) [0]['0010,0020'])

        # Test "GetQueryOneAnswer()" in "OrthancRestModalities.cpp"
        self.assertEqual('ozp00SjY2xG', DoGet(_REMOTE, '/queries/%s/answers/0/content' % a) ['0010,0020']['Value'])
        self.assertEqual('PatientID', DoGet(_REMOTE, '/queries/%s/answers/0/content' % a) ['0010,0020']['Name'])
        self.assertEqual('ozp00SjY2xG', DoGet(_REMOTE, '/queries/%s/answers/0/content?simplify' % a) ['PatientID'])
        self.assertEqual('ozp00SjY2xG', DoGet(_REMOTE, '/queries/%s/answers/0/content?short' % a) ['0010,0020'])
        
        # Test "GetQueryArguments()" in "OrthancRestModalities.cpp"
        self.assertEqual('*', DoGet(_REMOTE, '/queries/%s/query' % a) ['0010,0020']['Value'])
        self.assertEqual('PatientID', DoGet(_REMOTE, '/queries/%s/query' % a) ['0010,0020']['Name'])
        self.assertEqual('*', DoGet(_REMOTE, '/queries/%s/query?simplify' % a) ['PatientID'])
        self.assertEqual('*', DoGet(_REMOTE, '/queries/%s/query?short' % a) ['0010,0020'])
        
        # Test "BulkContent()" in "OrthancRestResources.cpp"
        a = DoPost(_REMOTE, '/tools/bulk-content', { 'Resources' : [ patient, study, series, instance ] })
        self.assertEqual(4, len(a))
        self.assertEqual('ozp00SjY2xG', a[0]['MainDicomTags']['PatientID'])
        self.assertEqual('Knee (R)', a[1]['MainDicomTags']['StudyDescription'])
        self.assertEqual('KNIX', a[1]['PatientMainDicomTags']['PatientName'])
        self.assertEqual('AX.  FSE PD', a[2]['MainDicomTags']['SeriesDescription'])
        self.assertEqual('1.2.840.113619.2.176.2025.1499492.7040.1171286242.109',
                         a[3]['MainDicomTags']['SOPInstanceUID'])

        a = DoPost(_REMOTE, '/tools/bulk-content', { 'Resources' : [ patient, study, series, instance ],
                                                     'Short': True })
        self.assertEqual(4, len(a))
        self.assertEqual('ozp00SjY2xG', a[0]['MainDicomTags']['0010,0020'])
        self.assertEqual('Knee (R)', a[1]['MainDicomTags']['0008,1030'])
        self.assertEqual('KNIX', a[1]['PatientMainDicomTags']['0010,0010'])
        self.assertEqual('AX.  FSE PD', a[2]['MainDicomTags']['0008,103e'])
        self.assertEqual('1.2.840.113619.2.176.2025.1499492.7040.1171286242.109',
                         a[3]['MainDicomTags']['0008,0018'])
        
        a = DoPost(_REMOTE, '/tools/bulk-content', { 'Resources' : [ patient, study, series, instance ],
                                                     'Full': True })
        self.assertEqual(4, len(a))
        self.assertEqual('ozp00SjY2xG', a[0]['MainDicomTags']['0010,0020']['Value'])
        self.assertEqual('PatientID', a[0]['MainDicomTags']['0010,0020']['Name'])
        self.assertEqual('Knee (R)', a[1]['MainDicomTags']['0008,1030']['Value'])
        self.assertEqual('StudyDescription', a[1]['MainDicomTags']['0008,1030']['Name'])
        self.assertEqual('KNIX', a[1]['PatientMainDicomTags']['0010,0010']['Value'])
        self.assertEqual('PatientName', a[1]['PatientMainDicomTags']['0010,0010']['Name'])
        self.assertEqual('AX.  FSE PD', a[2]['MainDicomTags']['0008,103e']['Value'])
        self.assertEqual('SeriesDescription', a[2]['MainDicomTags']['0008,103e']['Name'])
        self.assertEqual('1.2.840.113619.2.176.2025.1499492.7040.1171286242.109',
                         a[3]['MainDicomTags']['0008,0018']['Value'])
        self.assertEqual('SOPInstanceUID', a[3]['MainDicomTags']['0008,0018']['Name'])
        

    def test_bulk_content(self):
        # New in Orthanc 1.9.4
        knee1 = UploadInstance(_REMOTE, 'Knee/T1/IM-0001-0001.dcm') ['ID']
        knee2 = UploadInstance(_REMOTE, 'Knee/T2/IM-0001-0001.dcm') ['ID']
        brainix = UploadInstance(_REMOTE, 'Brainix/Flair/IM-0001-0001.dcm') ['ID']

        brainixHierarchy = [
            DoGet(_REMOTE, '/instances/%s/patient' % brainix) ['ID'],
            DoGet(_REMOTE, '/instances/%s/study' % brainix) ['ID'],
            DoGet(_REMOTE, '/instances/%s/series' % brainix) ['ID'],
            brainix,
        ]
        
        a = DoPost(_REMOTE, '/tools/bulk-content', { 'Resources' : brainixHierarchy })
        self.assertEqual(4, len(a))
        b = map(lambda x: x['ID'], a)
        for i in range(4):
            self.assertEqual(brainixHierarchy[i], b[i])
            self.assertTrue('Metadata' in a[i])

        for (level, index) in [
                ('Patient', 0),
                ('Study', 1),
                ('Series', 2),
                ('Instance', 3),
                ]:
            a = DoPost(_REMOTE, '/tools/bulk-content', { 'Resources' : brainixHierarchy,
                                                         'Level' : level })
            self.assertEqual(1, len(a))
            self.assertEqual(level, a[0]['Type'])
            self.assertEqual(brainixHierarchy[index], a[0]['ID'])
            self.assertTrue('Metadata' in a[0])
        
            a = DoPost(_REMOTE, '/tools/bulk-content', { 'Resources' : [ brainix ],
                                                         'Level' : level,
                                                         'Metadata' : False })
            self.assertEqual(1, len(a))
            self.assertEqual(level, a[0]['Type'])
            self.assertEqual(brainixHierarchy[index], a[0]['ID'])
            self.assertFalse('Metadata' in a[0])

        a = DoPost(_REMOTE, '/tools/bulk-content', { 'Resources' : [ knee1, knee2, brainix ] })
        self.assertEqual(3, len(a))
        for item in a:
            self.assertEqual('Instance', item['Type'])
        b = map(lambda x: x['ID'], a)
        self.assertTrue(knee1 in b)
        self.assertTrue(knee2 in b)
        self.assertTrue(brainix in b)

        a = DoPost(_REMOTE, '/tools/bulk-content', { 'Resources' : [ knee1, knee2 ],
                                                     'Level' : 'Series' })
        self.assertEqual(2, len(a))
        for item in a:
            self.assertEqual('Series', item['Type'])
        b = map(lambda x: x['ID'], a)
        self.assertTrue(DoGet(_REMOTE, '/instances/%s' % knee1) ['ParentSeries'] in b)
        self.assertTrue(DoGet(_REMOTE, '/instances/%s' % knee2) ['ParentSeries'] in b)

        a = DoPost(_REMOTE, '/tools/bulk-content', { 'Resources' : [ knee1, knee2 ],
                                                     'Level' : 'Study',
                                                     'Metadata' : False })
        self.assertEqual(1, len(a))
        self.assertEqual(DoGet(_REMOTE, '/instances/%s/study' % knee1) ['ID'], a[0]['ID'])
        self.assertEqual('Study', a[0]['Type'])
        self.assertEqual('KNEE', a[0]['PatientMainDicomTags']['PatientName'])
        self.assertFalse('Metadata' in a[0])

        a = DoPost(_REMOTE, '/tools/bulk-content', { 'Resources' : [ knee1, knee2 ],
                                                     'Level' : 'Patient',
                                                     'Metadata' : True })
        self.assertEqual(1, len(a))
        self.assertEqual(DoGet(_REMOTE, '/instances/%s/patient' % knee1) ['ID'], a[0]['ID'])
        self.assertEqual('Patient', a[0]['Type'])
        self.assertEqual('KNEE', a[0]['MainDicomTags']['PatientName'])
        self.assertTrue('Metadata' in a[0])
        if IsOrthancVersionAbove(_REMOTE, 1, 12, 9) and HasPostgresIndexPlugin(_REMOTE):
            self.assertEqual(3, len(a[0]['Metadata']))
            self.assertTrue('MainDicomTagsSignature' in a[0]['Metadata'])
            self.assertTrue('PatientRecyclingOrder' in a[0]['Metadata'])
        elif IsOrthancVersionAbove(_REMOTE, 1, 11, 0):
            self.assertEqual(2, len(a[0]['Metadata']))
            self.assertTrue('MainDicomTagsSignature' in a[0]['Metadata'])
        else:
            self.assertEqual(1, len(a[0]['Metadata']))

        self.assertTrue('LastUpdate' in a[0]['Metadata'])

        for level in [ 'Instance', 'Series', 'Study', 'Patient' ]:
            a = DoPost(_REMOTE, '/tools/bulk-content', { 'Resources' : [ knee1, brainix ],
                                                         'Level' : level })
            self.assertEqual(2, len(a))
            for item in a:
                self.assertEqual(level, item['Type'])
            b = map(lambda x: x['ID'], a)
            if level == 'Instance':
                self.assertTrue(knee1 in b)
                self.assertTrue(brainix in b)
            else:
                self.assertTrue(DoGet(_REMOTE, '/instances/%s/%s' % (knee1, level.lower())) ['ID'] in b)
                self.assertTrue(DoGet(_REMOTE, '/instances/%s/%s' % (brainix, level.lower())) ['ID'] in b)


    def test_split_instances(self):
        # New in 1.9.4
        knee1 = UploadInstance(_REMOTE, 'Knee/T1/IM-0001-0001.dcm') ['ID']
        knee2 = UploadInstance(_REMOTE, 'Knee/T1/IM-0001-0002.dcm') ['ID']
        study = '0a9b3153-2512774b-2d9580de-1fc3dcf6-3bd83918'
        series = '6de73705-c4e65c1b-9d9ea1b5-cabcd8e7-f15e4285'

        self.assertEqual(1, len(DoGet(_REMOTE, '/patients')))
        self.assertEqual(1, len(DoGet(_REMOTE, '/studies')))
        self.assertEqual(1, len(DoGet(_REMOTE, '/series')))

        instances = DoGet(_REMOTE, '/instances')
        self.assertEqual(2, len(instances))
        self.assertEqual('1', DoGet(_REMOTE, '/instances/%s/tags?simplify' % knee1) ['InstanceNumber'])
        self.assertEqual('2', DoGet(_REMOTE, '/instances/%s/tags?simplify' % knee2) ['InstanceNumber'])
        for i in [ knee1, knee2 ]:
            self.assertEqual(series, DoGet(_REMOTE, '/instances/%s/series' % i) ['ID'])
            self.assertEqual(study, DoGet(_REMOTE, '/instances/%s/study' % i) ['ID'])
            
        self.assertRaises(Exception, lambda: DoPost(_REMOTE, '/studies/%s/split' % study, {
            'KeepSource' : False
        }))  # Neither "Instances", nor "Series"

        self.assertRaises(Exception, lambda: DoPost(_REMOTE, '/studies/%s/split' % study, {
            'KeepSource' : False,
            'Instances' : [ ],
            'Series' : [ ]
        }))  # Empty "Instances" and "Series"

        self.assertRaises(Exception, lambda: DoPost(_REMOTE, '/studies/%s/split' % study, {
            'Instances' : [ 'nope' ],
            'KeepSource' : False
        }))

        self.assertRaises(Exception, lambda: DoPost(_REMOTE, '/studies/%s/split' % study, {
            'Series' : [ 'nope' ],
            'KeepSource' : False
        }))

        result = DoPost(_REMOTE, '/studies/%s/split' % study, {
            'Instances' : [ knee1 ],
            'KeepSource' : False
        })

        self.assertEqual(1, len(DoGet(_REMOTE, '/patients')))
        self.assertEqual(2, len(DoGet(_REMOTE, '/studies')))
        self.assertEqual(2, len(DoGet(_REMOTE, '/series')))

        instances = DoGet(_REMOTE, '/instances')
        self.assertEqual(2, len(instances))

        self.assertFalse(knee1 in instances)
        self.assertTrue(knee2 in instances)
        instances.remove(knee2)
        self.assertEqual(series, DoGet(_REMOTE, '/instances/%s/series' % knee2) ['ID'])
        self.assertEqual(study, DoGet(_REMOTE, '/instances/%s/study' % knee2) ['ID'])
        self.assertNotEqual(series, DoGet(_REMOTE, '/instances/%s/series' % instances[0]) ['ID'])
        self.assertNotEqual(study, DoGet(_REMOTE, '/instances/%s/study' % instances[0]) ['ID'])
        self.assertEqual('1', DoGet(_REMOTE, '/instances/%s/tags?simplify' % instances[0]) ['InstanceNumber'])


    def test_merge_instances(self):
        # New in Orthanc 1.9.4
        knee = UploadInstance(_REMOTE, 'Knee/T1/IM-0001-0001.dcm') ['ID']
        brainix = UploadInstance(_REMOTE, 'Brainix/Flair/IM-0001-0001.dcm') ['ID']
        brainixStudy = DoGet(_REMOTE, '/instances/%s/study' % brainix) ['ID']

        self.assertEqual(2, len(DoGet(_REMOTE, '/patients')))
        self.assertEqual(2, len(DoGet(_REMOTE, '/studies')))
        self.assertEqual(2, len(DoGet(_REMOTE, '/series')))
        self.assertEqual(2, len(DoGet(_REMOTE, '/instances')))

        instances = DoGet(_REMOTE, '/instances')
        self.assertEqual(2, len(instances))
        self.assertTrue(brainix in instances)
        self.assertTrue(knee in instances)

        result = DoPost(_REMOTE, '/studies/%s/merge' % brainixStudy, {
            'Resources' : [ knee ]
        })
        
        self.assertEqual(1, len(DoGet(_REMOTE, '/patients')))
        self.assertEqual(1, len(DoGet(_REMOTE, '/studies')))
        self.assertEqual(2, len(DoGet(_REMOTE, '/series')))
        self.assertEqual(brainixStudy, DoGet(_REMOTE, '/studies')[0])

        instances = DoGet(_REMOTE, '/instances')
        self.assertEqual(2, len(instances))
        self.assertTrue(brainix in instances)
        self.assertFalse(knee in instances)


    def test_query_retrieve_format(self):
        # New in Orthanc 1.9.5
        # https://groups.google.com/g/orthanc-users/c/1KC4d-0K8s0/m/hfYYz1-tAgAJ
        i = UploadInstance(_REMOTE, 'Knee/T1/IM-0001-0001.dcm') ['ID']
        study = DoGet(_REMOTE, '/instances/%s/study' % i) ['MainDicomTags']['StudyInstanceUID']

        a = DoPost(_REMOTE, '/modalities/self/query', {
            'Level' : 'Study',
            'Query' : {}
        })

        b = DoGet(_REMOTE, a['Path'] + '/answers')
        self.assertEqual(1, len(b))
        self.assertEqual('0', b[0])
        
        b = DoGet(_REMOTE, a['Path'] + '/answers?expand')
        self.assertEqual(1, len(b))
        self.assertEqual(6, len(b[0]))
        self.assertEqual('ISO_IR 100', b[0]['0008,0005']['Value'])
        self.assertEqual('SpecificCharacterSet', b[0]['0008,0005']['Name'])
        self.assertEqual('A10003245599', b[0]['0008,0050']['Value'])
        self.assertEqual('AccessionNumber', b[0]['0008,0050']['Name'])
        self.assertEqual('STUDY', b[0]['0008,0052']['Value'])
        self.assertEqual('QueryRetrieveLevel', b[0]['0008,0052']['Name'])
        self.assertEqual('ORTHANC', b[0]['0008,0054']['Value'])
        self.assertEqual('RetrieveAETitle', b[0]['0008,0054']['Name'])
        self.assertEqual('887', b[0]['0010,0020']['Value'])
        self.assertEqual('PatientID', b[0]['0010,0020']['Name'])
        self.assertEqual('2.16.840.1.113669.632.20.121711.10000160881', b[0]['0020,000d']['Value'])
        self.assertEqual('StudyInstanceUID', b[0]['0020,000d']['Name'])

        for (key, value) in b[0].items():
            self.assertEqual('String', value['Type'])

        self.assertEqual(json.dumps(b[0]),
                         json.dumps(DoGet(_REMOTE, a['Path'] + '/answers/0/content')))

        # What is below this point didn't work on Orthanc <= 1.9.3
        
        b = DoGet(_REMOTE, a['Path'] + '/answers?expand&short')
        self.assertEqual(1, len(b))
        self.assertEqual(6, len(b[0]))
        self.assertEqual('ISO_IR 100', b[0]['0008,0005'])
        self.assertEqual('A10003245599', b[0]['0008,0050'])
        self.assertEqual('STUDY', b[0]['0008,0052'])
        self.assertEqual('ORTHANC', b[0]['0008,0054'])
        self.assertEqual('887', b[0]['0010,0020'])
        self.assertEqual('2.16.840.1.113669.632.20.121711.10000160881', b[0]['0020,000d'])
        self.assertEqual(json.dumps(b[0]),
                         json.dumps(DoGet(_REMOTE, a['Path'] + '/answers/0/content?short')))
        
        b = DoGet(_REMOTE, a['Path'] + '/answers?expand&simplify')
        self.assertEqual(1, len(b))
        self.assertEqual(6, len(b[0]))
        self.assertEqual('ISO_IR 100', b[0]['SpecificCharacterSet'])
        self.assertEqual('A10003245599', b[0]['AccessionNumber'])
        self.assertEqual('STUDY', b[0]['QueryRetrieveLevel'])
        self.assertEqual('ORTHANC', b[0]['RetrieveAETitle'])
        self.assertEqual('887', b[0]['PatientID'])
        self.assertEqual('2.16.840.1.113669.632.20.121711.10000160881', b[0]['StudyInstanceUID'])
        self.assertEqual(json.dumps(b[0]),
                         json.dumps(DoGet(_REMOTE, a['Path'] + '/answers/0/content?simplify')))

        b = DoPost(_REMOTE, '/queries/%s/retrieve' % a['ID'], {})
        self.assertEqual('REST API', b['Description'])
        self.assertEqual('ORTHANC', b['LocalAet'])
        self.assertEqual('ORTHANC', b['RemoteAet'])
        self.assertEqual(1, len(b['Query']))
        self.assertEqual(4, len(b['Query'][0]))
        self.assertEqual('A10003245599', b['Query'][0]['0008,0050'])
        self.assertEqual('STUDY', b['Query'][0]['0008,0052'])
        self.assertEqual('887', b['Query'][0]['0010,0020'])
        self.assertEqual('2.16.840.1.113669.632.20.121711.10000160881', b['Query'][0]['0020,000d'])
        
        # What is below this point didn't work on Orthanc <= 1.9.4

        b = DoPost(_REMOTE, '/queries/%s/retrieve' % a['ID'], { 'Full' : True })
        self.assertEqual('REST API', b['Description'])
        self.assertEqual('ORTHANC', b['LocalAet'])
        self.assertEqual('ORTHANC', b['RemoteAet'])
        self.assertEqual(1, len(b['Query']))
        self.assertEqual(4, len(b['Query'][0]))
        self.assertEqual('A10003245599', b['Query'][0]['0008,0050']['Value'])
        self.assertEqual('STUDY', b['Query'][0]['0008,0052']['Value'])
        self.assertEqual('887', b['Query'][0]['0010,0020']['Value'])
        self.assertEqual('2.16.840.1.113669.632.20.121711.10000160881', b['Query'][0]['0020,000d']['Value'])
        self.assertEqual('AccessionNumber', b['Query'][0]['0008,0050']['Name'])
        self.assertEqual('QueryRetrieveLevel', b['Query'][0]['0008,0052']['Name'])
        self.assertEqual('PatientID', b['Query'][0]['0010,0020']['Name'])
        self.assertEqual('StudyInstanceUID', b['Query'][0]['0020,000d']['Name'])

        b = DoPost(_REMOTE, '/queries/%s/retrieve' % a['ID'], { 'Simplify' : True })
        self.assertEqual('REST API', b['Description'])
        self.assertEqual('ORTHANC', b['LocalAet'])
        self.assertEqual('ORTHANC', b['RemoteAet'])
        self.assertEqual(1, len(b['Query']))
        self.assertEqual(4, len(b['Query'][0]))
        self.assertEqual('A10003245599', b['Query'][0]['AccessionNumber'])
        self.assertEqual('STUDY', b['Query'][0]['QueryRetrieveLevel'])
        self.assertEqual('887', b['Query'][0]['PatientID'])
        self.assertEqual('2.16.840.1.113669.632.20.121711.10000160881', b['Query'][0]['StudyInstanceUID'])


    def test_anonymize_nested(self):
        # New in Orthanc 1.9.5

        tags = {
            'MappingResourceIdentificationSequence' : [
                {
                    # Test "DicomModification::RelationshipsVisitor::GetDefaultAction()"
                    '0009,1002' : 'ABCD',  # Private tag not registered in dictionary
                    '0016,0071' : '-12',  # "GPS Latitude" whose VR is DS in "removals_"
                    '0034,0005' : '13',  # VR is OB, and in "clearings_" (only in DCMTK 3.6.2)

                    # Test "DicomModification::RelationshipsVisitor::VisitString()"
                    'StudyDescription' : 'Hello',  # Removed
                    'StudyDate' : '20210705',  # Cleared
                    '0009,1001' : '-1234',  # Private tag whose VR is DS

                    # Test anonymization of nested sequences
                    'ReferencedStudySequence' : [
                        {
                            'PatientID' : 'HELLO'
                        }
                    ],

                    # Non-anonymized tags
                    'CodeMeaning' : 'MEANING1',
                    'EquivalentCodeSequence' : [
                        {
                            'CodeMeaning' : 'MEANING2',
                        }
                    ],
                }
            ],
        }
        
        a = DoPost(_REMOTE, '/tools/create-dicom',
                   json.dumps({
                       'Tags' : tags,
                       'PrivateCreator' : 'Lunit',
                   })) ['ID']

        study = DoGet(_REMOTE, '/instances/%s/study' % a) ['ID']
        b = DoPost(_REMOTE, '/studies/%s/anonymize' % study, {}) ['ID']
        c = DoGet(_REMOTE, '/studies/%s/instances' % b)
        self.assertEqual(1, len(c))

        tags1 = DoGet(_REMOTE, '/instances/%s/tags?short' % a)
        tags2 = DoGet(_REMOTE, '/instances/%s/tags?short' % c[0]['ID'])

        # Only "StudyDate" must be present in
        # "MappingResourceIdentificationSequence" after anonymization
        self.assertEqual(1, len(tags1['0008,0124']))
        self.assertEqual(1, len(tags2['0008,0124']))
        self.assertEqual(9, len(tags1['0008,0124'][0]))
        self.assertEqual(3, len(tags2['0008,0124'][0]))
        self.assertEqual('', tags2['0008,0124'][0]['0008,0020'])
        self.assertEqual('MEANING1', tags2['0008,0124'][0]['0008,0104'])
        self.assertEqual('MEANING2', tags2['0008,0124'][0]['0008,0121'][0]['0008,0104'])

        self.assertTrue('0008,1110' in tags1['0008,0124'][0])
        self.assertFalse('0008,1110' in tags2['0008,0124'][0])


    def test_issue_200(self):
        # https://groups.google.com/g/orthanc-users/c/9CTLsL-JqDw/m/2I0xgyYHBAAJ
        # https://bugs.orthanc-server.com/show_bug.cgi?id=200
        self.assertEqual(0, len(DoGet(_REMOTE, '/changes') ['Changes']))
        self.assertEqual(0, len(DoGet(_REMOTE, '/changes?last') ['Changes']))
        u = UploadInstance(_REMOTE, 'DummyCT.dcm') ['ID']

        for change in DoGet(_REMOTE, '/changes') ['Changes']:
            self.assertTrue(re.match('[0-9]{8}T[0-9]{6}', change['Date']))
            self.assertTrue(re.match('[0-9a-z]{8}-[0-9a-z]{8}-[0-9a-z]{8}-[0-9a-z]{8}', change['ID']))

        last = DoGet(_REMOTE, '/changes?last') ['Changes']
        self.assertEqual(1, len(last))
        self.assertTrue(re.match('[0-9]{8}T[0-9]{6}', last[0]['Date']))
        self.assertTrue(re.match('[0-9a-z]{8}-[0-9a-z]{8}-[0-9a-z]{8}-[0-9a-z]{8}', last[0]['ID']))

        self.assertEqual(0, len(DoGet(_REMOTE, '/exports') ['Exports']))
        self.assertEqual(0, len(DoGet(_REMOTE, '/exports?last') ['Exports']))
        DoPost(_REMOTE, '/modalities/self/store', [ u ])

        for change in DoGet(_REMOTE, '/exports') ['Exports']:
            self.assertTrue(re.match('[0-9]{8}T[0-9]{6}', change['Date']))
            self.assertTrue(re.match('[0-9a-z]{8}-[0-9a-z]{8}-[0-9a-z]{8}-[0-9a-z]{8}', change['ID']))

        last = DoGet(_REMOTE, '/exports?last') ['Exports']
        self.assertEqual(1, len(last))
        self.assertEqual('ozp00SjY2xG', last[0]['PatientID'])
        self.assertEqual('self', last[0]['RemoteModality'])
        self.assertEqual('Instance', last[0]['ResourceType'])
        self.assertEqual('/instances/%s' % last[0]['ID'], last[0]['Path'])
        self.assertEqual('1.2.840.113619.2.176.2025.1499492.7391.1171285944.390', last[0]['StudyInstanceUID'])
        self.assertEqual('1.2.840.113619.2.176.2025.1499492.7391.1171285944.394', last[0]['SeriesInstanceUID'])
        self.assertEqual('1.2.840.113619.2.176.2025.1499492.7040.1171286242.109', last[0]['SOPInstanceUID'])
        self.assertTrue(re.match('[0-9]{8}T[0-9]{6}', last[0]['Date']))
        self.assertTrue(re.match('[0-9a-z]{8}-[0-9a-z]{8}-[0-9a-z]{8}-[0-9a-z]{8}', last[0]['ID']))


    def test_upload_dicomdir_archive(self):
        # This test fails on Orthanc <= 1.9.6
        # https://groups.google.com/g/orthanc-users/c/sgBU89o4nhU/m/kbRAYiQUAAAJ

        # Create a ZIP archive with a DICOMDIR
        instance = UploadInstance(_REMOTE, 'DummyCT.dcm') ['ID']
        study = DoGet(_REMOTE, '/instances/%s/study' % instance) ['ID']
        media = DoGet(_REMOTE, '/studies/%s/media' % study)
        DoDelete(_REMOTE, '/instances/%s' % instance)
        
        result = DoPost(_REMOTE, '/instances', media)
        self.assertEqual(1, len(result))
        self.assertEqual(instance, result[0]['ID'])
        self.assertEqual('Success', result[0]['Status'])


    def test_modify_keep_source(self):
        # https://groups.google.com/g/orthanc-users/c/1lvlBTs2WUY/m/HmYsc2CPBQAJ
        instance = UploadInstance(_REMOTE, 'DummyCT.dcm') ['ID']
        study = DoGet(_REMOTE, '/instances/%s/study' % instance) ['ID']
        self.assertEqual(1, len(DoGet(_REMOTE, '/instances')))

        a = DoPost(_REMOTE, '/studies/%s/anonymize' % study, {}) ['ID']
        self.assertEqual(2, len(DoGet(_REMOTE, '/instances')))
        DoDelete(_REMOTE, '/studies/%s' % a)
        self.assertEqual(1, len(DoGet(_REMOTE, '/instances')))

        a = DoPost(_REMOTE, '/studies/%s/anonymize' % study, { 'KeepSource' : True }) ['ID']
        self.assertEqual(2, len(DoGet(_REMOTE, '/instances')))
        DoDelete(_REMOTE, '/studies/%s' % a)
        self.assertEqual(1, len(DoGet(_REMOTE, '/instances')))

        a = DoPost(_REMOTE, '/studies/%s/anonymize' % study, { 'KeepSource' : False }) ['ID']
        self.assertEqual(1, len(DoGet(_REMOTE, '/instances')))
        DoDelete(_REMOTE, '/studies/%s' % a)
        self.assertEqual(0, len(DoGet(_REMOTE, '/instances')))

        UploadInstance(_REMOTE, 'DummyCT.dcm')
        a = DoPost(_REMOTE, '/studies/%s/modify' % study, { 'Replace' : { } }) ['ID']
        self.assertEqual(2, len(DoGet(_REMOTE, '/instances')))
        DoDelete(_REMOTE, '/studies/%s' % a)
        self.assertEqual(1, len(DoGet(_REMOTE, '/instances')))

        a = DoPost(_REMOTE, '/studies/%s/modify' % study, { 'KeepSource' : True }) ['ID']
        self.assertEqual(2, len(DoGet(_REMOTE, '/instances')))
        DoDelete(_REMOTE, '/studies/%s' % a)
        self.assertEqual(1, len(DoGet(_REMOTE, '/instances')))

        a = DoPost(_REMOTE, '/studies/%s/modify' % study, { 'KeepSource' : False }) ['ID']
        self.assertEqual(1, len(DoGet(_REMOTE, '/instances')))
        DoDelete(_REMOTE, '/studies/%s' % a)
        self.assertEqual(0, len(DoGet(_REMOTE, '/instances')))

        def GetStudy(a):
            b = filter(lambda x: x['Type'] == 'Study', a['Resources'])
            if len(b) == 1:
                return b[0]['ID']
            else:
                raise Exception()

        UploadInstance(_REMOTE, 'DummyCT.dcm')
        a = GetStudy(DoPost(_REMOTE, '/tools/bulk-anonymize', { 'Resources' : [ study ]}))
        self.assertEqual(2, len(DoGet(_REMOTE, '/instances')))
        DoDelete(_REMOTE, '/studies/%s' % a)
        self.assertEqual(1, len(DoGet(_REMOTE, '/instances')))

        a = GetStudy(DoPost(_REMOTE, '/tools/bulk-anonymize', { 'Resources' : [ study ], 'KeepSource' : True}))
        self.assertEqual(2, len(DoGet(_REMOTE, '/instances')))
        DoDelete(_REMOTE, '/studies/%s' % a)
        self.assertEqual(1, len(DoGet(_REMOTE, '/instances')))

        a = GetStudy(DoPost(_REMOTE, '/tools/bulk-anonymize', { 'Resources' : [ study ], 'KeepSource' : False}))
        self.assertEqual(1, len(DoGet(_REMOTE, '/instances')))
        DoDelete(_REMOTE, '/studies/%s' % a)
        self.assertEqual(0, len(DoGet(_REMOTE, '/instances')))

        UploadInstance(_REMOTE, 'DummyCT.dcm')
        a = GetStudy(DoPost(_REMOTE, '/tools/bulk-modify', { 'Resources' : [ study ], 'Replace' : { }}))
        self.assertEqual(2, len(DoGet(_REMOTE, '/instances')))
        DoDelete(_REMOTE, '/studies/%s' % a)
        # No more studies, because "bulk-modify" was not given a
        # level, so the modified instance belongs to the same study as
        # the original instance
        self.assertEqual(0, len(DoGet(_REMOTE, '/instances')))

        # The following fails on Orthanc <= 1.9.6 because "Level" was
        # introduced in 1.9.7

        UploadInstance(_REMOTE, 'DummyCT.dcm')
        a = GetStudy(DoPost(_REMOTE, '/tools/bulk-modify', { 'Level' : 'Study', 'Resources' : [ study ], 'Replace' : { }}))
        self.assertEqual(2, len(DoGet(_REMOTE, '/instances')))
        DoDelete(_REMOTE, '/studies/%s' % a)
        self.assertEqual(1, len(DoGet(_REMOTE, '/instances')))

        a = GetStudy(DoPost(_REMOTE, '/tools/bulk-modify', { 'Level' : 'Study', 'Resources' : [ study ], 'KeepSource' : True}))
        self.assertEqual(2, len(DoGet(_REMOTE, '/instances')))
        DoDelete(_REMOTE, '/studies/%s' % a)
        self.assertEqual(1, len(DoGet(_REMOTE, '/instances')))

        a = GetStudy(DoPost(_REMOTE, '/tools/bulk-modify', { 'Level' : 'Study', 'Resources' : [ study ], 'KeepSource' : False}))
        self.assertEqual(1, len(DoGet(_REMOTE, '/instances')))
        DoDelete(_REMOTE, '/studies/%s' % a)
        self.assertEqual(0, len(DoGet(_REMOTE, '/instances')))


    def test_multiframe_windowing(self):
        # Fixed in Orthanc 1.9.7
        a = UploadInstance(_REMOTE, 'MultiframeWindowing.dcm') ['ID']

        im = GetImage(_REMOTE, '/instances/%s/frames/0/rendered?window-center=127&window-width=256' % a)
        self.assertEqual(0x00, im.getpixel((0, 0)))
        self.assertEqual(0x10, im.getpixel((1, 0)))
        self.assertEqual(0x20, im.getpixel((0, 1)))
        self.assertEqual(0x30, im.getpixel((1, 1)))

        # Center the window on value "16 == 0x10", thus it has the
        # mid-level value (i.e. 127)
        im = GetImage(_REMOTE, '/instances/%s/frames/0/rendered?window-center=16&window-width=128' % a)
        self.assertEqual(127 - 2 * 16, im.getpixel((0, 0)))
        self.assertEqual(127, im.getpixel((1, 0)))
        self.assertEqual(127 + 2 * 16, im.getpixel((0, 1)))
        self.assertEqual(127 + 2 * 32, im.getpixel((1, 1)))

        # Window center and window width are burned in FrameVOILUTSequence for frame 0
        im = GetImage(_REMOTE, '/instances/%s/frames/0/rendered' % a)
        self.assertEqual(127 - 2 * 16, im.getpixel((0, 0)))
        self.assertEqual(127, im.getpixel((1, 0)))
        self.assertEqual(127 + 2 * 16, im.getpixel((0, 1)))
        self.assertEqual(127 + 2 * 32, im.getpixel((1, 1)))

        im = GetImage(_REMOTE, '/instances/%s/frames/1/rendered?window-center=127&window-width=256' % a)
        self.assertEqual(100, im.getpixel((0, 0)))
        self.assertEqual(116, im.getpixel((1, 0)))
        self.assertEqual(132, im.getpixel((0, 1)))
        self.assertEqual(148, im.getpixel((1, 1)))

        im = GetImage(_REMOTE, '/instances/%s/frames/2/rendered?window-center=127&window-width=256' % a)
        self.assertEqual(0, im.getpixel((0, 0)))
        self.assertEqual(32, im.getpixel((1, 0)))
        self.assertEqual(64, im.getpixel((0, 1)))
        self.assertEqual(96, im.getpixel((1, 1)))

        im = GetImage(_REMOTE, '/instances/%s/frames/3/rendered?window-center=127&window-width=256' % a)
        self.assertEqual(100, im.getpixel((0, 0)))
        self.assertEqual(132, im.getpixel((1, 0)))
        self.assertEqual(164, im.getpixel((0, 1)))
        self.assertEqual(196, im.getpixel((1, 1)))

        im = GetImage(_REMOTE, '/instances/%s/frames/0/rendered?window-center=16&window-width=128' % a)
        self.assertEqual(127 - 2 * 16, im.getpixel((0, 0)))
        self.assertEqual(127, im.getpixel((1, 0)))
        self.assertEqual(127 + 2 * 16, im.getpixel((0, 1)))
        self.assertEqual(127 + 2 * 32, im.getpixel((1, 1)))


    def test_dicom_seg(self):
        # This test fails in Orthanc <= 1.9.7
        a = UploadInstance(_REMOTE, 'DicomSeg.dcm') ['ID']
        
        self.assertEqual(96, len(DoGet(_REMOTE, '/instances/%s/frames' % a)))
        self.assertRaises(Exception, lambda: DoGet(_REMOTE, '/instances/%s/frames/96/preview' % a))

        nonEmptyFrames = [ 11, 12, 13, 14, 15, 16, 39, 40, 42, 43, 44, 45,
                           46, 47, 48, 49, 75, 76, 77, 78, 79, 80, 81 ]
        
        for i in range(96):
            im = GetImage(_REMOTE, '/instances/%s/frames/%d/preview' % (a, i))
            self.assertEqual('L', im.mode)
            self.assertEqual(256, im.size[0])
            self.assertEqual(256, im.size[1])

            e = im.getextrema()
            self.assertEqual(0, e[0])

            if e[1] == 0:
                self.assertFalse(i in nonEmptyFrames)
            else:
                self.assertTrue(i in nonEmptyFrames)

        im1 = GetImage(_REMOTE, '/instances/%s/frames/44/preview' % a)

        # Generated by "dcm2pnm +F 45 DicomSeg.dcm DicomSeg-Frame45.pgm"
        im2 = Image.open(GetDatabasePath('DicomSeg-Frame45.pgm'))
        im2 = im2.point(lambda p: 255 if p == 128 else 0)

        self.assertTrue(ImageChops.difference(im1, im2).getbbox() is None)


    def test_numpy(self):
        # New in Orthanc 1.10.0
        a = UploadInstance(_REMOTE, 'Brainix/Flair/IM-0001-0001.dcm')['ID']
        UploadInstance(_REMOTE, 'Brainix/Flair/IM-0001-0002.dcm')
        b = UploadInstance(_REMOTE, 'DicomSeg.dcm') ['ID']
        d = UploadInstance(_REMOTE, 'Issue124.dcm') ['ID']

        c = numpy.load(io.BytesIO(DoGet(_REMOTE, '/instances/%s/frames/0/numpy' % a)))
        self.assertFalse(isinstance(c, numpy.lib.npyio.NpzFile))
        self.assertEqual(numpy.float32, c.dtype)
        self.assertEqual((288, 288, 1), c.shape)
        self.assertAlmostEqual(0, c.min())
        self.assertAlmostEqual(536, c.max())

        c = numpy.load(io.BytesIO(DoGet(_REMOTE, '/instances/%s/frames/0/numpy?rescale=0' % a)))
        self.assertFalse(isinstance(c, numpy.lib.npyio.NpzFile))
        self.assertEqual(numpy.uint16, c.dtype)
        self.assertEqual((288, 288, 1), c.shape)
        self.assertEqual(0, c.min())
        self.assertEqual(536, c.max())

        c = numpy.load(io.BytesIO(DoGet(_REMOTE, '/instances/%s/numpy?rescale=1&compress=false' % a)))
        self.assertFalse(isinstance(c, numpy.lib.npyio.NpzFile))
        self.assertEqual(numpy.float32, c.dtype)
        self.assertEqual((1, 288, 288, 1), c.shape)

        series = DoGet(_REMOTE, '/instances/%s/series' % a)['ID']
        c = numpy.load(io.BytesIO(DoGet(_REMOTE, '/series/%s/numpy?rescale=true&compress=0' % series)))
        self.assertFalse(isinstance(c, numpy.lib.npyio.NpzFile))
        self.assertEqual(numpy.float32, c.dtype)
        self.assertEqual((2, 288, 288, 1), c.shape)

        series = DoGet(_REMOTE, '/instances/%s/series' % a)['ID']
        c = numpy.load(io.BytesIO(DoGet(_REMOTE, '/series/%s/numpy?rescale=1' % series)))
        self.assertFalse(isinstance(c, numpy.lib.npyio.NpzFile))
        self.assertEqual(numpy.float32, c.dtype)
        self.assertEqual((2, 288, 288, 1), c.shape)

        c = numpy.load(io.BytesIO(DoGet(_REMOTE, '/instances/%s/numpy?compress' % a)))
        self.assertTrue(isinstance(c, numpy.lib.npyio.NpzFile))
        self.assertEqual(1, len(c.files))
        self.assertEqual(numpy.float32, c['arr_0'].dtype)
        self.assertEqual((1, 288, 288, 1), c['arr_0'].shape)

        c = numpy.load(io.BytesIO(DoGet(_REMOTE, '/instances/%s/frames/0/numpy' % b)))
        self.assertFalse(isinstance(c, numpy.lib.npyio.NpzFile))
        self.assertEqual(numpy.float32, c.dtype)
        self.assertEqual((256, 256, 1), c.shape)
        self.assertAlmostEqual(0, c.min())
        self.assertAlmostEqual(0, c.max())

        c = numpy.load(io.BytesIO(DoGet(_REMOTE, '/instances/%s/frames/14/numpy' % b)))
        self.assertFalse(isinstance(c, numpy.lib.npyio.NpzFile))
        self.assertEqual(numpy.float32, c.dtype)
        self.assertEqual((256, 256, 1), c.shape)
        self.assertAlmostEqual(0, c.min())
        self.assertAlmostEqual(255, c.max())

        c = numpy.load(io.BytesIO(DoGet(_REMOTE, '/instances/%s/numpy' % b)))
        self.assertFalse(isinstance(c, numpy.lib.npyio.NpzFile))
        self.assertEqual(numpy.float32, c.dtype)
        self.assertEqual((96, 256, 256, 1), c.shape)

        series = DoGet(_REMOTE, '/instances/%s/series' % b)['ID']
        c = numpy.load(io.BytesIO(DoGet(_REMOTE, '/series/%s/numpy' % series)))
        self.assertFalse(isinstance(c, numpy.lib.npyio.NpzFile))
        self.assertEqual(numpy.float32, c.dtype)
        self.assertEqual((96, 256, 256, 1), c.shape)

        c = numpy.load(io.BytesIO(DoGet(_REMOTE, '/instances/%s/frames/0/numpy' % d)))
        self.assertFalse(isinstance(c, numpy.lib.npyio.NpzFile))
        self.assertEqual(numpy.float32, c.dtype)
        self.assertEqual((512, 512, 1), c.shape)
        self.assertAlmostEqual(-3024, c.min())  # RescaleIntercept equals -1024 in this image
        self.assertAlmostEqual(2374, c.max())

        c = numpy.load(io.BytesIO(DoGet(_REMOTE, '/instances/%s/frames/0/numpy?rescale=0' % d)))
        self.assertFalse(isinstance(c, numpy.lib.npyio.NpzFile))
        self.assertEqual(numpy.int16, c.dtype)
        self.assertEqual((512, 512, 1), c.shape)
        self.assertEqual(-2000, c.min())
        self.assertEqual(3398, c.max())


    def test_find_patient_name_with_brackets_and_star(self):
        u = UploadInstance(_REMOTE, 'Beaufix/IM-0001-0001.dcm')['ID']

        modified = DoPost(_REMOTE, '/instances/%s/modify' % u, json.dumps({
            "Replace" : {
                "PatientName" : "MyName[*]",
                "PatientID": "test_brackets"
                },
            "Force": True
            }),
            'application/json')

        m = DoPost(_REMOTE, '/instances', modified, 'application/dicom')['ID']

        a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Series',
                                             'Query' : { 'PatientName' : 'MyName[*]' }})
        self.assertEqual(1, len(a))

        a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Patient',
                                             'Query' : { 'PatientName' : 'MyName[*]' }})
        self.assertEqual(1, len(a))

        a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Study',
                                             'Query' : { 'PatientName' : 'MyName*' }})
        self.assertEqual(1, len(a))

        a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Patient',
                                             'Query' : { 'PatientName' : 'MyName*' }})
        self.assertEqual(1, len(a))

    def test_find_patient_name_with_brackets_only(self):
        u = UploadInstance(_REMOTE, 'Beaufix/IM-0001-0001.dcm')['ID']

        modified = DoPost(_REMOTE, '/instances/%s/modify' % u, json.dumps({
            "Replace" : {
                "PatientName" : "MyName2[]",
                "PatientID": "test_brackets2"
                },
            "Force": True
            }),
            'application/json')

        m = DoPost(_REMOTE, '/instances', modified, 'application/dicom')['ID']

        a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Series',
                                             'Query' : { 'PatientName' : 'MyName2[*]' }})
        self.assertEqual(1, len(a))

        a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Patient',
                                             'Query' : { 'PatientName' : 'MyName2[*]' }})
        self.assertEqual(1, len(a))

        a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Study',
                                             'Query' : { 'PatientName' : 'MyName2*' }})
        self.assertEqual(1, len(a))

        a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Patient',
                                             'Query' : { 'PatientName' : 'MyName2*' }})
        self.assertEqual(1, len(a))


    def test_rest_find_requested_tags(self):
        if IsOrthancVersionAbove(_REMOTE, 1, 11, 1):  # RequestedTags introduced in 1.11.0 but Sequences allowed since 1.11.1

            # Upload instances
            for i in range(2):
                UploadInstance(_REMOTE, 'Brainix/Flair/IM-0001-000%d.dcm' % (i + 1))

            # Patient level
            a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Patient',
                                                'CaseSensitive' : False,
                                                'Query' : { 'PatientName' : 'BRAINIX' },
                                                'RequestedTags' : [ 'PatientName', 'PatientID', 'PatientSex', 'PatientBirthDate'],
                                                'Expand': True
                                                })
            self.assertEqual(1, len(a))
            self.assertIn('PatientName', a[0]['RequestedTags'])
            self.assertIn('PatientID', a[0]['RequestedTags'])
            self.assertIn('PatientSex', a[0]['RequestedTags'])
            self.assertIn('PatientBirthDate', a[0]['RequestedTags'])

            self.assertEqual('BRAINIX', a[0]['RequestedTags']['PatientName'])
            self.assertEqual('5Yp0E', a[0]['RequestedTags']['PatientID'])
            self.assertEqual('0000', a[0]['RequestedTags']['PatientSex'])
            self.assertEqual('19490301', a[0]['RequestedTags']['PatientBirthDate'])

            # Study level, request patient tags too
            a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Study',
                                                'CaseSensitive' : False,
                                                'Query' : { 'PatientName' : 'BRAINIX' },
                                                'RequestedTags' : [ 'PatientName', 'StudyInstanceUID'],
                                                'Expand': True
                                                })
            self.assertEqual(1, len(a))
            self.assertIn('PatientName', a[0]['RequestedTags'])
            self.assertIn('StudyInstanceUID', a[0]['RequestedTags'])

            self.assertEqual('BRAINIX', a[0]['RequestedTags']['PatientName'])
            self.assertEqual('2.16.840.1.113669.632.20.1211.10000357775', a[0]['RequestedTags']['StudyInstanceUID'])


            # Series level, request patient and study tags too
            a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Series',
                                                'CaseSensitive' : False,
                                                'Query' : { 'PatientName' : 'BRAINIX' },
                                                'RequestedTags' : [ 'PatientName', 'StudyInstanceUID', 'SeriesInstanceUID', 'RequestAttributesSequence'],
                                                'Expand': True
                                                })
            self.assertEqual(1, len(a))
            self.assertIn('PatientName', a[0]['RequestedTags'])
            self.assertIn('StudyInstanceUID', a[0]['RequestedTags'])
            self.assertIn('SeriesInstanceUID', a[0]['RequestedTags'])
            self.assertIn('RequestAttributesSequence', a[0]['RequestedTags'])

            self.assertEqual('BRAINIX', a[0]['RequestedTags']['PatientName'])
            self.assertEqual('2.16.840.1.113669.632.20.1211.10000357775', a[0]['RequestedTags']['StudyInstanceUID'])
            self.assertEqual('1.3.46.670589.11.0.0.11.4.2.0.8743.5.5396.2006120114285654497', a[0]['RequestedTags']['SeriesInstanceUID'])
            self.assertEqual('A10029316690', a[0]['RequestedTags']['RequestAttributesSequence'][0]['RequestedProcedureID'])


            # Instance level, request patient, study and series tags too, include tags that are not part of the main dicom tags
            a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Series',
                                                'CaseSensitive' : False,
                                                'Query' : { 'PatientName' : 'BRAINIX' },
                                                'RequestedTags' : [ 'PatientName', 'StudyInstanceUID', 'SeriesInstanceUID', 'SOPInstanceUID', 'PhotometricInterpretation', 'RequestAttributesSequence'],
                                                'Expand': True
                                                })
            self.assertEqual(1, len(a))
            self.assertIn('PatientName', a[0]['RequestedTags'])
            self.assertIn('StudyInstanceUID', a[0]['RequestedTags'])
            self.assertIn('SeriesInstanceUID', a[0]['RequestedTags'])
            self.assertIn('PhotometricInterpretation', a[0]['RequestedTags'])
            self.assertIn('RequestAttributesSequence', a[0]['RequestedTags'])

            self.assertEqual('BRAINIX', a[0]['RequestedTags']['PatientName'])
            self.assertEqual('2.16.840.1.113669.632.20.1211.10000357775', a[0]['RequestedTags']['StudyInstanceUID'])
            self.assertEqual('1.3.46.670589.11.0.0.11.4.2.0.8743.5.5396.2006120114285654497', a[0]['RequestedTags']['SeriesInstanceUID'])
            self.assertEqual('MONOCHROME2', a[0]['RequestedTags']['PhotometricInterpretation'])
            self.assertEqual('A10029316690', a[0]['RequestedTags']['RequestAttributesSequence'][0]['RequestedProcedureID'])


    def test_rest_find_requested_tags_computed_tags(self):
        if IsOrthancVersionAbove(_REMOTE, 1, 11, 0):
            # Upload instances
            for i in range(2):
                UploadInstance(_REMOTE, 'Brainix/Flair/IM-0001-000%d.dcm' % (i + 1))


            # Patient level
            a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Patient',
                                                'CaseSensitive' : False,
                                                'Query' : { 'PatientName' : 'BRAINIX' },
                                                'RequestedTags' : [ 'PatientName', 'NumberOfPatientRelatedStudies', 'NumberOfPatientRelatedSeries', 'NumberOfPatientRelatedInstances'],
                                                'Expand': True
                                                })
            self.assertEqual(1, len(a))

            self.assertEqual('BRAINIX', a[0]['RequestedTags']['PatientName'])
            self.assertEqual('1', a[0]['RequestedTags']['NumberOfPatientRelatedStudies'])
            self.assertEqual('1', a[0]['RequestedTags']['NumberOfPatientRelatedSeries'])
            self.assertEqual('2', a[0]['RequestedTags']['NumberOfPatientRelatedInstances'])

            # Study level
            a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Study',
                                                'CaseSensitive' : False,
                                                'Query' : { 'PatientName' : 'BRAINIX' },
                                                'RequestedTags' : [ 'PatientName', 'StudyInstanceUID', 'ModalitiesInStudy', 'SOPClassesInStudy', 'NumberOfStudyRelatedInstances', 'NumberOfStudyRelatedSeries'],
                                                'Expand': True
                                                })
            self.assertEqual(1, len(a))

            self.assertEqual('BRAINIX', a[0]['RequestedTags']['PatientName'])
            self.assertEqual('2.16.840.1.113669.632.20.1211.10000357775', a[0]['RequestedTags']['StudyInstanceUID'])
            self.assertEqual('MR', a[0]['RequestedTags']['ModalitiesInStudy'])
            self.assertEqual('1.2.840.10008.5.1.4.1.1.4', a[0]['RequestedTags']['SOPClassesInStudy'])
            self.assertEqual('2', a[0]['RequestedTags']['NumberOfStudyRelatedInstances'])
            self.assertEqual('1', a[0]['RequestedTags']['NumberOfStudyRelatedSeries'])

            # Series level
            a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Series',
                                                'CaseSensitive' : False,
                                                'Query' : { 'PatientName' : 'BRAINIX' },
                                                'RequestedTags' : [ 'PatientName', 'StudyInstanceUID', 'NumberOfSeriesRelatedInstances'],
                                                'Expand': True
                                                })
            self.assertEqual(1, len(a))

            self.assertEqual('BRAINIX', a[0]['RequestedTags']['PatientName'])
            self.assertEqual('2.16.840.1.113669.632.20.1211.10000357775', a[0]['RequestedTags']['StudyInstanceUID'])
            self.assertEqual('2', a[0]['RequestedTags']['NumberOfSeriesRelatedInstances'])

            # Instance level
            a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Instance',
                                                'CaseSensitive' : False,
                                                'Query' : { 'PatientName' : 'BRAINIX' },
                                                'RequestedTags' : [ 'PatientName', 'StudyInstanceUID', 'SOPInstanceUID', 'InstanceAvailability'],
                                                'Expand': True
                                                })
            self.assertEqual(2, len(a))

            self.assertEqual('BRAINIX', a[0]['RequestedTags']['PatientName'])
            self.assertEqual('2.16.840.1.113669.632.20.1211.10000357775', a[0]['RequestedTags']['StudyInstanceUID'])
            self.assertEqual('ONLINE', a[0]['RequestedTags']['InstanceAvailability'])

    def test_list_resources_requested_tags(self):

        if IsOrthancVersionAbove(_REMOTE, 1, 11, 0):
            instance = UploadInstance(_REMOTE, 'DummyCT.dcm') ['ID']
            patient = DoGet(_REMOTE, '/instances/%s/patient' % instance) ['ID']
            study = DoGet(_REMOTE, '/instances/%s/study' % instance) ['ID']

            # list series and request tags that are not in the default main dicom tags
            a = DoGet(_REMOTE, '/studies/%s/series?expand&simplify&requestedTags=PatientName;Modality;SeriesInstanceUID;MRAcquisitionType' % study)

            self.assertEqual('2D', a[0]['RequestedTags']['MRAcquisitionType'])
            self.assertEqual('MR', a[0]['RequestedTags']['Modality'])
            self.assertEqual('KNIX', a[0]['RequestedTags']['PatientName'])
            self.assertEqual('1.2.840.113619.2.176.2025.1499492.7391.1171285944.394', a[0]['RequestedTags']['SeriesInstanceUID'])

            # list studies and request patient and studies tags
            a = DoGet(_REMOTE, '/patients/%s/studies?expand&simplify&requestedTags=PatientName;StudyInstanceUID' % patient)

            self.assertEqual('1.2.840.113619.2.176.2025.1499492.7391.1171285944.390', a[0]['RequestedTags']['StudyInstanceUID'])
            self.assertEqual('KNIX', a[0]['RequestedTags']['PatientName'])


            # list instances and request patient, studies and series tags including tags that are not in main dicom tags
            a = DoGet(_REMOTE, '/patients/%s/instances?expand&simplify&requestedTags=PatientName;StudyInstanceUID;SeriesInstanceUID;SOPInstanceUID;Rows;Columns;InstanceAvailability' % patient)

            self.assertEqual('1.2.840.113619.2.176.2025.1499492.7391.1171285944.390', a[0]['RequestedTags']['StudyInstanceUID'])
            self.assertEqual('1.2.840.113619.2.176.2025.1499492.7391.1171285944.394', a[0]['RequestedTags']['SeriesInstanceUID'])
            self.assertEqual('1.2.840.113619.2.176.2025.1499492.7040.1171286242.109', a[0]['RequestedTags']['SOPInstanceUID'])
            self.assertEqual('KNIX', a[0]['RequestedTags']['PatientName'])
            self.assertEqual('512', a[0]['RequestedTags']['Rows'])
            self.assertEqual('512', a[0]['RequestedTags']['Columns'])
            self.assertEqual('ONLINE', a[0]['RequestedTags']['InstanceAvailability'])


    def test_list_resources_requested_tags_study_computed_tags(self):

        if IsOrthancVersionAbove(_REMOTE, 1, 11, 0):
            UploadInstance(_REMOTE, 'Comunix/Pet/IM-0001-0001.dcm')  # make sure there are 2 different SOPClassUID in the DB

            instance = UploadInstance(_REMOTE, 'DummyCT.dcm') ['ID']
            patient = DoGet(_REMOTE, '/instances/%s/patient' % instance) ['ID']
            study = DoGet(_REMOTE, '/instances/%s/study' % instance) ['ID']

            # list studies and request patient and studies tags, including ModalitiesInStudy
            a = DoGet(_REMOTE, '/patients/%s/studies?expand&simplify&requestedTags=PatientName;StudyInstanceUID;ModalitiesInStudy;SOPClassesInStudy;NumberOfStudyRelatedInstances;NumberOfStudyRelatedSeries' % patient)

            self.assertEqual('1.2.840.113619.2.176.2025.1499492.7391.1171285944.390', a[0]['RequestedTags']['StudyInstanceUID'])
            self.assertEqual('KNIX', a[0]['RequestedTags']['PatientName'])
            self.assertEqual('MR', a[0]['RequestedTags']['ModalitiesInStudy'])
            self.assertEqual('1.2.840.10008.5.1.4.1.1.4', a[0]['RequestedTags']['SOPClassesInStudy'])
            self.assertEqual('1', a[0]['RequestedTags']['NumberOfStudyRelatedInstances'])
            self.assertEqual('1', a[0]['RequestedTags']['NumberOfStudyRelatedSeries'])

            a = DoGet(_REMOTE, '/studies/%s?expand&simplify&requestedTags=ModalitiesInStudy;NumberOfStudyRelatedInstances;NumberOfStudyRelatedSeries;SOPClassesInStudy' % study)            
            self.assertEqual('1.2.840.10008.5.1.4.1.1.4', a['RequestedTags']['SOPClassesInStudy'])


    def test_list_resources_requested_tags_series_computed_tags(self):

        if IsOrthancVersionAbove(_REMOTE, 1, 11, 0):
            instance = UploadInstance(_REMOTE, 'DummyCT.dcm') ['ID']
            patient = DoGet(_REMOTE, '/instances/%s/patient' % instance) ['ID']
            study = DoGet(_REMOTE, '/instances/%s/study' % instance) ['ID']

            # list studies and request patient and studies tags, including ModalitiesInStudy
            a = DoGet(_REMOTE, '/studies/%s/series?expand&simplify&requestedTags=PatientName;SeriesInstanceUID;NumberOfSeriesRelatedInstances' % study)

            self.assertEqual('1.2.840.113619.2.176.2025.1499492.7391.1171285944.394', a[0]['RequestedTags']['SeriesInstanceUID'])
            self.assertEqual('KNIX', a[0]['RequestedTags']['PatientName'])
            self.assertEqual('1', a[0]['RequestedTags']['NumberOfSeriesRelatedInstances'])

    def test_dicomweb_jpeg2k_implicit(self):
        # This is a file encoded using 1.2.840.10008.1.2.4.90 transfer
        # syntax, in which most DICOM tags have the "UN" value
        # representation. Support introduced in Orthanc 1.10.1.
        # https://groups.google.com/g/orthanc-users/c/86fobx3ZyoM/m/KBG17un6AQAJ
        a = UploadInstance(_REMOTE, '2022-03-08-RicSmi.dcm') ['ID']
        b = DoGet(_REMOTE, '/instances/%s/file' % a,
                  headers = { 'Accept' : 'application/dicom+json' })
        self.assertEqual(b['0020000D']['Value'][0], '1.2.276.0.7230010.3.1.2.2358427580.3460.1646695830.793')
        self.assertEqual(b['0020000E']['Value'][0], '1.2.276.0.7230010.3.1.3.2358427580.3460.1646695830.794')
    
    def test_create_png16RBGA(self):
        with open(GetDatabasePath('Png16RBGATest.png'), 'rb') as f:
            png = f.read()

        i = DoPost(_REMOTE, '/tools/create-dicom',
                   json.dumps({
                    'PatientName' : 'Jodogne',
                    'Modality' : 'CT',
                    'SOPClassUID' : '1.2.840.10008.5.1.4.1.1.1',
                    'PixelData' : 'data:image/png;base64,' + base64.b64encode(png)
                    }))

        self.assertEqual('Jodogne', DoGet(_REMOTE, '/instances/%s/content/PatientName' % i['ID']).strip())
        self.assertEqual('CT', DoGet(_REMOTE, '/instances/%s/content/Modality' % i['ID']).strip())

        png = GetImage(_REMOTE, '/instances/%s/preview' % i['ID'])
        self.assertEqual((32, 32), png.size)

        png = GetImage(_REMOTE, '/instances/%s/rendered' % i['ID'])
        self.assertEqual((32, 32), png.size)

        j = DoGet(_REMOTE, i['Path'])
        self.assertEqual('Instance', j['Type'])
        self.assertEqual(j['ID'], i['ID'])

    def test_storescu_custom_host_ip_port(self):
        if IsOrthancVersionAbove(_REMOTE, 1, 11, 3):
            DropOrthanc(_LOCAL)
            DropOrthanc(_REMOTE)        

            a = UploadInstance(_REMOTE, 'Knee/T1/IM-0001-0001.dcm')

            # upload to self -> orthanctest shall not receive any content
            DoPost(_REMOTE, '/modalities/self/store', {  
                'Resources' : [ a['ID']]
            })
            self.assertEqual(0, len(DoGet(_LOCAL, '/instances')))

            # upload to self by overriding it with config from orthanctest -> orthanctest shall receive the content
            c = DoGet(_REMOTE, '/modalities/orthanctest/configuration')
            DoPost(_REMOTE, '/modalities/self/store', {  
                'LocalAet' : 'YOP',
                'CalledAet' : c['AET'],
                'Port' : c['Port'],
                'Host' : c['Host'],
                'Resources' : [ a['ID']]
            })

            self.assertEqual(1, len(DoGet(_LOCAL, '/instances')))

            DropOrthanc(_REMOTE)        
            DropOrthanc(_LOCAL)        

    def test_rle_planar_configuration(self):
        if IsOrthancVersionAbove(_REMOTE, 1, 11, 2):
            # https://groups.google.com/g/orthanc-users/c/CSVWfRasSR0/m/y1XDRXVnAgAJ
            a = UploadInstance(_REMOTE, '2022-11-14-RLEPlanarConfiguration.dcm') ['ID']
            uri = '/instances/%s/preview' % a
            im = GetImage(_REMOTE, uri)
            self.assertEqual('RGB', im.mode)
            self.assertEqual(1475, im.size[0])
            self.assertEqual(1475, im.size[1])
            self.assertEqual('c684b0050dc2523041240bf2d26dc85e', ComputeMD5(DoGet(_REMOTE, uri)))

        if IsOrthancVersionAbove(_REMOTE, 1, 12, 1):
            a = UploadInstance(_REMOTE, '2023-04-21-RLEPlanarConfigurationYBR_FULL.dcm') ['ID']
            uri = '/instances/%s/preview' % a
            im = GetImage(_REMOTE, uri)
            self.assertEqual('RGB', im.mode)
            self.assertEqual(1260, im.size[0])
            self.assertEqual(910, im.size[1])
            self.assertEqual('07a3ea7ea08d54362f744cc5945e8743', ComputeMD5(DoGet(_REMOTE, uri)))


    def test_rest_api_write_to_file_system(self):
        if IsOrthancVersionAbove(_REMOTE, 1, 12, 0):
            a = UploadInstance(_REMOTE, '2022-11-14-RLEPlanarConfiguration.dcm') ['ID']
            self.assertRaises(Exception, lambda: DoPost(_REMOTE, '/instances/%s/export' % a, '/tmp/test.dcm'))

    def test_overwrite_generates_stable_study(self):

        # This test makes sure there are no regression wrt StableStudy when uploading instances in Orthanc
        # The current behaviour (tested from 1.5.7 to 1.12.0) is
        # If you upload 2 instances with a delay > StableAge, you get 2 StableStudy events and they are both listed in /changes
        # If you upload twice the same instance with a delay > StableAge, you get 2 StableStudy events but only the last one is listed in /changes, the first one is deleted
        # If you upload an instance and a modified version of this instance with a delay > StableAge, you get 2 StableStudy events but only the last one is listed in /changes, the first one is deleted


        def GetAllStableStudyChangesIds(studyId, timeout):
            # try to be as fast as possible -> stop as soon as we've found a StableStudy event that appeared after we started monitoring
            fromSeq = DoGet(_REMOTE, '/changes')["Last"]

            endTime = time.time() + timeout
            newStableStudyFound = False
            while not newStableStudyFound and time.time() < endTime:
                time.sleep(0.1)
                changes = DoGet(_REMOTE, '/changes')
                stableStudyChangesIds = []

                for change in changes["Changes"]:
                    if change["ChangeType"] == "StableStudy" and studyId == change["ID"]:
                        stableStudyChangesIds.append(change["Seq"])
                        if change["Seq"] > fromSeq:
                            newStableStudyFound = True

            return stableStudyChangesIds

        if True:
            DropOrthanc(_REMOTE)        
            upload1 = UploadInstance(_REMOTE, 'Knix/Loc/IM-0001-0002.dcm')
            # StableAge is set to 1, expect a StableStudy within 4 seconds
            changes1 = GetAllStableStudyChangesIds(upload1["ParentStudy"], 4)
            self.assertEqual(1, len(changes1))

            # upload the same instance again and check a new change has been generated with a new id, the first change has been deleted
            upload1b = UploadInstance(_REMOTE, 'Knix/Loc/IM-0001-0002.dcm')
            changes1b = GetAllStableStudyChangesIds(upload1b["ParentStudy"], 4)
            self.assertEqual(1, len(changes1b))
            self.assertNotEqual(changes1[0], changes1b[0])

        if True:
            DropOrthanc(_REMOTE)        
            upload1 = UploadInstance(_REMOTE, 'Knix/Loc/IM-0001-0002.dcm')
            # StableAge is set to 1, expect a StableStudy within 4 seconds
            changes1 = GetAllStableStudyChangesIds(upload1["ParentStudy"], 4)
            self.assertEqual(1, len(changes1))

            # reupload a modified instance in the same study and check a new change has been generated with a new id, the first change has been deleted
            modified = DoPost(_REMOTE, '/instances/%s/modify' % upload1["ID"],
                            json.dumps({
                                "Replace" : {
                                    "InstitutionName" : "hello",
                                    "SOPInstanceUID": "1.2.840.113619.2.176.2025.1499492.7040.1171286241.705"
                                    },
                                "Force": True
                                }),
                                'application/json')
            upload1b = DoPost(_REMOTE, '/instances', modified, 'application/dicom')
            changes1b = GetAllStableStudyChangesIds(upload1b["ParentStudy"], 4)
            self.assertEqual(upload1["ParentStudy"], upload1b["ParentStudy"])
            self.assertEqual(1, len(changes1b))
            self.assertNotEqual(changes1[0], changes1b[0])


        if True:
            DropOrthanc(_REMOTE)        
            upload1 = UploadInstance(_REMOTE, 'Knix/Loc/IM-0001-0002.dcm')
            # StableAge is set to 1, expect a StableStudy within 4 seconds
            changes1 = GetAllStableStudyChangesIds(upload1["ParentStudy"], 4)
            self.assertEqual(1, len(changes1))

            # upload a new instance in the same study and check a second StableStudy change has been generated with a new id
            upload2 = UploadInstance(_REMOTE, 'Knix/Loc/IM-0001-0003.dcm')
            changes2 = GetAllStableStudyChangesIds(upload2["ParentStudy"], 4)
            self.assertEqual(upload1["ParentStudy"], upload2["ParentStudy"])
            self.assertEqual(2, len(changes2))
            self.assertEqual(changes1[0], changes2[0])

    def test_labels(self):
        def CheckAllLabels(expected):
            actual = DoGet(_REMOTE, '/tools/labels')
            self.assertEqual(len(actual), len(expected))
            for i in expected:
                self.assertTrue(i in actual)
            for i in actual:
                self.assertTrue(i in expected)

        if (IsOrthancVersionAbove(_REMOTE, 1, 12, 0) and
            DoGet(_REMOTE, '/system') ['HasLabels']):
            u = UploadInstance(_REMOTE, 'DummyCT.dcm')['ID']
            patient = DoGet(_REMOTE, '/instances/%s/patient' % u) ['ID']
            study = DoGet(_REMOTE, '/instances/%s/study' % u) ['ID']
            series = DoGet(_REMOTE, '/instances/%s/series' % u) ['ID']

            for base in [ '/instances/%s' % u,
                          '/series/%s' % series,
                          '/studies/%s' % study,
                          '/patients/%s' % patient ]:

                # no tags by default
                self.assertEqual(0, len(DoGet(_REMOTE, base) ['Labels']))
                CheckAllLabels([])
                
                # 404 if requesting a tag that does apply for a resource
                self.assertRaises(Exception, lambda: DoGet(_REMOTE, '%s/labels/hello' % base))
                
                # delete a non existing tag does not generate an error
                self.assertEqual('', DoDelete(_REMOTE, '%s/labels/hello' % base))
                self.assertEqual(0, len(DoGet(_REMOTE, base) ['Labels']))
                
                # Not an alphanumeric label -> 400
                self.assertRaises(Exception, lambda: DoPut(_REMOTE, '%s/labels/@' % base))

                # add a tag
                self.assertEqual('', DoPut(_REMOTE, '%s/labels/hello' % base))
                self.assertEqual(1, len(DoGet(_REMOTE, base) ['Labels']))
                self.assertEqual('hello', DoGet(_REMOTE, base) ['Labels'][0])
                CheckAllLabels([ 'hello' ])

                # double tagging does not generate any error
                self.assertEqual('', DoPut(_REMOTE, '%s/labels/hello' % base))
                self.assertEqual('', DoGet(_REMOTE, '%s/labels/hello' % base))
                self.assertEqual(1, len(DoGet(_REMOTE, base) ['Labels']))
                self.assertEqual('hello', DoGet(_REMOTE, base) ['Labels'][0])

                # add a second tag
                self.assertEqual('', DoPut(_REMOTE, '%s/labels/world' % base))
                self.assertEqual('', DoGet(_REMOTE, '%s/labels/world' % base))
                self.assertEqual('', DoGet(_REMOTE, '%s/labels/hello' % base))
                self.assertEqual(2, len(DoGet(_REMOTE, base) ['Labels']))
                self.assertIn(DoGet(_REMOTE, base) ['Labels'][0], ['hello', 'world'])
                self.assertIn(DoGet(_REMOTE, base) ['Labels'][1], ['hello', 'world'])
                CheckAllLabels([ 'hello', 'world' ])

                # delete the first tag
                self.assertEqual('', DoDelete(_REMOTE, '%s/labels/hello' % base))
                self.assertEqual(1, len(DoGet(_REMOTE, base) ['Labels']))
                self.assertEqual('world', DoGet(_REMOTE, base) ['Labels'][0])
                self.assertRaises(Exception, lambda: DoGet(_REMOTE, '%s/labels/hello' % base))
                CheckAllLabels([ 'world' ])

                # delete the second tag
                self.assertEqual('', DoDelete(_REMOTE, '%s/labels/world' % base))
                self.assertEqual(0, len(DoGet(_REMOTE, base) ['Labels']))
                self.assertRaises(Exception, lambda: DoGet(_REMOTE, '%s/labels/world' % base))
                CheckAllLabels([ ])

                # test all valid chars
                VALID = r'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-'
                self.assertEqual('', DoPut(_REMOTE, '%s/labels/%s' % (base, VALID)))
                CheckAllLabels([ VALID ])
                DoDelete(_REMOTE, '%s/labels/%s' % (base, VALID))
                CheckAllLabels([ ])

        else:
            print("Your database backend doesn't support labels")

    def test_find_labels(self):
        def Execute(labels, constraint, query = { }, level='Instance'):
            return DoPost(_REMOTE, '/tools/find', { 'Level' : level,
                                                    'Query' : query,
                                                    'Labels' : labels,
                                                    'LabelsConstraint' : constraint, })
        
        if (IsOrthancVersionAbove(_REMOTE, 1, 12, 0) and
            DoGet(_REMOTE, '/system') ['HasLabels']):
            u = UploadInstance(_REMOTE, 'DummyCT.dcm')
            studyId = u["ParentStudy"]
            seriesId = u["ParentSeries"]
            patientId = u["ParentPatient"]
            u = u["ID"]
            self.assertEqual(1, len(Execute([ 'a' ], 'None')))

            # The instance has no label
            self.assertEqual(1, len(Execute([], 'All')))
            self.assertEqual(1, len(Execute([], 'Any')))
            self.assertEqual(1, len(Execute([], 'None')))
            self.assertEqual(0, len(Execute([ 'a' ], 'All')))
            self.assertEqual(0, len(Execute([ 'a' ], 'Any')))
            self.assertEqual(1, len(Execute([ 'a' ], 'None')))
            self.assertEqual(0, len(Execute([ 'b' ], 'All')))
            self.assertEqual(0, len(Execute([ 'b' ], 'Any')))
            self.assertEqual(1, len(Execute([ 'b' ], 'None')))
            self.assertEqual(0, len(Execute([ 'a', 'b' ], 'All')))
            self.assertEqual(0, len(Execute([ 'a', 'b' ], 'Any')))
            self.assertEqual(1, len(Execute([ 'a', 'b' ], 'None')))

            DoPut(_REMOTE, '/instances/%s/labels/a' % u)
            # The instance has label "a"
            self.assertEqual(1, len(Execute([], 'All')))
            self.assertEqual(1, len(Execute([], 'Any')))
            self.assertEqual(1, len(Execute([], 'None')))
            self.assertEqual(1, len(Execute([ 'a' ], 'All')))
            self.assertEqual(1, len(Execute([ 'a' ], 'Any')))
            self.assertEqual(0, len(Execute([ 'a' ], 'None')))
            self.assertEqual(0, len(Execute([ 'b' ], 'All')))
            self.assertEqual(0, len(Execute([ 'b' ], 'Any')))
            self.assertEqual(1, len(Execute([ 'b' ], 'None')))
            self.assertEqual(0, len(Execute([ 'a', 'b' ], 'All')))
            self.assertEqual(1, len(Execute([ 'a', 'b' ], 'Any')))
            self.assertEqual(0, len(Execute([ 'a', 'b' ], 'None')))

            self.assertEqual(0, len(Execute([ 'a' ], 'All', { 'PatientID' : 'nope' })))
            self.assertEqual(1, len(Execute([ 'a' ], 'All', { 'PatientID' : '' })))
            self.assertEqual(0, len(Execute([ 'a' ], 'All', { 'StudyInstanceUID' : 'nope' })))
            self.assertEqual(1, len(Execute([ 'a' ], 'All', { 'StudyInstanceUID' : '' })))
            self.assertEqual(0, len(Execute([ 'a' ], 'All', { 'SeriesInstanceUID' : 'nope' })))
            self.assertEqual(1, len(Execute([ 'a' ], 'All', { 'SeriesInstanceUID' : '' })))
            self.assertEqual(0, len(Execute([ 'a' ], 'All', { 'SOPInstanceUID' : 'nope' })))
            self.assertEqual(1, len(Execute([ 'a' ], 'All', { 'SOPInstanceUID' : '' })))
            
            self.assertEqual(1, len(Execute([ 'a' ], 'All', { 'PatientID' : 'ozp00SjY2xG' })))
        
            self.assertEqual(1, len(Execute([ 'a' ], 'All', { 'StudyInstanceUID' : '1.2.840.113619.2.176.2025.1499492.7391.1171285944.390' })))
            self.assertEqual(1, len(Execute([ 'a' ], 'All', { 'SeriesInstanceUID' : '1.2.840.113619.2.176.2025.1499492.7391.1171285944.394' })))
            self.assertEqual(1, len(Execute([ 'a' ], 'All', { 'SOPInstanceUID' : '1.2.840.113619.2.176.2025.1499492.7040.1171286242.109' })))
            self.assertEqual(1, len(Execute([ 'a' ], 'All', {
                'PatientID' : 'ozp00SjY2xG',
                'StudyInstanceUID' : '1.2.840.113619.2.176.2025.1499492.7391.1171285944.390',
                'SeriesInstanceUID' : '1.2.840.113619.2.176.2025.1499492.7391.1171285944.394',
                'SOPInstanceUID' : '1.2.840.113619.2.176.2025.1499492.7040.1171286242.109',
            })))

            self.assertEqual(0, len(Execute([ 'b' ], 'All', { 'PatientID' : 'nope' })))
            self.assertEqual(0, len(Execute([ 'b' ], 'All', { 'PatientID' : '' })))
            self.assertEqual(0, len(Execute([ 'b' ], 'All', { 'StudyInstanceUID' : 'nope' })))
            self.assertEqual(0, len(Execute([ 'b' ], 'All', { 'StudyInstanceUID' : '' })))
            self.assertEqual(0, len(Execute([ 'b' ], 'All', { 'SeriesInstanceUID' : 'nope' })))
            self.assertEqual(0, len(Execute([ 'b' ], 'All', { 'SeriesInstanceUID' : '' })))
            self.assertEqual(0, len(Execute([ 'b' ], 'All', { 'SOPInstanceUID' : 'nope' })))
            self.assertEqual(0, len(Execute([ 'b' ], 'All', { 'SOPInstanceUID' : '' })))
            
            self.assertEqual(0, len(Execute([ 'b' ], 'All', { 'PatientID' : 'ozp00SjY2xG' })))
            self.assertEqual(0, len(Execute([ 'b' ], 'All', { 'StudyInstanceUID' : '1.2.840.113619.2.176.2025.1499492.7391.1171285944.390' })))
            self.assertEqual(0, len(Execute([ 'b' ], 'All', { 'SeriesInstanceUID' : '1.2.840.113619.2.176.2025.1499492.7391.1171285944.394' })))
            self.assertEqual(0, len(Execute([ 'b' ], 'All', { 'SOPInstanceUID' : '1.2.840.113619.2.176.2025.1499492.7040.1171286242.109' })))
            self.assertEqual(0, len(Execute([ 'b' ], 'All', {
                'PatientID' : 'ozp00SjY2xG',
                'StudyInstanceUID' : '1.2.840.113619.2.176.2025.1499492.7391.1171285944.390',
                'SeriesInstanceUID' : '1.2.840.113619.2.176.2025.1499492.7391.1171285944.394',
                'SOPInstanceUID' : '1.2.840.113619.2.176.2025.1499492.7040.1171286242.109',
            })))

            DoPut(_REMOTE, '/instances/%s/labels/b' % u)
            # The instance has labels "a" and "b"
            self.assertEqual(1, len(Execute([], 'All')))
            self.assertEqual(1, len(Execute([], 'Any')))
            self.assertEqual(1, len(Execute([], 'None')))
            self.assertEqual(1, len(Execute([ 'a' ], 'All')))
            self.assertEqual(1, len(Execute([ 'a' ], 'Any')))
            self.assertEqual(0, len(Execute([ 'a' ], 'None')))
            self.assertEqual(1, len(Execute([ 'b' ], 'All')))
            self.assertEqual(1, len(Execute([ 'b' ], 'Any')))
            self.assertEqual(0, len(Execute([ 'b' ], 'None')))
            self.assertEqual(1, len(Execute([ 'a', 'b' ], 'All')))
            self.assertEqual(1, len(Execute([ 'a', 'b' ], 'Any')))
            self.assertEqual(0, len(Execute([ 'a', 'b' ], 'None')))
            self.assertEqual(0, len(Execute([ 'b', 'c' ], 'All')))
            self.assertEqual(1, len(Execute([ 'b', 'c' ], 'Any')))
            self.assertEqual(0, len(Execute([ 'b', 'c' ], 'None')))
            self.assertEqual(0, len(Execute([ 'c', 'd' ], 'All')))
            self.assertEqual(0, len(Execute([ 'c', 'd' ], 'Any')))
            self.assertEqual(1, len(Execute([ 'c', 'c' ], 'None')))
            
            DoDelete(_REMOTE, '/instances/%s/labels/a' % u)
            # The instance has label "b"
            self.assertEqual(1, len(Execute([], 'All')))
            self.assertEqual(1, len(Execute([], 'Any')))
            self.assertEqual(1, len(Execute([], 'None')))
            self.assertEqual(0, len(Execute([ 'a' ], 'All')))
            self.assertEqual(0, len(Execute([ 'a' ], 'Any')))
            self.assertEqual(1, len(Execute([ 'a' ], 'None')))
            self.assertEqual(1, len(Execute([ 'b' ], 'All')))
            self.assertEqual(1, len(Execute([ 'b' ], 'Any')))
            self.assertEqual(0, len(Execute([ 'b' ], 'None')))
            self.assertEqual(0, len(Execute([ 'a', 'b' ], 'All')))
            self.assertEqual(1, len(Execute([ 'a', 'b' ], 'Any')))
            self.assertEqual(0, len(Execute([ 'a', 'b' ], 'None')))

            DoDelete(_REMOTE, '/instances/%s/labels/b' % u)
            # The instance has no more label
            self.assertEqual(1, len(Execute([], 'All')))
            self.assertEqual(1, len(Execute([], 'Any')))
            self.assertEqual(1, len(Execute([], 'None')))
            self.assertEqual(0, len(Execute([ 'a' ], 'All')))
            self.assertEqual(0, len(Execute([ 'a' ], 'Any')))
            self.assertEqual(1, len(Execute([ 'a' ], 'None')))
            self.assertEqual(0, len(Execute([ 'b' ], 'All')))
            self.assertEqual(0, len(Execute([ 'b' ], 'Any')))
            self.assertEqual(1, len(Execute([ 'b' ], 'None')))
            self.assertEqual(0, len(Execute([ 'a', 'b' ], 'All')))
            self.assertEqual(0, len(Execute([ 'a', 'b' ], 'Any')))
            self.assertEqual(1, len(Execute([ 'a', 'b' ], 'None')))


            # tests at series levels (make sure to test only with series levels and with multiple levels)
            DoPut(_REMOTE, '/series/%s/labels/b' % seriesId)
            self.assertEqual(1, len(Execute([ 'a' ], 'None', {
                'SeriesInstanceUID' : '1.2.840.113619.2.176.2025.1499492.7391.1171285944.394'
            }, 'Series')))
            self.assertEqual(0, len(Execute([ 'a' ], 'Any', {
                'SeriesInstanceUID' : '1.2.840.113619.2.176.2025.1499492.7391.1171285944.394'
            }, 'Series')))
            self.assertEqual(1, len(Execute([ 'b' ], 'Any', {
                'SeriesInstanceUID' : '1.2.840.113619.2.176.2025.1499492.7391.1171285944.394'
            }, 'Series')))
            self.assertEqual(1, len(Execute([ 'b' ], 'All', {
                'SeriesInstanceUID' : '1.2.840.113619.2.176.2025.1499492.7391.1171285944.394'
            }, 'Series')))
            self.assertEqual(1, len(Execute([ 'a' ], 'None', {
               'PatientID' : 'ozp00SjY2xG',
            }, 'Series')))
            self.assertEqual(0, len(Execute([ 'a' ], 'Any', {
               'PatientID' : 'ozp00SjY2xG',
            }, 'Series')))
            self.assertEqual(1, len(Execute([ 'b' ], 'Any', {
               'PatientID' : 'ozp00SjY2xG',
            }, 'Series')))
            self.assertEqual(1, len(Execute([ 'b' ], 'All', {
               'PatientID' : 'ozp00SjY2xG',
            }, 'Series')))

            # tests at study levels (make sure to test only with study levels and with multiple levels)
            DoPut(_REMOTE, '/studies/%s/labels/b' % studyId)
            self.assertEqual(1, len(Execute([ 'a' ], 'None', {
                'StudyInstanceUID' : '1.2.840.113619.2.176.2025.1499492.7391.1171285944.390'
            }, 'Study')))
            self.assertEqual(0, len(Execute([ 'a' ], 'Any', {
                'StudyInstanceUID' : '1.2.840.113619.2.176.2025.1499492.7391.1171285944.390'
            }, 'Study')))
            self.assertEqual(1, len(Execute([ 'b' ], 'Any', {
                'StudyInstanceUID' : '1.2.840.113619.2.176.2025.1499492.7391.1171285944.390'
            }, 'Study')))
            self.assertEqual(1, len(Execute([ 'b' ], 'All', {
                'StudyInstanceUID' : '1.2.840.113619.2.176.2025.1499492.7391.1171285944.390'
            }, 'Study')))
            self.assertEqual(1, len(Execute([ 'a' ], 'None', {
               'PatientID' : 'ozp00SjY2xG',
            }, 'Study')))
            self.assertEqual(0, len(Execute([ 'a' ], 'Any', {
               'PatientID' : 'ozp00SjY2xG',
            }, 'Study')))
            self.assertEqual(1, len(Execute([ 'b' ], 'Any', {
               'PatientID' : 'ozp00SjY2xG',
            }, 'Study')))
            self.assertEqual(1, len(Execute([ 'b' ], 'All', {
               'PatientID' : 'ozp00SjY2xG',
            }, 'Study')))

            # tests at patient levels
            DoPut(_REMOTE, '/patients/%s/labels/b' % patientId)
            self.assertEqual(1, len(Execute([ 'a' ], 'None', {
               'PatientID' : 'ozp00SjY2xG',
            }, 'Patient')))
            self.assertEqual(0, len(Execute([ 'a' ], 'Any', {
               'PatientID' : 'ozp00SjY2xG',
            }, 'Patient')))
            self.assertEqual(1, len(Execute([ 'b' ], 'Any', {
               'PatientID' : 'ozp00SjY2xG',
            }, 'Patient')))
            self.assertEqual(1, len(Execute([ 'b' ], 'All', {
               'PatientID' : 'ozp00SjY2xG',
            }, 'Patient')))

        else:
            print("Your database backend doesn't support labels")


    def test_numeric_metadata(self):
        if IsOrthancVersionAbove(_REMOTE, 1, 12, 0):
            instance = UploadInstance(_REMOTE, 'DummyCT.dcm')['ID']
            study = DoGet(_REMOTE, '/instances/%s/study' % instance)['ID']

            m = DoGet(_REMOTE, '/studies/%s/metadata' % study)
            self.assertEqual(2, len(m))
            self.assertTrue('LastUpdate' in m)
            self.assertTrue('MainDicomTagsSignature' in m)
            lastUpdate = DoGet(_REMOTE, '/studies/%s/metadata/%s' % (study, 'LastUpdate'))
            signature = DoGet(_REMOTE, '/studies/%s/metadata/%s' % (study, 'MainDicomTagsSignature'))
            
            m = DoGet(_REMOTE, '/studies/%s/metadata?numeric' % study)
            self.assertEqual(2, len(m))
            self.assertTrue(7 in m)   # MetadataType_LastUpdate
            self.assertTrue(15 in m)  # MetadataType_MainDicomTagsSignature
            self.assertEqual(lastUpdate, DoGet(_REMOTE, '/studies/%s/metadata/%d' % (study, 7)))
            self.assertEqual(signature, DoGet(_REMOTE, '/studies/%s/metadata/%d' % (study, 15)))

            m = DoGet(_REMOTE, '/studies/%s/metadata?expand' % study)
            self.assertEqual(2, len(m))
            self.assertTrue('LastUpdate' in m)
            self.assertTrue('MainDicomTagsSignature' in m)
            self.assertEqual(lastUpdate, m['LastUpdate'])
            self.assertEqual(signature, m['MainDicomTagsSignature'])
            
            m = DoGet(_REMOTE, '/studies/%s/metadata?expand&numeric' % study)
            self.assertEqual(2, len(m))
            self.assertTrue('7' in m)
            self.assertTrue('15' in m)
            self.assertEqual(lastUpdate, m['7'])
            self.assertEqual(signature, m['15'])

    def test_expand(self):
        # test new expand options introduced in 1.12.2
        if IsOrthancVersionAbove(_REMOTE, 1, 12, 2):
            r = UploadInstance(_REMOTE, 'DummyCT.dcm')
            instanceId = r['ID']
            seriesId = r['ParentSeries']
            studyId = r['ParentStudy']

            self.assertEqual(DoGet(_REMOTE, '/instances?expand'), DoGet(_REMOTE, '/instances?expand=true'))
            self.assertEqual(DoGet(_REMOTE, '/instances'), DoGet(_REMOTE, '/instances?expand=false'))

            self.assertEqual(DoGet(_REMOTE, '/series?expand'), DoGet(_REMOTE, '/series?expand=true'))
            self.assertEqual(DoGet(_REMOTE, '/series'), DoGet(_REMOTE, '/series?expand=false'))

            self.assertEqual(DoGet(_REMOTE, '/studies?expand'), DoGet(_REMOTE, '/studies?expand=true'))
            self.assertEqual(DoGet(_REMOTE, '/studies'), DoGet(_REMOTE, '/studies?expand=false'))

            r = DoGet(_REMOTE, '/studies/%s/instances?expand=true' % studyId)
            self.assertEqual(1, len(r))
            self.assertIn('MainDicomTags', r[0])

            r = DoGet(_REMOTE, '/studies/%s/instances?expand=false' % studyId)
            self.assertEqual(1, len(r))
            self.assertIn('66a662ce-7430e543-bad44d47-0dc5a943-ec7a538d', r[0])

            self.assertEqual(DoGet(_REMOTE, '/studies/%s/instances?expand' % studyId), DoGet(_REMOTE, '/studies/%s/instances?expand=true' % studyId))
            self.assertEqual(DoGet(_REMOTE, '/studies/%s/instances' % studyId), DoGet(_REMOTE, '/studies/%s/instances?expand=true' % studyId))

            r = DoGet(_REMOTE, '/studies/%s/series?expand=true' % studyId)
            self.assertEqual(1, len(r))
            self.assertIn('MainDicomTags', r[0])

            r = DoGet(_REMOTE, '/studies/%s/series?expand=false' % studyId)
            self.assertEqual(1, len(r))
            self.assertIn('f2635388-f01d497a-15f7c06b-ad7dba06-c4c599fe', r[0])

            self.assertEqual(DoGet(_REMOTE, '/studies/%s/series?expand' % studyId), DoGet(_REMOTE, '/studies/%s/series?expand=true' % studyId))
            self.assertEqual(DoGet(_REMOTE, '/studies/%s/series' % studyId), DoGet(_REMOTE, '/studies/%s/series?expand=true' % studyId))



    def test_add_attachment_to_non_existing_resource(self):
        if IsOrthancVersionAbove(_REMOTE, 1, 12, 1): # till 1.12.0, it returned a 200
            (headers, body) = DoPutRaw(_REMOTE, '/instances/11111111-11111111-11111111-11111111-11111111/attachments/1025', 'hello')
            self.assertEqual('404', headers['status'])

    def test_delete_updates_parents_last_update_metadata(self):
        if IsOrthancVersionAbove(_REMOTE, 1, 12, 1):
            i = UploadInstance(_REMOTE, 'Beaufix/IM-0001-0001.dcm')
            j = UploadInstance(_REMOTE, 'Beaufix/IM-0001-0002.dcm')
            
            #instanceLastUpdate1 = DoGet(_REMOTE, '/instances/%s/metadata/LastUpdate' % i['ID'])
            seriesLastUpdate1 = DoGet(_REMOTE, '/series/%s/metadata/LastUpdate' % i['ParentSeries'])
            studyLastUpdate1 = DoGet(_REMOTE, '/studies/%s/metadata/LastUpdate' % i['ParentStudy'])
            patientLastUpdate1 = DoGet(_REMOTE, '/patients/%s/metadata/LastUpdate' % i['ParentPatient'])
            
            time.sleep(1.01)
            DoDelete(_REMOTE, '/instances/%s' % j['ID'])

            #instanceLastUpdate2 = DoGet(_REMOTE, '/instances/%s/metadata/LastUpdate' % i['ID'])
            seriesLastUpdate2 = DoGet(_REMOTE, '/series/%s/metadata/LastUpdate' % i['ParentSeries'])
            studyLastUpdate2 = DoGet(_REMOTE, '/studies/%s/metadata/LastUpdate' % i['ParentStudy'])
            patientLastUpdate2 = DoGet(_REMOTE, '/patients/%s/metadata/LastUpdate' % i['ParentPatient'])

            #self.assertEqual(instanceLastUpdate1, instanceLastUpdate2)
            self.assertNotEqual(seriesLastUpdate1, seriesLastUpdate2)
            self.assertNotEqual(studyLastUpdate1, studyLastUpdate2)
            self.assertNotEqual(patientLastUpdate1, patientLastUpdate2)

    def test_pixel_data_vr(self):
        def Check(path, hasPixelData, hasMetadata, expectedVR):
            i = UploadInstance(_REMOTE, path) ['ID']
            m = DoGet(_REMOTE, '/instances/%s/metadata?expand' % i)
            if hasMetadata:
                self.assertTrue('PixelDataVR' in m)
                self.assertEqual(expectedVR, m['PixelDataVR'])
            else:
                self.assertFalse('PixelDataVR' in m)

            if hasPixelData:
                self.assertTrue('PixelDataOffset' in m)
                j = DoGet(_REMOTE, '/instances/%s/file?expand' % i, headers = {
                    'Accept': 'application/dicom+json'
                    })
                self.assertEqual(expectedVR, j['7FE00010']['vr'])

        if IsOrthancVersionAbove(_REMOTE, 1, 12, 1):
            # File without pixel data
            Check('MarekLatin2.dcm', False, False, None)

            # Those files are badly formatted, and should be 'OB'
            # according to the DICOM standard => medata is present
            Check('Issue143.dcm', True, True, 'OW')              # Little Endian Explicit, 8bpp
            Check('KarstenHilbertRF.dcm', True, True, 'OW')      # Little Endian Explicit, 8bpp
            Check('PilatesArgenturGEUltrasoundOsiriX.dcm', True, True, 'OW')  # Little Endian Explicit, 8bpp

            # Those files are formatted as expected
            Check('ColorTestMalaterre.dcm', True, False, 'OW')   # Implicit Little Endian, 8bpp
            Check('Issue94.dcm', True, False, 'OW')              # Implicit Little Endian, 16bpp
            Check('TransferSyntaxes/1.2.840.10008.1.2.1.dcm', True, False, 'OB') # Explicit Little Endian, 8bpp
            Check('Phenix/IM-0001-0001.dcm', True, False, 'OW')  # Explicit Little Endian, 16bpp
            Check('TransferSyntaxes/1.2.840.10008.1.2.2.dcm', True, False, 'OB') # Explicit Big Endian, 8bpp
            if IsOrthancVersionAbove(_REMOTE, 1, 12, 6):
                # From Orthanc 1.12.6, the PixelData is not present.  Anyway, it was not usable in 1.12.5
                Check('TransferSyntaxes/1.2.840.10008.1.2.4.50.dcm', False, False, 'OB')  # JPEG
                Check('Knee/T1/IM-0001-0001.dcm', False, False, 'OB') # JPEG2k
            else:
                # up to Orthanc 1.12.5, we get this (that is basically useless):
                # "7FE00010" : {
                #   "InlineBinary" : "",
                #   "vr" : "OB"
                # }
                Check('TransferSyntaxes/1.2.840.10008.1.2.4.50.dcm', True, False, 'OB')  # JPEG
                Check('Knee/T1/IM-0001-0001.dcm', True, False, 'OB') # JPEG2k

    def test_encapsulate_stl(self):
        if IsOrthancVersionAbove(_REMOTE, 1, 12, 1):
            stl = b'Hello, world'

            i = DoPost(_REMOTE, '/tools/create-dicom', json.dumps({
                'Content' : 'data:model/stl;base64,%s' % base64.b64encode(stl).decode(),
                'Force' : True,
                'Tags' : {
                    'PatientName' : 'Jodogne'
                }
            })) ['ID']

            tags = DoGet(_REMOTE, '/instances/%s/tags?simplify' % i)
            self.assertEqual('Jodogne', tags['PatientName'])
            self.assertEqual('M3D', tags['Modality'])
            self.assertEqual('model/stl', tags['MIMETypeOfEncapsulatedDocument'])
            self.assertEqual('1.2.840.10008.5.1.4.1.1.104.3', tags['SOPClassUID'])

            i = DoPost(_REMOTE, '/tools/create-dicom', json.dumps({
                'Content' : 'data:model/mtl;base64,%s' % base64.b64encode(stl).decode(),
                'Tags' : {}
            })) ['ID']

            tags = DoGet(_REMOTE, '/instances/%s/tags?simplify' % i)
            self.assertFalse('PatientName' in tags)
            self.assertEqual('M3D', tags['Modality'])
            self.assertEqual('model/mtl', tags['MIMETypeOfEncapsulatedDocument'])
            self.assertEqual('1.2.840.10008.5.1.4.1.1.104.5', tags['SOPClassUID'])

            i = DoPost(_REMOTE, '/tools/create-dicom', json.dumps({
                'Content' : 'data:model/obj;base64,%s' % base64.b64encode(stl).decode(),
                'Tags' : {}
            })) ['ID']

            tags = DoGet(_REMOTE, '/instances/%s/tags?simplify' % i)
            self.assertFalse('PatientName' in tags)
            self.assertEqual('M3D', tags['Modality'])
            self.assertEqual('model/obj', tags['MIMETypeOfEncapsulatedDocument'])
            self.assertEqual('1.2.840.10008.5.1.4.1.1.104.4', tags['SOPClassUID'])


    def test_error_codes_content_type(self):

        # from 1.12.2, check that a ContentType header is included in errors with an error description (ex: 404)
        (headers, body) = DoGetRaw(_REMOTE, '/rnm94%3Cscript%3Ealert(1)%3C/script%3Ejdtkc/explorer.html')
        self.assertEqual('404', headers['status'])

        if IsOrthancVersionAbove(_REMOTE, 1, 12, 2):
            self.assertEqual('text/plain', headers['content-type'])

        (headers, body) = DoPutRaw(_REMOTE, '/system', 'hello')
        self.assertEqual('405', headers['status'])
        # when there is no body, there is no content-type
        self.assertNotIn('content-type', headers)

        # responses with bodies contain x-content-type-options
        if IsOrthancVersionAbove(_REMOTE, 1, 12, 2):
            (headers, body) = DoGetRaw(_REMOTE, '/system')
            self.assertIn('nosniff', headers['x-content-type-options'])

    def test_modify_with_labels(self):

        if DoGet(_REMOTE, '/system')['ApiVersion'] < 23 or not DoGet(_REMOTE, '/system')['HasLabels']:
            return

        def UploadAndLabel(testId):
            DropOrthanc(_REMOTE)
            
            u = UploadInstance(_REMOTE, 'Brainix/Epi/IM-0001-0001.dcm')
            studyId = u["ParentStudy"]
            seriesId = u["ParentSeries"]
            patientId = u["ParentPatient"]
            instanceId = u["ID"]

            if testId == 2: # multi instance study
                UploadInstance(_REMOTE, 'Brainix/Epi/IM-0001-0002.dcm')
                UploadInstance(_REMOTE, 'Brainix/Flair/IM-0001-0001.dcm')
                UploadInstance(_REMOTE, 'Brainix/Flair/IM-0001-0002.dcm')

            # add a label to the study before modification
            DoPut(_REMOTE, '/patients/%s/labels/label-patient' % patientId)
            DoPut(_REMOTE, '/studies/%s/labels/label-study' % studyId)
            DoPut(_REMOTE, '/series/%s/labels/label-series' % seriesId)
            DoPut(_REMOTE, '/instances/%s/labels/label-instance' % instanceId)

            originalPatient = DoGet(_REMOTE, '/patients/%s' % patientId)
            self.assertEqual(1, len(originalPatient["Labels"]))
            self.assertIn('label-patient', originalPatient["Labels"])

            originalStudy = DoGet(_REMOTE, '/studies/%s' % studyId)
            self.assertEqual(1, len(originalStudy["Labels"]))
            self.assertIn('label-study', originalStudy["Labels"])

            originalSeries = DoGet(_REMOTE, '/series/%s' % seriesId)
            self.assertEqual(1, len(originalSeries["Labels"]))
            self.assertIn('label-series', originalSeries["Labels"])

            originalInstance = DoGet(_REMOTE, '/instances/%s' % instanceId)
            self.assertEqual(1, len(originalInstance["Labels"]))
            self.assertIn('label-instance', originalInstance["Labels"])

            return originalPatient, originalStudy, originalSeries, originalInstance


        for testId in range(1, 2): #test with a single instance study and a multi instance study

            originalPatient, originalStudy, originalSeries, originalInstance = UploadAndLabel(testId)

            # modify a study in place with no label field in the payload (default behavior before 1.12.3)
            DoPost(_REMOTE, '/studies/%s/modify' % originalStudy['ID'], {
                    'Keep' : ['StudyInstanceUID', 'SeriesInstanceUID', 'SOPInstanceUID'],
                    'Replace' : {
                        'PatientName': 'modified'
                    },
                    'Force': True
                })

            # with no options, all resources lose their labels during the modification
            modifiedStudy = DoGet(_REMOTE, '/studies/%s' % originalStudy['ID'])
            self.assertEqual(0, len(modifiedStudy["Labels"]))
            self.assertEqual('modified', modifiedStudy["PatientMainDicomTags"]["PatientName"])

        if IsOrthancVersionAbove(_REMOTE, 1, 12, 3) and DoGet(_REMOTE, '/system')['ApiVersion'] >= 23 and DoGet(_REMOTE, '/system')['HasLabels']:
            for testId in range(1, 2): #test with a single instance study and a multi instance study

                originalPatient, originalStudy, originalSeries, originalInstance = UploadAndLabel(testId)

                # modify a study in place with no label field in the payload (default behavior before 1.12.3)
                DoPost(_REMOTE, '/studies/%s/modify' % originalStudy['ID'], {
                        'Keep' : ['StudyInstanceUID', 'SeriesInstanceUID', 'SOPInstanceUID'],
                        'Replace' : {
                            'PatientName': 'modified2'
                        },
                        'Force': True,
                        'KeepLabels': True
                    })

                # now, each resource level shall have kept its labels

                modifiedInstance = DoGet(_REMOTE, '/instances/%s' % originalInstance['ID'])
                self.assertEqual(1, len(modifiedInstance["Labels"]))
                self.assertIn('label-instance', modifiedInstance["Labels"])

                modifiedSeries = DoGet(_REMOTE, '/series/%s' % originalSeries['ID'])
                self.assertEqual(1, len(modifiedSeries["Labels"]))
                self.assertIn('label-series', modifiedSeries["Labels"])

                modifiedStudy = DoGet(_REMOTE, '/studies/%s' % originalStudy['ID'])
                self.assertEqual(1, len(modifiedStudy["Labels"]))
                self.assertIn('label-study', modifiedStudy["Labels"])
                self.assertEqual('modified2', modifiedStudy["PatientMainDicomTags"]["PatientName"])

                modifiedPatient = DoGet(_REMOTE, '/patients/%s' % originalPatient['ID'])
                self.assertEqual(1, len(modifiedPatient["Labels"]))
                self.assertIn('label-patient', modifiedPatient["Labels"])

    def test_findscu_group_length(self):
        UploadInstance(_REMOTE, 'Comunix/Ct/IM-0001-0001.dcm')
        UploadInstance(_REMOTE, 'Comunix/Pet/IM-0001-0001.dcm')
        UploadInstance(_REMOTE, 'Comunix/Pet/IM-0001-0002.dcm')

        i = CallFindScu([ '-k', '0008,0052=PATIENT', '-k', '0008,0000=22' ])  # GE like C-Find that includes group-length
        # print(i)
        s = re.findall('\(0008,0000\).*?\[(.*?)\]', i)
        self.assertEqual(0, len(s))


    def test_tags_after_pixel_data(self):
        if IsOrthancVersionAbove(_REMOTE, 1, 12, 4):
            # https://discourse.orthanc-server.org/t/private-tags-with-group-7fe0-are-not-provided-via-rest-api/4744
            u = UploadInstance(_REMOTE, '2024-05-30-GuillemVela.dcm') ['ID']

            a = DoGet(_REMOTE, '/instances/%s/tags' % u)
            self.assertFalse('8e05,1000' in a)

            a = DoGet(_REMOTE, '/instances/%s/tags?whole' % u)
            self.assertTrue('8e05,1000' in a)
            self.assertEqual('XEOS_Attributes', a['8e05,0010']['Value'])
            self.assertEqual('acquisition', a['8e05,1000']['Value'])
            self.assertEqual('specimen', a['8e05,1001']['Value'])

            a = DoGet(_REMOTE, '/instances/%s/tags?full' % u)
            self.assertFalse('8e05,1000' in a)

            a = DoGet(_REMOTE, '/instances/%s/tags?full&whole' % u)
            self.assertTrue('8e05,1000' in a)
            self.assertEqual('XEOS_Attributes', a['8e05,0010']['Value'])
            self.assertEqual('acquisition', a['8e05,1000']['Value'])
            self.assertEqual('specimen', a['8e05,1001']['Value'])

            a = DoGet(_REMOTE, '/instances/%s/tags?short' % u)
            self.assertFalse('8e05,1000' in a)

            a = DoGet(_REMOTE, '/instances/%s/tags?short&whole' % u)
            self.assertTrue('8e05,1000' in a)
            self.assertEqual('XEOS_Attributes', a['8e05,0010'])
            self.assertEqual('acquisition', a['8e05,1000'])
            self.assertEqual('specimen', a['8e05,1001'])

            a = DoGet(_REMOTE, '/instances/%s/tags?simplify' % u)
            self.assertFalse('Unknown Tag & Data' in a)

            a = DoGet(_REMOTE, '/instances/%s/tags?simplify&whole' % u)
            self.assertTrue('Unknown Tag & Data' in a)

            a = DoGet(_REMOTE, '/instances/%s/simplified-tags' % u)
            self.assertFalse('Unknown Tag & Data' in a)

            a = DoGet(_REMOTE, '/instances/%s/simplified-tags?whole' % u)
            self.assertTrue('Unknown Tag & Data' in a)


    def test_requested_tags(self):
        u = UploadInstance(_REMOTE, 'DummyCT.dcm')

        def CheckPatientContent(patient):
            self.assertEqual(u['ParentPatient'], patient['ID'])
            self.assertEqual('Patient', patient['Type'])
            self.assertFalse(patient['IsStable'])
            self.assertEqual(0, len(patient['Labels']))
            self.assertTrue('LastUpdate' in patient)
            self.assertEqual(2, len(patient['MainDicomTags']))
            self.assertEqual('ozp00SjY2xG', patient['MainDicomTags']['PatientID'])
            self.assertEqual('KNIX', patient['MainDicomTags']['PatientName'])
            self.assertEqual(1, len(patient['Studies']))
            self.assertEqual(u['ParentStudy'], patient['Studies'][0])

        def CheckStudyContent(study):
            self.assertEqual(u['ParentStudy'], study['ID'])
            self.assertEqual(u['ParentPatient'], study['ParentPatient'])
            self.assertEqual('Study', study['Type'])
            self.assertFalse(study['IsStable'])
            self.assertEqual(0, len(study['Labels']))
            self.assertTrue('LastUpdate' in study)
            self.assertEqual(7, len(study['MainDicomTags']))
            self.assertEqual('0ECJ52puWpVIjTuhnBA0um', study['MainDicomTags']['InstitutionName'])
            self.assertEqual('1', study['MainDicomTags']['ReferringPhysicianName'])
            self.assertEqual('20070101', study['MainDicomTags']['StudyDate'])
            self.assertEqual('Knee (R)', study['MainDicomTags']['StudyDescription'])
            self.assertEqual('1', study['MainDicomTags']['StudyID'])
            self.assertEqual('1.2.840.113619.2.176.2025.1499492.7391.1171285944.390', study['MainDicomTags']['StudyInstanceUID'])
            self.assertEqual('120000.000000', study['MainDicomTags']['StudyTime'])
            self.assertEqual(2, len(study['PatientMainDicomTags']))
            self.assertEqual('ozp00SjY2xG', study['PatientMainDicomTags']['PatientID'])
            self.assertEqual('KNIX', study['PatientMainDicomTags']['PatientName'])
            self.assertEqual(1, len(study['Series']))
            self.assertEqual(u['ParentSeries'], study['Series'][0])

        def CheckSeriesContent(series):
            self.assertEqual(None, series['ExpectedNumberOfInstances'])
            self.assertEqual('Unknown', series['Status'])
            self.assertEqual(u['ParentSeries'], series['ID'])
            self.assertEqual(u['ParentStudy'], series['ParentStudy'])
            self.assertEqual('Series', series['Type'])
            self.assertFalse(series['IsStable'])
            self.assertEqual(0, len(series['Labels']))
            self.assertTrue('LastUpdate' in series)
            self.assertEqual(13, len(series['MainDicomTags']))
            self.assertEqual('0', series['MainDicomTags']['CardiacNumberOfImages'])
            self.assertEqual('0.999841\\0.000366209\\0.0178227\\-0.000427244\\0.999995\\0.00326545', series['MainDicomTags']['ImageOrientationPatient'])
            self.assertEqual('24', series['MainDicomTags']['ImagesInAcquisition'])
            self.assertEqual('GE MEDICAL SYSTEMS', series['MainDicomTags']['Manufacturer'])
            self.assertEqual('MR', series['MainDicomTags']['Modality'])
            self.assertEqual('ca', series['MainDicomTags']['OperatorsName'])
            self.assertEqual('324-58-2995/6', series['MainDicomTags']['ProtocolName'])
            self.assertEqual('20070101', series['MainDicomTags']['SeriesDate'])
            self.assertEqual('AX.  FSE PD', series['MainDicomTags']['SeriesDescription'])
            self.assertEqual('1.2.840.113619.2.176.2025.1499492.7391.1171285944.394', series['MainDicomTags']['SeriesInstanceUID'])
            self.assertEqual('5', series['MainDicomTags']['SeriesNumber'])
            self.assertEqual('120000.000000', series['MainDicomTags']['SeriesTime'])
            self.assertEqual('TWINOW', series['MainDicomTags']['StationName'])
            self.assertEqual(1, len(series['Instances']))
            self.assertEqual(u['ID'], series['Instances'][0])

        def CheckInstanceContent(instance):
            self.assertEqual(2472, instance['FileSize'])
            self.assertTrue('FileUuid' in instance)
            self.assertEqual(u['ID'], instance['ID'])
            self.assertEqual(u['ParentSeries'], instance['ParentSeries'])
            self.assertEqual('Instance', instance['Type'])
            self.assertEqual(1, instance['IndexInSeries'])
            self.assertEqual(0, len(instance['Labels']))
            # if IsOrthancVersionAbove(_REMOTE, 1, 12, 5):
            #     self.assertEqual(8, len(instance['MainDicomTags']))  # since we have added SOPClassUID
            # else:
            self.assertEqual(7, len(instance['MainDicomTags']))
            self.assertEqual('1', instance['MainDicomTags']['AcquisitionNumber'])
            self.assertEqual('0.999841\\0.000366209\\0.0178227\\-0.000427244\\0.999995\\0.00326545', instance['MainDicomTags']['ImageOrientationPatient'])
            self.assertEqual('-149.033\\-118.499\\-61.0464', instance['MainDicomTags']['ImagePositionPatient'])
            self.assertEqual('20070101', instance['MainDicomTags']['InstanceCreationDate'])
            self.assertEqual('120000.000000', instance['MainDicomTags']['InstanceCreationTime'])
            self.assertEqual('1', instance['MainDicomTags']['InstanceNumber'])
            self.assertEqual('1.2.840.113619.2.176.2025.1499492.7040.1171286242.109', instance['MainDicomTags']['SOPInstanceUID'])

        def CheckRequestedTags(resource):
            self.assertEqual(6, len(resource['RequestedTags']))
            self.assertEqual('ozp00SjY2xG', resource['RequestedTags']['PatientID'])
            self.assertEqual('Knee (R)', resource['RequestedTags']['StudyDescription'])
            self.assertEqual('AX.  FSE PD', resource['RequestedTags']['SeriesDescription'])
            self.assertEqual('1.2.840.10008.5.1.4.1.1.4', resource['RequestedTags']['SOPClassUID'])
            self.assertEqual('2800', resource['RequestedTags']['RepetitionTime'])
            self.assertEqual(3, len(resource['RequestedTags']['DerivationCodeSequence'][0]))
            self.assertEqual('121327', resource['RequestedTags']['DerivationCodeSequence'][0]['CodeValue'])
        
        requestedTags = 'PatientID;StudyDescription;SeriesDescription;SOPClassUID;RepetitionTime;DerivationCodeSequence'

        a = DoGet(_REMOTE, '/patients?expand')
        self.assertEqual(1, len(a))
        if IsOrthancVersionAbove(_REMOTE, 1, 12, 8):
            self.assertEqual(8, len(a[0]))
            self.assertTrue('IsProtected' in a[0])
        else:
            self.assertEqual(7, len(a[0]))
        CheckPatientContent(a[0])
        self.assertFalse('RequestedTags' in a[0])

        a = DoGet(_REMOTE, '/patients?expand&requestedTags=%s' % requestedTags)
        self.assertEqual(1, len(a))
        if IsOrthancVersionAbove(_REMOTE, 1, 12, 8):
            self.assertEqual(9, len(a[0]))
            self.assertTrue('IsProtected' in a[0])
        else:
            self.assertEqual(8, len(a[0]))
        CheckPatientContent(a[0])
        CheckRequestedTags(a[0])

        a = DoGet(_REMOTE, '/studies?expand')
        self.assertEqual(1, len(a))
        self.assertEqual(9, len(a[0]))
        CheckStudyContent(a[0])
        self.assertFalse('RequestedTags' in a[0])

        a = DoGet(_REMOTE, '/studies?expand&requestedTags=%s' % requestedTags)
        self.assertEqual(1, len(a))
        self.assertEqual(10, len(a[0]))
        CheckStudyContent(a[0])
        CheckRequestedTags(a[0])

        a = DoGet(_REMOTE, '/series?expand')
        self.assertEqual(1, len(a))
        self.assertEqual(10, len(a[0]))
        CheckSeriesContent(a[0])
        self.assertFalse('RequestedTags' in a[0])

        a = DoGet(_REMOTE, '/series?expand&requestedTags=%s' % requestedTags)
        self.assertEqual(1, len(a))
        self.assertEqual(11, len(a[0]))
        CheckSeriesContent(a[0])
        CheckRequestedTags(a[0])

        a = DoGet(_REMOTE, '/instances?expand')
        self.assertEqual(1, len(a))
        self.assertEqual(8, len(a[0]))
        CheckInstanceContent(a[0])
        self.assertFalse('RequestedTags' in a[0])

        a = DoGet(_REMOTE, '/instances?expand&requestedTags=%s' % requestedTags)
        self.assertEqual(1, len(a))
        self.assertEqual(9, len(a[0]))
        CheckInstanceContent(a[0])
        CheckRequestedTags(a[0])

        a = DoGet(_REMOTE, '/patients/%s' % u['ParentPatient'])
        if IsOrthancVersionAbove(_REMOTE, 1, 12, 8):
            self.assertEqual(8, len(a))
            self.assertTrue('IsProtected' in a)
        else:
            self.assertEqual(7, len(a))
        CheckPatientContent(a)
        self.assertFalse('RequestedTags' in a)

        a = DoGet(_REMOTE, '/patients/%s?requestedTags=%s' % (u['ParentPatient'], requestedTags))
        if IsOrthancVersionAbove(_REMOTE, 1, 12, 8):
            self.assertEqual(9, len(a))
            self.assertTrue('IsProtected' in a)
        else:
            self.assertEqual(8, len(a))
        CheckPatientContent(a)
        CheckRequestedTags(a)

        a = DoGet(_REMOTE, '/studies/%s' % u['ParentStudy'])
        self.assertEqual(9, len(a))
        CheckStudyContent(a)
        self.assertFalse('RequestedTags' in a)

        a = DoGet(_REMOTE, '/studies/%s?requestedTags=%s' % (u['ParentStudy'], requestedTags))
        self.assertEqual(10, len(a))
        CheckStudyContent(a)
        CheckRequestedTags(a)

        a = DoGet(_REMOTE, '/series/%s' % u['ParentSeries'])
        self.assertEqual(10, len(a))
        CheckSeriesContent(a)
        self.assertFalse('RequestedTags' in a)

        a = DoGet(_REMOTE, '/series/%s?requestedTags=%s' % (u['ParentSeries'], requestedTags))
        self.assertEqual(11, len(a))
        CheckSeriesContent(a)
        CheckRequestedTags(a)

        a = DoGet(_REMOTE, '/instances/%s' % u['ID'])
        self.assertEqual(8, len(a))
        CheckInstanceContent(a)
        self.assertFalse('RequestedTags' in a)

        a = DoGet(_REMOTE, '/instances/%s?requestedTags=%s' % (u['ID'], requestedTags))
        self.assertEqual(9, len(a))
        CheckInstanceContent(a)
        CheckRequestedTags(a)

        # this is equivalent to calling /dicom-web/series?PatientID=*
        # when there are no StudyInstanceUID specified, the DICOM-Web standard says we should retrieve all Series and Study tags
        # which includes e.g. NumberOfStudyRelatedInstances (0020,1208) that is a computed tag at study level
        c = GetStorageAccessesCount(_REMOTE)
        a = DoPost(_REMOTE, '/tools/find', {
            "Query": { "PatientID": "*"},
            "Level": "Series",
            "Expand": True,
            "RequestedTags": [
                "0008,0020",
                "0008,0030",
                "0008,0050",
                "0008,0056",
                "0008,0060",
                "0008,0061",
                "0008,0090",
                "0008,0201",
                "0008,103e",
                "0010,0010",
                "0010,0020",
                "0010,0030",
                "0010,0040",
                "0020,000d",
                "0020,000e",
                "0020,0010",
                "0020,0011",
                "0020,1206",
                "0020,1208",
                "0020,1209",
                "0040,0244",
                "0040,0245",
                "0040,0275"
            ]
        })        
        # Up to now, no versions of Orthanc ever returned this value but we keep the test for later (let's wait for someone to comlain !)
        self.assertNotIn("NumberOfStudyRelatedInstances", a[0]["RequestedTags"])
        if HasExtendedFind(_REMOTE):
            self.assertEqual(c, GetStorageAccessesCount(_REMOTE))  # the disk shall not have been accessed

        c = GetStorageAccessesCount(_REMOTE)
        a = DoPost(_REMOTE, '/tools/find', {
            "Query": { "PatientID": "*"},
            "Level": "Study",
            "Expand": True,
            "RequestedTags": [
                "SOPClassesInStudy",
                "NumberOfStudyRelatedInstances"
            ]
        })        
        # Up to now, no versions of Orthanc ever returned this value but we keep the test for later (let's wait for someone to comlain !)
        self.assertIn("SOPClassesInStudy", a[0]["RequestedTags"])
        self.assertIn("NumberOfStudyRelatedInstances", a[0]["RequestedTags"])
        if HasExtendedFind(_REMOTE):
            self.assertEqual(c, GetStorageAccessesCount(_REMOTE))  # the disk shall not have been accessed



    def test_computed_tags(self):
        # curl  'http://alice:orthanctest@localhost:8042/patients/0946fcb6-cf12ab43-bad958c1-bf057ad5-0fc6f54c?requested-tags=0020,1200;0020,1202;0020,1204'
        # curl   'http://alice:orthanctest@localhost:8042/studies/6c65289b-db2fcb71-7eaf73f4-8e12470c-a4d6d7cf?requested-tags=0008,0061;0008,0062;0020,1206;0020,1208'
        # curl    'http://alice:orthanctest@localhost:8042/series/318603c5-03e8cffc-a82b6ee1-3ccd3c1e-18d7e3bb?requested-tags=0020,1209'
        # curl 'http://alice:orthanctest@localhost:8042/instances/ee693caa-9786a685-4f0f9fb0-4411cc8b-988f5574?requested-tags=0008,0056'

        UploadInstance(_REMOTE, 'Comunix/Ct/IM-0001-0001.dcm')
        UploadInstance(_REMOTE, 'Comunix/Ct/IM-0001-0002.dcm')
        UploadInstance(_REMOTE, 'Comunix/Pet/IM-0001-0001.dcm')
        UploadInstance(_REMOTE, 'Comunix/Pet/IM-0001-0002.dcm')

        instance = 'ee693caa-9786a685-4f0f9fb0-4411cc8b-988f5574'
        series = '318603c5-03e8cffc-a82b6ee1-3ccd3c1e-18d7e3bb'
        study = '6c65289b-db2fcb71-7eaf73f4-8e12470c-a4d6d7cf'
        patient = '0946fcb6-cf12ab43-bad958c1-bf057ad5-0fc6f54c'

        if IsOrthancVersionAbove(_REMOTE, 1, 12, 4):     # the old syntax is still required for the upgrade/downgrade PG tests
            a = DoGet(_REMOTE, '/instances/%s?requested-tags=0008,0056' % instance)
        else:
            a = DoGet(_REMOTE, '/instances/%s?requestedTags=0008,0056' % instance)
        
        self.assertEqual(1, len(a['RequestedTags']))
        self.assertEqual('ONLINE', a['RequestedTags']['InstanceAvailability'])

        if IsOrthancVersionAbove(_REMOTE, 1, 12, 4):
            a = DoGet(_REMOTE, '/series/%s?requested-tags=0020,1209' % series)
        else:
            a = DoGet(_REMOTE, '/series/%s?requestedTags=0020,1209' % series)
        self.assertEqual(1, len(a['RequestedTags']))
        self.assertEqual(2, int(a['RequestedTags']['NumberOfSeriesRelatedInstances']))

        if IsOrthancVersionAbove(_REMOTE, 1, 12, 4):
            a = DoGet(_REMOTE, '/studies/%s?requested-tags=0008,0061;0008,0062;0020,1206;0020,1208' % study)
        else:
            a = DoGet(_REMOTE, '/studies/%s?requestedTags=0008,0061;0008,0062;0020,1206;0020,1208' % study)

        self.assertEqual(4, len(a['RequestedTags']))
        self.assertEqual('CT\\PT', a['RequestedTags']['ModalitiesInStudy'])
        self.assertEqual('1.2.840.10008.5.1.4.1.1.128\\1.2.840.10008.5.1.4.1.1.2', a['RequestedTags']['SOPClassesInStudy'])
        self.assertEqual(2, int(a['RequestedTags']['NumberOfStudyRelatedSeries']))
        self.assertEqual(4, int(a['RequestedTags']['NumberOfStudyRelatedInstances']))

        if IsOrthancVersionAbove(_REMOTE, 1, 12, 4):
            a = DoGet(_REMOTE, '/patients/%s?requested-tags=0020,1200;0020,1202;0020,1204' % patient)
        else:
            a = DoGet(_REMOTE, '/studies/%s?requestedTags=0020,1200;0020,1202;0020,1204' % study)
        self.assertEqual(3, len(a['RequestedTags']))
        self.assertEqual(1, int(a['RequestedTags']['NumberOfPatientRelatedStudies']))
        self.assertEqual(2, int(a['RequestedTags']['NumberOfPatientRelatedSeries']))
        self.assertEqual(4, int(a['RequestedTags']['NumberOfPatientRelatedInstances']))

    def test_computed_tags_and_patient_comments(self):
        UploadInstance(_REMOTE, 'WithEmptyPatientComments.dcm')

        # without requesting PatientComments, we get the computed tags
        i = CallFindScu([ '-k', 'PatientID=WITH_COMMENTS',  '-k', 'QueryRetrieveLevel=Study', '-k', 'ModalitiesInStudy', '-k', 'NumberOfStudyRelatedSeries', '-k', 'NumberOfStudyRelatedInstances' ])
        modalitiesInStudy = re.findall('\(0008,0061\).*?\[(.*?)\]', i)
        self.assertEqual(1, len(modalitiesInStudy))
        self.assertEqual('CT', modalitiesInStudy[0])

        if IsOrthancVersionAbove(_REMOTE, 1, 12, 5):
            # when requesting PatientComments, with 1.12.4, we did not get the computed tags
            i = CallFindScu([ '-k', 'PatientID=WITH_COMMENTS',  '-k', 'QueryRetrieveLevel=Study', '-k', 'ModalitiesInStudy', '-k', 'NumberOfStudyRelatedSeries', '-k', 'NumberOfStudyRelatedInstances', '-k', 'PatientComments' ])
            modalitiesInStudy = re.findall('\(0008,0061\).*?\[(.*?)\]', i)
            self.assertEqual(1, len(modalitiesInStudy))
            self.assertEqual('CT', modalitiesInStudy[0])
            numberOfStudyRelatedSeries = re.findall('\(0020,1206\).*?\[(.*?)\]', i)
            self.assertEqual(1, len(numberOfStudyRelatedSeries))
            self.assertEqual(1, int(numberOfStudyRelatedSeries[0]))
            numberOfStudyRelatedInstances = re.findall('\(0020,1208\).*?\[(.*?)\]', i)
            self.assertEqual(1, len(numberOfStudyRelatedInstances))
            self.assertEqual(1, int(numberOfStudyRelatedInstances[0]))

        a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Study',
                                             'Expand': True,
                                             'Query' : { 'PatientID' : 'WITH_COMMENTS'},
                                             'RequestedTags': ['ModalitiesInStudy', 'NumberOfStudyRelatedSeries', 'NumberOfStudyRelatedInstances', 'PatientComments']})

        self.assertEqual(4, len(a[0]['RequestedTags'].keys()))
        self.assertEqual(1, int(a[0]['RequestedTags']['NumberOfStudyRelatedSeries']))
        self.assertEqual(1, int(a[0]['RequestedTags']['NumberOfStudyRelatedInstances']))
        self.assertEqual('CT', a[0]['RequestedTags']['ModalitiesInStudy'])
        self.assertEqual('', a[0]['RequestedTags']['PatientComments'])


    def test_extended_find_order_by(self):
        if IsOrthancVersionAbove(_REMOTE, 1, 12, 5) and HasExtendedFind(_REMOTE):
            # Upload 12 instances
            for i in range(3):
                r = UploadInstance(_REMOTE, 'Brainix/Flair/IM-0001-000%d.dcm' % (i + 1))
                DoPut(_REMOTE, '/instances/%s/metadata/1234' % r['ID'], '%f' % (10.0 + 0.1 * i))
                r = UploadInstance(_REMOTE, 'Brainix/Epi/IM-0001-000%d.dcm' % (i + 1))
                DoPut(_REMOTE, '/instances/%s/metadata/1234' % r['ID'], '%f' % (20.0 + 0.1 * i))
                r = UploadInstance(_REMOTE, 'Knee/T1/IM-0001-000%d.dcm' % (i + 1))
                DoPut(_REMOTE, '/instances/%s/metadata/1234' % r['ID'], '%f' % (30.0 + 0.1 * i))
                r = UploadInstance(_REMOTE, 'Knee/T2/IM-0001-000%d.dcm' % (i + 1))
                DoPut(_REMOTE, '/instances/%s/metadata/1234' % r['ID'], '%f' % (40.0 + 0.1 * i))

            kneeT2SeriesId = 'bbf7a453-0d34251a-03663b55-46bb31b9-ffd74c59'
            kneeT1SeriesId = '6de73705-c4e65c1b-9d9ea1b5-cabcd8e7-f15e4285'
            brainixFlairSeriesId = '1e2c125c-411b8e86-3f4fe68e-a7584dd3-c6da78f0'
            brainixEpiSeriesId = '2ac1316d-3e432022-62eabff2-c59f5475-9b1ac3f8'
            DoPut(_REMOTE, '/series/%s/metadata/my-metadata' % kneeT2SeriesId, 'kneeT2')
            DoPut(_REMOTE, '/series/%s/metadata/my-metadata' % kneeT1SeriesId, 'kneeT1')
            DoPut(_REMOTE, '/series/%s/metadata/my-metadata' % brainixFlairSeriesId, 'brainixFlair')
            DoPut(_REMOTE, '/series/%s/metadata/my-metadata' % brainixEpiSeriesId, 'brainixEpi')

            # order by resource tag
            a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Study',
                                                'Expand': True,
                                                'Query' : { 
                                                    'PatientName' : '*'
                                                },
                                                'OrderBy' : [
                                                    {
                                                        'Type': 'DicomTag',
                                                        'Key': 'PatientName',
                                                        'Direction': 'ASC'
                                                    }
                                                ]
                                                })
            self.assertEqual(2, len(a))
            self.assertEqual("BRAINIX", a[0]['PatientMainDicomTags']['PatientName'])

            a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Study',
                                                'Expand': True,
                                                'Query' : { 
                                                    'PatientName' : '*'
                                                },
                                                'OrderBy' : [
                                                    {
                                                        'Type': 'DicomTag',
                                                        'Key': 'PatientName',
                                                        'Direction': 'DESC'
                                                    }
                                                ]
                                                })

            self.assertEqual("BRAINIX", a[1]['PatientMainDicomTags']['PatientName'])

            # order by parent tag
            a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Series',
                                                'Expand': False,
                                                'Query' : { 
                                                    'SeriesDescription' : '*'
                                                },
                                                'OrderBy' : [
                                                    {
                                                        'Type': 'DicomTag',
                                                        'Key': 'StudyDate',
                                                        'Direction': 'ASC'
                                                    }
                                                ]
                                                })
            # knee StudyDate = 20080819
            # brainix StudyDate = 20061201
            self.assertEqual(4, len(a))
            self.assertTrue(a[0] == brainixEpiSeriesId or a[0] == brainixFlairSeriesId)
            self.assertTrue(a[3] == kneeT1SeriesId or a[3] == kneeT2SeriesId)

            # order by parent tag and resource tag
            a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Series',
                                                'Expand': False,
                                                'Query' : { 
                                                    'SeriesDescription' : '*'
                                                },
                                                'OrderBy' : [
                                                    {
                                                        'Type': 'DicomTag',
                                                        'Key': 'StudyDate',
                                                        'Direction': 'ASC'
                                                    },
                                                    {
                                                        'Type': 'DicomTag',
                                                        'Key': 'SeriesTime',
                                                        'Direction': 'ASC'
                                                    }
                                                ]
                                                })
            # knee StudyDate = 20080819
            # brainix StudyDate = 20061201
            self.assertEqual(4, len(a))
            self.assertEqual(brainixFlairSeriesId, a[0])
            self.assertEqual(brainixEpiSeriesId, a[1])
            self.assertEqual(kneeT1SeriesId, a[2])
            self.assertEqual(kneeT2SeriesId, a[3])

            # order by grandparent tag and resource tag
            a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Series',
                                                'Expand': False,
                                                'Query' : { 
                                                    'SeriesDescription' : '*'
                                                },
                                                'OrderBy' : [
                                                    {
                                                        'Type': 'DicomTag',
                                                        'Key': 'PatientBirthDate',
                                                        'Direction': 'ASC'
                                                    },
                                                    {
                                                        'Type': 'DicomTag',
                                                        'Key': 'SeriesTime',
                                                        'Direction': 'ASC'
                                                    }
                                                ]
                                                })
            # knee PatientBirthDate = 20080822
            # brainix PatientBirthDate = 19490301
            self.assertEqual(4, len(a))
            self.assertEqual(brainixFlairSeriesId, a[0])
            self.assertEqual(brainixEpiSeriesId, a[1])
            self.assertEqual(kneeT1SeriesId, a[2])
            self.assertEqual(kneeT2SeriesId, a[3])

            # order by grandgrandparent tag and resource tag
            a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Instance',
                                                'Expand': True,
                                                'Query' : { 
                                                },
                                                'OrderBy' : [
                                                    {
                                                        'Type': 'DicomTag',
                                                        'Key': 'PatientBirthDate',
                                                        'Direction': 'ASC'
                                                    },
                                                    {
                                                        'Type': 'DicomTagAsInt',
                                                        'Key': 'InstanceNumber',
                                                        'Direction': 'ASC'
                                                    },
                                                    {
                                                        'Type': 'DicomTag',
                                                        'Key': 'SeriesTime',
                                                        'Direction': 'ASC'
                                                    }
                                                ],
                                                'RequestedTags' : ['PatientBirthDate', 'InstanceNumber', 'SeriesTime']
                                                })
            self.assertEqual(12, len(a))
            for i in range(1, len(a)-1):
                self.assertTrue(a[i-1]['RequestedTags']['PatientBirthDate'] <= a[i]['RequestedTags']['PatientBirthDate'])
                if a[i-1]['RequestedTags']['PatientBirthDate'] == a[i]['RequestedTags']['PatientBirthDate']:
                    self.assertTrue(int(a[i-1]['RequestedTags']['InstanceNumber']) <= int(a[i]['RequestedTags']['InstanceNumber']))
                    if a[i-1]['RequestedTags']['InstanceNumber'] == a[i]['RequestedTags']['InstanceNumber']:
                        self.assertTrue(a[i-1]['RequestedTags']['SeriesTime'] <= a[i]['RequestedTags']['SeriesTime'])    

            # order by grandgrandparent tag and resource tag (2)
            a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Instance',
                                                'Expand': True,
                                                'Query' : { 
                                                },
                                                'OrderBy' : [
                                                    {
                                                        'Type': 'DicomTagAsInt',
                                                        'Key': 'InstanceNumber',
                                                        'Direction': 'DESC'
                                                    },
                                                    {
                                                        'Type': 'DicomTag',
                                                        'Key': 'PatientBirthDate',
                                                        'Direction': 'ASC'
                                                    },
                                                    {
                                                        'Type': 'DicomTag',
                                                        'Key': 'SeriesTime',
                                                        'Direction': 'ASC'
                                                    }
                                                ],
                                                'RequestedTags' : ['InstanceNumber', 'PatientBirthDate', 'SeriesTime' ]
                                                })
            self.assertEqual(12, len(a))
            for i in range(1, len(a)-1):
                self.assertTrue(int(a[i-1]['RequestedTags']['InstanceNumber']) >= int(a[i]['RequestedTags']['InstanceNumber']))
                if a[i-1]['RequestedTags']['InstanceNumber'] == a[i]['RequestedTags']['InstanceNumber']:
                    self.assertTrue(a[i-1]['RequestedTags']['PatientBirthDate'] <= a[i]['RequestedTags']['PatientBirthDate'])
                    if a[i-1]['RequestedTags']['PatientBirthDate'] == a[i]['RequestedTags']['PatientBirthDate']:
                        self.assertTrue(a[i-1]['RequestedTags']['SeriesTime'] <= a[i]['RequestedTags']['SeriesTime'])    

            # order by resource tag on a tag that is missing in one of the resources -> it should be listed
            a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Series',
                                                 'Expand': False,
                                                 'Query' : { 
                                                },
                                                
                                                'OrderBy' : [
                                                    {
                                                        'Type': 'DicomTag',
                                                        'Key': 'BodyPartExamined',  # in Knee but not in Brainix  => Brainix is last because NULL are pushed at the end
                                                        'Direction': 'ASC'
                                                    }
                                                ]
                                                })
            self.assertTrue(a[0] == kneeT1SeriesId or a[0] == kneeT2SeriesId)
            self.assertTrue(a[3] == brainixEpiSeriesId or a[3] == brainixFlairSeriesId)

            # order by metadata
            a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Series',
                                                 'Query' : { 
                                                    'SeriesDescription' : '*'
                                                },
                                                'OrderBy' : [
                                                    {
                                                        'Type': 'Metadata',
                                                        'Key': 'my-metadata',
                                                        'Direction': 'ASC'
                                                    }
                                                ]
                                                })
            self.assertEqual(brainixEpiSeriesId, a[0])
            self.assertEqual(brainixFlairSeriesId, a[1])
            self.assertEqual(kneeT1SeriesId, a[2])
            self.assertEqual(kneeT2SeriesId, a[3])

            a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Series',
                                                 'Query' : { 
                                                    'SeriesDescription' : '*'
                                                },
                                                'OrderBy' : [
                                                    {
                                                        'Type': 'Metadata',
                                                        'Key': 'my-metadata',
                                                        'Direction': 'DESC'
                                                    }
                                                ]
                                                })
            self.assertEqual(brainixEpiSeriesId, a[3])
            self.assertEqual(brainixFlairSeriesId, a[2])
            self.assertEqual(kneeT1SeriesId, a[1])
            self.assertEqual(kneeT2SeriesId, a[0])

            # combined ordering (DicomTag + metadata)
            a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Series',
                                                 'Query' : { 
                                                    'SeriesDescription' : '*'
                                                },
                                                'OrderBy' : [
                                                    {
                                                        'Type': 'DicomTag',
                                                        'Key': 'PatientName',
                                                        'Direction': 'ASC'
                                                    },
                                                    {
                                                        'Type': 'Metadata',
                                                        'Key': 'my-metadata',
                                                        'Direction': 'DESC'
                                                    }
                                                ]
                                                })
            self.assertEqual(brainixFlairSeriesId, a[0])
            self.assertEqual(brainixEpiSeriesId, a[1])
            self.assertEqual(kneeT2SeriesId, a[2])
            self.assertEqual(kneeT1SeriesId, a[3])


            a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Instance',
                                                'ResponseContent': ['Metadata', 'RequestedTags'],
                                                'Query' : { 
                                                },
                                                'OrderBy' : [
                                                    {
                                                        'Type': 'MetadataAsFloat',
                                                        'Key': '1234',
                                                        'Direction': 'DESC'
                                                    }
                                                ],
                                                'RequestedTags' : ['SeriesDescription']
                                                })
            self.assertEqual(12, len(a))
            for i in range(0, 2):
                self.assertEqual("T2W_TSE", a[i]['RequestedTags']['SeriesDescription'])
            self.assertAlmostEqual(40.2, float(a[0]['Metadata']['1234']))
            self.assertAlmostEqual(40.0, float(a[2]['Metadata']['1234']))

            for i in range(3, 5):
                self.assertEqual("T1W_aTSE", a[i]['RequestedTags']['SeriesDescription'])

            for i in range(6, 8):
                self.assertEqual("T2W/FE-EPI", a[i]['RequestedTags']['SeriesDescription'])

            for i in range(9, 11):
                self.assertEqual("sT2W/FLAIR", a[i]['RequestedTags']['SeriesDescription'])


    def test_extended_find_parent(self):
        if IsOrthancVersionAbove(_REMOTE, 1, 12, 5) and HasExtendedFind(_REMOTE):
            # Upload 12 instances
            for i in range(3):
                UploadInstance(_REMOTE, 'Knee/T1/IM-0001-000%d.dcm' % (i + 1))
                UploadInstance(_REMOTE, 'Knee/T2/IM-0001-000%d.dcm' % (i + 1))
                UploadInstance(_REMOTE, 'Brainix/Flair/IM-0001-000%d.dcm' % (i + 1))
                UploadInstance(_REMOTE, 'Brainix/Epi/IM-0001-000%d.dcm' % (i + 1))

            kneeT2SeriesId = 'bbf7a453-0d34251a-03663b55-46bb31b9-ffd74c59'
            kneeT1SeriesId = '6de73705-c4e65c1b-9d9ea1b5-cabcd8e7-f15e4285'
            kneeStudyId = '0a9b3153-2512774b-2d9580de-1fc3dcf6-3bd83918'
            kneePatientId = 'ca29faea-b6a0e17f-067743a1-8b778011-a48b2a17'

            # retrieve only the series from a study
            a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Series',
                                                 'Query' : { 
                                                    'SeriesDescription' : 'T*'
                                                },
                                                'ParentStudy' : kneeStudyId
                                                })

            self.assertEqual(2, len(a))
            self.assertTrue(a[0] == kneeT1SeriesId or a[0] == kneeT2SeriesId)

            # retrieve only the series from a patient
            a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Series',
                                                 'Query' : { 
                                                    'SeriesDescription' : 'T*'
                                                },
                                                'ParentPatient' : kneePatientId
                                                })

            self.assertEqual(2, len(a))
            self.assertTrue(a[0] == kneeT1SeriesId or a[0] == kneeT2SeriesId)

            # retrieve only the instances from a patient
            a = DoPost(_REMOTE, '/tools/find', { 'Level' : 'Instance',
                                                 'Query' : { 
                                                    'SeriesDescription' : 'T*'
                                                },
                                                'ParentPatient' : kneePatientId
                                                })

            self.assertEqual(6, len(a))

            # same query in count-resources
            a = DoPost(_REMOTE, '/tools/count-resources', { 'Level' : 'Instance',
                                                 'Query' : { 
                                                    'SeriesDescription' : 'T*'
                                                },
                                                'ParentPatient' : kneePatientId
                                                })

            self.assertEqual(6, a["Count"])


    def test_extended_find_filter_metadata(self):
        if IsOrthancVersionAbove(_REMOTE, 1, 12, 5) and HasExtendedFind(_REMOTE):
            # Upload 12 instances
            for i in range(3):
                UploadInstance(_REMOTE, 'Brainix/Flair/IM-0001-000%d.dcm' % (i + 1))
                UploadInstance(_REMOTE, 'Brainix/Epi/IM-0001-000%d.dcm' % (i + 1))
                UploadInstance(_REMOTE, 'Knee/T1/IM-0001-000%d.dcm' % (i + 1))
                UploadInstance(_REMOTE, 'Knee/T2/IM-0001-000%d.dcm' % (i + 1))

            kneeT2SeriesId = 'bbf7a453-0d34251a-03663b55-46bb31b9-ffd74c59'
            kneeT1SeriesId = '6de73705-c4e65c1b-9d9ea1b5-cabcd8e7-f15e4285'
            brainixFlairSeriesId = '1e2c125c-411b8e86-3f4fe68e-a7584dd3-c6da78f0'
            brainixEpiSeriesId = '2ac1316d-3e432022-62eabff2-c59f5475-9b1ac3f8'
            DoPut(_REMOTE, '/series/%s/metadata/my-metadata' % kneeT2SeriesId, 'kneeT2')
            DoPut(_REMOTE, '/series/%s/metadata/my-metadata' % kneeT1SeriesId, 'kneeT1')
            DoPut(_REMOTE, '/series/%s/metadata/my-metadata' % brainixFlairSeriesId, 'brainixFlair')
            DoPut(_REMOTE, '/series/%s/metadata/my-metadata' % brainixEpiSeriesId, 'brainixEpi')

            # filter on metadata
            q = {
                'Level' : 'Series',
                'Query' : { 
                    'SeriesDescription' : 'T*'
                },
                'MetadataQuery' : {
                    'my-metadata': '*2*'
                }
            }
            a = DoPost(_REMOTE, '/tools/find', q)

            self.assertEqual(1, len(a))
            self.assertEqual(kneeT2SeriesId, a[0])

            a = DoPost(_REMOTE, '/tools/count-resources', q)
            self.assertEqual(1, a["Count"])



    def test_extended_find_expand(self):
        if IsOrthancVersionAbove(_REMOTE, 1, 12, 5):
            UploadInstance(_REMOTE, 'Knee/T2/IM-0001-0001.dcm')

            a = DoPost(_REMOTE, '/tools/find', {    'Level' : 'Series',
                                                    'Query' : { 
                                                        'SeriesDescription' : 'T*'
                                                    },
                                                    'Expand': True,
                                                    'RequestedTags': ['StudyDate']
                                                    })

            # backward compat for Expand = True
            self.assertIn('ExpectedNumberOfInstances', a[0])
            self.assertIn('ID', a[0])
            self.assertIn('Instances', a[0])
            self.assertIn('Labels', a[0])
            self.assertIn('LastUpdate', a[0])
            self.assertIn('MainDicomTags', a[0])
            self.assertIn('ParentStudy', a[0])
            self.assertIn('RequestedTags', a[0])
            self.assertIn('Status', a[0])
            self.assertIn('Type', a[0])
            self.assertIn('IsStable', a[0])
            self.assertNotIn('Attachments', a[0])
            self.assertNotIn('Metadata', a[0])
            self.assertNotIn('IsProtected', a[0])


            a = DoPost(_REMOTE, '/tools/find', {    'Level' : 'Series',
                                                    'Query' : { 
                                                        'SeriesDescription' : 'T*'
                                                    },
                                                    'ResponseContent': ["MainDicomTags"],
                                                    'RequestedTags': ['StudyDate']
                                                    })

            self.assertIn('ID', a[0])            # the ID is always in the response
            self.assertIn('Type', a[0])          # the Type is always in the response
            self.assertIn('RequestedTags', a[0]) # the RequestedTags are always in the response as soon as you have requested them
            self.assertIn('MainDicomTags', a[0])
            self.assertNotIn('ExpectedNumberOfInstances', a[0])
            self.assertNotIn('Instances', a[0])
            self.assertNotIn('Labels', a[0])
            self.assertNotIn('LastUpdate', a[0])
            self.assertNotIn('ParentStudy', a[0])
            self.assertNotIn('Status', a[0])
            self.assertNotIn('IsStable', a[0])
            self.assertNotIn('Attachments', a[0])
            self.assertNotIn('Metadata', a[0])
            self.assertNotIn('IsProtected', a[0])


            a = DoPost(_REMOTE, '/tools/find', {    'Level' : 'Series',
                                                    'Query' : { 
                                                        'SeriesDescription' : 'T*'
                                                    },
                                                    'ResponseContent': ["MainDicomTags", "Children", "Parent", "IsStable", "Status", "Labels", "Metadata"],
                                                    'RequestedTags': ['StudyDate']
                                                    })

            self.assertIn('ID', a[0])            # the ID is always in the response
            self.assertIn('Type', a[0])          # the Type is always in the response
            self.assertIn('RequestedTags', a[0]) # the RequestedTags are always in the response as soon as you have requested them
            self.assertIn('MainDicomTags', a[0])
            self.assertIn('Metadata', a[0])
            self.assertIn('LastUpdate', a[0]['Metadata'])
            self.assertIn('Instances', a[0])
            self.assertIn('Labels', a[0])
            self.assertIn('ParentStudy', a[0])
            self.assertIn('Status', a[0])
            self.assertIn('IsStable', a[0])
            self.assertNotIn('Attachments', a[0])
            self.assertNotIn('IsProtected', a[0])


            a = DoPost(_REMOTE, '/tools/find', {    'Level' : 'Instances',
                                                    'Query' : { 
                                                        'SeriesDescription' : 'T*'
                                                    },
                                                    'Expand': True,
                                                    'RequestedTags': ['StudyDate']
                                                    })

            # backward compat for Expand = True at instance level
            self.assertIn('ID', a[0])            # the ID is always in the response
            self.assertIn('Type', a[0])          # the Type is always in the response
            self.assertIn('RequestedTags', a[0]) # the RequestedTags are always in the response as soon as you have requested them
            self.assertIn('FileSize', a[0])
            self.assertIn('FileUuid', a[0])
            self.assertIn('IndexInSeries', a[0])
            self.assertIn('ParentSeries', a[0])
            self.assertIn('Labels', a[0])
            self.assertNotIn('Attachments', a[0])
            self.assertNotIn('Metadata', a[0])
            self.assertNotIn('IsProtected', a[0])

            a = DoPost(_REMOTE, '/tools/find', {    'Level' : 'Instances',
                                                    'Query' : { 
                                                        'SeriesDescription' : 'T*'
                                                    },
                                                    'ResponseContent' : ['Attachments'],
                                                    'RequestedTags': ['StudyDate']
                                                    })

            self.assertIn('ID', a[0])            # the ID is always in the response
            self.assertIn('Type', a[0])          # the Type is always in the response
            self.assertIn('RequestedTags', a[0]) # the RequestedTags are always in the response as soon as you have requested them
            self.assertIn('Attachments', a[0])
            self.assertIn('Uuid', a[0]['Attachments'][0])
            self.assertIn('UncompressedSize', a[0]['Attachments'][0])


            # 'internal check': make sure we get the SOPClassUID even when we do not request the Metadata
            a = DoPost(_REMOTE, '/tools/find', {    'Level' : 'Instances',
                                                    'Query' : { 
                                                        'SeriesDescription' : 'T*'
                                                    },
                                                    'ResponseContent' : [],
                                                    'RequestedTags': ['SOPClassUID']
                                                    })

            self.assertIn('ID', a[0])            # the ID is always in the response
            self.assertIn('Type', a[0])          # the Type is always in the response
            self.assertIn('RequestedTags', a[0]) # the RequestedTags are always in the response as soon as you have requested them
            self.assertIn('SOPClassUID', a[0]['RequestedTags'])

        if IsOrthancVersionAbove(_REMOTE, 1, 12, 8):
            a = DoPost(_REMOTE, '/tools/find', {    'Level' : 'Patients',
                                                    'Query' : { 
                                                    },
                                                    'ResponseContent' : ['IsProtected']
                                                    })

            self.assertIn('ID', a[0])            # the ID is always in the response
            self.assertIn('Type', a[0])          # the Type is always in the response
            self.assertIn('IsProtected', a[0])



    def test_extended_find_full(self):
        if IsOrthancVersionAbove(_REMOTE, 1, 12, 5) and HasExtendedFind(_REMOTE):
            # Upload 12 instances
            for i in range(3):
                UploadInstance(_REMOTE, 'Brainix/Flair/IM-0001-000%d.dcm' % (i + 1))
                UploadInstance(_REMOTE, 'Brainix/Epi/IM-0001-000%d.dcm' % (i + 1))
                UploadInstance(_REMOTE, 'Knee/T1/IM-0001-000%d.dcm' % (i + 1))
                UploadInstance(_REMOTE, 'Knee/T2/IM-0001-000%d.dcm' % (i + 1))

            kneeT2SeriesId = 'bbf7a453-0d34251a-03663b55-46bb31b9-ffd74c59'
            kneeT1SeriesId = '6de73705-c4e65c1b-9d9ea1b5-cabcd8e7-f15e4285'
            brainixFlairSeriesId = '1e2c125c-411b8e86-3f4fe68e-a7584dd3-c6da78f0'
            brainixEpiSeriesId = '2ac1316d-3e432022-62eabff2-c59f5475-9b1ac3f8'
            kneeStudyId = '0a9b3153-2512774b-2d9580de-1fc3dcf6-3bd83918'
            kneePatientId = 'ca29faea-b6a0e17f-067743a1-8b778011-a48b2a17'
            DoPut(_REMOTE, '/series/%s/metadata/my-metadata' % kneeT2SeriesId, 'kneeT2')
            DoPut(_REMOTE, '/series/%s/metadata/my-metadata' % kneeT1SeriesId, 'kneeT1')
            DoPut(_REMOTE, '/series/%s/metadata/my-metadata' % brainixFlairSeriesId, 'brainixFlair')
            DoPut(_REMOTE, '/series/%s/metadata/my-metadata' % brainixEpiSeriesId, 'brainixEpi')

            a = DoPost(_REMOTE, '/tools/find', {    'Level' : 'Series',
                                                    'Query' : { 
                                                        'PatientName' : '*'
                                                    },
                                                    'RequestedTags': ['StudyDate'],
                                                    'MetadataQuery' : {
                                                        'my-metadata': "*nee*"
                                                    },
                                                    'OrderBy' : [
                                                        {
                                                            'Type': 'DicomTag',
                                                            'Key': 'SeriesDescription',
                                                            'Direction': 'ASC'
                                                        },
                                                        {
                                                            'Type': 'Metadata',
                                                            'Key': 'my-metadata',
                                                            'Direction': 'DESC'
                                                        }
                                                    ],
                                                    'ParentPatient': kneePatientId,
                                                    'ResponseContent' : ['Parent', 'Children', 'MainDicomTags', 'Metadata']
                                                    })

            self.assertEqual(2, len(a))
            self.assertEqual(kneeT1SeriesId, a[0]['ID'])
            self.assertEqual(kneeT2SeriesId, a[1]['ID'])
            self.assertEqual(kneeStudyId, a[0]['ParentStudy'])
            self.assertEqual(3, len(a[0]['Instances']))
            self.assertEqual('', a[0]['Metadata']['RemoteAET'])

    def test_pagination_and_limit_find_results(self):
        # LimitFindInstances is set to 20
        # LimitFindResults is set to 10

        # Upload 27 instances from KNIX
        UploadFolder(_REMOTE, 'Knix/Loc')

        # Upload 13 other series
        UploadInstance(_REMOTE, 'DummyCT.dcm')
        UploadInstance(_REMOTE, 'Phenix/IM-0001-0001.dcm')
        UploadInstance(_REMOTE, 'Implicit-vr-us-palette.dcm')
        UploadInstance(_REMOTE, 'Multiframe.dcm')
        UploadInstance(_REMOTE, 'Brainix/Flair/IM-0001-0001.dcm')
        UploadInstance(_REMOTE, 'Knee/T1/IM-0001-0001.dcm')
        UploadInstance(_REMOTE, 'Knee/T2/IM-0001-0001.dcm')
        UploadInstance(_REMOTE, 'PrivateTags.dcm')
        UploadInstance(_REMOTE, 'PrivateMDNTags.dcm')
        UploadInstance(_REMOTE, 'Comunix/Ct/IM-0001-0001.dcm')
        UploadInstance(_REMOTE, 'Comunix/Pet/IM-0001-0001.dcm')
        UploadInstance(_REMOTE, 'Beaufix/IM-0001-0001.dcm')
        UploadInstance(_REMOTE, 'Encodings/Lena-ascii.dcm')

        self.assertEqual(14, len(DoGet(_REMOTE, '/series')))


        # knixInstancesNoLimit = DoPost(_REMOTE, '/tools/find', {    
        #                                         'Level' : 'Instances',
        #                                         'Query' : { 
        #                                             'PatientName' : 'KNIX'
        #                                         },
        #                                         'Expand': False
        #                                         })

        # # pprint.pprint(knixInstancesNoLimit)
        # if IsOrthancVersionAbove(_REMOTE, 1, 12, 5) and HasExtendedFind(_REMOTE):
        #     self.assertEqual(20, len(knixInstancesNoLimit))
        # else:
        #     self.assertEqual(21, len(knixInstancesNoLimit))

        # knixInstancesSince5Limit20 = DoPost(_REMOTE, '/tools/find', {    
        #                                         'Level' : 'Instances',
        #                                         'Query' : { 
        #                                             'PatientName' : 'KNIX'
        #                                         },
        #                                         'Expand': False,
        #                                         'Since': 5,
        #                                         'Limit': 20
        #                                         })
        # # pprint.pprint(knixInstancesSince5Limit20)
        
        # if IsOrthancVersionAbove(_REMOTE, 1, 12, 5):
        #     self.assertEqual(20, len(knixInstancesSince5Limit20))  # Orthanc actually returns LimitFindInstances + 1 resources
        #     # the first 5 from previous call shall not be in this answer
        #     for i in range(0, 5):
        #         self.assertNotIn(knixInstancesNoLimit[i], knixInstancesSince5Limit20)
        #     # the last 4 from last call shall not be in the first answer
        #     for i in range(16, 20):
        #         self.assertNotIn(knixInstancesSince5Limit20[i], knixInstancesNoLimit)

        # # request more instances than LimitFindInstances
        # knixInstancesSince0Limit23 = DoPost(_REMOTE, '/tools/find', {    
        #                                         'Level' : 'Instances',
        #                                         'Query' : { 
        #                                             'PatientName' : 'KNIX'
        #                                         },
        #                                         'Expand': False,
        #                                         'Since': 0,
        #                                         'Limit': 23
        #                                         })
        # if IsOrthancVersionAbove(_REMOTE, 1, 12, 5) and HasExtendedFind(_REMOTE):
        #     self.assertEqual(20, len(knixInstancesSince0Limit23))

        # seriesNoLimit = DoPost(_REMOTE, '/tools/find', {    
        #                                         'Level' : 'Series',
        #                                         'Query' : { 
        #                                             'PatientName' : '*'
        #                                         },
        #                                         'Expand': False
        #                                         })

        # # pprint.pprint(seriesNoLimit)
        # if IsOrthancVersionAbove(_REMOTE, 1, 12, 5) and HasExtendedFind(_REMOTE):
        #     self.assertEqual(10, len(seriesNoLimit))
        # else:
        #     self.assertEqual(11, len(seriesNoLimit))

        # seriesSince8Limit6 = DoPost(_REMOTE, '/tools/find', {    
        #                                         'Level' : 'Series',
        #                                         'Query' : { 
        #                                             'PatientName' : '*'
        #                                         },
        #                                         'Expand': False,
        #                                         'Since': 8,
        #                                         'Limit': 6
        #                                         })

        # # pprint.pprint(seriesSince8Limit6)
        # if IsOrthancVersionAbove(_REMOTE, 1, 12, 5) and HasExtendedFind(_REMOTE): # TODO: remove HasExtendedFind once find-refactoring branch has been merged and supported by all DB plugins !!!
        #     self.assertEqual(6, len(seriesSince8Limit6))

        #     # the first 7 from previous call shall not be in this answer
        #     for i in range(0, 7):
        #         self.assertNotIn(seriesNoLimit[i], seriesSince8Limit6)
        #     # the last 3 from last call shall not be in the first answer
        #     for i in range(3, 5):
        #         self.assertNotIn(seriesSince8Limit6[i], seriesNoLimit)

        # if IsOrthancVersionAbove(_REMOTE, 1, 12, 5) and HasExtendedFind(_REMOTE):
        #     # query by a tag that is not in the DB (there are 27 instances from Knix/Loc + 10 instances from other series that satisfies this criteria)
        #     a = DoPost(_REMOTE, '/tools/find', {    
        #                                             'Level' : 'Instances',
        #                                             'Query' : { 
        #                                                 'PhotometricInterpretation' : 'MONOCHROME*'
        #                                             },
        #                                             'Expand': True,
        #                                             'OrderBy' : [
        #                                                     {
        #                                                         'Type': 'DicomTag',
        #                                                         'Key': 'InstanceNumber',
        #                                                         'Direction': 'ASC'
        #                                                     }
        #                                             ]})

        #     # pprint.pprint(a)
        #     # print(len(a))
        #     # TODO: we should have something in the response that notifies us that the response is not "complete"
        #     # TODO: we should receive an error if we try to use "since" in this kind of search ?
        #     self.assertEqual(17, len(a))   # the fast DB filtering returns 20 instances -> only 17 of them meet the criteria but this is not really correct !!!

        if IsOrthancVersionAbove(_REMOTE, 1, 12, 5) and HasExtendedFind(_REMOTE):
            # make sur an error is returned when using Since or Limit when querying a tag that is not in DB
            self.assertRaises(Exception, lambda: DoPost(_REMOTE, '/tools/find', {'Level' : 'Instances',
                                                    'Query' : { 
                                                        'PhotometricInterpretation' : 'MONOCHROME*'
                                                    },
                                                    'Since': 2
                                                    }))

            # make sur an error is returned when using Since when querying a tag that is not in DB
            self.assertRaises(Exception, lambda: DoPost(_REMOTE, '/tools/find', {'Level' : 'Instances',
                                                    'Query' : { 
                                                        'PhotometricInterpretation' : 'MONOCHROME*'
                                                    },
                                                    'Since': 10
                                                    }))

        # https://github.com/orthanc-server/orthanc-explorer-2/issues/73
        if IsOrthancVersionAbove(_REMOTE, 1, 12, 6) and HasExtendedFind(_REMOTE):
            # make sur no error is returned when using Since or Limit when querying against ModalitiesInStudy
            a = DoPost(_REMOTE, '/tools/find', {'Level' : 'Studies',
                                                'Query' : { 
                                                    'ModalitiesInStudy' : 'CT\\MR'
                                                },
                                                'Since': 2,
                                                'Limit': 3,
                                                'Expand': True,
                                                'OrderBy': [
                                                    {
                                                        'Type': 'DicomTag',
                                                        'Key': 'StudyDate',
                                                        'Direction': 'ASC'
                                                    }                                                        
                                                ]})
            # pprint.pprint(a)
            self.assertEqual('20050927', a[0]['MainDicomTags']['StudyDate'])
            self.assertEqual('20061201', a[1]['MainDicomTags']['StudyDate'])
            self.assertEqual('20070101', a[2]['MainDicomTags']['StudyDate'])


    def test_attachment_range(self):
        def TestData(path):
            (resp, content) = DoGetRaw(_REMOTE, '/instances/%s/attachments/dicom/%s' % (i, path))
            self.assertFalse('content-range' in resp)
            self.assertEqual(200, resp.status)
            self.assertEqual(2472, len(content))
            self.assertEqual('2472', resp['content-length'])
            self.assertEqual('application/dicom', resp['content-type'])

            (resp, content) = DoGetRaw(_REMOTE, '/instances/%s/attachments/dicom/%s' % (i, path), headers = { 'Range' : 'bytes=128-131' })
            self.assertTrue('content-range' in resp)
            self.assertEqual(206, resp.status)
            self.assertEqual(4, len(content))
            self.assertEqual('D', content[0])
            self.assertEqual('I', content[1])
            self.assertEqual('C', content[2])
            self.assertEqual('M', content[3])
            self.assertEqual('4', resp['content-length'])
            self.assertEqual('application/octet-stream', resp['content-type'])
            self.assertEqual('bytes 128-131/2472', resp['content-range'])

            (resp, content) = DoGetRaw(_REMOTE, '/instances/%s/attachments/dicom/%s' % (i, path), headers = { 'Range' : 'bytes=-' })
            self.assertTrue('content-range' in resp)
            self.assertEqual(206, resp.status)
            self.assertEqual(2472, len(content))
            self.assertEqual('2472', resp['content-length'])
            self.assertEqual('application/octet-stream', resp['content-type'])
            self.assertEqual('bytes 0-2471/2472', resp['content-range'])

            (resp, content) = DoGetRaw(_REMOTE, '/instances/%s/attachments/dicom/%s' % (i, path), headers = { 'Range' : 'bytes=128-' })
            self.assertTrue('content-range' in resp)
            self.assertEqual(206, resp.status)
            self.assertEqual(2344, len(content))
            self.assertEqual('D', content[0])
            self.assertEqual('I', content[1])
            self.assertEqual('C', content[2])
            self.assertEqual('M', content[3])
            self.assertEqual('2344', resp['content-length'])
            self.assertEqual('application/octet-stream', resp['content-type'])
            self.assertEqual('bytes 128-2471/2472', resp['content-range'])

            (resp, content) = DoGetRaw(_REMOTE, '/instances/%s/attachments/dicom/%s' % (i, path), headers = { 'Range' : 'bytes=-131' })
            self.assertTrue('content-range' in resp)
            self.assertEqual(206, resp.status)
            self.assertEqual(132, len(content))
            self.assertEqual('D', content[-4])
            self.assertEqual('I', content[-3])
            self.assertEqual('C', content[-2])
            self.assertEqual('M', content[-1])
            self.assertEqual('132', resp['content-length'])
            self.assertEqual('application/octet-stream', resp['content-type'])
            self.assertEqual('bytes 0-131/2472', resp['content-range'])

        if IsOrthancVersionAbove(_REMOTE, 1, 12, 5):
            i = UploadInstance(_REMOTE, 'DummyCT.dcm') ['ID']

            DoPost(_REMOTE, '/instances/%s/attachments/dicom/uncompress' % i)
            TestData('data')
            TestData('compressed-data')

            DoPost(_REMOTE, '/instances/%s/attachments/dicom/compress' % i)
            TestData('data')

            (resp, compressed) = DoGetRaw(_REMOTE, '/instances/%s/attachments/dicom/compressed-data' % i)
            self.assertFalse('content-range' in resp)
            self.assertEqual(200, resp.status)
            self.assertTrue(len(compressed) < 2000)
            self.assertEqual(len(compressed), int(resp['content-length']))
            self.assertEqual('application/octet-stream', resp['content-type'])

            (resp, content) = DoGetRaw(_REMOTE, '/instances/%s/attachments/dicom/compressed-data' % i, headers = { 'Range' : 'bytes=-' })
            self.assertTrue('content-range' in resp)
            self.assertEqual(206, resp.status)
            self.assertEqual(compressed, content)
            self.assertEqual(len(compressed), int(resp['content-length']))
            self.assertEqual('application/octet-stream', resp['content-type'])
            self.assertEqual('bytes 0-%d/%d' % (len(compressed) - 1, len(compressed)), resp['content-range'])

            (resp, content) = DoGetRaw(_REMOTE, '/instances/%s/attachments/dicom/compressed-data' % i, headers = { 'Range' : 'bytes=10-' })
            self.assertTrue('content-range' in resp)
            self.assertEqual(206, resp.status)
            self.assertEqual(compressed[10:], content)
            self.assertEqual(len(compressed) - 10, int(resp['content-length']))
            self.assertEqual('application/octet-stream', resp['content-type'])
            self.assertEqual('bytes 10-%d/%d' % (len(compressed) - 1, len(compressed)), resp['content-range'])

            (resp, content) = DoGetRaw(_REMOTE, '/instances/%s/attachments/dicom/compressed-data' % i, headers = { 'Range' : 'bytes=-20' })
            self.assertTrue('content-range' in resp)
            self.assertEqual(206, resp.status)
            self.assertEqual(compressed[0:21], content)
            self.assertEqual(21, int(resp['content-length']))
            self.assertEqual('application/octet-stream', resp['content-type'])
            self.assertEqual('bytes 0-20/%d' % len(compressed), resp['content-range'])

            (resp, content) = DoGetRaw(_REMOTE, '/instances/%s/attachments/dicom/compressed-data' % i, headers = { 'Range' : 'bytes=10-20' })
            self.assertTrue('content-range' in resp)
            self.assertEqual(206, resp.status)
            self.assertEqual(compressed[10:21], content)
            self.assertEqual(11, int(resp['content-length']))
            self.assertEqual('application/octet-stream', resp['content-type'])
            self.assertEqual('bytes 10-20/%d' % len(compressed), resp['content-range'])

    def test_order_by_non_existing_metadata(self):
        if IsOrthancVersionAbove(_REMOTE, 1, 12, 7) and HasExtendedFind(_REMOTE):
            r = UploadInstance(_REMOTE, 'sample-pdf.dcm')

            # order by a metadata that does not exist (PDF do not have IndexInSeries)
            a = DoPost(_REMOTE, '/tools/find', {    'Level' : 'Instances',
                                                    'ParentSeries': r['ParentSeries'],
                                                    'Query' : { 
                                                    },
                                                    'OrderBy' : [
                                                        {
                                                            'Type': 'Metadata',
                                                            'Key': 'IndexInSeries',
                                                            'Direction': 'ASC'
                                                        }
                                                    ]
                                                })
            self.assertEqual(1, len(a))

            a = DoPost(_REMOTE, '/tools/find', {    'Level' : 'Instances',
                                                    'ParentSeries': r['ParentSeries'],
                                                    'Query' : { 
                                                    },
                                                    'OrderBy' : [
                                                        {
                                                            'Type': 'Metadata',
                                                            'Key': '9876',
                                                            'Direction': 'ASC'
                                                        }
                                                    ]
                                                })
            self.assertEqual(1, len(a))

    def test_order_by_non_existing_tag(self):
        if IsOrthancVersionAbove(_REMOTE, 1, 12, 7) and HasExtendedFind(_REMOTE):
            r = UploadInstance(_REMOTE, 'sample-pdf.dcm')

            # order by a DICOM Tag that does not exist (PDF do not have ROWS)
            a = DoPost(_REMOTE, '/tools/find', {    'Level' : 'Instances',
                                                    'ParentSeries': r['ParentSeries'],
                                                    'Query' : { 
                                                    },
                                                    'OrderBy' : [
                                                        {
                                                            'Type': 'DicomTag',
                                                            'Key': 'Rows',
                                                            'Direction': 'ASC'
                                                        }
                                                    ]
                                                })
            self.assertEqual(1, len(a))

    def test_deflated_invalid_size(self):  # https://discourse.orthanc-server.org/t/transcoding-to-deflated-transfer-syntax-fails/5489
        if IsOrthancVersionAbove(_REMOTE, 1, 12, 7):
            instanceId = '6582b1c0-292ad5ab-ba0f088f-f7a1766f-9a29a54f'

            r = UploadInstance(_REMOTE, 'TransferSyntaxes/1.2.840.10008.1.2.1.99.dcm')
            attachments = DoGet(_REMOTE, '/instances/' + instanceId + '/attachments/dicom/info/')
            self.assertEqual(instanceId, r['ID'])
            self.assertEqual(181071, int(attachments['UncompressedSize']))

            DoDelete(_REMOTE, '/instances/' + instanceId)

            subprocess.check_call([ FindExecutable('storescu'), '-xd', # propose deflated
                                _REMOTE['Server'], str(_REMOTE['DicomPort']),
                                GetDatabasePath('TransferSyntaxes/1.2.840.10008.1.2.1.99.dcm') ])
            attachments = DoGet(_REMOTE, '/instances/' + instanceId + '/attachments/dicom/info/')
            self.assertLessEqual(181071, int(attachments['UncompressedSize']))
            self.assertGreaterEqual(181073, int(attachments['UncompressedSize']))  # there might be some padding added

    def test_embed_jpeg(self):
        if not IsOrthancVersionAbove(_REMOTE, 1, 12, 7):
            return

        with open(GetDatabasePath('Lena.jpg'), 'rb') as f:
            jpeg = f.read()

        i = DoPost(_REMOTE, '/tools/create-dicom', json.dumps({
            'Content' : 'data:image/jpeg;base64,%s' % base64.b64encode(jpeg).decode(),
            'Encapsulate' : True,
            'Tags' : {
                'SOPClassUID' : '1.2.840.10008.5.1.4.1.1.7',
            }
        })) ['ID']

        tags = DoGet(_REMOTE, '/instances/%s/tags?simplify' % i)
        self.assertEqual(tags['BitsAllocated'], '8')
        self.assertEqual(tags['BitsStored'], '8')
        self.assertEqual(tags['Columns'], '512')
        self.assertEqual(tags['HighBit'], '7')
        self.assertEqual(tags['PhotometricInterpretation'], 'YBR_FULL_422')
        self.assertEqual(tags['PixelData'], None)
        self.assertEqual(tags['PixelRepresentation'], '0')
        self.assertEqual(tags['PlanarConfiguration'], '0')
        self.assertEqual(tags['Rows'], '512')
        self.assertEqual(tags['SOPClassUID'], '1.2.840.10008.5.1.4.1.1.7')
        self.assertEqual(tags['SamplesPerPixel'], '3')
        self.assertEqual(tags['SpecificCharacterSet'], 'ISO_IR 100')
        pixelData = DoGet(_REMOTE, '/instances/%s/content/7fe0,0010' % i)
        self.assertEqual(len(pixelData), 2)
        self.assertEqual(pixelData[0], '0')
        self.assertEqual(pixelData[1], '1')
        resp, embedded = DoGetRaw(_REMOTE, '/instances/%s/content/7fe0,0010/1' % i)
        self.assertEqual('200', resp['status'])
        self.assertEqual(len(embedded), len(jpeg))
        self.assertEqual(embedded, jpeg)

        b = io.BytesIO()
        UncompressImage(jpeg).convert('L').save(b, format = 'jpeg')

        b.seek(0)
        grayscale = b.read()

        if len(grayscale) % 2 != 0:
            grayscale = grayscale + '\0'   # Add padding to OW boundaries (2 bytes)

        i = DoPost(_REMOTE, '/tools/create-dicom', json.dumps({
            'Content' : 'data:image/jpeg;base64,%s' % base64.b64encode(grayscale).decode(),
            'Encapsulate' : True,
            'Tags' : {
                'SOPClassUID' : '1.2.840.10008.5.1.4.1.1.7',
            }
        })) ['ID']

        tags = DoGet(_REMOTE, '/instances/%s/tags?simplify' % i)
        self.assertEqual(tags['BitsAllocated'], '8')
        self.assertEqual(tags['BitsStored'], '8')
        self.assertEqual(tags['Columns'], '512')
        self.assertEqual(tags['HighBit'], '7')
        self.assertEqual(tags['PhotometricInterpretation'], 'MONOCHROME2')
        self.assertEqual(tags['PixelData'], None)
        self.assertEqual(tags['PixelRepresentation'], '0')
        self.assertFalse('PlanarConfiguration' in tags)
        self.assertEqual(tags['Rows'], '512')
        self.assertEqual(tags['SOPClassUID'], '1.2.840.10008.5.1.4.1.1.7')
        self.assertEqual(tags['SamplesPerPixel'], '1')
        self.assertEqual(tags['SpecificCharacterSet'], 'ISO_IR 100')
        pixelData = DoGet(_REMOTE, '/instances/%s/content/7fe0,0010' % i)
        self.assertEqual(len(pixelData), 2)
        self.assertEqual(pixelData[0], '0')
        self.assertEqual(pixelData[1], '1')
        resp, embedded = DoGetRaw(_REMOTE, '/instances/%s/content/7fe0,0010/1' % i)
        self.assertEqual('200', resp['status'])
        self.assertEqual(len(embedded), len(grayscale))
        self.assertEqual(embedded, grayscale)


    def test_encodings_iso_ir13(self):
        if IsOrthancVersionAbove(_REMOTE, 1, 12, 9):
            # from https://discourse.orthanc-server.org/t/issue-with-special-characters-when-scans-where-uploaded-with-specificcharacterset-dicom-tag-value-as-iso-ir-13/5962
            instanceId = UploadInstance(_REMOTE, 'Encodings/ISO_IR13.dcm')['ID']
            tags = DoGet(_REMOTE, '/instances/%s/tags?simplify' % instanceId)
            self.assertEqual('ORIGINAL\PRIMARY\M\NORM\DIS2D\FM\FIL', tags['ImageType'])


    def test_jobs_user_data(self):
        if IsOrthancVersionAbove(_REMOTE, 1, 12, 9):
            u = UploadInstance(_REMOTE, 'DummyCT.dcm')

            job = DoPost(_REMOTE, '/studies/%s/modify' % u['ParentStudy'],
                                json.dumps({
                                    "Replace": {"PatientName": "toto"},
                                    "UserData": { "user-data": "titi"
                                                },
                                    "Asynchronous": True
                                }))
            jobDetails = DoGet(_REMOTE, '/jobs/%s' % job['ID'])
            self.assertEqual('titi', jobDetails['UserData']['user-data'])

            job = DoPost(_REMOTE, '/tools/create-archive',
                                json.dumps({
                                    "Resources": [u['ParentStudy']],
                                    "UserData": "simple-string",
                                    "Asynchronous": True
                                }))
            jobDetails = DoGet(_REMOTE, '/jobs/%s' % job['ID'])
            self.assertEqual('simple-string', jobDetails['UserData'])

            job = DoPost(_REMOTE, '/modalities/orthanctest/move', { 
                'Level' : 'Study',
                'Asynchronous': True,
                "UserData": "simple-string",
                'Resources' : [
                    { 
                        'StudyInstanceUID' : '1.2.840.113619.2.176.2025.1499492.7391.1171285944.390'
                    }
                ]})

            jobDetails = DoGet(_REMOTE, '/jobs/%s' % job['ID'])
            self.assertEqual('simple-string', jobDetails['UserData'])

            job = DoPost(_REMOTE, '/modalities/orthanctest/store', { 
                'Level' : 'Study',
                'Asynchronous': True,
                "UserData": "simple-string",
                'Resources' : [u['ParentStudy']]})

            jobDetails = DoGet(_REMOTE, '/jobs/%s' % job['ID'])
            self.assertEqual('simple-string', jobDetails['UserData'])
