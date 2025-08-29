#!/usr/bin/env python3

import os
import sys
import pydicom

ROOT = os.path.join(os.path.dirname(__file__), '..', 'Database')

for root, dirs, files in os.walk(ROOT):
    for f in files:
        path = os.path.join(root, f)
        
        try:
            ds = pydicom.dcmread(path)
        except:
            continue

        ts = ds.file_meta.TransferSyntaxUID

        if not 'PixelData' in ds:
            print(path, '=> no pixel data')
            continue

        print(path)

        if ts == '1.2.840.10008.1.2':
            # Implicit VR Endian
            # https://dicom.nema.org/medical/dicom/current/output/chtml/part05/chapter_A.html#sect_A.1
            assert(ds['PixelData'].VR == 'OW')
            
        elif ts in [ '1.2.840.10008.1.2.1',
                     '1.2.840.10008.1.2.2' ]:
            # Explicit VR Little Endian
            # https://dicom.nema.org/medical/dicom/current/output/chtml/part05/sect_A.2.html

            # DICOM Big Endian Transfer Syntax (Explicit VR) - Retired, but same rule
            # https://dicom.nema.org/medical/dicom/2016b/output/chtml/part05/sect_A.3.html
            
            if f in [ 'PilatesArgenturGEUltrasoundOsiriX.dcm',
                      'KarstenHilbertRF.dcm',
                      'Issue143.dcm' ]:
                continue
            
            if ds['BitsAllocated'].value <= 8:
                assert(ds['PixelData'].VR == 'OB')
            else:
                assert(ds['PixelData'].VR == 'OW')

        else:
            if (('Beaufix/IM-' in path or
                 'Comunix/Ct/IM-' in path or
                 'Comunix/Pet/IM-' in path or
                 'Knee/T1/IM-' in path or
                 'Knee/T2/IM-' in path) and
                ts == '1.2.840.10008.1.2.4.91'):
                # JPEG2k should be "OB", but this is not the case of these modalities
                continue

            assert(ds['PixelData'].VR == 'OB')

