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

#include <boost/noncopyable.hpp>
#include <string>

namespace OrthancPlugins
{
  class ICache : public boost::noncopyable
  {
  public:
    virtual ~ICache()
    {
    }

    virtual void Store(const std::string& key,
                       const std::string& value,
                       unsigned int validity /* in seconds */) = 0;

    virtual void Invalidate(const std::string& key) = 0;

    virtual bool Retrieve(std::string& value,
                          const std::string& key) = 0;
  };
}
