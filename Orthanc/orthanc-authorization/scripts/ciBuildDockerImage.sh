#!/usr/bin/env bash
# Builds the Orthanc authorization plugin Docker image
# Arguments:

set -x # Trace execution
set -e # Stop on error
set -u # Stop on uninitialized variable

docker build -t osimis/orthanc-authorization-plugin .
