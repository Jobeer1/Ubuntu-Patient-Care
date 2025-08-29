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


#include "DicomWebFormatter.h"

#include "../Resources/Orthanc/Plugins/OrthancPluginCppWrapper.h"

#if !defined(NDEBUG)  // In debug mode, check that the value is actually a JSON string
#  include <Toolbox.h>
#endif


namespace OrthancPlugins
{
  static std::string FormatTag(uint16_t group,
                               uint16_t element)
  {
    char buf[16];
    sprintf(buf, "%04x%04x", group, element);
    return std::string(buf);
  }


  void DicomWebFormatter::Callback(OrthancPluginDicomWebNode *node,
                                   OrthancPluginDicomWebSetBinaryNode setter,
                                   uint32_t levelDepth,
                                   const uint16_t *levelTagGroup,
                                   const uint16_t *levelTagElement,
                                   const uint32_t *levelIndex,
                                   uint16_t tagGroup,
                                   uint16_t tagElement,
                                   OrthancPluginValueRepresentation vr,
                                   void* payload)
  {
    const DicomWebFormatter& that = *reinterpret_cast<const DicomWebFormatter*>(payload);

    switch (that.mode_)
    {
      case OrthancPluginDicomWebBinaryMode_Ignore:
      case OrthancPluginDicomWebBinaryMode_InlineBinary:
        setter(node, that.mode_, NULL);
        break;

      case OrthancPluginDicomWebBinaryMode_BulkDataUri:
      {
        std::string uri = that.bulkRoot_;

        for (size_t i = 0; i < levelDepth; i++)
        {
          uri += ("/" + FormatTag(levelTagGroup[i], levelTagElement[i]) + "/" +
                  boost::lexical_cast<std::string>(levelIndex[i] + 1));
        }
    
        uri += "/" + FormatTag(tagGroup, tagElement);
    
        setter(node, that.mode_, uri.c_str());
        break;
      }
    }
  }


  void DicomWebFormatter::Apply(std::string& target,
                                OrthancPluginContext* context,
                                const void* data,
                                size_t size,
                                bool xml,
                                OrthancPluginDicomWebBinaryMode mode,
                                const std::string& bulkRoot)
  {
    DicomWebFormatter payload(mode, bulkRoot);

    OrthancString s;

    if (xml)
    {
      s.Assign(OrthancPluginEncodeDicomWebXml2(context, data, size, Callback, &payload));
    }
    else
    {
      s.Assign(OrthancPluginEncodeDicomWebJson2(context, data, size, Callback, &payload));
    }

    if (s.GetContent() == NULL)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError,
                                      "Cannot convert DICOM to DICOMweb");
    }
    else
    {
      s.ToString(target);
    }
  }


  void DicomWebFormatter::Apply(std::string& target,
                                OrthancPluginContext* context,
                                const Json::Value& value,
                                bool xml,
                                OrthancPluginDicomWebBinaryMode mode,
                                const std::string& bulkRoot)
  {
    MemoryBuffer dicom;
    dicom.CreateDicom(value, OrthancPluginCreateDicomFlags_None);
    Apply(target, context, dicom.GetData(), dicom.GetSize(), xml, mode, bulkRoot);
  }


  void DicomWebFormatter::Apply(std::string& target,
                                OrthancPluginContext* context,
                                const DicomInstance& instance,
                                bool xml,
                                OrthancPluginDicomWebBinaryMode mode,
                                const std::string& bulkRoot)
  {
    DicomWebFormatter payload(mode, bulkRoot);

    OrthancString s;

    if (xml)
    {
      s.Assign(OrthancPluginGetInstanceDicomWebXml(context, instance.GetObject(), Callback, &payload));
    }
    else
    {
      s.Assign(OrthancPluginGetInstanceDicomWebJson(context, instance.GetObject(), Callback, &payload));
    }

    if (s.GetContent() == NULL)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError,
                                      "Cannot convert DICOM to DICOMweb");
    }
    else
    {
      s.ToString(target);
    }
  }


  DicomWebFormatter::HttpWriter::HttpWriter(OrthancPluginRestOutput* output,
                                            bool isXml) :
    context_(GetGlobalContext()),
    output_(output),
    isXml_(isXml),
    first_(true)
  {
    if (context_ == NULL ||
        (isXml_ && output_ == NULL))  // allow no output when working with Json output.
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_NullPointer);
    }

    if (isXml_)
    {
      OrthancPluginStartMultipartAnswer(context_, output_, "related", "application/dicom+xml");
    }
    else
    {
      jsonBuffer_.AddChunk("[");
    }
  }


  void DicomWebFormatter::HttpWriter::AddInternal(const void* dicom,
                                                  size_t size,
                                                  OrthancPluginDicomWebBinaryMode mode,
                                                  const std::string& bulkRoot)
  {
    if (!first_ &&
        !isXml_)
    {
      jsonBuffer_.AddChunk(",");      
    }

    first_ = false;

    std::string item;

    DicomWebFormatter::Apply(item, context_, dicom, size, isXml_, mode, bulkRoot);
   
    if (isXml_)
    {
      OrthancPluginSendMultipartItem(context_, output_, item.c_str(), item.size());
    }
    else
    {
      jsonBuffer_.AddChunk(item);
    }
  }


  static void ToShortDicomAsJson(Json::Value& target, const Json::Value& fullJsonSource)
  {
    // printf("%s", fullJsonSource.toStyledString().c_str());

    if (fullJsonSource.isArray() && target.isArray())
    {
      for (Json::Value::ArrayIndex i = 0; i < fullJsonSource.size(); ++i)
      {
        Json::Value& child = target.append(Json::objectValue);
        ToShortDicomAsJson(child, fullJsonSource[i]);
      }
    }
    else if (fullJsonSource.isObject() && target.isObject())
    {
      const Json::Value::Members& members = fullJsonSource.getMemberNames();
      for (Json::Value::Members::const_iterator member = members.begin();
           member != members.end(); ++member)
      {
        target[*member] = Json::objectValue;
        const Json::Value& jsonSourceMember = fullJsonSource[*member];
        if (jsonSourceMember.isMember("Type"))
        {
          if (jsonSourceMember["Type"] == "String")
          {
            target[*member] = jsonSourceMember["Value"];
          }
          else if (jsonSourceMember["Type"] == "Sequence")
          {
            target[*member] = Json::arrayValue;
            ToShortDicomAsJson(target[*member], jsonSourceMember["Value"]);
          }
          else if (jsonSourceMember["Type"] == "Null")
          {
            target[*member] = Json::nullValue;
          }
        }
      }
    }
  }
                  
  void DicomWebFormatter::HttpWriter::AddOrthancMap(const Orthanc::DicomMap& value)
  {
    Json::Value json = Json::objectValue;

    std::set<Orthanc::DicomTag> tags;
    value.GetTags(tags);
    
    // construct a "short" DicomAsJson that can be used in CreateDicom
    for (std::set<Orthanc::DicomTag>::const_iterator
           it = tags.begin(); it != tags.end(); ++it)
    {
      const Orthanc::DicomValue& v = value.GetValue(*it);
      if (v.IsSequence())
      {
        json[it->Format()] = Json::arrayValue;
        ToShortDicomAsJson(json[it->Format()], v.GetSequenceContent());
      }
      else
      {
        std::string s;
        if (value.LookupStringValue(s, *it, false))
        {
          json[it->Format()] = s;
        }
      }
    }
    
    AddOrthancJson(json);
  }


  void DicomWebFormatter::HttpWriter::AddOrthancJson(const Json::Value& value)
  {
    MemoryBuffer dicom;
    dicom.CreateDicom(value, OrthancPluginCreateDicomFlags_None);

    AddInternal(dicom.GetData(), dicom.GetSize(), OrthancPluginDicomWebBinaryMode_Ignore, "");
  }


  void DicomWebFormatter::HttpWriter::AddDicomWebInstanceSerializedJson(const void* data,
                                                                        size_t size)
  {
    if (isXml_)
    {
      // This function can only be used in the JSON case
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
    }

#if !defined(NDEBUG)  // In debug mode, check that the value is actually a JSON string
    Json::Value json;
    if (!OrthancPlugins::ReadJson(json, data, size))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
    }
#endif
    
    if (first_)
    {
      first_ = false;
    }
    else
    {
      jsonBuffer_.AddChunk(",");
    }
    
    jsonBuffer_.AddChunk(data, size);
  }

  void DicomWebFormatter::HttpWriter::AddDicomWebSeriesSerializedJson(const void* data,
                                                                      size_t size)
  {
    if (isXml_)
    {
      // This function can only be used in the JSON case
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
    }

#if !defined(NDEBUG)  // In debug mode, check that the value is actually a JSON string
    Json::Value json;
    if (!OrthancPlugins::ReadJson(json, data, size))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
    }
#endif
    
    if (size <= 2 ||
        reinterpret_cast<const char*>(data)[0] != '[' ||
        reinterpret_cast<const char*>(data)[size-1] != ']')
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat, "The series metadata json does not contain an array.");
    }

    if (first_)
    {
      first_ = false;
    }
    else
    {
      jsonBuffer_.AddChunk(",");
    }
    
    jsonBuffer_.AddChunk(reinterpret_cast<const char*>(data) + 1, size - 2);  // remove leading and trailing []
  }

  void DicomWebFormatter::HttpWriter::Send()
  {
    if (!isXml_)
    {
      jsonBuffer_.AddChunk("]");
      
      std::string answer;
      jsonBuffer_.Flatten(answer);
      OrthancPluginAnswerBuffer(context_, output_, answer.c_str(), answer.size(), "application/dicom+json");
    }
  }

  void DicomWebFormatter::HttpWriter::CloseAndGetJsonOutput(std::string& target)
  {
    if (!isXml_)
    {
      jsonBuffer_.AddChunk("]");
      
      jsonBuffer_.Flatten(target);
    }
  }

  void DicomWebFormatter::HttpWriter::AddInstance(const DicomInstance& instance,
                                                  const std::string& bulkRoot)
  {
    if (!first_ &&
        !isXml_)
    {
      jsonBuffer_.AddChunk(",");
    }

    first_ = false;

    std::string item;

    DicomWebFormatter::Apply(item, context_, instance, isXml_, OrthancPluginDicomWebBinaryMode_BulkDataUri, bulkRoot);
   
    if (isXml_)
    {
      OrthancPluginSendMultipartItem(context_, output_, item.c_str(), item.size());
    }
    else
    {
      jsonBuffer_.AddChunk(item);
    }
  }
}
