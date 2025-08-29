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


#include "QidoRs.h"

#include "../Resources/Orthanc/Plugins/OrthancPluginCppWrapper.h"
#include "Configuration.h"
#include "DicomWebFormatter.h"

#include <DicomFormat/DicomMap.h>
#include <DicomFormat/DicomTag.h>
#include <Logging.h>
#include <Toolbox.h>

#include <list>
#include <boost/lexical_cast.hpp>
#include <boost/regex.hpp>
#include <boost/algorithm/string/replace.hpp>


namespace
{
  class ModuleMatcher : public boost::noncopyable
  {
  public:
    typedef std::map<Orthanc::DicomTag, std::string>  Filters;

  private:
    bool                          fuzzy_;
    unsigned int                  offset_;
    unsigned int                  limit_;
    std::list<Orthanc::DicomTag>  includeFields_;
    bool                          includeAllFields_;
    Filters                       filters_;
    bool                          filteredStudyInstanceUid_;
    bool                          filteredSeriesInstanceUid_;


    static void AddResultAttributesForLevel(std::set<Orthanc::DicomTag>& result,
                                            Orthanc::ResourceType level)
    {
      switch (level)
      {
        case Orthanc::ResourceType_Study:
          // http://dicom.nema.org/medical/dicom/2019a/output/html/part18.html#table_6.7.1-2
          //result.insert(Orthanc::DicomTag(0x0008, 0x0005));  // Specific Character Set  => SPECIAL CASE
          result.insert(Orthanc::DicomTag(0x0008, 0x0020));  // Study Date
          result.insert(Orthanc::DicomTag(0x0008, 0x0030));  // Study Time
          result.insert(Orthanc::DicomTag(0x0008, 0x0050));  // Accession Number
          result.insert(Orthanc::DicomTag(0x0008, 0x0056));  // Instance Availability
          result.insert(Orthanc::DicomTag(0x0008, 0x0061));  // Modalities in Study  => SPECIAL CASE
          result.insert(Orthanc::DicomTag(0x0008, 0x0090));  // Referring Physician's Name
          result.insert(Orthanc::DicomTag(0x0008, 0x0201));  // Timezone Offset From UTC
          //result.insert(Orthanc::DicomTag(0x0008, 0x1190));  // Retrieve URL  => SPECIAL CASE
          result.insert(Orthanc::DicomTag(0x0010, 0x0010));  // Patient's Name
          result.insert(Orthanc::DicomTag(0x0010, 0x0020));  // Patient ID
          result.insert(Orthanc::DicomTag(0x0010, 0x0030));  // Patient's Birth Date
          result.insert(Orthanc::DicomTag(0x0010, 0x0040));  // Patient's Sex
          result.insert(Orthanc::DicomTag(0x0020, 0x000D));  // Study Instance UID
          result.insert(Orthanc::DicomTag(0x0020, 0x0010));  // Study ID
          result.insert(Orthanc::DicomTag(0x0020, 0x1206));  // Number of Study Related Series  => SPECIAL CASE
          result.insert(Orthanc::DicomTag(0x0020, 0x1208));  // Number of Study Related Instances  => SPECIAL CASE
          break;

        case Orthanc::ResourceType_Series:
          // http://dicom.nema.org/medical/dicom/2019a/output/html/part18.html#table_6.7.1-2a
          //result.insert(Orthanc::DicomTag(0x0008, 0x0005));  // Specific Character Set  => SPECIAL CASE
          result.insert(Orthanc::DicomTag(0x0008, 0x0060));  // Modality
          result.insert(Orthanc::DicomTag(0x0008, 0x0201));  // Timezone Offset From UTC
          result.insert(Orthanc::DicomTag(0x0008, 0x103E));  // Series Description
          //result.insert(Orthanc::DicomTag(0x0008, 0x1190));  // Retrieve URL  => SPECIAL CASE
          result.insert(Orthanc::DicomTag(0x0020, 0x000E));  // Series Instance UID
          result.insert(Orthanc::DicomTag(0x0020, 0x0011));  // Series Number
          result.insert(Orthanc::DicomTag(0x0020, 0x1209));  // Number of Series Related Instances  => SPECIAL CASE
          result.insert(Orthanc::DicomTag(0x0040, 0x0244));  // Performed Procedure Step Start Date
          result.insert(Orthanc::DicomTag(0x0040, 0x0245));  // Performed Procedure Step Start Time
          result.insert(Orthanc::DicomTag(0x0040, 0x0275));  // Request Attribute Sequence
          break;

        case Orthanc::ResourceType_Instance:
          // http://dicom.nema.org/medical/dicom/2019a/output/html/part18.html#table_6.7.1-2b
          //result.insert(Orthanc::DicomTag(0x0008, 0x0005));  // Specific Character Set  => SPECIAL CASE
          result.insert(Orthanc::DicomTag(0x0008, 0x0016));  // SOP Class UID
          result.insert(Orthanc::DicomTag(0x0008, 0x0018));  // SOP Instance UID
          result.insert(Orthanc::DicomTag(0x0008, 0x0056));  // Instance Availability
          result.insert(Orthanc::DicomTag(0x0008, 0x0201));  // Timezone Offset From UTC
          result.insert(Orthanc::DicomTag(0x0008, 0x1190));  // Retrieve URL
          result.insert(Orthanc::DicomTag(0x0020, 0x0013));  // Instance Number
          result.insert(Orthanc::DicomTag(0x0028, 0x0010));  // Rows
          result.insert(Orthanc::DicomTag(0x0028, 0x0011));  // Columns
          result.insert(Orthanc::DicomTag(0x0028, 0x0100));  // Bits Allocated
          result.insert(Orthanc::DicomTag(0x0028, 0x0008));  // Number of Frames
          break;

        default:
          throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
      }
    }


  public:
    explicit ModuleMatcher(const OrthancPluginHttpRequest* request) :
      fuzzy_(false),
      offset_(0),
      limit_(0),
      includeAllFields_(false),
      filteredStudyInstanceUid_(false),
      filteredSeriesInstanceUid_(false)
    {
      std::string args;
      
      for (uint32_t i = 0; i < request->getCount; i++)
      {
        std::string key(request->getKeys[i]);
        if (key.empty())
        {
          /**
           * This case can happen in Weasis, which uses the following
           * URL if doing a basic QIDO-RS request (note the "?&"):
           * http://localhost:8042/dicom-web/studies?&includefield=00080020,00080030,00080050,00080061,00080090,00081030,00100010,00100020,00100021,00100030,00100040,0020000D,00200010&limit=10&offset=0
           **/
          continue;
        }

        std::string value(request->getValues[i]);
        args += " [" + key + "=" + value + "]";

        if (key == "limit")
        {
          limit_ = boost::lexical_cast<unsigned int>(value);
        }
        else if (key == "offset")
        {
          offset_ = boost::lexical_cast<unsigned int>(value);
        }
        else if (key == "fuzzymatching")
        {
          if (value == "true")
          {
            fuzzy_ = true;
          }
          else if (value == "false")
          {
            fuzzy_ = false;
          }
          else
          {
            throw Orthanc::OrthancException(
              Orthanc::ErrorCode_BadRequest,
              "Not a proper value for fuzzy matching (true or false): " + value);
          }
        }
        else if (key == "includefield")
        {
          if (value == "all")
          {
            includeAllFields_ = true;
          }
          else
          {
            // Split a comma-separated list of tags
            std::vector<std::string> tags;
            Orthanc::Toolbox::TokenizeString(tags, value, ',');
            
            for (size_t j = 0; j < tags.size(); j++)
            {
              Orthanc::DicomTag tag(0, 0);
              if (OrthancPlugins::ParseTag(tag, tags[j]))
              {
                includeFields_.push_back(tag);
              }
            }
          }
        }
        else
        {
          Orthanc::DicomTag tag(0, 0);
          if (OrthancPlugins::ParseTag(tag, key))
          {
            // The following lines are new in DICOMweb > 1.0, and
            // allow one to query against a list of multiple values
            // http://dicom.nema.org/MEDICAL/dicom/2019a/output/chtml/part18/sect_6.7.html#sect_6.7.1.1.1
            boost::replace_all(value, "\\", "");  // Remove backslashes from source request

            // Replace commas by backslashes
            boost::replace_all(value, ",", "\\");
            boost::replace_all(value, "%2c", "\\");
            boost::replace_all(value, "%2C", "\\");
            
            AddFilter(tag, value, false);
          }
        }
      }

      LOG(INFO) << "Arguments of QIDO-RS request:" << args;
    }

    unsigned int GetLimit() const
    {
      return limit_;
    }

    unsigned int GetOffset() const
    {
      return offset_;
    }

    void AddFilter(const Orthanc::DicomTag& tag,
                   const std::string& constraint,
                   bool isFromPath)
    {
      filters_[tag] = constraint;

      if (!isFromPath)
      {
        if (tag == Orthanc::DICOM_TAG_STUDY_INSTANCE_UID)
        {
          filteredStudyInstanceUid_ = true;
        }
        else if (tag == Orthanc::DICOM_TAG_SERIES_INSTANCE_UID)
        {
          filteredSeriesInstanceUid_ = true;
        }
      }
    }

    void Print(std::ostream& out) const 
    {
      for (Filters::const_iterator it = filters_.begin(); 
           it != filters_.end(); ++it)
      {
        printf("Filter [%04x,%04x] = [%s]\n", it->first.GetGroup(), it->first.GetElement(), it->second.c_str());
      }
      printf("QIDO on StudyInstanceUID: %d\n", filteredStudyInstanceUid_);
      printf("QIDO on SeriesInstanceUID: %d\n\n", filteredSeriesInstanceUid_);
    }

    void ConvertToOrthanc(Json::Value& result,
                          Orthanc::ResourceType level) const
    {
      result = Json::objectValue;

      switch (level)
      {
        case Orthanc::ResourceType_Study:
          result["Level"] = "Study";
          break;

        case Orthanc::ResourceType_Series:
          result["Level"] = "Series";
          break;

        case Orthanc::ResourceType_Instance:
          result["Level"] = "Instance";
          break;

        default:
          throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
      }

      bool caseSensitive;
      if (OrthancPlugins::Configuration::LookupBooleanValue(caseSensitive, "QidoCaseSensitive"))
      {
        result["CaseSensitive"] = caseSensitive;
      }

      result["Expand"] = true;
      result["Full"] = true;
      result["Query"] = Json::objectValue;
      result["Limit"] = limit_;
      result["Since"] = offset_;
      result["RequestedTags"] = Json::arrayValue;

      if (offset_ != 0 &&
          !OrthancPlugins::CheckMinimalOrthancVersion(1, 3, 0))
      {
        LOG(ERROR) << "QIDO-RS request with \"offset\" argument: "
                      "Only available if the Orthanc core version is >= 1.3.0";
      }
      
      for (Filters::const_iterator it = filters_.begin(); 
           it != filters_.end(); ++it)
      {
        result["Query"][it->first.Format()] = it->second;
      }

      std::set<Orthanc::DicomTag> requestedTags;
      ExtractResultFields(requestedTags, level);

      for (std::set<Orthanc::DicomTag>::const_iterator it = requestedTags.begin();
          it != requestedTags.end(); ++it)
      {
        result["RequestedTags"].append(it->Format());
      }
    }



    void ExtractResultFields(std::set<Orthanc::DicomTag>& fields,
                             Orthanc::ResourceType level) const
    {
      for (std::list<Orthanc::DicomTag>::const_iterator
             it = includeFields_.begin(); it != includeFields_.end(); ++it)
      {
        fields.insert(*it);
      }

      // The list of attributes for this query level
      AddResultAttributesForLevel(fields, level);

      // All other attributes passed as query keys
      for (Filters::const_iterator it = filters_.begin();
           it != filters_.end(); ++it)
      {
        fields.insert(it->first);
      }

      // For instances and series, add all Study-level attributes if
      // {StudyInstanceUID} is not specified.
      if (!filteredStudyInstanceUid_ &&
          (level == Orthanc::ResourceType_Instance ||
           level == Orthanc::ResourceType_Series))
      {
        AddResultAttributesForLevel(fields, Orthanc::ResourceType_Study);
      }

      // For instances, add all Series-level attributes if
      // {SeriesInstanceUID} is not specified.
      if (!filteredSeriesInstanceUid_ &&
          level == Orthanc::ResourceType_Instance)
      {
        AddResultAttributesForLevel(fields, Orthanc::ResourceType_Series);
      }

    }

    void ExtractFields(Orthanc::DicomMap& result,
                       const Orthanc::DicomMap& source,
                       const std::string& wadoBasePublicUrl,
                       Orthanc::ResourceType level) const
    {
      std::set<Orthanc::DicomTag> fields;
      ExtractResultFields(fields, level);

      // Copy all the required fields to the target
      for (std::set<Orthanc::DicomTag>::const_iterator
             it = fields.begin(); it != fields.end(); ++it)
      {
        if (source.HasTag(*it))
        {
          const Orthanc::DicomValue& val = source.GetValue(*it);
          result.SetValue(*it, val);
        }
      }

      // Set the retrieve URL for WADO-RS
      std::string url = (wadoBasePublicUrl + "studies/" +
                         source.GetStringValue(Orthanc::DICOM_TAG_STUDY_INSTANCE_UID, "", false));

      if (level == Orthanc::ResourceType_Series || 
          level == Orthanc::ResourceType_Instance)
      {
        url += "/series/" + source.GetStringValue(Orthanc::DICOM_TAG_SERIES_INSTANCE_UID, "", false);
      }

      if (level == Orthanc::ResourceType_Instance)
      {
        url += "/instances/" + source.GetStringValue(Orthanc::DICOM_TAG_SOP_INSTANCE_UID, "", false);
      }
    
      static const Orthanc::DicomTag DICOM_TAG_RETRIEVE_URL(0x0008, 0x1190);
      result.SetValue(DICOM_TAG_RETRIEVE_URL, url, false);
    }
  };
}



static void ApplyMatcher(OrthancPluginRestOutput* output,
                         const OrthancPluginHttpRequest* request,
                         const ModuleMatcher& matcher,
                         Orthanc::ResourceType level)
{
  Json::Value find;
  matcher.ConvertToOrthanc(find, level);

  LOG(INFO) << "Body of the call from QIDO-RS to /tools/find: " << find.toStyledString();
  
  std::map<std::string, std::string> httpHeaders;
  OrthancPlugins::GetHttpHeaders(httpHeaders, request);

  Json::Value resources;
  if (!OrthancPlugins::RestApiPost(resources, "/tools/find", find, httpHeaders, true) ||
      resources.type() != Json::arrayValue)
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
  }

  std::string wadoBasePublicUrl = OrthancPlugins::Configuration::GetBasePublicUrl(request);

  OrthancPlugins::DicomWebFormatter::HttpWriter writer(
    output, OrthancPlugins::Configuration::IsXmlExpected(request));

  for (Json::Value::ArrayIndex i = 0; i < resources.size(); i++)
  {
    const Json::Value& resource = resources[i];

    Orthanc::DicomMap source;
    if (resource["RequestedTags"].isObject())
    {
      source.FromDicomAsJson(resource["RequestedTags"], false, true);
    }

    Orthanc::DicomMap target;

    // since we are populating the target with values from JSON, all string are actually UTF-8
    target.SetValue(Orthanc::DICOM_TAG_SPECIFIC_CHARACTER_SET, "ISO_IR 192", false);

    matcher.ExtractFields(target, source, wadoBasePublicUrl, level);
    writer.AddOrthancMap(target);
  }
  writer.Send();
}



void SearchForStudies(OrthancPluginRestOutput* output,
                      const char* url,
                      const OrthancPluginHttpRequest* request)
{
  if (request->method != OrthancPluginHttpMethod_Get)
  {
    OrthancPluginSendMethodNotAllowed(OrthancPlugins::GetGlobalContext(), output, "GET");
  }
  else
  {
    ModuleMatcher matcher(request);
    ApplyMatcher(output, request, matcher, Orthanc::ResourceType_Study);
  }
}


void SearchForSeries(OrthancPluginRestOutput* output,
                     const char* url,
                     const OrthancPluginHttpRequest* request)
{
  if (request->method != OrthancPluginHttpMethod_Get)
  {
    OrthancPluginSendMethodNotAllowed(OrthancPlugins::GetGlobalContext(), output, "GET");
  }
  else
  {
    ModuleMatcher matcher(request);

    if (request->groupsCount == 1)
    {
      // The "StudyInstanceUID" is provided by the regular expression
      matcher.AddFilter(Orthanc::DICOM_TAG_STUDY_INSTANCE_UID, request->groups[0], true);
    }

    ApplyMatcher(output, request, matcher, Orthanc::ResourceType_Series);
  }
}


void SearchForInstances(OrthancPluginRestOutput* output,
                        const char* url,
                        const OrthancPluginHttpRequest* request)
{
  if (request->method != OrthancPluginHttpMethod_Get)
  {
    OrthancPluginSendMethodNotAllowed(OrthancPlugins::GetGlobalContext(), output, "GET");
  }
  else
  {
    ModuleMatcher matcher(request);

    if (request->groupsCount == 1 || 
        request->groupsCount == 2)
    {
      // The "StudyInstanceUID" is provided by the regular expression
      matcher.AddFilter(Orthanc::DICOM_TAG_STUDY_INSTANCE_UID, request->groups[0], true);
    }

    if (request->groupsCount == 2)
    {
      // The "SeriesInstanceUID" is provided by the regular expression
      matcher.AddFilter(Orthanc::DICOM_TAG_SERIES_INSTANCE_UID, request->groups[1], true);
    }

    ApplyMatcher(output, request, matcher, Orthanc::ResourceType_Instance);
  }
}
