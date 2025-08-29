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


#include "IndexBackend.h"

#include "../Common/Utf8StringValue.h"
#include "DatabaseBackendAdapterV2.h"
#include "DatabaseBackendAdapterV3.h"
#include "DatabaseBackendAdapterV4.h"
#include "GlobalProperties.h"

#include <Compatibility.h>  // For std::unique_ptr<>
#include <Logging.h>
#include <OrthancException.h>
#include <Toolbox.h>

#include <boost/algorithm/string/join.hpp>


namespace OrthancDatabases
{
  static std::string ConvertWildcardToLike(const std::string& query)
  {
    std::string s = query;

    for (size_t i = 0; i < s.size(); i++)
    {
      if (s[i] == '*')
      {
        s[i] = '%';
      }
      else if (s[i] == '?')
      {
        s[i] = '_';
      }
    }

    // TODO Escape underscores and percents

    return s;
  }


#if ORTHANC_PLUGINS_VERSION_IS_ABOVE(1, 12, 5)
  static std::string JoinChanges(const std::set<uint32_t>& changeTypes)
  {
    std::set<std::string> changeTypesString;
    for (std::set<uint32_t>::const_iterator it = changeTypes.begin(); it != changeTypes.end(); ++it)
    {
      changeTypesString.insert(boost::lexical_cast<std::string>(*it));
    }

    std::string joinedChangesTypes;
    Orthanc::Toolbox::JoinStrings(joinedChangesTypes, changeTypesString, ", ");

    return joinedChangesTypes;
  }
#endif  


  template <typename T>
  static void ReadListOfIntegers(std::list<T>& target,
                                 DatabaseManager::CachedStatement& statement,
                                 const Dictionary& args)
  {
    statement.Execute(args);
      
    target.clear();

    if (!statement.IsDone())
    {
      if (statement.GetResultFieldsCount() != 1)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
      }
      
      statement.SetResultFieldType(0, ValueType_Integer64);

      while (!statement.IsDone())
      {
        target.push_back(static_cast<T>(statement.ReadInteger64(0)));
        statement.Next();
      }
    }
  }

    
  static void ReadListOfStrings(std::list<std::string>& target,
                                DatabaseManager::CachedStatement& statement,
                                const Dictionary& args)
  {
    statement.Execute(args);

    target.clear();
      
    if (!statement.IsDone())
    {
      if (statement.GetResultFieldsCount() != 1)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
      }
      
      while (!statement.IsDone())
      {
        target.push_back(statement.ReadString(0));
        statement.Next();
      }
    }
  }


  namespace  // Anonymous namespace to avoid clashes between compilation modules
  {
    struct Change
    {
      int64_t       seq_;
      int32_t       changeType_;
      OrthancPluginResourceType       resourceType_;
      std::string   publicId_;
      std::string   changeDate_;

      Change(int64_t seq, int32_t changeType, OrthancPluginResourceType resourceType, const std::string& publicId, const std::string& changeDate)
      : seq_(seq), changeType_(changeType), resourceType_(resourceType), publicId_(publicId), changeDate_(changeDate)
      {
      }
    };
  }


  void IndexBackend::ReadChangesInternal(IDatabaseBackendOutput& output,
                                         bool& done,
                                         DatabaseManager& manager,
                                         DatabaseManager::CachedStatement& statement,
                                         const Dictionary& args,
                                         uint32_t limit,
                                         bool returnFirstResults)
  {
    statement.Execute(args);

    std::list<Change> changes;
    while (!statement.IsDone())
    {
      changes.push_back(Change(
        statement.ReadInteger64(0),
        statement.ReadInteger32(1),
        static_cast<OrthancPluginResourceType>(statement.ReadInteger32(2)),
        statement.ReadString(3),
        statement.ReadString(4)
      ));

      statement.Next();
    }
    
    done = changes.size() <= limit;  // 'done' means we have returned all requested changes

    // if we have retrieved more changes than requested -> cleanup
    if (changes.size() > limit)
    {
      assert(changes.size() == limit+1); // the statement should only request 1 element more

      if (returnFirstResults)
      {
        changes.pop_back();
      }
      else
      {
        changes.pop_front();
      }
    }

    for (std::list<Change>::const_iterator it = changes.begin(); it != changes.end(); ++it)
    {
      output.AnswerChange(it->seq_, it->changeType_, it->resourceType_, it->publicId_, it->changeDate_);
    }
  }


  void IndexBackend::ReadExportedResourcesInternal(IDatabaseBackendOutput& output,
                                                   bool& done,
                                                   DatabaseManager::CachedStatement& statement,
                                                   const Dictionary& args,
                                                   uint32_t limit)
  {
    statement.Execute(args);

    uint32_t count = 0;

    while (count < limit &&
           !statement.IsDone())
    {
      int64_t seq = statement.ReadInteger64(0);
      OrthancPluginResourceType resourceType =
        static_cast<OrthancPluginResourceType>(statement.ReadInteger32(1));
      std::string publicId = statement.ReadString(2);

      output.AnswerExportedResource(seq, 
                                    resourceType,
                                    publicId,
                                    statement.ReadString(3),  // modality
                                    statement.ReadString(8),  // date
                                    statement.ReadString(4),  // patient ID
                                    statement.ReadString(5),  // study instance UID
                                    statement.ReadString(6),  // series instance UID
                                    statement.ReadString(7)); // sop instance UID
      
      statement.Next();
      count++;
    }

    done = (count < limit ||
            statement.IsDone());
  }

  void IndexBackend::ClearRemainingAncestor(DatabaseManager& manager)
  {
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "DELETE FROM RemainingAncestor");

    statement.Execute();
  }



  void IndexBackend::ClearDeletedFiles(DatabaseManager& manager)
  {
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "DELETE FROM DeletedFiles");

    statement.Execute();
  }
    

  void IndexBackend::ClearDeletedResources(DatabaseManager& manager)
  {
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "DELETE FROM DeletedResources");

    statement.Execute();
  }
    

  void IndexBackend::SignalDeletedFiles(IDatabaseBackendOutput& output,
                                        DatabaseManager& manager)
  {
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "SELECT uuid, fileType, uncompressedSize, uncompressedHash, compressionType, "
      "compressedSize, compressedHash, revision, customData FROM DeletedFiles");

    statement.SetReadOnly(true);
    statement.Execute();

    statement.SetResultFieldType(8, ValueType_BinaryString);

    while (!statement.IsDone())
    {
      output.SignalDeletedAttachment(statement.ReadString(0),
                                     statement.ReadInteger32(1),
                                     statement.ReadInteger64(2),
                                     statement.ReadString(3),
                                     statement.ReadInteger32(4),
                                     statement.ReadInteger64(5),
                                     statement.ReadString(6),
                                     statement.ReadStringOrNull(8));
      
      statement.Next();
    }
  }


  void IndexBackend::SignalDeletedResources(IDatabaseBackendOutput& output,
                                            DatabaseManager& manager)
  {
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "SELECT resourceType, publicId FROM DeletedResources");

    statement.SetReadOnly(true);
    statement.Execute();

    while (!statement.IsDone())
    {
      output.SignalDeletedResource(
        statement.ReadString(1),
        static_cast<OrthancPluginResourceType>(statement.ReadInteger32(0)));

      statement.Next();
    }
  }


  IndexBackend::IndexBackend(OrthancPluginContext* context,
                             bool readOnly, 
                             bool allowInconsistentChildCounts) :
    context_(context),
    readOnly_(readOnly),
    allowInconsistentChildCounts_(allowInconsistentChildCounts)
  {
  }


  void IndexBackend::SetOutputFactory(IDatabaseBackendOutput::IFactory* factory)
  {
    boost::unique_lock<boost::shared_mutex> lock(outputFactoryMutex_);
      
    if (factory == NULL)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_NullPointer);
    }
    else if (outputFactory_.get() != NULL)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
    }
    else
    {
      outputFactory_.reset(factory);
    }
  }


  IDatabaseBackendOutput* IndexBackend::CreateOutput()
  {
    boost::shared_lock<boost::shared_mutex> lock(outputFactoryMutex_);
      
    if (outputFactory_.get() == NULL)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
    }
    else
    {
      return outputFactory_->CreateOutput();
    }
  }

  static void ExecuteAddAttachment(DatabaseManager& manager,
                                   int64_t id,
                                   const char* uuid,
                                   int32_t     contentType,
                                   uint64_t    uncompressedSize,
                                   const char* uncompressedHash,
                                   int32_t     compressionType,
                                   uint64_t    compressedSize,
                                   const char* compressedHash,
                                   const void* customData,
                                   size_t      customDataSize,
                                   int64_t     revision)
  {
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "INSERT INTO AttachedFiles VALUES(${id}, ${type}, ${uuid}, ${compressed}, "
      "${uncompressed}, ${compression}, ${hash}, ${hash-compressed}, ${revision}, ${custom-data})");

    Dictionary args;

    statement.SetParameterType("id", ValueType_Integer64);
    statement.SetParameterType("type", ValueType_Integer64);
    statement.SetParameterType("uuid", ValueType_Utf8String);
    statement.SetParameterType("compressed", ValueType_Integer64);
    statement.SetParameterType("uncompressed", ValueType_Integer64);
    statement.SetParameterType("compression", ValueType_Integer64);
    statement.SetParameterType("hash", ValueType_Utf8String);
    statement.SetParameterType("hash-compressed", ValueType_Utf8String);
    statement.SetParameterType("revision", ValueType_Integer64);
    statement.SetParameterType("custom-data", ValueType_BinaryString);

    args.SetIntegerValue("id", id);
    args.SetIntegerValue("type", contentType);
    args.SetUtf8Value("uuid", uuid);
    args.SetIntegerValue("compressed", compressedSize);
    args.SetIntegerValue("uncompressed", uncompressedSize);
    args.SetIntegerValue("compression", compressionType);
    args.SetUtf8Value("hash", uncompressedHash);
    args.SetUtf8Value("hash-compressed", compressedHash);
    args.SetIntegerValue("revision", revision);
    args.SetBinaryValue("custom-data", customData, customDataSize);

    statement.Execute(args);
  }


  void IndexBackend::AddAttachment(DatabaseManager& manager,
                                   int64_t id,
                                   const OrthancPluginAttachment& attachment,
                                   int64_t revision)
  {
    assert(HasRevisionsSupport()); // all plugins support these features now
    ExecuteAddAttachment(manager, id, attachment.uuid, attachment.contentType, attachment.uncompressedSize, attachment.uncompressedHash,
                         attachment.compressionType, attachment.compressedSize, attachment.compressedHash, NULL, 0, revision);
  }


#if ORTHANC_PLUGINS_HAS_ATTACHMENTS_CUSTOM_DATA == 1
  void IndexBackend::AddAttachment(DatabaseManager& manager,
                                   int64_t id,
                                   const OrthancPluginAttachment& attachment,
                                   int64_t revision,
                                   const std::string& customData)
  {
    assert(HasRevisionsSupport() && HasAttachmentCustomDataSupport());
    ExecuteAddAttachment(manager, id, attachment.uuid, attachment.contentType, attachment.uncompressedSize, attachment.uncompressedHash,
                         attachment.compressionType, attachment.compressedSize, attachment.compressedHash,
                         customData.empty() ? NULL : customData.c_str(), customData.size(), revision);
  }
#endif


  void IndexBackend::AttachChild(DatabaseManager& manager,
                                 int64_t parent,
                                 int64_t child)
  {
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "UPDATE Resources SET parentId = ${parent} WHERE internalId = ${child}");

    statement.SetParameterType("parent", ValueType_Integer64);
    statement.SetParameterType("child", ValueType_Integer64);

    Dictionary args;
    args.SetIntegerValue("parent", parent);
    args.SetIntegerValue("child", child);
    
    statement.Execute(args);
  }

    
  void IndexBackend::ClearChanges(DatabaseManager& manager)
  {
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "DELETE FROM Changes");

    statement.Execute();
  }

    
  void IndexBackend::ClearExportedResources(DatabaseManager& manager)
  {
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "DELETE FROM ExportedResources");

    statement.Execute();
  }

    
  void IndexBackend::DeleteAttachment(IDatabaseBackendOutput& output,
                                      DatabaseManager& manager,
                                      int64_t id,
                                      int32_t attachment)
  {
    ClearDeletedFiles(manager);

    {
      DatabaseManager::CachedStatement statement(
        STATEMENT_FROM_HERE, manager,
        "DELETE FROM AttachedFiles WHERE id=${id} AND fileType=${type}");

      statement.SetParameterType("id", ValueType_Integer64);
      statement.SetParameterType("type", ValueType_Integer64);

      Dictionary args;
      args.SetIntegerValue("id", id);
      args.SetIntegerValue("type", static_cast<int>(attachment));
    
      statement.Execute(args);
    }

    SignalDeletedFiles(output, manager);
  }


  void IndexBackend::DeleteMetadata(DatabaseManager& manager,
                                    int64_t id,
                                    int32_t metadataType)
  {
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "DELETE FROM Metadata WHERE id=${id} and type=${type}");

    statement.SetParameterType("id", ValueType_Integer64);
    statement.SetParameterType("type", ValueType_Integer64);

    Dictionary args;
    args.SetIntegerValue("id", id);
    args.SetIntegerValue("type", static_cast<int>(metadataType));
    
    statement.Execute(args);
  }


  void IndexBackend::DeleteResource(IDatabaseBackendOutput& output,
                                    DatabaseManager& manager,
                                    int64_t id)
  {
    ClearDeletedFiles(manager);
    ClearDeletedResources(manager);
    ClearRemainingAncestor(manager);
      
    {
      DatabaseManager::CachedStatement statement(
        STATEMENT_FROM_HERE, manager,
        "DELETE FROM Resources WHERE internalId=${id}");

      statement.SetParameterType("id", ValueType_Integer64);

      Dictionary args;
      args.SetIntegerValue("id", id);
    
      statement.Execute(args);
    }


    {
      DatabaseManager::CachedStatement statement(
        STATEMENT_FROM_HERE, manager,
        "SELECT * FROM RemainingAncestor");
      statement.Execute();

      if (!statement.IsDone())
      {
        output.SignalRemainingAncestor(
          statement.ReadString(1),
          static_cast<OrthancPluginResourceType>(statement.ReadInteger32(0)));
          
        // There is at most 1 remaining ancestor
        assert((statement.Next(), statement.IsDone()));
      }
    }

    SignalDeletedFiles(output, manager);
    SignalDeletedResources(output, manager);

  }


  void IndexBackend::GetAllInternalIds(std::list<int64_t>& target,
                                       DatabaseManager& manager,
                                       OrthancPluginResourceType resourceType)
  {
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "SELECT internalId FROM Resources WHERE resourceType=${type}");
      
    statement.SetReadOnly(true);
    statement.SetParameterType("type", ValueType_Integer64);

    Dictionary args;
    args.SetIntegerValue("type", static_cast<int>(resourceType));

    ReadListOfIntegers<int64_t>(target, statement, args);
  }

    
  void IndexBackend::GetAllPublicIds(std::list<std::string>& target,
                                     DatabaseManager& manager,
                                     OrthancPluginResourceType resourceType)
  {
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "SELECT publicId FROM Resources WHERE resourceType=${type}");
      
    statement.SetReadOnly(true);
    statement.SetParameterType("type", ValueType_Integer64);

    Dictionary args;
    args.SetIntegerValue("type", static_cast<int>(resourceType));

    ReadListOfStrings(target, statement, args);
  }

    
  void IndexBackend::GetAllPublicIds(std::list<std::string>& target,
                                     DatabaseManager& manager,
                                     OrthancPluginResourceType resourceType,
                                     int64_t since,
                                     uint32_t limit)
  {
    std::string suffix;
    if (manager.GetDialect() == Dialect_MSSQL)
    {
      suffix = "OFFSET ${since} ROWS FETCH FIRST ${limit} ROWS ONLY";
    }
    else if (limit > 0)
    {
      suffix = "LIMIT ${limit} OFFSET ${since}";
    }
    
    std::string sql = "SELECT publicId FROM (SELECT publicId FROM Resources "
      "WHERE resourceType=${type}) AS tmp ORDER BY tmp.publicId " + suffix;

    DatabaseManager::CachedStatement statement(STATEMENT_FROM_HERE_DYNAMIC(sql), manager, sql);
      
    statement.SetReadOnly(true);

    Dictionary args;

    statement.SetParameterType("type", ValueType_Integer64);
    args.SetIntegerValue("type", static_cast<int>(resourceType));
    
    if (limit > 0)
    {
      statement.SetParameterType("limit", ValueType_Integer64);
      statement.SetParameterType("since", ValueType_Integer64);
      args.SetIntegerValue("limit", limit);
      args.SetIntegerValue("since", since);
    }

    ReadListOfStrings(target, statement, args);
  }

  void IndexBackend::GetChanges(IDatabaseBackendOutput& output,
                                bool& done /*out*/,
                                DatabaseManager& manager,
                                int64_t since,
                                uint32_t limit)
  {
    std::set<uint32_t> changeTypes;
    GetChangesExtended(output, done, manager, since, -1, changeTypes, limit);
  }

  /* Use GetOutput().AnswerChange() */
  void IndexBackend::GetChangesExtended(IDatabaseBackendOutput& output,
                                        bool& done /*out*/,
                                        DatabaseManager& manager,
                                        int64_t since,
                                        int64_t to,
                                        const std::set<uint32_t>& changeTypes,
                                        uint32_t limit)
  {
    std::string limitSuffix;
    if (manager.GetDialect() == Dialect_MSSQL)
    {
      limitSuffix = "OFFSET 0 ROWS FETCH FIRST ${limit} ROWS ONLY";
    }
    else
    {
      limitSuffix = "LIMIT ${limit}";
    }
    
    std::vector<std::string> filters;
    bool hasSince = false;
    bool hasTo = false;

    if (since > 0)
    {
      hasSince = true;
      filters.push_back("seq>${since}");
    }
    if (to != -1)
    {
      hasTo = true;
      filters.push_back("seq<=${to}");
    }
#if ORTHANC_PLUGINS_HAS_CHANGES_EXTENDED == 1
    if (changeTypes.size() > 0)
    {
      filters.push_back("changeType IN (" + JoinChanges(changeTypes) + ") ");
    }
#endif

    std::string filtersString;
    if (filters.size() > 0)
    {
      filtersString = "WHERE " + boost::algorithm::join(filters, " AND ");
    }

    std::string sql;
    bool returnFirstResults;
    if (hasTo && !hasSince)
    {
      // in this case, we want the largest values but we want them ordered in ascending order
      sql = "SELECT * FROM (SELECT Changes.seq, Changes.changeType, Changes.resourceType, Resources.publicId, Changes.date "
            "FROM Changes INNER JOIN Resources "
            "ON Changes.internalId = Resources.internalId " + filtersString + " ORDER BY seq DESC " + limitSuffix + 
            ") AS FilteredChanges ORDER BY seq ASC";

      returnFirstResults = false;
    }
    else
    {
      // default query: we want the smallest values ordered in ascending order
      sql = "SELECT Changes.seq, Changes.changeType, Changes.resourceType, Resources.publicId, "
            "Changes.date FROM Changes INNER JOIN Resources "
            "ON Changes.internalId = Resources.internalId " + filtersString + " ORDER BY seq ASC " + limitSuffix;
      returnFirstResults = true;
    }

    DatabaseManager::CachedStatement statement(STATEMENT_FROM_HERE_DYNAMIC(sql), manager, sql);
    statement.SetReadOnly(true);
    Dictionary args;

    statement.SetParameterType("limit", ValueType_Integer64);
    args.SetIntegerValue("limit", limit + 1);  // we take limit+1 because we use the +1 to know if "Done" must be set to true

    if (hasSince)
    {
      statement.SetParameterType("since", ValueType_Integer64);
      args.SetIntegerValue("since", since);
    }

    if (hasTo)
    {
      statement.SetParameterType("to", ValueType_Integer64);
      args.SetIntegerValue("to", to);
    }

    ReadChangesInternal(output, done, manager, statement, args, limit, returnFirstResults);
  }

    
  void IndexBackend::GetChildrenInternalId(std::list<int64_t>& target /*out*/,
                                           DatabaseManager& manager,
                                           int64_t id)
  {
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "SELECT a.internalId FROM Resources AS a, Resources AS b  "
      "WHERE a.parentId = b.internalId AND b.internalId = ${id}");
      
    statement.SetReadOnly(true);
    statement.SetParameterType("id", ValueType_Integer64);

    Dictionary args;
    args.SetIntegerValue("id", id);

    ReadListOfIntegers<int64_t>(target, statement, args);
  }

    
  void IndexBackend::GetChildrenPublicId(std::list<std::string>& target /*out*/,
                                         DatabaseManager& manager,
                                         int64_t id)
  {
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "SELECT a.publicId FROM Resources AS a, Resources AS b  "
      "WHERE a.parentId = b.internalId AND b.internalId = ${id}");
      
    statement.SetReadOnly(true);
    statement.SetParameterType("id", ValueType_Integer64);

    Dictionary args;
    args.SetIntegerValue("id", id);

    ReadListOfStrings(target, statement, args);
  }

    
  /* Use GetOutput().AnswerExportedResource() */
  void IndexBackend::GetExportedResources(IDatabaseBackendOutput& output,
                                          bool& done /*out*/,
                                          DatabaseManager& manager,
                                          int64_t since,
                                          uint32_t limit)
  {
    std::string suffix;
    if (manager.GetDialect() == Dialect_MSSQL)
    {
      suffix = "OFFSET 0 ROWS FETCH FIRST ${limit} ROWS ONLY";
    }
    else
    {
      suffix = "LIMIT ${limit}";
    }
    
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "SELECT * FROM ExportedResources WHERE seq>${since} ORDER BY seq " + suffix);
    
    statement.SetReadOnly(true);
    statement.SetParameterType("limit", ValueType_Integer64);
    statement.SetParameterType("since", ValueType_Integer64);

    Dictionary args;
    args.SetIntegerValue("limit", limit + 1);
    args.SetIntegerValue("since", since);

    ReadExportedResourcesInternal(output, done, statement, args, limit);
  }

    
  /* Use GetOutput().AnswerChange() */
  void IndexBackend::GetLastChange(IDatabaseBackendOutput& output,
                                   DatabaseManager& manager)
  {
    std::string suffix;
    if (manager.GetDialect() == Dialect_MSSQL)
    {
      suffix = "OFFSET 0 ROWS FETCH FIRST 1 ROWS ONLY";
    }
    else
    {
      suffix = "LIMIT 1";
    }

    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "SELECT Changes.seq, Changes.changeType, Changes.resourceType, Resources.publicId, "
      "Changes.date FROM Changes INNER JOIN Resources "
      "ON Changes.internalId = Resources.internalId ORDER BY seq DESC " + suffix);

    statement.SetReadOnly(true);
      
    Dictionary args;

    bool done;  // Ignored
    ReadChangesInternal(output, done, manager, statement, args, 1, true);
  }

    
  /* Use GetOutput().AnswerExportedResource() */
  void IndexBackend::GetLastExportedResource(IDatabaseBackendOutput& output,
                                             DatabaseManager& manager)
  {
    std::string suffix;
    if (manager.GetDialect() == Dialect_MSSQL)
    {
      suffix = "OFFSET 0 ROWS FETCH FIRST 1 ROWS ONLY";
    }
    else
    {
      suffix = "LIMIT 1";
    }

    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "SELECT * FROM ExportedResources ORDER BY seq DESC " + suffix);

    statement.SetReadOnly(true);
      
    Dictionary args;

    bool done;  // Ignored
    ReadExportedResourcesInternal(output, done, statement, args, 1);
  }

    
  /* Use GetOutput().AnswerDicomTag() */
  void IndexBackend::GetMainDicomTags(IDatabaseBackendOutput& output,
                                      DatabaseManager& manager,
                                      int64_t id)
  {
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "SELECT * FROM MainDicomTags WHERE id=${id}");

    statement.SetReadOnly(true);
    statement.SetParameterType("id", ValueType_Integer64);

    Dictionary args;
    args.SetIntegerValue("id", id);

    statement.Execute(args);

    while (!statement.IsDone())
    {
      output.AnswerDicomTag(static_cast<uint16_t>(statement.ReadInteger64(1)),
                            static_cast<uint16_t>(statement.ReadInteger64(2)),
                            statement.ReadString(3));
      statement.Next();
    }
  }

    
  std::string IndexBackend::GetPublicId(DatabaseManager& manager,
                                        int64_t resourceId)
  {
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "SELECT publicId FROM Resources WHERE internalId=${id}");

    statement.SetReadOnly(true);
    statement.SetParameterType("id", ValueType_Integer64);

    Dictionary args;
    args.SetIntegerValue("id", resourceId);

    statement.Execute(args);

    if (statement.IsDone())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_UnknownResource, "No public id found for internal id");
    }
    else
    {
      return statement.ReadString(0);
    }
  }

    
  uint64_t IndexBackend::GetResourcesCount(DatabaseManager& manager,
                                           OrthancPluginResourceType resourceType)
  {
    std::unique_ptr<DatabaseManager::CachedStatement> statement;

    switch (manager.GetDialect())
    {
      case Dialect_MySQL:
        statement.reset(new DatabaseManager::CachedStatement(
                          STATEMENT_FROM_HERE, manager,
                          "SELECT CAST(COUNT(*) AS UNSIGNED INT) FROM Resources WHERE resourceType=${type}"));
        break;

      case Dialect_PostgreSQL:
        statement.reset(new DatabaseManager::CachedStatement(
                          STATEMENT_FROM_HERE, manager,
                          "SELECT CAST(COUNT(*) AS BIGINT) FROM Resources WHERE resourceType=${type}"));
        break;

      case Dialect_MSSQL:
      case Dialect_SQLite:
        statement.reset(new DatabaseManager::CachedStatement(
                          STATEMENT_FROM_HERE, manager,
                          "SELECT COUNT(*) FROM Resources WHERE resourceType=${type}"));
        break;

      default:
        throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
    }

    statement->SetReadOnly(true);
    statement->SetParameterType("type", ValueType_Integer64);

    Dictionary args;
    args.SetIntegerValue("type", resourceType);

    statement->Execute(args);

    return static_cast<uint64_t>(statement->ReadInteger64(0));
  }

    
  OrthancPluginResourceType IndexBackend::GetResourceType(DatabaseManager& manager,
                                                          int64_t resourceId)
  {
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "SELECT resourceType FROM Resources WHERE internalId=${id}");

    statement.SetReadOnly(true);
    statement.SetParameterType("id", ValueType_Integer64);

    Dictionary args;
    args.SetIntegerValue("id", resourceId);

    statement.Execute(args);

    if (statement.IsDone())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_UnknownResource, "No resource type found for internal id");
    }
    else
    {
      return static_cast<OrthancPluginResourceType>(statement.ReadInteger32(0));
    }
  }

    
  uint64_t IndexBackend::GetTotalCompressedSize(DatabaseManager& manager)
  {
    std::unique_ptr<DatabaseManager::CachedStatement> statement;

    // NB: "COALESCE" is used to replace "NULL" by "0" if the number of rows is empty

    switch (manager.GetDialect())
    {
      case Dialect_MySQL:
        statement.reset(new DatabaseManager::CachedStatement(
                          STATEMENT_FROM_HERE, manager,
                          "SELECT CAST(COALESCE(SUM(compressedSize), 0) AS UNSIGNED INTEGER) FROM AttachedFiles"));
        break;
        
      case Dialect_PostgreSQL:
        statement.reset(new DatabaseManager::CachedStatement(
                          STATEMENT_FROM_HERE, manager,
                          "SELECT CAST(COALESCE(SUM(compressedSize), 0) AS BIGINT) FROM AttachedFiles"));
        break;

      case Dialect_MSSQL:
      case Dialect_SQLite:
        statement.reset(new DatabaseManager::CachedStatement(
                          STATEMENT_FROM_HERE, manager,
                          "SELECT COALESCE(SUM(compressedSize), 0) FROM AttachedFiles"));
        break;

      default:
        throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
    }

    statement->SetReadOnly(true);
    statement->Execute();

    return static_cast<uint64_t>(statement->ReadInteger64(0));
  }

    
  uint64_t IndexBackend::GetTotalUncompressedSize(DatabaseManager& manager)
  {
    std::unique_ptr<DatabaseManager::CachedStatement> statement;

    // NB: "COALESCE" is used to replace "NULL" by "0" if the number of rows is empty

    switch (manager.GetDialect())
    {
      case Dialect_MySQL:
        statement.reset(new DatabaseManager::CachedStatement(
                          STATEMENT_FROM_HERE, manager,
                          "SELECT CAST(COALESCE(SUM(uncompressedSize), 0) AS UNSIGNED INTEGER) FROM AttachedFiles"));
        break;
        
      case Dialect_PostgreSQL:
        statement.reset(new DatabaseManager::CachedStatement(
                          STATEMENT_FROM_HERE, manager,
                          "SELECT CAST(COALESCE(SUM(uncompressedSize), 0) AS BIGINT) FROM AttachedFiles"));
        break;

      case Dialect_MSSQL:
      case Dialect_SQLite:
        statement.reset(new DatabaseManager::CachedStatement(
                          STATEMENT_FROM_HERE, manager,
                          "SELECT COALESCE(SUM(uncompressedSize), 0) FROM AttachedFiles"));
        break;

      default:
        throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
    }

    statement->SetReadOnly(true);
    statement->Execute();

    return static_cast<uint64_t>(statement->ReadInteger64(0));
  }

    
  bool IndexBackend::IsExistingResource(DatabaseManager& manager,
                                        int64_t internalId)
  {
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "SELECT * FROM Resources WHERE internalId=${id}");

    statement.SetReadOnly(true);
    statement.SetParameterType("id", ValueType_Integer64);

    Dictionary args;
    args.SetIntegerValue("id", internalId);

    statement.Execute(args);

    return !statement.IsDone();
  }

    
  bool IndexBackend::IsProtectedPatient(DatabaseManager& manager,
                                        int64_t internalId)
  {
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "SELECT * FROM PatientRecyclingOrder WHERE patientId = ${id}");

    statement.SetReadOnly(true);
    statement.SetParameterType("id", ValueType_Integer64);

    Dictionary args;
    args.SetIntegerValue("id", internalId);

    statement.Execute(args);

    return statement.IsDone();
  }

    
  void IndexBackend::ListAvailableMetadata(std::list<int32_t>& target /*out*/,
                                           DatabaseManager& manager,
                                           int64_t id)
  {
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "SELECT type FROM Metadata WHERE id=${id}");
      
    statement.SetReadOnly(true);
    statement.SetParameterType("id", ValueType_Integer64);

    Dictionary args;
    args.SetIntegerValue("id", id);

    ReadListOfIntegers<int32_t>(target, statement, args);
  }

    
  void IndexBackend::ListAvailableAttachments(std::list<int32_t>& target /*out*/,
                                              DatabaseManager& manager,
                                              int64_t id)
  {
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "SELECT fileType FROM AttachedFiles WHERE id=${id}");
      
    statement.SetReadOnly(true);
    statement.SetParameterType("id", ValueType_Integer64);

    Dictionary args;
    args.SetIntegerValue("id", id);

    ReadListOfIntegers<int32_t>(target, statement, args);
  }

    
  void IndexBackend::LogChange(DatabaseManager& manager,
                               int32_t changeType,
                               int64_t resourceId,
                               OrthancPluginResourceType resourceType,
                               const char* date)
  {
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "INSERT INTO Changes VALUES(${AUTOINCREMENT} ${changeType}, ${id}, ${resourceType}, ${date})");

    statement.SetParameterType("changeType", ValueType_Integer64);
    statement.SetParameterType("id", ValueType_Integer64);
    statement.SetParameterType("resourceType", ValueType_Integer64);
    statement.SetParameterType("date", ValueType_Utf8String);

    Dictionary args;
    args.SetIntegerValue("changeType", changeType);
    args.SetIntegerValue("id", resourceId);
    args.SetIntegerValue("resourceType", resourceType);
    args.SetUtf8Value("date", date);

    statement.Execute(args);
  }

    
  void IndexBackend::LogExportedResource(DatabaseManager& manager,
                                         OrthancPluginResourceType resourceType,
                                         const char* publicId,
                                         const char* modality,
                                         const char* date,
                                         const char* patientId,
                                         const char* studyInstanceUid,
                                         const char* seriesInstanceUid,
                                         const char* sopInstanceUid)
  {
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "INSERT INTO ExportedResources VALUES(${AUTOINCREMENT} ${type}, ${publicId}, "
      "${modality}, ${patient}, ${study}, ${series}, ${instance}, ${date})");

    statement.SetParameterType("type", ValueType_Integer64);
    statement.SetParameterType("publicId", ValueType_Utf8String);
    statement.SetParameterType("modality", ValueType_Utf8String);
    statement.SetParameterType("patient", ValueType_Utf8String);
    statement.SetParameterType("study", ValueType_Utf8String);
    statement.SetParameterType("series", ValueType_Utf8String);
    statement.SetParameterType("instance", ValueType_Utf8String);
    statement.SetParameterType("date", ValueType_Utf8String);

    Dictionary args;
    args.SetIntegerValue("type", resourceType);
    args.SetUtf8Value("publicId", publicId);
    args.SetUtf8Value("modality", modality);
    args.SetUtf8Value("patient", patientId);
    args.SetUtf8Value("study", studyInstanceUid);
    args.SetUtf8Value("series", seriesInstanceUid);
    args.SetUtf8Value("instance", sopInstanceUid);
    args.SetUtf8Value("date", date);

    statement.Execute(args);
  }

    
  bool IndexBackend::LookupAttachment(IDatabaseBackendOutput& output,
                                      int64_t& revision /*out*/,
                                      DatabaseManager& manager,
                                      int64_t id,
                                      int32_t contentType)
  {
    assert(HasRevisionsSupport() && HasAttachmentCustomDataSupport()); // we have forced all v4 plugins to support both ! 
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "SELECT uuid, uncompressedSize, compressionType, compressedSize, uncompressedHash, "
      "compressedHash, revision, customData FROM AttachedFiles WHERE id=${id} AND fileType=${type}");


    statement.SetReadOnly(true);
    statement.SetParameterType("id", ValueType_Integer64);
    statement.SetParameterType("type", ValueType_Integer64);

    Dictionary args;
    args.SetIntegerValue("id", id);
    args.SetIntegerValue("type", static_cast<int>(contentType));

    statement.Execute(args);
    statement.SetResultFieldType(7, ValueType_BinaryString);

    if (statement.IsDone())
    {
      return false;
    }
    else
    {
      if (statement.GetResultField(6).GetType() == ValueType_Null)
      {
        // "NULL" can happen with a database created by PostgreSQL
        // plugin <= 3.3 (because of "ALTER TABLE AttachedFiles")
        revision = 0;
      }
      else
      {
        revision = statement.ReadInteger64(6);
      }

      std::string customData;
      customData = statement.ReadStringOrNull(7);

      output.AnswerAttachment(statement.ReadString(0),
                              contentType,
                              statement.ReadInteger64(1),
                              statement.ReadString(4),
                              statement.ReadInteger32(2),
                              statement.ReadInteger64(3),
                              statement.ReadString(5),
                              customData);
      return true;
    }

  }


  static bool ReadGlobalProperty(std::string& target,
                                 DatabaseManager::CachedStatement& statement,
                                 const Dictionary& args)
  {
    statement.Execute(args);
    statement.SetResultFieldType(0, ValueType_Utf8String);

    if (statement.IsDone())
    {
      return false;
    }
    else
    {
      ValueType type = statement.GetResultField(0).GetType();

      if (type == ValueType_Null)
      {
        return false;
      }
      else if (type != ValueType_Utf8String)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_Database);
      }
      else
      {
        target = dynamic_cast<const Utf8StringValue&>(statement.GetResultField(0)).GetContent();
        return true;
      }
    }
  }
  
    
  bool IndexBackend::LookupGlobalProperty(std::string& target /*out*/,
                                          DatabaseManager& manager,
                                          const char* serverIdentifier,
                                          int32_t property)
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
          "SELECT value FROM GlobalProperties WHERE property=${property}");

        statement.SetReadOnly(true);
        statement.SetParameterType("property", ValueType_Integer64);

        Dictionary args;
        args.SetIntegerValue("property", property);

        return ReadGlobalProperty(target, statement, args);
      }
      else
      {
        DatabaseManager::CachedStatement statement(
          STATEMENT_FROM_HERE, manager,
          "SELECT value FROM ServerProperties WHERE server=${server} AND property=${property}");

        statement.SetReadOnly(true);
        statement.SetParameterType("server", ValueType_Utf8String);
        statement.SetParameterType("property", ValueType_Integer64);

        Dictionary args;
        args.SetUtf8Value("server", serverIdentifier);
        args.SetIntegerValue("property", property);

        return ReadGlobalProperty(target, statement, args);
      }
    }
  }

  bool IndexBackend::HasAtomicIncrementGlobalProperty()
  {
    return false; // currently only implemented in Postgres
  }

  int64_t IndexBackend::IncrementGlobalProperty(DatabaseManager& manager,
                                                const char* serverIdentifier,
                                                int32_t property,
                                                int64_t increment)
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
  }

  bool IndexBackend::HasUpdateAndGetStatistics()
  {
    return false; // currently only implemented in Postgres
  }

  void IndexBackend::UpdateAndGetStatistics(DatabaseManager& manager,
                                            int64_t& patientsCount,
                                            int64_t& studiesCount,
                                            int64_t& seriesCount,
                                            int64_t& instancesCount,
                                            int64_t& compressedSize,
                                            int64_t& uncompressedSize)
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
  }

  bool IndexBackend::HasMeasureLatency()
  {
#if ORTHANC_FRAMEWORK_VERSION_IS_ABOVE(1, 12, 2)
    return true;
#else
    return false;
#endif
  }


  void IndexBackend::LookupIdentifier(std::list<int64_t>& target /*out*/,
                                      DatabaseManager& manager,
                                      OrthancPluginResourceType resourceType,
                                      uint16_t group,
                                      uint16_t element,
                                      OrthancPluginIdentifierConstraint constraint,
                                      const char* value)
  {
    std::unique_ptr<DatabaseManager::CachedStatement> statement;

    std::string header =
      "SELECT d.id FROM DicomIdentifiers AS d, Resources AS r WHERE "
      "d.id = r.internalId AND r.resourceType=${type} AND d.tagGroup=${group} "
      "AND d.tagElement=${element} AND ";
      
    switch (constraint)
    {
      case OrthancPluginIdentifierConstraint_Equal:
        header += "d.value = ${value}";
        statement.reset(new DatabaseManager::CachedStatement(
                          STATEMENT_FROM_HERE, manager, header.c_str()));
        break;
        
      case OrthancPluginIdentifierConstraint_SmallerOrEqual:
        header += "d.value <= ${value}";
        statement.reset(new DatabaseManager::CachedStatement(
                          STATEMENT_FROM_HERE, manager, header.c_str()));
        break;
        
      case OrthancPluginIdentifierConstraint_GreaterOrEqual:
        header += "d.value >= ${value}";
        statement.reset(new DatabaseManager::CachedStatement(
                          STATEMENT_FROM_HERE, manager, header.c_str()));
        break;
        
      case OrthancPluginIdentifierConstraint_Wildcard:
        header += "d.value LIKE ${value}";
        statement.reset(new DatabaseManager::CachedStatement(
                          STATEMENT_FROM_HERE, manager, header.c_str()));
        break;
        
      default:
        throw Orthanc::OrthancException(Orthanc::ErrorCode_Database);
    }

    statement->SetReadOnly(true);
    statement->SetParameterType("type", ValueType_Integer64);
    statement->SetParameterType("group", ValueType_Integer64);
    statement->SetParameterType("element", ValueType_Integer64);
    statement->SetParameterType("value", ValueType_Utf8String);

    Dictionary args;
    args.SetIntegerValue("type", resourceType);
    args.SetIntegerValue("group", group);
    args.SetIntegerValue("element", element);

    if (constraint == OrthancPluginIdentifierConstraint_Wildcard)
    {
      args.SetUtf8Value("value", ConvertWildcardToLike(value));
    }
    else
    {
      args.SetUtf8Value("value", value);
    }

    statement->Execute(args);

    target.clear();
    while (!statement->IsDone())
    {
      target.push_back(statement->ReadInteger64(0));
      statement->Next();
    }
  }

    
  void IndexBackend::LookupIdentifierRange(std::list<int64_t>& target /*out*/,
                                           DatabaseManager& manager,
                                           OrthancPluginResourceType resourceType,
                                           uint16_t group,
                                           uint16_t element,
                                           const char* start,
                                           const char* end)
  {
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "SELECT d.id FROM DicomIdentifiers AS d, Resources AS r WHERE "
      "d.id = r.internalId AND r.resourceType=${type} AND d.tagGroup=${group} "
      "AND d.tagElement=${element} AND d.value>=${start} AND d.value<=${end}");
      
    statement.SetReadOnly(true);
    statement.SetParameterType("type", ValueType_Integer64);
    statement.SetParameterType("group", ValueType_Integer64);
    statement.SetParameterType("element", ValueType_Integer64);
    statement.SetParameterType("start", ValueType_Utf8String);
    statement.SetParameterType("end", ValueType_Utf8String);
    
    Dictionary args;
    args.SetIntegerValue("type", resourceType);
    args.SetIntegerValue("group", group);
    args.SetIntegerValue("element", element);
    args.SetUtf8Value("start", start);
    args.SetUtf8Value("end", end);

    statement.Execute(args);

    target.clear();
    while (!statement.IsDone())
    {
      target.push_back(statement.ReadInteger64(0));
      statement.Next();
    }
  }

    
  bool IndexBackend::LookupMetadata(std::string& target /*out*/,
                                    int64_t& revision /*out*/,
                                    DatabaseManager& manager,
                                    int64_t id,
                                    int32_t metadataType)
  {
    std::unique_ptr<DatabaseManager::CachedStatement> statement;

    if (HasRevisionsSupport())
    {
      statement.reset(new DatabaseManager::CachedStatement(
                        STATEMENT_FROM_HERE, manager,
                        "SELECT value, revision FROM Metadata WHERE id=${id} and type=${type}"));
    }
    else
    {
      statement.reset(new DatabaseManager::CachedStatement(
                        STATEMENT_FROM_HERE, manager,
                        "SELECT value FROM Metadata WHERE id=${id} and type=${type}"));
    }    
    
    statement->SetReadOnly(true);
    statement->SetParameterType("id", ValueType_Integer64);
    statement->SetParameterType("type", ValueType_Integer64);

    Dictionary args;
    args.SetIntegerValue("id", id);
    args.SetIntegerValue("type", metadataType);

    statement->Execute(args);

    if (statement->IsDone())
    {
      return false;
    }
    else
    {
      target = statement->ReadString(0);

      if (HasRevisionsSupport())
      {
        if (statement->GetResultField(1).GetType() == ValueType_Null)
        {
          // "NULL" can happen with a database created by PostgreSQL
          // plugin <= 3.3 (because of "ALTER TABLE AttachedFiles")
          revision = 0;
        }
        else
        {
          revision = statement->ReadInteger64(1);
        }
      }
      else
      {
        revision = 0;  // No support for revisions
      }
      
      return true;
    }
  } 

    
  bool IndexBackend::LookupParent(int64_t& parentId /*out*/,
                                  DatabaseManager& manager,
                                  int64_t resourceId)
  {
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "SELECT parentId FROM Resources WHERE internalId=${id}");

    statement.SetReadOnly(true);
    statement.SetParameterType("id", ValueType_Integer64);

    Dictionary args;
    args.SetIntegerValue("id", resourceId);

    statement.Execute(args);

    if (statement.IsDone() ||
        statement.GetResultField(0).GetType() == ValueType_Null)
    {
      return false;
    }
    else
    {
      parentId = statement.ReadInteger64(0);
      return true;
    }
  }

    
  bool IndexBackend::LookupResource(int64_t& id /*out*/,
                                    OrthancPluginResourceType& type /*out*/,
                                    DatabaseManager& manager,
                                    const char* publicId)
  {
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "SELECT internalId, resourceType FROM Resources WHERE publicId=${id}");

    statement.SetReadOnly(true);
    statement.SetParameterType("id", ValueType_Utf8String);

    Dictionary args;
    args.SetUtf8Value("id", publicId);

    statement.Execute(args);

    if (statement.IsDone())
    {
      return false;
    }
    else
    {
      id = statement.ReadInteger64(0);
      type = static_cast<OrthancPluginResourceType>(statement.ReadInteger32(1));
      return true;
    }
  }

    
  bool IndexBackend::SelectPatientToRecycle(int64_t& internalId /*out*/,
                                            DatabaseManager& manager)
  {
    std::string suffix;
    if (manager.GetDialect() == Dialect_MSSQL)
    {
      suffix = "OFFSET 0 ROWS FETCH FIRST 1 ROWS ONLY";
    }
    else
    {
      suffix = "LIMIT 1";
    }
    
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "SELECT patientId FROM PatientRecyclingOrder ORDER BY seq ASC " + suffix);
    
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

    
  bool IndexBackend::SelectPatientToRecycle(int64_t& internalId /*out*/,
                                            DatabaseManager& manager,
                                            int64_t patientIdToAvoid)
  {
    std::string suffix;
    if (manager.GetDialect() == Dialect_MSSQL)
    {
      suffix = "OFFSET 0 ROWS FETCH FIRST 1 ROWS ONLY";
    }
    else
    {
      suffix = "LIMIT 1";
    }
    
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "SELECT patientId FROM PatientRecyclingOrder "
      "WHERE patientId != ${id} ORDER BY seq ASC " + suffix);

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


  static void RunSetGlobalPropertyStatement(DatabaseManager::CachedStatement& statement,
                                            bool hasServer,
                                            bool hasValue,
                                            const char* serverIdentifier,
                                            int32_t property,
                                            const char* utf8)
  {
    Dictionary args;

    statement.SetParameterType("property", ValueType_Integer64);
    args.SetIntegerValue("property", static_cast<int>(property));

    if (hasValue)
    {
      assert(utf8 != NULL);
      statement.SetParameterType("value", ValueType_Utf8String);
      args.SetUtf8Value("value", utf8);
    }
    else
    {
      assert(utf8 == NULL);
    }        

    if (hasServer)
    {
      assert(serverIdentifier != NULL && strlen(serverIdentifier) > 0);
      statement.SetParameterType("server", ValueType_Utf8String);
      args.SetUtf8Value("server", serverIdentifier);
    }
    else
    {
      assert(serverIdentifier == NULL);
    }
      
    statement.Execute(args);
  }

    
  void IndexBackend::SetGlobalProperty(DatabaseManager& manager,
                                       const char* serverIdentifier,
                                       int32_t property,
                                       const char* utf8)
  {
    if (serverIdentifier == NULL)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_NullPointer);
    }
    else if (manager.GetDialect() == Dialect_SQLite)
    {
      bool hasServer = (strlen(serverIdentifier) != 0);

      if (hasServer)
      {
        DatabaseManager::CachedStatement statement(
          STATEMENT_FROM_HERE, manager,
          "INSERT OR REPLACE INTO ServerProperties VALUES (${server}, ${property}, ${value})");

        RunSetGlobalPropertyStatement(statement, true, true, serverIdentifier, property, utf8);
      }
      else
      {
        DatabaseManager::CachedStatement statement(
          STATEMENT_FROM_HERE, manager,
          "INSERT OR REPLACE INTO GlobalProperties VALUES (${property}, ${value})");

        RunSetGlobalPropertyStatement(statement, false, true, NULL, property, utf8);
      }
    }
    else
    {
      bool hasServer = (strlen(serverIdentifier) != 0);

      if (hasServer)
      {
        {
          DatabaseManager::CachedStatement statement(
            STATEMENT_FROM_HERE, manager,
            "DELETE FROM ServerProperties WHERE server=${server} AND property=${property}");

          RunSetGlobalPropertyStatement(statement, true, false, serverIdentifier, property, NULL);
        }

        {
          DatabaseManager::CachedStatement statement(
            STATEMENT_FROM_HERE, manager,
            "INSERT INTO ServerProperties VALUES (${server}, ${property}, ${value})");

          RunSetGlobalPropertyStatement(statement, true, true, serverIdentifier, property, utf8);
        }
      }
      else
      {
        {
          DatabaseManager::CachedStatement statement(
            STATEMENT_FROM_HERE, manager,
            "DELETE FROM GlobalProperties WHERE property=${property}");
      
          RunSetGlobalPropertyStatement(statement, false, false, NULL, property, NULL);
        }

        {
          DatabaseManager::CachedStatement statement(
            STATEMENT_FROM_HERE, manager,
            "INSERT INTO GlobalProperties VALUES (${property}, ${value})");
      
          RunSetGlobalPropertyStatement(statement, false, true, NULL, property, utf8);
        }
      }
    }
  }


  static void ExecuteSetTag(DatabaseManager::CachedStatement& statement,
                            int64_t id,
                            uint16_t group,
                            uint16_t element,
                            const char* value)
  {
    statement.SetParameterType("id", ValueType_Integer64);
    statement.SetParameterType("group", ValueType_Integer64);
    statement.SetParameterType("element", ValueType_Integer64);
    statement.SetParameterType("value", ValueType_Utf8String);
        
    Dictionary args;
    args.SetIntegerValue("id", id);
    args.SetIntegerValue("group", group);
    args.SetIntegerValue("element", element);
    args.SetUtf8Value("value", value);
        
    statement.Execute(args);
  }

    
  void IndexBackend::SetMainDicomTag(DatabaseManager& manager,
                                     int64_t id,
                                     uint16_t group,
                                     uint16_t element,
                                     const char* value)
  {
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "INSERT INTO MainDicomTags VALUES(${id}, ${group}, ${element}, ${value})");

    ExecuteSetTag(statement, id, group, element, value);
  }

    
  void IndexBackend::SetIdentifierTag(DatabaseManager& manager,
                                      int64_t id,
                                      uint16_t group,
                                      uint16_t element,
                                      const char* value)
  {
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "INSERT INTO DicomIdentifiers VALUES(${id}, ${group}, ${element}, ${value})");
        
    ExecuteSetTag(statement, id, group, element, value);
  } 


  static void ExecuteSetMetadata(DatabaseManager::CachedStatement& statement,
                                 Dictionary& args,
                                 int64_t id,
                                 int32_t metadataType,
                                 const char* value)
  {
    statement.SetParameterType("id", ValueType_Integer64);
    statement.SetParameterType("type", ValueType_Integer64);
    statement.SetParameterType("value", ValueType_Utf8String);

    args.SetIntegerValue("id", id);
    args.SetIntegerValue("type", metadataType);
    args.SetUtf8Value("value", value);

    statement.Execute(args);
  }
    
  void IndexBackend::SetMetadata(DatabaseManager& manager,
                                 int64_t id,
                                 int32_t metadataType,
                                 const char* value,
                                 int64_t revision)
  {
    if (manager.GetDialect() == Dialect_SQLite)
    {
      assert(HasRevisionsSupport());
      DatabaseManager::CachedStatement statement(
        STATEMENT_FROM_HERE, manager,
        "INSERT OR REPLACE INTO Metadata VALUES (${id}, ${type}, ${value}, ${revision})");
        
      Dictionary args;
      statement.SetParameterType("revision", ValueType_Integer64);
      args.SetIntegerValue("revision", revision);

      ExecuteSetMetadata(statement, args, id, metadataType, value);
    }
    else
    {
      {
        DatabaseManager::CachedStatement statement(
          STATEMENT_FROM_HERE, manager,
          "DELETE FROM Metadata WHERE id=${id} AND type=${type}");
        
        statement.SetParameterType("id", ValueType_Integer64);
        statement.SetParameterType("type", ValueType_Integer64);
        
        Dictionary args;
        args.SetIntegerValue("id", id);
        args.SetIntegerValue("type", metadataType);
        
        statement.Execute(args);
      }

      if (HasRevisionsSupport())
      {
        DatabaseManager::CachedStatement statement(
          STATEMENT_FROM_HERE, manager,
          "INSERT INTO Metadata VALUES (${id}, ${type}, ${value}, ${revision})");
        
        Dictionary args;
        statement.SetParameterType("revision", ValueType_Integer64);
        args.SetIntegerValue("revision", revision);
        
        ExecuteSetMetadata(statement, args, id, metadataType, value);
      }
      else
      {
        DatabaseManager::CachedStatement statement(
          STATEMENT_FROM_HERE, manager,
          "INSERT INTO Metadata VALUES (${id}, ${type}, ${value})");
        
        Dictionary args;
        ExecuteSetMetadata(statement, args, id, metadataType, value);
      }
    }
  }

    
  void IndexBackend::SetProtectedPatient(DatabaseManager& manager,
                                         int64_t internalId, 
                                         bool isProtected)
  {
    if (isProtected)
    {
      DatabaseManager::CachedStatement statement(
        STATEMENT_FROM_HERE, manager,
        "DELETE FROM PatientRecyclingOrder WHERE patientId=${id}");
        
      statement.SetParameterType("id", ValueType_Integer64);
        
      Dictionary args;
      args.SetIntegerValue("id", internalId);
        
      statement.Execute(args);
    }
    else if (IsProtectedPatient(manager, internalId))
    {
      DatabaseManager::CachedStatement statement(
        STATEMENT_FROM_HERE, manager,
        "INSERT INTO PatientRecyclingOrder VALUES(${AUTOINCREMENT} ${id})");
        
      statement.SetParameterType("id", ValueType_Integer64);
        
      Dictionary args;
      args.SetIntegerValue("id", internalId);
        
      statement.Execute(args);
    }
    else
    {
      // Nothing to do: The patient is already unprotected
    }
  }

    
  uint32_t IndexBackend::GetDatabaseVersion(DatabaseManager& manager)
  {
    // Create a read-only, explicit transaction to read the database
    // version (this was a read-write, implicit transaction in
    // PostgreSQL plugin <= 3.3 and MySQL plugin <= 3.0)
    DatabaseManager::Transaction transaction(manager, TransactionType_ReadOnly);
    
    std::string version = "unknown";
      
    if (LookupGlobalProperty(version, manager, MISSING_SERVER_IDENTIFIER, Orthanc::GlobalProperty_DatabaseSchemaVersion))
    {
      try
      {
        return boost::lexical_cast<unsigned int>(version);
      }
      catch (boost::bad_lexical_cast&)
      {
      }
    }

    LOG(ERROR) << "The database is corrupted. Drop it manually for Orthanc to recreate it";
    throw Orthanc::OrthancException(Orthanc::ErrorCode_Database);
  }

    
  /**
   * Upgrade the database to the specified version of the database
   * schema.  The upgrade script is allowed to make calls to
   * OrthancPluginReconstructMainDicomTags().
   **/
  void IndexBackend::UpgradeDatabase(DatabaseManager& manager,
                                     uint32_t  targetVersion,
                                     OrthancPluginStorageArea* storageArea)
  {
    LOG(ERROR) << "Upgrading database is not implemented by this plugin";
    throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
  }

    
  void IndexBackend::ClearMainDicomTags(DatabaseManager& manager,
                                        int64_t internalId)
  {
    {
      DatabaseManager::CachedStatement statement(
        STATEMENT_FROM_HERE, manager,
        "DELETE FROM MainDicomTags WHERE id=${id}");
        
      statement.SetParameterType("id", ValueType_Integer64);
        
      Dictionary args;
      args.SetIntegerValue("id", internalId);
        
      statement.Execute(args);
    }

    {
      DatabaseManager::CachedStatement statement(
        STATEMENT_FROM_HERE, manager,
        "DELETE FROM DicomIdentifiers WHERE id=${id}");
        
      statement.SetParameterType("id", ValueType_Integer64);
        
      Dictionary args;
      args.SetIntegerValue("id", internalId);
        
      statement.Execute(args);
    }
  }


  // For unit testing only!
  uint64_t IndexBackend::GetAllResourcesCount(DatabaseManager& manager)
  {
    std::unique_ptr<DatabaseManager::CachedStatement> statement;

    switch (manager.GetDialect())
    {
      case Dialect_MySQL:
        statement.reset(new DatabaseManager::CachedStatement(
                          STATEMENT_FROM_HERE, manager,
                          "SELECT CAST(COUNT(*) AS UNSIGNED INT) FROM Resources"));
        break;
        
      case Dialect_PostgreSQL:
        statement.reset(new DatabaseManager::CachedStatement(
                          STATEMENT_FROM_HERE, manager,
                          "SELECT CAST(COUNT(*) AS BIGINT) FROM Resources"));
        break;

      case Dialect_SQLite:
      case Dialect_MSSQL:
        statement.reset(new DatabaseManager::CachedStatement(
                          STATEMENT_FROM_HERE, manager,
                          "SELECT COUNT(*) FROM Resources"));
        break;

      default:
        throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
    }

    statement->SetReadOnly(true);
    statement->Execute();

    return static_cast<uint64_t>(statement->ReadInteger64(0));
  }    


  // For unit testing only!
  uint64_t IndexBackend::GetUnprotectedPatientsCount(DatabaseManager& manager)
  {
    std::unique_ptr<DatabaseManager::CachedStatement> statement;

    switch (manager.GetDialect())
    {
      case Dialect_MySQL:
        statement.reset(new DatabaseManager::CachedStatement(
                          STATEMENT_FROM_HERE, manager,
                          "SELECT CAST(COUNT(*) AS UNSIGNED INT) FROM PatientRecyclingOrder"));
        break;
        
      case Dialect_PostgreSQL:
        throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
        break;

      case Dialect_MSSQL:
      case Dialect_SQLite:
        statement.reset(new DatabaseManager::CachedStatement(
                          STATEMENT_FROM_HERE, manager,
                          "SELECT COUNT(*) FROM PatientRecyclingOrder"));
        break;

      default:
        throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
    }

    statement->SetReadOnly(true);
    statement->Execute();

    return static_cast<uint64_t>(statement->ReadInteger64(0));
  }    


  // For unit testing only!
  bool IndexBackend::GetParentPublicId(std::string& target,
                                       DatabaseManager& manager,
                                       int64_t id)
  {
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "SELECT a.publicId FROM Resources AS a, Resources AS b "
      "WHERE a.internalId = b.parentId AND b.internalId = ${id}");

    statement.SetReadOnly(true);
    statement.SetParameterType("id", ValueType_Integer64);

    Dictionary args;
    args.SetIntegerValue("id", id);

    statement.Execute(args);

    if (statement.IsDone())
    {
      return false;
    }
    else
    {
      target = statement.ReadString(0);
      return true;
    }
  }


  // For unit tests only!
  void IndexBackend::GetChildren(std::list<std::string>& childrenPublicIds,
                                 DatabaseManager& manager,
                                 int64_t id)
  { 
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "SELECT publicId FROM Resources WHERE parentId=${id}");
      
    statement.SetReadOnly(true);
    statement.SetParameterType("id", ValueType_Integer64);

    Dictionary args;
    args.SetIntegerValue("id", id);

    ReadListOfStrings(childrenPublicIds, statement, args);
  }


#if ORTHANC_PLUGINS_HAS_DATABASE_CONSTRAINT == 1
  class IndexBackend::LookupFormatter : public ISqlLookupFormatter
  {
  private:
    Dialect     dialect_;
    size_t      count_;
    Dictionary  dictionary_;

    static std::string FormatParameter(size_t index)
    {
      return "p" + boost::lexical_cast<std::string>(index);
    }
    
  public:
    explicit LookupFormatter(Dialect dialect) :
      dialect_(dialect),
      count_(0)
    {
    }

    virtual std::string GenerateParameter(const std::string& value)
    {
      const std::string key = FormatParameter(count_);

      count_ ++;
      dictionary_.SetUtf8Value(key, value);

      return "${" + key + "}";
    }

    virtual std::string GenerateParameter(const int64_t& value)
    {
      const std::string key = FormatParameter(count_);

      count_ ++;
      dictionary_.SetIntegerValue(key, value);

      return "${" + key + "}";
    }

    virtual std::string FormatResourceType(Orthanc::ResourceType level)
    {
      return boost::lexical_cast<std::string>(MessagesToolbox::ConvertToPlainC(level));
    }

    virtual std::string FormatWildcardEscape()
    {
      switch (dialect_)
      {
        case Dialect_MSSQL:
        case Dialect_SQLite:
        case Dialect_PostgreSQL:
          return "ESCAPE '\\'";

        case Dialect_MySQL:
          return "ESCAPE '\\\\'";

        default:
          throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
      }
    }

    virtual std::string FormatNull(const char* type)
    {
      switch (dialect_)
      {
        case Dialect_PostgreSQL:
          return std::string("NULL::") + type;
        case Dialect_MSSQL:
        case Dialect_SQLite:
        case Dialect_MySQL:
          return "NULL";

        default:
          throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
      }
    }


    virtual std::string FormatLimits(uint64_t since, uint64_t count)
    {
      std::string sql;

      switch (dialect_)
      {
        case Dialect_MSSQL:
        {
          if (count > 0 || since > 0)
          {
            std::string parameterSince = GenerateParameter(since);
            sql += " OFFSET " + parameterSince + " ROWS ";
          }
          if (count > 0)
          {
            std::string parameterCount = GenerateParameter(count);
            sql += " FETCH NEXT " + parameterCount + " ROWS ONLY ";
          }
        }; break;
        case Dialect_SQLite:
        case Dialect_PostgreSQL:
        {
          if (count > 0)
          {
            std::string parameterCount = GenerateParameter(count);
            sql += " LIMIT " + parameterCount;
          }
          if (since > 0)
          {
            std::string parameterSince = GenerateParameter(since);
            sql += " OFFSET " + parameterSince;
          }
        }; break;
        case Dialect_MySQL:
        {
          if (count > 0 && since > 0)
          {
            std::string parameterCount = GenerateParameter(count);
            std::string parameterSince = GenerateParameter(since);
            sql += " LIMIT " + parameterSince + ", " + parameterCount;
          }
          else if (count > 0)
          {
            std::string parameterCount = GenerateParameter(count);
            sql += " LIMIT " + parameterCount;
          }
          else if (since > 0)
          {
            std::string parameterSince = GenerateParameter(since);
            sql += " LIMIT " + parameterSince + ", 18446744073709551615"; // max uint64 value when you don't want any limit
          }
        }; break;
        default:
          throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
      }
      
      return sql;
    }

    virtual bool IsEscapeBrackets() const
    {
      // This was initially done at a bad location by the following changeset:
      // https://orthanc.uclouvain.be/hg/orthanc-databases/rev/389c037387ea
      return (dialect_ == Dialect_MSSQL);
    }

    virtual bool SupportsNullsLast() const
    {
      return (dialect_ == Dialect_PostgreSQL);
    }

    virtual std::string FormatIntegerCast() const
    {
      switch (dialect_)
      {
        case Dialect_MSSQL:
          return "INT";
        case Dialect_SQLite:
        case Dialect_PostgreSQL:
          return "INTEGER";
        case Dialect_MySQL:
          return "SIGNED";
        default:
          throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
      }
    }

    virtual std::string FormatFloatCast() const
    {
      switch (dialect_)
      {
        case Dialect_SQLite:
          return "REAL";
        case Dialect_MSSQL:
        case Dialect_PostgreSQL:
          return "FLOAT";
        case Dialect_MySQL:
          return "DECIMAL(10,10)";
        default:
          throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
      }
    }


    const Dictionary& GetDictionary() const
    {
      return dictionary_;
    }
  };
#endif

  
#if ORTHANC_PLUGINS_HAS_DATABASE_CONSTRAINT == 1
  // New primitive since Orthanc 1.5.2
  void IndexBackend::LookupResources(IDatabaseBackendOutput& output,
                                     DatabaseManager& manager,
                                     const DatabaseConstraints& lookup,
                                     OrthancPluginResourceType queryLevel_,
                                     const std::set<std::string>& labels,
                                     LabelsConstraint labelsConstraint,
                                     uint32_t limit,
                                     bool requestSomeInstance)
  {
    LookupFormatter formatter(manager.GetDialect());
    Orthanc::ResourceType queryLevel = MessagesToolbox::Convert(queryLevel_);
    Orthanc::ResourceType lowerLevel, upperLevel;
    ISqlLookupFormatter::GetLookupLevels(lowerLevel, upperLevel,  queryLevel, lookup);

    std::string sql;
    bool enableNewStudyCode = true;

    if (enableNewStudyCode && lowerLevel == queryLevel && upperLevel == queryLevel)
    {
      ISqlLookupFormatter::ApplySingleLevel(sql, formatter, lookup, queryLevel, labels, labelsConstraint, limit);

      if (requestSomeInstance)
      {
        // Composite query to find some instance if requested
        switch (queryLevel)
        {
          case Orthanc::ResourceType_Patient:
            sql = ("SELECT patients_studies.patients_public_id, MIN(instances.publicId) AS instances_public_id "
                    "FROM (SELECT patients.publicId AS patients_public_id, MIN(studies.internalId) AS studies_internal_id "
                          "FROM (" + sql + 
                                ") AS patients "
                                "INNER JOIN Resources studies ON studies.parentId = patients.internalId "
                                "GROUP BY patients.publicId "
                          ") AS patients_studies "
                    "INNER JOIN Resources series ON series.parentId = patients_studies.studies_internal_id "
                    "INNER JOIN Resources instances ON instances.parentId = series.internalId "
                    "GROUP BY patients_studies.patients_public_id");
            break;
          case Orthanc::ResourceType_Study:
            sql = ("SELECT studies_series.studies_public_id, MIN(instances.publicId) AS instances_public_id "
                    "FROM (SELECT studies.publicId AS studies_public_id, MIN(series.internalId) AS series_internal_id "
                          "FROM (" + sql + 
                                ") AS studies "
                                "INNER JOIN Resources series ON series.parentId = studies.internalId "
                                "GROUP BY studies.publicId "
                          ") AS studies_series "
                    "INNER JOIN Resources instances ON instances.parentId = studies_series.series_internal_id "
                    "GROUP BY studies_series.studies_public_id");
            break;
          case Orthanc::ResourceType_Series:
            sql = ("SELECT series.publicId AS series_public_id, MIN(instances.publicId) AS instances_public_id "
                          "FROM (" + sql + 
                                ") AS series "
                                "INNER JOIN Resources instances ON instances.parentId = series.internalId "
                                "GROUP BY series.publicId ");
            break;

          case Orthanc::ResourceType_Instance:
            sql = ("SELECT instances.publicId, instances.publicId FROM (" + sql + ") instances");
            break;

          default:
            throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
        }
      }
    }
    else
    {
      ISqlLookupFormatter::Apply(sql, formatter, lookup, queryLevel, labels, labelsConstraint, limit);

      if (requestSomeInstance)
      {
        // Composite query to find some instance if requested
        switch (queryLevel)
        {
          case Orthanc::ResourceType_Patient:
            sql = ("SELECT patients.publicId, MIN(instances.publicId) FROM (" + sql + ") patients "
                  "INNER JOIN Resources studies   ON studies.parentId   = patients.internalId "
                  "INNER JOIN Resources series    ON series.parentId    = studies.internalId "
                  "INNER JOIN Resources instances ON instances.parentId = series.internalId "
                  "GROUP BY patients.publicId");
            break;

          case Orthanc::ResourceType_Study:
            sql = ("SELECT studies.publicId, MIN(instances.publicId) FROM (" + sql + ") studies "
                  "INNER JOIN Resources series    ON series.parentId    = studies.internalId "
                  "INNER JOIN Resources instances ON instances.parentId = series.internalId "
                  "GROUP BY studies.publicId");                 
            break;
          case Orthanc::ResourceType_Series:
            sql = ("SELECT series.publicId, MIN(instances.publicId) FROM (" + sql + ") series "
                  "INNER JOIN Resources instances ON instances.parentId = series.internalId "
                  "GROUP BY series.publicId");
            break;

          case Orthanc::ResourceType_Instance:
            sql = ("SELECT instances.publicId, instances.publicId FROM (" + sql + ") instances");
            break;

          default:
            throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
        }
      }
    }

    Query::Parameters parametersTypes;
    formatter.GetDictionary().GetParametersType(parametersTypes);

    DatabaseManager::StandaloneStatement statement(manager, sql, parametersTypes);
    statement.Execute(formatter.GetDictionary());

    while (!statement.IsDone())
    {
      if (requestSomeInstance)
      {
        output.AnswerMatchingResource(statement.ReadString(0), statement.ReadString(1));
      }
      else
      {
        output.AnswerMatchingResource(statement.ReadString(0));
      }

      statement.Next();
    }    
  }
#endif


#if ORTHANC_PLUGINS_HAS_DATABASE_CONSTRAINT == 1
  static void ExecuteSetResourcesContentTags(
    DatabaseManager& manager,
    const std::string& table,
    const std::string& variablePrefix,
    uint32_t count,
    const OrthancPluginResourcesContentTags* tags)
  {
    std::string sql;
    Dictionary args;
    
    for (uint32_t i = 0; i < count; i++)
    {
      std::string name = variablePrefix + boost::lexical_cast<std::string>(i);

      args.SetUtf8Value(name, tags[i].value);
      
      std::string insert = ("(" + boost::lexical_cast<std::string>(tags[i].resource) + ", " +
                            boost::lexical_cast<std::string>(tags[i].group) + ", " +
                            boost::lexical_cast<std::string>(tags[i].element) + ", " +
                            "${" + name + "})");

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
      DatabaseManager::StandaloneStatement statement(manager, sql);

      for (uint32_t i = 0; i < count; i++)
      {
        statement.SetParameterType(variablePrefix + boost::lexical_cast<std::string>(i),
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
    std::string sqlRemove;  // To overwrite    
    std::string sqlInsert;
    Dictionary args;
    
    for (uint32_t i = 0; i < count; i++)
    {
      std::string name = "m" + boost::lexical_cast<std::string>(i);

      args.SetUtf8Value(name, metadata[i].value);

      std::string revisionSuffix;
      if (hasRevisionsSupport)
      {
        revisionSuffix = ", 0";
      }
      
      std::string insert = ("(" + boost::lexical_cast<std::string>(metadata[i].resource) + ", " +
                            boost::lexical_cast<std::string>(metadata[i].metadata) + ", " +
                            "${" + name + "}" + revisionSuffix + ")");

      std::string remove = ("(id=" + boost::lexical_cast<std::string>(metadata[i].resource) +
                            " AND type=" + boost::lexical_cast<std::string>(metadata[i].metadata)
                            + ")");

      if (sqlInsert.empty())
      {
        sqlInsert = "INSERT INTO Metadata VALUES " + insert;
      }
      else
      {
        sqlInsert += ", " + insert;
      }

      if (sqlRemove.empty())
      {
        sqlRemove = "DELETE FROM Metadata WHERE " + remove;
      }
      else
      {
        sqlRemove += " OR " + remove;
      }
    }

    if (!sqlRemove.empty())
    {
      DatabaseManager::StandaloneStatement statement(manager, sqlRemove);
      statement.Execute();
    }
    
    if (!sqlInsert.empty())
    {
      DatabaseManager::StandaloneStatement statement(manager, sqlInsert);

      for (uint32_t i = 0; i < count; i++)
      {
        statement.SetParameterType("m" + boost::lexical_cast<std::string>(i),
                                   ValueType_Utf8String);
      }

      statement.Execute(args);
    }
  }
#endif
  

#if ORTHANC_PLUGINS_HAS_DATABASE_CONSTRAINT == 1
  // New primitive since Orthanc 1.5.2
  void IndexBackend::SetResourcesContent(
    DatabaseManager& manager,
    uint32_t countIdentifierTags,
    const OrthancPluginResourcesContentTags* identifierTags,
    uint32_t countMainDicomTags,
    const OrthancPluginResourcesContentTags* mainDicomTags,
    uint32_t countMetadata,
    const OrthancPluginResourcesContentMetadata* metadata)
  {
    /**
     * TODO - PostgreSQL doesn't allow multiple commands in a prepared
     * statement, so we execute 3 separate commands (for identifiers,
     * main tags and metadata). Maybe MySQL does not suffer from the
     * same limitation, to check.
     **/
    
    ExecuteSetResourcesContentTags(manager, "DicomIdentifiers", "i",
                                   countIdentifierTags, identifierTags);

    ExecuteSetResourcesContentTags(manager, "MainDicomTags", "t",
                                   countMainDicomTags, mainDicomTags);
    
    ExecuteSetResourcesContentMetadata(manager, HasRevisionsSupport(), countMetadata, metadata);
  }
#endif


  // New primitive since Orthanc 1.5.2
  void IndexBackend::GetChildrenMetadata(std::list<std::string>& target,
                                         DatabaseManager& manager,
                                         int64_t resourceId,
                                         int32_t metadata)
  {
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "SELECT value FROM Metadata WHERE type=${metadata} AND "
      "id IN (SELECT internalId FROM Resources WHERE parentId=${id})");
      
    statement.SetReadOnly(true);
    statement.SetParameterType("id", ValueType_Integer64);
    statement.SetParameterType("metadata", ValueType_Integer64);

    Dictionary args;
    args.SetIntegerValue("id", static_cast<int>(resourceId));
    args.SetIntegerValue("metadata", static_cast<int>(metadata));

    ReadListOfStrings(target, statement, args);
  }


  // New primitive since Orthanc 1.5.2
  void IndexBackend::TagMostRecentPatient(DatabaseManager& manager,
                                          int64_t patient)
  {
    std::string suffix;
    if (manager.GetDialect() == Dialect_MSSQL)
    {
      suffix = "OFFSET 0 ROWS FETCH FIRST 2 ROWS ONLY";
    }
    else
    {
      suffix = "LIMIT 2";
    }

    int64_t seq;
    
    {
      DatabaseManager::CachedStatement statement(
        STATEMENT_FROM_HERE, manager,
        "SELECT * FROM PatientRecyclingOrder WHERE seq >= "
        "(SELECT seq FROM PatientRecyclingOrder WHERE patientid=${id}) ORDER BY seq " + suffix);

      statement.SetReadOnly(true);
      statement.SetParameterType("id", ValueType_Integer64);

      Dictionary args;
      args.SetIntegerValue("id", patient);

      statement.Execute(args);
      
      if (statement.IsDone())
      {
        // The patient is protected, don't add it to the recycling order
        return;
      }

      seq = statement.ReadInteger64(0);

      statement.Next();

      if (statement.IsDone())
      {
        // The patient is already at the end of the recycling order
        // (because of the "LIMIT 2" above), no need to modify the table
        return;
      }
    }

    // Delete the old position of the patient in the recycling order

    {
      DatabaseManager::CachedStatement statement(
        STATEMENT_FROM_HERE, manager,
        "DELETE FROM PatientRecyclingOrder WHERE seq=${seq}");
        
      statement.SetParameterType("seq", ValueType_Integer64);
        
      Dictionary args;
      args.SetIntegerValue("seq", seq);
        
      statement.Execute(args);
    }

    // Add the patient to the end of the recycling order

    {
      DatabaseManager::CachedStatement statement(
        STATEMENT_FROM_HERE, manager,
        "INSERT INTO PatientRecyclingOrder VALUES(${AUTOINCREMENT} ${id})");
        
      statement.SetParameterType("id", ValueType_Integer64);
        
      Dictionary args;
      args.SetIntegerValue("id", patient);
        
      statement.Execute(args);
    }
  }


// New primitive since Orthanc 1.5.4
bool IndexBackend::LookupResourceAndParent(int64_t& id,
                                           OrthancPluginResourceType& type,
                                           std::string& parentPublicId,
                                           DatabaseManager& manager,
                                           const char* publicId)
{
  DatabaseManager::CachedStatement statement(
    STATEMENT_FROM_HERE, manager,
    "SELECT resource.internalId, resource.resourceType, parent.publicId "
    "FROM Resources AS resource LEFT JOIN Resources parent ON parent.internalId=resource.parentId "
    "WHERE resource.publicId=${id}");

  statement.SetParameterType("id", ValueType_Utf8String);
        
  Dictionary args;
  args.SetUtf8Value("id", publicId);

  statement.Execute(args);

  if (statement.IsDone())
  {
    return false;
  }
  else
  {
    if (statement.GetResultFieldsCount() != 3)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
    }

    statement.SetResultFieldType(0, ValueType_Integer64);
    statement.SetResultFieldType(1, ValueType_Integer64);      
    statement.SetResultFieldType(2, ValueType_Utf8String);

    id = statement.ReadInteger64(0);
    type = static_cast<OrthancPluginResourceType>(statement.ReadInteger32(1));

    const IValue& value = statement.GetResultField(2);
      
    switch (value.GetType())
    {
      case ValueType_Null:
        parentPublicId.clear();
        break;

      case ValueType_Utf8String:
        parentPublicId = dynamic_cast<const Utf8StringValue&>(value).GetContent();
        break;

      default:
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
    }
      
    assert((statement.Next(), statement.IsDone()));
    return true;
  }
}
  

  // New primitive since Orthanc 1.5.4
  void IndexBackend::GetAllMetadata(std::map<int32_t, std::string>& result,
                                    DatabaseManager& manager,
                                    int64_t id)
  {
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "SELECT type, value FROM Metadata WHERE id=${id}");
      
    statement.SetReadOnly(true);
    statement.SetParameterType("id", ValueType_Integer64);

    Dictionary args;
    args.SetIntegerValue("id", id);

    statement.Execute(args);
      
    result.clear();

    if (!statement.IsDone())
    {
      if (statement.GetResultFieldsCount() != 2)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
      }
      
      statement.SetResultFieldType(0, ValueType_Integer64);
      statement.SetResultFieldType(1, ValueType_Utf8String);

      while (!statement.IsDone())
      {
        result[statement.ReadInteger32(0)] = statement.ReadString(1);
        statement.Next();
      }
    }
  }


#if ORTHANC_PLUGINS_HAS_DATABASE_CONSTRAINT == 1
  void IndexBackend::CreateInstanceGeneric(OrthancPluginCreateInstanceResult& result,
                                           DatabaseManager& manager,
                                           const char* hashPatient,
                                           const char* hashStudy,
                                           const char* hashSeries,
                                           const char* hashInstance)
  {
    // Check out "OrthancServer/Sources/Database/Compatibility/ICreateInstance.cpp"
    
    {
      OrthancPluginResourceType type;
      int64_t tmp;
        
      if (LookupResource(tmp, type, manager, hashInstance))
      {
        // The instance already exists
        assert(type == OrthancPluginResourceType_Instance);
        result.instanceId = tmp;
        result.isNewInstance = false;
        return;
      }
    }

    result.instanceId = CreateResource(manager, hashInstance, OrthancPluginResourceType_Instance);
    result.isNewInstance = true;

    result.isNewPatient = false;
    result.isNewStudy = false;
    result.isNewSeries = false;
    result.patientId = -1;
    result.studyId = -1;
    result.seriesId = -1;
      
    // Detect up to which level the patient/study/series/instance
    // hierarchy must be created

    {
      OrthancPluginResourceType dummy;

      if (LookupResource(result.seriesId, dummy, manager, hashSeries))
      {
        assert(dummy == OrthancPluginResourceType_Series);
        // The patient, the study and the series already exist

        bool ok = (LookupResource(result.patientId, dummy, manager, hashPatient) &&
                   LookupResource(result.studyId, dummy, manager, hashStudy));
        (void) ok;  // Remove warning about unused variable in release builds
        assert(ok);
      }
      else if (LookupResource(result.studyId, dummy, manager, hashStudy))
      {
        assert(dummy == OrthancPluginResourceType_Study);

        // New series: The patient and the study already exist
        result.isNewSeries = true;

        bool ok = LookupResource(result.patientId, dummy, manager, hashPatient);
        (void) ok;  // Remove warning about unused variable in release builds
        assert(ok);
      }
      else if (LookupResource(result.patientId, dummy, manager, hashPatient))
      {
        assert(dummy == OrthancPluginResourceType_Patient);

        // New study and series: The patient already exist
        result.isNewStudy = true;
        result.isNewSeries = true;
      }
      else
      {
        // New patient, study and series: Nothing exists
        result.isNewPatient = true;
        result.isNewStudy = true;
        result.isNewSeries = true;
      }
    }

    // Create the series if needed
    if (result.isNewSeries)
    {
      result.seriesId = CreateResource(manager, hashSeries, OrthancPluginResourceType_Series);
    }

    // Create the study if needed
    if (result.isNewStudy)
    {
      result.studyId = CreateResource(manager, hashStudy, OrthancPluginResourceType_Study);
    }

    // Create the patient if needed
    if (result.isNewPatient)
    {
      result.patientId = CreateResource(manager, hashPatient, OrthancPluginResourceType_Patient);
    }

    // Create the parent-to-child links
    AttachChild(manager, result.seriesId, result.instanceId);

    if (result.isNewSeries)
    {
      AttachChild(manager, result.studyId, result.seriesId);
    }

    if (result.isNewStudy)
    {
      AttachChild(manager, result.patientId, result.studyId);
    }

    TagMostRecentPatient(manager, result.patientId);
      
    // Sanity checks
    assert(result.patientId != -1);
    assert(result.studyId != -1);
    assert(result.seriesId != -1);
    assert(result.instanceId != -1);
  }
#endif


  void IndexBackend::AddLabel(DatabaseManager& manager,
                              int64_t resource,
                              const std::string& label)
  {
    std::unique_ptr<DatabaseManager::CachedStatement> statement;

    switch (manager.GetDialect())
    {
      case Dialect_PostgreSQL:
        statement.reset(new DatabaseManager::CachedStatement(
                          STATEMENT_FROM_HERE, manager,
                          "INSERT INTO Labels VALUES(${id}, ${label}) ON CONFLICT DO NOTHING"));
        break;

      case Dialect_SQLite:
        statement.reset(new DatabaseManager::CachedStatement(
                          STATEMENT_FROM_HERE, manager,
                          "INSERT OR IGNORE INTO Labels VALUES(${id}, ${label})"));
        break;

      case Dialect_MySQL:
        statement.reset(new DatabaseManager::CachedStatement(
                          STATEMENT_FROM_HERE, manager,
                          "INSERT IGNORE INTO Labels VALUES(${id}, ${label})"));
        break;

      default:
        throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
    }
    
    statement->SetParameterType("id", ValueType_Integer64);
    statement->SetParameterType("label", ValueType_Utf8String);

    Dictionary args;
    args.SetIntegerValue("id", resource);
    args.SetUtf8Value("label", label);

    statement->Execute(args);
  }


  void IndexBackend::RemoveLabel(DatabaseManager& manager,
                                 int64_t resource,
                                 const std::string& label)
  {
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "DELETE FROM Labels WHERE id=${id} AND label=${label}");

    statement.SetParameterType("id", ValueType_Integer64);
    statement.SetParameterType("label", ValueType_Utf8String);

    Dictionary args;
    args.SetIntegerValue("id", resource);
    args.SetUtf8Value("label", label);

    statement.Execute(args);
  }


  void IndexBackend::ListLabels(std::list<std::string>& target,
                                DatabaseManager& manager,
                                int64_t resource)
  {
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "SELECT label FROM Labels WHERE id=${id}");
      
    statement.SetReadOnly(true);
    statement.SetParameterType("id", ValueType_Integer64);

    Dictionary args;
    args.SetIntegerValue("id", resource);

    ReadListOfStrings(target, statement, args);
  }
  

  void IndexBackend::ListAllLabels(std::list<std::string>& target,
                                   DatabaseManager& manager)
  {
    DatabaseManager::CachedStatement statement(
      STATEMENT_FROM_HERE, manager,
      "SELECT DISTINCT label FROM Labels");
      
    Dictionary args;
    ReadListOfStrings(target, statement, args);
  }

  
  void IndexBackend::Register(IndexBackend* backend,
                              size_t countConnections,
                              bool useDynamicConnectionPool,
                              unsigned int maxDatabaseRetries,
                              unsigned int housekeepingDelaySeconds)
  {
    if (backend == NULL)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_NullPointer);
    }
    
    LOG(WARNING) << "The index plugin will use " << countConnections << " connection(s) to the database, "
                 << "and will retry up to " << maxDatabaseRetries << " time(s) in the case of a collision";
      
#if defined(ORTHANC_PLUGINS_VERSION_IS_ABOVE)         // Macro introduced in Orthanc 1.3.1
#  if ORTHANC_PLUGINS_VERSION_IS_ABOVE(1, 12, 0)
    if (OrthancPluginCheckVersionAdvanced(backend->GetContext(), 1, 12, 0) == 1)
    {
      DatabaseBackendAdapterV4::Register(backend, countConnections, useDynamicConnectionPool, maxDatabaseRetries, housekeepingDelaySeconds);
      return;
    }
#  endif
#endif

#if defined(ORTHANC_PLUGINS_VERSION_IS_ABOVE)         // Macro introduced in Orthanc 1.3.1
#  if ORTHANC_PLUGINS_VERSION_IS_ABOVE(1, 9, 2)
    if (OrthancPluginCheckVersionAdvanced(backend->GetContext(), 1, 9, 2) == 1)
    {
      DatabaseBackendAdapterV3::Register(backend, countConnections, maxDatabaseRetries, housekeepingDelaySeconds);
      return;
    }
#  endif
#endif

    LOG(WARNING) << "Performance warning: Your version of the Orthanc core or SDK doesn't support multiple readers/writers";
    DatabaseBackendAdapterV2::Register(backend);
  }


  bool IndexBackend::LookupGlobalIntegerProperty(int& target,
                                                 DatabaseManager& manager,
                                                 const char* serverIdentifier,
                                                 int32_t property)
  {
    std::string value;

    if (LookupGlobalProperty(value, manager, serverIdentifier, property))
    {
      try
      {
        target = boost::lexical_cast<int>(value);
        return true;
      }
      catch (boost::bad_lexical_cast&)
      {
        LOG(ERROR) << "Corrupted database";
        throw Orthanc::OrthancException(Orthanc::ErrorCode_Database);
      }      
    }
    else
    {
      return false;
    }    
  }
  

  void IndexBackend::SetGlobalIntegerProperty(DatabaseManager& manager,
                                              const char* serverIdentifier,
                                              int32_t property,
                                              int value)
  {
    std::string s = boost::lexical_cast<std::string>(value);
    SetGlobalProperty(manager, serverIdentifier, property, s.c_str());
  }
  

  void IndexBackend::Finalize()
  {
    DatabaseBackendAdapterV2::Finalize();

#if defined(ORTHANC_PLUGINS_VERSION_IS_ABOVE)         // Macro introduced in Orthanc 1.3.1
#  if ORTHANC_PLUGINS_VERSION_IS_ABOVE(1, 9, 2)
    DatabaseBackendAdapterV3::Finalize();
#  endif
#endif

#if defined(ORTHANC_PLUGINS_VERSION_IS_ABOVE)         // Macro introduced in Orthanc 1.3.1
#  if ORTHANC_PLUGINS_VERSION_IS_ABOVE(1, 12, 0)
    DatabaseBackendAdapterV4::Finalize();
#  endif
#endif
  }


  uint64_t IndexBackend::MeasureLatency(DatabaseManager& manager)
  {
#if ORTHANC_FRAMEWORK_VERSION_IS_ABOVE(1, 12, 2)
    // execute 11x the simplest statement and return the median value
    std::vector<uint64_t> measures;

    for (int i = 0; i < 11; i++)
    {
      DatabaseManager::StandaloneStatement statement(manager, "SELECT 1");

      Orthanc::Toolbox::ElapsedTimer timer;

      statement.ExecuteWithoutResult();

      measures.push_back(timer.GetElapsedMicroseconds());
    }
    
    std::sort(measures.begin(), measures.end());

    return measures[measures.size() / 2];
#else
    throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
#endif
  }


  DatabaseManager* IndexBackend::CreateSingleDatabaseManager(IDatabaseBackend& backend,
                                                             bool hasIdentifierTags,
                                                             const std::list<IdentifierTag>& identifierTags)
  {
    std::unique_ptr<DatabaseManager> manager(new DatabaseManager(backend.CreateDatabaseFactory()));
    backend.ConfigureDatabase(*manager, hasIdentifierTags, identifierTags);
    return manager.release();
  }

#if ORTHANC_PLUGINS_VERSION_IS_ABOVE(1, 12, 5)
  bool IndexBackend::HasFindSupport() const
  {
    return true;
  }
#endif


#if ORTHANC_PLUGINS_VERSION_IS_ABOVE(1, 12, 5)
  Orthanc::DatabasePluginMessages::Find_Response_ResourceContent* GetResourceContent(
                              Orthanc::DatabasePluginMessages::Find_Response* response,
                              Orthanc::DatabasePluginMessages::ResourceType level)
  {
    Orthanc::DatabasePluginMessages::Find_Response_ResourceContent* content = NULL;  // the protobuf response will be the owner
    
    switch (level)
    {
      case Orthanc::DatabasePluginMessages::RESOURCE_PATIENT:
        content = response->mutable_patient_content();
        break;
      case Orthanc::DatabasePluginMessages::RESOURCE_STUDY:
        content = response->mutable_study_content();
        break;
      case Orthanc::DatabasePluginMessages::RESOURCE_SERIES:
        content =response->mutable_series_content();
        break;
      case Orthanc::DatabasePluginMessages::RESOURCE_INSTANCE:
        content = response->mutable_instance_content();
        break;
      default:
        throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
    }
    return content;
  }

  Orthanc::DatabasePluginMessages::Find_Response_ChildrenContent* GetChildrenContent(
                              Orthanc::DatabasePluginMessages::Find_Response* response,
                              Orthanc::DatabasePluginMessages::ResourceType childrenLevel)
  {
    Orthanc::DatabasePluginMessages::Find_Response_ChildrenContent* content = NULL;  // the protobuf response will be the owner
    
    switch (childrenLevel)
    {
      case Orthanc::DatabasePluginMessages::RESOURCE_STUDY:
        content = response->mutable_children_studies_content();
        break;
      case Orthanc::DatabasePluginMessages::RESOURCE_SERIES:
        content =response->mutable_children_series_content();
        break;
      case Orthanc::DatabasePluginMessages::RESOURCE_INSTANCE:
        content = response->mutable_children_instances_content();
        break;
      default:
        throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
    }
    return content;
  }

  std::string JoinRequestedMetadata(const Orthanc::DatabasePluginMessages::Find_Request_ChildrenSpecification* childrenSpec)
  {
    std::set<std::string> metadataTypes;
    for (int i = 0; i < childrenSpec->retrieve_metadata_size(); ++i)
    {
      metadataTypes.insert(boost::lexical_cast<std::string>(childrenSpec->retrieve_metadata(i)));
    }
    std::string joinedMetadataTypes;
    Orthanc::Toolbox::JoinStrings(joinedMetadataTypes, metadataTypes, ", ");

    return joinedMetadataTypes;
  }

  std::string JoinRequestedTags(const Orthanc::DatabasePluginMessages::Find_Request_ChildrenSpecification* childrenSpec)
  {
    std::set<std::string> tags;
    for (int i = 0; i < childrenSpec->retrieve_main_dicom_tags_size(); ++i)
    {
      tags.insert("(" + boost::lexical_cast<std::string>(childrenSpec->retrieve_main_dicom_tags(i).group()) 
                  + ", " + boost::lexical_cast<std::string>(childrenSpec->retrieve_main_dicom_tags(i).element()) + ")");
    }
    std::string joinedTags;
    Orthanc::Toolbox::JoinStrings(joinedTags, tags, ", ");

    return joinedTags;
  }


#define C0_QUERY_ID 0
#define C1_INTERNAL_ID 1
#define C2_ROW_NUMBER 2
#define C3_STRING_1 3
#define C4_STRING_2 4
#define C5_STRING_3 5
#define C6_STRING_4 6
#define C7_INT_1 7
#define C8_INT_2 8
#define C9_INT_3 9
#define C10_BIG_INT_1 10
#define C11_BIG_INT_2 11

#define QUERY_LOOKUP 1
#define QUERY_MAIN_DICOM_TAGS 2
#define QUERY_ATTACHMENTS 3
#define QUERY_METADATA 4
#define QUERY_LABELS 5
#define QUERY_PARENT_MAIN_DICOM_TAGS 10
#define QUERY_PARENT_IDENTIFIER 11
#define QUERY_PARENT_METADATA 12
#define QUERY_GRAND_PARENT_MAIN_DICOM_TAGS 15
#define QUERY_GRAND_PARENT_METADATA 16
#define QUERY_CHILDREN_IDENTIFIERS 20
#define QUERY_CHILDREN_MAIN_DICOM_TAGS 21
#define QUERY_CHILDREN_METADATA 22
#define QUERY_CHILDREN_COUNT 23
#define QUERY_GRAND_CHILDREN_IDENTIFIERS 30
#define QUERY_GRAND_CHILDREN_MAIN_DICOM_TAGS 31
#define QUERY_GRAND_CHILDREN_METADATA 32
#define QUERY_GRAND_CHILDREN_COUNT 33
#define QUERY_GRAND_GRAND_CHILDREN_IDENTIFIERS 40
#define QUERY_GRAND_GRAND_CHILDREN_COUNT 41
#define QUERY_ONE_INSTANCE_IDENTIFIER 50
#define QUERY_ONE_INSTANCE_METADATA 51
#define QUERY_ONE_INSTANCE_ATTACHMENTS 52

#define STRINGIFY(x) #x
#define TOSTRING(x) STRINGIFY(x)

  void IndexBackend::ExecuteCount(Orthanc::DatabasePluginMessages::TransactionResponse& response,
                                  DatabaseManager& manager,
                                  const Orthanc::DatabasePluginMessages::Find_Request& request)
  {
    std::string sql;

    LookupFormatter formatter(manager.GetDialect());
    std::string lookupSql;
    ISqlLookupFormatter::Apply(lookupSql, formatter, request);

    sql = "WITH Lookup AS (" + lookupSql + ") SELECT COUNT(*) FROM Lookup";

    Query::Parameters parametersTypes;
    formatter.GetDictionary().GetParametersType(parametersTypes);

    DatabaseManager::CachedStatement statement(STATEMENT_FROM_HERE_DYNAMIC(sql), manager, sql, parametersTypes);
    statement.Execute(formatter.GetDictionary());
    response.mutable_count_resources()->set_count(statement.ReadInteger64(0));
  }

  void IndexBackend::ExecuteFind(Orthanc::DatabasePluginMessages::TransactionResponse& response,
                                    DatabaseManager& manager,
                                    const Orthanc::DatabasePluginMessages::Find_Request& request)
  {
    // If we want the Find to use a read-only transaction, we can not create temporary tables with
    // the lookup results.  So we must use a CTE (Common Table Expression).  
    // However, a CTE can only be used in a single query -> we must unionize all the following 
    // queries to retrieve values from various tables.
    // However, to use UNION, all tables must have the same columns (numbers and types).  That's
    // why we have generic column names.
    // So, at the end we'll have only one very big query !

    const Orthanc::DatabasePluginMessages::Find_Request_ChildrenSpecification* childrenSpec = NULL;
    const Orthanc::DatabasePluginMessages::Find_Request_ChildrenSpecification* grandchildrenSpec = NULL;
    const Orthanc::DatabasePluginMessages::Find_Request_ChildrenSpecification* grandgrandchildrenSpec = NULL;

    switch (request.level())
    {
    case Orthanc::DatabasePluginMessages::RESOURCE_PATIENT:
      childrenSpec = &(request.children_studies());
      grandchildrenSpec = &(request.children_series());
      grandgrandchildrenSpec = &(request.children_instances());
      break;
    case Orthanc::DatabasePluginMessages::RESOURCE_STUDY:
      childrenSpec = &(request.children_series());
      grandchildrenSpec = &(request.children_instances());
      break;
    case Orthanc::DatabasePluginMessages::RESOURCE_SERIES:
      childrenSpec = &(request.children_instances());
      break;
    
    default:
      break;
    }

    std::string sql;

    // extract the resource id of interest by executing the lookup in a CTE
    LookupFormatter formatter(manager.GetDialect());
    std::string lookupSqlCTE;
    ISqlLookupFormatter::Apply(lookupSqlCTE, formatter, request);

    // base query, retrieve the ordered internalId and publicId of the selected resources
    sql = "WITH Lookup AS (" + lookupSqlCTE + ") ";

    std::string oneInstanceSqlCTE;

    // OneInstance CTE
    if (request.level() != Orthanc::DatabasePluginMessages::RESOURCE_INSTANCE &&
        request.retrieve_one_instance_metadata_and_attachments())
    {
      switch (request.level())
      {
        case Orthanc::DatabasePluginMessages::RESOURCE_SERIES:
        {
          oneInstanceSqlCTE = "SELECT Lookup.internalId AS parentInternalId, childLevel.publicId AS instancePublicId, childLevel.internalId AS instanceInternalId, ROW_NUMBER() OVER (PARTITION BY Lookup.internalId ORDER BY childLevel.publicId) AS rowNum"
                "   FROM Resources AS childLevel "
                "   INNER JOIN Lookup ON childLevel.parentId = Lookup.internalId";
        }; break;
        case Orthanc::DatabasePluginMessages::RESOURCE_STUDY:
        {
          oneInstanceSqlCTE = "SELECT Lookup.internalId AS parentInternalId, grandChildLevel.publicId AS instancePublicId, grandChildLevel.internalId AS instanceInternalId, ROW_NUMBER() OVER (PARTITION BY Lookup.internalId ORDER BY grandChildLevel.publicId) AS rowNum"
                "   FROM Resources AS grandChildLevel "
                "   INNER JOIN Resources childLevel ON grandChildLevel.parentId = childLevel.internalId "
                "   INNER JOIN Lookup ON childLevel.parentId = Lookup.internalId";
        }; break;
        case Orthanc::DatabasePluginMessages::RESOURCE_PATIENT:
        {
          oneInstanceSqlCTE = "SELECT Lookup.internalId AS parentInternalId, grandGrandChildLevel.publicId AS instancePublicId, grandGrandChildLevel.internalId AS instanceInternalId, ROW_NUMBER() OVER (PARTITION BY Lookup.internalId ORDER BY grandGrandChildLevel.publicId) AS rowNum"
                "   FROM Resources AS grandGrandChildLevel "
                "   INNER JOIN Resources grandChildLevel ON grandGrandChildLevel.parentId = grandChildLevel.internalId "
                "   INNER JOIN Resources childLevel ON grandChildLevel.parentId = childLevel.internalId "
                "   INNER JOIN Lookup ON childLevel.parentId = Lookup.internalId";
        }; break;
        default:
          throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
      }
      sql += ", _OneInstance AS (" + oneInstanceSqlCTE + ") ";
      sql += ", OneInstance AS (SELECT parentInternalId, instancePublicId, instanceInternalId FROM _OneInstance WHERE rowNum = 1) ";  // this is a generic way to implement DISTINCT ON
    }

    // GrandChildCount CTE in some specific cases
    bool hasGrandChildCountCTE = false;
    if (HasChildCountColumn() && !allowInconsistentChildCounts_ &&
        grandchildrenSpec != NULL && 
        !grandchildrenSpec->retrieve_identifiers() && // no need to count if we have retrieved the list of identifiers
        grandchildrenSpec->retrieve_count())  
    {
      sql += ", ValidGrandChildCounts AS (SELECT thisLevel.internalId, COALESCE(SUM(childLevel.childCount), 0) AS totalGrandChildCount "
             "  FROM Resources AS thisLevel "
             "  LEFT JOIN Resources AS childLevel ON childLevel.parentId = thisLevel.internalId "
             "    WHERE NOT EXISTS (SELECT 1 FROM InvalidChildCounts WHERE id = thisLevel.internalId) "
             "      AND NOT EXISTS (SELECT 1 FROM Resources AS child "
             "                               JOIN InvalidChildCounts ON InvalidChildCounts.id = child.internalId "
             "                               WHERE child.parentId = thisLevel.internalId) "
             "  GROUP BY thisLevel.internalId) ";
      hasGrandChildCountCTE = true;
    }

    // GrandGrandChildCount CTE in some specific cases
    bool hasGrandGrandChildCountCTE = false;
    if (HasChildCountColumn() && !allowInconsistentChildCounts_ &&
        grandgrandchildrenSpec != NULL && 
        !grandgrandchildrenSpec->retrieve_identifiers() && // no need to count if we have retrieved the list of identifiers
        grandgrandchildrenSpec->retrieve_count())  
    {
      sql += ", ValidGrandGrandChildCounts AS (SELECT thisLevel.internalId, COALESCE(SUM(grandChildLevel.childCount), 0) AS totalGrandGrandChildCount "
              "  FROM Resources AS thisLevel "
              "  LEFT JOIN Resources AS childLevel ON childLevel.parentId = thisLevel.internalId "
              "  LEFT JOIN Resources AS grandChildLevel ON grandChildLevel.parentId = childLevel.internalId "
              "    WHERE NOT EXISTS (SELECT 1 FROM InvalidChildCounts WHERE id = thisLevel.internalId) "
              "      AND NOT EXISTS (SELECT 1 FROM Resources AS child "
              "                               JOIN InvalidChildCounts ON InvalidChildCounts.id = child.internalId "
              "                               WHERE child.parentId = thisLevel.internalId) "
              "      AND NOT EXISTS (SELECT 1 FROM Resources AS grandChild "
              "                               JOIN Resources AS child ON grandChild.parentId = child.internalId "
              "                               JOIN InvalidChildCounts ON InvalidChildCounts.id = grandChild.internalId "
              "                               WHERE child.parentId = thisLevel.internalId) "
              "  GROUP BY thisLevel.internalId) ";
      hasGrandGrandChildCountCTE = true;
    }
    
    std::string revisionInC7;
    if (HasRevisionsSupport())
    {
      revisionInC7 = "  revision AS c8_int2, ";
    }
    else
    {
      revisionInC7 = "  0 AS c8_int2, ";
    }


    sql += " SELECT "
          "  " TOSTRING(QUERY_LOOKUP) " AS c0_queryId, "
          "  Lookup.internalId AS c1_internalId, "
          "  Lookup.rowNumber AS c2_rowNumber, "
          "  Lookup.publicId AS c3_string1, "
          "  " + formatter.FormatNull("TEXT") + " AS c4_string2, "
          "  " + formatter.FormatNull("TEXT") + " AS c5_string3, "
          "  " + formatter.FormatNull("BYTEA") + " AS c6_string4, "
          "  " + formatter.FormatNull("INT") + " AS c7_int1, "
          "  " + formatter.FormatNull("INT") + " AS c8_int2, "
          "  " + formatter.FormatNull("INT") + " AS c9_int3, "
          "  " + formatter.FormatNull("BIGINT") + " AS c10_big_int1, "
          "  " + formatter.FormatNull("BIGINT") + " AS c11_big_int2 "
          "  FROM Lookup ";

    // need MainDicomTags from resource ?
    if (request.retrieve_main_dicom_tags())
    {
      sql += "UNION ALL SELECT "
             "  " TOSTRING(QUERY_MAIN_DICOM_TAGS) " AS c0_queryId, "
             "  Lookup.internalId AS c1_internalId, "
             "  " + formatter.FormatNull("BIGINT") + " AS c2_rowNumber, "
             "  value AS c3_string1, "
             "  " + formatter.FormatNull("TEXT") + " AS c4_string2, "
             "  " + formatter.FormatNull("TEXT") + " AS c5_string3, "
             "  " + formatter.FormatNull("BYTEA") + " AS c6_string4, "
             "  tagGroup AS c7_int1, "
             "  tagElement AS c8_int2, "
             "  " + formatter.FormatNull("INT") + " AS c9_int3, "
             "  " + formatter.FormatNull("BIGINT") + " AS c10_big_int1, "
             "  " + formatter.FormatNull("BIGINT") + " AS c11_big_int2 "
             "FROM Lookup "
             "INNER JOIN MainDicomTags ON MainDicomTags.id = Lookup.internalId ";
    }
    
    // need resource metadata ?
    if (request.retrieve_metadata())
    {
      sql += "UNION ALL SELECT "
             "  " TOSTRING(QUERY_METADATA) " AS c0_queryId, "
             "  Lookup.internalId AS c1_internalId, "
             "  " + formatter.FormatNull("BIGINT") + " AS c2_rowNumber, "
             "  value AS c3_string1, "
             "  " + formatter.FormatNull("TEXT") + " AS c4_string2, "
             "  " + formatter.FormatNull("TEXT") + " AS c5_string3, "
             "  " + formatter.FormatNull("BYTEA") + " AS c6_string4, "
             "  type AS c7_int1, "
             + revisionInC7 +
             "  " + formatter.FormatNull("INT") + " AS c9_int3, "
             "  " + formatter.FormatNull("BIGINT") + " AS c10_big_int1, "
             "  " + formatter.FormatNull("BIGINT") + " AS c11_big_int2 "
             "FROM Lookup "
             "INNER JOIN Metadata ON Metadata.id = Lookup.internalId ";
    }

    // need resource attachments ?
    if (request.retrieve_attachments())
    {
      sql += "UNION ALL SELECT "
             "  " TOSTRING(QUERY_ATTACHMENTS) " AS c0_queryId, "
             "  Lookup.internalId AS c1_internalId, "
             "  " + formatter.FormatNull("BIGINT") + " AS c2_rowNumber, "
             "  uuid AS c3_string1, "
             "  uncompressedHash AS c4_string2, "
             "  compressedHash AS c5_string3, "
             "  customData AS c6_string4, "
             "  fileType AS c7_int1, "
             + revisionInC7 +
             "  compressionType AS c9_int3, "
             "  compressedSize AS c10_big_int1, "
             "  uncompressedSize AS c11_big_int2 "
             "FROM Lookup "
             "INNER JOIN AttachedFiles ON AttachedFiles.id = Lookup.internalId ";
    }

    // need resource labels ?
    if (request.retrieve_labels())
    {
      sql += "UNION ALL SELECT "
             "  " TOSTRING(QUERY_LABELS) " AS c0_queryId, "
             "  Lookup.internalId AS c1_internalId, "
             "  " + formatter.FormatNull("BIGINT") + " AS c2_rowNumber, "
             "  label AS c3_string1, "
             "  " + formatter.FormatNull("TEXT") + " AS c4_string2, "
             "  " + formatter.FormatNull("TEXT") + " AS c5_string3, "
             "  " + formatter.FormatNull("BYTEA") + " AS c6_string4, "
             "  " + formatter.FormatNull("INT") + " AS c7_int1, "
             "  " + formatter.FormatNull("INT") + " AS c8_int2, "
             "  " + formatter.FormatNull("INT") + " AS c9_int3, "
             "  " + formatter.FormatNull("BIGINT") + " AS c10_big_int1, "
             "  " + formatter.FormatNull("BIGINT") + " AS c11_big_int2 "
             "FROM Lookup "
             "INNER JOIN Labels ON Labels.id = Lookup.internalId ";
    }

    // need MainDicomTags from parent ?
    if (request.level() > Orthanc::DatabasePluginMessages::RESOURCE_PATIENT)
    {
      const Orthanc::DatabasePluginMessages::Find_Request_ParentSpecification* parentSpec = NULL;
      switch (request.level())
      {
      case Orthanc::DatabasePluginMessages::RESOURCE_STUDY:
        parentSpec = &(request.parent_patient());
        break;
      case Orthanc::DatabasePluginMessages::RESOURCE_SERIES:
        parentSpec = &(request.parent_study());
        break;
      case Orthanc::DatabasePluginMessages::RESOURCE_INSTANCE:
        parentSpec = &(request.parent_series());
        break;
      
      default:
        break;
      }

      if (parentSpec->retrieve_main_dicom_tags())
      {
        sql += "UNION ALL SELECT "
               "  " TOSTRING(QUERY_PARENT_MAIN_DICOM_TAGS) " AS c0_queryId, "
               "  Lookup.internalId AS c1_internalId, "
               "  " + formatter.FormatNull("BIGINT") + " AS c2_rowNumber, "
               "  value AS c3_string1, "
               "  " + formatter.FormatNull("TEXT") + " AS c4_string2, "
               "  " + formatter.FormatNull("TEXT") + " AS c5_string3, "
               "  " + formatter.FormatNull("BYTEA") + " AS c6_string4, "
               "  tagGroup AS c7_int1, "
               "  tagElement AS c8_int2, "
               "  " + formatter.FormatNull("INT") + " AS c9_int3, "
               "  " + formatter.FormatNull("BIGINT") + " AS c10_big_int1, "
               "  " + formatter.FormatNull("BIGINT") + " AS c11_big_int2 "
               "FROM Lookup "
               "INNER JOIN Resources currentLevel ON Lookup.internalId = currentLevel.internalId "
               "INNER JOIN MainDicomTags ON MainDicomTags.id = currentLevel.parentId ";
      }

      if (parentSpec->retrieve_metadata())
      {
        sql += "UNION ALL SELECT "
               "  " TOSTRING(QUERY_PARENT_METADATA) " AS c0_queryId, "
               "  Lookup.internalId AS c1_internalId, "
               "  " + formatter.FormatNull("BIGINT") + " AS c2_rowNumber, "
               "  value AS c3_string1, "
               "  " + formatter.FormatNull("TEXT") + " AS c4_string2, "
               "  " + formatter.FormatNull("TEXT") + " AS c5_string3, "
               "  " + formatter.FormatNull("BYTEA") + " AS c6_string4, "
               "  type AS c7_int1, "
               + revisionInC7 +
               "  " + formatter.FormatNull("INT") + " AS c9_int3, "
               "  " + formatter.FormatNull("BIGINT") + " AS c10_big_int1, "
               "  " + formatter.FormatNull("BIGINT") + " AS c11_big_int2 "
               "FROM Lookup "
               "INNER JOIN Resources currentLevel ON Lookup.internalId = currentLevel.internalId "
               "INNER JOIN Metadata ON Metadata.id = currentLevel.parentId ";
      }

      // need MainDicomTags from grandparent ?
      if (request.level() > Orthanc::DatabasePluginMessages::RESOURCE_STUDY)
      {
        const Orthanc::DatabasePluginMessages::Find_Request_ParentSpecification* grandparentSpec = NULL;
        switch (request.level())
        {
        case Orthanc::DatabasePluginMessages::RESOURCE_SERIES:
          grandparentSpec = &(request.parent_patient());
          break;
        case Orthanc::DatabasePluginMessages::RESOURCE_INSTANCE:
          grandparentSpec = &(request.parent_study());
          break;
        
        default:
          break;
        }

        if (grandparentSpec->retrieve_main_dicom_tags())
        {
          sql += "UNION ALL SELECT "
               "  " TOSTRING(QUERY_GRAND_PARENT_MAIN_DICOM_TAGS) " AS c0_queryId, "
               "  Lookup.internalId AS c1_internalId, "
               "  " + formatter.FormatNull("BIGINT") + " AS c2_rowNumber, "
               "  value AS c3_string1, "
               "  " + formatter.FormatNull("TEXT") + " AS c4_string2, "
               "  " + formatter.FormatNull("TEXT") + " AS c5_string3, "
               "  " + formatter.FormatNull("BYTEA") + " AS c6_string4, "
               "  tagGroup AS c7_int1, "
               "  tagElement AS c8_int2, "
               "  " + formatter.FormatNull("INT") + " AS c9_int3, "
               "  " + formatter.FormatNull("BIGINT") + " AS c10_big_int1, "
               "  " + formatter.FormatNull("BIGINT") + " AS c11_big_int2 "
               "FROM Lookup "
               "INNER JOIN Resources currentLevel ON Lookup.internalId = currentLevel.internalId "
               "INNER JOIN Resources parentLevel ON currentLevel.parentId = parentLevel.internalId "
               "INNER JOIN MainDicomTags ON MainDicomTags.id = parentLevel.parentId ";
        }

        if (grandparentSpec->retrieve_metadata())
        {
          sql += "UNION ALL SELECT "
                "  " TOSTRING(QUERY_GRAND_PARENT_METADATA) " AS c0_queryId, "
                "  Lookup.internalId AS c1_internalId, "
                "  " + formatter.FormatNull("BIGINT") + " AS c2_rowNumber, "
                "  value AS c3_string1, "
                "  " + formatter.FormatNull("TEXT") + " AS c4_string2, "
                "  " + formatter.FormatNull("TEXT") + " AS c5_string3, "
                "  " + formatter.FormatNull("BYTEA") + " AS c6_string4, "
                "  type AS c7_int1, "
                + revisionInC7 +
                "  " + formatter.FormatNull("INT") + " AS c9_int3, "
                "  " + formatter.FormatNull("BIGINT") + " AS c10_big_int1, "
                "  " + formatter.FormatNull("BIGINT") + " AS c11_big_int2 "
                "FROM Lookup "
                "INNER JOIN Resources currentLevel ON Lookup.internalId = currentLevel.internalId "
                "INNER JOIN Resources parentLevel ON currentLevel.parentId = parentLevel.internalId "
                "INNER JOIN Metadata ON Metadata.id = parentLevel.parentId ";
        }
      }
    }

    // need MainDicomTags from children ?
    if (request.level() <= Orthanc::DatabasePluginMessages::RESOURCE_SERIES)
    {
      assert(childrenSpec != NULL);

      if (childrenSpec->retrieve_main_dicom_tags_size() > 0)
      {
        sql += "UNION ALL SELECT "
               "  " TOSTRING(QUERY_CHILDREN_MAIN_DICOM_TAGS) " AS c0_queryId, "
               "  Lookup.internalId AS c1_internalId, "
               "  " + formatter.FormatNull("BIGINT") + " AS c2_rowNumber, "
               "  value AS c3_string1, "
               "  " + formatter.FormatNull("TEXT") + " AS c4_string2, "
               "  " + formatter.FormatNull("TEXT") + " AS c5_string3, "
               "  " + formatter.FormatNull("BYTEA") + " AS c6_string4, "
               "  tagGroup AS c7_int1, "
               "  tagElement AS c8_int2, "
               "  " + formatter.FormatNull("INT") + " AS c9_int3, "
               "  " + formatter.FormatNull("BIGINT") + " AS c10_big_int1, "
               "  " + formatter.FormatNull("BIGINT") + " AS c11_big_int2 "
               "FROM Lookup "
               "  INNER JOIN Resources childLevel ON childLevel.parentId = Lookup.internalId "
               "  INNER JOIN MainDicomTags ON MainDicomTags.id = childLevel.internalId AND (tagGroup, tagElement) IN (" + JoinRequestedTags(childrenSpec) + ")";
      }

      // need children identifiers ?
      if (childrenSpec->retrieve_identifiers())  
      {
        sql += "UNION ALL SELECT "
               "  " TOSTRING(QUERY_CHILDREN_IDENTIFIERS) " AS c0_queryId, "
               "  Lookup.internalId AS c1_internalId, "
               "  " + formatter.FormatNull("BIGINT") + " AS c2_rowNumber, "
               "  childLevel.publicId AS c3_string1, "
               "  " + formatter.FormatNull("TEXT") + " AS c4_string2, "
               "  " + formatter.FormatNull("TEXT") + " AS c5_string3, "
               "  " + formatter.FormatNull("BYTEA") + " AS c6_string4, "
               "  " + formatter.FormatNull("INT") + " AS c7_int1, "
               "  " + formatter.FormatNull("INT") + " AS c8_int2, "
               "  " + formatter.FormatNull("INT") + " AS c9_int3, "
               "  " + formatter.FormatNull("BIGINT") + " AS c10_big_int1, "
               "  " + formatter.FormatNull("BIGINT") + " AS c11_big_int2 "
               "FROM Lookup "
               "  INNER JOIN Resources childLevel ON Lookup.internalId = childLevel.parentId ";
      }
      else if (childrenSpec->retrieve_count())  // no need to count if we have retrieved the list of identifiers
      {
        if (HasChildCountColumn())
        {
          // we get the count value either from the childCount column if it has been computed or from the Resources table
          std::string getResourcesChildCount;
          
          if (allowInconsistentChildCounts_) // allow approximate childCount if childCount is populated but has not yet been updated
          {
            getResourcesChildCount = "Resources.childCount"; // read the last known value without taking into account the InvalidChildCounts table to speed up the query
          }
          else
          {
            // read the last known value only if it has not been invalidated by an entry in the InvalidChildCounts table -> more complex/slower query
            getResourcesChildCount = "SELECT childCount "
                                     "FROM Resources AS thisLevel "
                                     "WHERE thisLevel.internalId = lookup.internalId "
                                     "  AND NOT EXISTS (SELECT 1 FROM Invalidchildcounts WHERE id = thisLevel.internalId)"; 
          }

          sql += "UNION ALL SELECT "
                "  " TOSTRING(QUERY_CHILDREN_COUNT) " AS c0_queryId, "
                "  Lookup.internalId AS c1_internalId, "
                "  " + formatter.FormatNull("BIGINT") + " AS c2_rowNumber, "
                "  " + formatter.FormatNull("TEXT") + " AS c3_string1, "
                "  " + formatter.FormatNull("TEXT") + " AS c4_string2, "
                "  " + formatter.FormatNull("TEXT") + " AS c5_string3, "
                "  " + formatter.FormatNull("BYTEA") + " AS c6_string4, "
                "  " + formatter.FormatNull("INT") + " AS c7_int1, "
                "  " + formatter.FormatNull("INT") + " AS c8_int2, "
                "  " + formatter.FormatNull("INT") + " AS c9_int3, "
                "  COALESCE("
                "           (" + getResourcesChildCount + "),"
                "        		(SELECT COUNT(childLevel.internalId)"
                "            FROM Resources AS childLevel"
                "            WHERE Lookup.internalId = childLevel.parentId"
                "           )) AS c10_big_int1, "
                "  " + formatter.FormatNull("BIGINT") + " AS c11_big_int2 "
                "FROM Lookup "
                "LEFT JOIN Resources ON Lookup.internalId = Resources.internalId ";
        }
        else
        {
          sql += "UNION ALL SELECT "
                "  " TOSTRING(QUERY_CHILDREN_COUNT) " AS c0_queryId, "
                "  Lookup.internalId AS c1_internalId, "
                "  " + formatter.FormatNull("BIGINT") + " AS c2_rowNumber, "
                "  " + formatter.FormatNull("TEXT") + " AS c3_string1, "
                "  " + formatter.FormatNull("TEXT") + " AS c4_string2, "
                "  " + formatter.FormatNull("TEXT") + " AS c5_string3, "
                "  " + formatter.FormatNull("BYTEA") + " AS c6_string4, "
                "  " + formatter.FormatNull("INT") + " AS c7_int1, "
                "  " + formatter.FormatNull("INT") + " AS c8_int2, "
                "  " + formatter.FormatNull("INT") + " AS c9_int3, "
                "  COUNT(childLevel.internalId) AS c10_big_int1, "
                "  " + formatter.FormatNull("BIGINT") + " AS c11_big_int2 "
                "FROM Lookup "
                "  INNER JOIN Resources childLevel ON Lookup.internalId = childLevel.parentId GROUP BY Lookup.internalId ";
        }
      }

      if (childrenSpec->retrieve_metadata_size() > 0)
      {
        sql += "UNION ALL SELECT "
                "  " TOSTRING(QUERY_CHILDREN_METADATA) " AS c0_queryId, "
                "  Lookup.internalId AS c1_internalId, "
                "  " + formatter.FormatNull("BIGINT") + " AS c2_rowNumber, "
                "  value AS c3_string1, "
                "  " + formatter.FormatNull("TEXT") + " AS c4_string2, "
                "  " + formatter.FormatNull("TEXT") + " AS c5_string3, "
                "  " + formatter.FormatNull("BYTEA") + " AS c6_string4, "
                "  type AS c7_int1, "
                + revisionInC7 +
                "  " + formatter.FormatNull("INT") + " AS c9_int3, "
                "  " + formatter.FormatNull("BIGINT") + " AS c10_big_int1, "
                "  " + formatter.FormatNull("BIGINT") + " AS c11_big_int2 "
                "FROM Lookup "
                "  INNER JOIN Resources childLevel ON childLevel.parentId = Lookup.internalId "
                "  INNER JOIN Metadata ON Metadata.id = childLevel.internalId AND Metadata.type IN (" + JoinRequestedMetadata(childrenSpec) + ") ";
      }

      if (request.level() <= Orthanc::DatabasePluginMessages::RESOURCE_STUDY)
      {
        assert(grandchildrenSpec != NULL);

        // need grand children identifiers ?
        if (grandchildrenSpec->retrieve_identifiers())  
        {
          sql += "UNION ALL SELECT "
                "  " TOSTRING(QUERY_GRAND_CHILDREN_IDENTIFIERS) " AS c0_queryId, "
                "  Lookup.internalId AS c1_internalId, "
                "  " + formatter.FormatNull("BIGINT") + " AS c2_rowNumber, "
                "  grandChildLevel.publicId AS c3_string1, "
                "  " + formatter.FormatNull("TEXT") + " AS c4_string2, "
                "  " + formatter.FormatNull("TEXT") + " AS c5_string3, "
                "  " + formatter.FormatNull("BYTEA") + " AS c6_string4, "
                "  " + formatter.FormatNull("INT") + " AS c7_int1, "
                "  " + formatter.FormatNull("INT") + " AS c8_int2, "
                "  " + formatter.FormatNull("INT") + " AS c9_int3, "
                "  " + formatter.FormatNull("BIGINT") + " AS c10_big_int1, "
                "  " + formatter.FormatNull("BIGINT") + " AS c11_big_int2 "
                "FROM Lookup "
                "INNER JOIN Resources childLevel ON Lookup.internalId = childLevel.parentId "
                "INNER JOIN Resources grandChildLevel ON childLevel.internalId = grandChildLevel.parentId ";
        }
        else if (grandchildrenSpec->retrieve_count())  // no need to count if we have retrieved the list of identifiers
        {
          if (HasChildCountColumn())
          {

            // we get the count value either from the childCount column if it has been computed or from the Resources table
            std::string getResourcesGrandChildCount;
            
            if (allowInconsistentChildCounts_) // allow approximate childCount if childCount is populated but has not yet been updated
            {
              // read the last known value without taking into account the InvalidChildCounts table to speed up the query
              getResourcesGrandChildCount = "SELECT SUM(childLevel.childCount) "
                                            "FROM Resources AS childLevel "
                                            "WHERE childLevel.parentId = Lookup.internalId"; 
            }
            else
            {
              assert(hasGrandChildCountCTE);
              // read the last known value only if it has not been invalidated by an entry in the InvalidChildCounts table -> more complex/slower query
              getResourcesGrandChildCount = "SELECT totalGrandChildCount "
                                            "FROM ValidGrandChildCounts "
                                            "WHERE internalId = lookup.internalId";
                                            //"  AND NOT EXISTS (SELECT 1 FROM Invalidchildcounts WHERE id = childLevel.internalId OR id = lookup.internalId)"; 
            }

            // we get the count value either from the childCount column if it has been computed or from the Resources table
            sql += "UNION ALL SELECT "

                    "  " TOSTRING(QUERY_GRAND_CHILDREN_COUNT) " AS c0_queryId, "
                    "  Lookup.internalId AS c1_internalId, "
                    "  " + formatter.FormatNull("BIGINT") + " AS c2_rowNumber, "
                    "  " + formatter.FormatNull("TEXT") + " AS c3_string1, "
                    "  " + formatter.FormatNull("TEXT") + " AS c4_string2, "
                    "  " + formatter.FormatNull("TEXT") + " AS c5_string3, "
                    "  " + formatter.FormatNull("BYTEA") + " AS c6_string4, "
                    "  " + formatter.FormatNull("INT") + " AS c7_int1, "
                    "  " + formatter.FormatNull("INT") + " AS c8_int2, "
                    "  " + formatter.FormatNull("INT") + " AS c9_int3, "
                    "  COALESCE("
                    "           (" + getResourcesGrandChildCount + "),"
                    "        		(SELECT COUNT(grandChildLevel.internalId)"
                    "            FROM Resources AS childLevel"
                    "            INNER JOIN Resources AS grandChildLevel ON childLevel.internalId = grandChildLevel.parentId"
                    "            WHERE Lookup.internalId = childLevel.parentId"
                    "           )) AS c10_big_int1, "
                    "  " + formatter.FormatNull("BIGINT") + " AS c11_big_int2 "
                    "FROM Lookup ";
          }
          else
          {
            sql += "UNION ALL SELECT "
                  "  " TOSTRING(QUERY_GRAND_CHILDREN_COUNT) " AS c0_queryId, "
                  "  Lookup.internalId AS c1_internalId, "
                  "  " + formatter.FormatNull("BIGINT") + " AS c2_rowNumber, "
                  "  " + formatter.FormatNull("TEXT") + " AS c3_string1, "
                  "  " + formatter.FormatNull("TEXT") + " AS c4_string2, "
                  "  " + formatter.FormatNull("TEXT") + " AS c5_string3, "
                  "  " + formatter.FormatNull("BYTEA") + " AS c6_string4, "
                  "  " + formatter.FormatNull("INT") + " AS c7_int1, "
                  "  " + formatter.FormatNull("INT") + " AS c8_int2, "
                  "  " + formatter.FormatNull("INT") + " AS c9_int3, "
                  "  COUNT(grandChildLevel.internalId) AS c10_big_int1, "
                  "  " + formatter.FormatNull("BIGINT") + " AS c11_big_int2 "
                  "FROM Lookup "
                  "  INNER JOIN Resources childLevel ON Lookup.internalId = childLevel.parentId "
                  "  INNER JOIN Resources grandChildLevel ON childLevel.internalId = grandChildLevel.parentId GROUP BY Lookup.internalId ";
          }
        }

        if (grandchildrenSpec->retrieve_main_dicom_tags_size() > 0)
        {
          sql += "UNION ALL SELECT "
                 "  " TOSTRING(QUERY_GRAND_CHILDREN_MAIN_DICOM_TAGS) " AS c0_queryId, "
                 "  Lookup.internalId AS c1_internalId, "
                 "  " + formatter.FormatNull("BIGINT") + " AS c2_rowNumber, "
                 "  value AS c3_string1, "
                 "  " + formatter.FormatNull("TEXT") + " AS c4_string2, "
                 "  " + formatter.FormatNull("TEXT") + " AS c5_string3, "
                 "  " + formatter.FormatNull("BYTEA") + " AS c6_string4, "
                 "  tagGroup AS c7_int1, "
                 "  tagElement AS c8_int2, "
                 "  " + formatter.FormatNull("INT") + " AS c9_int3, "
                 "  " + formatter.FormatNull("BIGINT") + " AS c10_big_int1, "
                 "  " + formatter.FormatNull("BIGINT") + " AS c11_big_int2 "
                 "FROM Lookup "
                 "  INNER JOIN Resources childLevel ON childLevel.parentId = Lookup.internalId "
                 "  INNER JOIN Resources grandChildLevel ON grandChildLevel.parentId = childLevel.internalId "
                 "  INNER JOIN MainDicomTags ON MainDicomTags.id = grandChildLevel.internalId AND (tagGroup, tagElement) IN (" + JoinRequestedTags(grandchildrenSpec) + ")";
        }

        if (grandchildrenSpec->retrieve_metadata_size() > 0)
        {
          sql += "UNION ALL SELECT "
                 "  " TOSTRING(QUERY_GRAND_CHILDREN_METADATA) " AS c0_queryId, "
                 "  Lookup.internalId AS c1_internalId, "
                 "  " + formatter.FormatNull("BIGINT") + " AS c2_rowNumber, "
                 "  value AS c3_string1, "
                 "  " + formatter.FormatNull("TEXT") + " AS c4_string2, "
                 "  " + formatter.FormatNull("TEXT") + " AS c5_string3, "
                 "  " + formatter.FormatNull("BYTEA") + " AS c6_string4, "
                 "  type AS c7_int1, "
                 + revisionInC7 +
                 "  " + formatter.FormatNull("INT") + " AS c9_int3, "
                 "  " + formatter.FormatNull("BIGINT") + " AS c10_big_int1, "
                 "  " + formatter.FormatNull("BIGINT") + " AS c11_big_int2 "
                 "FROM Lookup "
                 "  INNER JOIN Resources childLevel ON childLevel.parentId = Lookup.internalId "
                 "  INNER JOIN Resources grandChildLevel ON grandChildLevel.parentId = childLevel.internalId "
                 "  INNER JOIN Metadata ON Metadata.id = grandChildLevel.internalId AND Metadata.type IN (" + JoinRequestedMetadata(grandchildrenSpec) + ") ";
        }

        if (request.level() == Orthanc::DatabasePluginMessages::RESOURCE_PATIENT)
        {
          assert(grandgrandchildrenSpec != NULL);

          // need grand children identifiers ?
          if (grandgrandchildrenSpec->retrieve_identifiers())  
          {
            sql += "UNION ALL SELECT "
                  "  " TOSTRING(QUERY_GRAND_GRAND_CHILDREN_IDENTIFIERS) " AS c0_queryId, "
                  "  Lookup.internalId AS c1_internalId, "
                  "  " + formatter.FormatNull("BIGINT") + " AS c2_rowNumber, "
                  "  grandGrandChildLevel.publicId AS c3_string1, "
                  "  " + formatter.FormatNull("TEXT") + " AS c4_string2, "
                  "  " + formatter.FormatNull("TEXT") + " AS c5_string3, "
                  "  " + formatter.FormatNull("BYTEA") + " AS c6_string4, "
                  "  " + formatter.FormatNull("INT") + " AS c7_int1, "
                  "  " + formatter.FormatNull("INT") + " AS c8_int2, "
                  "  " + formatter.FormatNull("INT") + " AS c9_int3, "
                  "  " + formatter.FormatNull("BIGINT") + " AS c10_big_int1, "
                  "  " + formatter.FormatNull("BIGINT") + " AS c11_big_int2 "
                  "FROM Lookup "
                  "INNER JOIN Resources childLevel ON Lookup.internalId = childLevel.parentId "
                  "INNER JOIN Resources grandChildLevel ON childLevel.internalId = grandChildLevel.parentId "
                  "INNER JOIN Resources grandGrandChildLevel ON grandChildLevel.internalId = grandGrandChildLevel.parentId ";
          }
          else if (grandgrandchildrenSpec->retrieve_count())  // no need to count if we have retrieved the list of identifiers
          {
            if (HasChildCountColumn())
            {
              std::string getResourcesGrandGrandChildCount;
              if (allowInconsistentChildCounts_) // allow approximate childCount if childCount is populated but has not yet been updated
              {
                // read the last known value without taking into account the InvalidChildCounts table to speed up the query
                getResourcesGrandGrandChildCount = "SELECT SUM(grandChildLevel.childCount)"
                                                   "FROM Resources AS grandChildLevel"
                                                   "INNER JOIN Resources AS childLevel ON childLevel.parentId = Lookup.internalId"
                                                   "WHERE grandChildLevel.parentId = childLevel.internalId"; 
              }
              else
              {
                assert(hasGrandGrandChildCountCTE);
                // read the last known value only if it has not been invalidated by an entry in the InvalidChildCounts table -> more complex/slower query
                getResourcesGrandGrandChildCount = "SELECT totalGrandGrandChildCount "
                                                   "FROM ValidGrandGrandChildCounts "
                                                   "WHERE internalId = lookup.internalId";
                                                  //  "INNER JOIN Resources AS childLevel ON childLevel.parentId = Lookup.internalId"
                                                  //  "WHERE grandChildLevel.parentId = childLevel.internalId"
                                                  //  "  AND NOT EXISTS (SELECT 1 FROM Invalidchildcounts WHERE id = grandChildLevel.internalId OR id = childLevel.internalId OR id = lookup.internalId)";
              }
  

              // we get the count value either from the childCount column if it has been computed or from the Resources table
              sql += "UNION ALL SELECT "
                    "  " TOSTRING(QUERY_GRAND_GRAND_CHILDREN_COUNT) " AS c0_queryId, "
                    "  Lookup.internalId AS c1_internalId, "
                    "  " + formatter.FormatNull("BIGINT") + " AS c2_rowNumber, "
                    "  " + formatter.FormatNull("TEXT") + " AS c3_string1, "
                    "  " + formatter.FormatNull("TEXT") + " AS c4_string2, "
                    "  " + formatter.FormatNull("TEXT") + " AS c5_string3, "
                    "  " + formatter.FormatNull("BYTEA") + " AS c6_string4, "
                    "  " + formatter.FormatNull("INT") + " AS c7_int1, "
                    "  " + formatter.FormatNull("INT") + " AS c8_int2, "
                    "  " + formatter.FormatNull("INT") + " AS c9_int3, "
                    "  COALESCE("
                    "           (" + getResourcesGrandGrandChildCount + "),"
                    "        		(SELECT COUNT(grandGrandChildLevel.internalId)"
                    "            FROM Resources AS childLevel"
                    "            INNER JOIN Resources AS grandChildLevel ON childLevel.internalId = grandChildLevel.parentId"
                    "            INNER JOIN Resources AS grandGrandChildLevel ON grandChildLevel.internalId = grandGrandChildLevel.parentId"
                    "            WHERE Lookup.internalId = childLevel.parentId"
                    "           )) AS c10_big_int1, "
                    "  " + formatter.FormatNull("BIGINT") + " AS c11_big_int2 "
                    "FROM Lookup ";
            }
            else
            {
              sql += "UNION ALL SELECT "
                    "  " TOSTRING(QUERY_GRAND_GRAND_CHILDREN_COUNT) " AS c0_queryId, "
                    "  Lookup.internalId AS c1_internalId, "
                    "  " + formatter.FormatNull("BIGINT") + " AS c2_rowNumber, "
                    "  " + formatter.FormatNull("TEXT") + " AS c3_string1, "
                    "  " + formatter.FormatNull("TEXT") + " AS c4_string2, "
                    "  " + formatter.FormatNull("TEXT") + " AS c5_string3, "
                    "  " + formatter.FormatNull("BYTEA") + " AS c6_string4, "
                    "  " + formatter.FormatNull("INT") + " AS c7_int1, "
                    "  " + formatter.FormatNull("INT") + " AS c8_int2, "
                    "  " + formatter.FormatNull("INT") + " AS c9_int3, "
                    "  COUNT(grandChildLevel.internalId) AS c10_big_int1, "
                    "  " + formatter.FormatNull("BIGINT") + " AS c11_big_int2 "
                    "FROM Lookup "
                    "INNER JOIN Resources childLevel ON Lookup.internalId = childLevel.parentId "
                    "INNER JOIN Resources grandChildLevel ON childLevel.internalId = grandChildLevel.parentId "
                    "INNER JOIN Resources grandGrandChildLevel ON grandChildLevel.internalId = grandGrandChildLevel.parentId GROUP BY Lookup.internalId ";
            }
          }
        }
      }
    }

    // need parent identifier ?
    if (request.retrieve_parent_identifier())
    {
      sql += "UNION ALL SELECT "
             "  " TOSTRING(QUERY_PARENT_IDENTIFIER) " AS c0_queryId, "
             "  Lookup.internalId AS c1_internalId, "
             "  " + formatter.FormatNull("BIGINT") + " AS c2_rowNumber, "
             "  parentLevel.publicId AS c3_string1, "
             "  " + formatter.FormatNull("TEXT") + " AS c4_string2, "
             "  " + formatter.FormatNull("TEXT") + " AS c5_string3, "
             "  " + formatter.FormatNull("BYTEA") + " AS c6_string4, "
             "  " + formatter.FormatNull("INT") + " AS c7_int1, "
             "  " + formatter.FormatNull("INT") + " AS c8_int2, "
             "  " + formatter.FormatNull("INT") + " AS c9_int3, "
             "  " + formatter.FormatNull("BIGINT") + " AS c10_big_int1, "
             "  " + formatter.FormatNull("BIGINT") + " AS c11_big_int2 "
             "FROM Lookup "
             "  INNER JOIN Resources currentLevel ON currentLevel.internalId = Lookup.internalId "
             "  INNER JOIN Resources parentLevel ON currentLevel.parentId = parentLevel.internalId ";
    }

    // need one instance info ?
    if (request.level() != Orthanc::DatabasePluginMessages::RESOURCE_INSTANCE &&
        request.retrieve_one_instance_metadata_and_attachments())
    {
      sql += "   UNION ALL SELECT"
             "    " TOSTRING(QUERY_ONE_INSTANCE_IDENTIFIER) " AS c0_queryId, "
             "    parentInternalId AS c1_internalId, "
             "    " + formatter.FormatNull("BIGINT") + " AS c2_rowNumber, "
             "    instancePublicId AS c3_string1, "
             "    " + formatter.FormatNull("TEXT") + " AS c4_string2, "
             "    " + formatter.FormatNull("TEXT") + " AS c5_string3, "
             "    " + formatter.FormatNull("BYTEA") + " AS c6_string4, "
             "    " + formatter.FormatNull("INT") + " AS c7_int1, "
             "    " + formatter.FormatNull("INT") + " AS c8_int2, "
             "  " + formatter.FormatNull("INT") + " AS c9_int3, "
             "    instanceInternalId AS c10_big_int1, "
             "    " + formatter.FormatNull("BIGINT") + " AS c11_big_int2 "
             "   FROM OneInstance ";

      sql += "   UNION ALL SELECT"
             "    " TOSTRING(QUERY_ONE_INSTANCE_METADATA) " AS c0_queryId, "
             "    parentInternalId AS c1_internalId, "
             "    " + formatter.FormatNull("BIGINT") + " AS c2_rowNumber, "
             "    Metadata.value AS c3_string1, "
             "    " + formatter.FormatNull("TEXT") + " AS c4_string2, "
             "    " + formatter.FormatNull("TEXT") + " AS c5_string3, "
             "    " + formatter.FormatNull("BYTEA") + " AS c6_string4, "
             "    Metadata.type AS c7_int1, "
             + revisionInC7 +
             "  " + formatter.FormatNull("INT") + " AS c9_int3, "
             "    " + formatter.FormatNull("BIGINT") + " AS c10_big_int1, "
             "    " + formatter.FormatNull("BIGINT") + " AS c11_big_int2 "
             "   FROM Metadata "
             "   INNER JOIN OneInstance ON Metadata.id = OneInstance.instanceInternalId";
             
      sql += "   UNION ALL SELECT"
             "    " TOSTRING(QUERY_ONE_INSTANCE_ATTACHMENTS) " AS c0_queryId, "
             "    parentInternalId AS c1_internalId, "
             "    " + formatter.FormatNull("BIGINT") + " AS c2_rowNumber, "
             "    uuid AS c3_string1, "
             "    uncompressedHash AS c4_string2, "
             "    compressedHash AS c5_string3, "
             "    customData AS c6_string4, "
             "    fileType AS c7_int1, "
             + revisionInC7 +
             "    compressionType AS c9_int3, "
             "    compressedSize AS c10_big_int1, "
             "    uncompressedSize AS c11_big_int2 "
             "   FROM AttachedFiles "
             "   INNER JOIN OneInstance ON AttachedFiles.id = OneInstance.instanceInternalId";

      // sql += "  ) ";

    }

    sql += " ORDER BY c0_queryId, c2_rowNumber";  // this is really important to make sure that the Lookup query is the first one to provide results since we use it to create the responses element !

    std::unique_ptr<DatabaseManager::StatementBase> statement;

    Query::Parameters parametersTypes;
    formatter.GetDictionary().GetParametersType(parametersTypes);
    if (manager.GetDialect() == Dialect_MySQL)
    { // TODO: investigate why "complex" cached statement do not seem to work properly in MySQL
      statement.reset(new DatabaseManager::StandaloneStatement(manager, sql, parametersTypes));
    }
    else
    {
      statement.reset(new DatabaseManager::CachedStatement(STATEMENT_FROM_HERE_DYNAMIC(sql), manager, sql, parametersTypes));
    }
    
    statement->Execute(formatter.GetDictionary());

    statement->SetResultFieldType(C6_STRING_4, ValueType_BinaryString);

    // LOG(INFO) << sql;

    std::map<int64_t, Orthanc::DatabasePluginMessages::Find_Response*> responses;

    while (!statement->IsDone())
    {
      int32_t queryId = statement->ReadInteger32(C0_QUERY_ID);
      int64_t internalId = statement->ReadInteger64(C1_INTERNAL_ID);
      
      assert(queryId == QUERY_LOOKUP || responses.find(internalId) != responses.end()); // the QUERY_LOOKUP must be read first and must create the response before any other query tries to populate the fields

      // LOG(INFO) << queryId << "  " << statement->ReadString(C3_STRING_1);

      switch (queryId)
      {
        case QUERY_LOOKUP:
          responses[internalId] = response.add_find();
          responses[internalId]->set_public_id(statement->ReadString(C3_STRING_1));
          responses[internalId]->set_internal_id(internalId);
          break;

        case QUERY_LABELS:
          responses[internalId]->add_labels(statement->ReadString(C3_STRING_1));
          break;

        case QUERY_MAIN_DICOM_TAGS:
        {
          Orthanc::DatabasePluginMessages::Find_Response_ResourceContent* content = GetResourceContent(responses[internalId], request.level());
          Orthanc::DatabasePluginMessages::Find_Response_Tag* tag = content->add_main_dicom_tags();

          tag->set_value(statement->ReadString(C3_STRING_1));
          tag->set_group(statement->ReadInteger32(C7_INT_1));
          tag->set_element(statement->ReadInteger32(C8_INT_2));
          }; break;

        case QUERY_PARENT_MAIN_DICOM_TAGS:
        {
          Orthanc::DatabasePluginMessages::Find_Response_ResourceContent* content = GetResourceContent(responses[internalId], static_cast<Orthanc::DatabasePluginMessages::ResourceType>(request.level() - 1));
          Orthanc::DatabasePluginMessages::Find_Response_Tag* tag = content->add_main_dicom_tags();

          tag->set_value(statement->ReadString(C3_STRING_1));
          tag->set_group(statement->ReadInteger32(C7_INT_1));
          tag->set_element(statement->ReadInteger32(C8_INT_2));
        }; break;

        case QUERY_GRAND_PARENT_MAIN_DICOM_TAGS:
        {
          Orthanc::DatabasePluginMessages::Find_Response_ResourceContent* content = GetResourceContent(responses[internalId], static_cast<Orthanc::DatabasePluginMessages::ResourceType>(request.level() - 2));
          Orthanc::DatabasePluginMessages::Find_Response_Tag* tag = content->add_main_dicom_tags();

          tag->set_value(statement->ReadString(C3_STRING_1));
          tag->set_group(statement->ReadInteger32(C7_INT_1));
          tag->set_element(statement->ReadInteger32(C8_INT_2));
        }; break;

        case QUERY_CHILDREN_IDENTIFIERS:
        {
          Orthanc::DatabasePluginMessages::Find_Response_ChildrenContent* content = GetChildrenContent(responses[internalId], static_cast<Orthanc::DatabasePluginMessages::ResourceType>(request.level() + 1));
          content->add_identifiers(statement->ReadString(C3_STRING_1));
          content->set_count(content->identifiers_size());
        }; break;

        case QUERY_CHILDREN_COUNT:
        {
          Orthanc::DatabasePluginMessages::Find_Response_ChildrenContent* content = GetChildrenContent(responses[internalId], static_cast<Orthanc::DatabasePluginMessages::ResourceType>(request.level() + 1));
          content->set_count(statement->ReadInteger64(C10_BIG_INT_1));
        }; break;

        case QUERY_CHILDREN_MAIN_DICOM_TAGS:
        {
          Orthanc::DatabasePluginMessages::Find_Response_ChildrenContent* content = GetChildrenContent(responses[internalId], static_cast<Orthanc::DatabasePluginMessages::ResourceType>(request.level() + 1));
          Orthanc::DatabasePluginMessages::Find_Response_Tag* tag = content->add_main_dicom_tags();
          tag->set_value(statement->ReadString(C3_STRING_1)); // TODO: handle sequences ??
          tag->set_group(statement->ReadInteger32(C7_INT_1));
          tag->set_element(statement->ReadInteger32(C8_INT_2));
        }; break;

        case QUERY_CHILDREN_METADATA:
        {
          Orthanc::DatabasePluginMessages::Find_Response_ChildrenContent* content = GetChildrenContent(responses[internalId], static_cast<Orthanc::DatabasePluginMessages::ResourceType>(request.level() + 1));
          Orthanc::DatabasePluginMessages::Find_Response_Metadata* metadata = content->add_metadata();

          metadata->set_value(statement->ReadString(C3_STRING_1));
          metadata->set_key(statement->ReadInteger32(C7_INT_1));
          metadata->set_revision(0);  // Setting a revision is not required in this case, as of Orthanc 1.12.5
        }; break;

        case QUERY_GRAND_CHILDREN_IDENTIFIERS:
        {
          Orthanc::DatabasePluginMessages::Find_Response_ChildrenContent* content = GetChildrenContent(responses[internalId], static_cast<Orthanc::DatabasePluginMessages::ResourceType>(request.level() + 2));
          content->add_identifiers(statement->ReadString(C3_STRING_1));
          content->set_count(content->identifiers_size());
        }; break;

        case QUERY_GRAND_CHILDREN_COUNT:
        {
          Orthanc::DatabasePluginMessages::Find_Response_ChildrenContent* content = GetChildrenContent(responses[internalId], static_cast<Orthanc::DatabasePluginMessages::ResourceType>(request.level() + 2));
          content->set_count(statement->ReadInteger64(C10_BIG_INT_1));
        }; break;

        case QUERY_GRAND_CHILDREN_MAIN_DICOM_TAGS:
        {
          Orthanc::DatabasePluginMessages::Find_Response_ChildrenContent* content = GetChildrenContent(responses[internalId], static_cast<Orthanc::DatabasePluginMessages::ResourceType>(request.level() + 2));
          Orthanc::DatabasePluginMessages::Find_Response_Tag* tag = content->add_main_dicom_tags();

          tag->set_value(statement->ReadString(C3_STRING_1)); // TODO: handle sequences ??
          tag->set_group(statement->ReadInteger32(C7_INT_1));
          tag->set_element(statement->ReadInteger32(C8_INT_2));
        }; break;

        case QUERY_GRAND_CHILDREN_METADATA:
        {
          Orthanc::DatabasePluginMessages::Find_Response_ChildrenContent* content = GetChildrenContent(responses[internalId], static_cast<Orthanc::DatabasePluginMessages::ResourceType>(request.level() + 2));
          Orthanc::DatabasePluginMessages::Find_Response_Metadata* metadata = content->add_metadata();

          metadata->set_value(statement->ReadString(C3_STRING_1));
          metadata->set_key(statement->ReadInteger32(C7_INT_1));
          metadata->set_revision(0);  // Setting a revision is not required in this case, as of Orthanc 1.12.5
        }; break;

        case QUERY_GRAND_GRAND_CHILDREN_IDENTIFIERS:
        {
          Orthanc::DatabasePluginMessages::Find_Response_ChildrenContent* content = GetChildrenContent(responses[internalId], static_cast<Orthanc::DatabasePluginMessages::ResourceType>(request.level() + 3));
          content->add_identifiers(statement->ReadString(C3_STRING_1));
          content->set_count(content->identifiers_size());
        }; break;

        case QUERY_GRAND_GRAND_CHILDREN_COUNT:
        {
          Orthanc::DatabasePluginMessages::Find_Response_ChildrenContent* content = GetChildrenContent(responses[internalId], static_cast<Orthanc::DatabasePluginMessages::ResourceType>(request.level() + 3));
          content->set_count(statement->ReadInteger64(C10_BIG_INT_1));
        }; break;

        case QUERY_ATTACHMENTS:
        {
          Orthanc::DatabasePluginMessages::FileInfo* attachment = responses[internalId]->add_attachments();

          attachment->set_uuid(statement->ReadString(C3_STRING_1));
          attachment->set_uncompressed_hash(statement->ReadString(C4_STRING_2));
          attachment->set_compressed_hash(statement->ReadString(C5_STRING_3));

          attachment->set_content_type(statement->ReadInteger32(C7_INT_1));
          attachment->set_compression_type(statement->ReadInteger32(C9_INT_3));
          attachment->set_compressed_size(statement->ReadInteger64(C10_BIG_INT_1));
          attachment->set_uncompressed_size(statement->ReadInteger64(C11_BIG_INT_2));

#if ORTHANC_PLUGINS_VERSION_IS_ABOVE(1, 12, 8)
          attachment->set_custom_data(statement->ReadStringOrNull(C6_STRING_4));
#endif

          if (!statement->IsNull(C8_INT_2))  // revision can be null for files that have been atttached by older Orthanc versions
          {
            responses[internalId]->add_attachments_revisions(statement->ReadInteger32(C8_INT_2));
          }
          else
          {
            responses[internalId]->add_attachments_revisions(0);
          }
        }; break;

        case QUERY_METADATA:
        {
          Orthanc::DatabasePluginMessages::Find_Response_ResourceContent* content = GetResourceContent(responses[internalId], request.level());
          Orthanc::DatabasePluginMessages::Find_Response_Metadata* metadata = content->add_metadata();

          metadata->set_value(statement->ReadString(C3_STRING_1));
          metadata->set_key(statement->ReadInteger32(C7_INT_1));
          
          if (!statement->IsNull(C8_INT_2))  // revision can be null for metadata that have been created by older Orthanc versions
          {
            metadata->set_revision(statement->ReadInteger32(C8_INT_2));
          }
          else
          {
            metadata->set_revision(0);
          }
        }; break;

        case QUERY_PARENT_METADATA:
        {
          Orthanc::DatabasePluginMessages::Find_Response_ResourceContent* content = GetResourceContent(responses[internalId], static_cast<Orthanc::DatabasePluginMessages::ResourceType>(request.level() - 1));
          Orthanc::DatabasePluginMessages::Find_Response_Metadata* metadata = content->add_metadata();

          metadata->set_value(statement->ReadString(C3_STRING_1));
          metadata->set_key(statement->ReadInteger32(C7_INT_1));

          if (!statement->IsNull(C8_INT_2))  // revision can be null for metadata that have been created by older Orthanc versions
          {
            metadata->set_revision(statement->ReadInteger32(C8_INT_2));
          }
          else
          {
            metadata->set_revision(0);
          }
        }; break;

        case QUERY_GRAND_PARENT_METADATA:
        {
          Orthanc::DatabasePluginMessages::Find_Response_ResourceContent* content = GetResourceContent(responses[internalId], static_cast<Orthanc::DatabasePluginMessages::ResourceType>(request.level() - 2));
          Orthanc::DatabasePluginMessages::Find_Response_Metadata* metadata = content->add_metadata();

          metadata->set_value(statement->ReadString(C3_STRING_1));
          metadata->set_key(statement->ReadInteger32(C7_INT_1));

          if (!statement->IsNull(C8_INT_2))  // revision can be null for metadata that have been created by older Orthanc versions
          {
            metadata->set_revision(statement->ReadInteger32(C8_INT_2));
          }
          else
          {
            metadata->set_revision(0);
          }
        }; break;

        case QUERY_PARENT_IDENTIFIER:
        {
          responses[internalId]->set_parent_public_id(statement->ReadString(C3_STRING_1));
        }; break;

        case QUERY_ONE_INSTANCE_IDENTIFIER:
        {
          responses[internalId]->set_one_instance_public_id(statement->ReadString(C3_STRING_1));
        }; break;
        case QUERY_ONE_INSTANCE_METADATA:
        {
          Orthanc::DatabasePluginMessages::Find_Response_Metadata* metadata = responses[internalId]->add_one_instance_metadata();

          metadata->set_value(statement->ReadString(C3_STRING_1));
          metadata->set_key(statement->ReadInteger32(C7_INT_1));

          if (!statement->IsNull(C8_INT_2))  // revision can be null for metadata that have been created by older Orthanc versions
          {
            metadata->set_revision(statement->ReadInteger32(C8_INT_2));
          }
          else
          {
            metadata->set_revision(0);
          }
        }; break;
        case QUERY_ONE_INSTANCE_ATTACHMENTS:
        {
          Orthanc::DatabasePluginMessages::FileInfo* attachment = responses[internalId]->add_one_instance_attachments();
          
          attachment->set_uuid(statement->ReadString(C3_STRING_1));
          attachment->set_uncompressed_hash(statement->ReadString(C4_STRING_2));
          attachment->set_compressed_hash(statement->ReadString(C5_STRING_3));
          attachment->set_content_type(statement->ReadInteger32(C7_INT_1));
          attachment->set_compression_type(statement->ReadInteger32(C9_INT_3));
          attachment->set_compressed_size(statement->ReadInteger64(C10_BIG_INT_1));
          attachment->set_uncompressed_size(statement->ReadInteger64(C11_BIG_INT_2));

#if ORTHANC_PLUGINS_VERSION_IS_ABOVE(1, 12, 8)
          attachment->set_custom_data(statement->ReadStringOrNull(C6_STRING_4));
#endif
        }; break;

        default:
          throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
      }
      statement->Next();
    }    
  }
#endif

#if ORTHANC_PLUGINS_HAS_KEY_VALUE_STORES == 1
    void IndexBackend::StoreKeyValue(DatabaseManager& manager,
                                     const std::string& storeId,
                                     const std::string& key,
                                     const std::string& value)
    {
      // TODO: that probably needs to be adapted in ODBC and MySQL
      DatabaseManager::CachedStatement statement(
        STATEMENT_FROM_HERE, manager,
        "INSERT INTO KeyValueStores VALUES(${storeId}, ${key}, ${value}) ON CONFLICT (storeId, key) DO UPDATE SET value = EXCLUDED.value;");

      statement.SetParameterType("storeId", ValueType_Utf8String);
      statement.SetParameterType("key", ValueType_Utf8String);
      statement.SetParameterType("value", ValueType_BinaryString);

      Dictionary args;
      args.SetUtf8Value("storeId", storeId);
      args.SetUtf8Value("key", key);
      args.SetBinaryValue("value", value);

      statement.Execute(args);
    }

    void IndexBackend::DeleteKeyValue(DatabaseManager& manager,
                                      const std::string& storeId,
                                      const std::string& key)
    {
      DatabaseManager::CachedStatement statement(
        STATEMENT_FROM_HERE, manager,
        "DELETE FROM KeyValueStores WHERE storeId = ${storeId} AND key = ${key}");

      statement.SetParameterType("storeId", ValueType_Utf8String);
      statement.SetParameterType("key", ValueType_Utf8String);

      Dictionary args;
      args.SetUtf8Value("storeId", storeId);
      args.SetUtf8Value("key", key);

      statement.Execute(args);
    }

    bool IndexBackend::GetKeyValue(std::string& value,
                                   DatabaseManager& manager,
                                   const std::string& storeId,
                                   const std::string& key)
    {
      DatabaseManager::CachedStatement statement(
        STATEMENT_FROM_HERE, manager,
        "SELECT value FROM KeyValueStores WHERE storeId = ${storeId} AND key = ${key}");
        
      statement.SetReadOnly(true);
      statement.SetParameterType("storeId", ValueType_Utf8String);
      statement.SetParameterType("key", ValueType_Utf8String);

      Dictionary args;
      args.SetUtf8Value("storeId", storeId);
      args.SetUtf8Value("key", key);

      statement.Execute(args);
      statement.SetResultFieldType(0, ValueType_BinaryString);

      if (statement.IsDone())
      {
        return false;
      }
      else
      {
        value = statement.ReadString(0);
        return true;
      }
    }                  

    void IndexBackend::ListKeysValues(Orthanc::DatabasePluginMessages::TransactionResponse& response,
                                      DatabaseManager& manager,
                                      const Orthanc::DatabasePluginMessages::ListKeysValues_Request& request)
    {
      response.mutable_list_keys_values()->Clear();

      LookupFormatter formatter(manager.GetDialect());

      std::unique_ptr<DatabaseManager::CachedStatement> statement;
      
      std::string storeIdParameter = formatter.GenerateParameter(request.store_id());

      if (request.from_first())
      {
        statement.reset(new DatabaseManager::CachedStatement(
                        STATEMENT_FROM_HERE, manager,
                        "SELECT key, value FROM KeyValueStores WHERE storeId= " + storeIdParameter + " ORDER BY key ASC " + formatter.FormatLimits(0, request.limit())));
      }
      else
      {
        std::string fromKeyParameter = formatter.GenerateParameter(request.from_key());
        statement.reset(new DatabaseManager::CachedStatement(
                        STATEMENT_FROM_HERE, manager,
                        "SELECT key, value FROM KeyValueStores WHERE storeId= " + storeIdParameter + " AND key > " + fromKeyParameter + " ORDER BY key ASC " + formatter.FormatLimits(0, request.limit())));
      }

      statement->Execute(formatter.GetDictionary());

      if (!statement->IsDone())
      {
        if (statement->GetResultFieldsCount() != 2)
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
        }
        
        statement->SetResultFieldType(0, ValueType_Utf8String);
        statement->SetResultFieldType(1, ValueType_BinaryString);

        while (!statement->IsDone())
        {
          Orthanc::DatabasePluginMessages::ListKeysValues_Response_KeyValue* kv = response.mutable_list_keys_values()->add_keys_values();
          kv->set_key(statement->ReadString(0));
          kv->set_value(statement->ReadString(1));

          statement->Next();
        }
      }

    }
#endif

#if ORTHANC_PLUGINS_HAS_QUEUES == 1
    void IndexBackend::EnqueueValue(DatabaseManager& manager,
                                    const std::string& queueId,
                                    const std::string& value)
    {
      DatabaseManager::CachedStatement statement(
        STATEMENT_FROM_HERE, manager,
        "INSERT INTO Queues VALUES(${AUTOINCREMENT} ${queueId}, ${value})");

      statement.SetParameterType("queueId", ValueType_Utf8String);
      statement.SetParameterType("value", ValueType_BinaryString);

      Dictionary args;
      args.SetUtf8Value("queueId", queueId);
      args.SetBinaryValue("value", value);

      statement.Execute(args);
    }


    bool IndexBackend::DequeueValueSQLite(std::string& value,
                                          DatabaseManager& manager,
                                          const std::string& queueId,
                                          bool fromFront)
    {
      assert(manager.GetDialect() == Dialect_SQLite);

      LookupFormatter formatter(manager.GetDialect());

      std::unique_ptr<DatabaseManager::CachedStatement> statement;

      std::string queueIdParameter = formatter.GenerateParameter(queueId);

      if (fromFront)
      {
        statement.reset(new DatabaseManager::CachedStatement(
                          STATEMENT_FROM_HERE, manager,
                          "SELECT id, value FROM Queues WHERE queueId=" + queueIdParameter + " ORDER BY id ASC LIMIT 1"));
      }
      else
      {
        statement.reset(new DatabaseManager::CachedStatement(
                          STATEMENT_FROM_HERE, manager,
                          "SELECT id, value FROM Queues WHERE queueId=" + queueIdParameter + " ORDER BY id DESC LIMIT 1"));
      }

      statement->Execute(formatter.GetDictionary());

      if (statement->IsDone())
      {
        return false;
      }
      else
      {
        statement->SetResultFieldType(0, ValueType_Integer64);
        statement->SetResultFieldType(1, ValueType_BinaryString);

        value = statement->ReadString(1);

        {
          DatabaseManager::CachedStatement s2(STATEMENT_FROM_HERE, manager,
                                              "DELETE FROM Queues WHERE id=${id}");

          s2.SetParameterType("id", ValueType_Integer64);

          Dictionary args;
          args.SetIntegerValue("id", statement->ReadInteger64(0));

          s2.Execute(args);
        }

        return true;
      }
    }


    bool IndexBackend::DequeueValue(std::string& value,
                                    DatabaseManager& manager,
                                    const std::string& queueId,
                                    bool fromFront)
    {
      if (manager.GetDialect() == Dialect_SQLite)
      {
        return DequeueValueSQLite(value, manager, queueId, fromFront);
      }
      else
      {
        LookupFormatter formatter(manager.GetDialect());

        std::unique_ptr<DatabaseManager::CachedStatement> statement;

        std::string queueIdParameter = formatter.GenerateParameter(queueId);

        switch (manager.GetDialect())
        {
          case Dialect_PostgreSQL:
            if (fromFront)
            {
              statement.reset(new DatabaseManager::CachedStatement(
                                STATEMENT_FROM_HERE, manager,
                                "WITH poppedRows AS (DELETE FROM Queues WHERE id = (SELECT MIN(id) FROM Queues WHERE queueId=" + queueIdParameter + ") RETURNING value) "
                                "SELECT value FROM poppedRows"));
            }
            else
            {
              statement.reset(new DatabaseManager::CachedStatement(
                                STATEMENT_FROM_HERE, manager,
                                "WITH poppedRows AS (DELETE FROM Queues WHERE id = (SELECT MAX(id) FROM Queues WHERE queueId=" + queueIdParameter + ") RETURNING value) "
                                "SELECT value FROM poppedRows"));
            }
            break;

          default:
            throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
        }

        statement->Execute(formatter.GetDictionary());

        if (statement->IsDone())
        {
          return false;
        }
        else
        {
          statement->SetResultFieldType(0, ValueType_BinaryString);
          value = statement->ReadString(0);
          return true;
        }
      }
    }

    uint64_t IndexBackend::GetQueueSize(DatabaseManager& manager,
                                        const std::string& queueId)
    {
      DatabaseManager::CachedStatement statement(
        STATEMENT_FROM_HERE, manager,
        "SELECT COUNT(*) FROM Queues WHERE queueId = ${queueId}");
        
      statement.SetReadOnly(true);
      statement.SetParameterType("queueId", ValueType_Utf8String);

      Dictionary args;
      args.SetUtf8Value("queueId", queueId);

      statement.Execute(args);
      statement.SetResultFieldType(0, ValueType_Integer64);

      return statement.ReadInteger64(0);
    }
#endif

#if ORTHANC_PLUGINS_HAS_ATTACHMENTS_CUSTOM_DATA == 1
    void IndexBackend::GetAttachmentCustomData(std::string& customData,
                                               DatabaseManager& manager,
                                               const std::string& attachmentUuid)
    {
      DatabaseManager::CachedStatement statement(
        STATEMENT_FROM_HERE, manager,
        "SELECT customData FROM AttachedFiles WHERE uuid = ${uuid}");

      statement.SetReadOnly(true);
      statement.SetParameterType("uuid", ValueType_Utf8String);

      Dictionary args;
      args.SetUtf8Value("uuid", attachmentUuid);

      statement.Execute(args);
      statement.SetResultFieldType(8, ValueType_BinaryString);

      if (statement.IsDone())
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_UnknownResource, "Nonexistent attachment: " + attachmentUuid);
      }
      else
      {
        customData = statement.ReadStringOrNull(0);
      }
    }

    void  IndexBackend::SetAttachmentCustomData(DatabaseManager& manager,
                                                const std::string& attachmentUuid,
                                                const std::string& customData)
    {
      DatabaseManager::CachedStatement statement(
        STATEMENT_FROM_HERE, manager,
        "UPDATE AttachedFiles SET customData = ${customData} WHERE uuid = ${uuid}");

      statement.SetParameterType("uuid", ValueType_Utf8String);
      statement.SetParameterType("customData", ValueType_BinaryString);

      Dictionary args;
      args.SetUtf8Value("uuid", attachmentUuid);
      args.SetBinaryValue("customData", customData);

      statement.Execute(args);
    }
#endif

#if ORTHANC_PLUGINS_HAS_AUDIT_LOGS == 1
    void IndexBackend::RecordAuditLog(DatabaseManager& manager,
                                      const std::string& sourcePlugin,
                                      const std::string& userId,
                                      OrthancPluginResourceType resourceType,
                                      const std::string& resourceId,
                                      const std::string& action,
                                      const void* logData,
                                      uint32_t logDataSize)
    {
      DatabaseManager::CachedStatement statement(
        STATEMENT_FROM_HERE, manager,
        "INSERT INTO AuditLogs (sourcePlugin, userId, resourceType, resourceId, action, logData) "
        "VALUES(${sourcePlugin}, ${userId}, ${resourceType}, ${resourceId}, ${action}, ${logData})");

      statement.SetParameterType("sourcePlugin", ValueType_Utf8String);
      statement.SetParameterType("userId", ValueType_Utf8String);
      statement.SetParameterType("resourceType", ValueType_Integer64);
      statement.SetParameterType("resourceId", ValueType_Utf8String);
      statement.SetParameterType("action", ValueType_Utf8String);
      statement.SetParameterType("logData", ValueType_BinaryString);

      Dictionary args;
      args.SetUtf8Value("sourcePlugin", sourcePlugin);
      args.SetUtf8Value("userId", userId);
      args.SetIntegerValue("resourceType", static_cast<int>(resourceType));
      args.SetUtf8Value("resourceId", resourceId);
      args.SetUtf8Value("action", action);
      
      if (logData != NULL && logDataSize > 0)
      {
        args.SetBinaryValue("logData", logData, logDataSize);
      }
      else
      {
        args.SetBinaryNullValue("logData");
      }

      statement.Execute(args);
    }

    void IndexBackend::GetAuditLogs(DatabaseManager& manager,
                                    std::list<AuditLog>& logs,
                                    const std::string& userIdFilter,
                                    const std::string& resourceIdFilter,
                                    const std::string& actionFilter,
                                    const std::string& fromTsIsoFormat,
                                    const std::string& toTsIsoFormat,
                                    uint64_t since,
                                    uint64_t limit)
    {
      LookupFormatter formatter(manager.GetDialect());
      std::vector<std::string> filters;

      std::string sql = "SELECT to_char(ts, 'YYYY-MM-DD\"T\"HH24:MI:SS.MS\"Z\"'), sourcePlugin, userId, resourceType, resourceId, action, logData FROM AuditLogs ";

      if (!userIdFilter.empty())
      {
        filters.push_back("userId = " + formatter.GenerateParameter(userIdFilter));
      }

      if (!resourceIdFilter.empty())
      {
        filters.push_back("resourceId = " + formatter.GenerateParameter(resourceIdFilter));
      }

      if (!actionFilter.empty())
      {
        filters.push_back("action = " + formatter.GenerateParameter(actionFilter));
      }

      if (!fromTsIsoFormat.empty())
      {
        filters.push_back("ts >= " + formatter.GenerateParameter(fromTsIsoFormat) + "::TIMESTAMPTZ");
      }

      if (!toTsIsoFormat.empty())
      {
        filters.push_back("ts < " + formatter.GenerateParameter(toTsIsoFormat) + "::TIMESTAMPTZ");
      }

      if (filters.size() > 0)
      {
        std::string joinedFilters;
        Orthanc::Toolbox::JoinStrings(joinedFilters, filters, " AND ");
        sql += " WHERE " + joinedFilters;
      }

      sql += " ORDER BY ts ASC ";

      if (since > 0 || limit > 0)
      {
        sql += formatter.FormatLimits(since, limit);
      }

      DatabaseManager::CachedStatement statement(STATEMENT_FROM_HERE_DYNAMIC(sql), manager, sql);
      statement.SetReadOnly(true);

      statement.Execute(formatter.GetDictionary());

      if (!statement.IsDone())
      {
        if (statement.GetResultFieldsCount() != 7)
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
        }
        
        statement.SetResultFieldType(0, ValueType_Utf8String);
        statement.SetResultFieldType(1, ValueType_Utf8String);
        statement.SetResultFieldType(2, ValueType_Utf8String);
        statement.SetResultFieldType(3, ValueType_Integer64);
        statement.SetResultFieldType(4, ValueType_Utf8String);
        statement.SetResultFieldType(5, ValueType_Utf8String);
        statement.SetResultFieldType(6, ValueType_BinaryString);

        while (!statement.IsDone())
        {
          logs.push_back(AuditLog(statement.ReadString(0),
                                  statement.ReadString(1),
                                  statement.ReadString(2),
                                  static_cast<OrthancPluginResourceType>(statement.ReadInteger64(3)),
                                  statement.ReadString(4),
                                  statement.ReadString(5),
                                  statement.ReadStringOrNull(6),
                                  !statement.IsNull(6)));

          statement.Next();
        }
      }
    }
#endif

}
