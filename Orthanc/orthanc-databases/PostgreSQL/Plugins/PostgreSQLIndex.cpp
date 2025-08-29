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


#include "PostgreSQLIndex.h"

#include "../../Framework/Plugins/GlobalProperties.h"
#include "../../Framework/PostgreSQL/PostgreSQLDatabase.h"
#include "../../Framework/PostgreSQL/PostgreSQLTransaction.h"
#include "PostgreSQLDefinitions.h"

#include <EmbeddedResources.h>  // Auto-generated file

#include <Compatibility.h>  // For std::unique_ptr<>
#include <Toolbox.h>
#include <SystemToolbox.h>
#include <Logging.h>
#include <OrthancException.h>

#include <boost/algorithm/string/join.hpp>


namespace Orthanc
{
  // Some aliases for internal properties
  static const GlobalProperty GlobalProperty_HasTrigramIndex = GlobalProperty_DatabaseInternal0;
  static const GlobalProperty GlobalProperty_HasCreateInstance = GlobalProperty_DatabaseInternal1;
  static const GlobalProperty GlobalProperty_HasFastCountResources = GlobalProperty_DatabaseInternal2;
  static const GlobalProperty GlobalProperty_GetLastChangeIndex = GlobalProperty_DatabaseInternal3;
  static const GlobalProperty GlobalProperty_HasComputeStatisticsReadOnly = GlobalProperty_DatabaseInternal4;
}

#define CURRENT_DB_REVISION 6

namespace OrthancDatabases
{
  PostgreSQLIndex::PostgreSQLIndex(OrthancPluginContext* context,
                                   const PostgreSQLParameters& parameters,
                                   bool readOnly) :
    IndexBackend(context, readOnly, parameters.GetAllowInconsistentChildCounts()),
    parameters_(parameters),
    clearAll_(false),
    hkHasComputedAllMissingChildCount_(false)
  {
  }

  
  IDatabaseFactory* PostgreSQLIndex::CreateDatabaseFactory()
  {
    return PostgreSQLDatabase::CreateDatabaseFactory(parameters_);
  }

  void PostgreSQLIndex::ApplyPrepareIndex(DatabaseManager::Transaction& t, DatabaseManager& manager)
  {
    std::string query;

    Orthanc::EmbeddedResources::GetFileResource
      (query, Orthanc::EmbeddedResources::POSTGRESQL_PREPARE_INDEX);
    t.GetDatabaseTransaction().ExecuteMultiLines(query);
  }
  
  void PostgreSQLIndex::ConfigureDatabase(DatabaseManager& manager,
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
                 << "expecting the Orthanc DB schema version " << expectedVersion 
                 << ", but this plugin is only compatible with version 6";
      throw Orthanc::OrthancException(Orthanc::ErrorCode_Plugin);
    }

    PostgreSQLDatabase& db = dynamic_cast<PostgreSQLDatabase&>(manager.GetDatabase());

    if (parameters_.HasLock()) 
    {
      if (IsReadOnly())
      {
        LOG(ERROR) << "READ-ONLY SYSTEM: Unable to lock the database when working in ReadOnly mode."; 
        throw Orthanc::OrthancException(Orthanc::ErrorCode_Plugin);
      }

      db.AdvisoryLock(POSTGRESQL_LOCK_INDEX);
    }

    if (!IsReadOnly())
    {
      // lock the full DB while checking if it needs to be created/ugraded
      PostgreSQLDatabase::TransientAdvisoryLock lock(db, POSTGRESQL_LOCK_DATABASE_SETUP);

      if (clearAll_)
      {
        db.ClearAll();
      }

      {
        DatabaseManager::Transaction t(manager, TransactionType_ReadWrite);
        bool hasAppliedAnUpgrade = false;

        if (!t.GetDatabaseTransaction().DoesTableExist("Resources"))
        {
          LOG(WARNING) << "PostgreSQL is creating the database schema";

          ApplyPrepareIndex(t, manager);

          if (!t.GetDatabaseTransaction().DoesTableExist("Resources"))
          {
            LOG(ERROR) << "Corrupted PostgreSQL database or failed to create the database schema";
            throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);        
          }
        }
        else
        {
          LOG(WARNING) << "The database schema already exists, checking if it needs to be updated";

          int version = 0;
          if (!LookupGlobalIntegerProperty(version, manager, MISSING_SERVER_IDENTIFIER, Orthanc::GlobalProperty_DatabaseSchemaVersion) ||
              version != 6)
          {
            LOG(ERROR) << "PostgreSQL plugin is incompatible with Orthanc database schema version: " << version;
            throw Orthanc::OrthancException(Orthanc::ErrorCode_Database);        
          }

          int currentRevision = 0;
          if (!LookupGlobalIntegerProperty(currentRevision, manager, MISSING_SERVER_IDENTIFIER, Orthanc::GlobalProperty_DatabasePatchLevel))
          {
            LOG(WARNING) << "No Database revision found";
          }
          LOG(WARNING) << "Current Database revision is " << currentRevision;

          int hasTrigram = 0;
          if (!LookupGlobalIntegerProperty(hasTrigram, manager, MISSING_SERVER_IDENTIFIER,
                                           Orthanc::GlobalProperty_HasTrigramIndex) || 
              hasTrigram != 1)
          {
            // We've observed 9 minutes on DB with 100000 studies
            LOG(WARNING) << "The DB schema update will try to enable trigram matching on the PostgreSQL database "
                         << "to speed up wildcard searches. This may take several minutes. ";
            if (currentRevision > 0)
            {
              LOG(WARNING) << "Considering current revision is 1";
              currentRevision = 1;
            }
          }

          int property = 0;
          if (!LookupGlobalIntegerProperty(property, manager, MISSING_SERVER_IDENTIFIER,
                                          Orthanc::GlobalProperty_GetLastChangeIndex) ||
              property != 1)
          {
            LOG(WARNING) << "The DB schema does not contain the GetLastChangeIndex update. ";
            if (currentRevision > 0)
            {
              LOG(WARNING) << "Considering current revision is 1";
              currentRevision = 1;
            }

          }

          // If you add new tests here, update the test in the "ReadOnly" code below

          if (currentRevision == 0)
          {
            LOG(WARNING) << "Upgrading DB schema from unknown to revision 1";
            std::string query;

            Orthanc::EmbeddedResources::GetFileResource
              (query, Orthanc::EmbeddedResources::POSTGRESQL_UPGRADE_UNKNOWN_TO_REV1);
            t.GetDatabaseTransaction().ExecuteMultiLines(query);
            currentRevision = 1;
          }
          
          if (currentRevision == 1)
          {
            LOG(WARNING) << "Upgrading DB schema from revision 1 to revision 2";

            std::string query;

            Orthanc::EmbeddedResources::GetFileResource
              (query, Orthanc::EmbeddedResources::POSTGRESQL_UPGRADE_REV1_TO_REV2);
            t.GetDatabaseTransaction().ExecuteMultiLines(query);
            currentRevision = 2;
          }

          if (currentRevision == 2)
          {
            LOG(WARNING) << "Upgrading DB schema from revision 2 to revision 3";

            std::string query;

            Orthanc::EmbeddedResources::GetFileResource
              (query, Orthanc::EmbeddedResources::POSTGRESQL_UPGRADE_REV2_TO_REV3);
            t.GetDatabaseTransaction().ExecuteMultiLines(query);
            currentRevision = 3;
          }

          if (currentRevision == 3)
          {
            LOG(WARNING) << "Upgrading DB schema from revision 3 to revision 4";

            std::string query;

            Orthanc::EmbeddedResources::GetFileResource
              (query, Orthanc::EmbeddedResources::POSTGRESQL_UPGRADE_REV3_TO_REV4);
            t.GetDatabaseTransaction().ExecuteMultiLines(query);
            hasAppliedAnUpgrade = true;
            currentRevision = 4;
          }

          if (currentRevision == 4)
          {
            LOG(WARNING) << "Upgrading DB schema from revision 4 to revision 5";

            std::string query;

            Orthanc::EmbeddedResources::GetFileResource
              (query, Orthanc::EmbeddedResources::POSTGRESQL_UPGRADE_REV4_TO_REV5);
            t.GetDatabaseTransaction().ExecuteMultiLines(query);
            hasAppliedAnUpgrade = true;
            currentRevision = 5;
          }

          if (currentRevision == 5)
          {
            LOG(WARNING) << "Upgrading DB schema from revision 5 to revision 6";

            std::string query;

            Orthanc::EmbeddedResources::GetFileResource
              (query, Orthanc::EmbeddedResources::POSTGRESQL_UPGRADE_REV5_TO_REV6);
            t.GetDatabaseTransaction().ExecuteMultiLines(query);
            hasAppliedAnUpgrade = true;
            currentRevision = 6;
          }

          if (hasAppliedAnUpgrade)
          {
            LOG(WARNING) << "Upgrading DB schema by applying PrepareIndex.sql";
            // apply all idempotent changes that are in the PrepareIndex.sql
            ApplyPrepareIndex(t, manager);

            if (!LookupGlobalIntegerProperty(currentRevision, manager, MISSING_SERVER_IDENTIFIER, Orthanc::GlobalProperty_DatabasePatchLevel))
            {
              LOG(ERROR) << "No Database revision found after the upgrade !";
              throw Orthanc::OrthancException(Orthanc::ErrorCode_Database);
            }

            LOG(WARNING) << "Database revision after the upgrade is " << currentRevision;

            if (currentRevision != CURRENT_DB_REVISION)
            {
              LOG(ERROR) << "Invalid database revision after the upgrade !";
              throw Orthanc::OrthancException(Orthanc::ErrorCode_Database);
            }
          }

        }

        t.Commit();

        if (hasAppliedAnUpgrade)
        {
          int currentRevision = 0;
          
          LookupGlobalIntegerProperty(currentRevision, manager, MISSING_SERVER_IDENTIFIER, Orthanc::GlobalProperty_DatabasePatchLevel);
          LOG(WARNING) << "Database revision after the upgrade is " << currentRevision;

          if (currentRevision != CURRENT_DB_REVISION)
          {
            LOG(ERROR) << "Invalid database revision after the upgrade !";
            throw Orthanc::OrthancException(Orthanc::ErrorCode_Database);
          }
        }

      }
    }
    else
    {
      LOG(WARNING) << "READ-ONLY SYSTEM: checking if the DB already exists and has the right schema"; 

      DatabaseManager::Transaction t(manager, TransactionType_ReadOnly);

      // test if the latest "extension" has been installed
      int revision;
      if (!LookupGlobalIntegerProperty(revision, manager, MISSING_SERVER_IDENTIFIER, Orthanc::GlobalProperty_DatabasePatchLevel)
          || revision != CURRENT_DB_REVISION)
      {      
        LOG(ERROR) << "READ-ONLY SYSTEM: the DB does not have the correct schema to run with this version of the plugin"; 
        throw Orthanc::OrthancException(Orthanc::ErrorCode_Database);
      }
    }
  }


  int64_t PostgreSQLIndex::CreateResource(DatabaseManager& manager,
                                          const char* publicId,
                                          OrthancPluginResourceType type)
  {
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "INSERT INTO Resources VALUES(DEFAULT, ${type}, ${id}, NULL) RETURNING internalId");
     
    statement.SetParameterType("id", ValueType_Utf8String);
    statement.SetParameterType("type", ValueType_Integer64);

    Dictionary args;
    args.SetUtf8Value("id", publicId);
    args.SetIntegerValue("type", static_cast<int>(type));
     
    statement.Execute(args);

    return statement.ReadInteger64(0);
  }


  uint64_t PostgreSQLIndex::GetTotalCompressedSize(DatabaseManager& manager)
  {
    uint64_t result;

    {
      DatabaseManager::CachedStatement statement(
        STATEMENT_FROM_HERE, manager,
        "SELECT * FROM ComputeStatisticsReadOnly(0)");

      statement.Execute();

      if (statement.IsNull(0))
      {
        return 0;
      }
      else
      {
        result = static_cast<uint64_t>(statement.ReadInteger64(0));
      }
    }
    
    // disabled because this is not alway true while transactions are being executed in READ COMITTED TRANSACTION.  This is however true when no files are being delete/added
    //assert(result == IndexBackend::GetTotalCompressedSize(manager));
    return result;
  }

  
  uint64_t PostgreSQLIndex::GetTotalUncompressedSize(DatabaseManager& manager)
  {
    uint64_t result;

    {
      DatabaseManager::CachedStatement statement(
        STATEMENT_FROM_HERE, manager,
        "SELECT * FROM ComputeStatisticsReadOnly(1)");

      statement.Execute();

      if (statement.IsNull(0))
      {
        return 0;
      }
      else
      {
        result = static_cast<uint64_t>(statement.ReadInteger64(0));
      }
    }
    
    // disabled because this is not alway true while transactions are being executed in READ COMITTED TRANSACTION.  This is however true when no files are being delete/added
    // assert(result == IndexBackend::GetTotalUncompressedSize(manager));
    return result;
  }

  int64_t PostgreSQLIndex::IncrementGlobalProperty(DatabaseManager& manager,
                                                   const char* serverIdentifier,
                                                   int32_t property,
                                                   int64_t increment)
  {
    if (serverIdentifier == NULL)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_NullPointer);
    }
    else
    {
      if (strlen(serverIdentifier) == 0)
      {
        DatabaseManager::CachedStatement statement(
          STATEMENT_FROM_HERE, manager,
          "INSERT INTO GlobalProperties (property, value) VALUES(${property}, ${increment}) "
          "  ON CONFLICT (property) DO UPDATE SET value = CAST(GlobalProperties.value AS BIGINT) + ${increment}"
          " RETURNING CAST(value AS BIGINT)");

        statement.SetParameterType("property", ValueType_Integer64);
        statement.SetParameterType("increment", ValueType_Integer64);

        Dictionary args;
        args.SetIntegerValue("property", property);
        args.SetIntegerValue("increment", increment);
        
        statement.Execute(args);

        return statement.ReadInteger64(0);
      }
      else
      {
        DatabaseManager::CachedStatement statement(
          STATEMENT_FROM_HERE, manager,
          "INSERT INTO ServerProperties (server, property, value) VALUES(${server}, ${property}, ${increment}) "
          "  ON CONFLICT (server, property) DO UPDATE SET value = CAST(ServerProperties.value AS BIGINT) + ${increment}"
          " RETURNING CAST(value AS BIGINT)");

        statement.SetParameterType("server", ValueType_Utf8String);
        statement.SetParameterType("property", ValueType_Integer64);
        statement.SetParameterType("increment", ValueType_Integer64);

        Dictionary args;
        args.SetUtf8Value("server", serverIdentifier);
        args.SetIntegerValue("property", property);
        args.SetIntegerValue("increment", increment);
        
        statement.Execute(args);

        return statement.ReadInteger64(0);
      }
    }
  }

  void PostgreSQLIndex::UpdateAndGetStatistics(DatabaseManager& manager,
                                               int64_t& patientsCount,
                                               int64_t& studiesCount,
                                               int64_t& seriesCount,
                                               int64_t& instancesCount,
                                               int64_t& compressedSize,
                                               int64_t& uncompressedSize)
  {
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "SELECT * FROM UpdateStatistics()");

    statement.Execute();

    patientsCount = statement.ReadInteger64(0);
    studiesCount = statement.ReadInteger64(1);
    seriesCount = statement.ReadInteger64(2);
    instancesCount = statement.ReadInteger64(3);
    compressedSize = statement.ReadInteger64(4);
    uncompressedSize = statement.ReadInteger64(5);
  }

  void PostgreSQLIndex::DeleteAttachment(IDatabaseBackendOutput& output,
                                         DatabaseManager& manager,
                                         int64_t id,
                                         int32_t attachment)
  {
    {
      DatabaseManager::CachedStatement statement(
        STATEMENT_FROM_HERE, manager,
        "SELECT DeleteAttachment(${id}, ${type})");

      statement.SetParameterType("id", ValueType_Integer64);
      statement.SetParameterType("type", ValueType_Integer32);

      Dictionary args;
      args.SetIntegerValue("id", id);
      args.SetInteger32Value("type", attachment);
    
      statement.ExecuteWithoutResult(args);
    }

    SignalDeletedFiles(output, manager);
  }


  void PostgreSQLIndex::ClearDeletedFiles(DatabaseManager& manager)
  {
    { // note: the temporary table lifespan is the session, not the transaction -> that's why we need the IF NOT EXISTS
      DatabaseManager::CachedStatement statement(
        STATEMENT_FROM_HERE, manager,
        "SELECT CreateDeletedFilesTemporaryTable()"
        );
      statement.ExecuteWithoutResult();
    }
  }

  void PostgreSQLIndex::ClearDeletedResources(DatabaseManager& manager)
  {
    { // note: the temporary table lifespan is the session, not the transaction -> that's why we need the IF NOT EXISTS
      DatabaseManager::CachedStatement statement(
        STATEMENT_FROM_HERE, manager,
        "CREATE TEMPORARY TABLE IF NOT EXISTS  DeletedResources("
        "resourceType INTEGER NOT NULL,"
        "publicId VARCHAR(64) NOT NULL"
        ");"
        );
      statement.Execute();
    }
    {
      DatabaseManager::CachedStatement statement(
        STATEMENT_FROM_HERE, manager,
        "DELETE FROM DeletedResources;"
        );

      statement.Execute();
    }
  }

  void PostgreSQLIndex::ClearRemainingAncestor(DatabaseManager& manager)
  {
    // not used anymore in PostgreSQL
  }

  void PostgreSQLIndex::DeleteResource(IDatabaseBackendOutput& output,
                                       DatabaseManager& manager,
                                       int64_t id)
  {
    // clearing of temporary table is now implemented in the funcion DeleteResource
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "SELECT * FROM DeleteResource(${id})");

    statement.SetParameterType("id", ValueType_Integer64);

    Dictionary args;
    args.SetIntegerValue("id", id);

    statement.Execute(args);

    if (statement.IsDone() ||
        statement.GetResultFieldsCount() != 2)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_Database);
    }

    statement.SetResultFieldType(0, ValueType_Integer64);
    statement.SetResultFieldType(1, ValueType_Utf8String);

    if (!statement.IsNull(0))
    {
      output.SignalRemainingAncestor(
        statement.ReadString(1),
        static_cast<OrthancPluginResourceType>(statement.ReadInteger32(0)));
    }

    SignalDeletedFiles(output, manager);
    SignalDeletedResources(output, manager);
  }



#if ORTHANC_PLUGINS_HAS_DATABASE_CONSTRAINT == 1
  void PostgreSQLIndex::CreateInstance(OrthancPluginCreateInstanceResult& result,
                                       DatabaseManager& manager,
                                       const char* hashPatient,
                                       const char* hashStudy,
                                       const char* hashSeries,
                                       const char* hashInstance)
  {
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "SELECT * FROM CreateInstance(${patient}, ${study}, ${series}, ${instance})");

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

    if (statement.IsDone() ||
        statement.GetResultFieldsCount() != 8)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_Database);
    }

    for (size_t i = 0; i < 8; i++)
    {
      statement.SetResultFieldType(i, ValueType_Integer64);
    }

    // LOG(INFO) << statement.ReadInteger64(0) << statement.ReadInteger64(1) << statement.ReadInteger64(2) << statement.ReadInteger64(3);

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
#endif


#if ORTHANC_PLUGINS_HAS_DATABASE_CONSTRAINT == 1
  static void ExecuteSetResourcesContentTags(
    DatabaseManager& manager,
    const std::string& table,
    uint32_t count,
    const OrthancPluginResourcesContentTags* tags)
  {
    std::string sql;

    Dictionary args;
    
    for (uint32_t i = 0; i < count; i++)
    {
      std::string resourceArgName = "r" + boost::lexical_cast<std::string>(i);
      std::string groupArgName = "g" + boost::lexical_cast<std::string>(i);
      std::string elementArgName = "e" + boost::lexical_cast<std::string>(i);
      std::string valueArgName = "v" + boost::lexical_cast<std::string>(i);

      args.SetIntegerValue(resourceArgName, tags[i].resource);
      args.SetInteger32Value(elementArgName, tags[i].element);
      args.SetInteger32Value(groupArgName, tags[i].group);
      args.SetUtf8Value(valueArgName, tags[i].value);

      std::string insert = ("(${" + resourceArgName + "}, ${" +
                            groupArgName + "}, ${" +
                            elementArgName + "}, " +
                            "${" + valueArgName + "})");

      if (sql.empty())
      {
        sql = "INSERT INTO " + table + " VALUES " + insert;
      }
      else
      {
        sql += ", " + insert;
      }
    }

    if (!sql.empty())
    {
      DatabaseManager::CachedStatement statement(STATEMENT_FROM_HERE_DYNAMIC(sql), manager, sql);
      
      for (uint32_t i = 0; i < count; i++)
      {
        statement.SetParameterType("r" + boost::lexical_cast<std::string>(i),
                                    ValueType_Integer64);
        statement.SetParameterType("g" + boost::lexical_cast<std::string>(i),
                                    ValueType_Integer32);
        statement.SetParameterType("e" + boost::lexical_cast<std::string>(i),
                                    ValueType_Integer32);
        statement.SetParameterType("v" + boost::lexical_cast<std::string>(i),
                                   ValueType_Utf8String);
      }

      statement.Execute(args);
    }
  }
#endif
  

#if ORTHANC_PLUGINS_HAS_DATABASE_CONSTRAINT == 1
  static void ExecuteSetResourcesContentMetadata(
    DatabaseManager& manager,
    bool hasRevisionsSupport,
    uint32_t count,
    const OrthancPluginResourcesContentMetadata* metadata)
  {
    if (count < 1)
    {
      return;
    }

    std::vector<std::string> resourceIds;
    std::vector<std::string> metadataTypes;
    std::vector<std::string> metadataValues;
    std::vector<std::string> revisions;

    Dictionary args;
    
    for (uint32_t i = 0; i < count; i++)
    {
      std::string resourceArgName = "r" + boost::lexical_cast<std::string>(i);
      std::string typeArgName = "t" + boost::lexical_cast<std::string>(i);
      std::string valueArgName = "v" + boost::lexical_cast<std::string>(i);

      args.SetIntegerValue(resourceArgName, metadata[i].resource);
      args.SetInteger32Value(typeArgName, metadata[i].metadata);
      args.SetUtf8Value(valueArgName, metadata[i].value);

      resourceIds.push_back("${" + resourceArgName + "}");
      metadataTypes.push_back("${" + typeArgName + "}");
      metadataValues.push_back("${" + valueArgName + "}");
      revisions.push_back("0");
    }

    std::string joinedResourceIds = boost::algorithm::join(resourceIds, ",");
    std::string joinedMetadataTypes = boost::algorithm::join(metadataTypes, ",");
    std::string joinedMetadataValues = boost::algorithm::join(metadataValues, ",");
    std::string joinedRevisions = boost::algorithm::join(revisions, ",");

    std::string sql = std::string("SELECT InsertOrUpdateMetadata(ARRAY[") + 
                                  joinedResourceIds + "], ARRAY[" + 
                                  joinedMetadataTypes + "], ARRAY[" + 
                                  joinedMetadataValues + "], ARRAY[" + 
                                  joinedRevisions + "])";

    DatabaseManager::CachedStatement statement(STATEMENT_FROM_HERE_DYNAMIC(sql), manager, sql);

    for (uint32_t i = 0; i < count; i++)
    {
      statement.SetParameterType("v" + boost::lexical_cast<std::string>(i),
                                  ValueType_Utf8String);
      statement.SetParameterType("r" + boost::lexical_cast<std::string>(i),
                                  ValueType_Integer64);
      statement.SetParameterType("t" + boost::lexical_cast<std::string>(i),
                                  ValueType_Integer32);
    }

    statement.Execute(args);
  }
#endif


  void PostgreSQLIndex::SetResourcesContent(DatabaseManager& manager,
                                     uint32_t countIdentifierTags,
                                     const OrthancPluginResourcesContentTags* identifierTags,
                                     uint32_t countMainDicomTags,
                                     const OrthancPluginResourcesContentTags* mainDicomTags,
                                     uint32_t countMetadata,
                                     const OrthancPluginResourcesContentMetadata* metadata)
  {
    ExecuteSetResourcesContentTags(manager, "DicomIdentifiers", countIdentifierTags, identifierTags);

    ExecuteSetResourcesContentTags(manager, "MainDicomTags", countMainDicomTags, mainDicomTags);
    
    ExecuteSetResourcesContentMetadata(manager, HasRevisionsSupport(), countMetadata, metadata);

  }


  uint64_t PostgreSQLIndex::GetResourcesCount(DatabaseManager& manager,
                                              OrthancPluginResourceType resourceType)
  {
    assert(OrthancPluginResourceType_Patient == 0 &&
           OrthancPluginResourceType_Study == 1 &&
           OrthancPluginResourceType_Series == 2 &&
           OrthancPluginResourceType_Instance == 3);

    uint64_t result;
    
    {
      DatabaseManager::StandaloneStatement statement(
        manager,
        std::string("SELECT * FROM ComputeStatisticsReadOnly(") + boost::lexical_cast<std::string>(resourceType + 2) + ")");  // For an explanation of the "+ 2" below, check out "PrepareIndex.sql"

      statement.Execute();

      if (statement.IsNull(0))
      {
        return 0;
      }
      else
      {
        result = static_cast<uint64_t>(statement.ReadInteger64(0));
      }
    }
      
    // disabled because this is not alway true while transactions are being executed in READ COMITTED TRANSACTION.  This is however true when no files are being delete/added
    // assert(result == IndexBackend::GetResourcesCount(manager, resourceType));

    return result;
  }


  int64_t PostgreSQLIndex::GetLastChangeIndex(DatabaseManager& manager)
  {
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "SELECT value FROM GlobalIntegers WHERE key = 6");

    statement.SetReadOnly(true);
    statement.Execute();

    return statement.ReadInteger64(0);
  }


  void PostgreSQLIndex::TagMostRecentPatient(DatabaseManager& manager,
                                             int64_t patient)
  {
    // This behavior is implemented in "CreateInstance()", and no
    // backward compatibility is necessary
    throw Orthanc::OrthancException(Orthanc::ErrorCode_Database);
  }

  void PostgreSQLIndex::SetProtectedPatient(DatabaseManager& manager,
                                            int64_t internalId, 
                                            bool isProtected)
  {
    std::unique_ptr<DatabaseManager::CachedStatement> statement;
    Dictionary args;

    if (isProtected)
    {
      statement.reset(new DatabaseManager::CachedStatement(
                        STATEMENT_FROM_HERE, manager,
                        "SELECT ProtectPatient(${id})"));
    }
    else
    {
      statement.reset(new DatabaseManager::CachedStatement(
                        STATEMENT_FROM_HERE, manager,
                        "SELECT UnprotectPatient(${id})"));
    }        

    statement->SetParameterType("id", ValueType_Integer64);
    args.SetIntegerValue("id", internalId);
      
    statement->Execute(args);
  }

  bool PostgreSQLIndex::IsProtectedPatient(DatabaseManager& manager,
                                        int64_t internalId)
  {
    std::string value;
    int64_t revision;
    
    if (LookupMetadata(value, revision, manager, internalId, 18)) // 18 = IsProtected
    {
      return value == "true";
    }

    return false;
  }

  bool PostgreSQLIndex::SelectPatientToRecycle(int64_t& internalId /*out*/,
                                               DatabaseManager& manager)
  {
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "SELECT r.internalId "
      "FROM Resources r "
      "JOIN Metadata m ON r.internalId = m.id AND m.type = 19 " // 19 = PatientRecyclingOrder
      "WHERE r.resourceType = 0 "
      "  AND NOT EXISTS "
      "   (SELECT 1 FROM Metadata m "
      "    WHERE m.id = r.internalId AND m.type = 18 AND m.value = 'true') "  // 18 = IsProtected
      " ORDER BY CAST(m.value AS INTEGER) ASC LIMIT 1;");
    
    statement.SetReadOnly(true);
    statement.Execute();

    if (statement.IsDone())
    {
      return false;
    }
    else
    {
      internalId = statement.ReadInteger64(0);
      return true;
    }
  }

    
  bool PostgreSQLIndex::SelectPatientToRecycle(int64_t& internalId /*out*/,
                                               DatabaseManager& manager,
                                               int64_t patientIdToAvoid)
  {
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "SELECT r.internalId "
      "FROM Resources r "
      "JOIN Metadata m ON r.internalId = m.id AND m.type = 19 " // 19 = PatientRecyclingOrder
      "WHERE r.resourceType = 0 "
      "  AND r.internalId != ${id} "
      "  AND NOT EXISTS "
      "   (SELECT 1 FROM Metadata m "
      "    WHERE m.id = r.internalId AND m.type = 18 AND m.value = 'true') "  // 18 = IsProtected
      " ORDER BY CAST(m.value AS INTEGER) ASC LIMIT 1;");

    statement.SetReadOnly(true);
    statement.SetParameterType("id", ValueType_Integer64);

    Dictionary args;
    args.SetIntegerValue("id", patientIdToAvoid);

    statement.Execute(args);

    if (statement.IsDone())
    {
      return false;
    }
    else
    {
      internalId = statement.ReadInteger64(0);
      return true;
    }
  }


  bool PostgreSQLIndex::HasPerformDbHousekeeping()
  {
    return !IsReadOnly(); // Don't start HK on ReadOnly databases !
  }

  void PostgreSQLIndex::PerformDbHousekeeping(DatabaseManager& manager)
  {
    // Compute the missing child count (table introduced in rev3)
    if (!hkHasComputedAllMissingChildCount_)
    {
      DatabaseManager::CachedStatement statement(STATEMENT_FROM_HERE, manager,
        "SELECT ComputeMissingChildCount(50)");

      statement.Execute();

      int64_t updatedCount = statement.ReadInteger64(0);
      hkHasComputedAllMissingChildCount_ = updatedCount == 0;

      if (updatedCount > 0)
      {
        LOG(INFO) << "Computed " << updatedCount << " missing ChildCount entries";
      }
      else
      {
        LOG(INFO) << "No missing ChildCount entries";
      }
    }

    // Consume the statistics delta to minimize computation when calling ComputeStatisticsReadOnly
    {
      int64_t patientsCount, studiesCount, seriesCount, instancesCount, compressedSize, uncompressedSize;
      UpdateAndGetStatistics(manager, patientsCount, studiesCount, seriesCount, instancesCount, compressedSize, uncompressedSize);
    }

    // Update the invalidated childCounts
    try
    {
      DatabaseManager::CachedStatement statement(
        STATEMENT_FROM_HERE, manager,
        "SELECT * FROM UpdateInvalidChildCounts()");
  
      statement.Execute();
      
      int64_t updatedCount = statement.ReadInteger64(0);
      if (updatedCount > 0)
      {
        LOG(INFO) << "Updated " << updatedCount << " invalid ChildCount entries";
      }
    }
    catch (Orthanc::OrthancException&)
    {
      // the statement may fail in case of temporary deadlock -> it will be retried at the next HK
      LOG(INFO) << "Updat of invalid ChildCount entries has failed (will be retried)";
    }
  }
}
