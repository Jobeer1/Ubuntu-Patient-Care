import os
import time
import statistics
from orthancRestApi import OrthancClient

from TestResult import TestResult

class Test:

    def __init__(self, name: str):
        self.name = name
        self._orthanc = None
        self.repeatCount = 20
        
    def setOrthancClient(self, orthanc: OrthancClient):
        self._orthanc = orthanc

    def setRepeatCount(self, repeatCount: int):
        self.repeatCount = repeatCount

    def beforeAll(self):
        """
        Code to execute before the execution of all repetitions of a test; i.e: upload a file.
        This code is not included in timings
        """
        pass

    def beforeEach(self):
        """
        Code to execute before the execution of each repetition of a test.
        This code is not included in timings
        """
        pass

    def test(self):
        """
        Code whose execution time will be measured
        """
        pass

    def afterEach(self):
        """
        Code to execute after the execution of each repetition of a test.
        This code is not included in timings
        """
        pass

    def afterAll(self):
        """
        Code to execute after the execution of all repetitions of a test.
        This code is not included in timings
        """
        pass

    def run(self) -> TestResult:
        result = TestResult(self.name)

        self.beforeAll()

        for i in range(0, self.repeatCount):
            self.beforeEach()

            try:
                with open('/proc/sys/vm/drop_caches', 'w') as f:
                    f.write('3')
            except:
                print('Please run this script as root to be able to flush the disk cache, and have reproducible runtimes')

            startTime = time.time()
            self.test()
            endTime = time.time()
            
            self.afterEach()

            result.add((endTime - startTime) * 1000)

        self.afterAll()
        result.compute()
        return result

    def __str__(self):
        return "{name:<40}: {avg:>8.2f} ms {min:>8.2f} ms {max:>8.2f} ms".format(
            name=self.name,
            avg = self.averageTimeInMs,
            min=self.minTimeInMs,
            max=self.maxTimeInMs
        )
