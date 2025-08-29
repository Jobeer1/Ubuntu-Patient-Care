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


import argparse
import os
import pprint
import re
import subprocess
import sys
import tempfile
import unittest
from shutil import copyfile

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'Tests'))
from Toolbox import *


##
## Parse the command-line arguments
##

parser = argparse.ArgumentParser(description = 'Run the integration tests for the WSI Dicomizer.')

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
parser.add_argument('--dicomizer',
                    default = os.path.join(os.environ['HOME'], 'Subversion/orthanc-wsi/Applications/i/OrthancWSIDicomizer'),
                    help = 'Password to the REST API')
parser.add_argument('--to-tiff',
                    default = os.path.join(os.environ['HOME'], 'Subversion/orthanc-wsi/Applications/i/OrthancWSIDicomToTiff'),
                    help = 'Password to the REST API')
parser.add_argument('--valgrind', help = 'Use valgrind while running the DICOM-izer',
                    action = 'store_true')
parser.add_argument('--force', help = 'Do not warn the user',
                    action = 'store_true')
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
## The tests
##

ORTHANC = DefineOrthanc(server = args.server,
                        username = args.username,
                        password = args.password,
                        restPort = args.rest)

def CallCommand(command):
    prefix = []
    if args.valgrind:
        prefix = [ 'valgrind' ]
    
    log = subprocess.check_output(prefix + command,
                                  stderr=subprocess.STDOUT)

    if sys.version_info >= (3, 0):
        log = log.decode('ascii')

    # If using valgrind, only print the lines from the log starting
    # with '==' (they contain the report from valgrind)
    if args.valgrind:
        print('\n'.join(filter(lambda x: x.startswith('=='), log.splitlines())))

        
def CallDicomizer(suffix):
    CallCommand([ args.dicomizer,
                  '--orthanc=http://%s:%s' % (args.server, args.rest),
                  '--username=%s' % args.username,
                  '--password=%s' % args.password ] + suffix
                  )

    
def CallDicomToTiff(suffix):
    CallCommand([ args.to_tiff,
                  '--orthanc=http://%s:%s' % (args.server, args.rest),
                  '--username=%s' % args.username,
                  '--password=%s' % args.password ] + suffix)


def CallTiffInfoOnSeries(series):
    with tempfile.NamedTemporaryFile(delete = False) as temp:
        temp.close()
        CallDicomToTiff([ series, temp.name ])
        try:
            tiff = subprocess.check_output([ 'tiffinfo', temp.name ])
        except:
            print('\ntiffinfo is probably not installed => sudo apt-get install libtiff-tools\n')
            tiff = None

        if (tiff != None and sys.version_info >= (3, 0)):
            tiff = tiff.decode('ascii')
            
        os.unlink(temp.name)

    return tiff


def IsWhite(self, image):
    e = image.getextrema()
    self.assertEqual(3, len(e))
    return e == ((255, 255), (255, 255), (255, 255))


class Orthanc(unittest.TestCase):
    def setUp(self):
        if (sys.version_info >= (3, 0)):
            # Remove annoying warnings about unclosed socket in Python 3
            import warnings
            warnings.simplefilter("ignore", ResourceWarning)

        DropOrthanc(ORTHANC)


    def test_single(self):
        CallDicomizer([ GetDatabasePath('Lena.jpg') ])

        i = DoGet(ORTHANC, '/instances')
        self.assertEqual(1, len(i))

        tags = DoGet(ORTHANC, '/instances/%s/tags?simplify' % i[0])
        self.assertEqual(1, int(tags['NumberOfFrames']))
        self.assertEqual(512, int(tags['Columns']))
        self.assertEqual(512, int(tags['Rows']))
        self.assertEqual('YBR_FULL_422', tags['PhotometricInterpretation'])
        
        s = DoGet(ORTHANC, '/series')
        self.assertEqual(1, len(s))

        pyramid = DoGet(ORTHANC, '/wsi/pyramids/%s' % s[0])
        self.assertEqual(s[0], pyramid['ID'])
        self.assertEqual(1, len(pyramid['Resolutions']))
        self.assertEqual(1, len(pyramid['Sizes']))
        self.assertEqual(1, len(pyramid['TilesCount']))
        self.assertEqual(1, pyramid['Resolutions'][0])
        self.assertEqual(512, pyramid['Sizes'][0][0])
        self.assertEqual(512, pyramid['Sizes'][0][1])
        self.assertEqual(1, len(pyramid['TilesSizes']))
        self.assertEqual(2, len(pyramid['TilesSizes'][0]))
        self.assertEqual(512, pyramid['TilesSizes'][0][0])
        self.assertEqual(512, pyramid['TilesSizes'][0][1])
        self.assertEqual(512, pyramid['TotalWidth'])
        self.assertEqual(512, pyramid['TotalHeight'])
        self.assertEqual(1, pyramid['TilesCount'][0][0])
        self.assertEqual(1, pyramid['TilesCount'][0][1])

        tiff = CallTiffInfoOnSeries(s[0])
        p = list(filter(lambda x: 'Photometric Interpretation' in x, tiff.splitlines()))
        self.assertEqual(1, len(p))
        self.assertTrue('YCbCr' in p[0])


    def test_grayscale_pyramid(self):
        CallDicomizer([ GetDatabasePath('LenaGrayscale.png'), '--tile-width=64', '--tile-height=64' ])

        i = DoGet(ORTHANC, '/instances')
        self.assertEqual(4, len(i))

        for j in range(4):
            tags = DoGet(ORTHANC, '/instances/%s/tags?simplify' % i[j])
            self.assertEqual(64, int(tags['Columns']))
            self.assertEqual(64, int(tags['Rows']))
            self.assertEqual('MONOCHROME2', tags['PhotometricInterpretation'])
        
        s = DoGet(ORTHANC, '/series')
        self.assertEqual(1, len(s))

        pyramid = DoGet(ORTHANC, '/wsi/pyramids/%s' % s[0])
        self.assertEqual(s[0], pyramid['ID'])
        self.assertEqual(4, len(pyramid['Resolutions']))
        self.assertEqual(4, len(pyramid['Sizes']))
        self.assertEqual(4, len(pyramid['TilesCount']))
        self.assertEqual(4, len(pyramid['TilesSizes']))

        self.assertEqual(1, pyramid['Resolutions'][0])
        self.assertEqual(2, pyramid['Resolutions'][1])
        self.assertEqual(4, pyramid['Resolutions'][2])
        self.assertEqual(8, pyramid['Resolutions'][3])
        self.assertEqual(512, pyramid['Sizes'][0][0])
        self.assertEqual(512, pyramid['Sizes'][0][1])
        self.assertEqual(256, pyramid['Sizes'][1][0])
        self.assertEqual(256, pyramid['Sizes'][1][1])
        self.assertEqual(128, pyramid['Sizes'][2][0])
        self.assertEqual(128, pyramid['Sizes'][2][1])
        self.assertEqual(64, pyramid['Sizes'][3][0])
        self.assertEqual(64, pyramid['Sizes'][3][1])
        for i in range(4):
            self.assertEqual(2, len(pyramid['TilesSizes'][i]))
            self.assertEqual(64, pyramid['TilesSizes'][i][0])
            self.assertEqual(64, pyramid['TilesSizes'][i][1])
        self.assertEqual(512, pyramid['TotalWidth'])
        self.assertEqual(512, pyramid['TotalHeight'])
        self.assertEqual(8, pyramid['TilesCount'][0][0])
        self.assertEqual(8, pyramid['TilesCount'][0][1])
        self.assertEqual(4, pyramid['TilesCount'][1][0])
        self.assertEqual(4, pyramid['TilesCount'][1][1])
        self.assertEqual(2, pyramid['TilesCount'][2][0])
        self.assertEqual(2, pyramid['TilesCount'][2][1])
        self.assertEqual(1, pyramid['TilesCount'][3][0])
        self.assertEqual(1, pyramid['TilesCount'][3][1])

        tiff = CallTiffInfoOnSeries(s[0])
        p = list(filter(lambda x: 'Photometric Interpretation' in x, tiff.splitlines()))
        self.assertEqual(4, len(p))
        for j in range(4):
            self.assertTrue('min-is-black' in p[j])


    def test_import_tiff_grayscale(self):
        CallDicomizer([ GetDatabasePath('WSI/LenaGrayscaleJpeg.tiff') ])

        s = DoGet(ORTHANC, '/series')
        self.assertEqual(1, len(s))

        pyramid = DoGet(ORTHANC, '/wsi/pyramids/%s' % s[0])
        self.assertEqual(4, len(pyramid['Resolutions']))

        tiff = CallTiffInfoOnSeries(s[0])
        p = list(filter(lambda x: 'Photometric Interpretation' in x, tiff.splitlines()))
        self.assertEqual(4, len(p))
        for j in range(4):
            self.assertTrue('min-is-black' in p[j])

            
    def test_import_tiff_ycbcr(self):
        CallDicomizer([ GetDatabasePath('WSI/LenaColorJpegYCbCr.tiff') ])

        s = DoGet(ORTHANC, '/series')
        self.assertEqual(1, len(s))

        pyramid = DoGet(ORTHANC, '/wsi/pyramids/%s' % s[0])
        self.assertEqual(4, len(pyramid['Resolutions']))

        tiff = CallTiffInfoOnSeries(s[0])
        p = list(filter(lambda x: 'Photometric Interpretation' in x, tiff.splitlines()))
        self.assertEqual(4, len(p))
        for j in range(4):
            self.assertTrue('YCbCr' in p[j])


    def test_import_tiff_rgb(self):
        CallDicomizer([ GetDatabasePath('WSI/LenaColorJpegRGB.tiff') ])

        s = DoGet(ORTHANC, '/series')
        self.assertEqual(1, len(s))

        pyramid = DoGet(ORTHANC, '/wsi/pyramids/%s' % s[0])
        self.assertEqual(4, len(pyramid['Resolutions']))

        tiff = CallTiffInfoOnSeries(s[0])
        p = list(filter(lambda x: 'Photometric Interpretation' in x, tiff.splitlines()))
        self.assertEqual(4, len(p))
        for j in range(4):
            self.assertTrue('RGB' in p[j])


    def test_concatenation(self):
        # https://orthanc.uclouvain.be/bugs/show_bug.cgi?id=145
        CallDicomizer([ GetDatabasePath('LenaGrayscale.png'), '--levels=1', ])
        i = DoGet(ORTHANC, '/instances')
        self.assertEqual(1, len(i))
        tags = DoGet(ORTHANC, '/instances/%s/tags?short' % i[0])
        self.assertTrue('0020,0242' in tags)  # SOP Instance UID of Concatenation Source
        self.assertTrue('0020,9161' in tags)  # Concatenation UID
        self.assertTrue('0020,9162' in tags)  # In-concatenation Number
        self.assertTrue('0020,9228' in tags)  # Concatenation Frame Offset Number
        self.assertEqual('1', tags['0020,9162'])
        self.assertEqual('0', tags['0020,9228'])

        DropOrthanc(ORTHANC)

        # "--max-size" disables the concatenation
        CallDicomizer([ GetDatabasePath('LenaGrayscale.png'), '--levels=1', '--max-size=0' ])
        i = DoGet(ORTHANC, '/instances')
        self.assertEqual(1, len(i))
        tags = DoGet(ORTHANC, '/instances/%s/tags?short' % i[0])
        self.assertFalse('0020,0242' in tags)
        self.assertFalse('0020,9161' in tags)
        self.assertFalse('0020,9162' in tags)
        self.assertFalse('0020,9228' in tags)
            
        DropOrthanc(ORTHANC)

        # This creates a series with 2 instances of roughly 1.5MB (= 2 frames x 512 x 512 x 3 (RGB24) + DICOM overhead)
        CallDicomizer([ GetDatabasePath('WSI/Lena2x2.png'), '--levels=1', '--max-size=1', '--compression=none' ])
        i = DoGet(ORTHANC, '/instances')
        self.assertEqual(2, len(i))
        t1 = DoGet(ORTHANC, '/instances/%s/tags?short' % i[0])
        t2 = DoGet(ORTHANC, '/instances/%s/tags?short' % i[1])
        self.assertTrue('0020,0242' in t1)
        self.assertTrue('0020,9161' in t1)
        self.assertTrue('0020,9162' in t1)
        self.assertTrue('0020,9228' in t1)
        self.assertEqual(t1['0020,0242'], t2['0020,0242'])
        self.assertEqual(t1['0020,9161'], t2['0020,9161'])
        if t1['0020,9162'] == '1':
            self.assertEqual('1', t1['0020,9162'])
            self.assertEqual('0', t1['0020,9228'])
            self.assertEqual('2', t2['0020,9162'])
            self.assertEqual('2', t2['0020,9228'])
        else:
            self.assertEqual('1', t2['0020,9162'])
            self.assertEqual('0', t2['0020,9228'])
            self.assertEqual('2', t1['0020,9162'])
            self.assertEqual('2', t1['0020,9228'])


    def test_pixel_spacing(self):
        # https://orthanc.uclouvain.be/bugs/show_bug.cgi?id=139
        CallDicomizer([ GetDatabasePath('LenaGrayscale.png'),  # Image is 512x512
                        '--levels=4', '--tile-width=64', '--tile-height=64', '--max-size=0',
                        '--imaged-width=20', '--imaged-height=10' ])

        instances = DoGet(ORTHANC, '/instances')
        self.assertEqual(4, len(instances))

        spacings = {}
        for i in instances:
            t = DoGet(ORTHANC, '/instances/%s/tags?short' % i)
            spacings[t['0028,0008']] = t['5200,9229'][0]['0028,9110'][0]['0028,0030']

        self.assertEqual(4, len(spacings))
        for i in range(4):
            s = spacings[str(4 ** i)].split('\\')
            self.assertEqual(2, len(s))
            self.assertEqual(20.0 / 512.0 * (2.0 ** (3 - i)), float(s[0])) 
            self.assertEqual(10.0 / 512.0 * (2.0 ** (3 - i)), float(s[1])) 


    def test_http_accept(self):
        # https://discourse.orthanc-server.org/t/orthanc-wsi-image-quality-issue/3331

        def TestTransferSyntax(s, expected):
            instance = DoGet(ORTHANC, '/series/%s' % s[0]) ['Instances'][0]
            self.assertEqual(expected, DoGet(ORTHANC, '/instances/%s/metadata/TransferSyntax' % instance))
        
        def TestDefaultAccept(s, mime):
            tile = GetImage(ORTHANC, '/wsi/tiles/%s/0/0/0' % s[0])
            self.assertEqual(mime, tile.format)

            tile = GetImage(ORTHANC, '/wsi/tiles/%s/0/0/0' % s[0], {
                'Accept' : 'text/html,*/*'
            })
            self.assertEqual(mime, tile.format)

            tile = GetImage(ORTHANC, '/wsi/tiles/%s/0/0/0' % s[0], {
                'Accept' : 'image/*,text/html'
            })
            self.assertEqual(mime, tile.format)

            tile = DoGetRaw(ORTHANC, '/wsi/tiles/%s/0/0/0' % s[0], headers = {
                'Accept' : 'text/html'
            })
            self.assertEqual(406, int(tile[0]['status']))

        def TestForceAccept(s):
            tile = GetImage(ORTHANC, '/wsi/tiles/%s/0/0/0' % s[0], {
                'Accept' : 'image/jpeg'
            })
            self.assertEqual('JPEG', tile.format)

            tile = GetImage(ORTHANC, '/wsi/tiles/%s/0/0/0' % s[0], {
                'Accept' : 'image/png'
            })
            self.assertEqual('PNG', tile.format)

            tile = GetImage(ORTHANC, '/wsi/tiles/%s/0/0/0' % s[0], {
                'Accept' : 'image/jp2'
            })
            self.assertEqual('JPEG2000', tile.format)


        CallDicomizer([ GetDatabasePath('Lena.jpg') ])
        
        s = DoGet(ORTHANC, '/series')
        self.assertEqual(1, len(s))
        TestTransferSyntax(s, '1.2.840.10008.1.2.4.50')
        TestDefaultAccept(s, 'JPEG')
        TestForceAccept(s)

        DoDelete(ORTHANC, '/series/%s' % s[0])

        CallDicomizer([ GetDatabasePath('Lena.jpg'), '--compression', 'none' ])
        s = DoGet(ORTHANC, '/series')
        self.assertEqual(1, len(s))

        TestTransferSyntax(s, '1.2.840.10008.1.2')
        TestDefaultAccept(s, 'PNG')
        TestForceAccept(s)

        DoDelete(ORTHANC, '/series/%s' % s[0])

        CallDicomizer([ GetDatabasePath('Lena.jpg'), '--compression', 'jpeg2000' ])
        s = DoGet(ORTHANC, '/series')
        self.assertEqual(1, len(s))

        TestTransferSyntax(s, '1.2.840.10008.1.2.4.90')
        TestDefaultAccept(s, 'PNG')
        TestForceAccept(s)
        
    def test_iiif(self):
        CallDicomizer([ GetDatabasePath('LenaGrayscale.png'),  # Image is 512x512
                        '--levels=3', '--tile-width=128', '--tile-height=128' ])

        self.assertEqual(3, len(DoGet(ORTHANC, '/instances')))

        s = DoGet(ORTHANC, '/series')
        self.assertEqual(1, len(s))

        uri = '/wsi/iiif/tiles/%s' % s[0]
        info = DoGet(ORTHANC, '%s/info.json' % uri)
        self.assertEqual('http://iiif.io/api/image/3/context.json', info['@context'])
        self.assertEqual('http://iiif.io/api/image', info['protocol'])
        self.assertEqual('http://localhost:8042%s' % uri, info['id'])
        self.assertEqual('level0', info['profile'])
        self.assertEqual('ImageService3', info['type'])
        self.assertEqual(512, info['width'])
        self.assertEqual(512, info['height'])

        self.assertEqual(3, len(info['sizes']))
        
        if IsPluginVersionAtLeast(ORTHANC, "wsi", 2, 1, 0):   # https://orthanc.uclouvain.be/hg/orthanc-wsi/rev/9dc7f1e8716d
            self.assertEqual(512, info['sizes'][2]['width'])
            self.assertEqual(512, info['sizes'][2]['height'])
            self.assertEqual(256, info['sizes'][1]['width'])
            self.assertEqual(256, info['sizes'][1]['height'])
            self.assertEqual(128, info['sizes'][0]['width'])
            self.assertEqual(128, info['sizes'][0]['height'])
        else:
            self.assertEqual(512, info['sizes'][0]['width'])
            self.assertEqual(512, info['sizes'][0]['height'])
            self.assertEqual(256, info['sizes'][1]['width'])
            self.assertEqual(256, info['sizes'][1]['height'])
            self.assertEqual(128, info['sizes'][2]['width'])
            self.assertEqual(128, info['sizes'][2]['height'])

        self.assertEqual(1, len(info['tiles']))
        self.assertEqual(128, info['tiles'][0]['width'])
        self.assertEqual(128, info['tiles'][0]['height'])
        self.assertEqual([ 1, 2, 4 ], info['tiles'][0]['scaleFactors'])

        # The list of URIs below was generated by "orthanc-wsi/Resources/TestIIIFTiles.py"

        # Level 0
        GetImage(ORTHANC, '/%s/0,0,128,128/128,128/0/default.jpg' % uri)
        GetImage(ORTHANC, '/%s/128,0,128,128/128,128/0/default.jpg' % uri)
        GetImage(ORTHANC, '/%s/256,0,128,128/128,128/0/default.jpg' % uri)
        GetImage(ORTHANC, '/%s/384,0,128,128/128,128/0/default.jpg' % uri)
        GetImage(ORTHANC, '/%s/0,128,128,128/128,128/0/default.jpg' % uri)
        GetImage(ORTHANC, '/%s/128,128,128,128/128,128/0/default.jpg' % uri)
        GetImage(ORTHANC, '/%s/256,128,128,128/128,128/0/default.jpg' % uri)
        GetImage(ORTHANC, '/%s/384,128,128,128/128,128/0/default.jpg' % uri)
        GetImage(ORTHANC, '/%s/0,256,128,128/128,128/0/default.jpg' % uri)
        GetImage(ORTHANC, '/%s/128,256,128,128/128,128/0/default.jpg' % uri)
        GetImage(ORTHANC, '/%s/256,256,128,128/128,128/0/default.jpg' % uri)
        GetImage(ORTHANC, '/%s/384,256,128,128/128,128/0/default.jpg' % uri)
        GetImage(ORTHANC, '/%s/0,384,128,128/128,128/0/default.jpg' % uri)
        GetImage(ORTHANC, '/%s/128,384,128,128/128,128/0/default.jpg' % uri)
        GetImage(ORTHANC, '/%s/256,384,128,128/128,128/0/default.jpg' % uri)
        GetImage(ORTHANC, '/%s/384,384,128,128/128,128/0/default.jpg' % uri)

        # Level 1
        GetImage(ORTHANC, '/%s/0,0,256,256/128,128/0/default.jpg' % uri)
        GetImage(ORTHANC, '/%s/256,0,256,256/128,128/0/default.jpg' % uri)
        GetImage(ORTHANC, '/%s/0,256,256,256/128,128/0/default.jpg' % uri)
        GetImage(ORTHANC, '/%s/256,256,256,256/128,128/0/default.jpg' % uri)

        # Level 2
        i = GetImage(ORTHANC, '/%s/0,0,512,512/128,128/0/default.jpg' % uri)
        self.assertEqual(128, i.width)
        self.assertEqual(128, i.height)

        uri2 = '/wsi/iiif/series/%s/manifest.json' % s[0]
        manifest = DoGet(ORTHANC, uri2)
        self.assertEqual('http://iiif.io/api/presentation/3/context.json', manifest['@context'])
        self.assertEqual('http://localhost:8042%s' % uri2, manifest['id'])

        self.assertEqual(1, len(manifest['items']))
        self.assertEqual(1, len(manifest['items'][0]['items']))
        self.assertEqual(1, len(manifest['items'][0]['items'][0]['items']))

        self.assertEqual('Manifest', manifest['type'])
        self.assertEqual('Canvas', manifest['items'][0]['type'])
        self.assertEqual('AnnotationPage', manifest['items'][0]['items'][0]['type'])
        self.assertEqual('Annotation', manifest['items'][0]['items'][0]['items'][0]['type'])

        self.assertEqual(512, manifest['items'][0]['width'])
        self.assertEqual(512, manifest['items'][0]['height'])

        body = manifest['items'][0]['items'][0]['items'][0]['body']
        self.assertEqual(1, len(body['service']))
        self.assertEqual('image/jpeg', body['format'])
        self.assertEqual('Image', body['type'])
        self.assertEqual(512, body['width'])
        self.assertEqual(512, body['height'])
        self.assertEqual('level0', body['service'][0]['profile'])
        self.assertEqual('ImageService3', body['service'][0]['type'])
        self.assertEqual('http://localhost:8042%s' % uri, body['service'][0]['id'])

    def test_iiif_radiology(self):
        a = UploadInstance(ORTHANC, 'ColorTestMalaterre.dcm') ['ID']
        b = UploadInstance(ORTHANC, 'Multiframe.dcm') ['ID']
        c = UploadInstance(ORTHANC, 'Brainix/Epi/IM-0001-0001.dcm') ['ID']
        d = UploadInstance(ORTHANC, 'Brainix/Epi/IM-0001-0002.dcm') ['ID']

        s1 = DoGet(ORTHANC, '/instances/%s/series' % a) ['ID']
        s2 = DoGet(ORTHANC, '/instances/%s/series' % b) ['ID']
        s3 = DoGet(ORTHANC, '/instances/%s/series' % c) ['ID']

        manifest = DoGet(ORTHANC, '/wsi/iiif/series/%s/manifest.json' % s1)
        self.assertEqual(1, len(manifest['items']))

        manifest = DoGet(ORTHANC, '/wsi/iiif/series/%s/manifest.json' % s2)
        self.assertEqual(76, len(manifest['items']))

        manifest = DoGet(ORTHANC, '/wsi/iiif/series/%s/manifest.json' % s3)
        self.assertEqual(2, len(manifest['items']))

        for (i, width, height) in [ (a, 41, 41),
                                    (b, 512, 512),
                                    (c, 256, 256),
                                    (d, 256, 256) ]:
            uri = '/wsi/iiif/frames/%s/0' % i
            info = DoGet(ORTHANC, uri + '/info.json')
            self.assertEqual(8, len(info))
            self.assertEqual('http://iiif.io/api/image/3/context.json', info['@context'])
            self.assertEqual('http://iiif.io/api/image', info['protocol'])
            self.assertEqual('http://localhost:8042%s' % uri, info['id'])
            self.assertEqual('level0', info['profile'])
            self.assertEqual('ImageService3', info['type'])
            self.assertEqual(width, info['width'])
            self.assertEqual(height, info['height'])
            self.assertEqual(1, len(info['tiles']))
            self.assertEqual(3, len(info['tiles'][0]))
            self.assertEqual(width, info['tiles'][0]['width'])
            self.assertEqual(height, info['tiles'][0]['height'])
            self.assertEqual([ 1 ], info['tiles'][0]['scaleFactors'])

    def test_on_the_fly(self):
        a = UploadInstance(ORTHANC, 'Implicit-vr-us-palette.dcm') ['ID']

        self.assertRaises(Exception, lambda: DoGet(ORTHANC, '/wsi/frames-pyramids/%s/1' % a))

        info = DoGet(ORTHANC, '/wsi/frames-pyramids/%s/0' % a)
        self.assertEqual('#ffffff', info['BackgroundColor'])
        self.assertEqual(0, info['FrameNumber'])
        self.assertEqual(a, info['ID'])
        self.assertEqual(2, len(info['Resolutions']))
        self.assertEqual(1, info['Resolutions'][0])
        self.assertEqual(2, info['Resolutions'][1])
        self.assertEqual(2, len(info['Sizes']))
        self.assertEqual(832, info['Sizes'][0][0])  # Default padding is (64,64) for an image size (800,600)
        self.assertEqual(640, info['Sizes'][0][1])
        self.assertEqual(416, info['Sizes'][1][0])
        self.assertEqual(320, info['Sizes'][1][1])
        self.assertEqual(2, info['TilesCount'][0][0])
        self.assertEqual(2, info['TilesCount'][0][1])
        self.assertEqual(1, info['TilesCount'][1][0])
        self.assertEqual(1, info['TilesCount'][1][1])
        self.assertEqual(512, info['TilesSizes'][0][0])
        self.assertEqual(512, info['TilesSizes'][0][1])
        self.assertEqual(512, info['TilesSizes'][1][0])
        self.assertEqual(512, info['TilesSizes'][1][1])
        self.assertEqual(832, info['TotalWidth'])
        self.assertEqual(640, info['TotalHeight'])

        tile = GetImage(ORTHANC, '/wsi/frames-tiles/%s/0/0/0/0' % a)
        self.assertEqual((512, 512), tile.size)
        self.assertFalse(IsWhite(self, tile))
        tile = GetImage(ORTHANC, '/wsi/frames-tiles/%s/0/0/1/0' % a)
        self.assertEqual((512, 512), tile.size)
        self.assertFalse(IsWhite(self, tile))
        tile = GetImage(ORTHANC, '/wsi/frames-tiles/%s/0/0/0/1' % a)
        self.assertEqual((512, 512), tile.size)
        self.assertFalse(IsWhite(self, tile))
        tile = GetImage(ORTHANC, '/wsi/frames-tiles/%s/0/0/1/1' % a)
        self.assertEqual((512, 512), tile.size)
        self.assertFalse(IsWhite(self, tile))
        tile = GetImage(ORTHANC, '/wsi/frames-tiles/%s/0/0/1/2' % a)
        self.assertEqual((512, 512), tile.size)
        self.assertTrue(IsWhite(self, tile))
        tile = GetImage(ORTHANC, '/wsi/frames-tiles/%s/0/0/2/1' % a)
        self.assertEqual((512, 512), tile.size)
        self.assertTrue(IsWhite(self, tile))
        tile = GetImage(ORTHANC, '/wsi/frames-tiles/%s/0/0/2/2' % a)
        self.assertEqual((512, 512), tile.size)
        self.assertTrue(IsWhite(self, tile))
        tile = GetImage(ORTHANC, '/wsi/frames-tiles/%s/0/1/0/0' % a)
        self.assertEqual((512, 512), tile.size)
        self.assertFalse(IsWhite(self, tile))
        tile = GetImage(ORTHANC, '/wsi/frames-tiles/%s/0/1/0/1' % a)
        self.assertEqual((512, 512), tile.size)
        self.assertTrue(IsWhite(self, tile))
        tile = GetImage(ORTHANC, '/wsi/frames-tiles/%s/0/1/1/0' % a)
        self.assertEqual((512, 512), tile.size)
        self.assertTrue(IsWhite(self, tile))
        tile = GetImage(ORTHANC, '/wsi/frames-tiles/%s/0/1/1/1' % a)
        self.assertEqual((512, 512), tile.size)
        self.assertTrue(IsWhite(self, tile))

    def test_iiif_on_the_fly(self):
        a = UploadInstance(ORTHANC, 'Implicit-vr-us-palette.dcm') ['ID']

        uri = '/wsi/iiif/frames-pyramids/%s/0' % a
        manifest = DoGet(ORTHANC, uri + '/manifest.json')

        self.assertEqual('http://iiif.io/api/presentation/3/context.json', manifest['@context'])
        self.assertEqual('http://localhost:8042%s/manifest.json' % uri, manifest['id'])

        self.assertEqual(1, len(manifest['items']))
        self.assertEqual(1, len(manifest['items'][0]['items']))
        self.assertEqual(1, len(manifest['items'][0]['items'][0]['items']))

        self.assertEqual('Manifest', manifest['type'])
        self.assertEqual('Canvas', manifest['items'][0]['type'])
        self.assertEqual('AnnotationPage', manifest['items'][0]['items'][0]['type'])
        self.assertEqual('Annotation', manifest['items'][0]['items'][0]['items'][0]['type'])

        self.assertEqual(' - US -  - ', manifest['label']['en'][0])
        self.assertEqual('http://localhost:8042%s/canvas/p1' % uri, manifest['items'][0]['id'])

        annotation = manifest['items'][0]['items'][0]
        self.assertEqual('http://localhost:8042%s/page/p1/1' % uri, annotation['id'])
        self.assertEqual('AnnotationPage', annotation['type'])
        self.assertEqual(1, len(annotation['items']))

        item = manifest['items'][0]['items'][0]['items'][0]
        self.assertEqual('image/jpeg', item['body']['format'])
        self.assertEqual('Image', item['body']['type'])
        self.assertEqual(832, item['body']['width'])
        self.assertEqual(640, item['body']['height'])
        self.assertEqual('http://localhost:8042%s/full/max/0/default.jpg' % uri, item['body']['id'])
        self.assertEqual(1, len(item['body']['service']))
        self.assertEqual('http://localhost:8042%s' % uri, item['body']['service'][0]['id'])
        self.assertEqual('level0', item['body']['service'][0]['profile'])
        self.assertEqual('ImageService3', item['body']['service'][0]['type'])
        self.assertEqual('http://localhost:8042%s/annotation/p1-image' % uri, item['id'])
        self.assertEqual('painting', item['motivation'])
        self.assertEqual('Annotation', item['type'])
        self.assertEqual(manifest['items'][0]['id'], item['target'])

        self.assertEqual(832, manifest['items'][0]['width'])  # Default padding is (64,64) for an image size (800,600)
        self.assertEqual(640, manifest['items'][0]['height'])

        info = DoGet(ORTHANC, uri + '/info.json')
        self.assertEqual('http://iiif.io/api/image/3/context.json', info['@context'])
        self.assertEqual('http://iiif.io/api/image', info['protocol'])
        self.assertEqual('http://localhost:8042%s' % uri, info['id'])
        self.assertEqual('level0', info['profile'])
        self.assertEqual('ImageService3', info['type'])
        self.assertEqual(832, info['width'])
        self.assertEqual(640, info['height'])

        self.assertEqual(2, len(info['sizes']))
        self.assertEqual(320, info['sizes'][0]['height'])
        self.assertEqual(416, info['sizes'][0]['width'])
        self.assertEqual(640, info['sizes'][1]['height'])
        self.assertEqual(832, info['sizes'][1]['width'])

        self.assertEqual(1, len(info['tiles']))
        self.assertEqual(512, info['tiles'][0]['width'])
        self.assertEqual(512, info['tiles'][0]['height'])
        self.assertEqual([1, 2], info['tiles'][0]['scaleFactors'])

        # Those are the calls made by Mirador
        tile = GetImage(ORTHANC, '/wsi/iiif/frames-pyramids/%s/0/full/416,320/0/default.jpg' % a)
        self.assertEqual((416, 320), tile.size)
        self.assertFalse(IsWhite(self, tile))
        tile = GetImage(ORTHANC, '/wsi/iiif/frames-pyramids/%s/0/0,0,512,512/512,512/0/default.jpg' % a)
        self.assertEqual((512, 512), tile.size)
        self.assertFalse(IsWhite(self, tile))
        tile = GetImage(ORTHANC, '/wsi/iiif/frames-pyramids/%s/0/512,0,320,512/320,512/0/default.jpg' % a)
        self.assertEqual((320, 512), tile.size)
        self.assertFalse(IsWhite(self, tile))
        tile = GetImage(ORTHANC, '/wsi/iiif/frames-pyramids/%s/0/0,512,512,128/512,128/0/default.jpg' % a)
        self.assertEqual((512, 128), tile.size)
        self.assertFalse(IsWhite(self, tile))
        tile = GetImage(ORTHANC, '/wsi/iiif/frames-pyramids/%s/0/512,512,320,128/320,128/0/default.jpg' % a)
        self.assertEqual((320, 128), tile.size)
        self.assertFalse(IsWhite(self, tile))

try:
    print('\nStarting the tests...')
    unittest.main(argv = [ sys.argv[0] ] + args.options)

finally:
    print('\nDone')
