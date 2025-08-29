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



# You must add the following to the configuration file:
#
# {
#   "MaximumPatientCount" : 4
# }



import os
import pprint
import sys
import argparse
import unittest
import re

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'Tests'))
from Toolbox import *


##
## Parse the command-line arguments
##

parser = argparse.ArgumentParser(description = 'Run the integration tests for the patient recycling behavior.')

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


##
## The tests
##


DICOM = {
    'brainix' : [
        'Brainix/Flair/IM-0001-0001.dcm',
        'Brainix/Epi/IM-0001-0001.dcm',
    ],
    'knee' : [
        'Knee/T1/IM-0001-0001.dcm',
        'Knee/T2/IM-0001-0001.dcm',
    ],
    'beaufix' : [
        'Beaufix/IM-0001-0001.dcm',
    ],
    'phenix' : [
        'Phenix/IM-0001-0001.dcm',
    ],
    'dummy' : [
        'DummyCT.dcm',
    ],
    'comunix' : [
        'Comunix/Pet/IM-0001-0001.dcm',
        'Comunix/Pet/IM-0001-0002.dcm',
    ],
}

PATIENTS = list(DICOM.keys())



def UploadAndGetPatientId(patient, instance):
    a = UploadInstance(ORTHANC, DICOM[patient][instance])['ID']
    return DoGet(ORTHANC, '/instances/%s/patient' % a)['ID']

def TestContent(expectedPatients):
    patients = DoGet(ORTHANC, '/patients')
    if len(patients) != len(expectedPatients):
        return False

    for i in expectedPatients:
        if not i in patients:
            return False

    for i in patients:
        if not i in expectedPatients:
            return False

    return True


class Orthanc(unittest.TestCase):
    def setUp(self):
        if (sys.version_info >= (3, 0)):
            # Remove annoying warnings about unclosed socket in Python 3
            import warnings
            warnings.simplefilter("ignore", ResourceWarning)

        DropOrthanc(ORTHANC)

        
    def test_config(self):
        # Make sure that "MaximumPatientCount" equals 4
        a = UploadAndGetPatientId('brainix', 0)
        b = UploadAndGetPatientId('knee', 0)
        c = UploadAndGetPatientId('beaufix', 0)
        d = UploadAndGetPatientId('phenix', 0)
        self.assertEqual(4, len(DoGet(ORTHANC, '/instances')))

        e = UploadAndGetPatientId('dummy', 0)
        self.assertTrue(TestContent([b, c, d, e ]))

        
    def test_loop(self):
        ids = []
        
        for i in range(5):
            ids.append(UploadAndGetPatientId(PATIENTS[i], 0))
        
        self.assertEqual(4, len(DoGet(ORTHANC, '/instances')))

        for i in range(20):
            expected = set(ids)
            expected.remove(ids[i % 5])
            TestContent(expected)
            
            self.assertEqual(ids[i % 5], UploadAndGetPatientId(PATIENTS[i % 5], 0))

            
    def test_protection(self):
        a = UploadAndGetPatientId('brainix', 0)
        b = UploadAndGetPatientId('knee', 0)
        c = UploadAndGetPatientId('beaufix', 0)
        d = UploadAndGetPatientId('phenix', 0)

        DoPut(ORTHANC, '/patients/%s/protected' % b, '1')
        UploadAndGetPatientId('knee', 1)

        e = UploadAndGetPatientId('dummy', 0)
        f = UploadAndGetPatientId('comunix', 0)

        self.assertTrue(TestContent([ d, e, f, b ]))

        # This puts "b" at the end of the recycling order
        DoPut(ORTHANC, '/patients/%s/protected' % b, '0')
        
        a = UploadAndGetPatientId('brainix', 0)
        self.assertTrue(TestContent([ e, f, b, a ]))

        c = UploadAndGetPatientId('beaufix', 0)
        self.assertTrue(TestContent([ f, b, a, c ]))

        d = UploadAndGetPatientId('phenix', 0)
        self.assertTrue(TestContent([ b, a, c, d ]))
        
        e = UploadAndGetPatientId('dummy', 0)
        self.assertTrue(TestContent([ a, c, d, e ]))


    def test_bitbucket_issue_58(self):
        a = UploadAndGetPatientId('brainix', 0)
        b = UploadAndGetPatientId('knee', 0)
        c = UploadAndGetPatientId('beaufix', 0)
        d = UploadAndGetPatientId('phenix', 0)
        self.assertEqual(4, len(DoGet(ORTHANC, '/instances')))

        e = UploadAndGetPatientId('dummy', 0)
        self.assertTrue(TestContent([b, c, d, e ]))

        UploadAndGetPatientId('knee', 1)
        self.assertTrue(TestContent([c, d, e, b ]))

        f = UploadAndGetPatientId('comunix', 0)
        self.assertTrue(TestContent([d, e, b, f ]))
        
        
try:
    print('\nStarting the tests...')
    unittest.main(argv = [ sys.argv[0] ] + args.options)

finally:
    print('\nDone')
