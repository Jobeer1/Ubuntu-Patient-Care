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


#include "WadoUri.h"

#include "../Resources/Orthanc/Plugins/OrthancPluginCppWrapper.h"
#include "Configuration.h"
#include "Logging.h"

#include <string>



static bool LocateInstanceWadoUri(std::string& instance,
                                  std::string& contentType,
                                  const OrthancPluginHttpRequest* request)
{
  std::string requestType, studyUid, seriesUid, objectUid;

  for (uint32_t i = 0; i < request->getCount; i++)
  {
    std::string key(request->getKeys[i]);
    std::string value(request->getValues[i]);

    if (key == "studyUID")
    {
      studyUid = value;
    }
    else if (key == "seriesUID")
    {
      seriesUid = value;
    }
    else if (key == "objectUID")  // In WADO-URI, "objectUID" corresponds to "SOPInstanceUID"
    {
      objectUid = value;
    }
    else if (key == "requestType")
    {
      requestType = value;
    }
    else if (key == "contentType")
    {
      contentType = value;
    }
  }

  if (requestType != "WADO")
  {
    LOG(ERROR) << "WADO-URI: Invalid requestType: \"" << requestType << "\"";
    return false;
  }

  if (objectUid.empty())
  {
    LOG(ERROR) << "WADO-URI: No SOPInstanceUID provided";
    return false;
  }

  /**
  * Below are only sanity checks to ensure that the possibly provided
  * "seriesUID" and "studyUID" match that of the provided instance.
  **/

  Json::Value payload;
  Json::Value payloadQuery;

  payload["Level"] = "instance";
  payload["Expand"] = false;

  payloadQuery["SOPInstanceUID"] = objectUid;
  if (!seriesUid.empty())
  {
    payloadQuery["SeriesInstanceUID"] = seriesUid;
  }
  if (!studyUid.empty())
  {
    payloadQuery["StudyInstanceUID"] = studyUid;
  }

  payload["Query"] = payloadQuery;

  std::map<std::string, std::string> httpHeaders;
  OrthancPlugins::GetHttpHeaders(httpHeaders, request);

  Json::Value resources;
  if (!OrthancPlugins::RestApiPost(resources, "/tools/find", payload, httpHeaders, true) ||
      resources.type() != Json::arrayValue)
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
  }

  if (resources.size() == 0)
  {
    LOG(ERROR) << "WADO-URI: No such SOPInstanceUID in Orthanc: \"" << objectUid << "\" or parent SeriesInstanceUID/StudyInstanceUID is invalid";
    return false;
  }
  
  if (resources.size() > 1)
  {
    LOG(ERROR) << "WADO-URI: Multiple SOPInstanceUID found in Orthanc: \"" << objectUid;
    return false;
  }

  instance = resources[0].asString();
  return true;
}


static void AnswerDicom(OrthancPluginRestOutput* output,
                        const std::string& instance)
{
  OrthancPluginContext* context = OrthancPlugins::GetGlobalContext();

  std::string uri = "/instances/" + instance + "/file";

  OrthancPlugins::MemoryBuffer dicom;
  if (dicom.RestApiGet(uri, false))
  {
    OrthancPluginAnswerBuffer(context, output, 
                              dicom.GetData(), dicom.GetSize(), "application/dicom");
  }
  else
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_Plugin,
                                    "WADO-URI: Unable to retrieve DICOM file from " + uri);
  }
}


static void AnswerPreview(OrthancPluginRestOutput* output,
                          const std::string& instance,
                          const std::map<std::string, std::string>& httpHeaders)
{
  /**
   * (*) We can use "/rendered" that was introduced in the REST API of
   * Orthanc 1.6.0, as since release 1.2 of the DICOMweb plugin, the
   * minimal SDK version is Orthanc 1.7.0 (in order to be able to use
   * transcoding primitives). In releases <= 1.2, "/preview" was used,
   * which caused one issue:
   * https://groups.google.com/d/msg/orthanc-users/mKgr2QAKTCU/R7u4I1LvBAAJ
   **/
  const std::string uri = "/instances/" + instance + "/rendered";

  OrthancPluginContext* context = OrthancPlugins::GetGlobalContext();

  OrthancPlugins::MemoryBuffer png;
  if (png.RestApiGet(uri, httpHeaders, true))
  {
    OrthancPluginAnswerBuffer(context, output, png.GetData(), png.GetSize(), "image/png");
  }
  else
  {
    LOG(ERROR) << "WADO-URI: Unable to generate a preview image for " << uri;
    throw Orthanc::OrthancException(Orthanc::ErrorCode_Plugin);
  }
}


static void AnswerPngPreview(OrthancPluginRestOutput* output,
                              const std::string& instance)
{
  std::map<std::string, std::string> httpHeaders;
  httpHeaders["Accept"] = "image/png";
  AnswerPreview(output, instance, httpHeaders);
}


static void AnswerJpegPreview(OrthancPluginRestOutput* output,
                              const std::string& instance)
{
  std::map<std::string, std::string> httpHeaders;
  httpHeaders["Accept"] = "image/jpeg";
  AnswerPreview(output, instance, httpHeaders);
}


void WadoUriCallback(OrthancPluginRestOutput* output,
                     const char* url,
                     const OrthancPluginHttpRequest* request)
{
  if (request->method != OrthancPluginHttpMethod_Get)
  {
    OrthancPluginSendMethodNotAllowed(OrthancPlugins::GetGlobalContext(), output, "GET");
    return;
  }

  std::string instance;
  std::string contentType = "image/jpg";  // By default, JPEG image will be returned
  if (!LocateInstanceWadoUri(instance, contentType, request))
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_UnknownResource);
  }

  if (contentType == "application/dicom")
  {
    AnswerDicom(output, instance);
  }
  else if (contentType == "image/png")
  {
    AnswerPngPreview(output, instance);
  }
  else if (contentType == "image/jpeg" ||
           contentType == "image/jpg")
  {
    AnswerJpegPreview(output, instance);
  }
  else
  {
    throw Orthanc::OrthancException(
      Orthanc::ErrorCode_BadRequest,
      "WADO-URI: Unsupported content type: \"" + contentType + "\"");
  }
}
