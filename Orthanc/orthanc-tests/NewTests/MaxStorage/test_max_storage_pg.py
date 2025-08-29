import unittest
import time
import os
import threading
from helpers import OrthancTestCase, Helpers

from orthanc_api_client import OrthancApiClient, ChangeType
from orthanc_api_client.exceptions import HttpError
from orthanc_api_client import helpers as OrthancHelpers

from orthanc_tools import OrthancTestDbPopulator

import pathlib
import subprocess
import glob
here = pathlib.Path(__file__).parent.resolve()


class TestMaxStoragePG(OrthancTestCase):

    @classmethod
    def terminate(cls):

        if Helpers.is_docker():
            subprocess.run(["docker", "rm", "-f", "pg-server"])
        else:
            cls.pg_service_process.terminate()


    @classmethod
    def prepare(cls):
        test_name = "MaxStoragePG"
        cls._storage_name = "max-storage-pg"
        network_name = "max-storage-pg"

        print(f'-------------- preparing {test_name} tests')

        cls.clear_storage(storage_name=cls._storage_name)

        pg_hostname = "localhost"
        if Helpers.is_docker():
            pg_hostname = "pg-server"
            cls.create_docker_network(network_name)

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
            "MaximumStorageSize": 1,
            "MaximumStorageMode": "Recycle"
            # "MaximumPatientCount": 1,
            # "MaximumStorageMode": "Reject"
        }

        config_path = cls.generate_configuration(
            config_name=f"{test_name}",
            storage_name=cls._storage_name,
            config=config,
            plugins=Helpers.plugins
        )

        # launch the docker PG server
        print('--------------- launching PostgreSQL server ------------------')

        pg_cmd = [            
            "docker", "run", "--rm", 
            "-p", "5432:5432", 
            "--name", "pg-server",
            "--env", "POSTGRES_HOST_AUTH_METHOD=trust"
            ]
        
        if Helpers.is_docker():
            pg_cmd.extend(["--network", network_name])
        pg_cmd.append("postgres:15")

        cls.pg_service_process = subprocess.Popen(pg_cmd)
        time.sleep(5)

        if Helpers.break_after_preparation:
            print(f"++++ It is now time to start your Orthanc under tests with configuration file '{config_path}' +++++")
            input("Press Enter to continue")
        else:
            cls.launch_orthanc_under_tests(
                config_name=f"{test_name}",
                storage_name=cls._storage_name,
                config=config,
                plugins=Helpers.plugins,
                docker_network=network_name
            )

        cls.o = OrthancApiClient(cls.o._root_url)
        cls.o.wait_started()
        cls.o.delete_all_content()


    def test_upload(self):
        self.o.delete_all_content()
        self.clear_storage(storage_name=self._storage_name)

        uploaded_instances_ids = []
        counter = 0
        # upload 10 images of 500x500, since the MaximumStorageSize is 1MB, only 2 of them should remain in the storage
        for i in range(0, 10):
            counter += 1
            dicom_file = OrthancHelpers.generate_test_dicom_file(width=500, height=500,
                                                                tags = {
                                                                    "PatientID" : f"{i}",
                                                                    "StudyInstanceUID" : f"{i}",
                                                                    "SeriesInstanceUID" : f"{i}.{counter%10}"
                                                                })
            try:
                uploaded_instances_ids.extend(self.o.upload(dicom_file))
            except HttpError as er:
                if er.http_status_code == 507:
                    pass  # ignore

        # some instances have been discarded
        self.assertLess(len(self.o.instances.get_all_ids()), 10)
        self.assertLess(len(self.o.patients.get_all_ids()), 10)
        self.assertLess(self.o.get_statistics().total_disk_size, 1*1024*1024)
