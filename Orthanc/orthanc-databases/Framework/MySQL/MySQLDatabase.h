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


#pragma once

#if ORTHANC_ENABLE_MYSQL != 1
#  error MySQL support must be enabled to use this file
#endif

#include "../Common/IDatabaseFactory.h"
#include "MySQLParameters.h"

#include <mysql.h>

namespace OrthancDatabases
{
  class MySQLTransaction;
  
  class MySQLDatabase : public IDatabase
  {
  private:
    class Factory;
    
    MySQLParameters  parameters_;
    MYSQL           *mysql_;

    void OpenInternal(const char* database);
    
    void Close();

    bool RunAdvisoryLockStatement(Query& query,
                                  const std::string& lock);

  public:
    explicit MySQLDatabase(const MySQLParameters& parameters);

    virtual ~MySQLDatabase();

    void LogError();

    void CheckErrorCode(int code);

    void ThrowException();

    MYSQL* GetObject();

    void Open();

    void OpenRoot()
    {
      OpenInternal(NULL);
    }

    static void ClearDatabase(const MySQLParameters& parameters);

    bool LookupGlobalStringVariable(std::string& value,
                                    const std::string& variable);
    
    bool LookupGlobalIntegerVariable(int64_t& value,
                                     const std::string& variable);

    bool AcquireAdvisoryLock(const std::string& lock);

    bool ReleaseAdvisoryLock(const std::string& lock);

    void AdvisoryLock(const std::string& lock);

    void ExecuteMultiLines(const std::string& sql,
                           bool arobaseSeparator);

    bool DoesTableExist(MySQLTransaction& transaction,
                        const std::string& name);

    bool DoesDatabaseExist(MySQLTransaction& transaction,
                           const std::string& name);

    bool DoesTriggerExist(MySQLTransaction& transaction,
                          const std::string& name);

    virtual Dialect GetDialect() const ORTHANC_OVERRIDE
    {
      return Dialect_MySQL;
    }

    virtual IPrecompiledStatement* Compile(const Query& query) ORTHANC_OVERRIDE;

    virtual ITransaction* CreateTransaction(TransactionType type) ORTHANC_OVERRIDE;

    static void GlobalFinalization();

    static bool IsValidDatabaseIdentifier(const std::string& s);

    class TransientAdvisoryLock
    {
    private:
      MySQLDatabase&  database_;
      std::string     lock_;

    public:
      TransientAdvisoryLock(MySQLDatabase&  database,
                            const std::string& lock);

      ~TransientAdvisoryLock();
    };

    static IDatabaseFactory* CreateDatabaseFactory(const MySQLParameters& parameters);

    static MySQLDatabase* CreateDatabaseConnection(const MySQLParameters& parameters);
  };
}
