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
import subprocess
import unittest

from Toolbox import *


##
## Parse the command-line arguments
##

parser = argparse.ArgumentParser(description = 'Run the integration tests for DICOM TLS in Orthanc.')

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
parser.add_argument('--config-no-check-client', help = 'Create the configuration files for the "no-check-client" tests in the current folder',
                    action = 'store_true')
parser.add_argument('--config-check-client', help = 'Create the configuration files for the "check-client" tests test in the current folder',
                    action = 'store_true')
parser.add_argument('options', metavar = 'N', nargs = '*',
                    help='Arguments to Python unittest')

args = parser.parse_args()


##
## Configure the testing context
##


if args.config_no_check_client or args.config_check_client:
    def CreateCertificate(name):
        subprocess.check_call([ 'openssl', 'req', '-x509', '-nodes', '-days', '365', '-newkey', 'rsa:2048',
                                '-keyout', '%s.key' % name,
                                '-out', '%s.crt' % name,
                                '-subj', '/C=BE/CN=localhost' ])

    print('Writing configuration for the %s tests to current folder' % ('no-check-client' if args.config_no_check_client else 'check-client'))
    CreateCertificate('dicom-tls-a')
    CreateCertificate('dicom-tls-b')
    CreateCertificate('dicom-tls-c')  # Not trusted by Orthanc

    with open('dicom-tls-trusted.crt', 'w') as f:
        for i in [ 'dicom-tls-a.crt', 'dicom-tls-b.crt' ]:
            with open(i, 'r') as g:
                f.write(g.read())

    with open('dicom-tls.json', 'w') as f:
        f.write(json.dumps({
            'DicomTlsEnabled' : True,
            'DicomTlsCertificate' : 'dicom-tls-a.crt',
            'DicomTlsPrivateKey' : 'dicom-tls-a.key',
            'DicomTlsTrustedCertificates' : 'dicom-tls-trusted.crt',
            'ExecuteLuaEnabled' : True,
            'RemoteAccessAllowed' : True,
            'RegisteredUsers' : {
                'alice' : 'orthanctest'
            },
            'DicomTlsRemoteCertificateRequired' : args.config_check_client,  # New in Orthanc 1.9.3
        }))

    exit(0)


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
## The tests
##


FNULL = open(os.devnull, 'w')  # Emulates "subprocess.DEVNULL" on Python 2.7

    
# in these tests, Orthanc does not check client certificates
class OrthancNoCheckClient(unittest.TestCase):
    def setUp(self):
        if (sys.version_info >= (3, 0)):
            # Remove annoying warnings about unclosed socket in Python 3
            import warnings
            warnings.simplefilter('ignore', ResourceWarning)

        DropOrthanc(ORTHANC)

        
    def test_incoming(self):
        # No client certificate provided and client does not check server cert -> raise
        self.assertRaises(Exception, lambda: subprocess.check_call([
            FindExecutable('echoscu'),
            ORTHANC['Server'], 
            str(ORTHANC['DicomPort']),
            '-aec', 'ORTHANC',
        ], stderr = FNULL))

        # No client certificate provided and client does check server cert -> no raise
        self.assertRaises(Exception, lambda: subprocess.check_call([
            FindExecutable('echoscu'),
            ORTHANC['Server'], 
            str(ORTHANC['DicomPort']),
            '-aec', 'ORTHANC',
            '+cf', 'dicom-tls-a.crt'
        ], stderr = FNULL))

        # random client certificate provided and client does check server cert -> no raise since Orthanc does not check the client cert
        subprocess.check_call([
            FindExecutable('echoscu'),
            ORTHANC['Server'], 
            str(ORTHANC['DicomPort']),
            '-aec', 'ORTHANC',
            '+tls', 'dicom-tls-b.key', 'dicom-tls-b.crt',
            '+cf', 'dicom-tls-a.crt',
        ], stderr = FNULL)


        
    def test_outgoing_to_self(self):
        u = UploadInstance(ORTHANC, 'DummyCT.dcm') ['ID']

        # Error, as DICOM TLS is not enabled
        DoPut(ORTHANC, '/modalities/self', {
            'AET' : 'ORTHANC',
            'Host' : ORTHANC['Server'],
            'Port' : ORTHANC['DicomPort'],
            })

        self.assertRaises(Exception, lambda: DoPost(ORTHANC, '/modalities/self/store', u))

        # Retry using DICOM TLS
        DoPut(ORTHANC, '/modalities/self', {
            'AET' : 'ORTHANC',
            'Host' : ORTHANC['Server'],
            'Port' : ORTHANC['DicomPort'],
            'UseDicomTls' : True,
            })

        self.assertEqual(1, DoPost(ORTHANC, '/modalities/self/store', u) ['InstancesCount'])
        

    def test_anonymous(self):
        # Fails on Orthanc <= 1.9.2
        # https://orthanc.uclouvain.be/book/faq/dicom-tls.html#secure-tls-connections-without-certificate
        subprocess.check_call([
            FindExecutable('echoscu'),
            ORTHANC['Server'], 
            str(ORTHANC['DicomPort']),
            '-aec', 'ORTHANC',
            '--anonymous-tls',
            '+cf', 'dicom-tls-a.crt',
        ], stderr = FNULL)
        

# in these tests, Orthanc do checks client certificates
class OrthancCheckClient(unittest.TestCase):
    def setUp(self):
        if (sys.version_info >= (3, 0)):
            # Remove annoying warnings about unclosed socket in Python 3
            import warnings
            warnings.simplefilter('ignore', ResourceWarning)

        DropOrthanc(ORTHANC)

        
    def test_check_client_incoming(self):
        # client provides an untrusted certificate -> Orthanc will complain -> raise
        self.assertRaises(Exception, lambda: subprocess.check_call([
            FindExecutable('echoscu'),
            ORTHANC['Server'], 
            str(ORTHANC['DicomPort']),
            '-aec', 'ORTHANC',
            '+tls', 'dicom-tls-c.key', 'dicom-tls-c.crt',  # Not trusted by Orthanc
            '+cf', 'dicom-tls-a.crt',
        ], stderr = FNULL))

        # client provides a trusted certificate but expects another cert from Orthanc -> raise
        self.assertRaises(Exception, lambda: subprocess.check_call([
            FindExecutable('echoscu'),
            ORTHANC['Server'], 
            str(ORTHANC['DicomPort']),
            '-aec', 'ORTHANC',
            '+tls', 'dicom-tls-b.key', 'dicom-tls-b.crt',
            '+cf', 'dicom-tls-b.crt',  # Not the certificate of Orthanc
        ], stderr = FNULL))


try:
    print('\nStarting the tests...')
    unittest.main(argv = [ sys.argv[0] ] + args.options)

finally:
    print('\nDone')
