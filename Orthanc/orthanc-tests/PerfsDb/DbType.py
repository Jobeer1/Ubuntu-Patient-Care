from enum import Enum

class DbType(Enum):
    Sqlite = 1
    PG9 = 2
    MySQL = 3
    MSSQL = 4
    PG10 = 5
    PG11 = 5
    SqlitePlugin = 6

    def isPG(self):
        return self.value in [DbType.PG9.value, DbType.PG10.value, DbType.PG11.value]

    def isSqlite(self):
        return self.value in [DbType.Sqlite.value, DbType.SqlitePlugin.value]

    def isServer(self):
        return not self.isSqlite()