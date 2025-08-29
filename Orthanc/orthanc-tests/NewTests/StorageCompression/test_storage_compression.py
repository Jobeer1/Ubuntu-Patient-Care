import unittest
import time
from helpers import OrthancTestCase, Helpers

from orthanc_api_client import OrthancApiClient, generate_test_dicom_file

import pathlib
here = pathlib.Path(__file__).parent.resolve()


class TestStorageCompression(OrthancTestCase):

    @classmethod
    def prepare(cls):
        test_name = "StorageCompression"
        storage_name = "storage_compression"

        print(f'-------------- preparing {test_name} tests')

        cls.clear_storage(storage_name=storage_name)

        config = {
                "StorageCompression": True
            }

        config_path = cls.generate_configuration(
            config_name=f"{test_name}_preparation",
            storage_name=storage_name,
            config=config,
            plugins=Helpers.plugins
        )

        if Helpers.break_before_preparation:
            print(f"++++ It is now time to start your Orthanc under tests with configuration file '{config_path}' +++++")
            input("Press Enter to continue")
        else:
            cls.launch_orthanc_to_prepare_db(
                config_name=f"{test_name}_preparation",
                storage_name=storage_name,
                config=config,
                plugins=Helpers.plugins
            )


        # upload a study that will be stored with StorageCompression enabled
        instances_ids = cls.o.upload_folder(here / "../../Database/Knix/Loc")

        # make sure we can read files that have been uploaded (this tests the StorageCache with StorageCompression=true)
        dicom_file = cls.o.instances.get_file(instances_ids[0])
        tags = cls.o.instances.get_tags(instances_ids[0])
        if "PatientName" not in tags or tags["PatientName"] != "KNIX":
            print(f"ERROR: failed to get tags from uploaded file")
            exit(-1)

        if Helpers.break_before_preparation:
            print(f"++++ It is now time stop your Orthanc +++++")
            input("Press Enter to continue")
        else:
            cls.kill_orthanc()

        # generate config for orthanc-under-tests (change StorageCompression to false)
        config_path = cls.generate_configuration(
            config_name=f"{test_name}_under_test",
            storage_name=storage_name,
            config={
                "StorageCompression": False
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

        # upload a study that will be stored with StorageCompression disabled
        cls.o.upload_folder(here / "../../Database/Brainix/Flair")


    def test_read_compressed_and_uncompressed_files(self):
        
        # this test simply make sure we can read stored files
        # it is repeated 2 times to use the cache the second time

        for i in range(0, 2):
            print(f"run {i}")
            compressed_study = self.o.studies.find(query={
                "PatientName": "KNIX"
            })[0]
            uncompressed_study = self.o.studies.find(query={
                "PatientName": "BRAINIX"
            })[0]
            
            compressed_study_tags = self.o.studies.get_tags(orthanc_id = compressed_study.orthanc_id)
            uncompressed_study_tags = self.o.studies.get_tags(orthanc_id = uncompressed_study.orthanc_id)

            compressed_study_dicom_file = self.o.instances.get_file(orthanc_id = self.o.studies.get_first_instance_id(compressed_study.orthanc_id))
            uncompressed_study_dicom_file = self.o.instances.get_file(orthanc_id = self.o.studies.get_first_instance_id(uncompressed_study.orthanc_id))

            self.assertEqual("KNIX", compressed_study_tags["PatientName"])
            self.assertEqual("BRAINIX", uncompressed_study_tags["PatientName"])
