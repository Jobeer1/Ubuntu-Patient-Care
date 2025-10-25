/**
 * SPDX-FileCopyrightText: 2023-2025 Sebastien Jodogne, ICTEAM UCLouvain, Belgium
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

/**
 * OHIF plugin for Orthanc
 * Copyright (C) 2023-2025 Sebastien Jodogne, ICTEAM UCLouvain, Belgium
 *
 * This program is free software: you can redistribute it and/or
 * modify it under the terms of the GNU General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program. If not, see <http://www.gnu.org/licenses/>.
 **/


#include "../Resources/Orthanc/Plugins/OrthancPluginCppWrapper.h"

#include <Compression/GzipCompressor.h>
#include <DicomFormat/DicomInstanceHasher.h>
#include <DicomFormat/DicomMap.h>
#include <Logging.h>
#include <MultiThreading/SharedMessageQueue.h>
#include <SerializationToolbox.h>
#include <SystemToolbox.h>
#include <Toolbox.h>

#include <EmbeddedResources.h>

#include <boost/thread.hpp>
#include <boost/thread/shared_mutex.hpp>

#define ORTHANC_PLUGIN_NAME  "ohif"


static const std::string  METADATA_OHIF = "4202";
static const char* const  KEY_VERSION = "Version";
static const unsigned int MAX_INSTANCES_IN_QUEUE = 10000;


enum DataSource
{
  DataSource_DicomWeb,
  DataSource_DicomJson
};


// Reference: https://v3-docs.ohif.org/configuration/dataSources/dicom-json

enum DataType
{
  DataType_String,
  DataType_Integer,
  DataType_Float,
  DataType_ListOfFloats,
  DataType_ListOfStrings,
  DataType_None
};

class TagInformation
{
private:
  DataType     type_;
  std::string  name_;
  
public:
  TagInformation() :
    type_(DataType_None)
  {
  }
  
  TagInformation(DataType type,
                 const std::string& name) :
    type_(type),
    name_(name)
  {
  }

  DataType GetType() const
  {
    return type_;
  }

  const std::string& GetName() const
  {
    return name_;
  }

  bool operator== (const TagInformation& other) const
  {
    return (type_ == other.type_ &&
            name_ == other.name_);
  }
};

typedef std::map<Orthanc::DicomTag, TagInformation>  TagsDictionary;

static TagsDictionary ohifStudyTags_, ohifSeriesTags_, ohifInstanceTags_, allTags_;


static const Orthanc::DicomTag RADIOPHARMACEUTICAL_INFORMATION_SEQUENCE(0x0054, 0x0016);

static void InitializeOhifTags()
{
  /**
   * Those are the tags that are found in the documentation of the
   * "DICOM JSON" data source:
   * https://docs.ohif.org/configuration/dataSources/dicom-json
   *
   * Official list of tags:
   * https://github.com/OHIF/Viewers/blob/master/platform/docs/docs/faq.md#what-are-the-list-of-required-metadata-for-the-ohif-viewer-to-work
   *
   * Official example:
   * https://ohif-dicom-json-example.s3.amazonaws.com/LIDC-IDRI-0001.json
   **/
  ohifStudyTags_[Orthanc::DICOM_TAG_STUDY_INSTANCE_UID] = TagInformation(DataType_String, "StudyInstanceUID");
  ohifStudyTags_[Orthanc::DICOM_TAG_STUDY_DATE]         = TagInformation(DataType_String, "StudyDate");
  ohifStudyTags_[Orthanc::DICOM_TAG_STUDY_TIME]         = TagInformation(DataType_String, "StudyTime");
  ohifStudyTags_[Orthanc::DICOM_TAG_STUDY_DESCRIPTION]  = TagInformation(DataType_String, "StudyDescription");
  ohifStudyTags_[Orthanc::DICOM_TAG_PATIENT_NAME]       = TagInformation(DataType_String, "PatientName"); 
  ohifStudyTags_[Orthanc::DICOM_TAG_PATIENT_ID]         = TagInformation(DataType_String, "PatientID");
  ohifStudyTags_[Orthanc::DICOM_TAG_ACCESSION_NUMBER]   = TagInformation(DataType_String, "AccessionNumber");
  ohifStudyTags_[Orthanc::DicomTag(0x0010, 0x1010)]     = TagInformation(DataType_String, "PatientAge");
  ohifStudyTags_[Orthanc::DICOM_TAG_PATIENT_SEX]        = TagInformation(DataType_String, "PatientSex");

  ohifSeriesTags_[Orthanc::DICOM_TAG_SERIES_INSTANCE_UID] = TagInformation(DataType_String, "SeriesInstanceUID");
  ohifSeriesTags_[Orthanc::DICOM_TAG_SERIES_NUMBER]       = TagInformation(DataType_Integer, "SeriesNumber");
  ohifSeriesTags_[Orthanc::DICOM_TAG_SERIES_DESCRIPTION]  = TagInformation(DataType_String, "SeriesDescription");
  ohifSeriesTags_[Orthanc::DICOM_TAG_MODALITY]            = TagInformation(DataType_String, "Modality");
  ohifSeriesTags_[Orthanc::DICOM_TAG_SLICE_THICKNESS]     = TagInformation(DataType_Float, "SliceThickness");

  ohifInstanceTags_[Orthanc::DICOM_TAG_COLUMNS]                    = TagInformation(DataType_Integer, "Columns");
  ohifInstanceTags_[Orthanc::DICOM_TAG_ROWS]                       = TagInformation(DataType_Integer, "Rows");
  ohifInstanceTags_[Orthanc::DICOM_TAG_INSTANCE_NUMBER]            = TagInformation(DataType_Integer, "InstanceNumber");
  ohifInstanceTags_[Orthanc::DICOM_TAG_SOP_CLASS_UID]              = TagInformation(DataType_String, "SOPClassUID");
  ohifInstanceTags_[Orthanc::DICOM_TAG_PHOTOMETRIC_INTERPRETATION] = TagInformation(DataType_String, "PhotometricInterpretation");
  ohifInstanceTags_[Orthanc::DICOM_TAG_BITS_ALLOCATED]             = TagInformation(DataType_Integer, "BitsAllocated");
  ohifInstanceTags_[Orthanc::DICOM_TAG_BITS_STORED]                = TagInformation(DataType_Integer, "BitsStored");
  ohifInstanceTags_[Orthanc::DICOM_TAG_PIXEL_REPRESENTATION]       = TagInformation(DataType_Integer, "PixelRepresentation");
  ohifInstanceTags_[Orthanc::DICOM_TAG_SAMPLES_PER_PIXEL]          = TagInformation(DataType_Integer, "SamplesPerPixel");
  ohifInstanceTags_[Orthanc::DICOM_TAG_PIXEL_SPACING]              = TagInformation(DataType_ListOfFloats, "PixelSpacing");
  ohifInstanceTags_[Orthanc::DICOM_TAG_HIGH_BIT]                   = TagInformation(DataType_Integer, "HighBit");
  ohifInstanceTags_[Orthanc::DICOM_TAG_IMAGE_ORIENTATION_PATIENT]  = TagInformation(DataType_ListOfFloats, "ImageOrientationPatient");
  ohifInstanceTags_[Orthanc::DICOM_TAG_IMAGE_POSITION_PATIENT]     = TagInformation(DataType_ListOfFloats, "ImagePositionPatient");
  ohifInstanceTags_[Orthanc::DICOM_TAG_FRAME_OF_REFERENCE_UID]     = TagInformation(DataType_String, "FrameOfReferenceUID");
  ohifInstanceTags_[Orthanc::DicomTag(0x0008, 0x0008)]             = TagInformation(DataType_ListOfStrings, "ImageType");
  ohifInstanceTags_[Orthanc::DICOM_TAG_MODALITY]                   = TagInformation(DataType_String, "Modality");
  ohifInstanceTags_[Orthanc::DICOM_TAG_SOP_INSTANCE_UID]           = TagInformation(DataType_String, "SOPInstanceUID");
  ohifInstanceTags_[Orthanc::DICOM_TAG_SERIES_INSTANCE_UID]        = TagInformation(DataType_String, "SeriesInstanceUID");
  ohifInstanceTags_[Orthanc::DICOM_TAG_STUDY_INSTANCE_UID]         = TagInformation(DataType_String, "StudyInstanceUID");
  ohifInstanceTags_[Orthanc::DICOM_TAG_WINDOW_CENTER]              = TagInformation(DataType_Float, "WindowCenter");
  ohifInstanceTags_[Orthanc::DICOM_TAG_WINDOW_WIDTH]               = TagInformation(DataType_Float, "WindowWidth");
  ohifInstanceTags_[Orthanc::DICOM_TAG_SERIES_DATE]                = TagInformation(DataType_String, "SeriesDate");

  /**
   * The items below are related to PET scans. Their list can be found
   * by looking for "required metadata are missing" in
   * "extensions/default/src/getPTImageIdInstanceMetadata.ts"
   **/
  ohifInstanceTags_[Orthanc::DICOM_TAG_ACQUISITION_DATE]      = TagInformation(DataType_String, "AcquisitionDate");
  ohifInstanceTags_[Orthanc::DICOM_TAG_ACQUISITION_TIME]      = TagInformation(DataType_String, "AcquisitionTime");
  ohifInstanceTags_[Orthanc::DICOM_TAG_SERIES_TIME]           = TagInformation(DataType_String, "SeriesTime");
  ohifInstanceTags_[Orthanc::DicomTag(0x0010, 0x1020)]        = TagInformation(DataType_Float, "PatientSize");
  ohifInstanceTags_[Orthanc::DicomTag(0x0010, 0x1030)]        = TagInformation(DataType_Float, "PatientWeight");
  ohifInstanceTags_[Orthanc::DicomTag(0x0018, 0x1242)]        = TagInformation(DataType_Integer, "ActualFrameDuration");
  ohifInstanceTags_[Orthanc::DicomTag(0x0028, 0x0051)]        = TagInformation(DataType_ListOfStrings, "CorrectedImage");
  ohifInstanceTags_[Orthanc::DicomTag(0x0054, 0x1001)]        = TagInformation(DataType_String, "Units");
  ohifInstanceTags_[Orthanc::DicomTag(0x0054, 0x1102)]        = TagInformation(DataType_String, "DecayCorrection");
  ohifInstanceTags_[Orthanc::DicomTag(0x0054, 0x1300)]        = TagInformation(DataType_Float, "FrameReferenceTime");
  ohifInstanceTags_[RADIOPHARMACEUTICAL_INFORMATION_SEQUENCE] = TagInformation(DataType_None, "RadiopharmaceuticalInformationSequence");

  /**
   * Added in version 1.3
   **/
  ohifInstanceTags_[Orthanc::DICOM_TAG_RESCALE_INTERCEPT] = TagInformation(DataType_Float, "RescaleIntercept");
  ohifInstanceTags_[Orthanc::DICOM_TAG_RESCALE_SLOPE]     = TagInformation(DataType_Float, "RescaleSlope");
  ohifInstanceTags_[Orthanc::DICOM_TAG_NUMBER_OF_FRAMES]  = TagInformation(DataType_Integer, "NumberOfFrames");


  // UNTESTED
  ohifInstanceTags_[Orthanc::DicomTag(0x7053, 0x1000)] = TagInformation(DataType_Float, "70531000");  // Philips SUVScaleFactor
  ohifInstanceTags_[Orthanc::DicomTag(0x7053, 0x1009)] = TagInformation(DataType_Float, "70531009");  // Philips ActivityConcentrationScaleFactor
  ohifInstanceTags_[Orthanc::DicomTag(0x0009, 0x100d)] = TagInformation(DataType_String, "0009100d");  // GE PrivatePostInjectionDateTime

  for (TagsDictionary::const_iterator it = ohifStudyTags_.begin(); it != ohifStudyTags_.end(); ++it)
  {
    assert(allTags_.find(it->first) == allTags_.end() ||
           allTags_[it->first] == it->second);
    allTags_[it->first] = it->second;
  }

  for (TagsDictionary::const_iterator it = ohifSeriesTags_.begin(); it != ohifSeriesTags_.end(); ++it)
  {
    assert(allTags_.find(it->first) == allTags_.end() ||
           allTags_[it->first] == it->second);
    allTags_[it->first] = it->second;
  }

  for (TagsDictionary::const_iterator it = ohifInstanceTags_.begin(); it != ohifInstanceTags_.end(); ++it)
  {
    assert(allTags_.find(it->first) == allTags_.end() ||
           allTags_[it->first] == it->second);
    allTags_[it->first] = it->second;
  }
}


// Forward declaration
void ReadStaticAsset(std::string& target,
                     const std::string& path);


/**
 * As the OHIF static assets are gzipped by the "EmbedStaticAssets.py"
 * script, we use a cache to maintain the uncompressed assets in order
 * to avoid multiple gzip decodings.
 **/
class ResourcesCache : public boost::noncopyable
{
private:
  typedef std::map<std::string, std::string*>  Content;
  
  boost::shared_mutex  mutex_;
  Content              content_;

public:
  ~ResourcesCache()
  {
    for (Content::iterator it = content_.begin(); it != content_.end(); ++it)
    {
      assert(it->second != NULL);
      delete it->second;
    }
  }

  void Answer(OrthancPluginContext* context,
              OrthancPluginRestOutput* output,
              const std::string& path)
  {
    const std::string mime = Orthanc::EnumerationToString(Orthanc::SystemToolbox::AutodetectMimeType(path));

    {
      // Check whether the cache already contains the resource
      boost::shared_lock<boost::shared_mutex> lock(mutex_);

      Content::const_iterator found = content_.find(path);
    
      if (found != content_.end())
      {
        assert(found->second != NULL);
        OrthancPluginAnswerBuffer(context, output, found->second->c_str(), found->second->size(), mime.c_str());
        return;
      }
    }

    // This resource has not been cached yet

    std::unique_ptr<std::string> item(new std::string);
    ReadStaticAsset(*item, path);

    OrthancPluginAnswerBuffer(context, output, item->c_str(), item->size(), mime.c_str());

    {
      // Store the resource into the cache
      boost::unique_lock<boost::shared_mutex> lock(mutex_);

      if (content_.find(path) == content_.end())
      {
        content_[path] = item.release();
      }
    }
  }
};


static bool ParseTagFromOrthanc(Json::Value& target,
                                const Orthanc::DicomTag& tag,
                                const std::string& name,
                                DataType type,
                                const Json::Value& source)
{
  const std::string formattedTag = tag.Format();

  if (source.isMember(formattedTag))
  {
    const Json::Value& value = source[formattedTag];

    /**
     * The cases below derive from "Toolbox::SimplifyDicomAsJson()"
     * with "DicomToJsonFormat_Short", which is invoked by the REST
     * API call to "/instances/.../tags?short".
     **/

    switch (value.type())
    {
      case Json::nullValue:
        return false;
          
      case Json::arrayValue:
        // This should never happen, as this would correspond to a sequence
        return false;

      case Json::stringValue:
      {
        switch (type)
        {
          case DataType_String:
            target[name] = value;
            return true;

          case DataType_Integer:
          {
            std::vector<std::string> tokens;
            Orthanc::Toolbox::TokenizeString(tokens, value.asString(), '\\');

            if (!tokens.empty())
            {
              int32_t v;
              if (Orthanc::SerializationToolbox::ParseInteger32(v, tokens[0]))
              {
                target[name] = v;
              }
              return true;
            }
            else
            {
              return false;
            }
          }

          case DataType_Float:
          {
            std::vector<std::string> tokens;
            Orthanc::Toolbox::TokenizeString(tokens, value.asString(), '\\');

            if (!tokens.empty())
            {
              float v;
              if (Orthanc::SerializationToolbox::ParseFloat(v, tokens[0]))
              {
                target[name] = v;
              }
              return true;
            }
            else
            {
              return false;
            }
          }

          case DataType_ListOfStrings:
          {
            std::vector<std::string> tokens;
            Orthanc::Toolbox::TokenizeString(tokens, value.asString(), '\\');
            target[name] = Json::arrayValue;
            for (size_t i = 0; i < tokens.size(); i++)
            {
              target[name].append(tokens[i]);
            }
            return true;
          }

          case DataType_ListOfFloats:
          {
            std::vector<std::string> tokens;
            Orthanc::Toolbox::TokenizeString(tokens, value.asString(), '\\');
            target[name] = Json::arrayValue;
            for (size_t i = 0; i < tokens.size(); i++)
            {
              float v;
              if (Orthanc::SerializationToolbox::ParseFloat(v, tokens[i]))
              {
                target[name].append(v);
              }
            }
            return true;
          }

          default:
            throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
        }
      }

      default:
        // This should never happen
        return false;
    }
  }
  else
  {
    return false;
  }
}


static bool EncodeOhifInstance(Json::Value& target,
                               const std::string& instanceId)
{
  Json::Value source;
  if (!OrthancPlugins::RestApiGet(source, "/instances/" + instanceId + "/tags?short", false))
  {
    return false;
  }
  else if (source.type() != Json::objectValue)
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
  }
  else
  {
    target[KEY_VERSION] = static_cast<int>(METADATA_VERSION);
    
    for (TagsDictionary::const_iterator it = allTags_.begin(); it != allTags_.end(); ++it)
    {
      ParseTagFromOrthanc(target, it->first, it->first.Format(), it->second.GetType(), source);
    }

    /**
     * This is a sequence for PET scans that is manually injected, to be
     * used in function "getPTImageIdInstanceMetadata()" of
     * "extensions/default/src/getPTImageIdInstanceMetadata.ts"
     **/
    static const Orthanc::DicomTag RADIONUCLIDE_HALF_LIFE(0x0018, 0x1075);
    static const Orthanc::DicomTag RADIONUCLIDE_TOTAL_DOSE(0x0018, 0x1074);
    static const Orthanc::DicomTag RADIOPHARMACEUTICAL_START_DATETIME(0x0018, 0x1078);
    static const Orthanc::DicomTag RADIOPHARMACEUTICAL_START_TIME(0x0018, 0x1072);

    if (source.isMember(RADIOPHARMACEUTICAL_INFORMATION_SEQUENCE.Format()))
    {
      const Json::Value& pharma = source[RADIOPHARMACEUTICAL_INFORMATION_SEQUENCE.Format()];
      if (pharma.type() == Json::arrayValue &&
          pharma.size() > 0 &&
          pharma[0].type() == Json::objectValue)
      {
        Json::Value info;
        if (ParseTagFromOrthanc(info, RADIONUCLIDE_HALF_LIFE, "RadionuclideHalfLife", DataType_Float, pharma[0]) &&
            ParseTagFromOrthanc(info, RADIONUCLIDE_TOTAL_DOSE, "RadionuclideTotalDose", DataType_Float, pharma[0]) &&
            (ParseTagFromOrthanc(info, RADIOPHARMACEUTICAL_START_DATETIME, "RadiopharmaceuticalStartDateTime", DataType_String, pharma[0]) ||
             ParseTagFromOrthanc(info, RADIOPHARMACEUTICAL_START_TIME, "RadiopharmaceuticalStartTime", DataType_String, pharma[0])))
        {
          Json::Value sequence = Json::arrayValue;
          sequence.append(info);
        
          target[RADIOPHARMACEUTICAL_INFORMATION_SEQUENCE.Format()] = sequence;
        }
      }
    }

    return true;
  }
}


static std::string GetCacheUri(const std::string& instanceId)
{
  return "/instances/" + instanceId + "/metadata/" + METADATA_OHIF;
}


static void CacheAsMetadata(const Json::Value& instanceTags,
                            const std::string& instanceId)
{
  std::string uncompressed;
  Orthanc::Toolbox::WriteFastJson(uncompressed, instanceTags);

  std::string compressed;
  Orthanc::GzipCompressor compressor;
  Orthanc::IBufferCompressor::Compress(compressed, compressor, uncompressed);

  std::string metadata;
  Orthanc::Toolbox::EncodeBase64(metadata, compressed);

  Json::Value answer;
  OrthancPlugins::RestApiPut(answer, GetCacheUri(instanceId), metadata.c_str(), metadata.size(), false);
}


static bool GetOhifInstance(Json::Value& target,
                            const std::string& instanceId)
{
#if 0
  // This disables all the caching (for debugging)
  return EncodeOhifInstance(target, instanceId);
#else
  const std::string uri = GetCacheUri(instanceId);
  
  std::string metadata;
  
  if (OrthancPlugins::RestApiGetString(metadata, uri, false))
  {
    try
    {
      std::string compressed;
      Orthanc::Toolbox::DecodeBase64(compressed, metadata);

      std::string uncompressed;
      Orthanc::GzipCompressor compressor;
      Orthanc::IBufferCompressor::Uncompress(uncompressed, compressor, compressed);

      if (Orthanc::Toolbox::ReadJson(target, uncompressed) &&
          target.isMember(KEY_VERSION) &&
          target[KEY_VERSION].type() == Json::intValue &&
          target[KEY_VERSION].asInt() == METADATA_VERSION)
      {
        // Success, we can reuse the cached value
        return true;
      }
    }
    catch (Orthanc::OrthancException&)
    {
    }

    // Remove corrupted or metadata with an earlier version
    OrthancPlugins::RestApiDelete(uri, false);
  }

  if (EncodeOhifInstance(target, instanceId))
  {
    CacheAsMetadata(target, instanceId);
    return true;
  }
  else
  {
    return false;
  }
#endif
}


static ResourcesCache               cache_;
static std::string                  userConfiguration_;
static std::string                  routerBasename_;
static DataSource                   dataSource_;
static bool                         preload_;
static boost::thread                metadataThread_;
static Orthanc::SharedMessageQueue  pendingInstances_;
static bool                         continueThread_;

void ServeFile(OrthancPluginRestOutput* output,
               const char* url,
               const OrthancPluginHttpRequest* request)
{
  OrthancPluginContext* context = OrthancPlugins::GetGlobalContext();
  
  // The next 3 HTTP headers are required to enable SharedArrayBuffer
  // (https://web.dev/coop-coep/)
  OrthancPluginSetHttpHeader(context, output, "Cross-Origin-Embedder-Policy", "require-corp");
  OrthancPluginSetHttpHeader(context, output, "Cross-Origin-Opener-Policy", "same-origin");
  OrthancPluginSetHttpHeader(context, output, "Cross-Origin-Resource-Policy", "same-origin");

  std::string uri;
  if (request->groupsCount > 0)
  {
    uri = request->groups[0];
  }

  if (uri == "app-config.js")
  {
    std::string system;
    Orthanc::EmbeddedResources::GetFileResource(system, Orthanc::EmbeddedResources::APP_CONFIG_SYSTEM);

    std::map<std::string, std::string> dictionary;
    dictionary["ROUTER_BASENAME"] = routerBasename_;
    dictionary["USE_DICOM_WEB"] = (dataSource_ == DataSource_DicomWeb ? "true" : "false");

    system = Orthanc::Toolbox::SubstituteVariables(system, dictionary);

    std::string s = (userConfiguration_ + "\n" + system);
    OrthancPluginAnswerBuffer(context, output, s.c_str(), s.size(), "text/javascript");
  }
  else if (uri == "" ||             // Study list
           uri == "tmtv" ||         // Total metabolic tumor volume
           uri == "viewer" ||       // Default viewer (including MPR)
           uri == "segmentation" || // Segmentation mode
           uri == "microscopy"      // Microscopy mode
           )  
  {
    // Those correspond to the different modes of the OHIF platform:
    // https://v3-docs.ohif.org/platform/modes/
    cache_.Answer(context, output, "index.html");
  }
  else 
  {
    cache_.Answer(context, output, uri);
  }
}


static void GenerateOhifStudy(Json::Value& target,
                              const std::string& studyId)
{
  // https://v3-docs.ohif.org/configuration/dataSources/dicom-json
  static const char* const KEY_ID = "ID";
  const std::string KEY_PATIENT_ID = Orthanc::DICOM_TAG_PATIENT_ID.Format();
  const std::string KEY_STUDY_INSTANCE_UID = Orthanc::DICOM_TAG_STUDY_INSTANCE_UID.Format();
  const std::string KEY_SERIES_INSTANCE_UID = Orthanc::DICOM_TAG_SERIES_INSTANCE_UID.Format();
  const std::string KEY_SOP_INSTANCE_UID = Orthanc::DICOM_TAG_SOP_INSTANCE_UID.Format();
  
  Json::Value instancesIds;
  if (!OrthancPlugins::RestApiGet(instancesIds, "/studies/" + studyId + "/instances", false))
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_UnknownResource);
  }

  if (instancesIds.type() != Json::arrayValue)
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
  }

  std::vector<Json::Value> instancesTags;
  instancesTags.reserve(instancesIds.size());

  for (Json::ArrayIndex i = 0; i < instancesIds.size(); i++)
  {
    if (instancesIds[i].type() != Json::objectValue ||
        !instancesIds[i].isMember(KEY_ID) ||
        instancesIds[i][KEY_ID].type() != Json::stringValue)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
    }

    Json::Value t;
    if (GetOhifInstance(t, instancesIds[i][KEY_ID].asString()))
    {
      instancesTags.push_back(t);
    }
  }

  typedef std::list<const Json::Value*>           ListOfResources;
  typedef std::map<std::string, ListOfResources>  MapOfResources;

  MapOfResources studies;
  for (Json::ArrayIndex i = 0; i < instancesTags.size(); i++)
  {
    if (instancesTags[i].isMember(KEY_STUDY_INSTANCE_UID))
    {
      if (instancesTags[i][KEY_STUDY_INSTANCE_UID].type() != Json::stringValue)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
      }
      else
      {
        const std::string& studyInstanceUid = instancesTags[i][KEY_STUDY_INSTANCE_UID].asString();
        studies[studyInstanceUid].push_back(&instancesTags[i]);
      }
    }
  }

  target["studies"] = Json::arrayValue;
  
  for (MapOfResources::const_iterator it = studies.begin(); it != studies.end(); ++it)
  {
    if (!it->second.empty())
    {
      assert(it->second.front() != NULL);
      const Json::Value& firstInstanceInStudy = *it->second.front();
      
      Json::Value study = Json::objectValue;
      for (TagsDictionary::const_iterator tag = ohifStudyTags_.begin(); tag != ohifStudyTags_.end(); ++tag)
      {
        if (firstInstanceInStudy.isMember(tag->first.Format()))
        {
          study[tag->second.GetName()] = firstInstanceInStudy[tag->first.Format()];
        }
      }

      MapOfResources seriesInStudy;
      for (ListOfResources::const_iterator it2 = it->second.begin(); it2 != it->second.end(); ++it2)
      {
        assert(*it2 != NULL);
        const Json::Value& instanceInStudy = **it2;
        
        if (instanceInStudy.isMember(KEY_SERIES_INSTANCE_UID))
        {
          if (instanceInStudy[KEY_SERIES_INSTANCE_UID].type() != Json::stringValue)
          {
            throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
          }
          else
          {
            const std::string& seriesInstanceUid = instanceInStudy[KEY_SERIES_INSTANCE_UID].asString();
            seriesInStudy[seriesInstanceUid].push_back(&instanceInStudy);
          }
        }
      }

      study["series"] = Json::arrayValue;

      std::set<std::string> modalities;
      unsigned int countInstances = 0;

      for (MapOfResources::const_iterator it3 = seriesInStudy.begin(); it3 != seriesInStudy.end(); ++it3)
      {
        if (!it3->second.empty())
        {
          assert(it3->second.front() != NULL);
          const Json::Value& firstInstanceInSeries = *it3->second.front();

          if (firstInstanceInSeries.isMember(Orthanc::DICOM_TAG_MODALITY.Format()))
          {
            modalities.insert(firstInstanceInSeries[Orthanc::DICOM_TAG_MODALITY.Format()].asString());
          }

          Json::Value series = Json::objectValue;
          for (TagsDictionary::const_iterator tag = ohifSeriesTags_.begin(); tag != ohifSeriesTags_.end(); ++tag)
          {
            if (firstInstanceInSeries.isMember(tag->first.Format()))
            {
              series[tag->second.GetName()] = firstInstanceInSeries[tag->first.Format()];
            }
          }

          series["instances"] = Json::arrayValue;

          for (ListOfResources::const_iterator it4 = it3->second.begin(); it4 != it3->second.end(); ++it4)
          {
            assert(*it4 != NULL);
            const Json::Value& instanceInSeries = **it4;

            Json::Value metadata;
            for (TagsDictionary::const_iterator tag = ohifInstanceTags_.begin(); tag != ohifInstanceTags_.end(); ++tag)
            {
              if (instanceInSeries.isMember(tag->first.Format()))
              {
                metadata[tag->second.GetName()] = instanceInSeries[tag->first.Format()];
              }
            }

            Orthanc::DicomInstanceHasher hasher(instanceInSeries[KEY_PATIENT_ID].asString(),
                                                instanceInSeries[KEY_STUDY_INSTANCE_UID].asString(),
                                                instanceInSeries[KEY_SERIES_INSTANCE_UID].asString(),
                                                instanceInSeries[KEY_SOP_INSTANCE_UID].asString());

            Json::Value instance = Json::objectValue;
            instance["metadata"] = metadata;
            instance["url"] = "dicomweb:../instances/" + hasher.HashInstance() + "/file";

            series["instances"].append(instance);
            countInstances++;
          }

          study["series"].append(series);
        }
      }

      std::string jsonModalities;
      for (std::set<std::string>::const_iterator it2 = modalities.begin(); it2 != modalities.end(); ++it2)
      {
        if (!jsonModalities.empty())
        {
          jsonModalities += ",";
        }
        jsonModalities += *it2;
      }

      study["NumInstances"] = countInstances;
      study["Modalities"] = jsonModalities;

      target["studies"].append(study);
    }
  }  
}


void GetOhifStudy(OrthancPluginRestOutput* output,
                  const char* url,
                  const OrthancPluginHttpRequest* request)
{
  OrthancPluginContext* context = OrthancPlugins::GetGlobalContext();

  const std::string studyId = request->groups[0];

  Json::Value v;
  GenerateOhifStudy(v, studyId);

  std::string s;
  Orthanc::Toolbox::WriteFastJson(s, v);
  
  OrthancPluginAnswerBuffer(context, output, s.c_str(), s.size(), "application/json");
}


static void MetadataThread()
{
  while (continueThread_)
  {
    std::unique_ptr<Orthanc::IDynamicObject> instance(pendingInstances_.Dequeue(100));
    if (instance.get() != NULL)
    {
      const std::string instanceId = dynamic_cast<Orthanc::SingleValueObject<std::string>&>(*instance).GetValue();
      const std::string uri = GetCacheUri(instanceId);

      Json::Value instanceTags;
      std::string metadata;
      if (!OrthancPlugins::RestApiGetString(metadata, uri, false) &&
          EncodeOhifInstance(instanceTags, instanceId))
      {
        CacheAsMetadata(instanceTags, instanceId);
      }
    }
  }
}


OrthancPluginErrorCode OnChangeCallback(OrthancPluginChangeType changeType,
                                        OrthancPluginResourceType resourceType,
                                        const char* resourceId)
{
  try
  {
    switch (changeType)
    {
      case OrthancPluginChangeType_OrthancStarted:
      {
        continueThread_ = true;

        switch (dataSource_)
        {
          case DataSource_DicomWeb:
          {
            Json::Value info;
            if (!OrthancPlugins::RestApiGet(info, "/plugins/dicom-web", false))
            {
              throw Orthanc::OrthancException(
                Orthanc::ErrorCode_InternalError,
                "The OHIF plugin requires the DICOMweb plugin to be installed");
            }

            if (info.type() != Json::objectValue ||
                !info.isMember("ID") ||
                !info.isMember("Version") ||
                info["ID"].type() != Json::stringValue ||
                info["Version"].type() != Json::stringValue ||
                info["ID"].asString() != "dicom-web")
            {
              throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError,
                                              "The DICOMweb plugin is required by OHIF, but is not properly installed");
            }

            break;
          }

          case DataSource_DicomJson:
          {
            if (preload_)
            {
              metadataThread_ = boost::thread(MetadataThread);
              ORTHANC_PLUGINS_LOG_INFO("Started the OHIF preload thread");
            }
            else
            {
              ORTHANC_PLUGINS_LOG_INFO("The OHIF preload thread was not started, as indicated in the configuration file");
            }
            break;
          }

          default:
            throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
        }
        
        break;
      }

      case OrthancPluginChangeType_OrthancStopped:
      {
        continueThread_ = false;

        if (metadataThread_.joinable())
        {
          ORTHANC_PLUGINS_LOG_INFO("Stopping the OHIF preload thread");
          metadataThread_.join();
        }
        break;
      }

      case OrthancPluginChangeType_NewInstance:
      {
        if (metadataThread_.joinable() &&
            pendingInstances_.GetSize() < MAX_INSTANCES_IN_QUEUE) /* avoid overwhelming Orthanc */
        {
          pendingInstances_.Enqueue(new Orthanc::SingleValueObject<std::string>(resourceId));
        }

        break;
      }

      default:
        break;
    }
  }
  catch (Orthanc::OrthancException& e)
  {
    ORTHANC_PLUGINS_LOG_ERROR("Exception: " + std::string(e.What()));
    return static_cast<OrthancPluginErrorCode>(e.GetErrorCode());
  }

  return OrthancPluginErrorCode_Success;
}


extern "C"
{
  ORTHANC_PLUGINS_API int32_t OrthancPluginInitialize(OrthancPluginContext* context)
  {
    OrthancPlugins::SetGlobalContext(context, ORTHANC_PLUGIN_NAME);

#if ORTHANC_FRAMEWORK_VERSION_IS_ABOVE(1, 12, 4)
    Orthanc::Logging::InitializePluginContext(context, ORTHANC_PLUGIN_NAME);
#elif ORTHANC_FRAMEWORK_VERSION_IS_ABOVE(1, 7, 2)
    Orthanc::Logging::InitializePluginContext(context);
#else
    Orthanc::Logging::Initialize(context);
#endif

    /* Check the version of the Orthanc core */
    if (OrthancPluginCheckVersion(context) == 0)
    {
      char info[1024];
      sprintf(info, "Your version of Orthanc (%s) must be above %d.%d.%d to run this plugin",
              context->orthancVersion,
              ORTHANC_PLUGINS_MINIMAL_MAJOR_NUMBER,
              ORTHANC_PLUGINS_MINIMAL_MINOR_NUMBER,
              ORTHANC_PLUGINS_MINIMAL_REVISION_NUMBER);
      OrthancPluginLogError(context, info);
      return -1;
    }

    try
    {
      InitializeOhifTags();

      OrthancPlugins::OrthancConfiguration configuration;

      {
        OrthancPlugins::OrthancConfiguration globalConfiguration;
        globalConfiguration.GetSection(configuration, "OHIF");
      }

      routerBasename_ = configuration.GetStringValue("RouterBasename", "/ohif/");
      std::string s = configuration.GetStringValue("DataSource", "dicom-web");
      std::string userConfigurationPath = configuration.GetStringValue("UserConfiguration", "");
      preload_ = configuration.GetBooleanValue("Preload", true);

      static const std::string SOURCE_DICOM_WEB = "dicom-web";
      static const std::string SOURCE_DICOM_JSON = "dicom-json";

      if (s == SOURCE_DICOM_WEB)
      {
        dataSource_ = DataSource_DicomWeb;
      }
      else if (s == SOURCE_DICOM_JSON)
      {
        dataSource_ = DataSource_DicomJson;
      }
      else
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange,
                                        "Configuration option \"OHIF.DataSource\" must be either "
                                        "\"" + SOURCE_DICOM_WEB +"\" or \"" + SOURCE_DICOM_JSON + "\", but found: " + s);
      }

      if (userConfigurationPath.empty())
      {
        Orthanc::EmbeddedResources::GetFileResource(userConfiguration_, Orthanc::EmbeddedResources::APP_CONFIG_USER);
      }
      else
      {
        Orthanc::SystemToolbox::ReadFile(userConfiguration_, userConfigurationPath);
      }

      // Make sure that the router basename ends with a trailing slash
      if (routerBasename_.empty() ||
          routerBasename_[routerBasename_.size() - 1] != '/')
      {
        routerBasename_ += "/";
      }

      OrthancPlugins::SetDescription(ORTHANC_PLUGIN_NAME, "OHIF plugin for Orthanc.");

      OrthancPlugins::RegisterRestCallback<ServeFile>("/ohif", true);
      OrthancPlugins::RegisterRestCallback<ServeFile>("/ohif/(.*)", true);
      OrthancPlugins::RegisterRestCallback<GetOhifStudy>("/studies/([0-9a-f-]+)/ohif-dicom-json", true);

      OrthancPluginRegisterOnChangeCallback(context, OnChangeCallback);

      {
        // Extend the default Orthanc Explorer with custom JavaScript for OHIF
        std::string explorer;
        Orthanc::EmbeddedResources::GetFileResource(explorer, Orthanc::EmbeddedResources::ORTHANC_EXPLORER);

        std::map<std::string, std::string> dictionary;
        dictionary["USE_DICOM_WEB"] = (dataSource_ == DataSource_DicomWeb ? "true" : "false");
        explorer = Orthanc::Toolbox::SubstituteVariables(explorer, dictionary);
      
        OrthancPlugins::ExtendOrthancExplorer(ORTHANC_PLUGIN_NAME, explorer);
      }
    }
    catch (Orthanc::OrthancException& e)
    {
      return -1;
    }

    return 0;
  }


  ORTHANC_PLUGINS_API void OrthancPluginFinalize()
  {
  }


  ORTHANC_PLUGINS_API const char* OrthancPluginGetName()
  {
    return ORTHANC_PLUGIN_NAME;
  }


  ORTHANC_PLUGINS_API const char* OrthancPluginGetVersion()
  {
    return ORTHANC_OHIF_VERSION;
  }
}
