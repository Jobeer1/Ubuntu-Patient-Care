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


#include "MySQLIndex.h"

#include "../../Framework/Plugins/GlobalProperties.h"
#include "../../Framework/MySQL/MySQLDatabase.h"
#include "../../Framework/MySQL/MySQLTransaction.h"
#include "MySQLDefinitions.h"

#include <EmbeddedResources.h>  // Auto-generated file

#include <Compatibility.h>  // For std::unique_ptr<>
#include <Logging.h>
#include <OrthancException.h>

#include <ctype.h>

namespace OrthancDatabases
{
  MySQLIndex::MySQLIndex(OrthancPluginContext* context,
                         const MySQLParameters& parameters,
                         bool readOnly) :
    IndexBackend(context, readOnly, false),
    parameters_(parameters),
    clearAll_(false)
  {
  }


  IDatabaseFactory* MySQLIndex::CreateDatabaseFactory() 
  {
    return MySQLDatabase::CreateDatabaseFactory(parameters_);
  }


  static void ThrowCannotCreateTrigger()
  {
    LOG(ERROR) << "The MySQL user is not allowed to create triggers => 2 possible solutions:";
    LOG(ERROR) << "  1- Give the SUPER privilege to the MySQL database user, or";
    LOG(ERROR) << "  2- Run \"set global log_bin_trust_function_creators=1;\" as MySQL root user.";
    LOG(ERROR) << "Once you are done, drop and recreate the MySQL database";
    throw Orthanc::OrthancException(Orthanc::ErrorCode_Database,
                                    "Need to fix the MySQL permissions for \"CREATE TRIGGER\"");
  }
  

  void MySQLIndex::ConfigureDatabase(DatabaseManager& manager,
                                     bool hasIdentifierTags,
                                     const std::list<IdentifierTag>& identifierTags)
  {
    uint32_t expectedVersion = 6;

    if (GetContext())   // "GetContext()" can possibly be NULL in the unit tests
    {
      expectedVersion = OrthancPluginGetExpectedDatabaseVersion(GetContext());
    }

    // Check the expected version of the database
    if (expectedVersion != 6)
    {
      LOG(ERROR) << "This database plugin is incompatible with your version of Orthanc "
                 << "expecting the DB schema version " << expectedVersion 
                 << ", but this plugin is only compatible with version 6";
      throw Orthanc::OrthancException(Orthanc::ErrorCode_Plugin);
    }

    if (!MySQLDatabase::IsValidDatabaseIdentifier(parameters_.GetDatabase()))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }

    if (clearAll_)
    {
      MySQLDatabase::ClearDatabase(parameters_);
    }

    MySQLDatabase& db = dynamic_cast<MySQLDatabase&>(manager.GetDatabase());
    
    {
      MySQLDatabase::TransientAdvisoryLock lock(db, MYSQL_LOCK_DATABASE_SETUP);

      /**
       * In a first transaction, we create the tables. Such a
       * transaction cannot be rollback: "The CREATE TABLE statement
       * in InnoDB is processed as a single transaction. This means
       * that a ROLLBACK from the user does not undo CREATE TABLE
       * statements the user made during that transaction."
       * https://dev.mysql.com/doc/refman/8.0/en/implicit-commit.html
       *
       * As a consequence, we delay the initial population of the
       * tables in a sequence of transactions below. This solves the
       * error message "MySQL plugin is incompatible with database
       * schema version: 0" that was reported in the forum:
       * https://groups.google.com/d/msg/orthanc-users/OCFFkm1qm0k/Mbroy8VWAQAJ
       **/      
      {
        DatabaseManager::Transaction t(manager, TransactionType_ReadWrite);
        
        t.GetDatabaseTransaction().ExecuteMultiLines("ALTER DATABASE " + parameters_.GetDatabase() + 
                                                     " CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci");

        // This is the first table to be created
        if (!t.GetDatabaseTransaction().DoesTableExist("GlobalProperties"))
        {
          std::string query;
          
          Orthanc::EmbeddedResources::GetFileResource
            (query, Orthanc::EmbeddedResources::MYSQL_PREPARE_INDEX);

          // Need to escape arobases: Don't use "t.GetDatabaseTransaction().ExecuteMultiLines()" here
          db.ExecuteMultiLines(query, true);
        }

        t.Commit();
      }

      /**
       * This is the sequence of transactions that initially populate
       * the database. WARNING - As table creation cannot be rollback,
       * don't forget to add "IF NOT EXISTS" if some table must be
       * created below this point (in order to recover from failed
       * transaction).
       **/

      {
        DatabaseManager::Transaction t(manager, TransactionType_ReadWrite);

        // This is the last table to be created
        if (!t.GetDatabaseTransaction().DoesTableExist("PatientRecyclingOrder"))
        {
          LOG(ERROR) << "Corrupted MySQL database";
          throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);        
        }

        // This is the last item to be created
        if (!t.GetDatabaseTransaction().DoesTriggerExist("PatientAdded"))
        {
          ThrowCannotCreateTrigger();
        }

        int version = 0;

        if (!LookupGlobalIntegerProperty(version, manager, MISSING_SERVER_IDENTIFIER, Orthanc::GlobalProperty_DatabaseSchemaVersion))
        {
          SetGlobalIntegerProperty(manager, MISSING_SERVER_IDENTIFIER, Orthanc::GlobalProperty_DatabaseSchemaVersion, expectedVersion);
          SetGlobalIntegerProperty(manager, MISSING_SERVER_IDENTIFIER, Orthanc::GlobalProperty_DatabasePatchLevel, 1);
          version = expectedVersion;
        }

        if (version != 6)
        {
          LOG(ERROR) << "MySQL plugin is incompatible with database schema version: " << version;
          throw Orthanc::OrthancException(Orthanc::ErrorCode_Database);        
        }

        t.Commit();
      }

      int revision = 0;

      {
        DatabaseManager::Transaction t(manager, TransactionType_ReadWrite);

        if (!LookupGlobalIntegerProperty(revision, manager, MISSING_SERVER_IDENTIFIER, Orthanc::GlobalProperty_DatabasePatchLevel))
        {
          revision = 1;
          SetGlobalIntegerProperty(manager, MISSING_SERVER_IDENTIFIER, Orthanc::GlobalProperty_DatabasePatchLevel, revision);
        }

        t.Commit();
      }

      if (revision == 1)
      {
        DatabaseManager::Transaction t(manager, TransactionType_ReadWrite);
        
        // The serialization of jobs as a global property can lead to
        // very long values => switch to the LONGTEXT type that can
        // store up to 4GB:
        // https://stackoverflow.com/a/13932834/881731
        t.GetDatabaseTransaction().ExecuteMultiLines("ALTER TABLE GlobalProperties MODIFY value LONGTEXT");
        
        revision = 2;
        SetGlobalIntegerProperty(manager, MISSING_SERVER_IDENTIFIER, Orthanc::GlobalProperty_DatabasePatchLevel, revision);

        t.Commit();
      }

      if (revision == 2)
      {        
        DatabaseManager::Transaction t(manager, TransactionType_ReadWrite);

        // Install the "GetLastChangeIndex" extension
        std::string query;

        Orthanc::EmbeddedResources::GetFileResource
          (query, Orthanc::EmbeddedResources::MYSQL_GET_LAST_CHANGE_INDEX);

        // Need to escape arobases: Don't use "t.GetDatabaseTransaction().ExecuteMultiLines()" here
        db.ExecuteMultiLines(query, true);

        if (!t.GetDatabaseTransaction().DoesTriggerExist("ChangeAdded"))
        {
          ThrowCannotCreateTrigger();
        }
        
        revision = 3;
        SetGlobalIntegerProperty(manager, MISSING_SERVER_IDENTIFIER, Orthanc::GlobalProperty_DatabasePatchLevel, revision);

        t.Commit();
      }
      
      if (revision == 3)
      {
        DatabaseManager::Transaction t(manager, TransactionType_ReadWrite);

        // Reconfiguration of "Metadata" from TEXT type (up to 64KB)
        // to the LONGTEXT type (up to 4GB). This might be important
        // for applications such as the Osimis Web viewer that stores
        // large amount of metadata.
        // https://orthanc.uclouvain.be/book/faq/features.html#central-registry-of-metadata-and-attachments
        t.GetDatabaseTransaction().ExecuteMultiLines("ALTER TABLE Metadata MODIFY value LONGTEXT");
        
        revision = 4;
        SetGlobalIntegerProperty(manager, MISSING_SERVER_IDENTIFIER, Orthanc::GlobalProperty_DatabasePatchLevel, revision);

        t.Commit();
      }
      
      if (revision == 4)
      {
        DatabaseManager::Transaction t(manager, TransactionType_ReadWrite);
        
        // Install the "CreateInstance" extension
        std::string query;
        
        Orthanc::EmbeddedResources::GetFileResource
          (query, Orthanc::EmbeddedResources::MYSQL_CREATE_INSTANCE);

        // Need to escape arobases: Don't use "t.GetDatabaseTransaction().ExecuteMultiLines()" here
        db.ExecuteMultiLines(query, true);
        
        revision = 5;
        SetGlobalIntegerProperty(manager, MISSING_SERVER_IDENTIFIER, Orthanc::GlobalProperty_DatabasePatchLevel, revision);

        t.Commit();
      }

      if (revision == 5)      
      {
        // Added new table "ServerProperties" since release 4.0 to deal with multiple writers
        DatabaseManager::Transaction t(manager, TransactionType_ReadWrite);

        if (t.GetDatabaseTransaction().DoesTableExist("ServerProperties"))
        {
          /**
           * Patch for MySQL plugin 4.0, where the column "value" was
           * "TEXT" instead of "LONGTEXT", which prevented
           * serialization of large jobs. This was giving error "MySQL
           * error (1406,22001): Data too long for column 'value' at
           * row 1" after log message "Serializing the content of the
           * jobs engine" (in --trace mode).
           * https://groups.google.com/g/orthanc-users/c/1Y3nTBdr0uE/m/K7PA5pboAgAJ
           **/
          t.GetDatabaseTransaction().ExecuteMultiLines("ALTER TABLE ServerProperties MODIFY value LONGTEXT");          
        }
        else
        {
          t.GetDatabaseTransaction().ExecuteMultiLines("CREATE TABLE ServerProperties(server VARCHAR(64) NOT NULL, "
                                                       "property INTEGER, value LONGTEXT, PRIMARY KEY(server, property))");
        }

        // Revision 6 indicates that "value" of "ServerProperties" is
        // "LONGTEXT", whereas revision 5 corresponds to "TEXT"
        revision = 6;
        SetGlobalIntegerProperty(manager, MISSING_SERVER_IDENTIFIER, Orthanc::GlobalProperty_DatabasePatchLevel, revision);
        
        t.Commit();
      }

      if (revision == 6)
      {
        // Added new table "Labels" since release 5.0 to deal with
        // labels that were introduced in Orthanc 1.12.0
        DatabaseManager::Transaction t(manager, TransactionType_ReadWrite);

        t.GetDatabaseTransaction().ExecuteMultiLines(
          "CREATE TABLE Labels(id BIGINT NOT NULL,"
          "label VARCHAR(64) NOT NULL,"
          "PRIMARY KEY(id, label),"
          "CONSTRAINT Labels1 FOREIGN KEY (id) REFERENCES Resources(internalId) ON DELETE CASCADE);"
          "CREATE INDEX LabelsIndex1 ON Labels(id);"
          "CREATE INDEX LabelsIndex2 ON Labels(label);");

        revision = 7;
        SetGlobalIntegerProperty(manager, MISSING_SERVER_IDENTIFIER, Orthanc::GlobalProperty_DatabasePatchLevel, revision);

        t.Commit();
      }

      if (revision == 7)
      {
        DatabaseManager::Transaction t(manager, TransactionType_ReadWrite);
        
        // Install the "CreateInstance" extension
        std::string query;
        
        Orthanc::EmbeddedResources::GetFileResource
          (query, Orthanc::EmbeddedResources::MYSQL_DELETE_RESOURCES);

        // Need to escape arobases: Don't use "t.GetDatabaseTransaction().ExecuteMultiLines()" here
        db.ExecuteMultiLines(query, true);
        
        revision = 8;
        SetGlobalIntegerProperty(manager, MISSING_SERVER_IDENTIFIER, Orthanc::GlobalProperty_DatabasePatchLevel, revision);

        t.Commit();
      }

      if (revision == 8)
      {
        DatabaseManager::Transaction t(manager, TransactionType_ReadWrite);
        
        // Install revision and customData extension
        std::string query;
        
        Orthanc::EmbeddedResources::GetFileResource
          (query, Orthanc::EmbeddedResources::MYSQL_INSTALL_REVISION_AND_CUSTOM_DATA);

        // Need to escape arobases: Don't use "t.GetDatabaseTransaction().ExecuteMultiLines()" here
        db.ExecuteMultiLines(query, true);
        
        revision = 9;
        SetGlobalIntegerProperty(manager, MISSING_SERVER_IDENTIFIER, Orthanc::GlobalProperty_DatabasePatchLevel, revision);

        t.Commit();
      }

      if (revision != 9)
      {
        LOG(ERROR) << "MySQL plugin is incompatible with database schema revision: " << revision;
        throw Orthanc::OrthancException(Orthanc::ErrorCode_Database);        
      }
    }

    
    /**
     * WARNING: This lock must be acquired after
     * "MYSQL_LOCK_DATABASE_SETUP" is released. Indeed, in MySQL <
     * 5.7, it is impossible to acquire more than one lock at a time,
     * as calling "SELECT GET_LOCK()" releases all the
     * previously-acquired locks.
     * https://dev.mysql.com/doc/refman/5.7/en/locking-functions.html
     **/
    if (parameters_.HasLock())
    {
      db.AdvisoryLock(MYSQL_LOCK_INDEX);
    }
  }


  int64_t MySQLIndex::CreateResource(DatabaseManager& manager,
                                     const char* publicId,
                                     OrthancPluginResourceType type)
  {
    {
      DatabaseManager::CachedStatement statement(
        STATEMENT_FROM_HERE, manager,
        "INSERT INTO Resources VALUES(NULL, ${type}, ${id}, NULL)");
    
      statement.SetParameterType("id", ValueType_Utf8String);
      statement.SetParameterType("type", ValueType_Integer64);

      Dictionary args;
      args.SetUtf8Value("id", publicId);
      args.SetIntegerValue("type", static_cast<int>(type));
    
      statement.Execute(args);
    }

    {
      DatabaseManager::CachedStatement statement(
        STATEMENT_FROM_HERE, manager,
        "SELECT LAST_INSERT_ID()");

      statement.Execute();
      
      return statement.ReadInteger64(0);
    }
  }


  void MySQLIndex::DeleteResource(IDatabaseBackendOutput& output,
                                  DatabaseManager& manager,
                                  int64_t id)
  {
    /**
     * Contrarily to PostgreSQL and SQLite, the MySQL dialect doesn't
     * support cascaded delete inside the same table. This has to be
     * manually reimplemented.
     **/
    
    ClearDeletedFiles(manager);

    // Recursive exploration of resources to be deleted, from the "id"
    // resource to the top of the tree of resources
    
    bool done = false;

    while (!done)
    {
      bool hasSibling = false;
      int64_t parentId = -1;  // Dummy initialization
      
      {
        DatabaseManager::CachedStatement lookupSiblings(
          STATEMENT_FROM_HERE, manager,
          "SELECT parentId FROM Resources "
          "WHERE parentId = (SELECT parentId FROM Resources WHERE internalId=${id});");

        lookupSiblings.SetParameterType("id", ValueType_Integer64);

        Dictionary args;
        args.SetIntegerValue("id", id);
    
        lookupSiblings.Execute(args);

        if (lookupSiblings.IsDone())
        {
          // "id" is a root node
          done = true;
        }
        else
        {
          parentId = lookupSiblings.ReadInteger64(0);
          lookupSiblings.Next();

          if (lookupSiblings.IsDone())
          {
            // "id" has no sibling node, recursively remove
            done = false;
            id = parentId;
          }
          else
          {
            // "id" has at least one sibling node: the parent node is the remaining ancestor
            done = true;
            hasSibling = true;
          }
        }
      }

      if (hasSibling)
      {
        // This cannot be executed in the same scope as another
        // DatabaseManager::CachedStatement
        
        DatabaseManager::CachedStatement parent(
          STATEMENT_FROM_HERE, manager,
          "SELECT publicId, resourceType FROM Resources WHERE internalId=${id};");
        
        parent.SetParameterType("id", ValueType_Integer64);
        
        Dictionary args2;
        args2.SetIntegerValue("id", parentId);
        
        parent.Execute(args2);
        
        output.SignalRemainingAncestor(
          parent.ReadString(0),
          static_cast<OrthancPluginResourceType>(parent.ReadInteger32(1)));
      }
    }

    {
      DatabaseManager::CachedStatement dropTemporaryTable(
        STATEMENT_FROM_HERE, manager,
        "DROP TEMPORARY TABLE IF EXISTS DeletedResources");
      dropTemporaryTable.Execute();
    }

    {
      DatabaseManager::CachedStatement lookupResourcesToDelete(
        STATEMENT_FROM_HERE, manager,
        "CREATE TEMPORARY TABLE DeletedResources SELECT * FROM (SELECT internalId, resourceType, publicId FROM Resources WHERE internalId=${id} OR parentId=${id} OR parentId IN (SELECT internalId FROM Resources WHERE parentId=${id}) OR parentId IN (SELECT internalId FROM Resources WHERE parentId IN (SELECT internalId FROM Resources WHERE parentId=${id}))) AS t");
      lookupResourcesToDelete.SetParameterType("id", ValueType_Integer64);

      Dictionary args;
      args.SetIntegerValue("id", id);
      lookupResourcesToDelete.Execute(args);
    }

    // {
    //   DatabaseManager::CachedStatement deleteHierarchy(
    //     STATEMENT_FROM_HERE, manager,
    //     "DELETE FROM Resources WHERE internalId IN (SELECT internalId FROM DeletedResources)");
    //   deleteHierarchy.Execute();
    // }


    {
      DatabaseManager::CachedStatement deleteResources(
        STATEMENT_FROM_HERE, manager,
        "CALL DeleteResources(${id})");

      deleteResources.SetParameterType("id", ValueType_Integer64);

      Dictionary args;
      args.SetIntegerValue("id", id);
    
      deleteResources.Execute(args);
    }

    SignalDeletedResources(output, manager);
    SignalDeletedFiles(output, manager);
  }

  
  int64_t MySQLIndex::GetLastChangeIndex(DatabaseManager& manager)
  {
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "SELECT value FROM GlobalIntegers WHERE property = 0");
    
    statement.SetReadOnly(true);
    statement.Execute();

    return statement.ReadInteger64(0);
  }


#if ORTHANC_PLUGINS_HAS_DATABASE_CONSTRAINT == 1
  void MySQLIndex::CreateInstance(OrthancPluginCreateInstanceResult& result,
                                  DatabaseManager& manager,
                                  const char* hashPatient,
                                  const char* hashStudy,
                                  const char* hashSeries,
                                  const char* hashInstance)
  {
    {
      DatabaseManager::CachedStatement statement(
        STATEMENT_FROM_HERE, manager,
        "CALL CreateInstance(${patient}, ${study}, ${series}, ${instance}, "
        "@isNewPatient, @isNewStudy, @isNewSeries, @isNewInstance, "
        "@patientKey, @studyKey, @seriesKey, @instanceKey)");

      statement.SetParameterType("patient", ValueType_Utf8String);
      statement.SetParameterType("study", ValueType_Utf8String);
      statement.SetParameterType("series", ValueType_Utf8String);
      statement.SetParameterType("instance", ValueType_Utf8String);

      Dictionary args;
      args.SetUtf8Value("patient", hashPatient);
      args.SetUtf8Value("study", hashStudy);
      args.SetUtf8Value("series", hashSeries);
      args.SetUtf8Value("instance", hashInstance);
    
      statement.Execute(args);

      if (!statement.IsDone())
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_Database);
      }
    }

    {
      DatabaseManager::CachedStatement statement(
        STATEMENT_FROM_HERE, manager,
        "SELECT @isNewPatient, @isNewStudy, @isNewSeries, @isNewInstance, "
        "@patientKey, @studyKey, @seriesKey, @instanceKey");

      statement.Execute();

      for (size_t i = 0; i < 8; i++)
      {
        statement.SetResultFieldType(i, ValueType_Integer64);
      }

      result.isNewInstance = (statement.ReadInteger64(3) == 1);
      result.instanceId = statement.ReadInteger64(7);

      if (result.isNewInstance)
      {
        result.isNewPatient = (statement.ReadInteger64(0) == 1);
        result.isNewStudy = (statement.ReadInteger64(1) == 1);
        result.isNewSeries = (statement.ReadInteger64(2) == 1);
        result.patientId = statement.ReadInteger64(4);
        result.studyId = statement.ReadInteger64(5);
        result.seriesId = statement.ReadInteger64(6);
      }
    }   
  }
#endif


}
