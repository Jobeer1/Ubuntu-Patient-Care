
Introduction
============

This folder contains the Python script that reads the code model of
the Orthanc SDK, and that automatically wraps this SDK as a Python
extension module. This script is automatically invoked during the
build by CMake. It necessitates the Pystache module [1] to be
installed in the Python environment used by CMake.

Usage:

$ ./GenerateOrthancSDK.py


[1] https://pypi.org/project/pystache/
