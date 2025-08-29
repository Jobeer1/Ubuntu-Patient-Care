import unittest
import time
import pprint
import subprocess
from helpers import OrthancTestCase, Helpers

from orthanc_api_client import OrthancApiClient, generate_test_dicom_file
from orthanc_api_client import exceptions as orthanc_exceptions

import logging
import pathlib
here = pathlib.Path(__file__).parent.resolve()



class TestAuthorization(OrthancTestCase):

    label_a_study_id = None
    label_b_study_id = None
    no_label_study_id = None
    auth_service_process = None

    @classmethod
    def terminate(cls):

        if Helpers.is_docker():
            subprocess.run(["docker", "rm", "-f", "auth-service"])
        else:
            cls.auth_service_process.terminate()

    @classmethod
    def prepare(cls):
        test_name = "Authorization"
        storage_name = "authorization"

        print(f'-------------- preparing {test_name} tests')

        cls.clear_storage(storage_name=storage_name)

        auth_service_hostname = "localhost"
        if Helpers.is_docker():
            auth_service_hostname = "auth-service"
            cls.create_docker_network("auth-test-network")

        config = {
                "AuthenticationEnabled": False,
                "Authorization": {
                    "WebServiceRootUrl": f"http://{auth_service_hostname}:8020/",
                    "StandardConfigurations": [
                        "orthanc-explorer-2",
                        "stone-webviewer"
                    ],
                    "CheckedLevel": "studies",
                    "TokenHttpHeaders": ["user-token-key", "resource-token-key"],
                    "TokenGetArguments": ["resource-token-key"],
                    "UncheckedFolders": ["/plugins"]    # to allow testing plugin version while it is not included by default in the auth-plugin
                },
                "DicomWeb": {
                    "Enable": True
                },
                "StableAge": 5000 # not to be disturbed by StableAge events while debugging
            }

        config_path = cls.generate_configuration(
            config_name=f"{test_name}",
            storage_name=storage_name,
            config=config,
            plugins=Helpers.plugins
        )

        if Helpers.is_exe():
            # Start the auth-service application as a subprocess and wait for it to start
            cls.auth_service_process = subprocess.Popen(["uvicorn", "auth_service:app", "--host", "0.0.0.0", "--port", "8020"], cwd=here)
            time.sleep(2)
        else:
            # first build the docker image for the auth-service
            subprocess.run(["docker", "build", "-t", "auth-service", "."], cwd=here)
            cls.auth_service_process = subprocess.Popen(["docker", "run", "-p", "8020:8020", "--network", "auth-test-network", "--name", "auth-service", "auth-service"])
            time.sleep(5)


        if Helpers.break_before_preparation:
            print(f"++++ It is now time to start your Orthanc under tests with configuration file '{config_path}' +++++")
            input("Press Enter to continue")
        else:
            cls.launch_orthanc_under_tests(
                config_name=f"{test_name}",
                storage_name=storage_name,
                config=config,
                plugins=Helpers.plugins,
                docker_network="auth-test-network"
            )

        o = OrthancApiClient(cls.o._root_url, headers={"user-token-key": "token-uploader"})

        o.delete_all_content()

        # upload a few studies and add labels
        cls.label_a_instance_id = o.upload_file(here / "../../Database/Knix/Loc/IM-0001-0001.dcm")[0]
        cls.label_a_study_id = o.instances.get_parent_study_id(cls.label_a_instance_id)
        cls.label_a_series_id = o.instances.get_parent_series_id(cls.label_a_instance_id)
        cls.label_a_patient_dicom_id = o.studies.get_tags(cls.label_a_study_id)["PatientID"]
        cls.label_a_study_dicom_id = o.studies.get_tags(cls.label_a_study_id)["StudyInstanceUID"]
        cls.label_a_series_dicom_id = o.series.get_tags(cls.label_a_series_id)["SeriesInstanceUID"]
        cls.label_a_instance_dicom_id = o.instances.get_tags(cls.label_a_instance_id)["SOPInstanceUID"]
        o.studies.add_label(cls.label_a_study_id, "label_a")

        cls.label_b_instance_id = o.upload_file(here / "../../Database/Brainix/Epi/IM-0001-0001.dcm")[0]
        cls.label_b_study_id = o.instances.get_parent_study_id(cls.label_b_instance_id)
        cls.label_b_series_id = o.instances.get_parent_series_id(cls.label_b_instance_id)
        cls.label_b_patient_dicom_id = o.studies.get_tags(cls.label_b_study_id)["PatientID"]
        cls.label_b_study_dicom_id = o.studies.get_tags(cls.label_b_study_id)["StudyInstanceUID"]
        cls.label_b_series_dicom_id = o.series.get_tags(cls.label_b_series_id)["SeriesInstanceUID"]
        cls.label_b_instance_dicom_id = o.instances.get_tags(cls.label_b_instance_id)["SOPInstanceUID"]
        o.studies.add_label(cls.label_b_study_id, "label_b")

        instances_ids = o.upload_file(here / "../../Database/Comunix/Pet/IM-0001-0001.dcm")
        cls.no_label_study_id = o.instances.get_parent_study_id(instances_ids[0])

        cls.no_label_instance_id = o.upload_file(here / "../../Database/Comunix/Pet/IM-0001-0001.dcm")[0]
        cls.no_label_study_id = o.instances.get_parent_study_id(cls.no_label_instance_id)
        cls.no_label_series_id = o.instances.get_parent_series_id(cls.no_label_instance_id)
        cls.no_label_patient_dicom_id = o.studies.get_tags(cls.no_label_study_id)["PatientID"]
        cls.no_label_study_dicom_id = o.studies.get_tags(cls.no_label_study_id)["StudyInstanceUID"]
        cls.no_label_series_dicom_id = o.series.get_tags(cls.no_label_series_id)["SeriesInstanceUID"]
        cls.no_label_instance_dicom_id = o.instances.get_tags(cls.no_label_instance_id)["SOPInstanceUID"]

        cls.both_labels_instance_id = o.upload_file(here / "../../Database/Phenix/IM-0001-0001.dcm")[0]
        cls.both_labels_study_id = o.instances.get_parent_study_id(cls.both_labels_instance_id)
        cls.both_labels_series_id = o.instances.get_parent_series_id(cls.both_labels_instance_id)
        cls.both_labels_study_dicom_id = o.studies.get_tags(cls.both_labels_study_id)["StudyInstanceUID"]
        cls.both_labels_series_dicom_id = o.series.get_tags(cls.both_labels_series_id)["SeriesInstanceUID"]
        cls.both_labels_instance_dicom_id = o.instances.get_tags(cls.both_labels_instance_id)["SOPInstanceUID"]
        o.studies.add_label(cls.both_labels_study_id, "label_a")
        o.studies.add_label(cls.both_labels_study_id, "label_b")
        o.series.add_label(cls.both_labels_series_id, "label_a")
        o.series.add_label(cls.both_labels_series_id, "label_b")


    def assert_is_forbidden(self, api_call):
        with self.assertRaises(orthanc_exceptions.HttpError) as ctx:
            api_call()
        self.assertEqual(403, ctx.exception.http_status_code)


    def test_admin_user(self):
        
        o = OrthancApiClient(self.o._root_url, headers={"user-token-key": "token-admin"})

        # make sure we can access all these urls (they would throw if not)
        system = o.get_system()

        # make sure we can access all studies
        o.studies.get_tags(self.no_label_study_id)
        o.studies.get_tags(self.label_a_study_id)
        o.studies.get_tags(self.label_b_study_id)

        # make sure we can access series and instances of these studies
        series_ids = o.studies.get_series_ids(self.label_a_study_id)
        instances_ids = o.series.get_instances_ids(series_ids[0])
        o.instances.get_tags(instances_ids[0])

        if o.is_plugin_version_at_least("authorization", 0, 9, 0):
            # make sure labels filtering still works
            self.assertEqual(4, len(o.studies.find(query={},
                                                labels=[],
                                                labels_constraint='Any')))

            self.assertEqual(3, len(o.studies.find(query={},
                                                labels=['label_a', 'label_b'],
                                                labels_constraint='Any')))

        self.assertEqual(2, len(o.studies.find(query={},
                                               labels=['label_a'],
                                               labels_constraint='None')))

        all_labels = o.get_all_labels()
        self.assertEqual(2, len(all_labels))

    def test_user_a(self):
        
        o_admin = OrthancApiClient(self.o._root_url, headers={"user-token-key": "token-admin"})
        o = OrthancApiClient(self.o._root_url, headers={"user-token-key": "token-user-a"})

        # # make sure we can access all these urls (they would throw if not)
        system = o.get_system()

        all_labels = o.get_all_labels()
        self.assertEqual(1, len(all_labels))
        self.assertEqual("label_a", all_labels[0])

        # make sure we can access only the label_a studies
        self.assert_is_forbidden(lambda: o.studies.get_tags(self.label_b_study_id))
        self.assert_is_forbidden(lambda: o.studies.get_tags(self.no_label_study_id))

        # user_a shall not be able to upload a study
        self.assert_is_forbidden(lambda: o.upload_file(here / "../../Database/Beaufix/IM-0001-0001.dcm"))
        self.assert_is_forbidden(lambda: o.upload_files_dicom_web(paths = [here / "../../Database/Beaufix/IM-0001-0001.dcm"]))

        # should not raise
        o.studies.get_tags(self.label_a_study_id)

        # make sure we can access series and instances of the label_a studies
        series_ids = o.studies.get_series_ids(self.label_a_study_id)
        instances_ids = o.series.get_instances_ids(series_ids[0])
        o.instances.get_tags(instances_ids[0])

        # make sure we can not access series and instances of the label_b studies
        self.assert_is_forbidden(lambda: o.studies.get_series_ids(self.label_b_study_id))

        if o_admin.is_plugin_version_at_least("authorization", 0, 9, 0):
            # make sure tools/find only returns the label_a studies
            studies = o.studies.find(query={},
                                    labels=[],
                                    labels_constraint='Any')
            studies_orthanc_ids = [x.orthanc_id for x in studies]
            self.assertEqual(2, len(studies_orthanc_ids))
            self.assertIn(self.label_a_study_id, studies_orthanc_ids)
            self.assertIn(self.both_labels_study_id, studies_orthanc_ids)

            # if searching Any of label_a & label_b, return only label_a
            studies = o.studies.find(query={},
                                    labels=['label_a', 'label_b'],
                                    labels_constraint='Any')
            studies_orthanc_ids = [x.orthanc_id for x in studies]
            self.assertEqual(2, len(studies_orthanc_ids))
            self.assertIn(self.label_a_study_id, studies_orthanc_ids)
            self.assertIn(self.both_labels_study_id, studies_orthanc_ids)

        # if searching Any of label_b, expect a Forbidden access
        self.assert_is_forbidden(lambda: o.studies.find(query={},
                                                        labels=['label_b'],
                                                        labels_constraint='Any'))

        # if searching None of label_b, expect a Forbidden access because we are not able to compute this filter
        self.assert_is_forbidden(lambda: o.studies.find(query={},
                                                        labels=['label_b'],
                                                        labels_constraint='None'))

        # if searching All of label_b, expect a Forbidden access because we are not able to compute this filter
        self.assert_is_forbidden(lambda: o.studies.find(query={},
                                                        labels=['label_b'],
                                                        labels_constraint='All'))

        studies = o.studies.find(query={"PatientName": "KNIX"},  # KNIX is label_a
                                 labels=[],
                                 labels_constraint='Any')
        self.assertEqual(1, len(studies))

        studies = o.studies.find(query={"PatientName": "KNIX"},  # KNIX is label_a
                                 labels=['label_a'],
                                 labels_constraint='Any')
        self.assertEqual(1, len(studies))

        self.assert_is_forbidden(lambda: o.studies.find(query={"PatientName": "KNIX"},  # KNIX is label_a
                                                        labels=['label_b'],
                                                        labels_constraint='Any'))

        # make sure some generic routes are not accessible
        self.assert_is_forbidden(lambda: o.get_json('patients?expand'))
        self.assert_is_forbidden(lambda: o.get_json('studies?expand'))
        self.assert_is_forbidden(lambda: o.get_json('series?expand'))
        self.assert_is_forbidden(lambda: o.get_json('instances?expand'))
        self.assert_is_forbidden(lambda: o.get_json('studies'))
        self.assert_is_forbidden(lambda: o.get_json('studies/'))

        # make sure the label_a study is accessible (it does not throw)
        o.studies.get_tags(self.label_a_study_id)
        o.series.get_tags(self.label_a_series_id)
        o.instances.get_tags(self.label_a_instance_id)
        
        # make sure you can access a resource route with a user token (it does not throw)
        m = o.get_json(f"dicom-web/studies/{self.label_a_study_dicom_id}/metadata")
        self.assert_is_forbidden(lambda: o.get_json(f"dicom-web/studies/{self.label_b_study_dicom_id}/metadata"))

        if o_admin.is_plugin_version_at_least("authorization", 0, 7, 1):
            i = o.get_json(f"dicom-web/studies/{self.label_a_study_dicom_id}/instances")
            self.assert_is_forbidden(lambda: o.get_json(f"dicom-web/studies/{self.label_b_study_dicom_id}/instances"))

            i = o.get_binary(f"dicom-web/studies/{self.label_a_study_dicom_id}/series/{self.label_a_series_dicom_id}/instances/{self.label_a_instance_dicom_id}")
            self.assert_is_forbidden(lambda: o.get_binary(f"dicom-web/studies/{self.label_b_study_dicom_id}/series/{self.label_b_series_dicom_id}/instances/{self.label_b_instance_dicom_id}"))

            i = o.get_json(f"dicom-web/studies/{self.label_a_study_dicom_id}/series?includefield=00080021%2C00080031%2C0008103E%2C00200011")
            self.assert_is_forbidden(lambda: o.get_json(f"dicom-web/studies/{self.label_b_study_dicom_id}/series?includefield=00080021%2C00080031%2C0008103E%2C00200011"))

            o.get_json(f"/system")
            o.get_json(f"/plugins")
            o.get_json(f"/plugins/dicom-web")

        if o_admin.is_plugin_version_at_least("authorization", 0, 7, 2):
            # also check that this works with the admin user !
            i = o_admin.get_json(f"dicom-web/studies/{self.label_a_study_dicom_id}/instances")
            i = o_admin.get_binary(f"dicom-web/studies/{self.label_a_study_dicom_id}/series/{self.label_a_series_dicom_id}/instances/{self.label_a_instance_dicom_id}")
            i = o_admin.get_json(f"dicom-web/studies/{self.label_a_study_dicom_id}/series?includefield=00080021%2C00080031%2C0008103E%2C00200011")

        if o_admin.is_plugin_version_at_least("authorization", 0, 9, 0):
            # the user_a shall only see the label_a in the returned labels
            studies = o.post(endpoint="/tools/find", json={"Level": "Study", "Query": {}, "Labels": [], "LabelsConstraint": "Any", "Expand": True}).json()
            self.assertEqual(2, len(studies))
            self.assertEqual(1, len(studies[0]["Labels"]))
            self.assertEqual("label_a", studies[0]["Labels"][0])
            self.assertEqual(1, len(studies[1]["Labels"]))
            self.assertEqual("label_a", studies[1]["Labels"][0])

            r = o.get(endpoint=f"/studies/{self.both_labels_study_id}").json()
            self.assertEqual(1, len(r["Labels"]))
            self.assertEqual("label_a", r["Labels"][0])

            r = o.get(endpoint=f"/studies/{self.both_labels_study_id}/series?expand").json()
            self.assertEqual(1, len(r[0]["Labels"]))
            self.assertEqual("label_a", r[0]["Labels"][0])

            r = o.get(endpoint=f"/studies/{self.both_labels_study_id}/labels").json()
            self.assertEqual(1, len(r))
            self.assertEqual("label_a", r[0])

            r = o.get(endpoint=f"/series/{self.both_labels_series_id}/study").json()
            self.assertEqual(1, len(r["Labels"]))
            self.assertEqual("label_a", r["Labels"][0])

        if o_admin.is_plugin_version_at_least("authorization", 0, 9, 2):
            i = o.get_json(f"dicom-web/studies?StudyInstanceUID={self.label_a_study_dicom_id}")
            
            # this one is forbidden because we specify the study (and the study is forbidden)
            self.assert_is_forbidden(lambda: o.get_json(f"dicom-web/studies?StudyInstanceUID={self.label_b_study_dicom_id}"))
            
            # this one is empty because no studies are specified
            self.assertEqual(0, len(o.get_json(f"dicom-web/studies?PatientID={self.label_b_patient_dicom_id}")))


    def test_uploader_a(self):
        o_admin = OrthancApiClient(self.o._root_url, headers={"user-token-key": "token-admin"})
        o = OrthancApiClient(self.o._root_url, headers={"user-token-key": "token-uploader-a"})

        if o_admin.is_plugin_version_at_least("authorization", 0, 7, 3):

            # # make sure we can access all these urls (they would throw if not)
            system = o.get_system()

            all_labels = o.get_all_labels()
            self.assertEqual(1, len(all_labels))
            self.assertEqual("label_a", all_labels[0])

            # make sure we can access only the label_a studies
            self.assert_is_forbidden(lambda: o.studies.get_tags(self.label_b_study_id))
            self.assert_is_forbidden(lambda: o.studies.get_tags(self.no_label_study_id))

            # uploader-a shall be able to upload a study
            instances_ids = o.upload_file(here / "../../Database/Beaufix/IM-0001-0001.dcm")
            o_admin.instances.delete(orthanc_ids=instances_ids)

            # uploader-a shall be able to upload a study through DICOMWeb too
            o.upload_files_dicom_web(paths = [here / "../../Database/Beaufix/IM-0001-0001.dcm"])
            o_admin.instances.delete(orthanc_ids=instances_ids)

        if o_admin.is_plugin_version_at_least("authorization", 0, 9, 1):

            # uploader-a shall not be able to upload a study through DICOMWeb using /dicom-web/studies/<StudyInstanceUID of label_b>
            self.assert_is_forbidden(lambda: o.upload_files_dicom_web(paths = [here / "../../Database/Knix/Loc/IM-0001-0002.dcm"], endpoint=f"/dicom-web/studies/{self.label_b_study_dicom_id}"))

            # uploader-a shall be able to upload a study through DICOMWeb using /dicom-web/studies/<StudyInstanceUID of label_a>
            o.upload_files_dicom_web(paths = [here / "../../Database/Knix/Loc/IM-0001-0002.dcm"], endpoint=f"/dicom-web/studies/{self.label_a_study_dicom_id}")

            # note that, uploader-a is allowed to upload to /dicom-web/studies without checking any labels :-()
            o.upload_files_dicom_web(paths = [here / "../../Database/Knix/Loc/IM-0001-0002.dcm"], endpoint=f"/dicom-web/studies")

    def test_resource_token(self):

        o = OrthancApiClient(self.o._root_url, headers={"resource-token-key": "token-a-study"})
        
        # with a resource token, we can access only the given resource, not generic resources or resources from other studies

        # generic resources are forbidden
        # note: even tools/find is still forbidden in 0.9.3 (but not /dicom-web/studies -> see below)
        self.assert_is_forbidden(lambda: o.studies.find(query={"PatientName": "KNIX"},  # tools/find is forbidden with a resource token
                                                        labels=['label_b'],
                                                        labels_constraint='Any'))

        self.assert_is_forbidden(lambda: o.get_all_labels())
        self.assert_is_forbidden(lambda: o.studies.get_all_ids())
        self.assert_is_forbidden(lambda: o.patients.get_all_ids())
        self.assert_is_forbidden(lambda: o.series.get_all_ids())
        self.assert_is_forbidden(lambda: o.instances.get_all_ids())
        self.assert_is_forbidden(lambda: o.get_json('patients?expand'))
        self.assert_is_forbidden(lambda: o.get_json('studies?expand'))
        self.assert_is_forbidden(lambda: o.get_json('series?expand'))
        self.assert_is_forbidden(lambda: o.get_json('instances?expand'))
        self.assert_is_forbidden(lambda: o.get_json('studies'))
        self.assert_is_forbidden(lambda: o.get_json('studies/'))
        
        # some resources are still accessible to the 'anonymous' user  -> does not throw
        o.get_system()
        o.lookup("1.2.3")   # this route is still explicitely authorized because it is used by Stone

        # other studies are forbidden
        self.assert_is_forbidden(lambda: o.studies.get_series_ids(self.label_b_study_id))
        if self.o.is_orthanc_version_at_least(1, 12, 2):
            self.assert_is_forbidden(lambda: o.get_binary(f"tools/create-archive?resources={self.label_b_study_id}"))
            self.assert_is_forbidden(lambda: o.get_binary(f"tools/create-archive?resources={self.label_b_series_id}"))
            # if one of the studies is forbidden, the resource is forbidden
            self.assert_is_forbidden(lambda: o.get_binary(f"tools/create-archive?resources={self.label_b_study_id},{self.label_a_study_id}"))

        # the label_a study is allowed
        o.studies.get_series_ids(self.label_a_study_id)

        # test with DicomWEB routes + sub-routes
        o.get_binary(f"dicom-web/studies/{self.label_a_study_dicom_id}")
        o.get_json(f"dicom-web/studies/{self.label_a_study_dicom_id}/metadata")
        o.get_json(f"dicom-web/studies/{self.label_a_study_dicom_id}/series")
        o.get_json(f"dicom-web/studies/{self.label_a_study_dicom_id}/series?includefield=00080021%2C00080031%2C0008103E%2C00200011")
        o.get_binary(f"dicom-web/studies/{self.label_a_study_dicom_id}/series/{self.label_a_series_dicom_id}")
        o.get_json(f"dicom-web/studies/{self.label_a_study_dicom_id}/series/{self.label_a_series_dicom_id}/metadata")
        o.get_binary(f"dicom-web/studies/{self.label_a_study_dicom_id}/series/{self.label_a_series_dicom_id}/instances/{self.label_a_instance_dicom_id}")
        o.get_json(f"dicom-web/studies/{self.label_a_study_dicom_id}/series/{self.label_a_series_dicom_id}/instances/{self.label_a_instance_dicom_id}/metadata")
        o.get_json(f"dicom-web/studies?StudyInstanceUID={self.label_a_study_dicom_id}")
        o.get_json(f"dicom-web/studies?0020000D={self.label_a_study_dicom_id}")
        o.get_json(f"dicom-web/series?0020000D={self.label_a_study_dicom_id}")
        o.get_json(f"dicom-web/instances?0020000D={self.label_a_study_dicom_id}")

        if o.is_plugin_version_at_least("authorization", 0, 9, 3):
            # equivalent to the prior studies request in OHIF
            self.assertEqual(1, len(o.get_json(f"dicom-web/studies?PatientID={self.label_a_patient_dicom_id}")))
            self.assertEqual(0, len(o.get_json(f"dicom-web/studies?PatientID={self.label_b_patient_dicom_id}")))


        if self.o.is_orthanc_version_at_least(1, 12, 2):
            o.get_binary(f"tools/create-archive?resources={self.label_a_study_id}")
            o.get_binary(f"tools/create-archive?resources={self.label_a_series_id}")


            # now test with token-both
            o = OrthancApiClient(self.o._root_url, headers={"resource-token-key": "token-both-studies"})

            # other studies are forbidden
            self.assert_is_forbidden(lambda: o.studies.get_series_ids(self.no_label_study_id))
            self.assert_is_forbidden(lambda: o.get_binary(f"tools/create-archive?resources={self.no_label_study_id}"))

            # any of both or both studies together are allowed
            o.get_binary(f"tools/create-archive?resources={self.label_a_study_id}") 
            o.get_binary(f"tools/create-archive?resources={self.label_b_series_id}")
            o.get_binary(f"tools/create-archive?resources={self.label_b_study_id},{self.label_a_study_id}")
            o.get_binary(f"tools/create-archive?resources={self.label_b_study_id},{self.label_a_series_id}")
            o.get_binary(f"tools/create-archive?resources={self.label_b_study_id},{self.label_a_instance_id}")


