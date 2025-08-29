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


class TestWithIngestTranscoding(OrthancTestCase):

    @classmethod
    def prepare(cls):
        print('-------------- preparing TestWithIngestTranscoding tests')

        cls.clear_storage(storage_name="WithIngestTranscoding")

        config = {
                "IngestTranscoding": "1.2.840.10008.1.2.4.70"
            }

        config_path = cls.generate_configuration(
            config_name="with_ingest_transcoding",
            storage_name="WithIngestTranscoding",
            config=config,
            plugins=Helpers.plugins
        )

        print('-------------- prepared TestWithIngestTranscoding tests')
        if Helpers.break_after_preparation:
            print(f"++++ It is now time to start your Orthanc under tests with configuration file '{config_path}' +++++")
            input("Press Enter to continue")
        else:
            print('-------------- launching TestWithIngestTranscoding tests')
            cls.launch_orthanc_under_tests(
                config_path=config_path,
                config_name="with_ingest_transcoding",
                storage_name="WithIngestTranscoding",
                plugins=Helpers.plugins
            )

        print('-------------- waiting for orthanc-under-tests to be available')
        cls.o.wait_started()
        
    def test_modify(self):
        self.o.delete_all_content()

        # upload a study
        self.o.upload_file(here / "../../Database/Brainix/Flair/IM-0001-0001.dcm")

        # first modify it without transcoding
        r = self.o.post(
            endpoint="studies/27f7126f-4f66fb14-03f4081b-f9341db2-53925988/modify",
            json={
                "Replace": {"PatientID": "TUTU"},
                "Force": True,
                "KeepSource": True,
                "Synchronous": True
            }
            ).json()

        study_id = r['ID']
        instance_id = self.o.studies.get_first_instance_id(orthanc_id=study_id)

        r = self.o.get(
            endpoint=f"instances/{instance_id}/metadata?expand"
        ).json()
        self.assertEqual("1.2.840.10008.1.2.4.70", r['TransferSyntax'])
        self.o.studies.delete(orthanc_id=study_id)

        # first modify it with transcoding  -> IngestTranscoding shall not be applied
        r = self.o.post(
            endpoint="studies/27f7126f-4f66fb14-03f4081b-f9341db2-53925988/modify",
            json={
                "Replace": {"PatientID": "TUTU"},
                "Force": True,
                "KeepSource": True,
                "Synchronous": True,
                "Transcode": "1.2.840.10008.1.2.4.80"
            }
            ).json()

        instance_id = self.o.studies.get_first_instance_id(orthanc_id=r['ID'])

        r = self.o.get(
            endpoint=f"instances/{instance_id}/metadata?expand"
        ).json()
        self.assertEqual("1.2.840.10008.1.2.4.80", r['TransferSyntax'])


    def test_anonymize(self):
        self.o.delete_all_content()

        # upload a study
        self.o.upload_file(here / "../../Database/Brainix/Flair/IM-0001-0001.dcm")

        # first anonymize it without transcoding
        r = self.o.post(
            endpoint="studies/27f7126f-4f66fb14-03f4081b-f9341db2-53925988/anonymize",
            json={
                "Synchronous": True
            }
            ).json()

        study_id = r['ID']
        instance_id = self.o.studies.get_first_instance_id(orthanc_id=study_id)

        r = self.o.get(
            endpoint=f"instances/{instance_id}/metadata?expand"
        ).json()
        self.assertEqual("1.2.840.10008.1.2.4.70", r['TransferSyntax'])
        self.o.studies.delete(orthanc_id=study_id)

        # first anonymize it with transcoding  -> IngestTranscoding shall not be applied
        r = self.o.post(
            endpoint="studies/27f7126f-4f66fb14-03f4081b-f9341db2-53925988/anonymize",
            json={
                "Synchronous": True,
                "Transcode": "1.2.840.10008.1.2.4.80"
            }
            ).json()

        instance_id = self.o.studies.get_first_instance_id(orthanc_id=r['ID'])

        r = self.o.get(
            endpoint=f"instances/{instance_id}/metadata?expand"
        ).json()
        self.assertEqual("1.2.840.10008.1.2.4.80", r['TransferSyntax'])
