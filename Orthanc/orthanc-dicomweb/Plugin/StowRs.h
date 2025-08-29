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

#include "../Resources/Orthanc/Plugins/OrthancPluginCppWrapper.h"

#include <Compatibility.h>
#include <HttpServer/MultipartStreamReader.h>

namespace OrthancPlugins
{
  class StowServer : 
    public IChunkedRequestReader,
    private Orthanc::MultipartStreamReader::IHandler
  {
  private:
    OrthancPluginContext*  context_;
    bool                   xml_;
    std::string            wadoBasePublicUrl_;
    std::string            expectedStudy_;
    bool                   isFirst_;
    Json::Value            result_;
    Json::Value            success_;
    Json::Value            failed_;
    bool                   hasBadSyntax_;
    bool                   hasConflict_;
    std::map<std::string, std::string> headers_;

    std::unique_ptr<Orthanc::MultipartStreamReader>  parser_;

    virtual void HandlePart(const Orthanc::MultipartStreamReader::HttpHeaders& headers,
                            const void* part,
                            size_t size) ORTHANC_OVERRIDE;

  public:
    StowServer(OrthancPluginContext* context,
               const std::map<std::string, std::string>& headers,
               const std::string& expectedStudy);

    virtual void AddChunk(const void* data,
                          size_t size) ORTHANC_OVERRIDE;

    virtual void Execute(OrthancPluginRestOutput* output) ORTHANC_OVERRIDE;

    static IChunkedRequestReader* PostCallback(const char* url,
                                               const OrthancPluginHttpRequest* request);
  };
}
