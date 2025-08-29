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

#include "../../Framework/Plugins/IndexBackend.h"
#include "../../Framework/PostgreSQL/PostgreSQLParameters.h"
#include <boost/thread.hpp>


namespace OrthancDatabases
{
  class PostgreSQLIndex : public IndexBackend 
  {
  private:
    PostgreSQLParameters   parameters_;
    bool                   clearAll_;
    bool                   hkHasComputedAllMissingChildCount_;

  protected:
    virtual void ClearDeletedFiles(DatabaseManager& manager) ORTHANC_OVERRIDE;

    virtual void ClearDeletedResources(DatabaseManager& manager) ORTHANC_OVERRIDE;

    virtual void ClearRemainingAncestor(DatabaseManager& manager) ORTHANC_OVERRIDE;

    virtual bool HasChildCountColumn() const ORTHANC_OVERRIDE
    {
      return true;
    }

    void ApplyPrepareIndex(DatabaseManager::Transaction& t, DatabaseManager& manager);

  public:
    PostgreSQLIndex(OrthancPluginContext* context,
                    const PostgreSQLParameters& parameters,
                    bool readOnly = false);

    void SetClearAll(bool clear)
    {
      clearAll_ = clear;
    }

    virtual IDatabaseFactory* CreateDatabaseFactory() ORTHANC_OVERRIDE;

    virtual void ConfigureDatabase(DatabaseManager& manager,
                                   bool hasIdentifierTags,
                                   const std::list<IdentifierTag>& identifierTags) ORTHANC_OVERRIDE;

    virtual bool HasRevisionsSupport() const ORTHANC_OVERRIDE
    {
      return true;
    }
    
    virtual bool HasAttachmentCustomDataSupport() const ORTHANC_OVERRIDE
    {
      return true;
    }

    virtual bool HasKeyValueStores() const ORTHANC_OVERRIDE
    {
      return true;
    }

    virtual bool HasQueues() const ORTHANC_OVERRIDE
    {
      return true;
    }

    virtual bool HasAuditLogs() const ORTHANC_OVERRIDE
    {
      return true;
    }

    virtual int64_t CreateResource(DatabaseManager& manager,
                                   const char* publicId,
                                   OrthancPluginResourceType type) ORTHANC_OVERRIDE;

    virtual void DeleteResource(IDatabaseBackendOutput& output,
                                DatabaseManager& manager,
                                int64_t id) ORTHANC_OVERRIDE;

    virtual void DeleteAttachment(IDatabaseBackendOutput& output,
                                  DatabaseManager& manager,
                                  int64_t id,
                                  int32_t attachment) ORTHANC_OVERRIDE;

    virtual void SetResourcesContent(DatabaseManager& manager,
                                     uint32_t countIdentifierTags,
                                     const OrthancPluginResourcesContentTags* identifierTags,
                                     uint32_t countMainDicomTags,
                                     const OrthancPluginResourcesContentTags* mainDicomTags,
                                     uint32_t countMetadata,
                                     const OrthancPluginResourcesContentMetadata* metadata) ORTHANC_OVERRIDE;

    virtual uint64_t GetTotalCompressedSize(DatabaseManager& manager) ORTHANC_OVERRIDE;

    virtual uint64_t GetTotalUncompressedSize(DatabaseManager& manager) ORTHANC_OVERRIDE;
    
    virtual bool HasCreateInstance() const  ORTHANC_OVERRIDE
    {
      return true;
    }

#if ORTHANC_PLUGINS_HAS_DATABASE_CONSTRAINT == 1
    virtual void CreateInstance(OrthancPluginCreateInstanceResult& result,
                                DatabaseManager& manager,
                                const char* hashPatient,
                                const char* hashStudy,
                                const char* hashSeries,
                                const char* hashInstance)
      ORTHANC_OVERRIDE;
#endif

    virtual uint64_t GetResourcesCount(DatabaseManager& manager,
                                       OrthancPluginResourceType resourceType) ORTHANC_OVERRIDE;

    virtual int64_t GetLastChangeIndex(DatabaseManager& manager) ORTHANC_OVERRIDE;

    // This is now obsolete
    virtual void TagMostRecentPatient(DatabaseManager& manager,
                                      int64_t patient) ORTHANC_OVERRIDE;

    virtual void SetProtectedPatient(DatabaseManager& manager,
                                     int64_t internalId, 
                                     bool isProtected) ORTHANC_OVERRIDE;

    virtual bool IsProtectedPatient(DatabaseManager& manager,
                                    int64_t internalId) ORTHANC_OVERRIDE;

    virtual bool SelectPatientToRecycle(int64_t& internalId /*out*/,
                                        DatabaseManager& manager) ORTHANC_OVERRIDE;
    
    virtual bool SelectPatientToRecycle(int64_t& internalId /*out*/,
                                        DatabaseManager& manager,
                                        int64_t patientIdToAvoid) ORTHANC_OVERRIDE;

    // New primitive since Orthanc 1.12.0
    virtual bool HasLabelsSupport() const ORTHANC_OVERRIDE
    {
      return true;
    }

    virtual bool HasAtomicIncrementGlobalProperty() ORTHANC_OVERRIDE
    {
      return true;
    }

    virtual int64_t IncrementGlobalProperty(DatabaseManager& manager,
                                            const char* serverIdentifier,
                                            int32_t property,
                                            int64_t increment) ORTHANC_OVERRIDE;

    virtual bool HasUpdateAndGetStatistics() ORTHANC_OVERRIDE
    {
      return true;
    }

    virtual void UpdateAndGetStatistics(DatabaseManager& manager,
                                        int64_t& patientsCount,
                                        int64_t& studiesCount,
                                        int64_t& seriesCount,
                                        int64_t& instancesCount,
                                        int64_t& compressedSize,
                                        int64_t& uncompressedSize) ORTHANC_OVERRIDE;

    virtual bool HasPerformDbHousekeeping() ORTHANC_OVERRIDE;

    virtual void PerformDbHousekeeping(DatabaseManager& manager) ORTHANC_OVERRIDE;

  };
}
