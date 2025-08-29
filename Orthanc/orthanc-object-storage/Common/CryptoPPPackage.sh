#!/bin/bash

set -ex

VERSION=840

TARGET=/tmp/cryptopp-${VERSION}
rm -rf ${TARGET}
mkdir -p ${TARGET}/cryptopp
cd ${TARGET}/cryptopp
wget https://www.cryptopp.com/cryptopp${VERSION}.zip
unzip ./cryptopp${VERSION}.zip
rm ./cryptopp${VERSION}.zip
rm -rf ./TestData
rm -rf ./TestPrograms
rm -rf ./TestVectors
cd /tmp
tar cvfz cryptopp-${VERSION}.tar.gz cryptopp-${VERSION}

md5sum /tmp/cryptopp-${VERSION}.tar.gz
