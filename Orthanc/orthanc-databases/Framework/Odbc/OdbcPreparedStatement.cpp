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


#include "OdbcPreparedStatement.h"

#include "../Common/InputFileValue.h"
#include "../Common/Integer64Value.h"
#include "../Common/Utf8StringValue.h"
#include "OdbcResult.h"

#include <Logging.h>
#include <OrthancException.h>

#include <sqlext.h>


namespace OrthancDatabases
{
  void OdbcPreparedStatement::Setup(const Query& query)
  {
    formatter_.SetNamedDialect(Dialect_MSSQL);  /* ODBC uses "?" to name its parameters */
    
    std::string sql;
    query.Format(sql, formatter_);
      
    LOG(INFO) << "Preparing ODBC statement: " << sql;
    SQLCHAR* s = const_cast<SQLCHAR*>(reinterpret_cast<const SQLCHAR*>(sql.c_str()));
        
    if (!SQL_SUCCEEDED(SQLPrepare(statement_.GetHandle(), s, SQL_NTS)))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_Database,
                                      "Cannot prepare ODBC statement: " + sql);
    }

    paramsIndex_.resize(formatter_.GetParametersCount());

    size_t countInt64 = 0;
    size_t countStrings = 0;

    for (size_t i = 0; i < paramsIndex_.size(); i++)
    {
      switch (formatter_.GetParameterType(i))
      {
        case ValueType_Integer64:
          paramsIndex_[i] = countInt64;
          countInt64++;
          break;
            
        case ValueType_InputFile:
        case ValueType_Utf8String:
          paramsIndex_[i] = countStrings;
          countStrings++;
          break;
            
        default:
          throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
      }
    }

    paramsInt64_.resize(countInt64);
    paramsString_.resize(countStrings);
  }


  OdbcPreparedStatement::OdbcPreparedStatement(SQLHSTMT databaseHandle,
                                               Dialect dialect,
                                               const Query& query) :
    statement_(databaseHandle),
    formatter_(dialect)
  {
    Setup(query);
  }
    

  OdbcPreparedStatement::OdbcPreparedStatement(SQLHSTMT databaseHandle,
                                               Dialect dialect,
                                               const std::string& sql) :
    statement_(databaseHandle),
    formatter_(dialect)
  {
    Query query(sql);
    Setup(query);
  }

    
  IResult* OdbcPreparedStatement::Execute()
  {
    Dictionary parameters;
    return Execute(parameters);
  }

    
  IResult* OdbcPreparedStatement::Execute(const Dictionary& parameters)
  {
    /**
     * NB: This class creates a copy of all the string parameters from
     * "parameters", because "SQLBindParameter()" assumes that the
     * lifetime of the bound values must be larger than the lifetime
     * of the cursor. This is no problem for the index plugin, but
     * might be problematic if storing large files in the storage area
     * (as this doubles RAM requirements).
     **/
    
    for (size_t i = 0; i < formatter_.GetParametersCount(); i++)
    {
      const std::string& name = formatter_.GetParameterName(i);
          
      if (!parameters.HasKey(name))
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InexistentItem,
                                        "Missing parameter to SQL prepared statement: " + name);
      }
      else 
      {
        const IValue& value = parameters.GetValue(name);
        if (value.GetType() == ValueType_Null)
        {
          SQLSMALLINT cType, sqlType;
              
          switch (formatter_.GetParameterType(i))
          {
            case ValueType_Integer64:
              cType = SQL_C_SBIGINT;
              sqlType = SQL_BIGINT;
              break;

            case ValueType_Utf8String:
              cType = SQL_C_CHAR;
              sqlType = SQL_VARCHAR;
              break;

            default:
              throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
          }

          SQLLEN null = SQL_NULL_DATA;
          if (!SQL_SUCCEEDED(SQLBindParameter(statement_.GetHandle(), i + 1, SQL_PARAM_INPUT, cType, sqlType,
                                              0 /* ignored */, 0 /* ignored */, NULL, 0, &null)))
          {
            throw Orthanc::OrthancException(Orthanc::ErrorCode_Database,
                                            "Cannot bind NULL parameter: " + statement_.FormatError());
          }
        }
        else if (value.GetType() != formatter_.GetParameterType(i))
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_BadParameterType,
                                          "Parameter \"" + name + "\" should be of type \"" +
                                          EnumerationToString(formatter_.GetParameterType(i)) +
                                          "\", found \"" + EnumerationToString(value.GetType()) + "\"");
        }
        else
        {
          assert(i < paramsIndex_.size());
          size_t index = paramsIndex_[i];
              
          switch (value.GetType())
          {
            case ValueType_Integer64:
              assert(index < paramsInt64_.size());
              paramsInt64_[index] = dynamic_cast<const Integer64Value&>(value).GetValue();

              if (!SQL_SUCCEEDED(SQLBindParameter(statement_.GetHandle(), i + 1, SQL_PARAM_INPUT, SQL_C_SBIGINT, SQL_BIGINT,
                                                  0 /* ignored */, 0 /* ignored */, &paramsInt64_[index],
                                                  sizeof(int64_t), NULL)))
              {
                throw Orthanc::OrthancException(Orthanc::ErrorCode_Database,
                                                "Cannot bind integer parameter: " + statement_.FormatError());
              }
                                                  
              break;

            case ValueType_Utf8String:
            {
              assert(index < paramsString_.size());
              paramsString_[index] = dynamic_cast<const Utf8StringValue&>(value).GetContent();

              const char* content = (paramsString_[index].empty() ? "" : paramsString_[index].c_str());

              if (!SQL_SUCCEEDED(SQLBindParameter(
                                   statement_.GetHandle(), i + 1, SQL_PARAM_INPUT, SQL_C_CHAR, SQL_VARCHAR,
                                   0 /* ignored */, 0 /* ignored */, const_cast<char*>(content), paramsString_[index].size(), NULL)))
              {
                throw Orthanc::OrthancException(Orthanc::ErrorCode_Database,
                                                "Cannot bind UTF-8 parameter: " + statement_.FormatError());
              }
                                                  
              break;
            }

            case ValueType_InputFile:
            {
              assert(index < paramsString_.size());
              paramsString_[index] = dynamic_cast<const InputFileValue&>(value).GetContent();

              const char* content = (paramsString_[index].empty() ? NULL : paramsString_[index].c_str());

              SQLLEN a = paramsString_[index].size();
              if (!SQL_SUCCEEDED(SQLBindParameter(
                                   statement_.GetHandle(), i + 1, SQL_PARAM_INPUT, SQL_C_BINARY, SQL_LONGVARBINARY,
                                   paramsString_[index].size() /* only used by MSSQL */,
                                   0 /* ignored */, const_cast<char*>(content), 0, &a)))
              {
                throw Orthanc::OrthancException(Orthanc::ErrorCode_Database,
                                                "Cannot bind binary parameter: " + statement_.FormatError());
              }

              break;
            }

            default:
              throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
          }
        }
      }
    }

    const Dialect dialect = formatter_.GetAutoincrementDialect();
    
    SQLRETURN code = SQLExecute(statement_.GetHandle());
    
    if (code == SQL_SUCCESS ||
        code == SQL_NO_DATA /* this is the case of DELETE in PostgreSQL and MSSQL */)
    {          
      return new OdbcResult(statement_, dialect);
    }
    else
    {
      statement_.CheckCollision(dialect);

      throw Orthanc::OrthancException(Orthanc::ErrorCode_Database,
                                      "Cannot execute ODBC statement:\n" + statement_.FormatError());
    }
  }
}
