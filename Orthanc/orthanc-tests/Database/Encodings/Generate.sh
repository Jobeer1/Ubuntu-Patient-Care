#!/bin/bash

# Inspired from Levin Alexander on 2016-11-03
# https://groups.google.com/d/msg/orthanc-users/kYURTgtgPmI/KeOL8lGFAwAJ

set -e

convert -quality 90 -resize 128x128 ../Lena.png /tmp/Lena.jpg

function Encode {
    echo $1
    SOURCE="Test-éüäöòДΘĝדصķћ๛ﾈİ"
    CONVERTED=$(echo "$SOURCE" | iconv -c -t $1) 

    img2dcm /tmp/Lena.jpg Lena-$1.dcm \
        -k "(0010,0010)=${CONVERTED}" \
        -k "(0010,0020)=${1}" \
        -k "(0008,0005)=${2}" 

    echo -n "${CONVERTED}" | md5sum
}


# http://dicom.nema.org/medical/dicom/current/output/html/part03.html#sect_C.12.1.1.2
Encode 'arabic'    'ISO_IR 127'
Encode 'ascii'     'ISO_IR 6'    # More accurately, ISO 646
Encode 'cyrillic'  'ISO_IR 144'
Encode 'greek'     'ISO_IR 126'
Encode 'hebrew'    'ISO_IR 138'
Encode 'latin1'    'ISO_IR 100'
Encode 'latin2'    'ISO_IR 101'
Encode 'latin3'    'ISO_IR 109'
Encode 'latin4'    'ISO_IR 110'
Encode 'latin5'    'ISO_IR 148'
Encode 'shift-jis' 'ISO_IR 13'   # Japanese
Encode 'tis-620'   'ISO_IR 166'  # Thai
Encode 'utf8'      'ISO_IR 192'
