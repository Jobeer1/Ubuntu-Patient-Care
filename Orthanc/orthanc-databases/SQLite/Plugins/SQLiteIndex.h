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

namespace OrthancDatabases
{
  class SQLiteIndex : public IndexBackend 
  {
  private:
    std::string  path_;
    bool         fast_;

  public:
    explicit SQLiteIndex(OrthancPluginContext* context);  // Opens in memory

    SQLiteIndex(OrthancPluginContext* context,
                const std::string& path);

    void SetFast(bool fast)
    {
      fast_ = fast;
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
      return false;
    }

    virtual int64_t CreateResource(DatabaseManager& manager,
                                   const char* publicId,
                                   OrthancPluginResourceType type) ORTHANC_OVERRIDE;

    // New primitive since Orthanc 1.5.2
    virtual int64_t GetLastChangeIndex(DatabaseManager& manager) ORTHANC_OVERRIDE;

    // New primitive since Orthanc 1.12.0
    virtual bool HasLabelsSupport() const ORTHANC_OVERRIDE
    {
      return true;
    }

#if ORTHANC_PLUGINS_VERSION_IS_ABOVE(1, 12, 5)
    virtual bool HasFindSupport() const ORTHANC_OVERRIDE;
#endif

#if ORTHANC_PLUGINS_VERSION_IS_ABOVE(1, 12, 5)
    virtual void ExecuteFind(Orthanc::DatabasePluginMessages::TransactionResponse& response,
                             DatabaseManager& manager,
                             const Orthanc::DatabasePluginMessages::Find_Request& request) ORTHANC_OVERRIDE;
#endif

#if ORTHANC_PLUGINS_VERSION_IS_ABOVE(1, 12, 5)
    virtual void ExecuteCount(Orthanc::DatabasePluginMessages::TransactionResponse& response,
                              DatabaseManager& manager,
                              const Orthanc::DatabasePluginMessages::Find_Request& request) ORTHANC_OVERRIDE;
#endif

    virtual bool HasChildCountColumn() const ORTHANC_OVERRIDE
    {
      return false;
    }
  };
}
