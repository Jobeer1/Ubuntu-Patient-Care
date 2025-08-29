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
  class DefaultAuthorizationParser : public AuthorizationParserBase
  { 
  private:
    mutable boost::mutex mutex_; 
    boost::regex resourcesPattern_;
    boost::regex seriesPattern_;
    boost::regex instancesPattern_;
    boost::regex dicomWebStudies_;
    boost::regex dicomWebSeries_;
    boost::regex dicomWebInstances_;
    boost::regex dicomWebQidoRsFind_;

    boost::regex osimisViewerSeries_;
    boost::regex osimisViewerImages_;
    boost::regex osimisViewerStudies_;

    boost::regex listOfResourcesPattern_;
    boost::regex createBulkPattern_;

  public:
    DefaultAuthorizationParser(ICacheFactory& factory,
                               const std::string& dicomWebRoot);

    virtual bool Parse(AccessedResources& target,
                       const std::string& uri,
                       const std::map<std::string, std::string>& getArguments) ORTHANC_OVERRIDE;

    virtual bool IsListOfResources(const std::string& uri) const ORTHANC_OVERRIDE;

    virtual void GetSingleResourcePatterns(std::vector<boost::regex>& patterns) const ORTHANC_OVERRIDE;
  };
}
