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


#include "../../Framework/SQLite/SQLiteDatabase.h"
#include "../Plugins/SQLiteIndex.h"

#include <Compatibility.h>  // For std::unique_ptr<>
#include <Logging.h>
#include <SystemToolbox.h>

#include <gtest/gtest.h>


#include "../../Framework/Plugins/IndexUnitTests.h"


TEST(SQLiteIndex, Lock)
{
  std::list<OrthancDatabases::IdentifierTag> identifierTags;
  
  {
    // No locking if using memory backend
    OrthancDatabases::SQLiteIndex db1(NULL);
    std::unique_ptr<OrthancDatabases::DatabaseManager> manager1(OrthancDatabases::IndexBackend::CreateSingleDatabaseManager(db1, false, identifierTags));

    OrthancDatabases::SQLiteIndex db2(NULL);
    std::unique_ptr<OrthancDatabases::DatabaseManager> manager2(OrthancDatabases::IndexBackend::CreateSingleDatabaseManager(db2, false, identifierTags));
  }

  Orthanc::SystemToolbox::RemoveFile("index.db");

  {
    OrthancDatabases::SQLiteIndex db1(NULL, "index.db");
    std::unique_ptr<OrthancDatabases::DatabaseManager> manager1(OrthancDatabases::IndexBackend::CreateSingleDatabaseManager(db1, false, identifierTags));

    OrthancDatabases::SQLiteIndex db2(NULL, "index.db");
    ASSERT_THROW(OrthancDatabases::IndexBackend::CreateSingleDatabaseManager(db2, false, identifierTags), Orthanc::OrthancException);
  }

  {
    OrthancDatabases::SQLiteIndex db3(NULL, "index.db");
    std::unique_ptr<OrthancDatabases::DatabaseManager> manager3(OrthancDatabases::IndexBackend::CreateSingleDatabaseManager(db3, false, identifierTags));
  }
}


TEST(SQLite, ImplicitTransaction)
{
  OrthancDatabases::SQLiteDatabase db;
  db.OpenInMemory();

  ASSERT_FALSE(db.GetObject().DoesTableExist("test"));
  ASSERT_FALSE(db.GetObject().DoesTableExist("test2"));

  {
    std::unique_ptr<OrthancDatabases::ITransaction> t(db.CreateTransaction(OrthancDatabases::TransactionType_ReadWrite));
    ASSERT_FALSE(t->IsImplicit());
  }

  {
    OrthancDatabases::Query query("CREATE TABLE test(id INT)", false);
    std::unique_ptr<OrthancDatabases::IPrecompiledStatement> s(db.Compile(query));
    
    std::unique_ptr<OrthancDatabases::ITransaction> t(db.CreateTransaction(OrthancDatabases::TransactionType_Implicit));
    ASSERT_TRUE(t->IsImplicit());
    ASSERT_THROW(t->Commit(), Orthanc::OrthancException);
    ASSERT_THROW(t->Rollback(), Orthanc::OrthancException);

    OrthancDatabases::Dictionary args;
    t->ExecuteWithoutResult(*s, args);
    ASSERT_THROW(t->Rollback(), Orthanc::OrthancException);
    t->Commit();

    ASSERT_THROW(t->Commit(), Orthanc::OrthancException);
  }

  {
    // An implicit transaction does not need to be explicitely committed
    OrthancDatabases::Query query("CREATE TABLE test2(id INT)", false);
    std::unique_ptr<OrthancDatabases::IPrecompiledStatement> s(db.Compile(query));
    
    std::unique_ptr<OrthancDatabases::ITransaction> t(db.CreateTransaction(OrthancDatabases::TransactionType_Implicit));

    OrthancDatabases::Dictionary args;
    t->ExecuteWithoutResult(*s, args);
  }

  ASSERT_TRUE(db.GetObject().DoesTableExist("test"));
  ASSERT_TRUE(db.GetObject().DoesTableExist("test2"));
}


int main(int argc, char **argv)
{
  ::testing::InitGoogleTest(&argc, argv);
  Orthanc::Logging::Initialize();
  Orthanc::Logging::EnableInfoLevel(true);
  // Orthanc::Logging::EnableTraceLevel(true);

  int result = RUN_ALL_TESTS();

  Orthanc::Logging::Finalize();

  return result;
}
