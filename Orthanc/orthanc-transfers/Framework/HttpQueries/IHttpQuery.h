/**
 * Transfers accelerator plugin for Orthanc
 * Copyright (C) 2018-2023 Osimis S.A., Belgium
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

#include <Enumerations.h>
#include <map>

#include <boost/noncopyable.hpp>


namespace OrthancPlugins
{
  class IHttpQuery : public boost::noncopyable
  {
  public:
    virtual ~IHttpQuery()
    {
    }

    virtual Orthanc::HttpMethod GetMethod() const = 0;

    virtual const std::string& GetPeer() const = 0;

    virtual const std::string& GetUri() const = 0;

    virtual void ReadBody(std::string& body) const = 0;   // Only for PUT/POST

    virtual void HandleAnswer(const void* answer,
                              size_t size) = 0;

    virtual void GetHttpHeaders(std::map<std::string, std::string>& headers) const = 0;
  };
}
