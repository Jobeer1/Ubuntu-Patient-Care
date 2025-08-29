import unittest
import time
import os
import threading
from helpers import OrthancTestCase, Helpers

from orthanc_api_client import OrthancApiClient, ChangeType
from orthanc_api_client import helpers as OrthancHelpers

import pathlib
import subprocess
import glob
here = pathlib.Path(__file__).parent.resolve()

class TestCGet(OrthancTestCase):

    @classmethod
    def cleanup(cls):
        os.chdir(here)
        print("Cleaning old compose")
        subprocesss_env = os.environ.copy()
        subprocesss_env["ORTHANC_IMAGE_UNDER_TESTS"] = Helpers.orthanc_under_tests_docker_image
        subprocess.run(["docker", "compose", "-f", "docker-compose-c-get.yml", "down", "-v", "--remove-orphans"], 
                       env=subprocesss_env, check=True)

    @classmethod
    def compose_up(cls):
        # print("Pullling containers")
        # subprocesss_env = os.environ.copy()
        # subprocesss_env["ORTHANC_IMAGE_UNDER_TESTS"] = Helpers.orthanc_under_tests_docker_image
        # subprocess.run(["docker", "compose", "-f", "docker-compose-transfers-concurrency.yml", "pull"], 
        #                env=subprocesss_env, check=True)

        print("Compose up")
        subprocesss_env = os.environ.copy()
        subprocesss_env["ORTHANC_IMAGE_UNDER_TESTS"] = Helpers.orthanc_under_tests_docker_image
        subprocess.run(["docker", "compose", "-f", "docker-compose-c-get.yml", "up", "-d"], 
                       env=subprocesss_env, check=True)

    @classmethod
    def setUpClass(cls):
        cls.cleanup()
        cls.compose_up()

    @classmethod
    def tearDownClass(cls):
        cls.cleanup()
        pass

    def clean_start(self):
        oa = OrthancApiClient("http://localhost:8072")
        ob = OrthancApiClient("http://localhost:8073")

        oa.wait_started()
        ob.wait_started()

        oa.delete_all_content()
        ob.delete_all_content()

        return oa, ob

    def test_cget(self):

        oa, ob = self.clean_start()

        instances_ids = ob.upload_folder( here / "../../Database/Brainix")

        oa.modalities.get_study(from_modality='b', dicom_id='2.16.840.1.113669.632.20.1211.10000357775')
        self.assertEqual(len(instances_ids), len(oa.instances.get_all_ids()))       
