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

#include "../Resources/Orthanc/Plugins/OrthancPluginCppWrapper.h"
#include "DicomWebClient.h"
#include "DicomWebServers.h"
#include "QidoRs.h"
#include "StowRs.h"
#include "WadoRs.h"
#include "WadoUri.h"

#include <Logging.h>
#include <SystemToolbox.h>
#include <Toolbox.h>

#include <EmbeddedResources.h>

#include <boost/algorithm/string/predicate.hpp>


// we use "ResponseContent" in tools/find -> we need 1.12.5
#define ORTHANC_CORE_MINIMAL_MAJOR     1
#define ORTHANC_CORE_MINIMAL_MINOR     12
#define ORTHANC_CORE_MINIMAL_REVISION  5

static const char* const HAS_DELETE = "HasDelete";
static const char* const SYSTEM_CAPABILITIES = "Capabilities";
static const char* const SYSTEM_CAPABILITIES_HAS_EXTENDED_FIND = "HasExtendedFind";
static const char* const READ_ONLY = "ReadOnly";
bool isReadOnly_ = false;


bool RequestHasKey(const OrthancPluginHttpRequest* request, const char* key)
{
  for (uint32_t i = 0; i < request->getCount; i++)
  {
    if (strcmp(key, request->getKeys[i]) == 0)
      return true;
  }
  return false;
}


void ListServers(OrthancPluginRestOutput* output,
                 const char* url,
                 const OrthancPluginHttpRequest* request)
{
  OrthancPluginContext* context = OrthancPlugins::GetGlobalContext();

  if (request->method != OrthancPluginHttpMethod_Get)
  {
    OrthancPluginSendMethodNotAllowed(context, output, "GET");
  }
  else
  {
    std::list<std::string> servers;
    OrthancPlugins::DicomWebServers::GetInstance().ListServers(servers);

    if (RequestHasKey(request, "expand"))
    {
      Json::Value result = Json::objectValue;
      for (std::list<std::string>::const_iterator it = servers.begin(); it != servers.end(); ++it)
      {
        Orthanc::WebServiceParameters server = OrthancPlugins::DicomWebServers::GetInstance().GetServer(*it);
        Json::Value jsonServer;
        // only return the minimum information to identify the destination, do not include "security" information like passwords
        server.FormatPublic(jsonServer);
        result[*it] = jsonServer;
      }

      std::string answer = result.toStyledString();
      OrthancPluginAnswerBuffer(context, output, answer.c_str(), answer.size(), "application/json");
    }
    else // if expand is not present, keep backward compatibility and return an array of server names
    {
      Json::Value json = Json::arrayValue;
      for (std::list<std::string>::const_iterator it = servers.begin(); it != servers.end(); ++it)
      {
        json.append(*it);
      }

      std::string answer = json.toStyledString();
      OrthancPluginAnswerBuffer(context, output, answer.c_str(), answer.size(), "application/json");
    }
  }
}

void ListServerOperations(OrthancPluginRestOutput* output,
                          const char* /*url*/,
                          const OrthancPluginHttpRequest* request)
{
  OrthancPluginContext* context = OrthancPlugins::GetGlobalContext();

  switch (request->method)
  {
    case OrthancPluginHttpMethod_Get:
    {
      // Make sure the server does exist
      const Orthanc::WebServiceParameters& server = 
        OrthancPlugins::DicomWebServers::GetInstance().GetServer(request->groups[0]);

      Json::Value json = Json::arrayValue;
      json.append("get");
      json.append("retrieve");
      json.append("stow");
      json.append("wado");
      json.append("qido");

      if (server.GetBooleanUserProperty(HAS_DELETE, false))
      {
        json.append("delete");
      }

      std::string answer = json.toStyledString(); 
      OrthancPluginAnswerBuffer(context, output, answer.c_str(), answer.size(), "application/json");
      break;
    }
    
    case OrthancPluginHttpMethod_Delete:
    {
      OrthancPlugins::DicomWebServers::GetInstance().DeleteServer(request->groups[0]);
      OrthancPlugins::Configuration::SaveDicomWebServers();

      std::string answer = "{}";
      OrthancPluginAnswerBuffer(context, output, answer.c_str(), answer.size(), "application/json");
      break;
    }
    
    case OrthancPluginHttpMethod_Put:
    {
      Json::Value body;
      OrthancPlugins::ParseJsonBody(body, request);
      
      Orthanc::WebServiceParameters parameters(body);
      
      OrthancPlugins::DicomWebServers::GetInstance().SetServer(request->groups[0], parameters);
      OrthancPlugins::Configuration::SaveDicomWebServers();
      
      std::string answer = "{}";
      OrthancPluginAnswerBuffer(context, output, answer.c_str(), answer.size(), "application/json");
      break;
    }
    
    default:
      OrthancPluginSendMethodNotAllowed(context, output, "GET,PUT,DELETE");
      break;
  }
}



void GetClientInformation(OrthancPluginRestOutput* output,
                          const char* /*url*/,
                          const OrthancPluginHttpRequest* request)
{
  OrthancPluginContext* context = OrthancPlugins::GetGlobalContext();

  if (request->method != OrthancPluginHttpMethod_Get)
  {
    OrthancPluginSendMethodNotAllowed(context, output, "GET");
  }
  else
  {
    Json::Value info = Json::objectValue;
    info["DicomWebRoot"] = OrthancPlugins::Configuration::GetDicomWebRoot();
    info["OrthancApiRoot"] = OrthancPlugins::Configuration::GetOrthancApiRoot();

    std::string answer = info.toStyledString();
    OrthancPluginAnswerBuffer(context, output, answer.c_str(), answer.size(), "application/json");
  }
}



void QidoClient(OrthancPluginRestOutput* output,
                const char* /*url*/,
                const OrthancPluginHttpRequest* request)
{
  OrthancPluginContext* context = OrthancPlugins::GetGlobalContext();

  if (request->method != OrthancPluginHttpMethod_Post)
  {
    OrthancPluginSendMethodNotAllowed(context, output, "POST");
  }
  else
  {
    Json::Value answer;
    GetFromServer(answer, request);
    
    if (answer.type() != Json::arrayValue)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_NetworkProtocol);
    }

    Json::Value result = Json::arrayValue;
    for (Json::Value::ArrayIndex i = 0; i < answer.size(); i++)
    {
      if (answer[i].type() != Json::objectValue)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_NetworkProtocol);
      }

      Json::Value::Members tags = answer[i].getMemberNames();

      Json::Value item = Json::objectValue;
      
      for (size_t j = 0; j < tags.size(); j++)
      {
        Orthanc::DicomTag tag(0, 0);
        if (Orthanc::DicomTag::ParseHexadecimal(tag, tags[j].c_str()))
        {
          Json::Value value = Json::objectValue;
          value["Group"] = tag.GetGroup();
          value["Element"] = tag.GetElement();
          
#if ORTHANC_PLUGINS_VERSION_IS_ABOVE(1, 5, 7)
          OrthancPlugins::OrthancString name;

          name.Assign(OrthancPluginGetTagName(context, tag.GetGroup(), tag.GetElement(), NULL));
          if (name.GetContent() != NULL)
          {
            value["Name"] = std::string(name.GetContent());
          }
#endif

          const Json::Value& source = answer[i][tags[j]];
          if (source.type() != Json::objectValue ||
              !source.isMember("vr") ||
              source["vr"].type() != Json::stringValue)
          {
            throw Orthanc::OrthancException(Orthanc::ErrorCode_NetworkProtocol);
          }

          value["vr"] = source["vr"].asString();

          if (source.isMember("Value") &&
              source["Value"].type() == Json::arrayValue &&
              source["Value"].size() >= 1)
          {
            const Json::Value& content = source["Value"][0];

            switch (content.type())
            {
              case Json::intValue:
                value["Value"] = content;
                break;

              case Json::stringValue:
                value["Value"] = content.asString();
                break;

              case Json::objectValue:
                if (content.isMember("Alphabetic") &&
                    content["Alphabetic"].type() == Json::stringValue)
                {
                  value["Value"] = content["Alphabetic"].asString();
                }
                break;

              default:
                break;
            }
          }

          item[tags[j]] = value;
        }
      }

      result.append(item);
    }

    std::string tmp = result.toStyledString();
    OrthancPluginAnswerBuffer(context, output, tmp.c_str(), tmp.size(), "application/json");
  }
}


void DeleteClient(OrthancPluginRestOutput* output,
                const char* /*url*/,
                const OrthancPluginHttpRequest* request)
{
  OrthancPluginContext* context = OrthancPlugins::GetGlobalContext();

  if (request->method != OrthancPluginHttpMethod_Post)
  {
    OrthancPluginSendMethodNotAllowed(context, output, "POST");
  }
  else
  {
    static const char* const LEVEL = "Level";
    static const char* const SERIES_INSTANCE_UID = "SeriesInstanceUID";
    static const char* const STUDY_INSTANCE_UID = "StudyInstanceUID";
    static const char* const SOP_INSTANCE_UID = "SOPInstanceUID";

    const std::string serverName = request->groups[0];

    const Orthanc::WebServiceParameters& server = 
      OrthancPlugins::DicomWebServers::GetInstance().GetServer(serverName);

    if (!server.GetBooleanUserProperty(HAS_DELETE, false))
    {
      throw Orthanc::OrthancException(
        Orthanc::ErrorCode_BadFileFormat,
        "Cannot delete on DICOMweb server, check out property \"" + std::string(HAS_DELETE) + "\": " + serverName);
    }

    Json::Value body;
    OrthancPlugins::ParseJsonBody(body, request);

    if (body.type() != Json::objectValue ||
        !body.isMember(LEVEL) ||
        !body.isMember(STUDY_INSTANCE_UID) ||
        body[LEVEL].type() != Json::stringValue ||
        body[STUDY_INSTANCE_UID].type() != Json::stringValue)
    {
      throw Orthanc::OrthancException(
        Orthanc::ErrorCode_BadFileFormat,
        "The request body must contain a JSON object with fields \"Level\" and \"StudyInstanceUID\"");
    }

    Orthanc::ResourceType level = Orthanc::StringToResourceType(body[LEVEL].asCString());

    const std::string study = body[STUDY_INSTANCE_UID].asString();

    std::string series;    
    if (level == Orthanc::ResourceType_Series ||
        level == Orthanc::ResourceType_Instance)
    {
      if (!body.isMember(SERIES_INSTANCE_UID) ||
          body[SERIES_INSTANCE_UID].type() != Json::stringValue)
      {
        throw Orthanc::OrthancException(
          Orthanc::ErrorCode_BadFileFormat,
          "The request body must contain the field \"SeriesInstanceUID\"");
      }
      else
      {
        series = body[SERIES_INSTANCE_UID].asString();
      }
    }

    std::string instance;    
    if (level == Orthanc::ResourceType_Instance)
    {
      if (!body.isMember(SOP_INSTANCE_UID) ||
          body[SOP_INSTANCE_UID].type() != Json::stringValue)
      {
        throw Orthanc::OrthancException(
          Orthanc::ErrorCode_BadFileFormat,
          "The request body must contain the field \"SOPInstanceUID\"");
      }
      else
      {
        instance = body[SOP_INSTANCE_UID].asString();
      }
    }

    std::string uri;
    switch (level)
    {
      case Orthanc::ResourceType_Study:
        uri = "/studies/" + study;
        break;

      case Orthanc::ResourceType_Series:
        uri = "/studies/" + study + "/series/" + series;
        break;

      case Orthanc::ResourceType_Instance:
        uri = "/studies/" + study + "/series/" + series + "/instances/" + instance;
        break;

      default:
        throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }

    OrthancPlugins::HttpClient client;
    std::map<std::string, std::string> userProperties;
    OrthancPlugins::DicomWebServers::GetInstance().ConfigureHttpClient(client, userProperties, serverName, uri);
    client.SetMethod(OrthancPluginHttpMethod_Delete);
    client.Execute();

    std::string tmp = "{}";
    OrthancPluginAnswerBuffer(context, output, tmp.c_str(), tmp.size(), "application/json");
  }
}





static bool DisplayPerformanceWarning(OrthancPluginContext* context)
{
  (void) DisplayPerformanceWarning;   // Disable warning about unused function
  LOG(WARNING) << "Performance warning in DICOMweb: Non-release build, runtime debug assertions are turned on";
  return true;
}


template <enum Orthanc::EmbeddedResources::DirectoryResourceId folder>
void ServeEmbeddedFolder(OrthancPluginRestOutput* output,
                         const char* url,
                         const OrthancPluginHttpRequest* request)
{
  OrthancPluginContext* context = OrthancPlugins::GetGlobalContext();

  if (request->method != OrthancPluginHttpMethod_Get)
  {
    OrthancPluginSendMethodNotAllowed(context, output, "GET");
  }
  else
  {
    std::string path = "/" + std::string(request->groups[0]);
    const char* mime = Orthanc::EnumerationToString(Orthanc::SystemToolbox::AutodetectMimeType(path));

    std::string s;
    Orthanc::EmbeddedResources::GetDirectoryResource(s, folder, path.c_str());

    const char* resource = s.size() ? s.c_str() : NULL;
    OrthancPluginAnswerBuffer(context, output, resource, s.size(), mime);
  }
}


#if ORTHANC_STANDALONE == 0
void ServeDicomWebClient(OrthancPluginRestOutput* output,
                         const char* url,
                         const OrthancPluginHttpRequest* request)
{
  OrthancPluginContext* context = OrthancPlugins::GetGlobalContext();

  if (request->method != OrthancPluginHttpMethod_Get)
  {
    OrthancPluginSendMethodNotAllowed(context, output, "GET");
  }
  else
  {
    const std::string path = std::string(DICOMWEB_CLIENT_PATH) + std::string(request->groups[0]);
    const char* mime = Orthanc::EnumerationToString(Orthanc::SystemToolbox::AutodetectMimeType(path));

    OrthancPlugins::MemoryBuffer f;
    f.ReadFile(path);

    OrthancPluginAnswerBuffer(context, output, f.GetData(), f.GetSize(), mime);
  }
}
#endif


static OrthancPluginErrorCode OnChangeCallback(OrthancPluginChangeType changeType, 
                                               OrthancPluginResourceType resourceType, 
                                               const char *resourceId)
{
  try
  {
    switch (changeType)
    {
      case OrthancPluginChangeType_OrthancStarted:
      {
        OrthancPlugins::Configuration::LoadDicomWebServers();

        Json::Value system;
        if (OrthancPlugins::RestApiGet(system, "/system", false))
        {
          bool hasExtendedFind = system.isMember(SYSTEM_CAPABILITIES) 
                                      && system[SYSTEM_CAPABILITIES].isMember(SYSTEM_CAPABILITIES_HAS_EXTENDED_FIND)
                                      && system[SYSTEM_CAPABILITIES][SYSTEM_CAPABILITIES_HAS_EXTENDED_FIND].asBool();
          if (hasExtendedFind)
          {
            LOG(INFO) << "Orthanc supports ExtendedFind.";
            SetPluginCanUseExtendedFind(true);
          }
          else
          {
            LOG(WARNING) << "Orthanc does not support ExtendedFind. The DICOMweb plugin will not benefit from some optimizations.";
          }

          bool isReadOnly = system.isMember(READ_ONLY) && system[READ_ONLY].asBool();

          if (isReadOnly)
          {
            LOG(INFO) << "Orthanc is ReadOnly.";
            SetSystemIsReadOnly(true);
          }
        }

      }; break;

      case OrthancPluginChangeType_StableSeries:
        if (!OrthancPlugins::Configuration::IsReadOnly())
        {
          CacheSeriesMetadata(resourceId);
        }
        break;

      default:
        break;
    }
  }
  catch (Orthanc::OrthancException& e)
  {
    LOG(ERROR) << "Exception: " << e.What();
  }
  catch (...)
  {
    LOG(ERROR) << "Uncatched native exception";
  }  

  return OrthancPluginErrorCode_Success;
}

template <bool isThumbnail>
void RetrieveInstanceRenderedThumbnail(OrthancPluginRestOutput* output,
                                       const char* url,
                                       const OrthancPluginHttpRequest* request)
{
  RetrieveInstanceRendered(output, url, request, isThumbnail);
}

template <bool isThumbnail>
void RetrieveFrameRenderedThumbnail(OrthancPluginRestOutput* output,
                                    const char* url,
                                    const OrthancPluginHttpRequest* request)
{
  RetrieveFrameRendered(output, url, request, isThumbnail);
}

template <bool isThumbnail>
void RetrieveSeriesRenderedThumbnail(OrthancPluginRestOutput* output,
                                     const char* url,
                                     const OrthancPluginHttpRequest* request)
{
  RetrieveSeriesRendered(output, url, request, isThumbnail);
}

template <bool isThumbnail>
void RetrieveStudyRenderedThumbnail(OrthancPluginRestOutput* output,
                                    const char* url,
                                    const OrthancPluginHttpRequest* request)
{
  RetrieveStudyRendered(output, url, request, isThumbnail);
}



extern "C"
{
  ORTHANC_PLUGINS_API int32_t OrthancPluginInitialize(OrthancPluginContext* context)
  {
    OrthancPlugins::SetGlobalContext(context, ORTHANC_DICOM_WEB_NAME);

#if ORTHANC_FRAMEWORK_VERSION_IS_ABOVE(1, 12, 4)
    Orthanc::Logging::InitializePluginContext(context, ORTHANC_DICOM_WEB_NAME);
#elif ORTHANC_FRAMEWORK_VERSION_IS_ABOVE(1, 7, 2)
    Orthanc::Logging::InitializePluginContext(context);
#else
    Orthanc::Logging::Initialize(context);
#endif

    assert(DisplayPerformanceWarning(context));

    Orthanc::Logging::EnableInfoLevel(true);

    /* Check the version of the Orthanc core */
    if (OrthancPluginCheckVersion(context) == 0)
    {
      char info[1024];
      sprintf(info, "Your version of Orthanc (%s) must be above %d.%d.%d to run this plugin",
              context->orthancVersion,
              ORTHANC_PLUGINS_MINIMAL_MAJOR_NUMBER,
              ORTHANC_PLUGINS_MINIMAL_MINOR_NUMBER,
              ORTHANC_PLUGINS_MINIMAL_REVISION_NUMBER);
      LOG(ERROR) << info;
      return -1;
    }

    if (!OrthancPlugins::CheckMinimalOrthancVersion(ORTHANC_CORE_MINIMAL_MAJOR,
                                                    ORTHANC_CORE_MINIMAL_MINOR,
                                                    ORTHANC_CORE_MINIMAL_REVISION))
    {
      char info[1024];
      sprintf(info, "Your version of Orthanc (%s) must be above %d.%d.%d to run this plugin",
              context->orthancVersion,
              ORTHANC_CORE_MINIMAL_MAJOR,
              ORTHANC_CORE_MINIMAL_MINOR,
              ORTHANC_CORE_MINIMAL_REVISION);
      LOG(ERROR) << info;
      return -1;
    }

    SetPluginCanDownloadTranscodedFile(OrthancPlugins::CheckMinimalOrthancVersion(1, 12, 2));

#if HAS_ORTHANC_PLUGIN_CHUNKED_HTTP_CLIENT == 0
    LOG(WARNING) << "Performance warning in DICOMweb: The plugin was compiled against "
                 << "Orthanc SDK <= 1.5.6. STOW and WADO chunked transfers will be entirely stored in RAM.";
#endif

#if !ORTHANC_PLUGINS_VERSION_IS_ABOVE(1, 12, 1)
    LOG(WARNING) << "Performance warning in DICOMweb: The plugin was compiled against "
                 << "Orthanc SDK <= 1.12.0. Retrieving metadata will be slower.";
#endif

    OrthancPlugins::SetDescription(ORTHANC_DICOM_WEB_NAME, "Implementation of DICOMweb (QIDO-RS, STOW-RS and WADO-RS) and WADO-URI.");

    try
    {
      // Read the configuration
      OrthancPlugins::Configuration::Initialize();

      // Configure the DICOMweb callbacks
      if (OrthancPlugins::Configuration::GetBooleanValue("Enable", true))
      {
        std::string root = OrthancPlugins::Configuration::GetDicomWebRoot();
        assert(!root.empty() && root[root.size() - 1] == '/');

        LOG(WARNING) << "URI to the DICOMweb REST API: " << root;


        if (!OrthancPlugins::Configuration::IsReadOnly())
        {
          OrthancPlugins::ChunkedRestRegistration<
            SearchForStudies /* TODO => Rename as QIDO-RS */,
            OrthancPlugins::StowServer::PostCallback>::Apply(root + "studies");

          OrthancPlugins::ChunkedRestRegistration<
            RetrieveDicomStudy /* TODO => Rename as WADO-RS */,
            OrthancPlugins::StowServer::PostCallback>::Apply(root + "studies/([^/]*)");
        }
        else
        {
          LOG(WARNING) << "READ-ONLY SYSTEM: deactivating STOW-RS routes";
          
          OrthancPlugins::ChunkedRestRegistration<
            SearchForStudies /* TODO => Rename as QIDO-RS */>::Apply(root + "studies");

          OrthancPlugins::ChunkedRestRegistration<
            RetrieveDicomStudy /* TODO => Rename as WADO-RS */>::Apply(root + "studies/([^/]*)");
        }

        OrthancPlugins::RegisterRestCallback<SearchForInstances>(root + "instances", true);
        OrthancPlugins::RegisterRestCallback<SearchForSeries>(root + "series", true);    
        OrthancPlugins::RegisterRestCallback<SearchForInstances>(root + "studies/([^/]*)/instances", true);    
        OrthancPlugins::RegisterRestCallback<RetrieveStudyMetadata>(root + "studies/([^/]*)/metadata", true);
        OrthancPlugins::RegisterRestCallback<SearchForSeries>(root + "studies/([^/]*)/series", true);    
        OrthancPlugins::RegisterRestCallback<RetrieveDicomSeries>(root + "studies/([^/]*)/series/([^/]*)", true);
        OrthancPlugins::RegisterRestCallback<SearchForInstances>(root + "studies/([^/]*)/series/([^/]*)/instances", true);    
        OrthancPlugins::RegisterRestCallback<RetrieveDicomInstance>(root + "studies/([^/]*)/series/([^/]*)/instances/([^/]*)", true);
        OrthancPlugins::RegisterRestCallback<RetrieveBulkData>(root + "studies/([^/]*)/series/([^/]*)/instances/([^/]*)/bulk/(.*)", true);
        OrthancPlugins::RegisterRestCallback<RetrieveInstanceMetadata>(root + "studies/([^/]*)/series/([^/]*)/instances/([^/]*)/metadata", true);
        OrthancPlugins::RegisterRestCallback<RetrieveSeriesMetadata>(root + "studies/([^/]*)/series/([^/]*)/metadata", true);
        OrthancPlugins::RegisterRestCallback<RetrieveAllFrames>(root + "studies/([^/]*)/series/([^/]*)/instances/([^/]*)/frames", true);
        OrthancPlugins::RegisterRestCallback<RetrieveSelectedFrames>(root + "studies/([^/]*)/series/([^/]*)/instances/([^/]*)/frames/([^/]*)", true);

        OrthancPlugins::RegisterRestCallback<ListServers>(root + "servers", true);
        OrthancPlugins::RegisterRestCallback<ListServerOperations>(root + "servers/([^/]*)", true);
        
        if (!OrthancPlugins::Configuration::IsReadOnly())
        {
          OrthancPlugins::RegisterRestCallback<RetrieveFromServer>(root + "servers/([^/]*)/retrieve", true);
        }
        else
        {
          LOG(WARNING) << "READ-ONLY SYSTEM: deactivating 'servers/../retrieve' route";
        }

        OrthancPlugins::RegisterRestCallback<WadoRetrieveClient>(root + "servers/([^/]*)/wado", true);
        OrthancPlugins::RegisterRestCallback<StowClient>(root + "servers/([^/]*)/stow", true);
        OrthancPlugins::RegisterRestCallback<GetFromServer>(root + "servers/([^/]*)/get", true);
        OrthancPlugins::RegisterRestCallback<QidoClient>(root + "servers/([^/]*)/qido", true);
        OrthancPlugins::RegisterRestCallback<DeleteClient>(root + "servers/([^/]*)/delete", true);

        OrthancPlugins::RegisterRestCallback
          <ServeEmbeddedFolder<Orthanc::EmbeddedResources::JAVASCRIPT_LIBS> >
          (root + "app/libs/(.*)", true);

        OrthancPlugins::RegisterRestCallback<GetClientInformation>(root + "info", true);

        OrthancPlugins::RegisterRestCallback<RetrieveStudyRenderedThumbnail<false> >(root + "studies/([^/]*)/rendered", true);
        OrthancPlugins::RegisterRestCallback<RetrieveSeriesRenderedThumbnail<false> >(root + "studies/([^/]*)/series/([^/]*)/rendered", true);
        OrthancPlugins::RegisterRestCallback<RetrieveInstanceRenderedThumbnail<false> >(root + "studies/([^/]*)/series/([^/]*)/instances/([^/]*)/rendered", true);
        OrthancPlugins::RegisterRestCallback<RetrieveFrameRenderedThumbnail<false> >(root + "studies/([^/]*)/series/([^/]*)/instances/([^/]*)/frames/([^/]*)/rendered", true);

        OrthancPlugins::RegisterRestCallback<RetrieveStudyRenderedThumbnail<true> >(root + "studies/([^/]*)/thumbnail", true);
        OrthancPlugins::RegisterRestCallback<RetrieveSeriesRenderedThumbnail<true> >(root + "studies/([^/]*)/series/([^/]*)/thumbnail", true);
        OrthancPlugins::RegisterRestCallback<RetrieveInstanceRenderedThumbnail<true> >(root + "studies/([^/]*)/series/([^/]*)/instances/([^/]*)/thumbnail", true);
        OrthancPlugins::RegisterRestCallback<RetrieveFrameRenderedThumbnail<true> >(root + "studies/([^/]*)/series/([^/]*)/instances/([^/]*)/frames/([^/]*)/thumbnail", true);

        if (!OrthancPlugins::Configuration::IsReadOnly())
        {
          OrthancPlugins::RegisterRestCallback<UpdateSeriesMetadataCache>("/studies/([^/]*)/update-dicomweb-cache", true);
        }

        OrthancPluginRegisterOnChangeCallback(context, OnChangeCallback);


        // Extend the default Orthanc Explorer with custom JavaScript for STOW client
        std::string explorer;

#if ORTHANC_STANDALONE == 1
        Orthanc::EmbeddedResources::GetFileResource(explorer, Orthanc::EmbeddedResources::ORTHANC_EXPLORER);
        OrthancPlugins::RegisterRestCallback
          <ServeEmbeddedFolder<Orthanc::EmbeddedResources::WEB_APPLICATION> >
          (root + "app/client/(.*)", true);
#else
        Orthanc::SystemToolbox::ReadFile(explorer, std::string(DICOMWEB_CLIENT_PATH) + "../Plugin/OrthancExplorer.js");
        OrthancPlugins::RegisterRestCallback<ServeDicomWebClient>(root + "app/client/(.*)", true);
#endif

        {
          if (root.size() < 2 ||
              root[0] != '/' ||
              root[root.size() - 1] != '/')
          {
            throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
          }

          std::map<std::string, std::string> dictionary;
          dictionary["DICOMWEB_ROOT"] = root.substr(1, root.size() - 2);  // Remove heading and trailing slashes
          std::string configured = Orthanc::Toolbox::SubstituteVariables(explorer, dictionary);

          OrthancPlugins::ExtendOrthancExplorer(ORTHANC_DICOM_WEB_NAME, configured);
        }
        
        
        std::string uri = root + "app/client/index.html";
        OrthancPlugins::SetRootUri(ORTHANC_DICOM_WEB_NAME, uri.c_str());

        std::string publicUrlRoot = OrthancPlugins::Configuration::GetPublicRoot();
        LOG(WARNING) << "DICOMweb public root: " << publicUrlRoot;

        LOG(WARNING) << "The DICOMWeb plugin will use " << (OrthancPlugins::Configuration::GetWadoRsLoaderThreadsCount() == 0 ? 1 : OrthancPlugins::Configuration::GetWadoRsLoaderThreadsCount()) << " threads to load DICOM files for WADO-RS queries";
      }
      else
      {
        LOG(WARNING) << "DICOMweb support is disabled";
      }

      // Configure the WADO callback
      if (OrthancPlugins::Configuration::GetBooleanValue("EnableWado", true))
      {
        std::string wado = OrthancPlugins::Configuration::GetWadoRoot();
        LOG(WARNING) << "URI to the WADO-URI API: " << wado;

        OrthancPlugins::RegisterRestCallback<WadoUriCallback>(wado, true);
      }
      else
      {
        LOG(WARNING) << "WADO-URI support is disabled";
      }
    }
    catch (Orthanc::OrthancException& e)
    {
      LOG(ERROR) << "Exception while initializing the DICOMweb plugin: " << e.What();
      return -1;
    }
    catch (...)
    {
      LOG(ERROR) << "Exception while initializing the DICOMweb plugin";
      return -1;
    }

    return 0;
  }


  ORTHANC_PLUGINS_API void OrthancPluginFinalize()
  {
  }


  ORTHANC_PLUGINS_API const char* OrthancPluginGetName()
  {
    return ORTHANC_DICOM_WEB_NAME;
  }


  ORTHANC_PLUGINS_API const char* OrthancPluginGetVersion()
  {
    return ORTHANC_DICOM_WEB_VERSION;
  }
}
