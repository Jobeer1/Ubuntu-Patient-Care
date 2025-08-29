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


#include "MySQLDatabase.h"

#include "../Common/ImplicitTransaction.h"
#include "../Common/Integer64Value.h"
#include "../Common/RetryDatabaseFactory.h"
#include "MySQLResult.h"
#include "MySQLStatement.h"
#include "MySQLTransaction.h"

#include <Compatibility.h>  // For std::unique_ptr<>
#include <Logging.h>
#include <OrthancException.h>
#include <Toolbox.h>

#include <errmsg.h>
#include <mysqld_error.h>

#include <memory>
#include <boost/thread.hpp>

namespace OrthancDatabases
{
  void MySQLDatabase::Close()
  {
    if (mysql_ != NULL)
    {
      LOG(INFO) << "Closing connection to MySQL database";
      mysql_close(mysql_);
      mysql_ = NULL;
    }
  }


  void MySQLDatabase::ThrowException()
  {
    LogError();

    unsigned int error = mysql_errno(mysql_);
    if (error == CR_SERVER_GONE_ERROR ||
        error == CR_SERVER_LOST ||
        error == ER_QUERY_INTERRUPTED)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_DatabaseUnavailable);
    }
    else if (error == CR_COMMANDS_OUT_OF_SYNC)
    {
#if !defined(MARIADB_VERSION_ID)
      LOG(ERROR) << "TODO - This error seems to be related to the use of libmysqlclient: Try to switch to mariadb-connector";
#endif
      
      throw Orthanc::OrthancException(Orthanc::ErrorCode_DatabaseUnavailable);
    }
    else if (error == ER_LOCK_DEADLOCK)
    {
#if ORTHANC_PLUGINS_VERSION_IS_ABOVE(1, 9, 2)
      throw Orthanc::OrthancException(Orthanc::ErrorCode_DatabaseCannotSerialize);
#else
      throw Orthanc::OrthancException(Orthanc::ErrorCode_Database, "Collision between multiple writers");
#endif
    } 
    else
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_Database);
    }
  }


  void MySQLDatabase::CheckErrorCode(int code)
  {
    if (code == 0)
    {
      return;
    }
    else
    {
      ThrowException();
    }
  }


  MySQLDatabase::MySQLDatabase(const MySQLParameters& parameters) :
    parameters_(parameters),
    mysql_(NULL)
  {
  }


  MySQLDatabase::~MySQLDatabase()
  {
    try
    {
      Close();
    }
    catch (Orthanc::OrthancException&)
    {
      // Ignore possible exceptions due to connection loss
    }
  }


  void MySQLDatabase::LogError()
  {
    if (mysql_ != NULL)
    {
      LOG(ERROR) << "MySQL error (" << mysql_errno(mysql_)
                 << "," << mysql_sqlstate(mysql_)
                 << "): " << mysql_error(mysql_);
    }
  }

  
  MYSQL* MySQLDatabase::GetObject()
  {
    if (mysql_ == NULL)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
    }
    else
    {
      return mysql_;
    }
  }

  
  void MySQLDatabase::OpenInternal(const char* db)
  {
    if (mysql_ != NULL)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
    }

    mysql_ = mysql_init(NULL);
    if (mysql_ == NULL)
    {
      LOG(ERROR) << "Cannot initialize the MySQL connector";
      throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
    }

    if (parameters_.GetUnixSocket().empty())
    {
      // Fallback to TCP connection if no UNIX socket is provided
      unsigned int protocol = MYSQL_PROTOCOL_TCP;
      mysql_options(mysql_, MYSQL_OPT_PROTOCOL, (unsigned int *) &protocol);
    }

    if (parameters_.IsSsl())
    {
      if (parameters_.IsVerifyServerCertificates())
      {
#if (MYSQL_VERSION_ID > 50110 && MYSQL_VERSION_ID < 80000)  // Removed in MySQL client 8.0
        my_bool verifyCert = 1;
        mysql_options(mysql_, MYSQL_OPT_SSL_VERIFY_SERVER_CERT, (void *) &verifyCert);
#endif
        
        mysql_options(mysql_, MYSQL_OPT_SSL_CA, (void *)(parameters_.GetSslCaCertificates()));
      }

#if (MYSQL_VERSION_ID > 50110 && MYSQL_VERSION_ID < 80000)  // Removed in MySQL client 8.0
      my_bool enforceTls = 1;
      mysql_options(mysql_, MYSQL_OPT_SSL_ENFORCE, (void *) &enforceTls);
#endif
    }

    const char* socket = (parameters_.GetUnixSocket().empty() ? NULL :
                          parameters_.GetUnixSocket().c_str());

    if (mysql_real_connect(mysql_,
                           parameters_.GetHost().c_str(),
                           parameters_.GetUsername().c_str(),
                           parameters_.GetPassword().c_str(), db,
                           parameters_.GetPort(), socket, 0) == 0)
    {
      LogError();
      Close();
      throw Orthanc::OrthancException(Orthanc::ErrorCode_DatabaseUnavailable);
    }
    else
    {
      LOG(INFO) << "Successful connection to MySQL database";
    }

    if (mysql_set_character_set(mysql_, "utf8mb4") != 0)
    {
      LOG(ERROR) << "Cannot set the character set to UTF8";
      Close();
      throw Orthanc::OrthancException(Orthanc::ErrorCode_Database);        
    }
  }

  
  void MySQLDatabase::Open()
  {
    if (parameters_.GetDatabase().empty())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);        
    }
    else
    {
      OpenInternal(parameters_.GetDatabase().c_str());
    }
  }
  

  void MySQLDatabase::ClearDatabase(const MySQLParameters& parameters)
  {
    MySQLDatabase db(parameters);
    db.OpenRoot();

    const std::string& database = parameters.GetDatabase();
    
    {
      MySQLTransaction t(db, TransactionType_ReadWrite);

      if (!db.DoesDatabaseExist(t, database))
      {
        LOG(ERROR) << "Inexistent database, please create it first: " << database;
        throw Orthanc::OrthancException(Orthanc::ErrorCode_UnknownResource);
      }
      
      db.ExecuteMultiLines("DROP DATABASE " + database, false);
      db.ExecuteMultiLines("CREATE DATABASE " + database, false);
      t.Commit();
    }
  }


  namespace
  {
    class ResultWrapper : public boost::noncopyable
    {
    private:
      MYSQL_RES *result_;

    public:
      ResultWrapper(MySQLDatabase& mysql,
                    const std::string& sql) :
        result_(NULL)
      {
        if (mysql_real_query(mysql.GetObject(), sql.c_str(), sql.size()))
        {
          mysql.LogError();
          throw Orthanc::OrthancException(Orthanc::ErrorCode_Database);
        }

        result_ = mysql_use_result(mysql.GetObject());
        if (result_ == NULL)
        {
          mysql.LogError();
          throw Orthanc::OrthancException(Orthanc::ErrorCode_Database);
        }
      }

      ~ResultWrapper()
      {
        if (result_ != NULL)
        {
          mysql_free_result(result_);
          result_ = NULL;
        }
      }

      MYSQL_RES *GetObject()
      {
        return result_;
      }
    };
  }


  bool MySQLDatabase::LookupGlobalStringVariable(std::string& value,
                                                 const std::string& variable)
  {
    ResultWrapper result(*this, "SELECT @@global." + variable);

    MYSQL_ROW row = mysql_fetch_row(result.GetObject());
    if (mysql_errno(mysql_) == 0 &&
        row &&
        row[0])
    {
      value = std::string(row[0]);
      return true;
    }
    else
    {
      return false;
    }
  }

  
  bool MySQLDatabase::LookupGlobalIntegerVariable(int64_t& value,
                                                  const std::string& variable)
  {
    std::string s;
    
    if (LookupGlobalStringVariable(s, variable))
    {
      try
      {
        value = boost::lexical_cast<int64_t>(s);
        return true;
      }
      catch (boost::bad_lexical_cast&)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_Database);
      }
    }
    else
    {
      return false;
    }
  }


  bool MySQLDatabase::RunAdvisoryLockStatement(Query& query,
                                               const std::string& lock)
  {
    const std::string& dbName = parameters_.GetDatabase();

    // Prepend the name of the lock by the database name. This allows
    // to create a namespace for advisory locks:
    // https://groups.google.com/d/msg/orthanc-users/yV3LSTh_TjI/MQIcvnMlAQAJ
    std::string prefix;
    prefix.reserve(dbName.size());
    for (size_t i = 0; i < dbName.size(); i++)
    {
      if (isalnum(dbName[i]) ||
          dbName[i] == '$' ||
          dbName[i] == '_')
      {
        prefix.push_back(dbName[i]);
      }
    }

    query.SetType("lock", ValueType_Utf8String);
    
    Dictionary args;
    args.SetUtf8Value("lock", prefix + "." + lock);

    bool success;

    {
      MySQLStatement statement(*this, query);

      MySQLTransaction t(*this, TransactionType_ReadWrite);
      std::unique_ptr<IResult> result(t.Execute(statement, args));

      success = (!result->IsDone() &&
                 result->GetField(0).GetType() == ValueType_Integer64 &&
                 dynamic_cast<const Integer64Value&>(result->GetField(0)).GetValue() == 1);
      
      t.Commit();
    }

    return success;
  }
  

  bool MySQLDatabase::AcquireAdvisoryLock(const std::string& lock)
  {
    Query query("SELECT GET_LOCK(${lock}, 0)", false);
    return RunAdvisoryLockStatement(query, lock);
  }
  

  bool MySQLDatabase::ReleaseAdvisoryLock(const std::string& lock)
  {
    Query query("SELECT RELEASE_LOCK(${lock})", false);
    return RunAdvisoryLockStatement(query, lock);
  }


  void MySQLDatabase::AdvisoryLock(const std::string& lock)
  {
    if (!AcquireAdvisoryLock(lock))
    {
      LOG(ERROR) << "The MySQL database is locked by another instance of Orthanc";
      throw Orthanc::OrthancException(Orthanc::ErrorCode_Database);
    }
  }


  bool MySQLDatabase::DoesTableExist(MySQLTransaction& transaction,
                                     const std::string& name)
  {
    if (mysql_ == NULL)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
    }

    if (!IsValidDatabaseIdentifier(name))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
  
    Query query("SELECT COUNT(*) FROM information_schema.TABLES WHERE "
                "(TABLE_SCHEMA = ${database}) AND (TABLE_NAME = ${table})", true);
    query.SetType("database", ValueType_Utf8String);
    query.SetType("table", ValueType_Utf8String);
    
    MySQLStatement statement(*this, query);

    Dictionary args;
    args.SetUtf8Value("database", parameters_.GetDatabase());
    args.SetUtf8Value("table", name);

    std::unique_ptr<IResult> result(statement.Execute(transaction, args));
    return (!result->IsDone() &&
            result->GetFieldsCount() == 1 &&
            result->GetField(0).GetType() == ValueType_Integer64 &&
            dynamic_cast<const Integer64Value&>(result->GetField(0)).GetValue() == 1);            
  }


  bool MySQLDatabase::DoesDatabaseExist(MySQLTransaction& transaction,
                                        const std::string& name)
  {
    if (mysql_ == NULL)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
    }

    if (!IsValidDatabaseIdentifier(name))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
  
    Query query("SELECT COUNT(*) FROM information_schema.SCHEMATA "
                "WHERE SCHEMA_NAME = ${database}", true);
    query.SetType("database", ValueType_Utf8String);
    
    MySQLStatement statement(*this, query);

    Dictionary args;
    args.SetUtf8Value("database", name);

    std::unique_ptr<IResult> result(statement.Execute(transaction, args));
    return (!result->IsDone() &&
            result->GetFieldsCount() == 1 &&
            result->GetField(0).GetType() == ValueType_Integer64 &&
            dynamic_cast<const Integer64Value&>(result->GetField(0)).GetValue() == 1);            
  }


  bool MySQLDatabase::DoesTriggerExist(MySQLTransaction& transaction,
                                       const std::string& name)
  {
    if (mysql_ == NULL)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
    }

    if (!IsValidDatabaseIdentifier(name))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
  
    Query query("SELECT COUNT(*) FROM information_schema.TRIGGERS "
                "WHERE TRIGGER_NAME = ${trigger}", true);
    query.SetType("trigger", ValueType_Utf8String);
    
    MySQLStatement statement(*this, query);

    Dictionary args;
    args.SetUtf8Value("trigger", name);

    std::unique_ptr<IResult> result(statement.Execute(transaction, args));
    return (!result->IsDone() &&
            result->GetFieldsCount() == 1 &&
            result->GetField(0).GetType() == ValueType_Integer64 &&
            dynamic_cast<const Integer64Value&>(result->GetField(0)).GetValue() != 0);
  }


  void MySQLDatabase::ExecuteMultiLines(const std::string& sql,
                                        bool arobaseSeparator)
  {
    if (mysql_ == NULL)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
    }

    // This emulates the behavior of "CLIENT_MULTI_STATEMENTS" in
    // "mysql_real_connect()", avoiding to implement a loop over
    // "mysql_query()"
    std::vector<std::string> commands;
    Orthanc::Toolbox::TokenizeString(commands, sql, ';');

    for (size_t i = 0; i < commands.size(); i++)
    {
      std::string s = Orthanc::Toolbox::StripSpaces(commands[i]);

      if (!s.empty())
      {
        if (arobaseSeparator)
        {
          // Replace the escape character "@" by a semicolon
          std::replace(s.begin(), s.end(), '@', ';');
        }
      
        LOG(TRACE) << "MySQL: " << s;
        CheckErrorCode(mysql_query(mysql_, s.c_str()));
      }
    }
  }

  
  IPrecompiledStatement* MySQLDatabase::Compile(const Query& query)
  {
    if (mysql_ == NULL)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
    }

    return new MySQLStatement(*this, query);
  }



  namespace
  {
    class MySQLImplicitTransaction : public ImplicitTransaction
    {
    private:
      MySQLDatabase& db_;
      
    protected:
      virtual IResult* ExecuteInternal(IPrecompiledStatement& statement,
                                       const Dictionary& parameters) ORTHANC_OVERRIDE
      {
        return dynamic_cast<MySQLStatement&>(statement).Execute(*this, parameters);
      }

      virtual void ExecuteWithoutResultInternal(IPrecompiledStatement& statement,
                                                const Dictionary& parameters) ORTHANC_OVERRIDE
      {
        dynamic_cast<MySQLStatement&>(statement).ExecuteWithoutResult(*this, parameters);
      }

    public:
      explicit MySQLImplicitTransaction(MySQLDatabase& db) :
        db_(db)
      {
      }
      
      virtual bool DoesTableExist(const std::string& name) ORTHANC_OVERRIDE
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError, "An explicit transaction is needed");
      }

      virtual bool DoesIndexExist(const std::string& name) ORTHANC_OVERRIDE
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError, "An explicit transaction is needed");
      }

      virtual bool DoesTriggerExist(const std::string& name) ORTHANC_OVERRIDE
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError, "An explicit transaction is needed");
      }

      virtual void ExecuteMultiLines(const std::string& query) ORTHANC_OVERRIDE
      {
        db_.ExecuteMultiLines(query, false /* don't deal with arobases */);
      }
    };
  }
  

  ITransaction* MySQLDatabase::CreateTransaction(TransactionType type)
  {
    if (mysql_ == NULL)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
    }

    switch (type)
    {
      case TransactionType_Implicit:
        return new MySQLImplicitTransaction(*this);

      case TransactionType_ReadOnly:
      case TransactionType_ReadWrite:
        return new MySQLTransaction(*this, type);

      default:
        throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
  }

  
  void MySQLDatabase::GlobalFinalization()
  {
    mysql_library_end();
  } 


  bool MySQLDatabase::IsValidDatabaseIdentifier(const std::string& s)
  {
    for (size_t i = 0; i < s.length(); i++)
    {
      // https://dev.mysql.com/doc/refman/8.0/en/identifiers.html
      if (!isalnum(s[i]) &&
          s[i] != '$' &&
          s[i] != '_')
      {
        return false;
      }
    }

    return true;
  }


  MySQLDatabase::TransientAdvisoryLock::
  TransientAdvisoryLock(MySQLDatabase&  database,
                        const std::string& lock) :
    database_(database),
    lock_(lock)
  {
    bool locked = true;
    
    for (unsigned int i = 0; i < 10; i++)
    {
      if (database_.AcquireAdvisoryLock(lock_))
      {
        locked = false;
        break;
      }
      else
      {
        boost::this_thread::sleep(boost::posix_time::milliseconds(500));
      }
    }

    if (locked)
    {
      LOG(ERROR) << "Cannot acquire a transient advisory lock";
      throw Orthanc::OrthancException(Orthanc::ErrorCode_Plugin);
    }    
  }
    

  MySQLDatabase::TransientAdvisoryLock::~TransientAdvisoryLock()
  {
    database_.ReleaseAdvisoryLock(lock_);
  }

  
  class MySQLDatabase::Factory : public RetryDatabaseFactory
  {
  private:
    MySQLParameters  parameters_;

  protected:
    virtual IDatabase* TryOpen()
    {
      std::unique_ptr<MySQLDatabase> db(new MySQLDatabase(parameters_));
      db->Open();
      db->ExecuteMultiLines("SET SESSION TRANSACTION ISOLATION LEVEL SERIALIZABLE", false);
      return db.release();
    }
      
  public:
    explicit Factory(const MySQLParameters& parameters) :
      RetryDatabaseFactory(parameters.GetMaxConnectionRetries(),
                           parameters.GetConnectionRetryInterval()),
      parameters_(parameters)
    {
    }
  };


  IDatabaseFactory* MySQLDatabase::CreateDatabaseFactory(const MySQLParameters& parameters)
  {
    return new Factory(parameters);
  }


  MySQLDatabase* MySQLDatabase::CreateDatabaseConnection(const MySQLParameters& parameters)
  {
    Factory factory(parameters);
    return dynamic_cast<MySQLDatabase*>(factory.Open());
  }
}
