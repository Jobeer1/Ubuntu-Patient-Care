/**
 * Stone of Orthanc
 * Copyright (C) 2012-2016 Sebastien Jodogne, Medical Physics
 * Department, University Hospital of Liege, Belgium
 * Copyright (C) 2017-2023 Osimis S.A., Belgium
 * Copyright (C) 2021-2025 Sebastien Jodogne, ICTEAM UCLouvain, Belgium
 *
 * This program is free software: you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public License
 * as published by the Free Software Foundation, either version 3 of
 * the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this program. If not, see
 * <http://www.gnu.org/licenses/>.
 **/


#include "OrthancNativeDataset.h"

#include <OrthancException.h>


static const char* const NAME = "Name";
static const char* const TYPE = "Type";
static const char* const VALUE = "Value";


namespace OrthancStone
{
  const Json::Value* OrthancNativeDataset::LookupValue(std::string& type,
                                                       const Orthanc::DicomPath& path) const
  {
    if (path.IsPrefixUniversal(0))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
    }

    const Orthanc::DicomValue* rootSequence = dicom_->TestAndGetValue(path.GetPrefixTag(0));
    if (rootSequence == NULL ||
        !rootSequence->IsSequence())
    {
      return NULL;
    }

    Json::ArrayIndex index = path.GetPrefixIndex(0);

    if (rootSequence->GetSequenceContent().type() != Json::arrayValue)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
    }

    if (index >= rootSequence->GetSequenceContent().size())
    {
      return NULL;
    }

    const Json::Value* current = &(rootSequence->GetSequenceContent() [index]);

    for (size_t i = 1; i < path.GetPrefixLength(); i++)
    {
      if (path.IsPrefixUniversal(i))
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
      }

      index = path.GetPrefixIndex(i);
      std::string tag = path.GetPrefixTag(i).Format();

      if (current->type() != Json::objectValue)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
      }

      if (!current->isMember(tag))
      {
        return NULL;
      }

      if ((*current) [tag].type() != Json::objectValue ||
          !(*current) [tag].isMember(NAME) ||
          !(*current) [tag].isMember(TYPE) ||
          !(*current) [tag].isMember(VALUE) ||
          (*current) [tag][NAME].type() != Json::stringValue ||
          (*current) [tag][TYPE].type() != Json::stringValue)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
      }

      if ((*current) [tag][TYPE].asString() != "Sequence" ||
          (*current) [tag][VALUE].type() != Json::arrayValue ||
          index >= (*current) [tag][VALUE].size())
      {
        return NULL;
      }

      current = &(*current) [tag][VALUE][index];
    }

    std::string tag = path.GetFinalTag().Format();

    if (current->type() != Json::objectValue)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
    }

    if (!current->isMember(tag))
    {
      return NULL;
    }

    if ((*current) [tag].type() != Json::objectValue ||
        !(*current) [tag].isMember(NAME) ||
        !(*current) [tag].isMember(TYPE) ||
        !(*current) [tag].isMember(VALUE) ||
        (*current) [tag][NAME].type() != Json::stringValue ||
        (*current) [tag][TYPE].type() != Json::stringValue)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
    }
    else
    {
      type = (*current) [tag][TYPE].asString();
      return &((*current) [tag][VALUE]);
    }
  }


  OrthancNativeDataset::OrthancNativeDataset(const Json::Value& dicom) :
    dicom_(new Orthanc::DicomMap)
  {
    dicom_->FromDicomAsJson(dicom, false, true /* parse sequences */);
  }


  bool OrthancNativeDataset::GetStringValue(std::string& result,
                                            const Orthanc::DicomPath& path) const
  {
    if (path.GetPrefixLength() == 0)
    {
      return dicom_->LookupStringValue(result, path.GetFinalTag(), false);
    }
    else
    {
      std::string type;
      const Json::Value* value = LookupValue(type, path);

      if (value == NULL)
      {
        return false;
      }
      else if (type == "String" &&
               value->type() == Json::stringValue)
      {
        result = value->asString();
        return true;
      }
      else
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
      }
    }
  }


  bool OrthancNativeDataset::GetSequenceSize(size_t& size,
                                             const Orthanc::DicomPath& path) const
  {
    if (path.GetPrefixLength() == 0)
    {
      const Orthanc::DicomValue* value = dicom_->TestAndGetValue(path.GetFinalTag());
      if (value == NULL ||
          !value->IsSequence())
      {
        return false;
      }
      else if (value->GetSequenceContent().type() != Json::arrayValue)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
      }
      else
      {
        size = value->GetSequenceContent().size();
        return true;
      }
    }
    else
    {
      std::string type;
      const Json::Value* value = LookupValue(type, path);

      if (value == NULL ||
          type != "Sequence")
      {
        return false;
      }
      else if (value->type() != Json::arrayValue)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
      }
      else
      {
        size = value->size();
        return true;
      }
    }
  }
}
