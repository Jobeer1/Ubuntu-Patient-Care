/**
 * Advanced authorization plugin for Orthanc
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

#include "IAuthorizationParser.h"
#include "ResourceHierarchyCache.h"

#include <Compatibility.h>  // For std::unique_ptr<>

#if BUILD_UNIT_TESTS == 1
#  include <gtest/gtest_prod.h>
#endif


namespace OrthancPlugins
{
  class AuthorizationParserBase : public IAuthorizationParser
  {
  private:
    std::unique_ptr<ResourceHierarchyCache>  resourceHierarchy_;

    void AddResourceInternal(AccessedResources& target,
                             Orthanc::ResourceType level,
                             const std::string& orthancId,
                             const std::set<std::string>& labels);
    
  protected:
    void AddOrthancInstance(AccessedResources& target,
                            const std::string& orthancId);

    void AddOrthancSeries(AccessedResources& target,
                          const std::string& orthancId);

    void AddOrthancStudy(AccessedResources& target,
                         const std::string& orthancId);

    void AddOrthancPatient(AccessedResources& target,
                           const std::string& orthancId);

    Orthanc::ResourceType AddOrthancUnknownResource(AccessedResources& target,
                                                    const std::string& orthancId);

    void AddDicomPatient(AccessedResources& target,
                         const std::string& patientId);

    void AddDicomSeries(AccessedResources& target,
                        const std::string& studyDicomUid,
                        const std::string& seriesDicomUid);

    void AddDicomInstance(AccessedResources& target,
                          const std::string& studyDicomUid,
                          const std::string& seriesDicomUid,
                          const std::string& instanceDicomUid);

  public:
    virtual void AddDicomStudy(AccessedResources& target,
                               const std::string& studyDicomUid) ORTHANC_OVERRIDE;

    explicit AuthorizationParserBase(ICacheFactory& factory);

    virtual void Invalidate(Orthanc::ResourceType level,
                            const std::string& id) ORTHANC_OVERRIDE
    {
      resourceHierarchy_->Invalidate(level, id);
    }

#if BUILD_UNIT_TESTS == 1
    FRIEND_TEST(DefaultAuthorizationParser, Parse);
  protected:
    ResourceHierarchyCache* GetResourceHierarchy()
    {
      return resourceHierarchy_.get();
    }
#endif
  };
}
