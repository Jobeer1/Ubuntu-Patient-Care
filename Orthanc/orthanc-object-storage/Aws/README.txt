
Native compilation under Ubuntu 22.04
=====================================

# mkdir Build
# cd Build
# cmake .. -DCMAKE_BUILD_TYPE=Release -DUSE_VCPKG_PACKAGES=OFF -DUSE_SYSTEM_ORTHANC_SDK=OFF -G Ninja
# ninja


Linux Standard Base compilation
===============================

# ./holy-build-box-compile.sh Release


MinGW
=====

The minimum MinGW version to compile the AWS C++ SDK is 13.x. 

To build Windows 32 binaries:

# ./mingw-compile.sh Release i686
# ls ../mingw-binaries-i686/

To build Windows 64 binaries:

# ./mingw-compile.sh Release x86_64
# ls ../mingw-binaries-x86_64/


Microsoft Visual Studio
=======================

The minimum version to compile the AWS C++ SDK is Visual Studio 2015.

WARNING: The binaries that are produced with Visual Studio currently
do not work. They write empty files to the S3 storage.
