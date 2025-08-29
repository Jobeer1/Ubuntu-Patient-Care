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

#include "AccessedResource.h"

#include <boost/noncopyable.hpp>
#include <boost/regex.hpp>
#include <list>
#include <map>
#include <vector>

namespace OrthancPlugins
{
  // NOTE: This interface must be thread-safe 
  class IAuthorizationParser : public boost::noncopyable
  {
  public:
    typedef std::list<AccessedResource>  AccessedResources;
    
    virtual ~IAuthorizationParser()
    {
    }

    virtual void Invalidate(Orthanc::ResourceType level,
                            const std::string& id) = 0;

    virtual bool Parse(AccessedResources& target,
                       const std::string& uri,
                       const std::map<std::string, std::string>& getArguments) = 0;

    virtual bool IsListOfResources(const std::string& uri) const = 0;

    virtual void GetSingleResourcePatterns(std::vector<boost::regex>& patterns) const = 0;

    virtual void AddDicomStudy(AccessedResources& target,
                               const std::string& studyDicomUid) = 0;

  };
}
