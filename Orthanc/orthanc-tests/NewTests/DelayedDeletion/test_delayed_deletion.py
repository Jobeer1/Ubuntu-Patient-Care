import unittest
import time
import os
from helpers import OrthancTestCase, Helpers

from orthanc_api_client import OrthancApiClient, generate_test_dicom_file
from orthanc_tools import OrthancTestDbPopulator

import pathlib
import glob
import pprint
here = pathlib.Path(__file__).parent.resolve()


class TestDelayedDeletion(OrthancTestCase):

    @classmethod
    def prepare(cls):
        print('-------------- preparing TestDelayedDeletion tests')

        cls.clear_storage(storage_name="DelayedDeletion")

        config = {
                "DelayedDeletion": {
                    "Enable": True,
                    "ThrottleDelayMs": 200
                },
                "DatabaseServerIdentifier": "delayed-test"
            }

        config_path = cls.generate_configuration(
            config_name="delayed_deletion",
            storage_name="DelayedDeletion",
            config=config,
            plugins=Helpers.plugins
        )

        if Helpers.break_before_preparation:
            print(f"++++ It is now time to start your Orthanc under tests with configuration file '{config_path}' +++++")
            input("Press Enter to continue")
        else:
            print('-------------- launching DelayedDeletion preparation')

            cls.launch_orthanc_to_prepare_db(
                config_name="delayed_deletion",
                config_path=config_path,
                storage_name="DelayedDeletion",
                config=config,
                plugins=Helpers.plugins
            )
        
        print('-------------- waiting for orthanc-to-prepare-db to be available')
        cls.o.wait_started()

        print('-------------- populating')
        cls.o.upload_folder(here / "../../Database/Knix/Loc")
        print('-------------- populated')
        cls.files_count_after_preparation = len(glob.glob(os.path.join(cls.get_storage_path("DelayedDeletion"), "**"), recursive=True))

        all_studies_ids = cls.o.studies.get_all_ids()
        # delete all studies and exit Orthanc one seconds later
        cls.o.studies.delete(orthanc_ids = all_studies_ids)
        time.sleep(1)  

        if Helpers.break_before_preparation:
            print(f"++++ It is now time stop your Orthanc +++++")
            input("Press Enter to continue")
        else:
            cls.kill_orthanc()
        
        cls.files_count_after_stop = len(glob.glob(os.path.join(cls.get_storage_path("DelayedDeletion"), "**"), recursive=True))

        # speed up deletion for the second part of the tests
        config["DelayedDeletion"]["ThrottleDelayMs"] = 0

        config_path = cls.generate_configuration(
            config_name="delayed_deletion",
            storage_name="DelayedDeletion",
            config=config,
            plugins=Helpers.plugins
        )

        print('-------------- prepared DelayedDeletion tests')
        if Helpers.break_after_preparation:
            print(f"++++ It is now time to start your Orthanc under tests with configuration file '{config_path}' +++++")
            input("Press Enter to continue")
        else:
            print('-------------- launching DelayedDeletion tests')
            cls.launch_orthanc_under_tests(
                config_path=config_path,
                config_name="delayed_deletion",
                storage_name="DelayedDeletion",
                plugins=Helpers.plugins
            )

        print('-------------- waiting for orthanc-under-tests to be available')
        cls.o.wait_started()
        


    def test_resumes_pending_deletion(self):

        # plugin_status = self.o.get_json("plugins/delayed-deletion/status")
        # pprint.pprint(plugin_status)
        
        completed = False
        while not completed:
            print('-------------- waiting for DelayedDeletion to finish processing')
            time.sleep(1)
            plugin_status = self.o.get_json("plugins/delayed-deletion/status")
            # pprint.pprint(plugin_status)
            completed = plugin_status["FilesPendingDeletion"] == 0

        self.assertTrue(completed)
        files_count_after_delayed_deletion_is_complete = len(glob.glob(os.path.join(self.get_storage_path("DelayedDeletion"), "**"), recursive=True))
        self.assertGreater(10, files_count_after_delayed_deletion_is_complete)  # only the sqlite files shall remain (and . and ..)

