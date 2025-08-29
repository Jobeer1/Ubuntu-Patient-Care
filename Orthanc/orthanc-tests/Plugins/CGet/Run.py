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



import argparse
import os
import pprint
import re
import sys
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'Tests'))
from Toolbox import *


##
## Parse the command-line arguments
##

parser = argparse.ArgumentParser(description = 'Run the integration tests for the C-GET SCP of Orthanc.')

parser.add_argument('--server', 
                    default = 'localhost',
                    help = 'Address of the Orthanc server to test')
parser.add_argument('--aet',
                    default = 'ORTHANC',
                    help = 'AET of the Orthanc instance to test')
parser.add_argument('--dicom',
                    type = int,
                    default = 4242,
                    help = 'DICOM port of the Orthanc instance to test')
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
                        restPort = args.rest,
                        aet = args.aet,
                        dicomPort = args.dicom)


##
## pydicom toolbox
##

from pydicom.dataset import Dataset
from pynetdicom import (
    AE,
    evt,
    build_role,
    debug_logger,
)
from pynetdicom.sop_class import *

def ExecuteCGet(orthanc, dataset, sopClass, callback):
    handlers = [(evt.EVT_C_STORE, callback)]

    ae = AE(ae_title = 'ORTHANCTEST')

    ae.add_requested_context(PatientRootQueryRetrieveInformationModelGet)
    ae.add_requested_context(sopClass)
    role = build_role(sopClass, scp_role = True, scu_role = True)

    assoc = ae.associate(orthanc['Server'], orthanc['DicomPort'],
                         ext_neg = [role], evt_handlers = handlers)

    if assoc.is_established:
        responses = assoc.send_c_get(
            dataset,
            PatientRootQueryRetrieveInformationModelGet,
            msg_id = 9999,
        )

        # Only report the result of the last sub-operation
        last = None
        
        for (result, identifier) in responses:
            if result:
                last = result
            else:
                assoc.release()
                raise Exception('Connection timed out, was aborted or received invalid response')

        assoc.release()
        return last
    else:
        raise Exception('Association rejected, aborted or never connected')





##
## The tests
##
## IMPORTANT RESOURCES:
## http://dicom.nema.org/medical/dicom/current/output/chtml/part04/sect_C.4.3.html#table_C.4-3
## http://dicom.nema.org/medical/dicom/current/output/chtml/part04/sect_C.4.3.3.html
##


def DefaultCallback(event):
    to_match = PatientRootQueryRetrieveInformationModelGet
    cxs = [cx for cx in event.assoc.accepted_contexts if cx.abstract_syntax == to_match]
    if len(cxs) != 1:
        raise Exception()
    else:
        return 0x0000



class Orthanc(unittest.TestCase):
    def setUp(self):
        if (sys.version_info >= (3, 0)):
            # Remove annoying warnings about unclosed socket in Python 3
            import warnings
            warnings.simplefilter('ignore', ResourceWarning)

        DropOrthanc(ORTHANC)

        
    def test_success(self):
        UploadInstance(ORTHANC, 'Brainix/Epi/IM-0001-0001.dcm')
        UploadInstance(ORTHANC, 'Brainix/Flair/IM-0001-0001.dcm')
        
        dataset = Dataset()
        dataset.QueryRetrieveLevel = 'STUDY'
        dataset.StudyInstanceUID = '2.16.840.1.113669.632.20.1211.10000357775'

        result = ExecuteCGet(ORTHANC, dataset, MRImageStorage, DefaultCallback)

        self.assertEqual(0x0000, result[0x00000900].value)  # Status - Success
        self.assertEqual(2, result[0x00001021].value)  # Completed sub-operations
        self.assertEqual(0, result[0x00001022].value)  # Failed sub-operations
        self.assertEqual(0, result[0x00001023].value)  # Warning sub-operations

        # "Warning, Failure, or Success shall not contain the Number
        # of Remaining Sub-operations Attribute."
        self.assertFalse(0x00001020 in result)  # Remaining sub-operations


    def test_some_failure(self):
        # Failure in 1 on 2 images
        def Callback(event):
            Callback.count += 1

            if Callback.count == 1:
                return 0xA702   # Refused: Out of resources - Unable to perform sub-operations
            elif Callback.count == 2:
                return 0x0000
            else:
                raise Exception('')

        Callback.count = 0  # Static variable of function "Callback"

        UploadInstance(ORTHANC, 'Brainix/Epi/IM-0001-0001.dcm')
        UploadInstance(ORTHANC, 'Brainix/Epi/IM-0001-0002.dcm')
        
        dataset = Dataset()
        dataset.QueryRetrieveLevel = 'STUDY'
        dataset.StudyInstanceUID = '2.16.840.1.113669.632.20.1211.10000357775'

        result = ExecuteCGet(ORTHANC, dataset, MRImageStorage, Callback)

        # Fixed in Orthanc 1.8.1. "From what I read from the DICOM
        # standard the C-GET should at least return a warning
        # (0xB000), see C.4.3.1.4 Status as one or more sub-operations
        # failed."
        # https://groups.google.com/g/orthanc-users/c/tS826iEzHb0/m/KzHZk61tAgAJ
        # https://github.com/pydicom/pynetdicom/issues/552#issuecomment-712477451

        self.assertEqual(0xB000, result[0x00000900].value)  # Status - One or more Failures or Warnings
        self.assertEqual(1, result[0x00001021].value)  # Completed sub-operations
        self.assertEqual(1, result[0x00001022].value)  # Failed sub-operations
        self.assertEqual(0, result[0x00001023].value)  # Warning sub-operations

        # "Warning, Failure, or Success shall not contain the Number
        # of Remaining Sub-operations Attribute."
        self.assertFalse(0x00001020 in result)  # Remaining sub-operations

        
    def test_all_failure(self):
        def Callback(event):
            return 0xA702   # Refused: Out of resources - Unable to perform sub-operations

        UploadInstance(ORTHANC, 'Brainix/Epi/IM-0001-0001.dcm')
        UploadInstance(ORTHANC, 'Brainix/Epi/IM-0001-0002.dcm')
        
        dataset = Dataset()
        dataset.QueryRetrieveLevel = 'STUDY'
        dataset.StudyInstanceUID = '2.16.840.1.113669.632.20.1211.10000357775'

        result = ExecuteCGet(ORTHANC, dataset, MRImageStorage, Callback)

        # Must return "Failure or Refused if all sub-operations were unsuccessful"
        # http://dicom.nema.org/medical/dicom/current/output/chtml/part04/sect_C.4.3.3.html

        self.assertEqual(0xA702, result[0x00000900].value)  # Status - Unable to perform sub-operations
        self.assertEqual(0, result[0x00001021].value)  # Completed sub-operations
        self.assertEqual(2, result[0x00001022].value)  # Failed sub-operations
        self.assertEqual(0, result[0x00001023].value)  # Warning sub-operations

        # "Warning, Failure, or Success shall not contain the Number
        # of Remaining Sub-operations Attribute."
        self.assertFalse(0x00001020 in result)  # Remaining sub-operations


    def test_warning(self):
        def Callback(event):
            return 0xB000   # Sub-operations Complete - One or more Failures or Warnings

        UploadInstance(ORTHANC, 'Brainix/Epi/IM-0001-0001.dcm')
        
        dataset = Dataset()
        dataset.QueryRetrieveLevel = 'STUDY'
        dataset.StudyInstanceUID = '2.16.840.1.113669.632.20.1211.10000357775'

        result = ExecuteCGet(ORTHANC, dataset, MRImageStorage, Callback)

        self.assertEqual(0xB000, result[0x00000900].value)  # Status - One or more Failures or Warnings
        self.assertEqual(0, result[0x00001021].value)  # Completed sub-operations
        self.assertEqual(0, result[0x00001022].value)  # Failed sub-operations
        self.assertEqual(1, result[0x00001023].value)  # Warning sub-operations

        # "Warning, Failure, or Success shall not contain the Number
        # of Remaining Sub-operations Attribute."
        self.assertFalse(0x00001020 in result)  # Remaining sub-operations

        
    def test_missing(self):
        dataset = Dataset()
        dataset.QueryRetrieveLevel = 'STUDY'
        dataset.StudyInstanceUID = 'nope'

        result = ExecuteCGet(ORTHANC, dataset, UltrasoundImageStorage, DefaultCallback)

        self.assertEqual(0xC000, result[0x00000900].value)  # Status - Failed: Unable to process
        self.assertEqual(0, result[0x00001021].value)  # Completed sub-operations
        self.assertEqual(0, result[0x00001022].value)  # Failed sub-operations
        self.assertEqual(0, result[0x00001023].value)  # Warning sub-operations

        # "Warning, Failure, or Success shall not contain the Number
        # of Remaining Sub-operations Attribute."
        self.assertFalse(0x00001020 in result)  # Remaining sub-operations

        
    def test_cancel(self):
        # Fixed in Orthanc 1.8.1.
        # https://groups.google.com/g/orthanc-users/c/tS826iEzHb0/m/QbPw6XPZAgAJ
        # https://github.com/pydicom/pynetdicom/issues/553#issuecomment-713164041
        
        def Callback(event):
            Callback.count += 1

            if Callback.count == 1:
                return 0x0000
            elif Callback.count == 2:
                to_match = PatientRootQueryRetrieveInformationModelGet
                cxs = [cx for cx in event.assoc.accepted_contexts if cx.abstract_syntax == to_match]
                cx_id = cxs[0].context_id
                event.assoc.send_c_cancel(9999, cx_id)
                return 0x0000   # Success
            else:
                raise Exception('')

        Callback.count = 0  # Static variable of function "Callback"
        
        UploadInstance(ORTHANC, 'Brainix/Epi/IM-0001-0001.dcm')
        UploadInstance(ORTHANC, 'Brainix/Epi/IM-0001-0002.dcm')
        UploadInstance(ORTHANC, 'Brainix/Flair/IM-0001-0001.dcm')
        
        dataset = Dataset()
        dataset.QueryRetrieveLevel = 'STUDY'
        dataset.StudyInstanceUID = '2.16.840.1.113669.632.20.1211.10000357775'

        result = ExecuteCGet(ORTHANC, dataset, MRImageStorage, Callback)

        self.assertEqual(0xfe00, result[0x00000900].value)  # Status - Sub-operations terminated due to Cancel Indication
        self.assertEqual(2, result[0x00001020].value)  # Remaining sub-operations
        self.assertEqual(1, result[0x00001021].value)  # Completed sub-operations
        self.assertEqual(0, result[0x00001022].value)  # Failed sub-operations
        self.assertEqual(0, result[0x00001023].value)  # Warning sub-operations
        
        
        
try:
    print('\nStarting the tests...')
    unittest.main(argv = [ sys.argv[0] ] + args.options)

finally:
    print('\nDone')
