import argparse
import fnmatch
import csv
import datetime
import os

from ConfigFileBuilder import ConfigFileBuilder
from TestConfig import TestConfig
from Tests import *
from DbServer import DbServer
from DbType import DbType
from DbSize import DbSize


allTestConfigs = [
    TestConfig(label= "mysql-small", dbSize=DbSize.Small, dbServer=DbServer(dbType=DbType.MySQL, port=2000)),
    TestConfig(label= "pg9-small", dbSize=DbSize.Small, dbServer=DbServer(dbType=DbType.PG9, port=2001)),
    TestConfig(label= "pg9bis-small", dbSize=DbSize.Small, dbServer=DbServer(dbType=DbType.PG9, port=2011)),
    TestConfig(label= "pg10-small", dbSize=DbSize.Small, dbServer=DbServer(dbType=DbType.PG10, port=2002)),
    TestConfig(label= "pg11-small", dbSize=DbSize.Small, dbServer=DbServer(dbType=DbType.PG11, port=2003)),
    TestConfig(label= "mssql-small", dbSize=DbSize.Small, dbServer=DbServer(dbType=DbType.MSSQL, port=2004)),
    TestConfig(label= "sqlite-small", dbSize=DbSize.Small, dbType=DbType.Sqlite),
    TestConfig(label= "sqliteplugin-small", dbSize=DbSize.Small, dbType=DbType.SqlitePlugin),

    TestConfig(label= "mysql-tiny", dbSize=DbSize.Tiny, dbServer=DbServer(dbType=DbType.MySQL, port=3000)),
    TestConfig(label= "pg9-tiny", dbSize=DbSize.Tiny, dbServer=DbServer(dbType=DbType.PG9, port=3001)),
    TestConfig(label= "pg9bis-tiny", dbSize=DbSize.Tiny, dbServer=DbServer(dbType=DbType.PG9, port=3011)),
    TestConfig(label= "pg10-tiny", dbSize=DbSize.Tiny, dbServer=DbServer(dbType=DbType.PG10, port=3002)),
    TestConfig(label= "pg11-tiny", dbSize=DbSize.Tiny, dbServer=DbServer(dbType=DbType.PG11, port=3003)),
    TestConfig(label= "mssql-tiny", dbSize=DbSize.Tiny, dbServer=DbServer(dbType=DbType.MSSQL, port=3004)),
    TestConfig(label= "sqlite-tiny", dbSize=DbSize.Tiny, dbType=DbType.Sqlite),
    TestConfig(label= "sqliteplugin-tiny", dbSize=DbSize.Tiny, dbType=DbType.SqlitePlugin),

    TestConfig(label= "mysql-medium", dbSize=DbSize.Medium, dbServer=DbServer(dbType=DbType.MySQL, port=4000)),
    TestConfig(label= "pg9-medium", dbSize=DbSize.Medium, dbServer=DbServer(dbType=DbType.PG9, port=4001)),
    TestConfig(label= "pg10-medium", dbSize=DbSize.Medium, dbServer=DbServer(dbType=DbType.PG10, port=4002)),
    TestConfig(label= "pg11-medium", dbSize=DbSize.Medium, dbServer=DbServer(dbType=DbType.PG11, port=4003)),
    TestConfig(label= "mssql-medium", dbSize=DbSize.Medium, dbServer=DbServer(dbType=DbType.MSSQL, port=4004)),
    TestConfig(label= "sqlite-medium", dbSize=DbSize.Medium, dbType=DbType.Sqlite),
    TestConfig(label= "sqliteplugin-medium", dbSize=DbSize.Medium, dbType=DbType.SqlitePlugin),

    TestConfig(label= "mysql-large", dbSize=DbSize.Large, dbServer=DbServer(dbType=DbType.MySQL, port=5000)),
    TestConfig(label= "pg9-large", dbSize=DbSize.Large, dbServer=DbServer(dbType=DbType.PG9, port=5001)),
    TestConfig(label= "pg10-large", dbSize=DbSize.Large, dbServer=DbServer(dbType=DbType.PG10, port=5002)),
    TestConfig(label= "pg11-large", dbSize=DbSize.Large, dbServer=DbServer(dbType=DbType.PG11, port=5003)),
    TestConfig(label= "mssql-large", dbSize=DbSize.Large, dbServer=DbServer(dbType=DbType.MSSQL, port=5004)),
    TestConfig(label= "sqlite-large", dbSize=DbSize.Large, dbType=DbType.Sqlite),
    TestConfig(label= "sqliteplugin-large", dbSize=DbSize.Large, dbType=DbType.SqlitePlugin),
]

allTests = [
    TestStatistics(),
    TestFindStudyByStudyDescription1Result(),
    TestFindStudyByPatientId1Result(),
    TestFindStudyByStudyDescription0Results(),
    TestFindStudyByPatientId0Results(),
    TestFindStudyByPatientId5Results(),
    TestFindStudyByPatientId100Results(),
    TestUploadNextPatientFile(),
    TestUploadFirstPatientFile(),
    TestUploadLargeFile10MB(),
    TestToolsFindStudyByStudyInstanceUID(),
    TestToolsFindPatientByPatientID()
]

selectedTestConfigs = []
selectedTests = []

parser = argparse.ArgumentParser(description = "Initializes/Runs/Clears PerfsDb setup.")

# create a cli option for each config
for testConfig in allTestConfigs:
    parser.add_argument("--" + testConfig.label, action = "store_true")

parser.add_argument("--init", help = "initializes DBs", action = "store_true")
parser.add_argument("--run", help = "runs tests", action = "store_true")
parser.add_argument("--clear", help = "clear DBs", action = "store_true")

parser.add_argument("--orthanc-path", help = "path to the folder containing Orthanc executable", default=".")
parser.add_argument("--plugins-path", help = "path to the folder containing Orthanc executable", default=".")
parser.add_argument("--repeat", help = "number of times to repeat each test to average timings", type=int, default=50)
parser.add_argument("--test-filter", help = "filter tests by names (wildcards are allowed)", default="*")
parser.add_argument("--verbose", help = "start Orthanc in verbose mode", action = "store_true")
parser.add_argument("--trace", help = "start Orthanc in trace mode", action = "store_true")

args = parser.parse_args()

for testConfig in allTestConfigs:
    if args.__dict__[testConfig.label.replace("-", "_")]:
        selectedTestConfigs.append(testConfig)

# if no test config specified, take them all
if len(selectedTestConfigs) == 0:
    selectedTestConfigs = allTestConfigs

selectedTestConfigs.sort(key=lambda x: x.label)

# filter tests
for test in allTests:
    if fnmatch.fnmatch(test.name, args.test_filter):
        selectedTests.append(test)

selectedTests.sort(key=lambda x: x.name)

# if no action specified, it means only run
if not (args.init | args.run | args.clear):
    args.init = False
    args.run = True
    args.clear = False

print("***** Orthanc *******")
print("path    :", args.orthanc_path)

results = {}

for testConfig in selectedTestConfigs:
    testConfig.setRepeatCount(args.repeat)
    
    print("======= " + testConfig.label + " ========")

    if args.clear:
        print("** Clearing Db")
        testConfig.clearDb()

    if args.init or args.run:
        print("** Generating config files")
        testConfig.generateOrthancConfigurationFile(args.plugins_path)

        print("** Launching DbServer")
        testConfig.launchDbServer()
        
        print("** Launching Orthanc")
        orthancWasAlreadyRunning = not testConfig.launchOrthanc(args.orthanc_path, verboseEnabled=args.verbose, traceEnabled=args.trace)
        if orthancWasAlreadyRunning and len(selectedTestConfigs) > 1:
            print("Error: Can't execute multiple configuration on already running Orthanc.  Exit Orthanc and let this script start Orthanc instances")
            exit(-1)

    if args.init:
        testConfig.initializeDb()

    if args.run:
        print("** Runnnig tests")
        results[testConfig.label] = testConfig.runTests(selectedTests)
    
    print("** Stopping Orthanc")
    testConfig.stopOrthanc()
    
print("++++++++++++++ results summary +++++++++++++++")
testNames = set()
resultsByTestName = {}
for configName, configResult in results.items():
    for result in configResult:
        testNames.add(result.name)
        if not result.name in resultsByTestName:
            resultsByTestName[result.name] = {}
        resultsByTestName[result.name][configName] = result

resultFileName = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Results/run-" + datetime.datetime.now().strftime("%Y.%m.%d.%H.%M.%S"))

with open(resultFileName, 'w', newline='') as resultFile:
    resultWriter = csv.writer(resultFile)
    resultHeaderRow = [""]

    headerLine = "{empty:<40}|".format(empty="")

    for testConfig in selectedTestConfigs:
        headerLine += "{configName:^15}|".format(configName=testConfig.label)
        resultHeaderRow.append(configName)

    print(headerLine)
    resultWriter.writerow(resultHeaderRow)

    for testName in sorted(testNames):
        resultLine = "{name:<40}|".format(name=testName)
        resultRow=[testName]
        
        for testConfig in selectedTestConfigs:
            resultLine += "{avg:>11.2f} ms |".format(avg = resultsByTestName[testName][testConfig.label].averageTimeInMs)
            resultRow.append(resultsByTestName[testName][testConfig.label].averageTimeInMs)
        
        print(resultLine)
        resultWriter.writerow(resultRow)

print("** Done; results saved in " + resultFileName)
