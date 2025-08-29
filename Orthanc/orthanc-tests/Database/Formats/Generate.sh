#!/bin/bash

set -e

# http://gdcm.sourceforge.net/html/gdcmconv.html

gdcmconv -i ../Brainix/Epi/IM-0001-0001.dcm -o JpegLossless.dcm -L
gdcmconv -i ../Brainix/Epi/IM-0001-0001.dcm -o Jpeg.dcm -J
gdcmconv -i ../Brainix/Epi/IM-0001-0001.dcm -o Rle.dcm -R

# Generate study/series/sop instance UID++++
dcmodify -e '(0008,0005)' -m '(0010,0020)=FromGDCM' -gin -gst -gse JpegLossless.dcm 
dcmodify -e '(0008,0005)' -m '(0010,0020)=FromGDCM' -gin -gst -gse Jpeg.dcm 
dcmodify -e '(0008,0005)' -m '(0010,0020)=FromGDCM' -gin -gst -gse Rle.dcm 

rm -f JpegLossless.dcm.bak Jpeg.dcm.bak Rle.dcm.bak

gdcmraw -t PixelData ../Brainix/Epi/IM-0001-0001.dcm PixelData.raw
convert -define png:include-chunks=none -define png:compression-level=9 -size 256x256 -depth 16 gray:PixelData.raw Brainix.png

gdcmraw -t PixelData ../KarstenHilbertRF.dcm PixelData.raw
convert -define png:include-chunks=none -define png:compression-level=9 -size 512x464 -depth 8 gray:PixelData.raw KarstenHilbertRF.png

# Decompress the multiframe image
gdcmconv -w ../Multiframe.dcm tmp.dcm
gdcmraw -t PixelData ./tmp.dcm PixelData.raw
SIZE=$((512*512))
dd if=PixelData.raw of=PixelData2.raw bs=$SIZE count=1 skip=0 &> /dev/null
convert -define png:include-chunks=none -define png:compression-level=9 -size 512x512 -depth 8 gray:PixelData2.raw Multiframe0.png
dd if=PixelData.raw of=PixelData2.raw bs=$SIZE count=1 skip=75 &> /dev/null
convert -define png:include-chunks=none -define png:compression-level=9 -size 512x512 -depth 8 gray:PixelData2.raw Multiframe75.png

# Decompress the signed CT image, ignoring the fact that the data is signed
gdcmraw -t PixelData ../SignedCT.dcm PixelData.raw
convert -define png:include-chunks=none -define png:compression-level=9 -size 512x512 -depth 16 gray:PixelData.raw SignedCT.png

rm -f PixelData.raw PixelData2.raw tmp.dcm
