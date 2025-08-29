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

#include "ICacheFactory.h"
#include "Enumerations.h"
#include "OrthancResource.h"

#include <Compatibility.h>  // For std::unique_ptr<>

#include <orthanc/OrthancCPlugin.h>

#if BUILD_UNIT_TESTS == 1
#  include <gtest/gtest_prod.h>
#endif

namespace OrthancPlugins
{
  class ResourceHierarchyCache : public boost::noncopyable
  {
  private:
    std::unique_ptr<ICache>   cache_;   // Maps resources to their parents
    std::unique_ptr<ICache>   orthancToDicom_;
    std::unique_ptr<ICache>   dicomToOrthanc_;
    std::unique_ptr<ICache>   labels_;

    std::string ComputeKey(Orthanc::ResourceType level,
                           const std::string& identifier) const;
    
    std::string ComputeKey(const OrthancResource& resource) const
    {
      return ComputeKey(resource.GetLevel(), resource.GetIdentifier());
    }

    void LinkParent(const OrthancResource& child,
                    const OrthancResource& parent);

    bool LookupParent(std::string& target,
                      const OrthancResource& resource);

    bool LookupParent(std::string& target,
                      Orthanc::ResourceType level,
                      const std::string& identifier)
    {
      return LookupParent(target, OrthancResource(level, identifier));
    }

    void UpdateResourceFromOrthanc(OrthancResource& parent,
                                   std::set<std::string>& labels,
                                   const OrthancResource& resource);

  public:
    explicit ResourceHierarchyCache(ICacheFactory& factory);

    void Invalidate(Orthanc::ResourceType level,
                    const std::string& identifier);

    bool LookupStudy(std::string& patient,
                     const std::string& study)
    {
      return LookupParent(patient, Orthanc::ResourceType_Study, study);
    }

    bool LookupSeries(std::string& patient,
                      std::string& study,
                      const std::string& series);

    bool LookupInstance(std::string& patient,
                        std::string& study,
                        std::string& series,
                        const std::string& instance);

    bool LookupDicomUid(std::string& target,
                        Orthanc::ResourceType level,
                        const std::string& orthancId);

    bool LookupOrthancId(std::string& target,
                         Orthanc::ResourceType level,
                         const std::string& dicomUid);

    void GetLabels(std::set<std::string>& labels,
                   const OrthancResource& resource);

#if BUILD_UNIT_TESTS == 1
    FRIEND_TEST(DefaultAuthorizationParser, Parse);
  protected:
    void AddOrthancDicomMapping(Orthanc::ResourceType level,
                                const std::string& orthancId,
                                const std::string& dicomUid);

    void AddParentLink(Orthanc::ResourceType childLevel,
                       const std::string& childOrthancId,
                       const std::string& parentOrthancId);

    void AddLabels(Orthanc::ResourceType level,
                   const std::string& orthancId,
                   const std::string& serializedLabels);
#endif
  };
}
