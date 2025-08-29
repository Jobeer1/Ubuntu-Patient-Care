#!/bin/bash

set -e

convert -quality 90 -resize 128x128 ../Lena.png /tmp/Lena.jpg

function Generate() {
    echo $1
    img2dcm /tmp/Lena.jpg Lena-$1.dcm \
            -k "ImagesInAcquisition=2" \
            -k "NumberOfTemporalPositions=2" \
            -k "InstanceNumber=$1" \
            -k "StudyInstanceUID=1.2.840.113619.2.176.2025.1499492.7391.1171285944.390" \
            -k "SeriesInstanceUID=1.2.840.113619.2.176.2025.1499492.7391.1171285944.394"    
}

Generate 1
Generate 2
Generate 3
Generate 4
Generate 5
