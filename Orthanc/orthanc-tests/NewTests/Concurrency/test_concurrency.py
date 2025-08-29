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


def worker_upload_folder(orthanc_root_url: str, folder: str, repeat: int, worker_id: int):
    o = OrthancApiClient(orthanc_root_url)
    for i in range(0, repeat):
        o.upload_folder(folder, ignore_errors=True)

def worker_anonymize_study(orthanc_root_url: str, study_id: str, repeat: int, worker_id: int):
    o = OrthancApiClient(orthanc_root_url)
    
    for i in range(0, repeat):
        o.studies.anonymize(orthanc_id=study_id, delete_original=False)

def count_changes(changes, type: ChangeType):
    return len([c.change_type for c in changes if c.change_type==type])

def worker_upload_delete_study_part(orthanc_root_url: str, folder: str, repeat: int, workers_count: int, worker_id: int):
    o = OrthancApiClient(orthanc_root_url)

    all_files = glob.glob(os.path.join(folder, '*.dcm'))
    
    for i in range(0, repeat):
        instances_ids = []

        for i in range(0, len(all_files)):
            if i % workers_count == worker_id:  # each thread takes a part
                instances_ids.extend(o.upload_file(all_files[i]))

        for instance_id in instances_ids:
            o.instances.delete(orthanc_id=instance_id, ignore_errors=True)


def worker_upload_delete_test_dicoms(orthanc_root_url: str, files_count: int, worker_id: int):
    o = OrthancApiClient(orthanc_root_url)

    instances_ids = []
    counter = 0

    for i in range(0, files_count):
        counter += 1
        dicom_file = OrthancHelpers.generate_test_dicom_file(width=4, height=4,
                                                             tags = {
                                                                 "PatientID" : f"{worker_id}",
                                                                 "StudyInstanceUID" : f"{worker_id}",
                                                                 "SeriesInstanceUID" : f"{worker_id}.{counter%10}"
                                                             })
        instances_ids.extend(o.upload(dicom_file))

    study_id = o.instances.get_parent_study_id(instances_ids[0])
    o.studies.delete(orthanc_id=study_id)


class TestConcurrency(OrthancTestCase):

    @classmethod
    def terminate(cls):

        if Helpers.is_docker():
            subprocess.run(["docker", "rm", "-f", "pg-server"])
        else:
            cls.pg_service_process.terminate()


    @classmethod
    def prepare(cls):
        test_name = "Concurrency"
        cls._storage_name = "concurrency"

        print(f'-------------- preparing {test_name} tests')

        cls.clear_storage(storage_name=cls._storage_name)

        pg_hostname = "localhost"
        if Helpers.is_docker():
            pg_hostname = "pg-server"
            cls.create_docker_network("concurrency")

        config = { 
            "PostgreSQL" : {
                "EnableStorage": False,
                "EnableIndex": True,
                "Host": pg_hostname,
                "Port": 5432,
                "Database": "postgres",
                "Username": "postgres",
                "Password": "postgres",
                "IndexConnectionsCount": 10,
                "MaximumConnectionRetries" : 2000,
                "ConnectionRetryInterval" : 5,
                "TransactionMode": "ReadCommitted",
                #"TransactionMode": "Serializable",
                "EnableVerboseLogs": True
            },
            "AuthenticationEnabled": False,
            "OverwriteInstances": True,
            "JobsEngineThreadsCount" : {
                "ResourceModification": 8
            },
        }

        config_path = cls.generate_configuration(
            config_name=f"{test_name}",
            storage_name=cls._storage_name,
            config=config,
            plugins=Helpers.plugins
        )

        # launch the docker PG server
        print('--------------- launching PostgreSQL server ------------------')

        cls.pg_service_process = subprocess.Popen([
            "docker", "run", "--rm", 
            "-p", "5432:5432", 
            "--network", "concurrency", 
            "--name", "pg-server",
            "--env", "POSTGRES_HOST_AUTH_METHOD=trust",
            "postgres:15"])
        time.sleep(5)

        if Helpers.break_before_preparation:
            print(f"++++ It is now time to start your Orthanc under tests with configuration file '{config_path}' +++++")
            input("Press Enter to continue")
        else:
            cls.launch_orthanc_under_tests(
                config_name=f"{test_name}",
                storage_name=cls._storage_name,
                config=config,
                plugins=Helpers.plugins,
                docker_network="concurrency"
            )

        cls.o = OrthancApiClient(cls.o._root_url)
        cls.o.wait_started()
        cls.o.delete_all_content()

    def check_is_empty(self):
        self.assertEqual(0, len(self.o.studies.get_all_ids()))
        self.assertEqual(0, len(self.o.series.get_all_ids()))
        self.assertEqual(0, len(self.o.instances.get_all_ids()))

        stats = self.o.get_json("statistics")
        self.assertEqual(0, stats.get("CountPatients"))
        self.assertEqual(0, stats.get("CountStudies"))
        self.assertEqual(0, stats.get("CountSeries"))
        self.assertEqual(0, stats.get("CountInstances"))
        self.assertEqual(0, int(stats.get("TotalDiskSize")))
        # time.sleep(10000)
        self.assertTrue(self.is_storage_empty(self._storage_name))

        # all changes shall have been deleted as well
        changes, last_change, done = self.o.get_changes(since=0, limit=100000)
        self.assertTrue(done)
        self.assertEqual(0, len(changes))


    def execute_workers(self, worker_func, worker_args, workers_count):
        workers = []
        for i in range(0, workers_count):
            t = threading.Thread(target=worker_func, args=worker_args + (i, ))
            workers.append(t)
            t.start()

        for t in workers:
            t.join()

    def test_concurrent_uploads_same_study(self):
        if self.o.is_orthanc_version_at_least(1, 12, 4):

            self.o.delete_all_content()
            self.clear_storage(storage_name=self._storage_name)

            start_time = time.time()
            workers_count = 20
            repeat_count = 5

            # massively reupload the same study multiple times with OverwriteInstances set to true
            # Make sure the studies, series and instances are created only once
            self.execute_workers(
                worker_func=worker_upload_folder,
                worker_args=(self.o._root_url, here / "../../Database/Knee", repeat_count,),
                workers_count=workers_count)

            elapsed = time.time() - start_time
            print(f"TIMING test_concurrent_uploads_same_study with {workers_count} workers and {repeat_count}x repeat: {elapsed:.3f} s")

            self.assertTrue(self.o.is_alive())

            self.assertEqual(1, len(self.o.studies.get_all_ids()))
            self.assertEqual(2, len(self.o.series.get_all_ids()))
            self.assertEqual(50, len(self.o.instances.get_all_ids()))

            # check the computed count tags
            patients = self.o.get_json("/patients?requested-tags=NumberOfPatientRelatedInstances;NumberOfPatientRelatedSeries;NumberOfPatientRelatedStudies&expand=true")
            self.assertEqual(50, int(patients[0]['RequestedTags']['NumberOfPatientRelatedInstances']))
            self.assertEqual(2, int(patients[0]['RequestedTags']['NumberOfPatientRelatedSeries']))
            self.assertEqual(1, int(patients[0]['RequestedTags']['NumberOfPatientRelatedStudies']))


            stats = self.o.get_json("statistics")
            self.assertEqual(1, stats.get("CountPatients"))
            self.assertEqual(1, stats.get("CountStudies"))
            self.assertEqual(2, stats.get("CountSeries"))
            self.assertEqual(50, stats.get("CountInstances"))
            self.assertEqual(4118738, int(stats.get("TotalDiskSize")))

            self.o.instances.delete(orthanc_ids=self.o.instances.get_all_ids())

            self.check_is_empty()

    def test_concurrent_anonymize_same_study(self):
        self.o.delete_all_content()
        self.clear_storage(storage_name=self._storage_name)

        self.o.upload_folder(here / "../../Database/Knee")
        study_id = self.o.studies.get_all_ids()[0]

        start_time = time.time()
        workers_count = 4
        repeat_count = 10

        # massively anonymize the same study.  This generates new studies and is a
        # good way to simulate ingestion of new studies
        self.execute_workers(
            worker_func=worker_anonymize_study,
            worker_args=(self.o._root_url, study_id, repeat_count,),
            workers_count=workers_count)

        elapsed = time.time() - start_time
        print(f"TIMING test_concurrent_anonymize_same_study with {workers_count} workers and {repeat_count}x repeat: {elapsed:.3f} s")

        self.assertTrue(self.o.is_alive())

        self.assertEqual(1 + workers_count * repeat_count, len(self.o.studies.get_all_ids()))
        self.assertEqual(2 * (1 + workers_count * repeat_count), len(self.o.series.get_all_ids()))
        self.assertEqual(50 * (1 + workers_count * repeat_count), len(self.o.instances.get_all_ids()))

        stats = self.o.get_json("statistics")
        self.assertEqual(1 + workers_count * repeat_count, stats.get("CountPatients"))
        self.assertEqual(1 + workers_count * repeat_count, stats.get("CountStudies"))
        self.assertEqual(2 * (1 + workers_count * repeat_count), stats.get("CountSeries"))
        self.assertEqual(50 * (1 + workers_count * repeat_count), stats.get("CountInstances"))
        changes, last_change, done = self.o.get_changes(since=0, limit=100000)
        self.assertTrue(done)

        self.assertEqual(1 + workers_count * repeat_count, count_changes(changes, ChangeType.NEW_PATIENT))
        self.assertEqual(1 + workers_count * repeat_count, count_changes(changes, ChangeType.NEW_STUDY))
        self.assertEqual(2 * (1 + workers_count * repeat_count), count_changes(changes, ChangeType.NEW_SERIES))
        self.assertEqual(50 * (1 + workers_count * repeat_count), count_changes(changes, ChangeType.NEW_INSTANCE))

        # check the computed count tags
        patients = self.o.get_json("/patients?requested-tags=NumberOfPatientRelatedInstances;NumberOfPatientRelatedSeries;NumberOfPatientRelatedStudies&expand=true")
        for patient in patients:
            self.assertEqual(50, int(patient['RequestedTags']['NumberOfPatientRelatedInstances']))
            self.assertEqual(2, int(patient['RequestedTags']['NumberOfPatientRelatedSeries']))
            self.assertEqual(1, int(patient['RequestedTags']['NumberOfPatientRelatedStudies']))

        start_time = time.time()

        self.o.instances.delete(orthanc_ids=self.o.instances.get_all_ids())

        elapsed = time.time() - start_time
        print(f"TIMING test_concurrent_anonymize_same_study deletion took: {elapsed:.3f} s")

        self.check_is_empty()


    def test_upload_delete_same_study_from_multiple_threads(self):
        self.o.delete_all_content()
        self.clear_storage(storage_name=self._storage_name)

        start_time = time.time()
        overall_repeat = 10

        for i in range(0, overall_repeat):
            workers_count = 5
            repeat_count = 3

            # massively upload and delete the same study.  Each worker is writing a part of the instances and deleting them.
            # We are trying to have multiple workers deleting the last instance of a study at the same time.
            self.execute_workers(
                worker_func=worker_upload_delete_study_part,
                worker_args=(self.o._root_url, here / "../../Database/Knee/T1", repeat_count, workers_count, ),
                workers_count=workers_count)

            self.check_is_empty()

        # let's upload it one more time and check the children counts
        self.o.upload_folder(here / "../../Database/Knee")
        patients = self.o.get_json("/patients?requested-tags=NumberOfPatientRelatedInstances;NumberOfPatientRelatedSeries;NumberOfPatientRelatedStudies&expand=true")
        self.assertEqual(50, int(patients[0]['RequestedTags']['NumberOfPatientRelatedInstances']))
        self.assertEqual(2, int(patients[0]['RequestedTags']['NumberOfPatientRelatedSeries']))
        self.assertEqual(1, int(patients[0]['RequestedTags']['NumberOfPatientRelatedStudies']))

        elapsed = time.time() - start_time
        print(f"TIMING test_upload_delete_same_study_from_multiple_threads with {workers_count} workers and {repeat_count}x repeat ({overall_repeat}x): {elapsed:.3f} s")


    def test_upload_multiple_studies_from_multiple_threads(self):
        self.o.delete_all_content()
        self.clear_storage(storage_name=self._storage_name)

        start_time = time.time()
        overall_repeat = 3

        for i in range(0, overall_repeat):
            files_count = 25
            workers_count = 10

            # massively upload and delete all studies from the test detabase.  Each worker is writing all instances from a folder and then deletes them.
            # This test is only measuring performances.
            self.execute_workers(
                worker_func=worker_upload_delete_test_dicoms,
                worker_args=(self.o._root_url, files_count, ),
                workers_count=workers_count)

            self.check_is_empty()

        elapsed = time.time() - start_time
        print(f"TIMING test_upload_multiple_studies_from_multiple_threads with {workers_count} workers and {files_count} files and repeat {overall_repeat}x: {elapsed:.3f} s")

    # transfers + dicomweb