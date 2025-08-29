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


#include "OdbcResult.h"

#include "../Common/BinaryStringValue.h"
#include "../Common/Integer64Value.h"
#include "../Common/NullValue.h"
#include "../Common/Utf8StringValue.h"

#include <ChunkedBuffer.h>
#include <Logging.h>
#include <OrthancException.h>
#include <Toolbox.h>

#include <boost/lexical_cast.hpp>
#include <sqlext.h>


namespace OrthancDatabases
{
  static void ThrowCannotReadString()
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_Database, "Cannot read text field");
  }


  void OdbcResult::LoadFirst()
  {
    if (first_)
    {
      Next();
      first_ = false;
    }
  }

    
  void OdbcResult::SetValue(size_t index,
                            IValue* value)
  {
    std::unique_ptr<IValue> raii(value);
        
    if (index >= values_.size())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
    else if (value == NULL)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_NullPointer);
    }
    else
    {
      if (values_[index] != NULL)
      {
        delete values_[index];
      }
          
      values_[index] = raii.release();
    }
  }
      

  void OdbcResult::ReadString(std::string& target,
                              size_t column,
                              bool isBinary)
  {
    // https://docs.microsoft.com/en-us/sql/odbc/reference/develop-app/getting-long-data

    std::string buffer;
    buffer.resize(1024 * 1024);

    const SQLSMALLINT targetType = (isBinary ? SQL_BINARY : SQL_C_CHAR);

    SQLLEN length;
    SQLRETURN code = SQLGetData(statement_.GetHandle(), column + 1, targetType, &buffer[0], buffer.size(), &length);
    if (code == SQL_NO_DATA)
    {
      target.clear();
    }
    else if (code == SQL_SUCCESS)
    {
      if (length == -1)
      {
        target.clear();  // No data available
      }
      else
      {
        // The "buffer" was large enough to store the text value, plus the null termination
        target.assign(buffer.c_str(), length);
      }
    }
    else if (code == SQL_SUCCESS_WITH_INFO)
    {
      Orthanc::ChunkedBuffer chunks;
      
      if (isBinary)
      {
        chunks.AddChunk(buffer.c_str(), buffer.size());
      }
      else
      {
        /**
         * WARNING: At this point, in the MSSQL driver, "length"
         * contains the number of Unicode characters! This is
         * different from the actual number of **bytes** that are
         * required to store the UTF-8 string. As a consequence, the
         * "length" cannot be used to determine the final size of
         * the "target" string.
         **/
        chunks.AddChunk(buffer.c_str(), buffer.size() - 1);
      }

      for (;;)
      {
        code = SQLGetData(statement_.GetHandle(), column + 1, targetType, &buffer[0], buffer.size(), &length);
            
        if (code == SQL_SUCCESS)
        {
          // This is the last chunk
          if (length == 0 ||
              length > static_cast<SQLLEN>(buffer.size()))
          {
            ThrowCannotReadString();
          }
                  
          chunks.AddChunk(buffer.c_str(), length);
          break;
        }
        else if (code == SQL_SUCCESS_WITH_INFO)
        {
          // This is an intermediate chunk
          if (isBinary)
          {
            chunks.AddChunk(buffer.c_str(), buffer.size());
          }
          else
          {
            chunks.AddChunk(buffer.c_str(), buffer.size() - 1);
          }
        }
        else
        {
          ThrowCannotReadString();
        }
      }
          
      chunks.Flatten(target);
    }
    else
    {
      statement_.CheckCollision(dialect_);
      ThrowCannotReadString();
    }
  }
      

  OdbcResult::OdbcResult(OdbcStatement& statement,
                         Dialect dialect) :
    statement_(statement),
    dialect_(dialect),
    first_(true),
    done_(false)
  {
    SQLSMALLINT count;
    if (!SQL_SUCCEEDED(SQLNumResultCols(statement_.GetHandle(), &count)))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_Database);
    }

    types_.resize(count);
    typeNames_.resize(count);
    values_.resize(count);
        
    for (size_t i = 0; i < values_.size(); i++)
    {
      /**
       * NB: Don't use "SQLDescribeCol()", as it is less flexible
       * (cf. OMSSQL-7: "SQLDescribeParam()" doesn't work with
       * encrypted columns)
       **/
          
      if (!SQL_SUCCEEDED(SQLColAttribute(statement_.GetHandle(), i + 1, SQL_DESC_TYPE, NULL, -1, NULL, &types_[i])))
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_Database);
      }

      SQLCHAR buffer[1024];
      SQLSMALLINT length;

      if (!SQL_SUCCEEDED(SQLColAttribute(statement_.GetHandle(), i + 1, SQL_DESC_TYPE_NAME,
                                         buffer, sizeof(buffer) - 1, &length, NULL)))
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_Database);
      }

      std::string name(reinterpret_cast<const char*>(buffer), length);
      Orthanc::Toolbox::ToLowerCase(typeNames_[i], name);
    }
  }

    
  OdbcResult::~OdbcResult()
  {
    for (size_t i = 0; i < values_.size(); i++)
    {
      if (values_[i] != NULL)
      {
        delete values_[i];
      }
    }

    if (!first_ &&
        !SQL_SUCCEEDED(SQLCloseCursor(statement_.GetHandle())))
    {
      LOG(WARNING) << "Cannot close the ODBC cursor: " << std::endl << statement_.FormatError();
    }
  }
    
      
  void OdbcResult::SetExpectedType(size_t field,
                                   ValueType type) 
  {
    if (field >= types_.size())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
    else
    {
      // Ignore this information
    }
  }


  bool OdbcResult::IsDone() const 
  {
    const_cast<OdbcResult&>(*this).LoadFirst();
    return done_;
  }
    

  void OdbcResult::Next() 
  {
    SQLRETURN code = SQLFetch(statement_.GetHandle());

    if (code == SQL_NO_DATA)
    {
      done_ = true;
    }
    else if (code == SQL_SUCCESS)
    {
      done_ = false;
    }
    else
    {
      statement_.CheckCollision(dialect_);
      throw Orthanc::OrthancException(Orthanc::ErrorCode_Database, "Cannot fetch new row");
    }

    assert(values_.size() == types_.size() &&
           values_.size() == typeNames_.size());

    for (size_t i = 0; i < values_.size(); i++)
    {
      SQLLEN type = types_[i];
      const std::string& name = typeNames_[i];
          
      if (done_)
      {
        SetValue(i, new NullValue);
      }
      else if (type == SQL_INTEGER)
      {
        int32_t value;
        SQLLEN length;
        if (SQL_SUCCEEDED(SQLGetData(statement_.GetHandle(), i + 1, SQL_INTEGER, &value, sizeof(value), &length)))
        {
          if (length == SQL_NULL_DATA)
          {
            SetValue(i, new NullValue);
          }
          else
          {
            SetValue(i, new Integer64Value(value));
          }
        }
        else
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_Database, "Cannot get int32_t field");
        }
      }
      else if (type == SQL_BIGINT ||
               (dialect_ == Dialect_PostgreSQL && name == "bigserial"))
      {
        int64_t value;
        SQLLEN length;
        if (SQL_SUCCEEDED(SQLGetData(statement_.GetHandle(), i + 1, SQL_C_SBIGINT, &value, sizeof(value), &length)))
        {
          if (length == SQL_NULL_DATA)
          {
            SetValue(i, new NullValue);
          }
          else
          {
            SetValue(i, new Integer64Value(value));
          }
        }
        else
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_Database, "Cannot get int64_t field");
        }
      }
      else if (type == SQL_VARCHAR ||
               name == "varchar" ||
               (dialect_ == Dialect_MSSQL && name == "nvarchar") ||  // This means UTF-16
               (dialect_ == Dialect_MySQL && name == "longtext") ||
               (dialect_ == Dialect_MySQL && name.empty() && type == -9) ||  // Seen in "SQLTables()"
               (dialect_ == Dialect_PostgreSQL && name == "text") ||
               (dialect_ == Dialect_SQLite && name == "text") ||
               (dialect_ == Dialect_SQLite && name == "wvarchar"))  // Seen on Windows with sqliteodbc-0.9998-win32.exe
      {
        std::string value;
        ReadString(value, i, false /* not binary */);
        SetValue(i, new Utf8StringValue(value));
      }
      else if (type == SQL_NUMERIC)
      {
        /**
         * SQL_NUMERIC_STRUCT could be used here, but is much more
         * complex to deal with:
         * https://stackoverflow.com/a/9188737/881731
         **/
        
        std::string value;
        ReadString(value, i, false /* not binary */);
        SetValue(i, new Integer64Value(boost::lexical_cast<int64_t>(value)));
      }
      else if (type == SQL_BINARY ||
               (dialect_ == Dialect_PostgreSQL && name == "bytea") ||
               (dialect_ == Dialect_MySQL && name == "longblob") ||
               (dialect_ == Dialect_MSSQL && name == "varbinary"))
      {
        std::string value;
        ReadString(value, i, true /* binary */);
        SetValue(i, new BinaryStringValue(value));
      }
      else
      {
        throw Orthanc::OrthancException(
          Orthanc::ErrorCode_NotImplemented,
          "Unknown type in result: " + name + " (" + boost::lexical_cast<std::string>(type) + ")");
      }
    }
  }


  const IValue& OdbcResult::GetField(size_t field) const 
  {
    if (field >= values_.size())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
    else if (IsDone())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
    }
    else if (values_[field] == NULL)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
    }
    else
    {
      return *values_[field];
    }
  }
}
