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

#include "IHttpQuery.h"
#include "../TransferToolbox.h"

#include <Compatibility.h>

#include <map>


namespace OrthancPlugins
{
  class DetectTransferPlugin : public IHttpQuery
  {
  public:
    typedef std::map<std::string, bool>  Result;
    
  private:
    Result&      result_;
    std::string  peer_;
    std::string  uri_;

  public:
    DetectTransferPlugin(Result& result,
                         const std::string& peer);

    virtual Orthanc::HttpMethod GetMethod() const ORTHANC_OVERRIDE
    {
      return Orthanc::HttpMethod_Get;
    }

    virtual const std::string& GetPeer() const ORTHANC_OVERRIDE
    {
      return peer_;
    }

    virtual const std::string& GetUri() const ORTHANC_OVERRIDE
    {
      return uri_;
    }

    virtual void ReadBody(std::string& body) const ORTHANC_OVERRIDE;

    virtual void HandleAnswer(const void* answer,
                              size_t size) ORTHANC_OVERRIDE;

    virtual void GetHttpHeaders(std::map<std::string, std::string>& headers) const ORTHANC_OVERRIDE
    {/* no headers for this general purpose request*/}

    static void Apply(Result& result,
                      size_t threadsCount,
                      unsigned int timeout);
  };
}
