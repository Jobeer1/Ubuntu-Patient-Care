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

#include <WebServiceParameters.h>

#include <list>
#include <string>
#include <boost/thread/mutex.hpp>
#include <json/value.h>

namespace OrthancPlugins
{
  class DicomWebServers : public boost::noncopyable
  {
  private:
    typedef std::map<std::string, Orthanc::WebServiceParameters*>  Servers;

    boost::mutex  mutex_;
    Servers       servers_;

    DicomWebServers()  // Forbidden (singleton pattern)
    {
    }

  public:
    ~DicomWebServers()
    {
      Clear();
    }
    
    static void UriEncode(std::string& uri,
                          const std::string& resource,
                          const std::map<std::string, std::string>& getArguments);

    void Clear();

    void LoadGlobalConfiguration(const Json::Value& configuration);

    static DicomWebServers& GetInstance();

    Orthanc::WebServiceParameters GetServer(const std::string& name);

    void ListServers(std::list<std::string>& servers);

    void ConfigureHttpClient(HttpClient& client,
                             std::map<std::string, std::string>& userProperties,
                             const std::string& name,
                             const std::string& uri);

    void DeleteServer(const std::string& name);

    void SetServer(const std::string& name,
                   const Orthanc::WebServiceParameters& parameters);

    void SerializeGlobalProperty(std::string& target);

    void UnserializeGlobalProperty(const std::string& source);
  };


  void CallServer(MemoryBuffer& answerBody /* out */,
                  std::map<std::string, std::string>& answerHeaders /* out */,
                  const Orthanc::WebServiceParameters& server,
                  OrthancPluginHttpMethod method,
                  const std::map<std::string, std::string>& httpHeaders,
                  const std::string& uri,
                  const std::string& body);
}
