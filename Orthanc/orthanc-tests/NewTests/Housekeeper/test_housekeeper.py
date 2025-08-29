import unittest
import time
from helpers import OrthancTestCase, Helpers

from orthanc_api_client import OrthancApiClient, generate_test_dicom_file

import pathlib
here = pathlib.Path(__file__).parent.resolve()


class TestHousekeeper(OrthancTestCase):

    @classmethod
    def prepare(cls):
        print('-------------- preparing TestHousekeeper tests')

        cls.clear_storage(storage_name="housekeeper")

        cls.launch_orthanc_to_prepare_db(
            config_name="housekeeper_preparation",
            storage_name="housekeeper",
            config={
                "StorageCompression": False,
                "Housekeeper": {
                    "Enable": False
                }
            },
            plugins=Helpers.plugins
        )

        # upload a study and keep track of data before housekeeper runs
        cls.o.upload_folder(here / "../../Database/Knix/Loc")

        cls.instance_before, cls.series_before, cls.study_before, cls.patient_before = cls.get_infos()

        cls.kill_orthanc()
        time.sleep(3)

        # generate config for orthanc-under-tests (change StorageCompression and add ExtraMainDicomTags)
        config_path = cls.generate_configuration(
            config_name="housekeeper_under_test",
            storage_name="housekeeper",
            config={
                "StorageCompression": True,
                "ExtraMainDicomTags": {
                    "Patient" : ["PatientWeight", "PatientAge"],
                    "Study": ["NameOfPhysiciansReadingStudy"],
                    "Series": ["ScanOptions"],
                    "Instance": ["Rows", "Columns", "DerivationCodeSequence"]
                },
                "Housekeeper": {
                    "Enable": True
                }
            },
            plugins=Helpers.plugins
        )

        print('-------------- prepared TestHousekeeper tests')
        if Helpers.break_after_preparation:
            print(f"++++ It is now time to start your Orthanc under tests with configuration file '{config_path}' +++++")
            input("Press Enter to continue")
        else:
            print('-------------- launching TestHousekeeper tests')
            cls.launch_orthanc_under_tests(
                config_path=config_path,
                config_name="housekeeper_under_test",
                storage_name="housekeeper",
                plugins=Helpers.plugins,
                enable_verbose=False
            )

        print('-------------- waiting for orthanc-under-tests to be available')
        cls.o.wait_started()
        
        completed = False
        while not completed:
            print('-------------- waiting for housekeeper to finish processing')
            time.sleep(1)
            housekeeper_status = cls.o.get_json("/plugins/housekeeper/status")
            completed = (housekeeper_status["LastProcessedConfiguration"]["StorageCompressionEnabled"] == True) \
                        and (housekeeper_status["LastChangeToProcess"] == housekeeper_status["LastProcessedChange"])


    @classmethod
    def get_infos(cls):
        instance_id = cls.o.lookup(
            needle="1.2.840.113619.2.176.2025.1499492.7040.1171286241.704",
            filter="Instance"
        )[0]

        instance_info = cls.o.get_json(endpoint=f"instances/{instance_id}")
        
        series_id = instance_info["ParentSeries"]
        series_info = cls.o.get_json(endpoint=f"series/{series_id}")
        
        study_id = series_info["ParentStudy"]
        study_info = cls.o.get_json(endpoint=f"studies/{study_id}")

        patient_id = study_info["ParentPatient"]
        patient_info = cls.o.get_json(endpoint=f"patients/{patient_id}")

        return instance_info, series_info, study_info, patient_info



    def test_before_after_reconstruction(self):

        # make sure it has run once !
        housekeeper_status = self.o.get_json("housekeeper/status")
        self.assertIsNotNone(housekeeper_status["LastTimeStarted"])

        instance_after, series_after, study_after, patient_after = self.get_infos()

        # extra tags were not in DB before reconstruction
        self.assertNotIn("Rows", self.instance_before["MainDicomTags"])
        self.assertNotIn("DerivationCodeSequence", self.instance_before["MainDicomTags"])
        self.assertNotIn("ScanOptions", self.series_before["MainDicomTags"])
        self.assertNotIn("NameOfPhysiciansReadingStudy", self.study_before["MainDicomTags"])
        self.assertNotIn("PatientWeight", self.patient_before["MainDicomTags"])

        # extra tags are in  DB after reconstruction
        self.assertIn("Rows", instance_after["MainDicomTags"])
        self.assertIn("DerivationCodeSequence", instance_after["MainDicomTags"])
        self.assertIn("ScanOptions", series_after["MainDicomTags"])
        self.assertIn("NameOfPhysiciansReadingStudy", study_after["MainDicomTags"])
        self.assertIn("PatientWeight", patient_after["MainDicomTags"])

        # storage has been compressed during reconstruction
        self.assertTrue(self.instance_before["FileSize"] > instance_after["FileSize"]) 
        self.assertNotEqual(self.instance_before["FileUuid"], instance_after["FileUuid"]) # files ID have changed
