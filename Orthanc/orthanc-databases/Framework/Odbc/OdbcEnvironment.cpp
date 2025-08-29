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


#include "OdbcEnvironment.h"

#include <Logging.h>
#include <OrthancException.h>

#include <boost/lexical_cast.hpp>
#include <sqlext.h>


namespace OrthancDatabases
{
  OdbcEnvironment::OdbcEnvironment()
  {
    LOG(INFO) << "Creating the ODBC environment";
      
    /* Allocate an environment handle */
    if (!SQL_SUCCEEDED(SQLAllocHandle(SQL_HANDLE_ENV, SQL_NULL_HANDLE, &handle_)))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_Database,
                                      "Cannot create ODBC environment");
    }
      
    /* We want ODBC 3 support */
    if (!SQL_SUCCEEDED(SQLSetEnvAttr(handle_, SQL_ATTR_ODBC_VERSION, (void *) SQL_OV_ODBC3, 0)))
    {
      SQLFreeHandle(SQL_HANDLE_ENV, handle_);
      throw Orthanc::OrthancException(Orthanc::ErrorCode_Database,
                                      "Your environment doesn't support ODBC 3.x");
    }
  }


  OdbcEnvironment::~OdbcEnvironment()
  {
    LOG(INFO) << "Destructing the ODBC environment";
      
    if (!SQL_SUCCEEDED(SQLFreeHandle(SQL_HANDLE_ENV, handle_)))
    {
      LOG(ERROR) << "Cannot tear down ODBC environment";
    }
  }


  std::string OdbcEnvironment::FormatError(SQLHANDLE handle,
                                           SQLSMALLINT type)
  {
    SQLINTEGER   i = 0;
    SQLINTEGER   native;
    SQLCHAR      state[SQL_SQLSTATE_SIZE + 1];
    SQLCHAR      text[256];
    SQLSMALLINT  len;

    std::string s;
      
    for (;;)
    {
      SQLRETURN ret = SQLGetDiagRec(type, handle, ++i, state, &native, text, sizeof(text), &len);
      if (SQL_SUCCEEDED(ret))
      {
        if (i >= 2)
        {
          s += "\n";
        }
          
        s += (std::string(reinterpret_cast<const char*>(state)) + " : " +
              boost::lexical_cast<std::string>(i) + "/" +
              boost::lexical_cast<std::string>(native) + " " +
              std::string(reinterpret_cast<const char*>(text)));
      }
      else
      {
        return s;
      }
    }
  }


  void OdbcEnvironment::GlobalInitialization()
  {
    /**
     * Explicitly inform the ODBC driver that the application is using
     * UTF-8, by making sure that default "C" locale is used. We are
     * in the scenario "ANSI application with a Unicode driver".
     * https://docs.microsoft.com/en-us/sql/connect/odbc/linux-mac/programming-guidelines
     * https://www.progress.com/tutorials/odbc/unicode
     **/
    setlocale(LC_ALL, "C");
  }
}
