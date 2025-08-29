#!/usr/bin/env python3

import sys
import pydicom

if len(sys.argv) <= 1:
    print('Print the VR of the pixel data of a set of DICOM files')
    print('Usage: %s [list of DICOM files]' % sys.argv[0])
    exit(-1)

for f in sys.argv[1:]:
    try:
        ds = pydicom.dcmread(f)
        print(f, '=>', ds['PixelData'].VR)
    except:
        print(f, '=>', 'Unable to parse')
