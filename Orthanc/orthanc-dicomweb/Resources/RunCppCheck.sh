#!/bin/bash

set -ex

CPPCHECK=cppcheck

if [ $# -ge 1 ]; then
    CPPCHECK=$1
fi

cat <<EOF > /tmp/cppcheck-suppressions.txt
unusedFunction
EOF

${CPPCHECK} --enable=all --quiet --std=c++11 \
            --suppressions-list=/tmp/cppcheck-suppressions.txt \
            -DHAS_ORTHANC_EXCEPTION=1 \
            -DORTHANC_BUILDING_FRAMEWORK_LIBRARY=1 \
            -DORTHANC_ENABLE_BASE64=1 \
            -DORTHANC_ENABLE_CIVETWEB=0 \
            -DORTHANC_ENABLE_CURL=1 \
            -DORTHANC_ENABLE_DCMTK=1 \
            -DORTHANC_ENABLE_DCMTK_JPEG=1 \
            -DORTHANC_ENABLE_DCMTK_JPEG_LOSSLESS=1 \
            -DORTHANC_ENABLE_GLEW=1 \
            -DORTHANC_ENABLE_JPEG=1 \
            -DORTHANC_ENABLE_LOCALE=1 \
            -DORTHANC_ENABLE_LOGGING=1 \
            -DORTHANC_ENABLE_LOGGING_STDIO=1 \
            -DORTHANC_ENABLE_MD5=1 \
            -DORTHANC_ENABLE_MONGOOSE=0 \
            -DORTHANC_ENABLE_OPENGL=1 \
            -DORTHANC_ENABLE_PKCS11=0 \
            -DORTHANC_ENABLE_PNG=1 \
            -DORTHANC_ENABLE_PUGIXML=0 \
            -DORTHANC_ENABLE_SDL=1 \
            -DORTHANC_ENABLE_SSL=1 \
            -DORTHANC_ENABLE_THREADS=1 \
            -DORTHANC_ENABLE_WASM=1 \
            -DORTHANC_ENABLE_ZLIB=1 \
            -DORTHANC_SANDBOXED=0 \
            -D__GNUC__ \
            -D__cplusplus=201103 \
            -D__linux__ \
            -DEM_ASM \
            -UNDEBUG \
            -I../../orthanc/OrthancFramework/Sources \
            -I../../orthanc/OrthancServer/Plugins/Include/ \
            \
            ../Plugin \
            ../UnitTestsSources \
            \
            2>&1
