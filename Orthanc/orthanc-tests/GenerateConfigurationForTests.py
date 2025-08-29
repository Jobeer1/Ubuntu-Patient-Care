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


import argparse
import os
import re
import socket
import subprocess
import sys
import json
import sys

if sys.version_info[0] < 3:
    from urllib2 import urlopen
else:
    from urllib.request import urlopen


##
## Parse the command-line arguments
##

parser = argparse.ArgumentParser(description = 'Generate the configuration file for the ' +
                                 'instance of Orthanc to be checked against the integration tests.')

parser.add_argument('--target', 
                    default = 'IntegrationTestsConfiguration.json',
                    help = 'Configuration file to generate')

parser.add_argument('--force', 
                    help = 'Overwrite the file even if it already exists',
                    action = 'store_true')

parser.add_argument('--compression', 
                    help = 'Enable storage compression',
                    action = 'store_true')

parser.add_argument('--plugins', 
                    help = 'Add a path to a folder containing plugins')

parser.add_argument('--dicom',
                    type = int,
                    default = 4242,
                    help = 'DICOM port of the Orthanc server')

args = parser.parse_args()


##
## Check whether the file can be overwritten
##

if os.path.exists(args.target) and not args.force:
    print("""
WARNING: The file %s will be overwritten!

Are you sure ["yes" to go on]?""" % args.target)

    if sys.stdin.readline().strip() != 'yes':
        print('Aborting...')
        exit(0)


## 
## Generate the configuration file
##


# Retrieve the IP address of the localhost
ip = socket.gethostbyname(socket.gethostname())


# Download the content of the default configuration file
with open(args.target, 'wb') as f:
    url = 'https://orthanc.uclouvain.be/hg/orthanc/raw-file/default/OrthancServer/Resources/Configuration.json'
    http = urlopen(url)
    if http.getcode() != 200:
        raise Exception('Cannot download: %s' % url)
    
    f.write(http.read())
    

with open(args.target, 'r') as f:
    # Remove the C++-style comments
    nocomment = re.sub('//.*$', '', f.read(), 0, re.MULTILINE)

    # Remove the C-style comments
    nocomment = re.sub('/\*.*?\*/', '', nocomment, 0, re.DOTALL | re.MULTILINE)

    config = json.loads(nocomment)

config['DefaultEncoding'] = 'Utf8'
config['AuthenticationEnabled'] = True
config['DicomAet'] = 'ORTHANC'
config['DicomAssociationCloseDelay'] = 0
config['DicomModalities'] = {
     'orthanctest' : [ 'ORTHANCTEST', ip, 5001 ],
     'self' : [ 'ORTHANC', '127.0.0.1', 4242 ]
}
config['DicomPort'] = args.dicom
config['HttpCompressionEnabled'] = False
config['LogExportedResources'] = True
config['OrthancPeers'] = {
    'peer' : [ 'http://%s:%d/' % (ip, 5000), 'alice', 'orthanctest' ],
    'transfers-bidirectional' : {
        'Url' : 'http://localhost:8042/',
        'RemoteSelf' : 'transfers-bidirectional',
        'Username' : 'alice',
        'Password' : 'orthanctest'
    },
    'transfers-simple' : {
        'Url' : 'http://localhost:8042/',
        'Username' : 'alice',
        'Password' : 'orthanctest'
    },
    'self' : {
        'Url' : 'http://127.0.0.1:8042/',
        'Username' : 'alice',
        'Password' : 'orthanctest'
    }
}
config['RegisteredUsers'] = { 'alice' : 'orthanctest' }
config['RemoteAccessAllowed'] = True
config['OverwriteInstances'] = True
config['StableAge'] = 1
config['LimitFindInstances'] = 20
config['LimitFindResults'] = 10
config['JobsHistorySize'] = 1000
config['SynchronousCMove'] = False
config['MediaArchiveSize'] = 1
config['SaveJobs'] = False
config['ExecuteLuaEnabled'] = True
config['HttpTimeout'] = 2
config['SyncStorageArea'] = False  # For tests to run more quickly
config['WebDavEnabled'] = True
config['WebDavDeleteAllowed'] = True
config['WebDavUploadAllowed'] = True
config['StorageCompression'] = args.compression
config['CheckRevisions'] = True
config['HttpsCACertificates'] = "/etc/ssl/certs/ca-certificates.crt"   # for HTTPS lua tests (note: this path is valid only on linux !)

del config['DeidentifyLogsDicomVersion']
del config['KeepAlive']

config['Dictionary'] = {
    '00e1,10c2' : [ 'UI', 'PET-CT Multi Modality Name', 1, 1, 'ELSCINT1' ],
    '7053,1003' : [ 'ST', 'Original Image Filename', 1, 1, 'Philips PET Private Group' ],
    '4321,1012' : [ 'LO', 'RadioButton3', 1, 1, 'RadioLogic' ],     # For issue 140
    '0009,1001' : [ 'DS', 'Abnormality score', 1, 1, 'Lunit' ],     # For issue 168
    '0009,0010' : [ 'LO', 'Private data element', 1, 1, 'Lunit' ],  # For issue 168
}

config['UserMetadata'] = {
    'my-metadata': 1098
}

config['DefaultPrivateCreator'] = 'Lunit'  # For issue 168

config['DicomWeb'] = {
    'Servers' : {
        'sample' : [ 
            'http://localhost:8042/dicom-web/',
            'alice', 
            'orthanctest' 
        ]
    }
}

config['Worklists'] = {
    'Enable': True,
    'Database': os.path.abspath(os.path.join(os.path.dirname(__file__), './Database/Worklists/Working')),
}

config['PostgreSQL'] = {
    'EnableIndex' : True,
    'EnableStorage' : True,
    'Host' : 'localhost',
    'Port' : 5432,
    'Database' : 'orthanctest',
    'Username' : 'postgres',
    'Password' : 'postgres',
    'Lock' : False,
    'IndexConnectionsCount' : 5,
    'MaximumConnectionRetries' : 7,
}

config['MySQL'] = {
    'EnableIndex' : True,
    'EnableStorage' : True,
    'Host' : 'localhost',
    'Port' : 3306,
    'Database' : 'orthanctest',
    'Username' : 'root',
    'Password' : 'root',
    'UnixSocket' : '',
    'Lock' : False,
    'IndexConnectionsCount' : 5,
    'MaximumConnectionRetries' : 7,
}

config['Odbc'] = {
    'EnableIndex' : True,
    'EnableStorage' : True,
    'IndexConnectionString' : 'DSN=test',
    'StorageConnectionString' : 'DSN=storage',
    'IndexConnectionsCount' : 1,
    'MaximumConnectionRetries' : 7,
}

config['WholeSlideImaging'] = {
    'ServeMirador' : True,
    'ServeOpenSeadragon' : True,
}



# Enable case-insensitive PN (the default on versions <= 0.8.6)
config['CaseSensitivePN'] = False

if args.plugins != None:
    config['Plugins'] = [ args.plugins ]

with open(args.target, 'wt') as f:
    f.write(json.dumps(config, indent = True, sort_keys = True))
    f.write('\n')
