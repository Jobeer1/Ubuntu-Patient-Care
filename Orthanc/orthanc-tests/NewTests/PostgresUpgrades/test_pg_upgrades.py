import subprocess
import time
import unittest
from orthanc_api_client import OrthancApiClient
from helpers import Helpers, wait_container_healthy

import pathlib
import os
here = pathlib.Path(__file__).parent.resolve()


class TestPgUpgrades(unittest.TestCase):

    @classmethod
    def cleanup(cls):
        os.chdir(here)
        print("Cleaning old compose")
        subprocess.run(["docker", "compose", "down", "-v", "--remove-orphans"], check=True)


    @classmethod
    def setUpClass(cls):
        cls.cleanup()

    @classmethod
    def tearDownClass(cls):
        cls.cleanup()


    def test_upgrade_previous_revision_to_current(self):
        # remove everything including the DB from previous tests
        TestPgUpgrades.cleanup()

        print("Pullling container")
        subprocess.run(["docker", "compose", "pull"], check=True)

        print("Launching PG-15 server")
        subprocess.run(["docker", "compose", "up", "pg-15", "-d"], check=True)
        wait_container_healthy("pg-15")

        print("Launching Orthanc with DB previous-revision")
        subprocess.run(["docker", "compose", "up", "orthanc-pg-15-previous-revision", "-d"], check=True)

        o = OrthancApiClient("http://localhost:8052")
        o.wait_started()

        instances = o.upload_folder(here / "../../Database/Knee")

        print("Stopping Orthanc with DB previous-revision")
        subprocess.run(["docker", "compose", "stop", "orthanc-pg-15-previous-revision"], check=True)
        time.sleep(2)

        print("Launching newest Orthanc")
        subprocesss_env = os.environ.copy()
        subprocesss_env["ORTHANC_IMAGE_UNDER_TESTS"] = Helpers.orthanc_under_tests_docker_image
        subprocess.run(["docker", "compose", "up", "orthanc-pg-15-under-tests", "-d"], 
                       env=subprocesss_env, check=True)


        o = OrthancApiClient("http://localhost:8050")
        o.wait_started()

        # make sure we can 'play' with this Orthanc
        o.instances.get_tags(orthanc_id=instances[0])
        o.instances.delete_all()
        self.assertEqual(0, int(o.get_json('statistics')['TotalDiskSize']))
        instances = o.upload_folder(here / "../../Database/Knee")
        size_before_downgrade = int(o.get_json('statistics')['TotalDiskSize'])

        print("Stopping newest Orthanc ")
        subprocess.run(["docker", "compose", "stop", "orthanc-pg-15-under-tests"], check=True)
        time.sleep(2)

    
    # test a full upgrade from a very old version, and a downgrade to the previous version (where we run the integration tests)
    def test_upgrades_downgrades_with_pg_15(self):

        # remove everything including the DB from previous tests
        TestPgUpgrades.cleanup()

        print("Pullling container")
        subprocess.run(["docker", "compose", "pull"], check=True)

        print("Launching PG-15 server")
        subprocess.run(["docker", "compose", "up", "pg-15", "-d"], check=True)
        wait_container_healthy("pg-15")

        print("Launching old Orthanc (PG v2.0)")
        subprocess.run(["docker", "compose", "up", "orthanc-pg-15-2", "-d"], check=True)

        o = OrthancApiClient("http://localhost:8049")
        o.wait_started()

        instances = o.upload_folder(here / "../../Database/Knee")

        print("Stopping old Orthanc ")
        subprocess.run(["docker", "compose", "stop", "orthanc-pg-15-2"], check=True)
        time.sleep(2)

        print("Launching newest Orthanc")
        subprocesss_env = os.environ.copy()
        subprocesss_env["ORTHANC_IMAGE_UNDER_TESTS"] = Helpers.orthanc_under_tests_docker_image
        subprocess.run(["docker", "compose", "up", "orthanc-pg-15-under-tests", "-d"], 
                       env=subprocesss_env, check=True)

        o = OrthancApiClient("http://localhost:8050")
        o.wait_started()

        # make sure we can 'play' with Orthanc
        o.instances.get_tags(orthanc_id=instances[0])
        o.instances.delete_all()
        self.assertEqual(0, int(o.get_json('statistics')['TotalDiskSize']))
        instances = o.upload_folder(here / "../../Database/Knee")
        size_before_downgrade = int(o.get_json('statistics')['TotalDiskSize'])

        print("Stopping newest Orthanc ")
        subprocess.run(["docker", "compose", "stop", "orthanc-pg-15-under-tests"], check=True)
        time.sleep(2)

        print("Downgrading Orthanc DB to previous-revision")
        subprocess.run(["docker", "exec", "pg-15", "./scripts/downgrade.sh"], check=True)
        time.sleep(2)

        print("Launching previous Orthanc (DB previous-revision)")
        subprocess.run(["docker", "compose", "up", "orthanc-pg-15-previous-revision", "-d"], check=True)

        o = OrthancApiClient("http://localhost:8052")
        o.wait_started()

        # make sure we can 'play' with Orthanc
        o.instances.get_tags(orthanc_id=instances[0])
        self.assertEqual(size_before_downgrade, int(o.get_json('statistics')['TotalDiskSize']))
        o.instances.delete_all()
        self.assertEqual(0, int(o.get_json('statistics')['TotalDiskSize']))
        instances = o.upload_folder(here / "../../Database/Knee")
        o.instances.delete_all()
        self.assertEqual(0, int(o.get_json('statistics')['TotalDiskSize']))

        print("run the integration tests after a downgrade")
        # first create the containers (orthanc-tests + orthanc-pg-15-previous-revision-for-integ-tests) so they know each other
        subprocess.run(["docker", "compose", "create", "orthanc-tests"], check=True)

        subprocess.run(["docker", "compose", "up", "orthanc-pg-15-previous-revision-for-integ-tests", "-d"], check=True)

        o = OrthancApiClient("http://localhost:8053", user="alice", pwd="orthanctest")
        o.wait_started()

        # time.sleep(10000)
        subprocess.run(["docker", "compose", "up", "orthanc-tests", "--exit-code-from", "orthanc-tests"], check=True)



    # make sure we can still start a new Orthanc with an Old PG server
    def test_latest_orthanc_with_pg_9(self):

        # remove everything including the DB from previous tests
        TestPgUpgrades.cleanup()

        print("Launching PG-9 server")
        subprocess.run(["docker", "compose", "up", "pg-9", "-d"], check=True)
        wait_container_healthy("pg-9")

        print("Launching newest Orthanc")
        subprocesss_env = os.environ.copy()
        subprocesss_env["ORTHANC_IMAGE_UNDER_TESTS"] = Helpers.orthanc_under_tests_docker_image
        subprocess.run(["docker", "compose", "up", "orthanc-pg-9-under-tests", "-d"], 
                       env=subprocesss_env, check=True)

        o = OrthancApiClient("http://localhost:8051")
        o.wait_started()
        instances = o.upload_folder(here / "../../Database/Knee")
        o.instances.delete(orthanc_ids=instances)

        subprocess.run(["docker", "compose", "down", "-v", "--remove-orphans"], check=True)
