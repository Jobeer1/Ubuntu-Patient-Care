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


#include "StowRs.h"

#include "Configuration.h"
#include "DicomWebFormatter.h"
#include "Logging.h"

namespace OrthancPlugins
{
  StowServer::StowServer(OrthancPluginContext* context,
                         const std::map<std::string, std::string>& headers,
                         const std::string& expectedStudy) :
    context_(context),
    xml_(Configuration::IsXmlExpected(headers)),
    wadoBasePublicUrl_(Configuration::GetBasePublicUrl(headers)),
    expectedStudy_(expectedStudy),
    isFirst_(true),
    result_(Json::objectValue),
    success_(Json::arrayValue),
    failed_(Json::arrayValue),
    hasBadSyntax_(false),
    hasConflict_(false),
    headers_(headers)
  { 
    std::string tmp, contentType, subType, boundary;
    if (!Orthanc::MultipartStreamReader::GetMainContentType(tmp, headers) ||
        !Orthanc::MultipartStreamReader::ParseMultipartContentType(contentType, subType, boundary, tmp))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_UnsupportedMediaType,
                                      "The STOW-RS server expects a multipart body in its request");
    }

    if (contentType != "multipart/related")
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_UnsupportedMediaType,
                                      "The Content-Type of a STOW-RS request must be \"multipart/related\"");
    }

    if (subType != "application/dicom")
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_UnsupportedMediaType,
                                      "The STOW-RS plugin currently only supports \"application/dicom\" subtype");
    }

    // Hotfix for bug #190, until the Orthanc Framework is fixed
    // https://orthanc.uclouvain.be/bugs/show_bug.cgi?id=190
    if (!boundary.empty() &&
        boundary.size() >= 2 &&
        boundary[0] == '"' &&
        boundary[boundary.size() - 1] == '"')
    {
      boundary = boundary.substr(1, boundary.size() - 2);
    }

    parser_.reset(new Orthanc::MultipartStreamReader(boundary));
    parser_->SetHandler(*this);
  }


  void StowServer::HandlePart(const Orthanc::MultipartStreamReader::HttpHeaders& headers,
                              const void* part,
                              size_t size)
  {
    std::string contentType;

    if (!Orthanc::MultipartStreamReader::GetMainContentType(contentType, headers) ||
        contentType.find("application/dicom") == std::string::npos)
    {
      throw Orthanc::OrthancException(
        Orthanc::ErrorCode_UnsupportedMediaType,
        "The STOW-RS request contains a part that is not "
        "\"application/dicom\" (it is: \"" + contentType + "\")");
    }

    Json::Value dicom;
    bool ok = false;

    try
    {
      OrthancString s;
      s.Assign(OrthancPluginDicomBufferToJson(context_, part, size,
                                              OrthancPluginDicomToJsonFormat_Short,
                                              OrthancPluginDicomToJsonFlags_None, 256));

      if (s.GetContent() != NULL)
      {
        ok = true;
        s.ToJson(dicom);
      }
    }
    catch (Orthanc::OrthancException&)
    {
    }           

    if (!ok)
    {
      // Bad DICOM file
      LOG(WARNING) << "STOW-RS cannot parse an incoming DICOM file";
      hasBadSyntax_ = true;
      return;
    }

    if (dicom.type() != Json::objectValue ||
        !dicom.isMember(Orthanc::DICOM_TAG_SERIES_INSTANCE_UID.Format()) ||
        !dicom.isMember(Orthanc::DICOM_TAG_SOP_CLASS_UID.Format()) ||
        !dicom.isMember(Orthanc::DICOM_TAG_SOP_INSTANCE_UID.Format()) ||
        !dicom.isMember(Orthanc::DICOM_TAG_STUDY_INSTANCE_UID.Format()) ||
        dicom[Orthanc::DICOM_TAG_SERIES_INSTANCE_UID.Format()].type() != Json::stringValue ||
        dicom[Orthanc::DICOM_TAG_SOP_CLASS_UID.Format()].type() != Json::stringValue ||
        dicom[Orthanc::DICOM_TAG_SOP_INSTANCE_UID.Format()].type() != Json::stringValue ||
        dicom[Orthanc::DICOM_TAG_STUDY_INSTANCE_UID.Format()].type() != Json::stringValue)
    {
      LOG(WARNING) << "STOW-RS: Missing a mandatory tag in incoming DICOM file";
      hasBadSyntax_ = true;      

      if (dicom.isMember(Orthanc::DICOM_TAG_SOP_CLASS_UID.Format()) &&
          dicom.isMember(Orthanc::DICOM_TAG_SOP_INSTANCE_UID.Format()) &&
          dicom[Orthanc::DICOM_TAG_SOP_CLASS_UID.Format()].type() == Json::stringValue &&
          dicom[Orthanc::DICOM_TAG_SOP_INSTANCE_UID.Format()].type() == Json::stringValue)
      {
        Json::Value item = Json::objectValue;
        item[DICOM_TAG_REFERENCED_SOP_CLASS_UID.Format()] = dicom[Orthanc::DICOM_TAG_SOP_CLASS_UID.Format()].asString();
        item[DICOM_TAG_REFERENCED_SOP_INSTANCE_UID.Format()] = dicom[Orthanc::DICOM_TAG_SOP_INSTANCE_UID.Format()].asString();
        item[DICOM_TAG_FAILURE_REASON.Format()] =
          boost::lexical_cast<std::string>(0xC000);  // Error: Cannot understand
        failed_.append(item);
      }

      return;
    }

    const std::string seriesInstanceUid = dicom[Orthanc::DICOM_TAG_SERIES_INSTANCE_UID.Format()].asString();
    const std::string sopClassUid = dicom[Orthanc::DICOM_TAG_SOP_CLASS_UID.Format()].asString();
    const std::string sopInstanceUid = dicom[Orthanc::DICOM_TAG_SOP_INSTANCE_UID.Format()].asString();
    const std::string studyInstanceUid = dicom[Orthanc::DICOM_TAG_STUDY_INSTANCE_UID.Format()].asString();

    Json::Value item = Json::objectValue;
    item[DICOM_TAG_REFERENCED_SOP_CLASS_UID.Format()] = sopClassUid;
    item[DICOM_TAG_REFERENCED_SOP_INSTANCE_UID.Format()] = sopInstanceUid;
      
    if (!expectedStudy_.empty() &&
        studyInstanceUid != expectedStudy_)
    {
      LOG(WARNING) << "STOW-RS request restricted to study [" << expectedStudy_ << 
                      "], but received instance from study [" << studyInstanceUid << "]";

      hasConflict_ = true;

      item[DICOM_TAG_FAILURE_REASON.Format()] =
        boost::lexical_cast<std::string>(0x0110);  // Processing failure
      failed_.append(item);
    }
    else
    {
      if (isFirst_)
      {
        std::string url = wadoBasePublicUrl_ + "studies/" + studyInstanceUid;
        result_[DICOM_TAG_RETRIEVE_URL.Format()] = url;
        isFirst_ = false;
      }

      uint16_t failureReason = 0;
      try
      {
        MemoryBuffer tmp;

        // make sure to forward the auth headers in the request that is sent to Orthanc (to allow usage of the auth plugin)
        // since we do not know which header is being used, we include all the headers from the STOW-RS request (headers_), replace
        // the "content-disposition" + "content-type" that are rebuilt from the multi-part message and remove the headers that might
        // be mi-interpreted by Orthanc core (like "content-length" that is actually the "content-length" from the whole STOW-RS request, not the length of this file)
        Orthanc::MultipartStreamReader::HttpHeaders mergedHeaders = headers_;
        Orthanc::MultipartStreamReader::HttpHeaders::iterator foundContentLength = mergedHeaders.find("content-length");
        if (foundContentLength != mergedHeaders.end())
        {
          mergedHeaders.erase(foundContentLength);
        }
        
        ok = tmp.RestApiPost("/instances", part, size, mergedHeaders, true);
        tmp.Clear();
      }
      catch (Orthanc::OrthancException& ex)
      {
        ok = false;
        if (ex.GetErrorCode() == Orthanc::ErrorCode_FullStorage)
        {
          failureReason = 0xA700;  // out-of-resources
        }
        else
        {
          failureReason = 0x0110;  // processing error
        }
      }

      if (ok)
      {
        std::string url = (wadoBasePublicUrl_ + 
                           "studies/" + studyInstanceUid +
                           "/series/" + seriesInstanceUid +
                           "/instances/" + sopInstanceUid);

        item[DICOM_TAG_RETRIEVE_URL.Format()] = url;
        success_.append(item);      
      }
      else
      {
        LOG(ERROR) << "Orthanc was unable to store one instance in a STOW-RS request";
        item[DICOM_TAG_FAILURE_REASON.Format()] =
          boost::lexical_cast<std::string>(failureReason);
        failed_.append(item);
      }
    }
  }


  void StowServer::AddChunk(const void* data,
                            size_t size)
  {
    assert(parser_.get() != NULL);
    parser_->AddChunk(data, size);
  }


  void StowServer::Execute(OrthancPluginRestOutput* output)
  {
    assert(parser_.get() != NULL);
    parser_->CloseStream();

    if (failed_.size() > 0)
    {
      // new in 1.19: don't include the failed sequence if there are no failures (https://discourse.orthanc-server.org/t/orthanc-dicomweb-stowrs-server-request-response-compatibility/5763)
      result_[DICOM_TAG_FAILED_SOP_SEQUENCE.Format()] = failed_;
    }

    result_[DICOM_TAG_REFERENCED_SOP_SEQUENCE.Format()] = success_;
    
    std::string answer;
    
    DicomWebFormatter::Apply(answer, context_, result_, xml_,
                             OrthancPluginDicomWebBinaryMode_Ignore, "");

    // http://dicom.nema.org/medical/dicom/current/output/html/part18.html#table_10.5.3-1
    uint16_t statusCode = 200;
    if (hasBadSyntax_)
    {
      statusCode = 400;
    }
    else if (hasConflict_)
    {
      statusCode = 409;
    }
    else if (failed_.size() > 0 && success_.size() == 0)  // only failed instances but not a conflict or bad syntax -> 400
    {
      statusCode = 400;
    }
    else if (failed_.size() > 0 && success_.size() > 0) // 202 = Accepted but some instances have failures
    {
      statusCode = 202;
    }

    if (statusCode == 200)
    {
      OrthancPluginAnswerBuffer(context_, output, answer.c_str(), answer.size(),
                                xml_ ? "application/dicom+xml" : "application/dicom+json");
    }
    else
    {
      // TODO: if statusCode is 202, the content will only be sent if HttpDescribeErrors is set to true -> would need OrthancPluginAnswerBuffer with an HttpStatusCode arg
      OrthancPluginSetHttpHeader(context_, output, "Content-Type", xml_ ? "application/dicom+xml" : "application/dicom+json");
      OrthancPluginSendHttpStatus(context_, output, statusCode, answer.c_str(), answer.size());  
    }
  };

  
  IChunkedRequestReader* StowServer::PostCallback(const char* url,
                                                  const OrthancPluginHttpRequest* request)
  {
    OrthancPluginContext* context = GetGlobalContext();
  
    if (request->method != OrthancPluginHttpMethod_Post)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
    }

    std::map<std::string, std::string> headers;
    OrthancPlugins::GetHttpHeaders(headers, request);

    std::string expectedStudy;
    if (request->groupsCount == 1)
    {
      expectedStudy = request->groups[0];
    }

    if (expectedStudy.empty())
    {
      LOG(INFO) << "STOW-RS request without study";
    }
    else
    {
      LOG(INFO) << "STOW-RS request restricted to study UID " << expectedStudy;
    }

    return new StowServer(context, headers, expectedStudy);
  }
}
