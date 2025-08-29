import argparse
import unittest
import os
import sys
import argparse
from helpers import Helpers
import pathlib
# python3 main.py --orthanc_under_tests_exe=/home/alain/o/build/orthanc/Orthanc --pattern=Housekeeper.test_housekeeper.TestHousekeeper.* --plugin=/home/alain/o/build/orthanc/libHousekeeper.so

here = pathlib.Path(__file__).parent.resolve()


def load_tests(loader=None, tests=None, pattern='test_*.py'):
    this_dir = os.path.dirname(__file__)
    package_tests = loader.discover(start_dir=this_dir, pattern=pattern)
    return package_tests

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Executes Orthanc integration tests.')
    parser.add_argument('-k', '--pattern', dest='test_name_patterns', action='append', type=str, help='a test pattern (ex: Housekeeper.toto')
    parser.add_argument('--orthanc_under_tests_hostname', type=str, default="localhost", help="orthanc under tests hostname")
    parser.add_argument('--orthanc_under_tests_http_port', type=int, default=8052, help="orthanc under tests HTTP port")
    parser.add_argument('--orthanc_under_tests_dicom_port', type=int, default=4252, help="orthanc under tests DICOM port")
    parser.add_argument('--orthanc_under_tests_exe', type=str, default=None, help="path to the orthanc executable (if it must be launched by this script)")
    parser.add_argument('--orthanc_previous_version_exe', type=str, default=None, help="path to the orthanc executable used to prepare previous version of storage/db (if it must be launched by this script and if different from orthanc_under_tests_exe)")
    parser.add_argument('--orthanc_under_tests_docker_image', type=str, default=None, help="Docker image of the orthanc under tests (if it must be launched by this script)")
    parser.add_argument('--orthanc_previous_version_docker_image', type=str, default=None, help="Docker image of the orthanc version used to prepare previous version of storage/db (if it must be launched by this script)")
    parser.add_argument('--skip_preparation', action='store_true', help="if this is a multi stage tests with preparations, skip the preparation")
    parser.add_argument('--break_after_preparation', action='store_true', help="if this is a multi stage tests with preparations, pause after the preparation (such that you can start your own orthanc-under-tests in your debugger)")
    parser.add_argument('--break_before_preparation', action='store_true', help="if this is a multi stage tests with preparations, pause before the preparation (such that you can start your own orthanc-under-tests in your debugger)")
    parser.add_argument('--db', type=str, default='unspecified', help="the DB engine to use")
    parser.add_argument('-p', '--plugin', dest='plugins', action='append', type=str, help='path to a plugin to add to configuration')

    args = parser.parse_args()

    loader = unittest.TestLoader()
    loader.testNamePatterns = args.test_name_patterns

    Helpers.orthanc_under_tests_hostname = args.orthanc_under_tests_hostname
    Helpers.orthanc_under_tests_http_port = args.orthanc_under_tests_http_port
    Helpers.orthanc_under_tests_dicom_port = args.orthanc_under_tests_dicom_port
    Helpers.plugins = args.plugins
    Helpers.db = args.db

    Helpers.orthanc_under_tests_exe = args.orthanc_under_tests_exe
    Helpers.orthanc_under_tests_docker_image = args.orthanc_under_tests_docker_image

    if args.orthanc_previous_version_exe:
        Helpers.orthanc_previous_version_exe = args.orthanc_previous_version_exe
    else:
        Helpers.orthanc_previous_version_exe = args.orthanc_under_tests_exe

    if args.orthanc_previous_version_docker_image:
        Helpers.orthanc_previous_version_docker_image = args.orthanc_previous_version_docker_image
    else:
        Helpers.orthanc_previous_version_docker_image = args.orthanc_under_tests_docker_image

    if args.skip_preparation:
        Helpers.skip_preparation = True
    if args.break_after_preparation:
        Helpers.break_after_preparation = True
    if args.break_before_preparation:
        Helpers.break_before_preparation = True

    print("Launching tests")
    
    result = unittest.TextTestRunner(verbosity=2).run(load_tests(loader=loader))
    if not result.wasSuccessful():
        sys.exit(1)
