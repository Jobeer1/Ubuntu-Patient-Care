import json
import tempfile
import base64
from PIL import Image

from Test import Test


class TestUploadFirstPatientFile(Test):

    def __init__(self, name:str = "UploadFirstPatientFile", filePath:str = "../Database/DummyCT.dcm"):
        super().__init__(name)
        self._instanceId = None
        self._filePath = filePath
        self._dicomFileContent = None

    def beforeAll(self):
        # get the instance Id and dicom file content
        if self._instanceId is None:
            self._instanceId = self._orthanc.uploadDicomFile(self._filePath)
            self._dicomFileContent = self._orthanc.instances.getDicom(self._instanceId)

    def beforeEach(self):
        # make sure the file is not in Orthanc before the upload
        self._orthanc.instances.delete(self._instanceId)

    def test(self):
        self._orthanc.uploadDicom(self._dicomFileContent)


class TestUploadNextPatientFile(Test):

    def __init__(self, name:str = "UploadNextPatientFile", filePath:str = "../Database/DummyCT.dcm"):
        super().__init__(name)
        self._instanceId = None
        self._filePath = filePath
        self._dicomFileContent = None
        self._instanceIndex = 0

    def beforeAll(self):
        self._clear()

        # upload a source file that we will modify
        self._sourceInstanceId = self._orthanc.uploadDicomFile(self._filePath)
        
        # make sure no file is already in Orthanc before the upload
        patient = self._orthanc.patients.find("UploadNextPatientFile")
        if patient is not None:
            self._orthanc.patients.delete(patient.id)

        # upload the first instance of this patient
        self._dicomFileContent = self._modifyFile()
        self._orthanc.uploadDicom(self._dicomFileContent)



    def beforeEach(self):
        self._dicomFileContent = self._modifyFile()

    def test(self):
        self._orthanc.uploadDicom(self._dicomFileContent)

    def afterAll(self):
        self._clear()

    def _clear(self):
        patient = self._orthanc.patients.find("UploadNextPatientFile")
        if patient is not None:
            self._orthanc.patients.delete(patient.id)

    def _modifyFile(self):
        self._instanceIndex += 1
        return self._orthanc.instances.modify(
            instanceId=self._sourceInstanceId,
            replaceTags={
                "PatientName": "UploadNextPatientFile",
                "PatientID": "UploadNextPatientFile",
                "StudyDescription": "UploadNextPatientFile",
                "SeriesDescription": "UploadNextPatientFile",
                "SOPInstanceUID": "999999.888888.777777.666666.555555.44444",
                "StudyInstanceUID": "999999.888888.777777.666666",
                "SeriesInstanceUID": "999999.888888.777777.666666.555555",
                "SeriesNumber": "1",
                "InstanceNumber": str(self._instanceIndex)
            },
            deleteOriginal=False
        )



class TestUploadLargeFile10MB(Test):

    def __init__(self, name:str = "UploadLargeFile10MB"):
        super().__init__(name)
        self._instanceId = None
        self._dicomFileContent = None
        self._instanceIndex = 0

    def beforeAll(self):
        self._clear()

        # make sure no file is already in Orthanc before the upload
        patient = self._orthanc.patients.find("UploadLargeFile")
        if patient is not None:
            self._orthanc.patients.delete(patient.id)

        # upload a source file that we will modify
        self._sourceInstanceId = self._orthanc.post(
            relativeUrl="tools/create-dicom",
            data=json.dumps({
                "Tags": {
                    'PatientName' : 'UploadLargeFile',
                    'PatientID' : 'UploadLargeFile',
                    '8899-8899' : 'data:application/octet-stream;base64,' + base64.b64encode(b"\0" * 10000000).decode('utf-8')
                }
            })
        ).json()["ID"]

        # upload the first instance of this patient
        self._dicomFileContent = self._modifyFile()
        self._orthanc.uploadDicom(self._dicomFileContent)



    def beforeEach(self):
        self._dicomFileContent = self._modifyFile()

    def test(self):
        self._orthanc.uploadDicom(self._dicomFileContent)

    def afterAll(self):
        self._clear()

    def _clear(self):
        patient = self._orthanc.patients.find("UploadLargeFile")
        if patient is not None:
            self._orthanc.patients.delete(patient.id)

    def _modifyFile(self):
        self._instanceIndex += 1
        return self._orthanc.instances.modify(
            instanceId=self._sourceInstanceId,
            replaceTags={
                "PatientName": "UploadLargeFile",
                "PatientID": "UploadLargeFile",
                "StudyDescription": "UploadLargeFile",
                "SeriesDescription": "UploadLargeFile",
                "SOPInstanceUID": "999998.888888.777777.666666.555555.44444",
                "StudyInstanceUID": "999998.888888.777777.666666",
                "SeriesInstanceUID": "999998.888888.777777.666666.555555",
                "SeriesNumber": "1",
                "InstanceNumber": str(self._instanceIndex)
            },
            deleteOriginal=False
        )
