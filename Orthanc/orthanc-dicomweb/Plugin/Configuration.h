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

#include <DicomFormat/DicomTag.h>
#include <Enumerations.h>

#include <orthanc/OrthancCPlugin.h>
#include <json/value.h>

#if (ORTHANC_PLUGINS_MINIMAL_MAJOR_NUMBER <= 0 && \
     ORTHANC_PLUGINS_MINIMAL_MINOR_NUMBER <= 9 && \
     ORTHANC_PLUGINS_MINIMAL_REVISION_NUMBER <= 6)
#  define HAS_SEND_MULTIPART_ITEM_2   0
#else
#  define HAS_SEND_MULTIPART_ITEM_2   1
#endif

namespace OrthancPlugins
{
  static const Orthanc::DicomTag DICOM_TAG_RETRIEVE_URL(0x0008, 0x1190);
  static const Orthanc::DicomTag DICOM_TAG_FAILURE_REASON(0x0008, 0x1197);
  static const Orthanc::DicomTag DICOM_TAG_WARNING_REASON(0x0008, 0x1196);
  static const Orthanc::DicomTag DICOM_TAG_FAILED_SOP_SEQUENCE(0x0008, 0x1198);
  static const Orthanc::DicomTag DICOM_TAG_REFERENCED_SOP_SEQUENCE(0x0008, 0x1199);
  static const Orthanc::DicomTag DICOM_TAG_REFERENCED_SOP_CLASS_UID(0x0008, 0x1150);
  static const Orthanc::DicomTag DICOM_TAG_REFERENCED_SOP_INSTANCE_UID(0x0008, 0x1155);

  enum MetadataMode
  {
    MetadataMode_Full,           // Read all the DICOM instances from the storage area and store them in an attachment on StableSeries event
    MetadataMode_MainDicomTags,  // Only use the Orthanc database (main DICOM tags only)
    MetadataMode_Extrapolate     // Extrapolate user-specified tags from a few DICOM instances
  };


  bool LookupHttpHeader(std::string& value,
                        const OrthancPluginHttpRequest* request,
                        const std::string& header);

  void ParseAssociativeArray(std::map<std::string, std::string>& target,
                             const Json::Value& value,
                             const std::string& key);

  void ParseAssociativeArray(std::map<std::string, std::string>& target,
                             const Json::Value& value);

  bool ParseTag(Orthanc::DicomTag& target,
                const std::string& name);

  void ParseJsonBody(Json::Value& target,
                     const OrthancPluginHttpRequest* request);

  std::string RemoveMultipleSlashes(const std::string& source);

  bool LookupStringValue(std::string& target,
                         const Json::Value& json,
                         const std::string& key);

  bool LookupIntegerValue(int& target,
                          const Json::Value& json,
                          const std::string& key);

  bool LookupBooleanValue(bool& target,
                          const Json::Value& json,
                          const std::string& key);

  namespace Configuration
  {
    void Initialize();

    bool HasKey(const std::string& key);
    
    bool GetBooleanValue(const std::string& key,
                         bool defaultValue);

    bool LookupBooleanValue(bool& target,
                            const std::string& key);

    unsigned int GetUnsignedIntegerValue(const std::string& key,
                                         unsigned int defaultValue);

    std::string GetDicomWebRoot();

    std::string GetPublicRoot();

    std::string GetOrthancApiRoot();

    std::string GetWadoRoot();
      
    std::string GetBasePublicUrl(const std::map<std::string, std::string>& headers);

    // TODO => REMOVE
    std::string GetBasePublicUrl(const OrthancPluginHttpRequest* request);


    std::string GetWadoUrl(const std::string& wadoBase,
                           const std::string& studyInstanceUid,
                           const std::string& seriesInstanceUid,
                           const std::string& sopInstanceUid);

    Orthanc::Encoding GetDefaultEncoding();

    bool IsXmlExpected(const std::map<std::string, std::string>& headers);

    // TODO => REMOVE
    bool IsXmlExpected(const OrthancPluginHttpRequest* request);

    MetadataMode GetMetadataMode(Orthanc::ResourceType level);

    void GetSetOfTags(std::set<Orthanc::DicomTag>& tags,
                      const std::string& key);

    void GetExtrapolatedMetadataTags(std::set<Orthanc::DicomTag>& tags,
                                     Orthanc::ResourceType level);

    void LoadDicomWebServers();

    void SaveDicomWebServers();

    unsigned int GetMetadataWorkerThreadsCount();

    unsigned int GetWadoRsLoaderThreadsCount();

    bool IsMetadataCacheEnabled();

    bool IsReadOnly();

    bool IsPerformanceLogsEnabled();
  }
}
