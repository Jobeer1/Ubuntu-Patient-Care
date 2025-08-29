import subprocess
import time
import unittest
from orthanc_api_client import OrthancApiClient, ResourceType
from orthanc_tools import OrthancTestDbPopulator
from helpers import Helpers, wait_container_healthy

import pathlib
import os
here = pathlib.Path(__file__).parent.resolve()




class TestConcurrencyTransfers(unittest.TestCase):

    @classmethod
    def cleanup(cls):
        os.chdir(here)
        print("Cleaning old compose")
        subprocesss_env = os.environ.copy()
        subprocesss_env["ORTHANC_IMAGE_UNDER_TESTS"] = Helpers.orthanc_under_tests_docker_image
        subprocess.run(["docker", "compose", "-f", "docker-compose-transfers-concurrency.yml", "down", "-v", "--remove-orphans"], 
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
        subprocess.run(["docker", "compose", "-f", "docker-compose-transfers-concurrency.yml", "up", "-d"], 
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
        oa = OrthancApiClient("http://localhost:8062")
        ob = OrthancApiClient("http://localhost:8063")

        oa.wait_started()
        ob.wait_started()

        oa.delete_all_content()
        ob.delete_all_content()

        return oa, ob

    def test_push(self):
        oa, ob = self.clean_start()

        populator = OrthancTestDbPopulator(oa, studies_count=2, series_count=2, instances_count=200, random_seed=65)
        populator.execute()

        all_studies_ids = oa.studies.get_all_ids()
        instances_count = oa.get_statistics().instances_count
        disk_size = oa.get_statistics().total_disk_size
        repeat_count = 2

        for compression in [True, False]:
            start_time = time.time()

            for i in range(0, repeat_count):
                oa.transfers.send(target_peer='b',
                                  resources_ids=all_studies_ids,
                                  resource_type=ResourceType.STUDY,
                                  compress=compression)
                
                self.assertEqual(instances_count, ob.get_statistics().instances_count)
                self.assertEqual(disk_size, ob.get_statistics().total_disk_size)

                # check the computed count tags
                studies = ob.get_json("/studies?requested-tags=NumberOfStudyRelatedInstances;NumberOfStudyRelatedSeries&expand=true")
                for study in studies:
                    instance_count_a = len(oa.studies.get_instances_ids(study["ID"]))
                    instance_count_b = len(ob.studies.get_instances_ids(study["ID"]))
                    self.assertEqual(instance_count_a, instance_count_b)
                    self.assertEqual(instance_count_a, int(study['RequestedTags']['NumberOfStudyRelatedInstances']))
                    self.assertEqual(2, int(study['RequestedTags']['NumberOfStudyRelatedSeries']))

                ob.delete_all_content()

            elapsed = time.time() - start_time
            print(f"TIMING test_push (compression={compression}) with {instances_count} instances for a total of {disk_size/(1024*1024)} MB (repeat {repeat_count}x): {elapsed:.3f} s")


    def test_pull(self):
        oa, ob = self.clean_start()

        populator = OrthancTestDbPopulator(ob, studies_count=2, series_count=2, instances_count=200, random_seed=65)
        populator.execute()

        all_studies_ids = ob.studies.get_all_ids()
        instances_count = ob.get_statistics().instances_count
        disk_size = ob.get_statistics().total_disk_size
        repeat_count = 2

        for compression in [True, False]:
            start_time = time.time()

            for i in range(0, repeat_count):
                remote_job = ob.transfers.send_async(target_peer='a',
                                                    resources_ids=all_studies_ids,
                                                    resource_type=ResourceType.STUDY,
                                                    compress=compression)
                job = oa.jobs.get(orthanc_id=remote_job.remote_job_id)
                job.wait_completed(polling_interval=0.1)

                self.assertEqual(instances_count, oa.get_statistics().instances_count)
                self.assertEqual(disk_size, oa.get_statistics().total_disk_size)

                # check the computed count tags
                studies = oa.get_json("/studies?requested-tags=NumberOfStudyRelatedInstances;NumberOfStudyRelatedSeries&expand=true")
                for study in studies:
                    instance_count_a = len(oa.studies.get_instances_ids(study["ID"]))
                    instance_count_b = len(ob.studies.get_instances_ids(study["ID"]))
                    self.assertEqual(instance_count_a, instance_count_b)
                    self.assertEqual(instance_count_a, int(study['RequestedTags']['NumberOfStudyRelatedInstances']))
                    self.assertEqual(2, int(study['RequestedTags']['NumberOfStudyRelatedSeries']))

                oa.delete_all_content()


            elapsed = time.time() - start_time
            print(f"TIMING test_pull (compression={compression}) with {instances_count} instances for a total of {disk_size/(1024*1024)} MB (repeat {repeat_count}x): {elapsed:.3f} s")
