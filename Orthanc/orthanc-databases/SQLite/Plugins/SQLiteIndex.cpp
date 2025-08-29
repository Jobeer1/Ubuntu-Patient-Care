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


#include "SQLiteIndex.h"

#include "../../Framework/Common/Integer64Value.h"
#include "../../Framework/Plugins/GlobalProperties.h"
#include "../../Framework/SQLite/SQLiteDatabase.h"
#include "../../Framework/SQLite/SQLiteTransaction.h"

#include <EmbeddedResources.h>  // Auto-generated file

#include <Compatibility.h>  // For std::unique_ptr<>
#include <Logging.h>
#include <OrthancException.h>

namespace OrthancDatabases
{
  IDatabaseFactory* SQLiteIndex::CreateDatabaseFactory()
  {
    class Factory : public IDatabaseFactory
    {
    private:
      std::string  path_;
      bool         fast_;
      
    public:
      Factory(const std::string& path,
              bool fast) :
        path_(path),
        fast_(fast)
      {
      }
      
      virtual IDatabase* Open() ORTHANC_OVERRIDE
      {
        std::unique_ptr<SQLiteDatabase> db(new SQLiteDatabase);

        if (path_.empty())
        {
          db->OpenInMemory();
        }
        else
        {
          db->Open(path_);
        }

        db->Execute("PRAGMA ENCODING=\"UTF-8\";");

        if (fast_)
        {
          // Performance tuning of SQLite with PRAGMAs
          // http://www.sqlite.org/pragma.html
          db->Execute("PRAGMA SYNCHRONOUS=NORMAL;");
          db->Execute("PRAGMA JOURNAL_MODE=WAL;");
          db->Execute("PRAGMA LOCKING_MODE=EXCLUSIVE;");
          db->Execute("PRAGMA WAL_AUTOCHECKPOINT=1000;");
          //db->Execute("PRAGMA TEMP_STORE=memory");
        }

        return db.release();
      }
    };

    return new Factory(path_, fast_);
  }


  void SQLiteIndex::ConfigureDatabase(DatabaseManager& manager,
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

    {
      DatabaseManager::Transaction t(manager, TransactionType_ReadWrite);

      if (!t.GetDatabaseTransaction().DoesTableExist("Resources"))
      {
        std::string query;

        Orthanc::EmbeddedResources::GetFileResource
          (query, Orthanc::EmbeddedResources::SQLITE_PREPARE_INDEX);

        t.GetDatabaseTransaction().ExecuteMultiLines(query);

        SetGlobalIntegerProperty(manager, MISSING_SERVER_IDENTIFIER, Orthanc::GlobalProperty_DatabaseSchemaVersion, expectedVersion);
        SetGlobalIntegerProperty(manager, MISSING_SERVER_IDENTIFIER, Orthanc::GlobalProperty_DatabasePatchLevel, 1);
      }
          
      t.Commit();
    }

    {
      DatabaseManager::Transaction t(manager, TransactionType_ReadWrite);

      if (!t.GetDatabaseTransaction().DoesTableExist("Resources"))
      {
        LOG(ERROR) << "Corrupted SQLite database";
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);        
      }

      int version = 0;
      if (!LookupGlobalIntegerProperty(version, manager, MISSING_SERVER_IDENTIFIER, Orthanc::GlobalProperty_DatabaseSchemaVersion) ||
          version != 6)
      {
        LOG(ERROR) << "SQLite plugin is incompatible with database schema version: " << version;
        throw Orthanc::OrthancException(Orthanc::ErrorCode_Database);        
      }

      int revision;
      if (!LookupGlobalIntegerProperty(revision, manager, MISSING_SERVER_IDENTIFIER, Orthanc::GlobalProperty_DatabasePatchLevel))
      {
        revision = 1;
        SetGlobalIntegerProperty(manager, MISSING_SERVER_IDENTIFIER, Orthanc::GlobalProperty_DatabasePatchLevel, revision);
      }

      // install customData
      if (!LookupGlobalIntegerProperty(revision, manager, MISSING_SERVER_IDENTIFIER, Orthanc::GlobalProperty_DatabasePatchLevel)
          || revision == 1)
      {
        std::string query;

        Orthanc::EmbeddedResources::GetFileResource
          (query, Orthanc::EmbeddedResources::SQLITE_INSTALL_CUSTOM_DATA);

        t.GetDatabaseTransaction().ExecuteMultiLines(query);

        revision = 2;
        SetGlobalIntegerProperty(manager, MISSING_SERVER_IDENTIFIER, Orthanc::GlobalProperty_DatabasePatchLevel, revision);
      }

      if (revision != 2)
      {
        LOG(ERROR) << "SQLite plugin is incompatible with database schema revision: " << revision;
        throw Orthanc::OrthancException(Orthanc::ErrorCode_Database);        
      }      
          
      t.Commit();
    }

    {
      DatabaseManager::Transaction t(manager, TransactionType_ReadWrite);

      if (!t.GetDatabaseTransaction().DoesTableExist("ServerProperties"))
      {
        t.GetDatabaseTransaction().ExecuteMultiLines("CREATE TABLE ServerProperties(server TEXT, "
                                                     "property INTEGER, value TEXT, PRIMARY KEY(server, property))");
      }

      t.Commit();
    }    

    {
      DatabaseManager::Transaction t(manager, TransactionType_ReadWrite);

      if (!t.GetDatabaseTransaction().DoesTableExist("Labels"))
      {
        t.GetDatabaseTransaction().ExecuteMultiLines(
          "CREATE TABLE Labels("
          "  id INTEGER REFERENCES Resources(internalId) ON DELETE CASCADE,"
          "  label TEXT NOT NULL,"
          "  PRIMARY KEY(id, label));"
          "CREATE INDEX LabelsIndex1 ON Labels(id);"
          "CREATE INDEX LabelsIndex2 ON Labels(label);");
      }

      t.Commit();
    }    
  }


  SQLiteIndex::SQLiteIndex(OrthancPluginContext* context,
                           const std::string& path) :
    IndexBackend(context, false /* not read-only */, false),
    path_(path),
    fast_(true)
  {
    if (path.empty())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
  }


  SQLiteIndex::SQLiteIndex(OrthancPluginContext* context) :
    IndexBackend(context, false /* not read-only */, false),
    fast_(true)
  {
  }


  int64_t SQLiteIndex::CreateResource(DatabaseManager& manager,
                                      const char* publicId,
                                      OrthancPluginResourceType type)
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

    return dynamic_cast<SQLiteDatabase&>(statement.GetDatabase()).GetLastInsertRowId();
  }


  int64_t SQLiteIndex::GetLastChangeIndex(DatabaseManager& manager)
  {
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "SELECT seq FROM sqlite_sequence WHERE name='Changes'");

    statement.SetReadOnly(true);
    statement.Execute();
    
    if (statement.IsDone())
    {
      // No change has been recorded so far in the database
      return 0;
    }
    else
    {
      const IValue& value = statement.GetResultField(0);
      
      switch (value.GetType())
      {
        case ValueType_Integer64:
          return dynamic_cast<const Integer64Value&>(value).GetValue();
          
        default:
          //LOG(ERROR) << value.Format();
          throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
      }
    }
  }


#if ORTHANC_PLUGINS_VERSION_IS_ABOVE(1, 12, 5)
  bool SQLiteIndex::HasFindSupport() const
  {
    return false;
  }
#endif


#if ORTHANC_PLUGINS_VERSION_IS_ABOVE(1, 12, 5)
  void SQLiteIndex::ExecuteFind(Orthanc::DatabasePluginMessages::TransactionResponse& response,
                                DatabaseManager& manager,
                                const Orthanc::DatabasePluginMessages::Find_Request& request)
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
  }

  void SQLiteIndex::ExecuteCount(Orthanc::DatabasePluginMessages::TransactionResponse& response,
                                 DatabaseManager& manager,
                                 const Orthanc::DatabasePluginMessages::Find_Request& request)
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
  }
#endif
}
