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


class TestReadOnlyPG(OrthancTestCase):

    @classmethod
    def terminate(cls):

        if Helpers.is_docker():
            subprocess.run(["docker", "rm", "-f", "pg-server"])
        else:
            cls.pg_service_process.terminate()


    @classmethod
    def prepare(cls):
        test_name = "ReadOnlyPG"
        cls._storage_name = "read-only-pg"  #actually not used since we are using PG storage
        network_name = "read-only-pg"

        print(f'-------------- preparing {test_name} tests')

        pg_hostname = "localhost"
        if Helpers.is_docker():
            pg_hostname = "pg-server"
            cls.create_docker_network(network_name)

        config = { 
            "PostgreSQL" : {
                "EnableStorage": True,
                "EnableIndex": True,
                "Host": pg_hostname,
                "Port": 5432,
                "Database": "postgres",
                "Username": "postgres",
                "Password": "postgres",
                "IndexConnectionsCount": 10,
                "MaximumConnectionRetries" : 20,
                "ConnectionRetryInterval" : 1,
                "TransactionMode": "ReadCommitted",
                "EnableVerboseLogs": True
            },
            "AuthenticationEnabled": False,
            "OverwriteInstances": True,
            "ReadOnly": False,               # disable for preparation
            "DicomWeb": {
                "EnableMetadataCache": False # disable for preparation
            }
        }

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

        print('--------------- launching Orthanc to prepare DB ------------------')
        cls.launch_orthanc_to_prepare_db(
            config_name=f"{test_name}",
            storage_name=cls._storage_name,
            config=config,
            plugins=Helpers.plugins,
            docker_network=network_name
        )

        # upload a study
        cls.uploaded_instances_ids = cls.o.upload_folder(here / "../../Database/Knix/Loc")
        cls.one_instance_id = cls.uploaded_instances_ids[0]
        cls.one_series_id = cls.o.instances.get_parent_series_id(cls.one_instance_id)
        cls.one_study_id = cls.o.series.get_parent_study_id(cls.one_series_id)
        cls.one_patient_id = cls.o.studies.get_parent_patient_id(cls.one_study_id)

        cls.kill_orthanc()

        print('--------------- stopped preparation Orthanc  ------------------')

        time.sleep(3)

        # modify config for the readonly version
        config["ReadOnly"] = True
        config["DicomWeb"]["EnableMetadataCache"] = True

        config_path = cls.generate_configuration(
            config_name=f"{test_name}",
            storage_name=cls._storage_name,
            config=config,
            plugins=Helpers.plugins
        )

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


    def test_write_methods_fail(self):
        self.assertRaises(Exception, lambda: self.o.upload_folder(here / "../../Database/Knix/Loc"))
        self.assertRaises(Exception, lambda: self.o.instances.delete(self.one_instance_id))
        self.assertRaises(Exception, lambda: self.o.series.delete(self.one_series_id))
        self.assertRaises(Exception, lambda: self.o.studies.delete(self.one_study_id))
        self.assertRaises(Exception, lambda: self.o.patients.delete(self.one_patient_id))
        
        tags = self.o.instances.get_tags(self.one_instance_id)



    def test_read_methods_succeed(self):
        # nothing should raise
        tags = self.o.instances.get_tags(self.one_instance_id)

        self.o.get_json(f"/dicom-web/studies/{tags['StudyInstanceUID']}/metadata")
        self.o.get_json(f"/dicom-web/studies/{tags['StudyInstanceUID']}/series/{tags['SeriesInstanceUID']}/metadata")
        self.o.get_json(f"/statistics") 
