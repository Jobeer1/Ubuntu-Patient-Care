import unittest
import time
import subprocess
import pprint
import os
from helpers import OrthancTestCase, Helpers

from orthanc_api_client import OrthancApiClient, generate_test_dicom_file
from orthanc_api_client import exceptions as orthanc_exceptions

import pathlib
here = pathlib.Path(__file__).parent.resolve()


def count_files_in_storage(path):
    all_files = []
    for root, dirs, files in os.walk(path):
        for file in files:
            if len(file) == 36:
                all_files.append(file)
    
    return len(all_files)


class TestMaxStorageReject(OrthancTestCase):

    @classmethod
    def prepare(cls):
        test_name = "MaxStorageReject"
        storage_name = "max_storage_reject"

        cls.clear_storage(storage_name=storage_name)

        config_path = cls.generate_configuration(
            config_name=f"{test_name}_under_test",
            storage_name=storage_name,
            config={
                "MaximumPatientCount": 2,
                "MaximumStorageMode": "Reject"
            },
            plugins=Helpers.plugins
        )

        print(f'-------------- prepared {test_name} tests')
        if Helpers.break_after_preparation:
            print(f"++++ It is now time to start your Orthanc under tests with configuration file '{config_path}' +++++")
            input("Press Enter to continue")
        else:
            print(f'-------------- launching {test_name} tests')
            cls.launch_orthanc_under_tests(
                config_path=config_path,
                config_name=f"{test_name}_under_test",
                storage_name=storage_name,
                plugins=Helpers.plugins
            )

        print('-------------- waiting for orthanc-under-tests to be available')
        cls.o.wait_started()


    def test_upload_3_patients_rest_api(self):
        
        if self.o.get_system()["ApiVersion"] > 20:  # from Orthanc 1.12.1
            self.o.delete_all_content()

            # make sure the 3rd patient does not make it into the storage (through the Rest API)
            self.o.upload_file(here / "../../Database/Brainix/Flair/IM-0001-0001.dcm")
            self.o.upload_file(here / "../../Database/Knix/Loc/IM-0001-0001.dcm")
            with self.assertRaises(orthanc_exceptions.HttpError) as ctx:
                self.o.upload_file(here / "../../Database/Phenix/IM-0001-0001.dcm")
            self.assertEqual(507, ctx.exception.http_status_code)
            self.assertEqual(2, len(self.o.studies.get_all_ids()))
            self.assertEqual(2, count_files_in_storage(self.get_storage_path("max_storage_reject")))

    def upload_with_store_scu(self, path):
        subprocess.check_call([Helpers.find_executable('storescu'),
                               "-xs",
                               Helpers.get_orthanc_ip(),
                               str(Helpers.get_orthanc_dicom_port()),
                               path])

    def test_upload_3_patients_c_store(self):

        if self.o.get_system()["ApiVersion"] > 20:  # from Orthanc 1.12.1
            self.o.delete_all_content()
            
            # make sure the 3rd patient does not make it into the storage (through StoreSCU)
            self.upload_with_store_scu(here / "../../Database/Brainix/Flair/IM-0001-0001.dcm")
            self.upload_with_store_scu(here / "../../Database/Knix/Loc/IM-0001-0001.dcm")
            with self.assertRaises(subprocess.CalledProcessError) as ctx:
                self.upload_with_store_scu(here / "../../Database/Phenix/IM-0001-0001.dcm")
            self.assertEqual(2, len(self.o.studies.get_all_ids()))
            self.assertEqual(2, count_files_in_storage(self.get_storage_path("max_storage_reject")))

    def test_upload_3_patients_dicomweb(self):

        if self.o.get_system()["ApiVersion"] > 20:  # from Orthanc 1.12.1
            self.o.delete_all_content()
            
            # make sure the 3rd patient does not make it into the storage (through DicomWeb)
            self.o.upload_files_dicom_web([here / "../../Database/Brainix/Flair/IM-0001-0001.dcm"])
            self.o.upload_files_dicom_web([here / "../../Database/Knix/Loc/IM-0001-0001.dcm"])

            with self.assertRaises(orthanc_exceptions.HttpError) as ctx:
                self.o.upload_files_dicom_web([here / "../../Database/Phenix/IM-0001-0001.dcm"])
            self.assertEqual(400, ctx.exception.http_status_code)

            self.assertEqual(2, len(self.o.studies.get_all_ids()))
            self.assertEqual(2, count_files_in_storage(self.get_storage_path("max_storage_reject")))

    def test_upload_3_patients_dicomweb_in_one_query(self):

        if self.o.get_system()["ApiVersion"] > 20:  # from Orthanc 1.12.1
            self.o.delete_all_content()
            
            # make sure the 3rd patient does not make it into the storage (through DicomWeb)
            r = self.o.upload_files_dicom_web([
                here / "../../Database/Brainix/Flair/IM-0001-0001.dcm",
                here / "../../Database/Knix/Loc/IM-0001-0001.dcm",
                here / "../../Database/Phenix/IM-0001-0001.dcm"
                ])

            # pprint.pprint(r)
            self.assertEqual(2, len(self.o.studies.get_all_ids()))
            self.assertIn('00081198', r)
            self.assertEqual(0xA700, r['00081198']['Value'][0]['00081197']['Value'][0])  # one failed instance with out-of-resource status
            self.assertEqual(2, count_files_in_storage(self.get_storage_path("max_storage_reject")))
