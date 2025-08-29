/**
 * Advanced authorization plugin for Orthanc
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

#include "OrthancResource.h"

#include "../Resources/Orthanc/Plugins/OrthancPluginCppWrapper.h"

static const char* LABELS_KEY = "Labels";

namespace OrthancPlugins
{
  void OrthancResource::GetDicomUidInternal(std::string& result,
                                            Orthanc::ResourceType level,
                                            const Json::Value& content)
  {
    std::string uidTag;
        
    switch (level)
    {
      case Orthanc::ResourceType_Patient:
        uidTag = "PatientID";
        break;

      case Orthanc::ResourceType_Study:
        uidTag = "StudyInstanceUID";
        break;

      case Orthanc::ResourceType_Series:
        uidTag = "SeriesInstanceUID";
        break;

      case Orthanc::ResourceType_Instance:
        uidTag = "SOPInstanceUID";
        break;

      default:
        throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }

    static const char* MAIN_DICOM_TAGS = "MainDicomTags";
      
    if (content.type() != Json::objectValue ||
        !content.isMember(MAIN_DICOM_TAGS))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_Plugin);
    }

    const Json::Value& mainDicomTags = content[MAIN_DICOM_TAGS];
    if (mainDicomTags.type() != Json::objectValue ||
        (mainDicomTags.isMember(uidTag) &&
         mainDicomTags[uidTag].type() != Json::stringValue))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_Plugin);
    }

    if (!mainDicomTags.isMember(uidTag))
    {
      result.clear();
    }
    else
    {
      result = mainDicomTags[uidTag].asString();
    }
  }


  Orthanc::ResourceType OrthancResource::GetLevel() const
  {
    if (IsValid())
    {
      return level_;
    }
    else
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
    }
  }
  

  const std::string& OrthancResource::GetIdentifier() const
  {
    if (IsValid())
    {
      return id_;
    }
    else
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
    }
  }

  
  bool OrthancResource::GetContent(Json::Value& content) const
  {
    if (!IsValid())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
    }

    std::string uri;
    switch (level_)
    {
      case Orthanc::ResourceType_Patient:
        uri = "patients";
        break;

      case Orthanc::ResourceType_Study:
        uri = "studies";
        break;

      case Orthanc::ResourceType_Series:
        uri = "series";
        break;

      case Orthanc::ResourceType_Instance:
        uri = "instances";
        break;

      default:
        throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }

    uri = "/" + uri + "/" + id_;
        
    return RestApiGet(content, uri, false /* ignore plugins */);
  }
  

  bool OrthancResource::GetDicomUid(std::string& dicomUid /* out */) const
  {
    Json::Value content;
        
    if (!GetContent(content))
    {
      return false;
    }
    else
    {
      GetDicomUidInternal(dicomUid, level_, content);
      return true;
    }
  }
  
    
  bool OrthancResource::GetHierarchy(std::string& dicomUid /* out */,
                                     OrthancResource& parent /* out */,
                                     std::list<OrthancResource>& children /* out */,
                                     std::set<std::string>& labels) const
  {
    Json::Value content;
        
    if (!GetContent(content))
    {
      return false;
    }

    std::string parentKey, childrenKey;
        
    switch (level_)
    {
      case Orthanc::ResourceType_Patient:
        childrenKey = "Studies";
        break;

      case Orthanc::ResourceType_Study:
        parentKey = "ParentPatient";
        childrenKey = "Series";
        break;

      case Orthanc::ResourceType_Series:
        parentKey = "ParentStudy";
        childrenKey = "Instances";
        break;

      case Orthanc::ResourceType_Instance:
        parentKey = "ParentSeries";
        break;

      default:
        throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }

    GetDicomUidInternal(dicomUid, level_, content);
      
    if (content.type() != Json::objectValue)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_Plugin);
    }

    if (!parentKey.empty())
    {
      if (!content.isMember(parentKey) ||
          content[parentKey].type() != Json::stringValue)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_Plugin);
      }

      parent = OrthancResource(Orthanc::GetParentResourceType(level_),
                               content[parentKey].asString());
    }

    children.clear();
        
    if (!childrenKey.empty())
    {
      if (!content.isMember(childrenKey) ||
          content[childrenKey].type() != Json::arrayValue)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_Plugin);
      }

      Orthanc::ResourceType childrenType = Orthanc::GetChildResourceType(level_);

      for (Json::Value::ArrayIndex i = 0; i < content[childrenKey].size(); i++)
      {
        const Json::Value& child = content[childrenKey][i];

        if (child.type() != Json::stringValue)
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_Plugin);
        }

        children.push_back(OrthancResource(childrenType, child.asString()));
      }
    }

    labels.clear();
    if (content.isMember(LABELS_KEY) || 
        content[LABELS_KEY].type() != Json::arrayValue)
    {
      for (Json::Value::ArrayIndex i = 0; i < content[LABELS_KEY].size(); i++)
      {
        const Json::Value& label = content[LABELS_KEY][i];

        if (label.type() != Json::stringValue)
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_Plugin);
        }

        labels.insert(label.asString());
      }
    }

    return true;
  }


  bool OrthancResource::LookupOrthancId(std::string& result,
                                        Orthanc::ResourceType level,
                                        const std::string& dicomUid)
  {
    OrthancString s;

    switch (level)
    {
      case Orthanc::ResourceType_Patient:
        s.Assign(OrthancPluginLookupPatient(GetGlobalContext(), dicomUid.c_str()));
        break;

      case Orthanc::ResourceType_Study:
        s.Assign(OrthancPluginLookupStudy(GetGlobalContext(), dicomUid.c_str()));
        break;

      case Orthanc::ResourceType_Series:
        s.Assign(OrthancPluginLookupSeries(GetGlobalContext(), dicomUid.c_str()));
        break;

      case Orthanc::ResourceType_Instance:
        s.Assign(OrthancPluginLookupInstance(GetGlobalContext(), dicomUid.c_str()));
        break;

      default:
        throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }

    if (s.GetContent() == NULL)
    {
      // Inexisting resource
      return false;
    }
    else
    {
      result.assign(s.GetContent());
      return true;
    }
  }
}
