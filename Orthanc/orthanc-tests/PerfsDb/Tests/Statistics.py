import json

from Test import Test

class TestStatistics(Test):

    def __init__(self, name:str = "Statistics"):
        super().__init__(name)
        self._response = None

    def test(self):
        self._statistics = self._orthanc.getJson(relativeUrl="statistics")

    def beforeAll(self):
        # on large DB, statistics may be very  slow so we don't want to repeat it 30 times !
        self.repeatCount = int(max(int(self.repeatCount) / 10, 1))

    def afterAll(self):
        print("Statistics:" + json.dumps(self._statistics))