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

#include "AuthorizationParserBase.h"

#include <boost/regex.hpp>
#include <boost/thread/mutex.hpp>

namespace OrthancPlugins
{
  class PermissionPattern : public boost::noncopyable
  {
  private:
    OrthancPluginHttpMethod   method_;
    boost::regex              pattern_;
    std::set<std::string>     permissions_;

  public:
    PermissionPattern(const OrthancPluginHttpMethod& method,
                      const std::string& patternRegex,
                      const std::string& permissions);

    OrthancPluginHttpMethod GetMethod() const
    {
      return method_;
    }

    const boost::regex& GetPattern() const
    {
      return pattern_;
    }

    const std::set<std::string>& GetPermissions() const
    {
      return permissions_;
    }
  };

  class PermissionParser : public boost::noncopyable
  { 
  private:
    mutable boost::mutex mutex_; 
    std::list<PermissionPattern*> permissionsPattern_;
    std::set<std::string> permissionsList_;
    std::string dicomWebRoot_;
    std::string oe2Root_;

  public:
    PermissionParser(const std::string& dicomWebRoot,
                     const std::string& oe2Root);

    ~PermissionParser();

    void Add(const std::string& method,
             const std::string& patternRegex,
             const std::string& permission);

    void Add(const Json::Value& configuration, const IAuthorizationParser* authorizationParser);

    bool Parse(std::set<std::string>& permissions,
               std::string& matchedPattern,
               const OrthancPluginHttpMethod& method,
               const std::string& uri) const;

    const std::set<std::string>& GetPermissionsList() const
    {
      return permissionsList_;
    }
  };
}
