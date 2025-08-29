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
#include "PostgreSQLDatabase.h"

#include "../Common/ImplicitTransaction.h"
#include "../Common/RetryDatabaseFactory.h"
#include "PostgreSQLResult.h"
#include "PostgreSQLStatement.h"
#include "PostgreSQLTransaction.h"

#include <Logging.h>
#include <OrthancException.h>
#include <Toolbox.h>

#include <boost/lexical_cast.hpp>
#include <boost/thread.hpp>


namespace OrthancDatabases
{
  void PostgreSQLDatabase::ThrowException(bool log)
  {
    if (log)
    {
      LOG(ERROR) << "PostgreSQL error: "
                 << PQerrorMessage(reinterpret_cast<PGconn*>(pg_));
    }
    
    if (PQstatus(reinterpret_cast<PGconn*>(pg_)) == CONNECTION_OK)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_Database);
    }
    else
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_DatabaseUnavailable);
    }
  }


  void PostgreSQLDatabase::Close()
  {
    if (pg_ != NULL)
    {
      LOG(TRACE) << "Closing connection to PostgreSQL";
      PQfinish(reinterpret_cast<PGconn*>(pg_));
      pg_ = NULL;
    }
  }


  PostgreSQLDatabase::~PostgreSQLDatabase()
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
  
  
  void PostgreSQLDatabase::Open()
  {
    if (pg_ != NULL)
    {
      // Already connected
      return;
    }

    std::string s;
    parameters_.Format(s);

    pg_ = PQconnectdb(s.c_str());

    if (pg_ == NULL ||
        PQstatus(reinterpret_cast<PGconn*>(pg_)) != CONNECTION_OK)
    {
      std::string message;

      if (pg_)
      {
        message = PQerrorMessage(reinterpret_cast<PGconn*>(pg_));
        PQfinish(reinterpret_cast<PGconn*>(pg_));
        pg_ = NULL;
      }

      LOG(ERROR) << "PostgreSQL error: " << message;
      throw Orthanc::OrthancException(Orthanc::ErrorCode_DatabaseUnavailable);
    }
  }


  bool PostgreSQLDatabase::RunAdvisoryLockStatement(const std::string& statement)
  {
    PostgreSQLTransaction transaction(*this, TransactionType_ReadWrite);

    Query query(statement, false);
    PostgreSQLStatement s(*this, query);

    PostgreSQLResult result(s);

    bool success = (!result.IsDone() &&
                    result.GetBoolean(0));

    transaction.Commit();

    return success;
  }
  

  bool PostgreSQLDatabase::AcquireAdvisoryLock(int32_t lock)
  {
    return RunAdvisoryLockStatement(
      "select pg_try_advisory_lock(" + 
      boost::lexical_cast<std::string>(lock) + ")");
  }


  bool PostgreSQLDatabase::ReleaseAdvisoryLock(int32_t lock)
  {
    return RunAdvisoryLockStatement(
      "select pg_advisory_unlock(" + 
      boost::lexical_cast<std::string>(lock) + ")");
  }


  void PostgreSQLDatabase::AdvisoryLock(int32_t lock)
  {
    if (!AcquireAdvisoryLock(lock))
    {
      LOG(ERROR) << "The PostgreSQL database is locked by another instance of Orthanc";
      throw Orthanc::OrthancException(Orthanc::ErrorCode_Database);
    }
  }


  void PostgreSQLDatabase::ExecuteMultiLines(const std::string& sql)
  {
    if (IsVerboseEnabled())
    {
      LOG(INFO) << "PostgreSQL: " << sql;
    }
    Open();

    PGresult* result = PQexec(reinterpret_cast<PGconn*>(pg_), sql.c_str());
    if (result == NULL)
    {
      ThrowException(true);
    }

    bool ok = (PQresultStatus(result) == PGRES_COMMAND_OK ||
               PQresultStatus(result) == PGRES_TUPLES_OK);

    if (ok)
    {
      PQclear(result);
    }
    else
    {
      std::string message = PQresultErrorMessage(result);
      PQclear(result);

      LOG(ERROR) << "PostgreSQL error: " << message;
      ThrowException(false);
    }
  }


  bool PostgreSQLDatabase::DoesTableExist(const std::string& name)
  {
    std::string lower;
    Orthanc::Toolbox::ToLowerCase(lower, name);

    // http://stackoverflow.com/a/24089729/881731

    PostgreSQLStatement statement(*this, 
                                  "SELECT 1 FROM pg_catalog.pg_class c "
                                  "JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace "
                                  "WHERE n.nspname = 'public' AND c.relkind='r' "
                                  "AND c.relname=$1");

    statement.DeclareInputString(0);
    statement.BindString(0, lower);

    PostgreSQLResult result(statement);
    return !result.IsDone();
  }

  bool PostgreSQLDatabase::DoesIndexExist(const std::string& name)
  {
    std::string lower;
    Orthanc::Toolbox::ToLowerCase(lower, name);

    // http://stackoverflow.com/a/24089729/881731

    PostgreSQLStatement statement(*this, 
                                  "SELECT 1 FROM pg_catalog.pg_class c "
                                  "JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace "
                                  "WHERE n.nspname = 'public' AND c.relkind='i' "
                                  "AND c.relname=$1");

    statement.DeclareInputString(0);
    statement.BindString(0, lower);

    PostgreSQLResult result(statement);
    return !result.IsDone();
  }


  bool PostgreSQLDatabase::DoesColumnExist(const std::string& tableName,
                                           const std::string& columnName)
  {
    std::string lowerTable, lowerColumn;
    Orthanc::Toolbox::ToLowerCase(lowerTable, tableName);
    Orthanc::Toolbox::ToLowerCase(lowerColumn, columnName);

    PostgreSQLStatement statement(*this,
                                  "SELECT 1 FROM information_schema.columns "
                                  "WHERE table_schema=$1 AND table_name=$2 AND column_name=$3");
 
    statement.DeclareInputString(0);
    statement.DeclareInputString(1);
    statement.DeclareInputString(2);
    
    statement.BindString(0, "public" /* schema */);
    statement.BindString(1, lowerTable);
    statement.BindString(2, lowerColumn);
    
    PostgreSQLResult result(statement);
    return !result.IsDone();
  }


  void PostgreSQLDatabase::ClearAll()
  {
    PostgreSQLTransaction transaction(*this, TransactionType_ReadWrite);
    
    // Remove all the large objects
    ExecuteMultiLines("SELECT lo_unlink(loid) FROM (SELECT DISTINCT loid FROM pg_catalog.pg_largeobject) as loids;");

    // http://stackoverflow.com/a/21247009/881731
    ExecuteMultiLines("DROP SCHEMA public CASCADE;");
    ExecuteMultiLines("CREATE SCHEMA public;");
    ExecuteMultiLines("GRANT ALL ON SCHEMA public TO postgres;");
    ExecuteMultiLines("GRANT ALL ON SCHEMA public TO public;");
    ExecuteMultiLines("COMMENT ON SCHEMA public IS 'standard public schema';");

    transaction.Commit();
  }


  IPrecompiledStatement* PostgreSQLDatabase::Compile(const Query& query)
  {
    return new PostgreSQLStatement(*this, query);
  }


  namespace
  {
    class PostgreSQLImplicitTransaction : public ImplicitTransaction
    {
    private:
      PostgreSQLDatabase& db_;
      
    protected:
      virtual IResult* ExecuteInternal(IPrecompiledStatement& statement,
                                       const Dictionary& parameters) ORTHANC_OVERRIDE
      {
        return dynamic_cast<PostgreSQLStatement&>(statement).Execute(*this, parameters);
      }

      virtual void ExecuteWithoutResultInternal(IPrecompiledStatement& statement,
                                                const Dictionary& parameters) ORTHANC_OVERRIDE
      {
        dynamic_cast<PostgreSQLStatement&>(statement).ExecuteWithoutResult(*this, parameters);
      }

    public:
      explicit PostgreSQLImplicitTransaction(PostgreSQLDatabase& db) :
        db_(db)
      {
      }

      virtual bool DoesTableExist(const std::string& name) ORTHANC_OVERRIDE
      {
        return db_.DoesTableExist(name.c_str());
      }

      virtual bool DoesIndexExist(const std::string& name) ORTHANC_OVERRIDE
      {
        return db_.DoesIndexExist(name.c_str());
      }

      virtual bool DoesTriggerExist(const std::string& name) ORTHANC_OVERRIDE
      {
        return false;
      }

      virtual void ExecuteMultiLines(const std::string& query) ORTHANC_OVERRIDE
      {
        db_.ExecuteMultiLines(query);
      }
    };
  }
  
  
  ITransaction* PostgreSQLDatabase::CreateTransaction(TransactionType type)
  {
    switch (type)
    {
      case TransactionType_Implicit:
        return new PostgreSQLImplicitTransaction(*this);

      case TransactionType_ReadWrite:
      case TransactionType_ReadOnly:
        return new PostgreSQLTransaction(*this, type);

      default:
        throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
  }


  PostgreSQLDatabase::TransientAdvisoryLock::TransientAdvisoryLock(
    PostgreSQLDatabase&  database,
    int32_t lock,
    unsigned int retries,
    unsigned int retryInterval) :
    database_(database),
    lock_(lock)
  {
    bool locked = true;
    
    for (unsigned int i = 0; i < retries; i++)
    {
      if (database_.AcquireAdvisoryLock(lock_))
      {
        locked = false;
        break;
      }
      else
      {
        boost::this_thread::sleep(boost::posix_time::milliseconds(retryInterval));
      }
    }

    if (locked)
    {
      LOG(ERROR) << "Cannot acquire a transient advisory lock";
      throw Orthanc::OrthancException(Orthanc::ErrorCode_Plugin);
    }    
  }
    

  PostgreSQLDatabase::TransientAdvisoryLock::~TransientAdvisoryLock()
  {
    database_.ReleaseAdvisoryLock(lock_);
  }


  class PostgreSQLDatabase::Factory : public RetryDatabaseFactory
  {
  private:
    PostgreSQLParameters  parameters_;
    
  protected:
    virtual IDatabase* TryOpen()
    {
      std::unique_ptr<PostgreSQLDatabase> db(new PostgreSQLDatabase(parameters_));
      db->Open();
      return db.release();
    }
    
  public:
    explicit Factory(const PostgreSQLParameters& parameters) :
      RetryDatabaseFactory(parameters.GetMaxConnectionRetries(),
                           parameters.GetConnectionRetryInterval()),
      parameters_(parameters)
    {
    }
  };


  IDatabaseFactory* PostgreSQLDatabase::CreateDatabaseFactory(const PostgreSQLParameters& parameters)
  {
    return new Factory(parameters);
  }


  PostgreSQLDatabase* PostgreSQLDatabase::CreateDatabaseConnection(const PostgreSQLParameters& parameters)
  {
    Factory factory(parameters);
    return dynamic_cast<PostgreSQLDatabase*>(factory.Open());
  }
}
