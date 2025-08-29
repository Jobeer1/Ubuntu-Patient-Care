import typing
import subprocess
import os
import shutil
import time
from osimis_timer import TimeOut
from orthancRestApi import OrthancClient

from DbSize import DbSize
from DbType import DbType
from ConfigFileBuilder import ConfigFileBuilder
from DbServer import DbServer
from DbPopulator import DbPopulator
from Tests import *
from TestResult import TestResult

class TestConfig:

    def __init__(self,
        label: str,
        dbSize: DbSize,
        dbType: DbType=None,
        dbServer: DbServer=None
        ):

        self._dbSize = dbSize
        self._dbServer = dbServer
        self.label = label
        self._port = None
        self._orthancProcess = None
        self._repeatCount = 20
        self._results = []

        if dbServer is not None:
            self._dbType = dbServer.dbType
            self._dbServer.setLabel(self.label)
            self._port = dbServer.port
        else:
            self._dbType = dbType
        
    def setRepeatCount(self, repeatCount: int):
        self._repeatCount = repeatCount

    def launchDbServer(self):
        if self._dbServer is not None:
            self._dbServer.launch()

    def launchOrthanc(self, orthancPath, verboseEnabled: bool=False, traceEnabled: bool=False) -> bool:
        orthanc = OrthancClient("http://127.0.0.1:8042")
        
        print("Checking if Orthanc is already running")
        if orthanc.isAlive():
            print("Orthanc is already running")
            return False
        
        print("Launching Orthanc")
        runOrthancCommand = [
            os.path.join(orthancPath, "Orthanc"), 
            os.path.join(os.path.abspath(os.path.dirname(__file__)), "ConfigFiles", self.label + ".json"),
            '--no-jobs',
        ]
        if traceEnabled:
            runOrthancCommand.append("--trace")
        elif verboseEnabled:
            runOrthancCommand.append("--verbose")

        startupTimeResult = TestResult("Startup time")
        startTime = time.time()

        self._orthancProcess = subprocess.Popen(runOrthancCommand)
       
        print("Waiting for Orthanc to start")
        if not TimeOut.waitUntilCondition(lambda: orthanc.isAlive(), 5000, evaluateInterval = 0.1):
            print("Orthanc failed to start")
            exit(-2)
        endTime = time.time()
            
        startupTimeResult.add((endTime - startTime) * 1000)
        startupTimeResult.compute()
        self._results.append(startupTimeResult)
        print("Orthanc has started")
        return True

    def stopOrthanc(self):
        if self._orthancProcess is not None:
            self._orthancProcess.terminate()
            self._orthancProcess.wait()

    def initializeDb(self):
        dbPopulator = DbPopulator(orthanc=OrthancClient("http://127.0.0.1:8042"), dbSize=self._dbSize)
        dbPopulator.populate(self.label)

    def runTests(self, tests: typing.List[Test]) -> typing.List[TestResult]:

        for test in tests:
            test.setOrthancClient(OrthancClient("http://127.0.0.1:8042"))
            test.setRepeatCount(self._repeatCount)
            result = test.run()
            print(str(result))

            self._results.append(result)
        return self._results

    def clearDb(self):
        if self._dbServer is not None:
            self._dbServer.clear()
        
        # clear storage (in case of Sqlite DB, it will also clear the DB)
        shutil.rmtree(os.path.join(os.path.abspath(os.path.dirname(__file__)), "Storages/{name}".format(name=self.label)), ignore_errors=True)

    def generateOrthancConfigurationFile(self, pluginsPath: str):
        
        ConfigFileBuilder.generate(
            outputPath=os.path.join(os.path.abspath(os.path.dirname(__file__)), "ConfigFiles/{name}.json".format(name=self.label)), 
            pluginsPath=pluginsPath,
            storagePath=os.path.join(os.path.abspath(os.path.dirname(__file__)), "Storages/{name}".format(name=self.label)),
            dbType=self._dbType,
            dbSize=self._dbSize,
            port=self._port
            )
