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


#include "DicomWebServers.h"

#include "Configuration.h"

#include <Compatibility.h>
#include <Toolbox.h>
#include <Logging.h>

#include <boost/algorithm/string/predicate.hpp>

namespace OrthancPlugins
{
  void DicomWebServers::Clear()
  {
    for (Servers::iterator it = servers_.begin(); it != servers_.end(); ++it)
    {
      assert(it->second != NULL);
      delete it->second;
    }

    servers_.clear();
  }


  void DicomWebServers::LoadGlobalConfiguration(const Json::Value& servers)
  {
    boost::mutex::scoped_lock lock(mutex_);

    Clear();

    bool ok = true;

    try
    {
      if (servers.type() != Json::objectValue)
      {
        ok = false;
      }
      else
      {
        Json::Value::Members members = servers.getMemberNames();

        for (size_t i = 0; i < members.size(); i++)
        {
          std::unique_ptr<Orthanc::WebServiceParameters> parameters
            (new Orthanc::WebServiceParameters(servers[members[i]]));

          servers_[members[i]] = parameters.release();
        }
      }
    }
    catch (Orthanc::OrthancException& e)
    {
      LOG(ERROR) << "Exception while parsing the \"DicomWeb.Servers\" section "
                    "of the configuration file: " + std::string(e.What());
      throw;
    }

    if (!ok)
    {
      throw Orthanc::OrthancException(
        Orthanc::ErrorCode_BadFileFormat,
        "Cannot parse the \"DicomWeb.Servers\" section of the configuration file");
    }
  }


  DicomWebServers& DicomWebServers::GetInstance()
  {
    static DicomWebServers singleton;
    return singleton;
  }


  Orthanc::WebServiceParameters DicomWebServers::GetServer(const std::string& name)
  {
    boost::mutex::scoped_lock lock(mutex_);
    Servers::const_iterator server = servers_.find(name);

    if (server == servers_.end() ||
        server->second == NULL)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_InexistentItem,
                                      "Inexistent server: " + name);
    }
    else
    {
      return *server->second;
    }
  }


  void DicomWebServers::ListServers(std::list<std::string>& servers)
  {
    boost::mutex::scoped_lock lock(mutex_);

    servers.clear();
    for (Servers::const_iterator it = servers_.begin(); it != servers_.end(); ++it)
    {
      assert(it->second != NULL);
      servers.push_back(it->first);
    }
  }


  void DicomWebServers::ConfigureHttpClient(HttpClient& client,
                                            std::map<std::string, std::string>& userProperties,
                                            const std::string& name,
                                            const std::string& uri)
  {
    static const char* HAS_CHUNKED_TRANSFERS = "ChunkedTransfers";
    
    const Orthanc::WebServiceParameters parameters = GetServer(name);

    client.SetUrl(RemoveMultipleSlashes(parameters.GetUrl() + "/" + uri));
    client.SetHeaders(parameters.GetHttpHeaders());

    if (!parameters.GetUsername().empty())
    {
      client.SetCredentials(parameters.GetUsername(), parameters.GetPassword());
    }

    if (!parameters.GetCertificateFile().empty())
    {
      client.SetCertificate(
        parameters.GetCertificateFile(),
        parameters.GetCertificateKeyFile(),
        parameters.GetCertificateKeyPassword());
    }

    client.SetPkcs11(parameters.IsPkcs11Enabled());

    // By default, enable chunked transfers
    client.SetChunkedTransfersAllowed(
      parameters.GetBooleanUserProperty(HAS_CHUNKED_TRANSFERS, true));

    userProperties = parameters.GetUserProperties();

    if (parameters.HasTimeout())
    {
      client.SetTimeout(parameters.GetTimeout());
    }
  }


  void DicomWebServers::DeleteServer(const std::string& name)
  {
    boost::mutex::scoped_lock lock(mutex_);

    Servers::iterator found = servers_.find(name);

    if (found == servers_.end())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange,
                                      "Unknown DICOMweb server: " + name);
    }
    else
    {
      assert(found->second != NULL);
      delete found->second;
      servers_.erase(found);
    }
  }


  void DicomWebServers::SetServer(const std::string& name,
                                  const Orthanc::WebServiceParameters& parameters)
  {
    boost::mutex::scoped_lock lock(mutex_);

    Servers::iterator found = servers_.find(name);

    if (found != servers_.end())
    {
      assert(found->second != NULL);
      delete found->second;
      servers_.erase(found);
    }

    servers_[name] = new Orthanc::WebServiceParameters(parameters);
  }

  

  static const char* ConvertToCString(const std::string& s)
  {
    if (s.empty())
    {
      return NULL;
    }
    else
    {
      return s.c_str();
    }
  }



  void CallServer(MemoryBuffer& answerBody /* out */,
                  std::map<std::string, std::string>& answerHeaders /* out */,
                  const Orthanc::WebServiceParameters& server,
                  OrthancPluginHttpMethod method,
                  const std::map<std::string, std::string>& httpHeaders,
                  const std::string& uri,
                  const std::string& body)
  {
    answerBody.Clear();
    answerHeaders.clear();

    std::string url = server.GetUrl();
    assert(!url.empty() && url[url.size() - 1] == '/');

    // Remove the leading "/" in the URI if need be
    if (!uri.empty() &&
        uri[0] == '/')
    {
      url += uri.substr(1);
    }
    else
    {
      url += uri;
    }

    std::map<std::string, std::string> allHttpHeaders = server.GetHttpHeaders();
    
    {
      // Add the user-specified HTTP headers to the HTTP headers
      // coming from the Orthanc configuration file
      for (std::map<std::string, std::string>::const_iterator
             it = httpHeaders.begin(); it != httpHeaders.end(); ++it)
      {
        allHttpHeaders[it->first] = it->second;
      }
    }

    std::vector<const char*> httpHeadersKeys(allHttpHeaders.size());
    std::vector<const char*> httpHeadersValues(allHttpHeaders.size());

    {
      size_t pos = 0;
      for (std::map<std::string, std::string>::const_iterator
             it = allHttpHeaders.begin(); it != allHttpHeaders.end(); ++it)
      {
        httpHeadersKeys[pos] = it->first.c_str();
        httpHeadersValues[pos] = it->second.c_str();
        pos += 1;
      }

      assert(pos == allHttpHeaders.size());
    }

    const char* bodyContent = NULL;
    size_t bodySize = 0;

    if ((method == OrthancPluginHttpMethod_Put ||
         method == OrthancPluginHttpMethod_Post) &&
        !body.empty())
    {
      bodyContent = body.c_str();
      bodySize = body.size();
    }

    OrthancPluginContext* context = GetGlobalContext();

    uint16_t status = 0;
    MemoryBuffer answerHeadersTmp;
    OrthancPluginErrorCode code = OrthancPluginHttpClient(
      context, 
      /* Outputs */
      *answerBody, *answerHeadersTmp, &status, 
      method,
      url.c_str(), 
      /* HTTP headers*/
      allHttpHeaders.size(),
      httpHeadersKeys.empty() ? NULL : &httpHeadersKeys[0],
      httpHeadersValues.empty() ? NULL : &httpHeadersValues[0],
      bodyContent, bodySize,
      ConvertToCString(server.GetUsername()), /* Authentication */
      ConvertToCString(server.GetPassword()), 
      0,                                      /* Timeout */
      ConvertToCString(server.GetCertificateFile()),
      ConvertToCString(server.GetCertificateKeyFile()),
      ConvertToCString(server.GetCertificateKeyPassword()),
      server.IsPkcs11Enabled() ? 1 : 0);

    if (code != OrthancPluginErrorCode_Success ||
        (status < 200 || status >= 300))
    {
      throw Orthanc::OrthancException(
        static_cast<Orthanc::ErrorCode>(code),
        "Cannot issue an HTTP query to " + url + 
        " (HTTP status: " + boost::lexical_cast<std::string>(status) + ")");
    }

    Json::Value json;
    answerHeadersTmp.ToJson(json);
    answerHeadersTmp.Clear();

    if (json.type() != Json::objectValue)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
    }

    Json::Value::Members members = json.getMemberNames();
    for (size_t i = 0; i < members.size(); i++)
    {
      const std::string& key = members[i];

      if (json[key].type() != Json::stringValue)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
      }
      else
      {
        answerHeaders[key] = json[key].asString();        
      }
    }
  }


  void DicomWebServers::UriEncode(std::string& uri,
                                  const std::string& resource,
                                  const std::map<std::string, std::string>& getArguments)
  {
    if (resource.find('?') != std::string::npos)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat,
                                      "The GET arguments must be provided in a separate field "
                                      "(explicit \"?\" is disallowed): " + resource);
    }

    uri = resource;

    bool isFirst = true;
    for (std::map<std::string, std::string>::const_iterator
           it = getArguments.begin(); it != getArguments.end(); ++it)
    {
      if (isFirst)
      {
        uri += '?';
        isFirst = false;
      }
      else
      {
        uri += '&';
      }

      std::string key, value;
      Orthanc::Toolbox::UriEncode(key, it->first);
      Orthanc::Toolbox::UriEncode(value, it->second);

      if (value.empty())
      {
        uri += key;
      }
      else
      {
        uri += key + "=" + value;
      }
    }
  }


  void DicomWebServers::SerializeGlobalProperty(std::string& target)
  {
    boost::mutex::scoped_lock lock(mutex_);

    Json::Value json = Json::objectValue;

    for (Servers::const_iterator it = servers_.begin(); it != servers_.end(); ++it)
    {
      assert(it->second != NULL);

      Json::Value server;
      it->second->Serialize(server, true /* advanced format */, true /* store passwords */);
      json[it->first] = server;
    }

    OrthancPlugins::WriteFastJson(target, json);
  }


  void DicomWebServers::UnserializeGlobalProperty(const std::string& source)
  {
    Json::Value json;
    
    if (!OrthancPlugins::ReadJson(json, source) ||
        json.type() != Json::objectValue)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat, "Cannot unserialize "
                                      "the list of DICOMweb servers from global properties");
    }

    Clear();

    std::vector<std::string> members = json.getMemberNames();
    
    for (size_t i = 0; i < members.size(); i++)
    {
      const std::string& name = members[i];
      
      std::unique_ptr<Orthanc::WebServiceParameters> server(new Orthanc::WebServiceParameters);
      server->Unserialize(json[name]);

      assert(servers_.find(name) == servers_.end());
      servers_[name] = server.release();
    }
  }
}
