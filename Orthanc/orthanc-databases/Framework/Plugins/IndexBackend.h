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

#include "IDatabaseBackend.h"

#include <OrthancException.h>

#include <boost/thread/shared_mutex.hpp>


namespace OrthancDatabases
{
  /**
   * WARNING: This class can be invoked concurrently by several
   * threads if it is used from "DatabaseBackendAdapterV3".
   **/
  class IndexBackend : public IDatabaseBackend
  {
  private:
    class LookupFormatter;

    OrthancPluginContext*  context_;
    bool                   readOnly_;
    bool                   allowInconsistentChildCounts_;

    boost::shared_mutex                                outputFactoryMutex_;
    std::unique_ptr<IDatabaseBackendOutput::IFactory>  outputFactory_;
    
  protected:

    virtual void ClearDeletedFiles(DatabaseManager& manager);

    virtual void ClearDeletedResources(DatabaseManager& manager);

    virtual void ClearRemainingAncestor(DatabaseManager& manager);

    virtual bool HasChildCountColumn() const = 0;

    void SignalDeletedFiles(IDatabaseBackendOutput& output,
                            DatabaseManager& manager);

    void SignalDeletedResources(IDatabaseBackendOutput& output,
                                DatabaseManager& manager);

    bool IsReadOnly()
    {
      return readOnly_;
    }

  private:
    void ReadChangesInternal(IDatabaseBackendOutput& output,
                             bool& done,
                             DatabaseManager& manager,
                             DatabaseManager::CachedStatement& statement,
                             const Dictionary& args,
                             uint32_t limit,
                             bool returnFirstResults);

    void ReadExportedResourcesInternal(IDatabaseBackendOutput& output,
                                       bool& done,
                                       DatabaseManager::CachedStatement& statement,
                                       const Dictionary& args,
                                       uint32_t limit);

#if ORTHANC_PLUGINS_HAS_QUEUES == 1
    bool DequeueValueSQLite(std::string& value,
                            DatabaseManager& manager,
                            const std::string& queueId,
                            bool fromFront);
#endif

  public:
    explicit IndexBackend(OrthancPluginContext* context,
                          bool readOnly,
                          bool allowInconsistentChildCounts);

    virtual OrthancPluginContext* GetContext() ORTHANC_OVERRIDE
    {
      return context_;
    }

    virtual void SetOutputFactory(IDatabaseBackendOutput::IFactory* factory) ORTHANC_OVERRIDE;
    
    virtual IDatabaseBackendOutput* CreateOutput() ORTHANC_OVERRIDE;
    
    virtual void AddAttachment(DatabaseManager& manager,
                               int64_t id,
                               const OrthancPluginAttachment& attachment,
                               int64_t revision) ORTHANC_OVERRIDE;

#if ORTHANC_PLUGINS_HAS_ATTACHMENTS_CUSTOM_DATA == 1
    // New in Orthanc 1.12.8
    virtual void AddAttachment(DatabaseManager& manager,
                               int64_t id,
                               const OrthancPluginAttachment& attachment,
                               int64_t revision,
                               const std::string& customData) ORTHANC_OVERRIDE;
#endif

    virtual void AttachChild(DatabaseManager& manager,
                             int64_t parent,
                             int64_t child) ORTHANC_OVERRIDE;
    
    virtual void ClearChanges(DatabaseManager& manager) ORTHANC_OVERRIDE;
    
    virtual void ClearExportedResources(DatabaseManager& manager) ORTHANC_OVERRIDE;

    virtual void DeleteAttachment(IDatabaseBackendOutput& output,
                                  DatabaseManager& manager,
                                  int64_t id,
                                  int32_t attachment) ORTHANC_OVERRIDE;
    
    virtual void DeleteMetadata(DatabaseManager& manager,
                                int64_t id,
                                int32_t metadataType) ORTHANC_OVERRIDE;
    
    virtual void DeleteResource(IDatabaseBackendOutput& output,
                                DatabaseManager& manager,
                                int64_t id) ORTHANC_OVERRIDE;

    virtual void GetAllInternalIds(std::list<int64_t>& target,
                                   DatabaseManager& manager,
                                   OrthancPluginResourceType resourceType) ORTHANC_OVERRIDE;
    
    virtual void GetAllPublicIds(std::list<std::string>& target,
                                 DatabaseManager& manager,
                                 OrthancPluginResourceType resourceType) ORTHANC_OVERRIDE;
    
    virtual void GetAllPublicIds(std::list<std::string>& target,
                                 DatabaseManager& manager,
                                 OrthancPluginResourceType resourceType,
                                 int64_t since,
                                 uint32_t limit) ORTHANC_OVERRIDE;
    
    virtual void GetChanges(IDatabaseBackendOutput& output,
                            bool& done /*out*/,
                            DatabaseManager& manager,
                            int64_t since,
                            uint32_t limit) ORTHANC_OVERRIDE;

    virtual void GetChangesExtended(IDatabaseBackendOutput& output,
                                    bool& done /*out*/,
                                    DatabaseManager& manager,
                                    int64_t since,
                                    int64_t to,
                                    const std::set<uint32_t>& changeTypes,
                                    uint32_t limit) ORTHANC_OVERRIDE;

    virtual void GetChildrenInternalId(std::list<int64_t>& target /*out*/,
                                       DatabaseManager& manager,
                                       int64_t id) ORTHANC_OVERRIDE;
    
    virtual void GetChildrenPublicId(std::list<std::string>& target /*out*/,
                                     DatabaseManager& manager,
                                     int64_t id) ORTHANC_OVERRIDE;
    
    virtual void GetExportedResources(IDatabaseBackendOutput& output,
                                      bool& done /*out*/,
                                      DatabaseManager& manager,
                                      int64_t since,
                                      uint32_t limit) ORTHANC_OVERRIDE;
    
    virtual void GetLastChange(IDatabaseBackendOutput& output,
                               DatabaseManager& manager) ORTHANC_OVERRIDE;
    
    virtual void GetLastExportedResource(IDatabaseBackendOutput& output,
                                         DatabaseManager& manager) ORTHANC_OVERRIDE;
    
    virtual void GetMainDicomTags(IDatabaseBackendOutput& output,
                                  DatabaseManager& manager,
                                  int64_t id) ORTHANC_OVERRIDE;
    
    virtual std::string GetPublicId(DatabaseManager& manager,
                                    int64_t resourceId) ORTHANC_OVERRIDE;
    
    virtual uint64_t GetResourcesCount(DatabaseManager& manager,
                                       OrthancPluginResourceType resourceType) ORTHANC_OVERRIDE;
    
    virtual OrthancPluginResourceType GetResourceType(DatabaseManager& manager,
                                                      int64_t resourceId) ORTHANC_OVERRIDE;
    
    virtual uint64_t GetTotalCompressedSize(DatabaseManager& manager) ORTHANC_OVERRIDE;
    
    virtual uint64_t GetTotalUncompressedSize(DatabaseManager& manager) ORTHANC_OVERRIDE;
    
    virtual bool IsExistingResource(DatabaseManager& manager,
                                    int64_t internalId) ORTHANC_OVERRIDE;
    
    virtual bool IsProtectedPatient(DatabaseManager& manager,
                                    int64_t internalId) ORTHANC_OVERRIDE;
    
    virtual void ListAvailableMetadata(std::list<int32_t>& target /*out*/,
                                       DatabaseManager& manager,
                                       int64_t id) ORTHANC_OVERRIDE;
    
    virtual void ListAvailableAttachments(std::list<int32_t>& target /*out*/,
                                          DatabaseManager& manager,
                                          int64_t id) ORTHANC_OVERRIDE;
    
    virtual void LogChange(DatabaseManager& manager,
                           int32_t changeType,
                           int64_t resourceId,
                           OrthancPluginResourceType resourceType,
                           const char* date) ORTHANC_OVERRIDE;
    
    virtual void LogExportedResource(DatabaseManager& manager,
                                     OrthancPluginResourceType resourceType,
                                     const char* publicId,
                                     const char* modality,
                                     const char* date,
                                     const char* patientId,
                                     const char* studyInstanceUid,
                                     const char* seriesInstanceUid,
                                     const char* sopInstanceUid) ORTHANC_OVERRIDE;
    
    virtual bool LookupAttachment(IDatabaseBackendOutput& output,
                                  int64_t& revision /*out*/,
                                  DatabaseManager& manager,
                                  int64_t id,
                                  int32_t contentType) ORTHANC_OVERRIDE;
    
    virtual bool LookupGlobalProperty(std::string& target /*out*/,
                                      DatabaseManager& manager,
                                      const char* serverIdentifier,
                                      int32_t property) ORTHANC_OVERRIDE;
    
    virtual void LookupIdentifier(std::list<int64_t>& target /*out*/,
                                  DatabaseManager& manager,
                                  OrthancPluginResourceType resourceType,
                                  uint16_t group,
                                  uint16_t element,
                                  OrthancPluginIdentifierConstraint constraint,
                                  const char* value) ORTHANC_OVERRIDE;
    
    virtual void LookupIdentifierRange(std::list<int64_t>& target /*out*/,
                                       DatabaseManager& manager,
                                       OrthancPluginResourceType resourceType,
                                       uint16_t group,
                                       uint16_t element,
                                       const char* start,
                                       const char* end) ORTHANC_OVERRIDE;

    virtual bool LookupMetadata(std::string& target /*out*/,
                                int64_t& revision /*out*/,
                                DatabaseManager& manager,
                                int64_t id,
                                int32_t metadataType) ORTHANC_OVERRIDE;

    virtual bool LookupParent(int64_t& parentId /*out*/,
                              DatabaseManager& manager,
                              int64_t resourceId) ORTHANC_OVERRIDE;
    
    virtual bool LookupResource(int64_t& id /*out*/,
                                OrthancPluginResourceType& type /*out*/,
                                DatabaseManager& manager,
                                const char* publicId) ORTHANC_OVERRIDE;
    
    virtual bool SelectPatientToRecycle(int64_t& internalId /*out*/,
                                        DatabaseManager& manager) ORTHANC_OVERRIDE;
    
    virtual bool SelectPatientToRecycle(int64_t& internalId /*out*/,
                                        DatabaseManager& manager,
                                        int64_t patientIdToAvoid) ORTHANC_OVERRIDE;
    
    virtual void SetGlobalProperty(DatabaseManager& manager,
                                   const char* serverIdentifier,
                                   int32_t property,
                                   const char* utf8) ORTHANC_OVERRIDE;

    virtual void SetMainDicomTag(DatabaseManager& manager,
                                 int64_t id,
                                 uint16_t group,
                                 uint16_t element,
                                 const char* value) ORTHANC_OVERRIDE;
    
    virtual void SetIdentifierTag(DatabaseManager& manager,
                                  int64_t id,
                                  uint16_t group,
                                  uint16_t element,
                                  const char* value) ORTHANC_OVERRIDE;

    virtual void SetMetadata(DatabaseManager& manager,
                             int64_t id,
                             int32_t metadataType,
                             const char* value,
                             int64_t revision) ORTHANC_OVERRIDE;
    
    virtual void SetProtectedPatient(DatabaseManager& manager,
                                     int64_t internalId, 
                                     bool isProtected) ORTHANC_OVERRIDE;
    
    virtual uint32_t GetDatabaseVersion(DatabaseManager& manager) ORTHANC_OVERRIDE;
    
    virtual void UpgradeDatabase(DatabaseManager& manager,
                                 uint32_t  targetVersion,
                                 OrthancPluginStorageArea* storageArea) ORTHANC_OVERRIDE;
    
    virtual void ClearMainDicomTags(DatabaseManager& manager,
                                    int64_t internalId) ORTHANC_OVERRIDE;

    // For unit testing only!
    virtual uint64_t GetAllResourcesCount(DatabaseManager& manager);

    // For unit testing only!
    virtual uint64_t GetUnprotectedPatientsCount(DatabaseManager& manager);

    // For unit testing only!
    virtual bool GetParentPublicId(std::string& target,
                                   DatabaseManager& manager,
                                   int64_t id);

    // For unit tests only!
    virtual void GetChildren(std::list<std::string>& childrenPublicIds,
                             DatabaseManager& manager,
                             int64_t id);

#if ORTHANC_PLUGINS_HAS_DATABASE_CONSTRAINT == 1
    // New primitive since Orthanc 1.5.2
    virtual void LookupResources(IDatabaseBackendOutput& output,
                                 DatabaseManager& manager,
                                 const DatabaseConstraints& lookup,
                                 OrthancPluginResourceType queryLevel,
                                 const std::set<std::string>& labels,
                                 LabelsConstraint labelsConstraint,
                                 uint32_t limit,
                                 bool requestSomeInstance) ORTHANC_OVERRIDE;
#endif

#if ORTHANC_PLUGINS_HAS_DATABASE_CONSTRAINT == 1
    // New primitive since Orthanc 1.5.2
    virtual void SetResourcesContent(
      DatabaseManager& manager,
      uint32_t countIdentifierTags,
      const OrthancPluginResourcesContentTags* identifierTags,
      uint32_t countMainDicomTags,
      const OrthancPluginResourcesContentTags* mainDicomTags,
      uint32_t countMetadata,
      const OrthancPluginResourcesContentMetadata* metadata) ORTHANC_OVERRIDE;
#endif

    // New primitive since Orthanc 1.5.2
    virtual void GetChildrenMetadata(std::list<std::string>& target,
                                     DatabaseManager& manager,
                                     int64_t resourceId,
                                     int32_t metadata) ORTHANC_OVERRIDE;

    virtual void TagMostRecentPatient(DatabaseManager& manager,
                                      int64_t patient) ORTHANC_OVERRIDE;

    // New primitive since Orthanc 1.5.4
    virtual bool LookupResourceAndParent(int64_t& id,
                                         OrthancPluginResourceType& type,
                                         std::string& parentPublicId,
                                         DatabaseManager& manager,
                                         const char* publicId) ORTHANC_OVERRIDE;

    // New primitive since Orthanc 1.5.4
    virtual void GetAllMetadata(std::map<int32_t, std::string>& result,
                                DatabaseManager& manager,
                                int64_t id) ORTHANC_OVERRIDE;

    virtual bool HasCreateInstance() const ORTHANC_OVERRIDE
    {
      // This extension is available in PostgreSQL and MySQL, but is
      // emulated by "CreateInstanceGeneric()" in SQLite
      return false;
    }
      
#if ORTHANC_PLUGINS_HAS_DATABASE_CONSTRAINT == 1
    virtual void CreateInstance(OrthancPluginCreateInstanceResult& result,
                                DatabaseManager& manager,
                                const char* hashPatient,
                                const char* hashStudy,
                                const char* hashSeries,
                                const char* hashInstance) ORTHANC_OVERRIDE
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
    }
#endif

#if ORTHANC_PLUGINS_HAS_DATABASE_CONSTRAINT == 1
    // This function corresponds to
    // "Orthanc::Compatibility::ICreateInstance::Apply()"
    void CreateInstanceGeneric(OrthancPluginCreateInstanceResult& result,
                               DatabaseManager& manager,
                               const char* hashPatient,
                               const char* hashStudy,
                               const char* hashSeries,
                               const char* hashInstance);
#endif

    bool LookupGlobalIntegerProperty(int& target /*out*/,
                                     DatabaseManager& manager,
                                     const char* serverIdentifier,
                                     int32_t property);
    
    void SetGlobalIntegerProperty(DatabaseManager& manager,
                                  const char* serverIdentifier,
                                  int32_t property,
                                  int value);

    virtual void AddLabel(DatabaseManager& manager,
                          int64_t resource,
                          const std::string& label) ORTHANC_OVERRIDE;

    virtual void RemoveLabel(DatabaseManager& manager,
                             int64_t resource,
                             const std::string& label) ORTHANC_OVERRIDE;

    virtual void ListLabels(std::list<std::string>& target,
                            DatabaseManager& manager,
                            int64_t resource) ORTHANC_OVERRIDE;

    virtual void ListAllLabels(std::list<std::string>& target,
                               DatabaseManager& manager) ORTHANC_OVERRIDE;
    
    virtual bool HasAtomicIncrementGlobalProperty() ORTHANC_OVERRIDE;

    virtual int64_t IncrementGlobalProperty(DatabaseManager& manager,
                                            const char* serverIdentifier,
                                            int32_t property,
                                            int64_t increment) ORTHANC_OVERRIDE;

    virtual bool HasUpdateAndGetStatistics() ORTHANC_OVERRIDE;

    virtual void UpdateAndGetStatistics(DatabaseManager& manager,
                                        int64_t& patientsCount,
                                        int64_t& studiesCount,
                                        int64_t& seriesCount,
                                        int64_t& instancesCount,
                                        int64_t& compressedSize,
                                        int64_t& uncompressedSize) ORTHANC_OVERRIDE;

    virtual bool HasMeasureLatency() ORTHANC_OVERRIDE;

    virtual uint64_t MeasureLatency(DatabaseManager& manager) ORTHANC_OVERRIDE;

#if ORTHANC_PLUGINS_VERSION_IS_ABOVE(1, 12, 5)
    // New primitives since Orthanc 1.12.5
    virtual bool HasExtendedChanges() const ORTHANC_OVERRIDE
    {
      return true;
    }

    virtual bool HasFindSupport() const ORTHANC_OVERRIDE;

    virtual void ExecuteFind(Orthanc::DatabasePluginMessages::TransactionResponse& response,
                             DatabaseManager& manager,
                             const Orthanc::DatabasePluginMessages::Find_Request& request) ORTHANC_OVERRIDE;

    virtual void ExecuteCount(Orthanc::DatabasePluginMessages::TransactionResponse& response,
                              DatabaseManager& manager,
                              const Orthanc::DatabasePluginMessages::Find_Request& request) ORTHANC_OVERRIDE;
#endif

#if ORTHANC_PLUGINS_HAS_KEY_VALUE_STORES == 1
    virtual void StoreKeyValue(DatabaseManager& manager,
                               const std::string& storeId,
                               const std::string& key,
                               const std::string& value) ORTHANC_OVERRIDE;

    virtual void DeleteKeyValue(DatabaseManager& manager,
                                const std::string& storeId,
                                const std::string& key) ORTHANC_OVERRIDE;

    virtual bool GetKeyValue(std::string& value,
                             DatabaseManager& manager,
                             const std::string& storeId,
                             const std::string& key) ORTHANC_OVERRIDE;

    virtual void ListKeysValues(Orthanc::DatabasePluginMessages::TransactionResponse& response,
                                DatabaseManager& manager,
                                const Orthanc::DatabasePluginMessages::ListKeysValues_Request& request) ORTHANC_OVERRIDE;
#endif

#if ORTHANC_PLUGINS_HAS_QUEUES == 1
    virtual void EnqueueValue(DatabaseManager& manager,
                              const std::string& queueId,
                              const std::string& value) ORTHANC_OVERRIDE;

    virtual bool DequeueValue(std::string& value,
                              DatabaseManager& manager,
                              const std::string& queueId,
                              bool fromFront) ORTHANC_OVERRIDE;

    virtual uint64_t GetQueueSize(DatabaseManager& manager,
                                  const std::string& queueId) ORTHANC_OVERRIDE;

#endif

#if ORTHANC_PLUGINS_HAS_ATTACHMENTS_CUSTOM_DATA == 1
    virtual void GetAttachmentCustomData(std::string& customData,
                                         DatabaseManager& manager,
                                         const std::string& attachmentUuid) ORTHANC_OVERRIDE;

    virtual void SetAttachmentCustomData(DatabaseManager& manager,
                                         const std::string& attachmentUuid,
                                         const std::string& customData) ORTHANC_OVERRIDE;

#endif

#if ORTHANC_PLUGINS_HAS_AUDIT_LOGS == 1
    virtual void RecordAuditLog(DatabaseManager& manager,
                                const std::string& sourcePlugin,
                                const std::string& userId,
                                OrthancPluginResourceType type,
                                const std::string& resourceId,
                                const std::string& action,
                                const void* logData,
                                uint32_t logDataSize) ORTHANC_OVERRIDE;

    virtual void GetAuditLogs(DatabaseManager& manager,
                              std::list<AuditLog>& logs,
                              const std::string& userIdFilter,
                              const std::string& resourceIdFilter,
                              const std::string& actionFilter,
                              const std::string& fromTsIsoFormat,
                              const std::string& toTsIsoFormat,
                              uint64_t since,
                              uint64_t limit) ORTHANC_OVERRIDE;
#endif

    virtual bool HasPerformDbHousekeeping() ORTHANC_OVERRIDE
    {
      return false;
    }

    virtual void PerformDbHousekeeping(DatabaseManager& manager) ORTHANC_OVERRIDE
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
    }

    /**
     * "maxDatabaseRetries" is to handle
     * "OrthancPluginErrorCode_DatabaseCannotSerialize" if there is a
     * collision multiple writers. "countConnections" and
     * "maxDatabaseRetries" are only used if Orthanc >= 1.9.2.
     **/
    static void Register(IndexBackend* backend,
                         size_t countConnections,
                         bool useDynamicConnectionPool,
                         unsigned int maxDatabaseRetries,
                         unsigned int housekeepingDelaySeconds);

    static void Finalize();

    static DatabaseManager* CreateSingleDatabaseManager(IDatabaseBackend& backend,
                                                        bool hasIdentifierTags,
                                                        const std::list<IdentifierTag>& identifierTags);
  };
}
