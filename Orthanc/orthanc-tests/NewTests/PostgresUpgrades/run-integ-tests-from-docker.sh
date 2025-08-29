#!/bin/bash

set -ex

/scripts/wait-for-it.sh orthanc-pg-15-previous-revision-for-integ-tests:8042 -t 60
# python /tests/orthanc-tests/Tests/Run.py --server=orthanc-pg-15-previous-revision-for-integ-tests --force --docker -- -v  Orthanc.test_lua_deadlock
python /tests/orthanc-tests/Tests/Run.py --server=orthanc-pg-15-previous-revision-for-integ-tests --force --docker -- -v
