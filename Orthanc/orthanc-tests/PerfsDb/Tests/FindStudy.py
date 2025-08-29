from Test import Test

class TestFindStudyByStudyDescription1Result(Test):

    def __init__(self, name:str = "FindStudyByStudyDescription1Result"):
        super().__init__(name)

    def test(self):
        self._orthanc.studies.query(
            query = {"StudyDescription": "99999-99999"}
        )

class TestFindStudyByStudyDescription0Results(Test):

    def __init__(self, name:str = "FindStudyByStudyDescription0Results"):
        super().__init__(name)

    def test(self):
        self._orthanc.studies.query(
            query = {"StudyDescription": "X"}
        )

class TestFindStudyByPatientId1Result(Test):

    def __init__(self, name:str = "FindStudyByPatientId1Result"):
        super().__init__(name)

    def test(self):
        self._orthanc.studies.query(
            query = {"PatientID": "99999"}
        )

class TestFindStudyByPatientId0Results(Test):

    def __init__(self, name:str = "FindStudyByPatientId0Results"):
        super().__init__(name)

    def test(self):
        self._orthanc.studies.query(
            query = {"PatientID": "X"}
        )        

class TestFindStudyByPatientId5Results(Test):

    def __init__(self, name:str = "FindStudyByPatientId5Results"):
        super().__init__(name)

    def test(self):
        self._orthanc.studies.query(
            query = {"PatientID": "99998"}
        )        

class TestFindStudyByPatientId100Results(Test):

    def __init__(self, name:str = "FindStudyByPatientId100Results"):
        super().__init__(name)

    def test(self):
        self._orthanc.studies.query(
            query = {"PatientID": "99997"}
        )        