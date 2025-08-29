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


#include "Configuration.h"

#include "../Resources/Orthanc/Plugins/OrthancPluginCppWrapper.h"
#include "DicomWebServers.h"
#include <DicomFormat/DicomMap.h>

#include <Compatibility.h>
#include <Logging.h>
#include <Toolbox.h>

#include <fstream>
#include <boost/regex.hpp>
#include <boost/lexical_cast.hpp>
#include <boost/algorithm/string/predicate.hpp>


// Assume Latin-1 encoding by default (as in the Orthanc core)
static Orthanc::Encoding defaultEncoding_ = Orthanc::Encoding_Latin1;
static std::unique_ptr<OrthancPlugins::OrthancConfiguration> dicomWebConfiguration_;
static std::unique_ptr<OrthancPlugins::OrthancConfiguration> globalConfiguration_;
static bool serversInDatabase_ = false;
static const int32_t GLOBAL_PROPERTY_SERVERS = 5468;


namespace OrthancPlugins
{
  bool LookupHttpHeader(std::string& value,
                        const OrthancPluginHttpRequest* request,
                        const std::string& header)
  {
    value.clear();

    for (uint32_t i = 0; i < request->headersCount; i++)
    {
      std::string s = request->headersKeys[i];
      Orthanc::Toolbox::ToLowerCase(s);
      if (s == header)
      {
        value = request->headersValues[i];
        return true;
      }
    }

    return false;
  }


  void ParseAssociativeArray(std::map<std::string, std::string>& target,
                             const Json::Value& value)
  {
    if (value.type() != Json::objectValue)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat,
                                      "The JSON object is not a JSON associative array as expected");
    }

    Json::Value::Members names = value.getMemberNames();

    for (size_t i = 0; i < names.size(); i++)
    {
      if (value[names[i]].type() != Json::stringValue)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat,
                                        "Value \"" + names[i] + "\" in the associative array "
                                        "is not a string as expected");
      }
      else
      {
        target[names[i]] = value[names[i]].asString();
      }
    }
  }
  

  void ParseAssociativeArray(std::map<std::string, std::string>& target,
                             const Json::Value& value,
                             const std::string& key)
  {
    if (value.type() != Json::objectValue)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat,
                                      "This is not a JSON object");
    }

    if (value.isMember(key))
    {
      ParseAssociativeArray(target, value[key]);
    }
    else
    {
      target.clear();
    }
  }


  bool ParseTag(Orthanc::DicomTag& target,
                const std::string& name)
  {
    OrthancPluginDictionaryEntry entry;
    
    if (OrthancPluginLookupDictionary(GetGlobalContext(), &entry, name.c_str()) == OrthancPluginErrorCode_Success)
    {
      target = Orthanc::DicomTag(entry.group, entry.element);
      return true;
    }
    else
    {
      return false;
    }
  }


  void ParseJsonBody(Json::Value& target,
                     const OrthancPluginHttpRequest* request)
  {
    if (!OrthancPlugins::ReadJson(target, request->body, request->bodySize))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat,
                                      "A JSON file was expected");
    }
  }


  std::string RemoveMultipleSlashes(const std::string& source)
  {
    std::string target;
    target.reserve(source.size());

    size_t prefix = 0;
  
    if (boost::starts_with(source, "https://"))
    {
      prefix = 8;
    }
    else if (boost::starts_with(source, "http://"))
    {
      prefix = 7;
    }

    for (size_t i = 0; i < prefix; i++)
    {
      target.push_back(source[i]);
    }

    bool isLastSlash = false;

    for (size_t i = prefix; i < source.size(); i++)
    {
      if (source[i] == '/')
      {
        if (!isLastSlash)
        {
          target.push_back('/');
          isLastSlash = true;
        }
      }
      else
      {
        target.push_back(source[i]);
        isLastSlash = false;
      }
    }

    return target;
  }


  bool LookupStringValue(std::string& target,
                         const Json::Value& json,
                         const std::string& key)
  {
    if (json.type() != Json::objectValue)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
    }
    else if (!json.isMember(key))
    {
      return false;
    }
    else if (json[key].type() != Json::stringValue)
    {
      throw Orthanc::OrthancException(
        Orthanc::ErrorCode_BadFileFormat,
        "The field \"" + key + "\" in a JSON object should be a string");
    }
    else
    {
      target = json[key].asString();
      return true;
    }
  }


  bool LookupIntegerValue(int& target,
                          const Json::Value& json,
                          const std::string& key)
  {
    if (json.type() != Json::objectValue)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
    }
    else if (!json.isMember(key))
    {
      return false;
    }
    else if (json[key].type() != Json::intValue &&
             json[key].type() != Json::uintValue)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);      
    }
    else
    {
      target = json[key].asInt();
      return true;
    }
  }


  bool LookupBooleanValue(bool& target,
                          const Json::Value& json,
                          const std::string& key)
  {
    if (json.type() != Json::objectValue)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
    }
    else if (!json.isMember(key))
    {
      return false;
    }
    else if (json[key].type() != Json::booleanValue)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);      
    }
    else
    {
      target = json[key].asBool();
      return true;
    }
  }


  namespace Configuration
  {
    // TODO: find a way to reuse/share the method from/with the Orthanc Core
    void LoadMainDicomTags(const Json::Value& configuration)
    {
      static const char* const EXTRA_MAIN_DICOM_TAGS = "ExtraMainDicomTags";

      // note: the configuration is assumed to be valid since it has already been parsed by the Orthanc Core
      Json::Value::Members levels(configuration[EXTRA_MAIN_DICOM_TAGS].getMemberNames());

      for (Json::Value::ArrayIndex i = 0; i < levels.size(); i++)
      {
        Orthanc::ResourceType level = Orthanc::StringToResourceType(levels[i].c_str());

        const Json::Value& content = configuration[EXTRA_MAIN_DICOM_TAGS][levels[i]];
        std::set<Orthanc::DicomTag> defaultTags;
        Orthanc::DicomMap::GetMainDicomTags(defaultTags, level);

        if (content.size() > 0)
        {
          for (Json::Value::ArrayIndex t = 0; t < content.size(); t++)
          {
            const std::string& tagName = content[t].asString();
            Orthanc::DicomTag tag(0, 0);
            OrthancPlugins::ParseTag(tag, tagName);
            if (defaultTags.find(tag) == defaultTags.end()) // don't generate an error if the ExtraMainDicomTags is now a default one
            {
              Orthanc::DicomMap::AddMainDicomTag(tag, level);
            }
          }
        }
      }
    }

    void Initialize()
    {
      dicomWebConfiguration_.reset(new OrthancConfiguration);
      globalConfiguration_.reset(new OrthancConfiguration);

      globalConfiguration_->GetSection(*dicomWebConfiguration_, "DicomWeb");

      std::string s;
      if (globalConfiguration_->LookupStringValue(s, "DefaultEncoding"))
      {
        defaultEncoding_ = Orthanc::StringToEncoding(s.c_str());
      }

      if (!dicomWebConfiguration_->LookupBooleanValue(serversInDatabase_, "ServersInDatabase"))
      {
        serversInDatabase_ = false;
      }

      if (serversInDatabase_)
      {
        LOG(INFO) << "The DICOMweb plugin stores the DICOMweb servers in the Orthanc database";
      }
      else
      {
        LOG(INFO) << "The DICOMweb plugin reads the DICOMweb servers from the configuration file";
      }

      DicomWebServers::GetInstance().Clear();
        
      // Check configuration during initialization
      GetMetadataMode(Orthanc::ResourceType_Study);
      GetMetadataMode(Orthanc::ResourceType_Series);

      std::set<Orthanc::DicomTag> tags;
      GetExtrapolatedMetadataTags(tags, Orthanc::ResourceType_Study);
      GetExtrapolatedMetadataTags(tags, Orthanc::ResourceType_Series);

      LoadMainDicomTags(globalConfiguration_->GetJson());
    }


    std::string GetStringValue(const std::string& key,
                               const std::string& defaultValue)
    {
      assert(dicomWebConfiguration_.get() != NULL);
      return dicomWebConfiguration_->GetStringValue(key, defaultValue);
    }


    bool GetBooleanValue(const std::string& key,
                         bool defaultValue)
    {
      assert(dicomWebConfiguration_.get() != NULL);
      return dicomWebConfiguration_->GetBooleanValue(key, defaultValue);
    }


    bool LookupBooleanValue(bool& target,
                            const std::string& key)
    {
      assert(dicomWebConfiguration_.get() != NULL);
      return dicomWebConfiguration_->LookupBooleanValue(target, key);
    }


    unsigned int GetUnsignedIntegerValue(const std::string& key,
                                         unsigned int defaultValue)
    {
      assert(dicomWebConfiguration_.get() != NULL);
      return dicomWebConfiguration_->GetUnsignedIntegerValue(key, defaultValue);
    }

    std::string GetRootPath(const char* configName, const char* defaultValue)
    {
      assert(dicomWebConfiguration_.get() != NULL);
      std::string root = dicomWebConfiguration_->GetStringValue(configName, defaultValue);

      // Make sure the root URI starts and ends with a slash
      if (root.size() == 0 ||
          root[0] != '/')
      {
        root = "/" + root;
      }
    
      if (root[root.length() - 1] != '/')
      {
        root += "/";
      }

      return root;
    }

    std::string GetDicomWebRoot()
    {
      return GetRootPath("Root", "/dicom-web/");
    }

    std::string GetPublicRoot()
    {
      std::string root = GetDicomWebRoot();
      return GetRootPath("PublicRoot", root.c_str());
    }

    std::string GetOrthancApiRoot()
    {
      std::string root = Configuration::GetDicomWebRoot();
      std::vector<std::string> tokens;
      Orthanc::Toolbox::TokenizeString(tokens, root, '/');

      int depth = 0;
      for (size_t i = 0; i < tokens.size(); i++)
      {
        if (tokens[i].empty() ||
            tokens[i] == ".")
        {
          // Don't change the depth
        }
        else if (tokens[i] == "..")
        {
          depth--;
        }
        else
        {
          depth++;
        }
      }

      std::string orthancRoot = "./";
      for (int i = 0; i < depth; i++)
      {
        orthancRoot += "../";
      }

      return orthancRoot;
    }


    std::string GetWadoRoot()
    {
      assert(dicomWebConfiguration_.get() != NULL);
      std::string root = dicomWebConfiguration_->GetStringValue("WadoRoot", "/wado/");

      // Make sure the root URI starts with a slash
      if (root.size() == 0 ||
          root[0] != '/')
      {
        root = "/" + root;
      }

      // Remove the trailing slash, if any
      if (root[root.length() - 1] == '/')
      {
        root = root.substr(0, root.length() - 1);
      }

      return root;
    }


    static bool IsHttpsProto(const std::string& proto,
                             bool defaultValue)
    {
      if (proto == "http")
      {
        return false;
      }
      else if (proto == "https")
      {
        return true;
      }
      else
      {
        return defaultValue;
      }
    }


    static bool LookupHttpHeader2(std::string& value,
                                  const HttpHeaders& headers,
                                  const std::string& name)
    {
      for (HttpHeaders::const_iterator it = headers.begin(); it != headers.end(); ++it)
      {
        if (boost::iequals(it->first, name))
        {
          value = it->second;
          return true;
        }
      }

      return false;
    }


    std::string GetBasePublicUrl(const HttpHeaders& headers)
    {
      assert(dicomWebConfiguration_.get() != NULL);
      std::string host = dicomWebConfiguration_->GetStringValue("Host", "");
      bool https = dicomWebConfiguration_->GetBooleanValue("Ssl", false);

      std::string forwardedHost, forwardedProto;
      if (host.empty() &&
          LookupHttpHeader2(forwardedHost, headers, "x-forwarded-host") &&
          LookupHttpHeader2(forwardedProto, headers, "x-forwarded-proto"))
      {
        // There is a "X-Forwarded-Proto" and a "X-Forwarded-Host" HTTP header in the query
        // https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-Forwarded-Proto
        
        host = Orthanc::Toolbox::StripSpaces(forwardedHost);
        https = IsHttpsProto(Orthanc::Toolbox::StripSpaces(forwardedProto), https);
      }

      std::string forwarded;
      if (host.empty() &&
          LookupHttpHeader2(forwarded, headers, "forwarded"))
      {
        // There is a "Forwarded" HTTP header in the query
        // https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Forwarded
        
        std::vector<std::string> forwarders;
        Orthanc::Toolbox::TokenizeString(forwarders, forwarded, ',');

        // Only consider the first forwarder, if any
        if (!forwarders.empty())
        {
          std::vector<std::string> tokens;
          Orthanc::Toolbox::TokenizeString(tokens, forwarders[0], ';');

          for (size_t j = 0; j < tokens.size(); j++)
          {
            std::vector<std::string> args;
            Orthanc::Toolbox::TokenizeString(args, tokens[j], '=');
            
            if (args.size() == 2)
            {
              std::string key = Orthanc::Toolbox::StripSpaces(args[0]);
              std::string value = Orthanc::Toolbox::StripSpaces(args[1]);

              Orthanc::Toolbox::ToLowerCase(key);
              if (key == "host")
              {
                host = value;
              }
              else if (key == "proto")
              {
                https = IsHttpsProto(value, https);
              }
            }
          }
        }
      }

      if (host.empty() &&
          !LookupHttpHeader2(host, headers, "host"))
      {
        // Should never happen: The "host" header should always be present
        // in HTTP requests. Provide a default value anyway.
        host = "localhost:8042";
      }

      return (https ? "https://" : "http://") + host + GetPublicRoot();
    }

    std::string GetBasePublicUrl(const OrthancPluginHttpRequest* request)
    {
      HttpHeaders headers;

      std::string value;
      if (LookupHttpHeader(value, request, "forwarded"))
      {
        headers["Forwarded"] = value;
      }

      if (LookupHttpHeader(value, request, "host"))
      {
        headers["Host"] = value;
      }

      if (LookupHttpHeader(value, request, "x-forwarded-host"))
      {
        headers["X-Forwarded-Host"] = value;
      }

      if (LookupHttpHeader(value, request, "x-forwarded-proto"))
      {
        headers["X-Forwarded-Proto"] = value;
      }

      if (LookupHttpHeader(value, request, "host"))
      {
        headers["Host"] = value;
      }

      return GetBasePublicUrl(headers);
    }


    std::string GetWadoUrl(const std::string& wadoBase,
                           const std::string& studyInstanceUid,
                           const std::string& seriesInstanceUid,
                           const std::string& sopInstanceUid)
    {
      if (studyInstanceUid.empty() ||
          seriesInstanceUid.empty() ||
          sopInstanceUid.empty())
      {
        return "";
      }
      else
      {
        return (wadoBase + 
                "studies/" + studyInstanceUid + 
                "/series/" + seriesInstanceUid + 
                "/instances/" + sopInstanceUid + "/");
      }
    }


    Orthanc::Encoding GetDefaultEncoding()
    {
      return defaultEncoding_;
    }


    static bool IsXmlExpected(const std::string& acceptHeader)
    {
      std::string accept;
      Orthanc::Toolbox::ToLowerCase(accept, acceptHeader);
  
      if (accept == "application/dicom+json" ||
          accept == "application/json" ||
          accept == "*/*")
      {
        return false;
      }
      else if (accept == "application/dicom+xml" ||
               accept == "application/xml" ||
               accept == "text/xml")
      {
        return true;
      }
      else
      {
        LOG(ERROR) << "Unsupported return MIME type: " << accept <<
                      ", will return DICOM+JSON";
        return false;
      }
    }


    bool IsXmlExpected(const std::map<std::string, std::string>& headers)
    {
      std::map<std::string, std::string>::const_iterator found = headers.find("accept");

      if (found == headers.end())
      {
        return false;   // By default, return DICOM+JSON
      }
      else
      {
        return IsXmlExpected(found->second);
      }
    }


    bool IsXmlExpected(const OrthancPluginHttpRequest* request)
    {
      std::string accept;

      if (LookupHttpHeader(accept, request, "accept"))
      {
        return IsXmlExpected(accept);
      }
      else
      {
        return false;   // By default, return DICOM+JSON
      }
    }

    unsigned int GetMetadataWorkerThreadsCount()
    {
      return GetUnsignedIntegerValue("MetadataWorkerThreadsCount", 4);
    }

    bool IsMetadataCacheEnabled()
    {
      return GetBooleanValue("EnableMetadataCache", true);
    }

    bool IsReadOnly()
    {
      return globalConfiguration_->GetBooleanValue("ReadOnly", false);
    }
    
    unsigned int GetWadoRsLoaderThreadsCount()
    {
      return GetUnsignedIntegerValue("WadoRsLoaderThreadsCount", 0);
    }

    bool IsPerformanceLogsEnabled()
    {
      return GetBooleanValue("EnablePerformanceLogs", false);
    }

    MetadataMode GetMetadataMode(Orthanc::ResourceType level)
    {
      static const std::string FULL = "Full";
      static const std::string MAIN_DICOM_TAGS = "MainDicomTags";
      static const std::string EXTRAPOLATE = "Extrapolate";
      
      std::string key;
      switch (level)
      {
        case Orthanc::ResourceType_Study:
          key = "StudiesMetadata";
          break;

        case Orthanc::ResourceType_Series:
          key = "SeriesMetadata";
          break;

        default:
          throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
      }

      std::string value = GetStringValue(key, FULL);

      if (value == FULL)
      {
        return MetadataMode_Full;
      }
      else if (value == MAIN_DICOM_TAGS)
      {
        return MetadataMode_MainDicomTags;
      }
      else if (value == EXTRAPOLATE)
      {
        return MetadataMode_Extrapolate;
      }
      else
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange,
                                        "Bad value for option \"" + key +
                                        "\": Should be either \"" + FULL + "\" or \"" +
                                        MAIN_DICOM_TAGS + "\" or \"" + EXTRAPOLATE + "\"");
      }
    }


    void GetSetOfTags(std::set<Orthanc::DicomTag>& tags,
                      const std::string& key)
    {
      tags.clear();

      std::list<std::string> s;
      
      if (dicomWebConfiguration_->LookupListOfStrings(s, key, false))
      {
        for (std::list<std::string>::const_iterator it = s.begin(); it != s.end(); ++it)
        {
          OrthancPluginDictionaryEntry entry;
          if (OrthancPluginLookupDictionary(GetGlobalContext(), &entry, it->c_str()) == OrthancPluginErrorCode_Success)
          {
            tags.insert(Orthanc::DicomTag(entry.group, entry.element));
          }
          else
          {
            throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange,
                                            "Unknown DICOM tag in option \"" + key + "\" of DICOMweb: " + *it);
          }
        }
      }
    }


    void GetExtrapolatedMetadataTags(std::set<Orthanc::DicomTag>& tags,
                                     Orthanc::ResourceType level)
    {
      switch (level)
      {
        case Orthanc::ResourceType_Study:
          GetSetOfTags(tags, "StudiesMetadataExtrapolatedTags");
          break;

        case Orthanc::ResourceType_Series:
          GetSetOfTags(tags, "SeriesMetadataExtrapolatedTags");
          break;

        default:
          throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
      }
    }


    void LoadDicomWebServers()
    {
      if (serversInDatabase_)
      {
        // New in DICOMweb 1.5
        OrthancString property;
        property.Assign(OrthancPluginGetGlobalProperty(
                          GetGlobalContext(), GLOBAL_PROPERTY_SERVERS, "{}"));

        if (property.GetContent() == NULL)
        {
          DicomWebServers::GetInstance().Clear();
        }
        else
        {
          try
          {
            DicomWebServers::GetInstance().UnserializeGlobalProperty(property.GetContent());
          }
          catch (Orthanc::OrthancException&)
          {
            DicomWebServers::GetInstance().Clear();
            LOG(ERROR) << "Cannot read the DICOMweb servers from the database, no server will be defined";
          }
        }
      }
      else
      {
        OrthancConfiguration servers;
        dicomWebConfiguration_->GetSection(servers, "Servers");
        DicomWebServers::GetInstance().LoadGlobalConfiguration(servers.GetJson());
      }
    }

    
    void SaveDicomWebServers()
    {
      if (serversInDatabase_)
      {
        // New in DICOMweb 1.5
        std::string property;
        DicomWebServers::GetInstance().SerializeGlobalProperty(property);

        if (OrthancPluginSetGlobalProperty(
              OrthancPlugins::GetGlobalContext(), GLOBAL_PROPERTY_SERVERS, property.c_str()) !=
            OrthancPluginErrorCode_Success)
        {
          LOG(ERROR) << "Cannot write the DICOMweb servers into the database";
        }
      }
    }
  }
}
