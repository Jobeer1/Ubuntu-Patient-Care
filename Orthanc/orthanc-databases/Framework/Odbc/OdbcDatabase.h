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

#include "OdbcEnvironment.h"

#include "../Common/IDatabaseFactory.h"

#include <Compatibility.h>

#include <set>


namespace OrthancDatabases
{
  class OdbcDatabase : public IDatabase
  {
  private:
    class OdbcImplicitTransaction;
    class OdbcExplicitTransaction;
    
    SQLHDBC       handle_;
    Dialect       dialect_;
    unsigned int  dbmsMajorVersion_;

  public:
    OdbcDatabase(OdbcEnvironment& environment,
                 const std::string& connectionString);

    virtual ~OdbcDatabase();

    SQLHDBC GetHandle()
    {
      return handle_;
    }

    std::string FormatError();

    void ListTables(std::set<std::string>& target);

    // "name" must be in lower-case
    bool DoesTableExist(const std::string& name);

    void ExecuteMultiLines(const std::string& query);

    virtual Dialect GetDialect() const ORTHANC_OVERRIDE
    {
      return dialect_;
    }

    virtual IPrecompiledStatement* Compile(const Query& query) ORTHANC_OVERRIDE;

    virtual ITransaction* CreateTransaction(TransactionType type) ORTHANC_OVERRIDE;

    // https://en.wikipedia.org/wiki/History_of_Microsoft_SQL_Server
    unsigned int GetDbmsMajorVersion() const;

    static IDatabaseFactory* CreateDatabaseFactory(unsigned int maxConnectionRetries,
                                                   unsigned int connectionRetryInterval,
                                                   const std::string& connectionString,
                                                   bool checkEncodings);
  };
}
