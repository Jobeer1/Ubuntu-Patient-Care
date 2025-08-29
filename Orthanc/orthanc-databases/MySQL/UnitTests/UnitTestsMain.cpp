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


#include "../Plugins/MySQLIndex.h"
#include "../Plugins/MySQLStorageArea.h"

static OrthancDatabases::MySQLParameters globalParameters_;

#include "../../Framework/Common/Integer64Value.h"
#include "../../Framework/MySQL/MySQLDatabase.h"
#include "../../Framework/MySQL/MySQLResult.h"
#include "../../Framework/MySQL/MySQLStatement.h"
#include "../../Framework/MySQL/MySQLTransaction.h"
#include "../../Framework/Plugins/IndexUnitTests.h"

#include <Compatibility.h>  // For std::unique_ptr<>
#include <HttpClient.h>
#include <Logging.h>
#include <Toolbox.h>

#include <gtest/gtest.h>


TEST(MySQLIndex, Lock)
{
  OrthancDatabases::MySQLParameters noLock = globalParameters_;
  noLock.SetLock(false);

  OrthancDatabases::MySQLParameters lock = globalParameters_;
  lock.SetLock(true);

  OrthancDatabases::MySQLIndex db1(NULL, noLock, false);
  db1.SetClearAll(true);

  std::list<OrthancDatabases::IdentifierTag> identifierTags;
  
  std::unique_ptr<OrthancDatabases::DatabaseManager> manager1(OrthancDatabases::IndexBackend::CreateSingleDatabaseManager(db1, false, identifierTags));

  {
    OrthancDatabases::MySQLIndex db2(NULL, lock, false);
    std::unique_ptr<OrthancDatabases::DatabaseManager> manager2(OrthancDatabases::IndexBackend::CreateSingleDatabaseManager(db2, false, identifierTags));

    OrthancDatabases::MySQLIndex db3(NULL, lock, false);
    ASSERT_THROW(OrthancDatabases::IndexBackend::CreateSingleDatabaseManager(db3, false, identifierTags), Orthanc::OrthancException);

  }

  OrthancDatabases::MySQLIndex db4(NULL, lock, false);
  std::unique_ptr<OrthancDatabases::DatabaseManager> manager4(OrthancDatabases::IndexBackend::CreateSingleDatabaseManager(db4, false, identifierTags));
}


TEST(MySQL, Lock2)
{
  OrthancDatabases::MySQLDatabase::ClearDatabase(globalParameters_);  

  OrthancDatabases::MySQLDatabase db1(globalParameters_);
  db1.Open();

  ASSERT_FALSE(db1.ReleaseAdvisoryLock("mylock")); // lock counter = 0
  ASSERT_TRUE(db1.AcquireAdvisoryLock("mylock"));  // lock counter = 1

  // OK, as this is the same connection
  ASSERT_TRUE(db1.AcquireAdvisoryLock("mylock"));
  // lock counter = 2 if MySQL >= 5.7, or 1 if MySQL < 5.7 (because
  // acquiring a lock releases all the previously-acquired locks)
  
  ASSERT_TRUE(db1.ReleaseAdvisoryLock("mylock"));
  // lock counter = 1 if MySQL >= 5.7, or 0 if MySQL < 5.7

  // Try and release twice the lock
  db1.ReleaseAdvisoryLock("mylock"); // Succeeds iff MySQL >= 5.7

  ASSERT_TRUE(db1.AcquireAdvisoryLock("mylock2"));  // lock counter = 1

  {
    OrthancDatabases::MySQLDatabase db2(globalParameters_);
    db2.Open();

    // The "db1" is still actively locking
    ASSERT_FALSE(db2.AcquireAdvisoryLock("mylock2"));

    // Release the "db1" lock
    ASSERT_TRUE(db1.ReleaseAdvisoryLock("mylock2"));
    ASSERT_FALSE(db1.ReleaseAdvisoryLock("mylock2"));

    // "db2" can now acquire the lock, but not "db1"
    ASSERT_TRUE(db2.AcquireAdvisoryLock("mylock2"));
    ASSERT_FALSE(db1.AcquireAdvisoryLock("mylock2"));
  }

  // "db2" is closed, "db1" can now acquire the lock
  ASSERT_TRUE(db1.AcquireAdvisoryLock("mylock2"));
}



/**
 * WARNING: The following test only succeeds if MySQL >= 5.7. This is
 * because in MySQL < 5.7, acquiring a lock by calling "SELECT
 * GET_LOCK()" releases all the previously acquired locks!
 **/
TEST(MySQL, DISABLED_Lock3)
{
  OrthancDatabases::MySQLDatabase::ClearDatabase(globalParameters_);  

  OrthancDatabases::MySQLDatabase db1(globalParameters_);
  db1.Open();

  ASSERT_TRUE(db1.AcquireAdvisoryLock("mylock1"));  // lock counter = 1
  ASSERT_TRUE(db1.AcquireAdvisoryLock("mylock2"));  // lock counter = 1

  {
    OrthancDatabases::MySQLDatabase db2(globalParameters_);
    db2.Open();

    ASSERT_FALSE(db2.AcquireAdvisoryLock("mylock1"));
  }
}


static int64_t CountFiles(OrthancDatabases::MySQLDatabase& db)
{
  OrthancDatabases::MySQLTransaction transaction(db, OrthancDatabases::TransactionType_ReadOnly);

  int64_t count;
  {
    OrthancDatabases::Query query("SELECT COUNT(*) FROM StorageArea", true);
    OrthancDatabases::MySQLStatement s(db, query);
    OrthancDatabases::MySQLTransaction t(db, OrthancDatabases::TransactionType_ReadOnly);
    OrthancDatabases::Dictionary d;
    std::unique_ptr<OrthancDatabases::IResult> result(s.Execute(t, d));
    count = dynamic_cast<const OrthancDatabases::Integer64Value&>(result->GetField(0)).GetValue();
  }

  transaction.Commit();
  return count;
}


TEST(MySQL, StorageArea)
{
  std::unique_ptr<OrthancDatabases::MySQLDatabase> database(
    OrthancDatabases::MySQLDatabase::CreateDatabaseConnection(globalParameters_));
  
  OrthancDatabases::MySQLStorageArea storageArea(globalParameters_, true /* clear database */);

  {
    std::unique_ptr<OrthancDatabases::StorageBackend::IAccessor> accessor(storageArea.CreateAccessor());
    
    ASSERT_EQ(0, CountFiles(*database));
  
    for (int i = 0; i < 10; i++)
    {
      std::string uuid = boost::lexical_cast<std::string>(i);
      std::string value = "Value " + boost::lexical_cast<std::string>(i * 2);
      accessor->Create(uuid, value.c_str(), value.size(), OrthancPluginContentType_Unknown);
    }

    std::string buffer;
    ASSERT_THROW(OrthancDatabases::StorageBackend::ReadWholeToString(
                   buffer, *accessor, "nope", OrthancPluginContentType_Unknown), 
                 Orthanc::OrthancException);
  
    ASSERT_EQ(10, CountFiles(*database));
    accessor->Remove("5", OrthancPluginContentType_Unknown);

    ASSERT_EQ(9, CountFiles(*database));

    for (int i = 0; i < 10; i++)
    {
      std::string uuid = boost::lexical_cast<std::string>(i);
      std::string expected = "Value " + boost::lexical_cast<std::string>(i * 2);

      if (i == 5)
      {
        ASSERT_THROW(OrthancDatabases::StorageBackend::ReadWholeToString(
                       buffer, *accessor, uuid, OrthancPluginContentType_Unknown), 
                     Orthanc::OrthancException);
      }
      else
      {
        OrthancDatabases::StorageBackend::ReadWholeToString(buffer, *accessor, uuid, OrthancPluginContentType_Unknown);
        ASSERT_EQ(expected, buffer);
      }
    }

    for (int i = 0; i < 10; i++)
    {
      accessor->Remove(boost::lexical_cast<std::string>(i), OrthancPluginContentType_Unknown);
    }

    ASSERT_EQ(0, CountFiles(*database));
  }
}


TEST(MySQL, StorageReadRange)
{
  std::unique_ptr<OrthancDatabases::MySQLDatabase> database(
    OrthancDatabases::MySQLDatabase::CreateDatabaseConnection(globalParameters_));
  
  OrthancDatabases::MySQLStorageArea storageArea(globalParameters_, true /* clear database */);

  {
    std::unique_ptr<OrthancDatabases::StorageBackend::IAccessor> accessor(storageArea.CreateAccessor());
    ASSERT_EQ(0, CountFiles(*database));  
    accessor->Create("uuid", "abcd\0\1\2\3\4\5", 10, OrthancPluginContentType_Unknown);
    ASSERT_EQ(1u, CountFiles(*database));  
  }

  {
    std::unique_ptr<OrthancDatabases::StorageBackend::IAccessor> accessor(storageArea.CreateAccessor());
    ASSERT_EQ(1u, CountFiles(*database));

    std::string s;
    OrthancDatabases::StorageBackend::ReadWholeToString(s, *accessor, "uuid", OrthancPluginContentType_Unknown);
    ASSERT_EQ(10u, s.size());
    ASSERT_EQ('a', s[0]);
    ASSERT_EQ('d', s[3]);
    ASSERT_EQ('\0', s[4]);
    ASSERT_EQ('\5', s[9]);

    OrthancDatabases::StorageBackend::ReadRangeToString(s, *accessor, "uuid", OrthancPluginContentType_Unknown, 0, 0);
    ASSERT_TRUE(s.empty());

    OrthancDatabases::StorageBackend::ReadRangeToString(s, *accessor, "uuid", OrthancPluginContentType_Unknown, 0, 1);
    ASSERT_EQ(1u, s.size());
    ASSERT_EQ('a', s[0]);

    OrthancDatabases::StorageBackend::ReadRangeToString(s, *accessor, "uuid", OrthancPluginContentType_Unknown, 4, 1);
    ASSERT_EQ(1u, s.size());
    ASSERT_EQ('\0', s[0]);

    OrthancDatabases::StorageBackend::ReadRangeToString(s, *accessor, "uuid", OrthancPluginContentType_Unknown, 9, 1);
    ASSERT_EQ(1u, s.size());
    ASSERT_EQ('\5', s[0]);

    OrthancDatabases::StorageBackend::ReadRangeToString(s, *accessor, "uuid", OrthancPluginContentType_Unknown, 10, 0);
    ASSERT_TRUE(s.empty());

    // Cannot read non-empty range after the end of the string
    ASSERT_THROW(OrthancDatabases::StorageBackend::ReadRangeToString(
                   s, *accessor, "uuid", OrthancPluginContentType_Unknown, 10, 1), Orthanc::OrthancException);

    OrthancDatabases::StorageBackend::ReadRangeToString(s, *accessor, "uuid", OrthancPluginContentType_Unknown, 0, 4);
    ASSERT_EQ(4u, s.size());
    ASSERT_EQ('a', s[0]);
    ASSERT_EQ('b', s[1]);
    ASSERT_EQ('c', s[2]);
    ASSERT_EQ('d', s[3]);

    OrthancDatabases::StorageBackend::ReadRangeToString(s, *accessor, "uuid", OrthancPluginContentType_Unknown, 4, 6);
    ASSERT_EQ(6u, s.size());
    ASSERT_EQ('\0', s[0]);
    ASSERT_EQ('\1', s[1]);
    ASSERT_EQ('\2', s[2]);
    ASSERT_EQ('\3', s[3]);
    ASSERT_EQ('\4', s[4]);
    ASSERT_EQ('\5', s[5]);

    ASSERT_THROW(OrthancDatabases::StorageBackend::ReadRangeToString(
                   s, *accessor, "uuid", OrthancPluginContentType_Unknown, 4, 7), Orthanc::OrthancException);
  }
}


TEST(MySQL, ImplicitTransaction)
{
  OrthancDatabases::MySQLDatabase::ClearDatabase(globalParameters_);  
  OrthancDatabases::MySQLDatabase db(globalParameters_);
  db.Open();

  {
    OrthancDatabases::MySQLTransaction t(db, OrthancDatabases::TransactionType_ReadOnly);
    ASSERT_FALSE(db.DoesTableExist(t, "test"));
    ASSERT_FALSE(db.DoesTableExist(t, "test2"));
  }

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

  {
    OrthancDatabases::MySQLTransaction t(db, OrthancDatabases::TransactionType_ReadOnly);
    ASSERT_TRUE(db.DoesTableExist(t, "test"));
    ASSERT_TRUE(db.DoesTableExist(t, "test2"));
  }
}


int main(int argc, char **argv)
{
  if (argc < 5)
  {
    std::cerr
#if !defined(_WIN32)
      << "Usage (UNIX socket):      " << argv[0] << " <socket> <username> <password> <database>"
      << std::endl
#endif
      << "Usage (TCP connection):   " << argv[0] << " <host> <port> <username> <password> <database>"
      << std::endl << std::endl
#if !defined(_WIN32)
      << "Example (UNIX socket):    " << argv[0] << " /var/run/mysqld/mysqld.sock root root orthanctest"
      << std::endl
#endif
      << "Example (TCP connection): " << argv[0] << " localhost 3306 root root orthanctest"
      << std::endl << std::endl;
    return -1;
  }

  std::vector<std::string> args;
  for (int i = 1; i < argc; i++)
  {
    // Ignore arguments beginning with "-" to allow passing arguments
    // to Google Test such as "--gtest_filter="
    if (argv[i] != NULL &&
        argv[i][0] != '-')
    {
      args.push_back(std::string(argv[i]));
    }
  }
  
  ::testing::InitGoogleTest(&argc, argv);
  Orthanc::Logging::Initialize();
  Orthanc::Logging::EnableInfoLevel(true);
  // Orthanc::Logging::EnableTraceLevel(true);
  Orthanc::Toolbox::InitializeOpenSsl();
  Orthanc::HttpClient::GlobalInitialize();
  
  if (args.size() == 4)
  {
    // UNIX socket flavor
    globalParameters_.SetHost("");
    globalParameters_.SetUnixSocket(args[0]);
    globalParameters_.SetUsername(args[1]);
    globalParameters_.SetPassword(args[2]);
    globalParameters_.SetDatabase(args[3]);
  }
  else if (args.size() == 5)
  {
    // TCP connection flavor
    globalParameters_.SetHost(args[0]);
    globalParameters_.SetPort(boost::lexical_cast<unsigned int>(args[1]));
    globalParameters_.SetUsername(args[2]);
    globalParameters_.SetPassword(args[3]);
    globalParameters_.SetDatabase(args[4]);

    // Force the use of TCP on localhost, even if UNIX sockets are available
    globalParameters_.SetUnixSocket("");
  }
  else
  {
    LOG(ERROR) << "Bad number of arguments";
    return -1;
  }

  Json::Value config;
  globalParameters_.Format(config);
  std::cout << "Parameters of the MySQL connection: " << std::endl
            << config.toStyledString() << std::endl;

  int result = RUN_ALL_TESTS();

  Orthanc::HttpClient::GlobalFinalize();
  Orthanc::Toolbox::FinalizeOpenSsl();
  OrthancDatabases::MySQLDatabase::GlobalFinalization();
  Orthanc::Logging::Finalize();

  return result;
}
