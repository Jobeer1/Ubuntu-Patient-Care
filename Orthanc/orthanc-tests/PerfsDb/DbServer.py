import typing
import subprocess
import time

from DbType import DbType

class DbServer:

    class DockerDefinition:

        def __init__(self, image: str, internalPort: int, envVars: typing.Dict[str, str], storagePath: str, command: typing.List[str]=None, extraInitTime: int=0):
            self.image = image
            self.internalPort = internalPort
            self.envVars = envVars
            self.storagePath = storagePath
            self.command = command
            self.extraInitTime = extraInitTime

    def __init__(self, dbType: DbType, port: int):

        self.port = port
        self.dbType = dbType

        self._containerId = None
        self._label = None

    def setLabel(self, label: str):
        self._label = label

    def isRunning(self) -> bool:
        ret = subprocess.call([
            "docker",
            "top",
            self._label
        ])            
        return ret == 0

    def volumeExists(self) -> bool:
        ret = subprocess.call([
            "docker",
            "volume",
            "inspect",
            self._label
        ])
        return ret == 0

    def launch(self):
        dockerDefinition = self.getDockerDefinition()

        # check if the container is already running
        if self.isRunning():
            print("DbServer is already running")
            return

        volumeCreatedThisTime = False
        if not self.volumeExists():
            subprocess.check_call([
                "docker", 
                "volume", 
                "create", 
                "--name=" + self._label
            ])
            volumeCreatedThisTime = True
        
        dockerRunCommand = [
            "docker",
            "run",
            "-d",
            "--name=" + self._label,
            "-p", str(self.port) + ":" + str(dockerDefinition.internalPort),
            "--volume=" + self._label + ":" + dockerDefinition.storagePath
        ]

        if len(dockerDefinition.envVars) > 0:
            for k,v in dockerDefinition.envVars.items():
                dockerRunCommand.extend(["--env", k + "=" + v])
        
        dockerRunCommand.append(
            dockerDefinition.image
        )

        if dockerDefinition.command is not None:
            dockerRunCommand.extend(
                dockerDefinition.command
            )

        print("Launching DbServer")
        subprocess.check_call(dockerRunCommand)

        print("Waiting for DbServer to be ready")
        
        # wait until its port is open
        retryCounter = 0
        connected = False
        while not connected and retryCounter < 30:
            time.sleep(1)
            connected = subprocess.call(["nc", "-z", "localhost", str(self.port)]) == 0
        if retryCounter >= 30:
            print("DbServer still not ready after 30 sec")
            raise TimeoutError

        if dockerDefinition.extraInitTime > 0 and volumeCreatedThisTime:
            time.sleep(dockerDefinition.extraInitTime)

    def stop(self):
        if self.isRunning():
            subprocess.check_call([
                "docker",
                "stop",
                self._label
            ])

        subprocess.call([
            "docker",
            "rm",
            self._label
        ])

    def clear(self):
        # remove the volume
        self.stop()        
        subprocess.call([
            "docker",
            "volume",
            "rm",
            self._label
        ])


    def getDockerDefinition(self):
        if self.dbType == DbType.MySQL:
            return DbServer.DockerDefinition(
                image="mysql:8.0",
                internalPort=3306,
                envVars={
                    "MYSQL_PASSWORD": "orthanc",
                    "MYSQL_USER": "orthanc",
                    "MYSQL_DATABASE": "orthanc",
                    "MYSQL_ROOT_PASSWORD": "foo-root"       
                },
                storagePath="/var/lib/mysql",
                command=["mysqld", "--default-authentication-plugin=mysql_native_password", "--log-bin-trust-function-creators=1"],
                extraInitTime=30
            )
        elif self.dbType == DbType.MSSQL:
            return DbServer.DockerDefinition(
                image="microsoft/mssql-server-linux", 
                internalPort=1433,
                envVars={
                    "ACCEPT_EULA": "Y",
                    "SA_PASSWORD": "MyStrOngPa55word!"
                },
                storagePath="/var/opt/mssql/data",
                extraInitTime=10
            )
        elif self.dbType == DbType.PG9 or self.dbType == DbType.PG10 or self.dbType == DbType.PG11:
            if self.dbType == DbType.PG9:
                image = "postgres:9"
            elif self.dbType == DbType.PG10:
                image = "postgres:10"
            elif self.dbType == DbType.PG11:
                image = "postgres:11"
            return DbServer.DockerDefinition(
                image=image, 
                internalPort=5432,
                envVars={
                },
                storagePath="/var/lib/postgresql/data"
            )

