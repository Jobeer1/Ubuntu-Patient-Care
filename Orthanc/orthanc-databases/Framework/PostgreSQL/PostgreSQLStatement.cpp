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


#include "PostgreSQLIncludes.h"  // Must be the first
#include "PostgreSQLStatement.h"

#include "../Common/BinaryStringValue.h"
#include "../Common/InputFileValue.h"
#include "../Common/Integer32Value.h"
#include "../Common/Integer64Value.h"
#include "../Common/NullValue.h"
#include "../Common/ResultBase.h"
#include "../Common/Utf8StringValue.h"
#include "PostgreSQLResult.h"

#include <Compatibility.h>  // For std::unique_ptr<>
#include <Logging.h>
#include <OrthancException.h>
#include <Toolbox.h>
#include <Endianness.h>

#include <cassert>


namespace OrthancDatabases
{
  class PostgreSQLStatement::Inputs : public boost::noncopyable
  {
  private:
    std::vector<char*> values_;
    std::vector<int> sizes_;

    static char* Allocate(const void* source, int size)
    {
      if (size == 0)
      {
        return NULL;
      }
      else
      {
        char* ptr = reinterpret_cast<char*>(malloc(size));

        if (source != NULL)
        {
          memcpy(ptr, source, size);
        }

        return ptr;
      }
    }

    void Resize(size_t size)
    {
      // Shrinking of the vector
      for (size_t i = size; i < values_.size(); i++)
      {
        if (values_[i] != NULL)
          free(values_[i]);
      }

      values_.resize(size, NULL);
      sizes_.resize(size, 0);
    }

    void EnlargeForIndex(size_t index)
    {
      if (index >= values_.size())
      {
        // The vector is too small
        Resize(index + 1);
      }
    }

  public:
    Inputs()
    {
    }

    ~Inputs()
    {
      Resize(0);
    }

    void SetItem(size_t pos, const void* source, int size)
    {
      EnlargeForIndex(pos);

      if (sizes_[pos] == size)
      {
        if (source && size != 0)
        {
          memcpy(values_[pos], source, size);
        }
      }
      else
      {
        if (values_[pos] != NULL)
        {
          free(values_[pos]);
        }

        values_[pos] = Allocate(source, size);
        sizes_[pos] = size;
      }
    }

    void SetItem(size_t pos, int size)
    {
      SetItem(pos, NULL, size);
    }

    void* GetItem(size_t pos) const
    {
      if (pos >= values_.size())
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
      }

      return values_[pos];
    }

    const std::vector<char*>& GetValues() const
    {
      return values_;
    }

    const std::vector<int>& GetSizes() const
    {
      return sizes_;
    }
  };


  void PostgreSQLStatement::Prepare()
  {
    if (id_.size() > 0)
    {
      // Already prepared
      return;
    }

    for (size_t i = 0; i < oids_.size(); i++)
    {
      if (oids_[i] == 0)
      {
        // The type of an input parameter was not set
        throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
      }
    }

    id_ = Orthanc::Toolbox::GenerateUuid();

    const unsigned int* tmp = oids_.size() ? &oids_[0] : NULL;

    PGresult* result = PQprepare(reinterpret_cast<PGconn*>(database_.pg_),
                                 id_.c_str(), sql_.c_str(), oids_.size(), tmp);

    if (result == NULL)
    {
      id_.clear();
      database_.ThrowException(true);
    }

    bool ok = (PQresultStatus(result) == PGRES_COMMAND_OK);
    if (ok)
    {
      PQclear(result);
    }
    else
    {
      std::string message = PQresultErrorMessage(result);
      PQclear(result);
      id_.clear();
      LOG(ERROR) << "PostgreSQL error: " << message;
      database_.ThrowException(false);
    }
  }


  void PostgreSQLStatement::Unprepare()
  {
    if (id_.size() > 0)
    {
      // "Although there is no libpq function for deleting a
      // prepared statement, the SQL DEALLOCATE statement can be
      // used for that purpose."
      database_.ExecuteMultiLines("DEALLOCATE \"" + id_ + "\"");
    }

    id_.clear();
  }


  void PostgreSQLStatement::DeclareInputInternal(unsigned int param,
                                                 unsigned int /*Oid*/ type)
  {
    Unprepare();

    if (oids_.size() <= param)
    {
      oids_.resize(param + 1, 0);
      binary_.resize(param + 1);
    }

    oids_[param] = type;
    binary_[param] = (type == TEXTOID || type == OIDOID) ? 0 : 1;
  }


  void PostgreSQLStatement::DeclareInputInteger(unsigned int param)
  {
    DeclareInputInternal(param, INT4OID);
  }
    

  void PostgreSQLStatement::DeclareInputInteger64(unsigned int param)
  {
    DeclareInputInternal(param, INT8OID);
  }


  void PostgreSQLStatement::DeclareInputString(unsigned int param)
  {
    DeclareInputInternal(param, TEXTOID);
  }


  void PostgreSQLStatement::DeclareInputBinary(unsigned int param)
  {
    DeclareInputInternal(param, BYTEAOID);
  }


  void PostgreSQLStatement::DeclareInputLargeObject(unsigned int param)
  {
    DeclareInputInternal(param, OIDOID);
  }


  void* /* PGresult* */ PostgreSQLStatement::Execute()
  {
    Prepare();

    PGresult* result;

    if (oids_.size() == 0)
    {
      // No parameter
      result = PQexecPrepared(reinterpret_cast<PGconn*>(database_.pg_),
                              id_.c_str(), 0, NULL, NULL, NULL, 1);
    }
    else
    {
      // At least 1 parameter
      result = PQexecPrepared(reinterpret_cast<PGconn*>(database_.pg_),
                              id_.c_str(),
                              oids_.size(),
                              &inputs_->GetValues()[0],
                              &inputs_->GetSizes()[0],
                              &binary_[0],
                              1);
    }

    if (PQtransactionStatus(reinterpret_cast<PGconn*>(database_.pg_)) == PQTRANS_INERROR)
    {
      std::string message;

      if (result != NULL)
      {
        message.assign(PQresultErrorMessage(result));
        PQclear(result);  // Frees the memory allocated by "PQresultErrorMessage()"
      }

      if (message.empty())
      {
        message = "Collision between multiple writers";
      }

#if ORTHANC_PLUGINS_VERSION_IS_ABOVE(1, 9, 2)
      throw Orthanc::OrthancException(Orthanc::ErrorCode_DatabaseCannotSerialize, message, false); // don't log here, it is handled #else
#else
      throw Orthanc::OrthancException(Orthanc::ErrorCode_Database, message);
#endif
    }
    else if (result == NULL)
    {
      database_.ThrowException(true);
    }

    return result;
  }


  PostgreSQLStatement::PostgreSQLStatement(PostgreSQLDatabase& database,
                                           const std::string& sql) :
    database_(database),
    sql_(sql),
    inputs_(new Inputs),
    formatter_(Dialect_PostgreSQL)
  {
    if (database.IsVerboseEnabled())
    {
      LOG(TRACE) << "PostgreSQL: " << sql;
    }
  }


  PostgreSQLStatement::PostgreSQLStatement(PostgreSQLDatabase& database,
                                           const Query& query) :
    database_(database),
    inputs_(new Inputs),
    formatter_(Dialect_PostgreSQL)
  {
    query.Format(sql_, formatter_);
    
    if (database.IsVerboseEnabled())
    {
      LOG(TRACE) << "PostgreSQL: " << sql_;
    }

    for (size_t i = 0; i < formatter_.GetParametersCount(); i++)
    {
      switch (formatter_.GetParameterType(i))
      {
        case ValueType_Integer64:
          DeclareInputInteger64(i);
          break;

        case ValueType_Integer32:
          DeclareInputInteger(i);
          break;

        case ValueType_Utf8String:
          DeclareInputString(i);
          break;

        case ValueType_BinaryString:
          DeclareInputBinary(i);
          break;

        case ValueType_InputFile:
          DeclareInputLargeObject(i);
          break;

        case ValueType_Null:
        default:
          throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
      }
    }
  }


  PostgreSQLStatement::~PostgreSQLStatement()
  {
    try
    {
      Unprepare();
    }
    catch (Orthanc::OrthancException&)
    {
      // Ignore possible exceptions due to connection loss
    }
  }


  void PostgreSQLStatement::Run()
  {
    PGresult* result = reinterpret_cast<PGresult*>(Execute());
    assert(result != NULL);   // An exception would have been thrown otherwise

    bool ok = (PQresultStatus(result) == PGRES_COMMAND_OK ||
               PQresultStatus(result) == PGRES_TUPLES_OK);
    if (ok)
    {
      PQclear(result);
    }
    else
    {
      std::string error = PQresultErrorMessage(result);
      PQclear(result);
      LOG(ERROR) << "PostgreSQL error: " << error;
      database_.ThrowException(false);
    }
  }


  void PostgreSQLStatement::BindNull(unsigned int param)
  {
    if (param >= oids_.size())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }

    inputs_->SetItem(param, 0);
  }


  void PostgreSQLStatement::BindInteger(unsigned int param,
                                        int value)
  {
    if (param >= oids_.size())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }

    if (oids_[param] != INT4OID)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadParameterType);
    }

    assert(sizeof(int32_t) == 4);
    int32_t v = htobe32(static_cast<int32_t>(value));
    inputs_->SetItem(param, &v, sizeof(int32_t));
  }


  void PostgreSQLStatement::BindInteger64(unsigned int param,
                                          int64_t value)
  {
    if (param >= oids_.size())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }

    if (oids_[param] != INT8OID)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadParameterType);
    }

    assert(sizeof(int64_t) == 8);
    int64_t v = htobe64(value);
    inputs_->SetItem(param, &v, sizeof(int64_t));
  }


  void PostgreSQLStatement::BindString(unsigned int param,
                                       const std::string& value)
  {
    if (param >= oids_.size())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }

    switch (oids_[param])
    {
      case TEXTOID:
      {
        std::string s = value + '\0';  // Make sure that there is an end-of-string character
        inputs_->SetItem(param, s.c_str(), s.size());
        break;
      }

      case BYTEAOID:
        inputs_->SetItem(param, value.c_str(), value.size());
        break;

      default:
        throw Orthanc::OrthancException(Orthanc::ErrorCode_BadParameterType);
    }
  }


  void PostgreSQLStatement::BindLargeObject(unsigned int param,
                                            const PostgreSQLLargeObject& value)
  {
    if (param >= oids_.size())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }

    if (oids_[param] != OIDOID)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadParameterType);
    }

    inputs_->SetItem(param, value.GetOid().c_str(), 
                     value.GetOid().size() + 1);  // "+1" for end-of-string character
  }


  class PostgreSQLStatement::ResultWrapper : public ResultBase
  {
  private:
    std::unique_ptr<PostgreSQLResult>  result_;

  protected:
    virtual IValue* FetchField(size_t index)
    {
      return result_->GetValue(index);
    }

  public:
    explicit ResultWrapper(PostgreSQLStatement& statement) :
      result_(new PostgreSQLResult(statement))
    {
      SetFieldsCount(result_->GetColumnsCount());
      FetchFields();
    }

    virtual void Next()
    {
      result_->Next();
      FetchFields();
    }

    virtual bool IsDone() const
    {
      return result_->IsDone();
    }
  };


  IResult* PostgreSQLStatement::Execute(ITransaction& transaction,
                                        const Dictionary& parameters)
  {
    for (size_t i = 0; i < formatter_.GetParametersCount(); i++)
    {
      const std::string& name = formatter_.GetParameterName(i);
      
      const IValue& value = parameters.GetValue(name);

      if (value.GetType() == ValueType_Null || value.IsNull())
      {
        BindNull(i);
      }
      else
      {
        switch (formatter_.GetParameterType(i))
        {
          case ValueType_Integer64:
            BindInteger64(i, dynamic_cast<const Integer64Value&>(value).GetValue());
            break;

          case ValueType_Integer32:
            BindInteger(i, dynamic_cast<const Integer32Value&>(value).GetValue());
            break;

          case ValueType_Utf8String:
            BindString(i, dynamic_cast<const Utf8StringValue&>(value).GetContent());
            break;

          case ValueType_BinaryString:
            BindString(i, dynamic_cast<const BinaryStringValue&>(value).GetContent());
            break;

          case ValueType_InputFile:
          {
            const InputFileValue& blob = dynamic_cast<const InputFileValue&>(value);

            PostgreSQLLargeObject largeObject(database_, blob.GetContent());
            BindLargeObject(i, largeObject);
            break;
          }

          default:
            throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
        }
      }
    }

    return new ResultWrapper(*this);
  }


  void PostgreSQLStatement::ExecuteWithoutResult(ITransaction& transaction,
                                                 const Dictionary& parameters)
  {
    std::unique_ptr<IResult> dummy(Execute(transaction, parameters));
  }
}
