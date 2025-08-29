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


#include "../Plugins/PostgreSQLIndex.h"

#include <Logging.h>
#include <Toolbox.h>
#include <gtest/gtest.h>

OrthancDatabases::PostgreSQLParameters  globalParameters_;

#include "../../Framework/Plugins/IndexUnitTests.h"
#include "../../Framework/PostgreSQL/PostgreSQLDatabase.h"


#if ORTHANC_POSTGRESQL_STATIC == 1
#  include <c.h>  // PostgreSQL includes

TEST(PostgreSQL, Version)
{
  ASSERT_STREQ("13.1", PG_VERSION);
}
#endif


TEST(PostgreSQLParameters, Basic)
{
  OrthancDatabases::PostgreSQLParameters p;
  p.SetDatabase("world");

  ASSERT_EQ("postgresql://localhost:5432/world", p.GetConnectionUri());

  p.ResetDatabase();
  ASSERT_EQ("postgresql://localhost:5432/", p.GetConnectionUri());

  p.SetDatabase("hello");
  ASSERT_EQ("postgresql://localhost:5432/hello", p.GetConnectionUri());

  p.SetHost("server");
  ASSERT_EQ("postgresql://server:5432/hello", p.GetConnectionUri());

  p.SetPortNumber(1234);
  ASSERT_EQ("postgresql://server:1234/hello", p.GetConnectionUri());

  p.SetPortNumber(5432);
  ASSERT_EQ("postgresql://server:5432/hello", p.GetConnectionUri());

  p.SetUsername("user");
  p.SetPassword("pass");
  ASSERT_EQ("postgresql://user:pass@server:5432/hello", p.GetConnectionUri());

  p.SetPassword("");
  ASSERT_EQ("postgresql://user@server:5432/hello", p.GetConnectionUri());

  p.SetUsername("");
  p.SetPassword("pass");
  ASSERT_EQ("postgresql://server:5432/hello", p.GetConnectionUri());

  p.SetUsername("");
  p.SetPassword("");
  ASSERT_EQ("postgresql://server:5432/hello", p.GetConnectionUri());

  p.SetConnectionUri("hello://world");
  ASSERT_EQ("hello://world", p.GetConnectionUri());
}


TEST(PostgreSQLIndex, Lock)
{
  OrthancDatabases::PostgreSQLParameters noLock = globalParameters_;
  noLock.SetLock(false);

  OrthancDatabases::PostgreSQLParameters lock = globalParameters_;
  lock.SetLock(true);

  OrthancDatabases::PostgreSQLIndex db1(NULL, noLock);
  db1.SetClearAll(true);

  std::list<OrthancDatabases::IdentifierTag> identifierTags;
  std::unique_ptr<OrthancDatabases::DatabaseManager> manager1(OrthancDatabases::IndexBackend::CreateSingleDatabaseManager(db1, false, identifierTags));

  {
    OrthancDatabases::PostgreSQLIndex db2(NULL, lock);
    std::unique_ptr<OrthancDatabases::DatabaseManager> manager2(OrthancDatabases::IndexBackend::CreateSingleDatabaseManager(db2, false, identifierTags));

    OrthancDatabases::PostgreSQLIndex db3(NULL, lock);
    ASSERT_THROW(OrthancDatabases::IndexBackend::CreateSingleDatabaseManager(db3, false, identifierTags), Orthanc::OrthancException);
  }

  OrthancDatabases::PostgreSQLIndex db4(NULL, lock);
    std::unique_ptr<OrthancDatabases::DatabaseManager> manager4(OrthancDatabases::IndexBackend::CreateSingleDatabaseManager(db4, false, identifierTags));
}


int main(int argc, char **argv)
{
  if (argc < 6)
  {
    std::cerr << "Usage: " << argv[0] << " <host> <port> <username> <password> <database>"
              << std::endl << std::endl
              << "Example: " << argv[0] << " localhost 5432 postgres postgres orthanctest"
              << std::endl << std::endl;
    return -1;
  }

  globalParameters_.SetHost(argv[1]);
  globalParameters_.SetPortNumber(boost::lexical_cast<uint16_t>(argv[2]));
  globalParameters_.SetUsername(argv[3]);
  globalParameters_.SetPassword(argv[4]);
  globalParameters_.SetDatabase(argv[5]);

  ::testing::InitGoogleTest(&argc, argv);
  Orthanc::Toolbox::InitializeOpenSsl();
  Orthanc::Logging::Initialize();
  Orthanc::Logging::EnableInfoLevel(true);
  //Orthanc::Logging::EnableTraceLevel(true);

  int result = RUN_ALL_TESTS();

  Orthanc::Logging::Finalize();
  Orthanc::Toolbox::FinalizeOpenSsl();

  return result;
}
