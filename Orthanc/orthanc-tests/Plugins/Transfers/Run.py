#!/usr/bin/env python3
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

class Orthanc(unittest.TestCase):
    def setUp(self):
        if (sys.version_info >= (3, 0)):
            # Remove annoying warnings about unclosed socket in Python 3
            import warnings
            warnings.simplefilter("ignore", ResourceWarning)

        DropOrthanc(ORTHANC)


    def test_list_peers(self):
        peers = DoGet(ORTHANC, '/transfers/peers')
        self.assertEqual(4, len(peers)) # "self" peer was added in Orthanc 1.7.3
        self.assertEqual('disabled', peers['peer'])
        self.assertEqual('installed', peers['transfers-simple'])
        self.assertEqual('bidirectional', peers['transfers-bidirectional'])


    def test_pull(self):
        i = UploadInstance(ORTHANC, 'DummyCT.dcm')['ID']

        a = DoPost(ORTHANC, '/transfers/pull', {
            'Compression' : 'gzip',
            'Peer' : 'transfers-simple',
            'Resources' : [
                {
                    'Level' : 'Instance',
                    'ID' : i
                },
            ],
            'Priority' : 10,
            })

        WaitJobDone(ORTHANC, a['ID'])

        b = DoGet(ORTHANC, '/jobs/%s' % a['ID'])
        self.assertEqual('PullTransfer', b['Type'])
        self.assertEqual('Success', b['State'])
        self.assertEqual(a['ID'], b['ID'])
        self.assertEqual(10, b['Priority'])

        self.assertEqual('gzip', b['Content']['Compression'])
        self.assertEqual(1, b['Content']['CompletedHttpQueries'])
        self.assertEqual('transfers-simple', b['Content']['Peer'])
        self.assertEqual(1, b['Content']['TotalInstances'])


    def test_send_push(self):
        i = UploadInstance(ORTHANC, 'DummyCT.dcm')['ID']

        a = DoPost(ORTHANC, '/transfers/send', {
            'Compression' : 'gzip',
            'Peer' : 'transfers-simple',
            'Resources' : [
                {
                    'Level' : 'Instance',
                    'ID' : i
                },
            ],
            'Priority' : -10,
            })

        WaitJobDone(ORTHANC, a['ID'])

        b = DoGet(ORTHANC, '/jobs/%s' % a['ID'])
        self.assertEqual('PushTransfer', b['Type'])
        self.assertEqual('Success', b['State'])
        self.assertEqual(a['ID'], b['ID'])
        self.assertEqual(-10, b['Priority'])

        self.assertEqual('gzip', b['Content']['Compression'])
        self.assertEqual(1, b['Content']['CompletedHttpQueries'])
        self.assertEqual('transfers-simple', b['Content']['Peer'])
        self.assertEqual(1, b['Content']['TotalInstances'])


    def test_send_bidirectional(self):
        i = UploadInstance(ORTHANC, 'DummyCT.dcm')['ID']

        a = DoPost(ORTHANC, '/transfers/send', {
            'Compression' : 'gzip',
            'Peer' : 'transfers-bidirectional',
            'Resources' : [
                {
                    'Level' : 'Instance',
                    'ID' : i
                },
            ],
            'Priority' : 42,
            })

        self.assertEqual(3, len(a))
        self.assertEqual('transfers-bidirectional', a['Peer'])
        self.assertTrue('RemoteJob' in a)
        self.assertTrue('URL' in a)

        # In this integration test, the remote peer is the same as the local peer
        WaitJobDone(ORTHANC, a['RemoteJob'])

        b = DoGet(ORTHANC, '/jobs/%s' % a['RemoteJob'])
        self.assertEqual('PullTransfer', b['Type'])
        self.assertEqual('Success', b['State'])
        self.assertEqual(a['RemoteJob'], b['ID'])
        self.assertEqual(0, b['Priority'])  # Priority is chosen by the remote peer

        self.assertEqual('gzip', b['Content']['Compression'])
        self.assertEqual(1, b['Content']['CompletedHttpQueries'])
        self.assertEqual('transfers-bidirectional', b['Content']['Peer'])
        self.assertEqual(1, b['Content']['TotalInstances'])

try:
    print('\nStarting the tests...')
    unittest.main(argv = [ sys.argv[0] ] + args.options)

finally:
    print('\nDone')
