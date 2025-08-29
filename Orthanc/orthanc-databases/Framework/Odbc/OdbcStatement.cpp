/**
 * Orthanc - A Lightweight, RESTful DICOM Store
 * Copyright (C) 2012-2016 Sebastien Jodogne, Medical Physics
 * Department, University Hospital of Liege, Belgium
 * Copyright (C) 2017-2023 Osimis S.A., Belgium
 * Copyright (C) 2024-2025 Orthanc Team SRL, Belgium
 * Copyright (C) 2021-2025 Sebastien Jodogne, ICTEAM UCLouvain, Belgium
 *
 * This program is free software: you can redistribute it and/or
 * modify it under the terms of the GNU Affero General Public License
 * as published by the Free Software Foundation, either version 3 of
 * the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Affero General Public License for more details.
 * 
 * You should have received a copy of the GNU Affero General Public License
 * along with this program. If not, see <http://www.gnu.org/licenses/>.
 **/


#include "OdbcStatement.h"

#include "../../Resources/Orthanc/Plugins/OrthancPluginCppWrapper.h"  // For ORTHANC_PLUGINS_VERSION_IS_ABOVE
#include "OdbcEnvironment.h"

#include <Logging.h>
#include <OrthancException.h>

#include <sqlext.h>


namespace OrthancDatabases
{
  OdbcStatement::OdbcStatement(SQLHSTMT databaseHandle)
  {
    if (!SQL_SUCCEEDED(SQLAllocHandle(SQL_HANDLE_STMT, databaseHandle, &handle_)))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_Database, "Cannot allocate statement");          
    }
  }

  
  OdbcStatement::~OdbcStatement()
  {
    if (!SQL_SUCCEEDED(SQLFreeHandle(SQL_HANDLE_STMT, handle_)))
    {
      LOG(ERROR) << "Cannot destruct statement";
    }
  }

  
  std::string OdbcStatement::FormatError()
  {
    return OdbcEnvironment::FormatError(handle_, SQL_HANDLE_STMT);
  }


  void OdbcStatement::CheckCollision(Dialect dialect)
  {
    SQLINTEGER native = -1;
    SQLCHAR stateBuf[SQL_SQLSTATE_SIZE + 1];
    SQLSMALLINT stateLength = 0;

    for (SQLSMALLINT recNum = 1; ; recNum++)
    {
      if (SQL_SUCCEEDED(SQLGetDiagField(SQL_HANDLE_STMT, handle_,
                                        recNum, SQL_DIAG_NATIVE, &native, SQL_IS_INTEGER, 0)) &&
          SQL_SUCCEEDED(SQLGetDiagField(SQL_HANDLE_STMT, handle_,
                                        recNum, SQL_DIAG_SQLSTATE, &stateBuf, sizeof(stateBuf), &stateLength)))
      {
        const std::string state(reinterpret_cast<const char*>(stateBuf));
          
        if (state == "40001" ||
            (dialect == Dialect_MySQL && native == 1213) ||
            (dialect == Dialect_MSSQL && native == 1205))
        {
#if ORTHANC_PLUGINS_VERSION_IS_ABOVE(1, 9, 2)
          throw Orthanc::OrthancException(Orthanc::ErrorCode_DatabaseCannotSerialize);
#else
          throw Orthanc::OrthancException(Orthanc::ErrorCode_Database, "Collision between multiple writers");
#endif
        }
        else if (state == "08S01")
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_DatabaseUnavailable);
        }

      }
      else
      {
        return;
      }
    }
  }
}
