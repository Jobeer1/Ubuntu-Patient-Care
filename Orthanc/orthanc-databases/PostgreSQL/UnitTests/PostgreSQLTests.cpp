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


#include <gtest/gtest.h>

#if defined(_WIN32)
// Fix redefinition of symbols on MinGW (these symbols are manually
// defined both by PostgreSQL and Google Test)
#  undef S_IRGRP
#  undef S_IROTH
#  undef S_IRWXG
#  undef S_IRWXO
#  undef S_IWGRP
#  undef S_IWOTH
#  undef S_IXGRP
#  undef S_IXOTH
#endif

#include "../../Framework/Plugins/GlobalProperties.h"
#include "../../Framework/PostgreSQL/PostgreSQLLargeObject.h"
#include "../../Framework/PostgreSQL/PostgreSQLResult.h"
#include "../../Framework/PostgreSQL/PostgreSQLTransaction.h"
#include "../Plugins/PostgreSQLIndex.h"
#include "../Plugins/PostgreSQLStorageArea.h"

#include <Compatibility.h>  // For std::unique_ptr<>
#include <OrthancException.h>

#include <boost/lexical_cast.hpp>

using namespace OrthancDatabases;

extern PostgreSQLParameters  globalParameters_;


static PostgreSQLDatabase* CreateTestDatabase()
{
  std::unique_ptr<PostgreSQLDatabase> pg
    (new PostgreSQLDatabase(globalParameters_));

  pg->Open();
  pg->ClearAll();

  return pg.release();
}


static int64_t CountLargeObjects(PostgreSQLDatabase& db)
{
  PostgreSQLTransaction transaction(db, TransactionType_ReadOnly);

  int64_t count;
  
  {
    // Count the number of large objects in the DB
    PostgreSQLStatement s(db, "SELECT COUNT(*) FROM pg_catalog.pg_largeobject");
    PostgreSQLResult r(s);
    count = r.GetInteger64(0);
  }

  transaction.Commit();
  return count;
}


TEST(PostgreSQL, Basic)
{
  std::unique_ptr<PostgreSQLDatabase> pg(CreateTestDatabase());

  ASSERT_FALSE(pg->DoesTableExist("Test"));
  ASSERT_FALSE(pg->DoesColumnExist("Test", "value"));
  ASSERT_FALSE(pg->DoesTableExist("TEST"));
  ASSERT_FALSE(pg->DoesTableExist("test"));
  pg->ExecuteMultiLines("CREATE TABLE Test(name INTEGER, value BIGINT)");
  ASSERT_TRUE(pg->DoesTableExist("Test"));
  ASSERT_TRUE(pg->DoesTableExist("TEST"));
  ASSERT_TRUE(pg->DoesTableExist("test"));

  ASSERT_TRUE(pg->DoesColumnExist("Test", "Value"));
  ASSERT_TRUE(pg->DoesColumnExist("TEST", "VALUE"));
  ASSERT_TRUE(pg->DoesColumnExist("test", "value"));
  
  PostgreSQLStatement s(*pg, "INSERT INTO Test VALUES ($1,$2)");
  s.DeclareInputInteger(0);
  s.DeclareInputInteger64(1);

  s.BindInteger(0, 43);
  s.BindNull(0);
  s.BindInteger(0, 42);
  s.BindInteger64(1, -4242);
  s.Run();

  s.BindInteger(0, 43);
  s.BindNull(1);
  s.Run();

  s.BindNull(0);
  s.BindInteger64(1, 4444);
  s.Run();

  {
    PostgreSQLStatement t(*pg, "SELECT name, value FROM Test ORDER BY name");
    PostgreSQLResult r(t);

    ASSERT_FALSE(r.IsDone());
    ASSERT_FALSE(r.IsNull(0)); ASSERT_EQ(42, r.GetInteger(0));
    ASSERT_FALSE(r.IsNull(1)); ASSERT_EQ(-4242, r.GetInteger64(1));

    r.Next();
    ASSERT_FALSE(r.IsDone());
    ASSERT_FALSE(r.IsNull(0)); ASSERT_EQ(43, r.GetInteger(0));
    ASSERT_TRUE(r.IsNull(1));

    r.Next();
    ASSERT_FALSE(r.IsDone());
    ASSERT_TRUE(r.IsNull(0));
    ASSERT_FALSE(r.IsNull(1)); ASSERT_EQ(4444, r.GetInteger64(1));

    r.Next();
    ASSERT_TRUE(r.IsDone());
  }

  {
    PostgreSQLStatement t(*pg, "SELECT name, value FROM Test WHERE name=$1");
    t.DeclareInputInteger(0);

    {
      t.BindInteger(0, 42);
      PostgreSQLResult r(t);
      ASSERT_FALSE(r.IsDone());
      ASSERT_FALSE(r.IsNull(0)); ASSERT_EQ(42, r.GetInteger(0));
      ASSERT_FALSE(r.IsNull(1)); ASSERT_EQ(-4242, r.GetInteger64(1));

      r.Next();
      ASSERT_TRUE(r.IsDone());
    }

    {
      t.BindInteger(0, 40);
      PostgreSQLResult r(t);
      ASSERT_TRUE(r.IsDone());
    }
  }
  
}


TEST(PostgreSQL, String)
{
  std::unique_ptr<PostgreSQLDatabase> pg(CreateTestDatabase());

  pg->ExecuteMultiLines("CREATE TABLE Test(name INTEGER, value VARCHAR(40))");

  PostgreSQLStatement s(*pg, "INSERT INTO Test VALUES ($1,$2)");
  s.DeclareInputInteger(0);
  s.DeclareInputString(1);

  s.BindInteger(0, 42);
  s.BindString(1, "Hello");
  s.Run();

  s.BindInteger(0, 43);
  s.BindNull(1);
  s.Run();

  s.BindNull(0);
  s.BindString(1, "");
  s.Run();

  {
    PostgreSQLStatement t(*pg, "SELECT name, value FROM Test ORDER BY name");
    PostgreSQLResult r(t);

    ASSERT_FALSE(r.IsDone());
    ASSERT_FALSE(r.IsNull(0)); ASSERT_EQ(42, r.GetInteger(0));
    ASSERT_FALSE(r.IsNull(1)); ASSERT_EQ("Hello", r.GetString(1));

    r.Next();
    ASSERT_FALSE(r.IsDone());
    ASSERT_FALSE(r.IsNull(0)); ASSERT_EQ(43, r.GetInteger(0));
    ASSERT_TRUE(r.IsNull(1));

    r.Next();
    ASSERT_FALSE(r.IsDone());
    ASSERT_TRUE(r.IsNull(0));
    ASSERT_FALSE(r.IsNull(1)); ASSERT_EQ("", r.GetString(1));

    r.Next();
    ASSERT_TRUE(r.IsDone());
  }
}


TEST(PostgreSQL, Transaction)
{
  std::unique_ptr<PostgreSQLDatabase> pg(CreateTestDatabase());

  pg->ExecuteMultiLines("CREATE TABLE Test(name INTEGER, value INTEGER)");

  {
    PostgreSQLStatement s(*pg, "INSERT INTO Test VALUES ($1,$2)");
    s.DeclareInputInteger(0);
    s.DeclareInputInteger(1);
    s.BindInteger(0, 42);
    s.BindInteger(1, 4242);
    s.Run();

    {
      PostgreSQLTransaction t(*pg, TransactionType_ReadOnly);
      s.BindInteger(0, 0);
      s.BindInteger(1, 1);
      // Failure, as INSERT in a read-only transaction
      ASSERT_THROW(s.Run(), Orthanc::OrthancException);
    }

    {
      PostgreSQLTransaction t(*pg, TransactionType_ReadWrite);
      s.BindInteger(0, 43);
      s.BindInteger(1, 4343);
      s.Run();
      s.BindInteger(0, 44);
      s.BindInteger(1, 4444);
      s.Run();

      PostgreSQLStatement u(*pg, "SELECT COUNT(*) FROM Test");
      PostgreSQLResult r(u);
      ASSERT_EQ(3, r.GetInteger64(0));

      // No commit
    }

    {
      // Implicit transaction
      PostgreSQLStatement u(*pg, "SELECT COUNT(*) FROM Test");
      PostgreSQLResult r(u);
      ASSERT_EQ(1, r.GetInteger64(0));  // Just "1" because of implicit rollback
    }
    
    {
      PostgreSQLTransaction t(*pg, TransactionType_ReadWrite);
      s.BindInteger(0, 43);
      s.BindInteger(1, 4343);
      s.Run();
      s.BindInteger(0, 44);
      s.BindInteger(1, 4444);
      s.Run();

      {
        PostgreSQLStatement u(*pg, "SELECT COUNT(*) FROM Test");
        PostgreSQLResult r(u);
        ASSERT_EQ(3, r.GetInteger64(0));

        t.Commit();
        ASSERT_THROW(t.Rollback(), Orthanc::OrthancException);
        ASSERT_THROW(t.Commit(), Orthanc::OrthancException);
      }
    }

    {
      PostgreSQLTransaction t(*pg, TransactionType_ReadOnly);
      PostgreSQLStatement u(*pg, "SELECT COUNT(*) FROM Test");
      PostgreSQLResult r(u);
      ASSERT_EQ(3, r.GetInteger64(0));
    }
  }
}





TEST(PostgreSQL, LargeObject)
{
  std::unique_ptr<PostgreSQLDatabase> pg(CreateTestDatabase());
  ASSERT_EQ(0, CountLargeObjects(*pg));

  pg->ExecuteMultiLines("CREATE TABLE Test(name VARCHAR, value OID)");

  // Automatically remove the large objects associated with the table
  pg->ExecuteMultiLines("CREATE RULE TestDelete AS ON DELETE TO Test DO SELECT lo_unlink(old.value);");

  {
    PostgreSQLStatement s(*pg, "INSERT INTO Test VALUES ($1,$2)");
    s.DeclareInputString(0);
    s.DeclareInputLargeObject(1);
    
    for (int i = 0; i < 10; i++)
    {
      PostgreSQLTransaction t(*pg, TransactionType_ReadWrite);

      std::string value = "Value " + boost::lexical_cast<std::string>(i * 2);
      PostgreSQLLargeObject obj(*pg, value);

      s.BindString(0, "Index " + boost::lexical_cast<std::string>(i));
      s.BindLargeObject(1, obj);
      s.Run();

      std::string tmp;
      PostgreSQLLargeObject::ReadWhole(tmp, *pg, obj.GetOid());
      ASSERT_EQ(value, tmp);

      t.Commit();
    }
  }


  ASSERT_EQ(10, CountLargeObjects(*pg));

  {
    PostgreSQLTransaction t(*pg, TransactionType_ReadOnly);
    PostgreSQLStatement s(*pg, "SELECT * FROM Test ORDER BY name DESC");
    PostgreSQLResult r(s);

    ASSERT_FALSE(r.IsDone());

    ASSERT_FALSE(r.IsNull(0));
    ASSERT_EQ("Index 9", r.GetString(0));

    std::string data;
    r.GetLargeObjectContent(data, 1);
    ASSERT_EQ("Value 18", data);    

    r.Next();
    ASSERT_FALSE(r.IsDone());

    //ASSERT_TRUE(r.IsString(0));
  }


  {
    PostgreSQLTransaction t(*pg, TransactionType_ReadWrite);
    PostgreSQLStatement s(*pg, "DELETE FROM Test WHERE name='Index 9'");
    s.Run();
    t.Commit();
  }


  {
    // Count the number of items in the DB
    PostgreSQLTransaction t(*pg, TransactionType_ReadOnly);
    PostgreSQLStatement s(*pg, "SELECT COUNT(*) FROM Test");
    PostgreSQLResult r(s);
    ASSERT_EQ(9, r.GetInteger64(0));
  }

  ASSERT_EQ(9, CountLargeObjects(*pg));
}


TEST(PostgreSQL, StorageArea)
{
  std::unique_ptr<PostgreSQLDatabase> database(PostgreSQLDatabase::CreateDatabaseConnection(globalParameters_));
  
  PostgreSQLStorageArea storageArea(globalParameters_, true /* clear database */);

  {
    std::unique_ptr<OrthancDatabases::StorageBackend::IAccessor> accessor(storageArea.CreateAccessor());
    
    ASSERT_EQ(0, CountLargeObjects(*database));
  
    for (int i = 0; i < 10; i++)
    {
      std::string uuid = boost::lexical_cast<std::string>(i);
      std::string value = "Value " + boost::lexical_cast<std::string>(i * 2);
      accessor->Create(uuid, value.c_str(), value.size(), OrthancPluginContentType_Unknown);
    }

    std::string buffer;
    ASSERT_THROW(OrthancDatabases::StorageBackend::ReadWholeToString(buffer, *accessor, "nope", OrthancPluginContentType_Unknown), 
                 Orthanc::OrthancException);
  
    ASSERT_EQ(10, CountLargeObjects(*database));
    accessor->Remove("5", OrthancPluginContentType_Unknown);

    ASSERT_EQ(9, CountLargeObjects(*database));

    for (int i = 0; i < 10; i++)
    {
      std::string uuid = boost::lexical_cast<std::string>(i);
      std::string expected = "Value " + boost::lexical_cast<std::string>(i * 2);

      if (i == 5)
      {
        ASSERT_THROW(OrthancDatabases::StorageBackend::ReadWholeToString(buffer, *accessor, uuid, OrthancPluginContentType_Unknown), 
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

    ASSERT_EQ(0, CountLargeObjects(*database));
  }
}


TEST(PostgreSQL, StorageReadRange)
{
  std::unique_ptr<OrthancDatabases::PostgreSQLDatabase> database(
    OrthancDatabases::PostgreSQLDatabase::CreateDatabaseConnection(globalParameters_));
  
  OrthancDatabases::PostgreSQLStorageArea storageArea(globalParameters_, true /* clear database */);

  {
    std::unique_ptr<OrthancDatabases::StorageBackend::IAccessor> accessor(storageArea.CreateAccessor());
    ASSERT_EQ(0, CountLargeObjects(*database));
    accessor->Create("uuid", "abcd\0\1\2\3\4\5", 10, OrthancPluginContentType_Unknown);
    ASSERT_EQ(1u, CountLargeObjects(*database));
  }

  {
    std::unique_ptr<OrthancDatabases::StorageBackend::IAccessor> accessor(storageArea.CreateAccessor());
    ASSERT_EQ(1u, CountLargeObjects(*database));

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

    // Cannot read non-empty range after the end of the string. NB:
    // The behavior on range (10, 0) is different than in MySQL!
    ASSERT_THROW(OrthancDatabases::StorageBackend::ReadRangeToString(
                   s, *accessor, "uuid", OrthancPluginContentType_Unknown, 10, 0), Orthanc::OrthancException);

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


TEST(PostgreSQL, ImplicitTransaction)
{
  std::unique_ptr<PostgreSQLDatabase> db(CreateTestDatabase());

  ASSERT_FALSE(db->DoesTableExist("test"));
  ASSERT_FALSE(db->DoesTableExist("test2"));

  {
    std::unique_ptr<OrthancDatabases::ITransaction> t(db->CreateTransaction(TransactionType_ReadWrite));
    ASSERT_FALSE(t->IsImplicit());
  }

  {
    Query query("CREATE TABLE test(id INT)", false);
    std::unique_ptr<IPrecompiledStatement> s(db->Compile(query));
    
    std::unique_ptr<ITransaction> t(db->CreateTransaction(TransactionType_Implicit));
    ASSERT_TRUE(t->IsImplicit());
    ASSERT_THROW(t->Commit(), Orthanc::OrthancException);
    ASSERT_THROW(t->Rollback(), Orthanc::OrthancException);

    Dictionary args;
    t->ExecuteWithoutResult(*s, args);
    ASSERT_THROW(t->Rollback(), Orthanc::OrthancException);
    t->Commit();

    ASSERT_THROW(t->Commit(), Orthanc::OrthancException);
  }

  {
    // An implicit transaction does not need to be explicitely committed
    Query query("CREATE TABLE test2(id INT)", false);
    std::unique_ptr<IPrecompiledStatement> s(db->Compile(query));
    
    std::unique_ptr<ITransaction> t(db->CreateTransaction(TransactionType_Implicit));

    Dictionary args;
    t->ExecuteWithoutResult(*s, args);
  }

  ASSERT_TRUE(db->DoesTableExist("test"));
  ASSERT_TRUE(db->DoesTableExist("test2"));
}


#if ORTHANC_PLUGINS_HAS_DATABASE_CONSTRAINT == 1
TEST(PostgreSQLIndex, CreateInstance)
{
  OrthancDatabases::PostgreSQLIndex db(NULL, globalParameters_);
  db.SetClearAll(true);

  std::list<OrthancDatabases::IdentifierTag> tags;
  std::unique_ptr<OrthancDatabases::DatabaseManager> manager(OrthancDatabases::IndexBackend::CreateSingleDatabaseManager(db, false, tags));

  std::string s;
  ASSERT_TRUE(db.LookupGlobalProperty(s, *manager, MISSING_SERVER_IDENTIFIER, Orthanc::GlobalProperty_DatabaseInternal1));
  ASSERT_EQ("3", s);

  OrthancPluginCreateInstanceResult r1, r2;
  
  memset(&r1, 0, sizeof(r1));
  db.CreateInstance(r1, *manager, "a", "b", "c", "d");
  ASSERT_TRUE(r1.isNewInstance);
  ASSERT_TRUE(r1.isNewSeries);
  ASSERT_TRUE(r1.isNewStudy);
  ASSERT_TRUE(r1.isNewPatient);

  memset(&r2, 0, sizeof(r2));
  db.CreateInstance(r2, *manager, "a", "b", "c", "d");
  ASSERT_FALSE(r2.isNewInstance);
  ASSERT_EQ(r1.instanceId, r2.instanceId);

  // Breaking the hierarchy
  // This does not throw anymore since at least 6.0.  This would only happen in case of series hash collision
  // which would actually be very damagefull at many places in Orthanc.
  // memset(&r2, 0, sizeof(r2));
  // ASSERT_THROW(db.CreateInstance(r2, *manager, "a", "e", "c", "f"), Orthanc::OrthancException);

  memset(&r2, 0, sizeof(r2));
  db.CreateInstance(r2, *manager, "a", "b", "c", "e");
  ASSERT_TRUE(r2.isNewInstance);
  ASSERT_FALSE(r2.isNewSeries);
  ASSERT_FALSE(r2.isNewStudy);
  ASSERT_FALSE(r2.isNewPatient);
  ASSERT_EQ(r1.patientId, r2.patientId);
  ASSERT_EQ(r1.studyId, r2.studyId);
  ASSERT_EQ(r1.seriesId, r2.seriesId);
  ASSERT_NE(r1.instanceId, r2.instanceId);

  memset(&r2, 0, sizeof(r2));
  db.CreateInstance(r2, *manager, "a", "b", "f", "g");
  ASSERT_TRUE(r2.isNewInstance);
  ASSERT_TRUE(r2.isNewSeries);
  ASSERT_FALSE(r2.isNewStudy);
  ASSERT_FALSE(r2.isNewPatient);
  ASSERT_EQ(r1.patientId, r2.patientId);
  ASSERT_EQ(r1.studyId, r2.studyId);
  ASSERT_NE(r1.seriesId, r2.seriesId);
  ASSERT_NE(r1.instanceId, r2.instanceId);

  memset(&r2, 0, sizeof(r2));
  db.CreateInstance(r2, *manager, "a", "h", "i", "j");
  ASSERT_TRUE(r2.isNewInstance);
  ASSERT_TRUE(r2.isNewSeries);
  ASSERT_TRUE(r2.isNewStudy);
  ASSERT_FALSE(r2.isNewPatient);
  ASSERT_EQ(r1.patientId, r2.patientId);
  ASSERT_NE(r1.studyId, r2.studyId);
  ASSERT_NE(r1.seriesId, r2.seriesId);
  ASSERT_NE(r1.instanceId, r2.instanceId);

  memset(&r2, 0, sizeof(r2));
  db.CreateInstance(r2, *manager, "k", "l", "m", "n");
  ASSERT_TRUE(r2.isNewInstance);
  ASSERT_TRUE(r2.isNewSeries);
  ASSERT_TRUE(r2.isNewStudy);
  ASSERT_TRUE(r2.isNewPatient);
  ASSERT_NE(r1.patientId, r2.patientId);
  ASSERT_NE(r1.studyId, r2.studyId);
  ASSERT_NE(r1.seriesId, r2.seriesId);
  ASSERT_NE(r1.instanceId, r2.instanceId);
}
#endif


TEST(PostgreSQL, Lock2)
{
  std::unique_ptr<PostgreSQLDatabase> db1(CreateTestDatabase());

  ASSERT_FALSE(db1->ReleaseAdvisoryLock(43)); // lock counter = 0
  ASSERT_TRUE(db1->AcquireAdvisoryLock(43));  // lock counter = 1

  // OK, as this is the same connection
  ASSERT_TRUE(db1->AcquireAdvisoryLock(43));  // lock counter = 2
  ASSERT_TRUE(db1->ReleaseAdvisoryLock(43));  // lock counter = 1

  // Try and release twice the lock
  ASSERT_TRUE(db1->ReleaseAdvisoryLock(43));  // lock counter = 0
  ASSERT_FALSE(db1->ReleaseAdvisoryLock(43)); // cannot unlock
  ASSERT_TRUE(db1->AcquireAdvisoryLock(43));  // lock counter = 1

  {
    std::unique_ptr<PostgreSQLDatabase> db2(CreateTestDatabase());

    // The "db1" is still actively locking
    ASSERT_FALSE(db2->AcquireAdvisoryLock(43));

    // Release the "db1" lock
    ASSERT_TRUE(db1->ReleaseAdvisoryLock(43));
    ASSERT_FALSE(db1->ReleaseAdvisoryLock(43));

    // "db2" can now acquire the lock, but not "db1"
    ASSERT_TRUE(db2->AcquireAdvisoryLock(43));
    ASSERT_FALSE(db1->AcquireAdvisoryLock(43));
  }

  // "db2" is closed, "db1" can now acquire the lock
  ASSERT_TRUE(db1->AcquireAdvisoryLock(43));
}
