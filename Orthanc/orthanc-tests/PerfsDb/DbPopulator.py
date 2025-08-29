import typing
import time
import csv
import os
from orthancRestApi import OrthancClient
from TestResult import TestResult
from DbSize import DbSize

class DbPopulator:

    def __init__(self, orthanc: OrthancClient, dbSize: DbSize):
        self._orthanc = orthanc
        self._dbSize = dbSize
        self._sourceInstanceId = None
        self._fileCounter = 0
    
    def populate(self, label: str):
        self._sourceInstanceId = self._orthanc.uploadDicomFile("../Database/DummyCT.dcm")

        if self._dbSize == DbSize.Tiny:
            patientCount = 1
            smallStudiesPerPatient = 2
            largeStudiesPerPatient = 1
            seriesPerSmallStudy = 1
            seriesPerLargeStudy = 2
            instancesPerSmallSeries = 1
            instancesPerLargeSeries = 5
        elif self._dbSize == DbSize.Small:
            patientCount = 100
            smallStudiesPerPatient = 2
            largeStudiesPerPatient = 1
            seriesPerSmallStudy = 1
            seriesPerLargeStudy = 2
            instancesPerSmallSeries = 1
            instancesPerLargeSeries = 30
        elif self._dbSize == DbSize.Medium:
            patientCount = 1000
            smallStudiesPerPatient = 2
            largeStudiesPerPatient = 2
            seriesPerSmallStudy = 1
            seriesPerLargeStudy = 2
            instancesPerSmallSeries = 1
            instancesPerLargeSeries = 300
        elif self._dbSize == DbSize.Large:
            patientCount = 10000
            smallStudiesPerPatient = 2
            largeStudiesPerPatient = 2
            seriesPerSmallStudy = 1
            seriesPerLargeStudy = 2
            instancesPerSmallSeries = 1
            instancesPerLargeSeries = 300
        else:
            raise NotImplementedError

        print("Will generate data for (approximately):")
        print("{n:>12} patients".format(n=patientCount))
        print("{n:>12} studies".format(n=patientCount * (smallStudiesPerPatient + largeStudiesPerPatient)))
        print("{n:>12} instances".format(n=patientCount * (smallStudiesPerPatient * seriesPerSmallStudy * instancesPerSmallSeries + largeStudiesPerPatient * seriesPerLargeStudy * instancesPerLargeSeries)))

        startTime = time.time()
        # first add data that are the same in small and large DBs (and that can be used in tests for comparing the same things !!)

        # used in TestFindStudyByPatientId100Results
        for i in range(100):
            self.createStudy(studyIndex=199000+i, patientIndex=99997, seriesCount=1, instancesPerSeries=1)

        # used in TestFindStudyByPatientId5Results
        self.createStudy(studyIndex=99994, patientIndex=99998, seriesCount=1, instancesPerSeries=1)
        self.createStudy(studyIndex=99995, patientIndex=99998, seriesCount=1, instancesPerSeries=1)
        self.createStudy(studyIndex=99996, patientIndex=99998, seriesCount=1, instancesPerSeries=1)
        self.createStudy(studyIndex=99997, patientIndex=99998, seriesCount=1, instancesPerSeries=1)
        self.createStudy(studyIndex=99998, patientIndex=99998, seriesCount=1, instancesPerSeries=1)

        # used in TestFindStudyByStudyDescription1Result
        # used in TestFindStudyByPatientId1Result
        # used in TestToolsFindStudyByStudyInstanceUID
        self.createStudy(studyIndex=99999, patientIndex=99999, seriesCount=1, instancesPerSeries=1)

        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "Results/db-init-" + label + ".csv"), 'w', newline='') as resultFile:
            resultWriter = csv.writer(resultFile)
            resultWriter.writerow(["#patientCount", "filesCount", "files/sec"])
            # then, add data to make the DB "large" or "small"
            for patientIndex in range(0, patientCount):
                studyIndex=0
                print("Generating data for patient " + str(patientIndex))
                fileCounterAtPatientStart = self._fileCounter
                startTimePatient = time.time()

                for i in range(0, smallStudiesPerPatient):
                    print("Generating small study " + str(i))
                    self.createStudy(studyIndex=studyIndex, patientIndex=patientIndex, seriesCount=seriesPerSmallStudy, instancesPerSeries=instancesPerSmallSeries)
                    studyIndex+=1
                for i in range(0, largeStudiesPerPatient):
                    print("Generating large study " + str(i))
                    self.createStudy(studyIndex=studyIndex, patientIndex=patientIndex, seriesCount=seriesPerLargeStudy, instancesPerSeries=instancesPerLargeSeries)
                    studyIndex+=1

                endTimePatient = time.time()
                print("STATS: uploaded {n} files in {s:.2f} seconds; {x:.2f} files/sec".format(
                    n=self._fileCounter - fileCounterAtPatientStart,
                    s=endTimePatient - startTimePatient,
                    x=(self._fileCounter - fileCounterAtPatientStart)/(endTimePatient - startTimePatient)
                ))
                resultWriter.writerow([
                    patientIndex, 
                    self._fileCounter, 
                    (self._fileCounter - fileCounterAtPatientStart)/(endTimePatient - startTimePatient)
                    ])
                resultFile.flush()

        endTime = time.time()
        print("Generation completed.  Elapsed time: {duration:.2f} sec".format(duration=endTime-startTime))    
        print("Uploaded {n} files -> {p:.2f} files/sec".format(n=self._fileCounter, p=self._fileCounter/(endTime-startTime)))

    def createStudy(self, studyIndex: int, patientIndex: int, seriesCount: int, instancesPerSeries: int):
        for seriesIndex in range(0, seriesCount):
            for instanceIndex in range(0, instancesPerSeries):
                dicomFile = self.createDicomFile(patientIndex=patientIndex, studyIndex=studyIndex, seriesIndex=seriesIndex, instanceIndex=instanceIndex)
                self._orthanc.uploadDicom(dicomFile)

    def createDicomFile(self, patientIndex: int, studyIndex: int, seriesIndex: int, instanceIndex: int) -> object:
        self._fileCounter += 1
        return self._orthanc.instances.modify(
            instanceId=self._sourceInstanceId,
            replaceTags={
                "PatientName": "Patient-" + str(patientIndex),
                "PatientID": str(patientIndex),
                "StudyDescription": str(patientIndex) + "-" + str(studyIndex),
                "SeriesDescription": str(patientIndex) + "-" + str(studyIndex) + "-" + str(seriesIndex),
                "SOPInstanceUID": str(patientIndex) + "." + str(studyIndex) + "." + str(seriesIndex) + "." + str(instanceIndex),
                "StudyInstanceUID": str(patientIndex) + "." + str(studyIndex),
                "SeriesInstanceUID": str(patientIndex) + "." + str(studyIndex) + "." + str(seriesIndex),
                "SeriesNumber": str(seriesIndex),
                "InstanceNumber": str(instanceIndex)
            },
            deleteOriginal=False
        )