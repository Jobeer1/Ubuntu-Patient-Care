import unittest
import time
import os
from helpers import OrthancTestCase, Helpers

from orthanc_api_client import OrthancApiClient, generate_test_dicom_file
from orthanc_tools import OrthancTestDbPopulator

import pathlib
import glob
here = pathlib.Path(__file__).parent.resolve()


class TestExtraMainDicomTags(OrthancTestCase):

    @classmethod
    def prepare(cls):
        print('-------------- preparing TestExtraMainDicomTags tests')

        cls.clear_storage(storage_name="ExtraMainDicomTags")

        config = {
                "ExtraMainDicomTags": {
                    "Instance" : [
                        "Rows",
                        "PerformedProtocolCodeSequence"
                    ],
                    "Series" : [
                        "RequestAttributesSequence"
                    ],
                    "Study": [
                    ],
                    "Patient": []
                },
                "OverwriteInstances": True,
                "DicomWeb" : {
                    "StudiesMetadata" : "MainDicomTags",
                    "SeriesMetadata": "MainDicomTags"
                },
                "StableAge": 1000  # we don't want to be disturbed by events when debugging
            }

        config_path = cls.generate_configuration(
            config_name="extra_main_dicom_tags",
            storage_name="ExtraMainDicomTags",
            config=config,
            plugins=Helpers.plugins
        )

        print('-------------- prepared ExtraMainDicomTags tests')
        if Helpers.break_after_preparation:
            print(f"++++ It is now time to start your Orthanc under tests with configuration file '{config_path}' +++++")
            input("Press Enter to continue")
        else:
            print('-------------- launching ExtraMainDicomTags tests')
            cls.launch_orthanc_under_tests(
                config_path=config_path,
                config_name="extra_main_dicom_tags",
                storage_name="ExtraMainDicomTags",
                plugins=Helpers.plugins
            )

        print('-------------- waiting for orthanc-under-tests to be available')
        cls.o.wait_started()
        
    def test_main_dicom_tags(self):

        # upload a study
        self.o.upload_file(here / "../../Database/Brainix/Flair/IM-0001-0001.dcm")

        instance = self.o.get(endpoint="instances/4dc71dc0-6093b5f8-ca67aa8a-07b18ff5-95dbe3c8").json()

        self.assertIn("Rows", instance["MainDicomTags"])
        self.assertIn("PerformedProtocolCodeSequence", instance["MainDicomTags"])

    def test_main_dicom_tags_full(self):

        # upload a study
        self.o.upload_file(here / "../../Database/Brainix/Flair/IM-0001-0001.dcm")

        instance = self.o.get(endpoint="instances/4dc71dc0-6093b5f8-ca67aa8a-07b18ff5-95dbe3c8?full").json()

        self.assertIn("0028,0010", instance["MainDicomTags"])
        self.assertIn("0040,0260", instance["MainDicomTags"])


    def test_main_reconstruct(self):

        # upload a study
        self.o.upload_file(here / "../../Database/Brainix/Flair/IM-0001-0001.dcm")

        instance = self.o.get(endpoint="instances/4dc71dc0-6093b5f8-ca67aa8a-07b18ff5-95dbe3c8").json()

        self.assertIn("Rows", instance["MainDicomTags"])
        self.assertIn("PerformedProtocolCodeSequence", instance["MainDicomTags"])

        # reconstruct instance
        self.o.post(endpoint="instances/4dc71dc0-6093b5f8-ca67aa8a-07b18ff5-95dbe3c8/reconstruct", json={})
        instance = self.o.get(endpoint="instances/4dc71dc0-6093b5f8-ca67aa8a-07b18ff5-95dbe3c8").json()
        self.assertIn("Rows", instance["MainDicomTags"])
        self.assertIn("PerformedProtocolCodeSequence", instance["MainDicomTags"])

    def get_storage_access_count(self):
        mm = self.o.get_binary("/tools/metrics-prometheus").decode("utf-8")
        
        mm = [x.split(" ") for x in mm.split("\n")]

        count = 0
        for m in mm:
            if m[0] == 'orthanc_storage_cache_hit_count':
                # print(f"orthanc_storage_cache_hit_count = {m[1]}")
                count += int(m[1])
            if m[0] == 'orthanc_storage_cache_miss_count':
                # print(f"orthanc_storage_cache_miss_count = {m[1]}")
                count += int(m[1])

        print(f"storage access count = {count}")
        return count


    def test_tools_find(self):
        if self.o.is_orthanc_version_at_least(12, 5, 0) and self.o.capabilities.has_extended_find:

            # upload a study
            self.o.upload_file(here / "../../Database/Brainix/Flair/IM-0001-0001.dcm")

            # instance level, only extra main dicom tags from that level
            c = self.get_storage_access_count()
            r = self.o.post(
                endpoint="tools/find",
                json={
                    "Level": "Instances",
                    "Query": {
                        "PatientID": "5Yp0E"
                    },
                    "Expand": True,
                    "RequestedTags" : [
                        "Rows",                             # in the ExtraMainDicomTags at instance level
                        "PerformedProtocolCodeSequence"     # in the ExtraMainDicomTags at instance level
                    ]
                }
            )

            instances = r.json()
            self.assertEqual(1, len(instances))
            self.assertIn("Rows", instances[0]["RequestedTags"])
            self.assertIn("PerformedProtocolCodeSequence", instances[0]["RequestedTags"])
            self.assertEqual(c, self.get_storage_access_count()) # nothing should be read from disk

            # instance level, only extra main dicom tags from that level + a tag from disk
            c = self.get_storage_access_count()
            r = self.o.post(
                endpoint="tools/find",
                json={
                    "Level": "Instances",
                    "Query": {
                        "PatientID": "5Yp0E"
                    },
                    "Expand": True,
                    "RequestedTags" : [
                        "Rows",                             # in the ExtraMainDicomTags at instance level
                        "PerformedProtocolCodeSequence",    # in the ExtraMainDicomTags at instance level
                        "ReferencedStudySequence"           # "ReferencedStudySequence" is not stored in MainDicomTags !
                    ]
                }
            )

            instances = r.json()
            self.assertEqual(1, len(instances))
            self.assertIn("Rows", instances[0]["RequestedTags"])
            self.assertIn("PerformedProtocolCodeSequence", instances[0]["RequestedTags"])
            self.assertIn("ReferencedStudySequence", instances[0]["RequestedTags"])
            self.assertEqual(c + 1, self.get_storage_access_count())
            # TO test manually: ReferencedStudySequence 0008,1110 should be read from disk

            # instance level, extra main dicom tags from that level + a sequence from upper level
            c = self.get_storage_access_count()
            r = self.o.post(
                endpoint="tools/find",
                json={
                    "Level": "Instances",
                    "Query": {
                        "PatientID": "5Yp0E"
                    },
                    "Expand": True,
                    "RequestedTags" : [
                        "Rows",                             # in the ExtraMainDicomTags at instance level
                        "PerformedProtocolCodeSequence",    # in the ExtraMainDicomTags at instance level   0040,0260
                        "RequestAttributesSequence"         # in the ExtraMainDicomTags at series level     0040,0275
                    ]
                }
            )

            instances = r.json()
            self.assertEqual(1, len(instances))
            self.assertIn("Rows", instances[0]["RequestedTags"])
            self.assertIn("PerformedProtocolCodeSequence", instances[0]["RequestedTags"])
            self.assertIn("RequestAttributesSequence", instances[0]["RequestedTags"])
            self.assertEqual(c, self.get_storage_access_count()) # nothing should be read from disk

            # series level, request a sequence
            c = self.get_storage_access_count()
            r = self.o.post(
                endpoint="tools/find",
                json={
                    "Level": "Series",
                    "Query": {
                        "PatientID": "5Yp0E"
                    },
                    "Expand": True,
                    "RequestedTags" : [
                        "RequestAttributesSequence"         # in the ExtraMainDicomTags at series level
                    ]
                }
            )

            series = r.json()
            self.assertEqual(1, len(series))
            self.assertIn("RequestAttributesSequence", series[0]["RequestedTags"])
            self.assertEqual(c, self.get_storage_access_count()) # nothing should be read from disk

            # series level, request a sequence + a tag from disk
            c = self.get_storage_access_count()
            r = self.o.post(
                endpoint="tools/find",
                json={
                    "Level": "Series",
                    "Query": {
                        "PatientID": "5Yp0E"
                    },
                    "Expand": True,
                    "RequestedTags" : [
                        "RequestAttributesSequence",        # in the ExtraMainDicomTags at series level
                        "ReferencedStudySequence"           # "ReferencedStudySequence" is not stored in MainDicomTags !
                    ]
                }
            )

            series = r.json()
            self.assertEqual(1, len(series))
            self.assertIn("RequestAttributesSequence", series[0]["RequestedTags"])
            self.assertIn("ReferencedStudySequence", series[0]["RequestedTags"])
            self.assertEqual(c + 1, self.get_storage_access_count())
            # TO test manually: ReferencedStudySequence 0008,1110 should be read from disk


    def test_dicom_web_metadata(self):

        # upload a study
        self.o.upload_file(here / "../../Database/Brainix/Flair/IM-0001-0001.dcm")

        metadata = self.o.get(
            endpoint="dicom-web/studies/2.16.840.1.113669.632.20.1211.10000357775/metadata"
        ).json()

        self.assertEqual(1, len(metadata))
        self.assertIn("00280010", metadata[0])      # Rows
        self.assertNotIn("00280011", metadata[0])   # Columns should not be stored !
        self.assertIn("00400260", metadata[0])      # PerformedProtocolCodeSequence

    def test_storage_accesses_for_dicom_web(self):
        if self.o.is_orthanc_version_at_least(12, 5, 0) and self.o.capabilities.has_extended_find:

            # upload a study
            self.o.upload_file(here / "../../Database/Brainix/Flair/IM-0001-0001.dcm")

            # study level, only tags that are in DB (note, since 1.12.5, TimezoneOffsetFromUTC is a standard MainDicomTags)
            c = self.get_storage_access_count()
            r = self.o.get_json("/dicom-web/studies?PatientID=5Yp0E")
            self.assertEqual(c, self.get_storage_access_count()) # nothing should be read from disk

            # series level, only tags that are in DB (note, since 1.12.5, TimezoneOffsetFromUTC is a standard MainDicomTags)
            c = self.get_storage_access_count()
            r = self.o.get_json("/dicom-web/series?PatientID=5Yp0E")
            self.assertEqual(c, self.get_storage_access_count()) # nothing should be read from disk


