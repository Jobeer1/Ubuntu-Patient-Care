from Test import Test

class TestToolsFindStudyByStudyInstanceUID(Test):

    def __init__(self, name:str = "ToolsFindStudyByStudyInstanceUID"):
        super().__init__(name)

    def test(self):
        self._orthanc.studies.find(
            studyInstanceUid="99999.99999"
        )

class TestToolsFindPatientByPatientID(Test):

    def __init__(self, name:str = "ToolsFindPatientByPatientID"):
        super().__init__(name)

    def test(self):
        self._orthanc.patients.find(
            dicomPatientId="99999"
        )