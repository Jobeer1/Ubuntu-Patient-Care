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


#include "OdbcDatabase.h"

#include "../../Resources/Orthanc/Plugins/OrthancPluginCppWrapper.h"  // For ORTHANC_PLUGINS_VERSION_IS_ABOVE
#include "../Common/ImplicitTransaction.h"
#include "../Common/RetryDatabaseFactory.h"
#include "../Common/Utf8StringValue.h"
#include "OdbcPreparedStatement.h"
#include "OdbcResult.h"

#include <Logging.h>
#include <OrthancException.h>
#include <Toolbox.h>

#include <boost/algorithm/string/predicate.hpp>
#include <sqlext.h>


namespace OrthancDatabases
{
  static void SetAutoCommitTransaction(SQLHDBC handle,
                                       bool autocommit)
  {
    // Go to autocommit mode
    SQLPOINTER value = (SQLPOINTER) (autocommit ? SQL_AUTOCOMMIT_ON : SQL_AUTOCOMMIT_OFF);
      
    if (!SQL_SUCCEEDED(SQLSetConnectAttr(handle, SQL_ATTR_AUTOCOMMIT, value, SQL_IS_UINTEGER)))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_Database,
                                      "Cannot switch the autocommit mode");
    }
  }
    

  class OdbcDatabase::OdbcImplicitTransaction : public ImplicitTransaction
  {
  private:
    OdbcDatabase&  db_;

  protected:
    virtual IResult* ExecuteInternal(IPrecompiledStatement& statement,
                                     const Dictionary& parameters) ORTHANC_OVERRIDE
    {
      return dynamic_cast<OdbcPreparedStatement&>(statement).Execute(parameters);
    }

    virtual void ExecuteWithoutResultInternal(IPrecompiledStatement& statement,
                                              const Dictionary& parameters) ORTHANC_OVERRIDE
    {
      std::unique_ptr<IResult> result(Execute(statement, parameters));
    }
      
  public:
    explicit OdbcImplicitTransaction(OdbcDatabase& db) :
      db_(db)
    {
      SetAutoCommitTransaction(db_.GetHandle(), true);
    }

    virtual bool DoesTableExist(const std::string& name) ORTHANC_OVERRIDE
    {
      return db_.DoesTableExist(name.c_str());
    }

    virtual bool DoesIndexExist(const std::string& name) ORTHANC_OVERRIDE
    {
      return false;
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
    
    
  class OdbcDatabase::OdbcExplicitTransaction : public ITransaction
  {
  private:
    OdbcDatabase&  db_;
    bool           isOpen_;

    void EndTransaction(SQLSMALLINT completionType)
    {
      if (!isOpen_)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls, "Transaction is already finalized");
      }
      else if (SQL_SUCCEEDED(SQLEndTran(SQL_HANDLE_DBC, db_.GetHandle(), completionType)))
      {
        isOpen_ = false;
      }
      else
      {
        SQLCHAR stateBuf[SQL_SQLSTATE_SIZE + 1];
        SQLSMALLINT stateLength = 0;
      
        const SQLSMALLINT recNum = 1;
        
        if (SQL_SUCCEEDED(SQLGetDiagField(SQL_HANDLE_DBC, db_.GetHandle(),
                                          recNum, SQL_DIAG_SQLSTATE, &stateBuf, sizeof(stateBuf), &stateLength)))
        {
          const std::string state(reinterpret_cast<const char*>(stateBuf));

          if (state == "40001")
          {
#if ORTHANC_PLUGINS_VERSION_IS_ABOVE(1, 9, 2)
            throw Orthanc::OrthancException(Orthanc::ErrorCode_DatabaseCannotSerialize);
#else
            throw Orthanc::OrthancException(Orthanc::ErrorCode_Database, "Collision between multiple writers");
#endif
          }
        }
        
        switch (completionType)
        {
          case SQL_COMMIT:
            throw Orthanc::OrthancException(Orthanc::ErrorCode_Database, "Cannot commit transaction");

          case SQL_ROLLBACK:
            throw Orthanc::OrthancException(Orthanc::ErrorCode_Database, "Cannot rollback transaction");

          default:
            throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
        }
      }
    }
      
  public:
    explicit OdbcExplicitTransaction(OdbcDatabase& db) :
      db_(db),
      isOpen_(true)
    {
      SetAutoCommitTransaction(db_.GetHandle(), false);
    }

    virtual ~OdbcExplicitTransaction()
    {
      if (isOpen_)
      {
        LOG(INFO) << "An active ODBC transaction was dismissed";
        if (!SQL_SUCCEEDED(SQLEndTran(SQL_HANDLE_DBC, db_.GetHandle(), SQL_ROLLBACK)))
        {
          LOG(ERROR) << "Cannot rollback transaction";
        }
      }
    }

    virtual bool IsImplicit() const ORTHANC_OVERRIDE
    {
      return false;
    }

    virtual void Commit() ORTHANC_OVERRIDE
    {
      EndTransaction(SQL_COMMIT);
    }

    virtual void Rollback() ORTHANC_OVERRIDE
    {
      EndTransaction(SQL_ROLLBACK);
    }

    virtual bool DoesTableExist(const std::string& name) ORTHANC_OVERRIDE
    {
      return db_.DoesTableExist(name.c_str());
    }

    virtual bool DoesIndexExist(const std::string& name) ORTHANC_OVERRIDE
    {
      return false;  // note implemented yet
    }

    virtual bool DoesTriggerExist(const std::string& name) ORTHANC_OVERRIDE
    {
      return false;
    }

    virtual void ExecuteMultiLines(const std::string& query) ORTHANC_OVERRIDE
    {
      db_.ExecuteMultiLines(query);
    }

    virtual IResult* Execute(IPrecompiledStatement& statement,
                             const Dictionary& parameters) ORTHANC_OVERRIDE
    {
      return dynamic_cast<OdbcPreparedStatement&>(statement).Execute(parameters);
    }

    virtual void ExecuteWithoutResult(IPrecompiledStatement& statement,
                                      const Dictionary& parameters) ORTHANC_OVERRIDE
    {
      std::unique_ptr<IResult> result(Execute(statement, parameters));
    }
  };


  static bool ParseThreePartsVersion(unsigned int& majorVersion,
                                     const std::string& version)
  {
    std::vector<std::string> tokens;
    Orthanc::Toolbox::TokenizeString(tokens, version, '.');

    try
    {
      if (tokens.size() == 3u)
      {
        int tmp = boost::lexical_cast<int>(tokens[0]);
        if (tmp >= 0)
        {
          majorVersion = static_cast<unsigned int>(tmp);
          return true;
        }
      }
    }
    catch (boost::bad_lexical_cast&)
    {
    }

    return false;
  }
  
    
  OdbcDatabase::OdbcDatabase(OdbcEnvironment& environment,
                             const std::string& connectionString) :
    dbmsMajorVersion_(0)
  {
    LOG(INFO) << "Creating an ODBC connection: " << connectionString;
      
    /* Allocate a connection handle */
    if (!SQL_SUCCEEDED(SQLAllocHandle(SQL_HANDLE_DBC, environment.GetHandle(), &handle_)))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_DatabaseUnavailable,
                                      "Cannot create ODBC connection");
    }

    /* Connect to the DSN mydsn */
    SQLCHAR* tmp = const_cast<SQLCHAR*>(reinterpret_cast<const SQLCHAR*>(connectionString.c_str()));
    SQLCHAR outBuffer[2048];
    SQLSMALLINT outSize = 0;

    bool success = true;
      
    if (SQL_SUCCEEDED(SQLDriverConnect(handle_, NULL, tmp, SQL_NTS /* null-terminated string */,
                                       outBuffer, sizeof(outBuffer), &outSize, SQL_DRIVER_COMPLETE)))
    {
      LOG(INFO) << "Returned connection string: " << outBuffer;        
    }
    else
    {
      success = false;
    }

    if (!SQL_SUCCEEDED(SQLSetConnectAttr(handle_, SQL_ATTR_TXN_ISOLATION, (SQLPOINTER) SQL_TXN_SERIALIZABLE, SQL_NTS)))
    {
      /**
       * Switch to the "serializable" isolation level that is expected
       * by Orthanc. This is already the default for MySQL and MSSQL,
       * but is needed for PostgreSQL.
       * https://docs.microsoft.com/en-us/sql/odbc/reference/develop-app/transaction-isolation-levels
       **/
      success = false;
    }

    SQLCHAR versionBuffer[2048];
    SQLSMALLINT versionSize;

    if (success &&
        SQL_SUCCEEDED(SQLGetInfo(handle_, SQL_DBMS_NAME, outBuffer, sizeof(outBuffer) - 1, &outSize)) &&
        SQL_SUCCEEDED(SQLGetInfo(handle_, SQL_DBMS_VER, versionBuffer, sizeof(versionBuffer) - 1, &versionSize)))
    {
      std::string dbms(reinterpret_cast<const char*>(outBuffer), outSize);
      std::string version(reinterpret_cast<const char*>(versionBuffer), versionSize);

      LOG(WARNING) << "DBMS Name: " << dbms;
      LOG(WARNING) << "DBMS Version: " << version;
        
      if (dbms == "PostgreSQL")
      {
        dialect_ = Dialect_PostgreSQL;
      }
      else if (dbms == "SQLite")
      {
        dialect_ = Dialect_SQLite;
        ExecuteMultiLines("PRAGMA FOREIGN_KEYS=ON");  // Necessary for cascaded delete to work
        ExecuteMultiLines("PRAGMA ENCODING=\"UTF-8\"");

        // The following lines speed up SQLite
        
        /*ExecuteMultiLines("PRAGMA SYNCHRONOUS=NORMAL;");
          ExecuteMultiLines("PRAGMA JOURNAL_MODE=WAL;");
          ExecuteMultiLines("PRAGMA LOCKING_MODE=EXCLUSIVE;");
          ExecuteMultiLines("PRAGMA WAL_AUTOCHECKPOINT=1000;");*/
      }
      else if (dbms == "MySQL")
      {
        dialect_ = Dialect_MySQL;

        if (!ParseThreePartsVersion(dbmsMajorVersion_, version))
        {
          SQLFreeHandle(SQL_HANDLE_DBC, handle_);
          throw Orthanc::OrthancException(Orthanc::ErrorCode_Database, "Cannot parse the version of MySQL: " + version);
        }
      }
      else if (dbms == "Microsoft SQL Server")
      {
        dialect_ = Dialect_MSSQL;

        if (!ParseThreePartsVersion(dbmsMajorVersion_, version))
        {
          SQLFreeHandle(SQL_HANDLE_DBC, handle_);
          throw Orthanc::OrthancException(Orthanc::ErrorCode_Database, "Cannot parse the version of SQL Server: " + version);
        }
      }
      else
      {
        SQLFreeHandle(SQL_HANDLE_DBC, handle_);
        throw Orthanc::OrthancException(Orthanc::ErrorCode_Database, "Unknown SQL dialect for DBMS: " + dbms);
      }
    }
    else
    {
      success = false;
    }

    if (!success)
    {
      std::string error = FormatError();
      SQLFreeHandle(SQL_HANDLE_DBC, handle_); // Cannot call FormatError() below this point
        
      throw Orthanc::OrthancException(Orthanc::ErrorCode_DatabaseUnavailable, "Error in SQLDriverConnect():\n" + error);
    }
  }

    
  OdbcDatabase::~OdbcDatabase()
  {
    LOG(INFO) << "Destructing an ODBC connection";
      
    if (!SQL_SUCCEEDED(SQLDisconnect(handle_)))
    {
      LOG(ERROR) << "Cannot disconnect from driver";
    }
      
    if (!SQL_SUCCEEDED(SQLFreeHandle(SQL_HANDLE_DBC, handle_)))
    {
      LOG(ERROR) << "Cannot destruct the ODBC connection";
    }
  }


  std::string OdbcDatabase::FormatError()
  {
    return OdbcEnvironment::FormatError(handle_, SQL_HANDLE_DBC);
  }


  void OdbcDatabase::ListTables(std::set<std::string>& target)
  {
    target.clear();

    OdbcStatement statement(GetHandle());

    if (SQL_SUCCEEDED(SQLTables(statement.GetHandle(), NULL, 0, NULL, 0, NULL, 0,
                                const_cast<SQLCHAR*>(reinterpret_cast<const SQLCHAR*>("'TABLE'")), SQL_NTS)))
    {
      OdbcResult result(statement, dialect_);

      while (!result.IsDone())
      {
        if (result.GetFieldsCount() < 5)
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_Database, "Invalid result for SQLTables()");
        }
        else
        {
          if (result.GetField(2).GetType() == ValueType_Utf8String &&
              result.GetField(3).GetType() == ValueType_Utf8String &&
              dynamic_cast<const Utf8StringValue&>(result.GetField(3)).GetContent() == "TABLE")
          {
            std::string name = dynamic_cast<const Utf8StringValue&>(result.GetField(2)).GetContent();
            Orthanc::Toolbox::ToLowerCase(name);
            target.insert(name);
          }
        }

        result.Next();
      }
    }
  }


  bool OdbcDatabase::DoesTableExist(const std::string& name)
  {
    std::set<std::string> tables;
    ListTables(tables);
    return (tables.find(name) != tables.end());
  }

  
  void OdbcDatabase::ExecuteMultiLines(const std::string& query)
  {
    OdbcStatement statement(GetHandle());

    std::vector<std::string> lines;
    Orthanc::Toolbox::TokenizeString(lines, query, ';');
      
    for (size_t i = 0; i < lines.size(); i++)
    {
      std::string line = Orthanc::Toolbox::StripSpaces(lines[i]);
      if (!line.empty())
      {
        LOG(INFO) << "Running ODBC SQL: " << line;
        SQLCHAR* tmp = const_cast<SQLCHAR*>(reinterpret_cast<const SQLCHAR*>(line.c_str()));

        SQLRETURN code = SQLExecDirect(statement.GetHandle(), tmp, SQL_NTS);

        if (code != SQL_NO_DATA &&
            code != SQL_SUCCESS &&
            code != SQL_SUCCESS_WITH_INFO)
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_Database,
                                          "Cannot execute multi-line SQL:\n" + statement.FormatError());
        }
      }
    }
  }


  IPrecompiledStatement* OdbcDatabase::Compile(const Query& query)
  {
    return new OdbcPreparedStatement(GetHandle(), GetDialect(), query);
  }

    
  ITransaction* OdbcDatabase::CreateTransaction(TransactionType type)
  {
    /**
     * In ODBC, there is no "START TRANSACTION". A transaction is
     * automatically created with each connection, and the "READ
     * ONLY" status can only be set at the statement level
     * (cf. SQL_CONCUR_READ_ONLY). One can only control the
     * autocommit: https://stackoverflow.com/a/35351267/881731
     **/
    switch (type)
    {
      case TransactionType_Implicit:
        return new OdbcImplicitTransaction(*this);
          
      case TransactionType_ReadWrite:
      case TransactionType_ReadOnly:
        return new OdbcExplicitTransaction(*this);
          
      default:
        throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
  }


  unsigned int OdbcDatabase::GetDbmsMajorVersion() const
  {
    return dbmsMajorVersion_;
  }    


  IDatabaseFactory* OdbcDatabase::CreateDatabaseFactory(unsigned int maxConnectionRetries,
                                                        unsigned int connectionRetryInterval,
                                                        const std::string& connectionString,
                                                        bool checkEncodings)
  {
    class Factory : public RetryDatabaseFactory
    {
    private:
      OdbcEnvironment environment_;
      std::string     connectionString_;
      bool            checkEncodings_;

      bool LookupConnectionOption(std::string& value,
                                  const std::string& option) const
      {
        std::vector<std::string> tokens;
        Orthanc::Toolbox::TokenizeString(tokens, connectionString_, ';');

        for (size_t i = 0; i < tokens.size(); i++)
        {
          if (boost::starts_with(tokens[i], option + "="))
          {
            value = tokens[i];
            return true;
          }
        }

        return false;
      }

      
      void CheckMSSQLEncodings(const OdbcDatabase& db)
      {
        // https://en.wikipedia.org/wiki/History_of_Microsoft_SQL_Server
        if (db.GetDbmsMajorVersion() <= 14)
        {
          // Microsoft SQL Server up to 2017

          std::string value;
          if (LookupConnectionOption(value, "AutoTranslate"))
          {
            if (value != "AutoTranslate=no")
            {
              LOG(WARNING) << "For UTF-8 to work properly, it is strongly advised to set \"AutoTranslate=no\" in the "
                           << "ODBC connection string when connecting to Microsoft SQL Server with version <= 2017";
            }
          }
          else
          {
            throw Orthanc::OrthancException(Orthanc::ErrorCode_Database,
                                            "Your Microsoft SQL Server has version <= 2017, and thus doesn't support UTF-8; "
                                            "Please upgrade or add \"AutoTranslate=no\" to your ODBC connection string");
          }
        }
        else
        {
          std::string value;
          if (LookupConnectionOption(value, "AutoTranslate") &&
              value != "AutoTranslate=yes")
          {
            throw Orthanc::OrthancException(Orthanc::ErrorCode_Database,
                                            "Your Microsoft SQL Server has version >= 2019, and thus fully supports UTF-8; "
                                            "Please set \"AutoTranslate=yes\" in your ODBC connection string");
          }
        }
      }


      void CheckMySQLEncodings(const OdbcDatabase& db)
      {
        // https://dev.mysql.com/doc/connector-odbc/en/connector-odbc-configuration-connection-parameters.html

        std::string value;
        if (LookupConnectionOption(value, "charset"))
        {
          if (value != "charset=utf8")
          {
            throw Orthanc::OrthancException(Orthanc::ErrorCode_Database,
                                            "For compatibility with UTF-8 in Orthanc, your connection string to MySQL "
                                            "must *not* set the \"charset\" option to another value than \"utf8\"");
          }
        }
        else if (db.GetDbmsMajorVersion() < 8)
        {
          // MySQL up to 5.7
          LOG(WARNING) << "It is advised to set the \"charset=utf8\" option in your connection string if using MySQL <= 5.7";
        }
        else
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_Database,
                                          "For compatibility with UTF-8 in Orthanc, your connection string to MySQL >= 8.0 "
                                          "*must* set the \"charset=utf8\" in your connection string");
        }
      }
      

    protected:
      IDatabase* TryOpen()
      {
        std::unique_ptr<OdbcDatabase> db(new OdbcDatabase(environment_, connectionString_));

        if (checkEncodings_)
        {
          switch (db->GetDialect())
          {
            case Dialect_MSSQL:
              CheckMSSQLEncodings(*db);
              break;

            case Dialect_MySQL:
              CheckMySQLEncodings(*db);
              break;

            case Dialect_SQLite:
            case Dialect_PostgreSQL:
              // Nothing specific to be checked wrt. encodings
              break;

            default:
              throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
          }
        }

        if (db->GetDbmsMajorVersion() >= 15)
        {
          /**
           * SQL Server 2019 introduces support for UTF-8. Note that
           * "ALTER" cannot be run inside a transaction, and must be
           * done *before* the creation of the tables.
           * https://docs.microsoft.com/en-US/sql/relational-databases/collations/collation-and-unicode-support#utf8
           *
           * Furthermore, this call must be done by both
           * "odbc-index" and "odbc-storage" plugins, because
           * altering collation is an operation that requires
           * exclusive lock: If "odbc-storage" is the first plugin
           * to be loaded and doesn't set the UTF-8 collation,
           * "odbc-index" cannot start because it doesn't have
           * exclusive access.
           **/
          db->ExecuteMultiLines("IF 'Latin1_General_100_CI_AS_SC_UTF8' != (SELECT CONVERT (varchar(256), DATABASEPROPERTYEX(DB_NAME(),'collation'))) ALTER DATABASE CURRENT COLLATE LATIN1_GENERAL_100_CI_AS_SC_UTF8");
        }
        
        return db.release();
      }
      
    public:
      Factory(unsigned int maxConnectionRetries,
              unsigned int connectionRetryInterval,
              const std::string& connectionString,
              bool checkEncodings) :
        RetryDatabaseFactory(maxConnectionRetries, connectionRetryInterval),
        connectionString_(connectionString),
        checkEncodings_(checkEncodings)
      {
      }
    };

    return new Factory(maxConnectionRetries, connectionRetryInterval, connectionString, checkEncodings);
  }
}
