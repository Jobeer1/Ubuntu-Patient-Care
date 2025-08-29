#!/usr/bin/python

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


import re
import sys
import argparse
import subprocess
import unittest
import pprint

from Tests import *
import Toolbox


##
## Parse the command-line arguments
##

parser = argparse.ArgumentParser(description = 'Run the integration tests on some instance of Orthanc.')
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
parser.add_argument('--docker', help = 'These tests are run from Docker',
                    action = 'store_true')
parser.add_argument('--orthanc',
                    default = 'Orthanc',
                    help = 'Path to the executable of Orthanc')
parser.add_argument('options', metavar = 'N', nargs = '*',
                    help='Arguments to Python unittest')

args = parser.parse_args()

if not args.force:
    print("""
WARNING: This test will remove all the content of your
Orthanc instance running on %s!

Are you sure ["yes" to go on]?""" % args.server)

    if sys.stdin.readline().strip() != 'yes':
        print('Aborting...')
        exit(0)



## 
## Generate the configuration file for the anciliary instance of
## Orthanc
##

CONFIG = '/tmp/IntegrationTestsConfiguration.json'
subprocess.check_call([ Toolbox.FindExecutable(args.orthanc),
                        '--config=%s' % CONFIG ])

with open(CONFIG, 'rt') as f:
    config = f.read()

if args.docker and args.server == 'localhost':
    args.server = GetDockerHostAddress()

config = re.sub(r'("StorageDirectory"\s*:)\s*".*?"', r'\1 "/tmp/OrthancStorage"', config)
config = re.sub(r'("IndexDirectory"\s*:)\s*".*?"', r'\1 "/tmp/OrthancStorage"', config)
config = re.sub(r'("DicomAet"\s*:)\s*".*?"', r'\1 "ORTHANCTEST"', config)
config = re.sub(r'("DicomPort"\s*:)\s*.*?,', r'\1 5001,', config)
config = re.sub(r'("HttpPort"\s*:)\s*.*?,', r'\1 5000,', config)
config = re.sub(r'("RemoteAccessAllowed"\s*:)\s*false', r'\1 true', config)
config = re.sub(r'("AuthenticationEnabled"\s*:)\s*false,', r'', config)  # Set with "RegisteredUsers"
config = re.sub(r'("RegisteredUsers"\s*:)\s*{', r'"AuthenticationEnabled" : true, \1 { "alice" : "orthanctest"', config)
config = re.sub(r'("ExecuteLuaEnabled"\s*:)\s*false', r'\1 true', config)
config = re.sub(r'("HttpCompressionEnabled"\s*:)\s*true', r'\1 false', config)
config = re.sub(r'("DicomAssociationCloseDelay"\s*:)\s*[0-9]*', r'\1 0', config)
config = re.sub(r'("DicomModalities"\s*:)\s*{', r'\1 { "orthanc" : [ "%s", "%s", %s ]' % 
                (args.aet, args.server, args.dicom), config)

# New to test transcoding over DICOM (1.7.0)
config = re.sub(r'("RleTransferSyntaxAccepted"\s*:)\s*true', r'\1 false', config)


with open(CONFIG, 'wt') as f:
    f.write(config)

localOrthanc = ExternalCommandThread([ 
    Toolbox.FindExecutable(args.orthanc),
    CONFIG,
    #'--verbose', 
    #'--no-jobs'
    #'/home/jodogne/Subversion/Orthanc/i/Orthanc', CONFIG, '--verbose'
])


LOCAL = DefineOrthanc(aet = 'ORTHANCTEST',
                      server = 'localhost',
                      dicomPort = 5001,
                      restPort = 5000,
                      username = 'alice',
                      password = 'orthanctest')

REMOTE = DefineOrthanc(server = args.server,
                       username = args.username,
                       password = args.password,
                       aet = args.aet,
                       dicomPort = args.dicom,
                       restPort = args.rest)



print('Parameters of the instance of Orthanc being tested:')
pprint.pprint(REMOTE)
print('')


print('Waiting for the internal Orthanc to start...')
while True:
    try:
        Toolbox.DoGet(LOCAL, '/instances')
        break
    except:
        time.sleep(0.1)


try:
    print('\nStarting the tests...')
    SetOrthancParameters(LOCAL, REMOTE, args.docker)

    # Change the order of the tests
    # https://stackoverflow.com/a/4006044/881731
    # https://stackoverflow.com/a/54923706/881731

    # Reverse order
    # unittest.TestLoader.sortTestMethodsUsing = lambda _, x, y: cmp(y, x)

    # import random
    # random.seed(25)
    # unittest.TestLoader.sortTestMethodsUsing = lambda self, a, b: random.choice([1, 0, -1])
    
    unittest.main(argv = [ sys.argv[0] ] + args.options)


finally:
    print('\nDone')

    # The tests have stopped or "Ctrl-C" has been hit
    try:
        localOrthanc.stop()
    except:
        pass
