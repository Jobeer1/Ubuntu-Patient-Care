import time
import statistics
from orthancRestApi import OrthancClient

class TestResult:

    def __init__(self, name: str):
        self.minTimeInMs = 0
        self.maxTimeInMs = 0
        self.averageTimeInMs = 0
        self.name = name
        self._durations = []
        
    def add(self, durationInMs: float):
        self._durations.append(durationInMs)

    def compute(self):

        if len(self._durations) >= 2:
            mean = statistics.mean(self._durations)
            stdDev = statistics.stdev(self._durations)

            # remove outliers
            cleanedDurations = [x for x in self._durations if (x > mean - 2*stdDev) and (x < mean + 2*stdDev)]
            
            self.averageTimeInMs = statistics.mean(cleanedDurations)
            self.minTimeInMs = min(cleanedDurations)
            self.maxTimeInMs = max(cleanedDurations)
        elif len(self._durations) == 1:
            self.averageTimeInMs = self._durations[0]
            self.minTimeInMs = self._durations[0]
            self.maxTimeInMs = self._durations[0]
        else:
            raise ArithmeticError # you need at least one measure !

            

    def __str__(self):
        return "{name:<40}: {avg:>8.2f} ms {min:>8.2f} ms {max:>8.2f} ms".format(
            name=self.name,
            avg = self.averageTimeInMs,
            min=self.minTimeInMs,
            max=self.maxTimeInMs
        )