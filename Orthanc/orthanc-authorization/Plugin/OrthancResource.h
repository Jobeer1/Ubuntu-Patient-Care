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

#include "Enumerations.h"

#include <orthanc/OrthancCPlugin.h>
#include <json/value.h>
#include <list>

namespace OrthancPlugins
{
  class OrthancResource
  {
  private:
    bool                  isValid_;
    Orthanc::ResourceType level_;
    std::string           id_;

    static void GetDicomUidInternal(std::string& result,
                                    Orthanc::ResourceType level,
                                    const Json::Value& content);

  public:
    OrthancResource() :
      isValid_(false)
    {
    }
    
    OrthancResource(Orthanc::ResourceType level,
                    const std::string& id) :
      isValid_(true),
      level_(level),
      id_(id)
    {
    }

    bool IsValid() const
    {
      return isValid_;
    }

    Orthanc::ResourceType GetLevel() const;

    const std::string& GetIdentifier() const;

    bool GetContent(Json::Value& content) const;

    bool GetDicomUid(std::string& dicomUid /* out */) const;
    
    bool GetHierarchy(std::string& dicomUid /* out */,
                      OrthancResource& parent /* out */,
                      std::list<OrthancResource>& children /* out */,
                      std::set<std::string>& labels /* out */) const;

    static bool LookupOrthancId(std::string& result,
                                Orthanc::ResourceType level,
                                const std::string& dicomUid);
  };
}
