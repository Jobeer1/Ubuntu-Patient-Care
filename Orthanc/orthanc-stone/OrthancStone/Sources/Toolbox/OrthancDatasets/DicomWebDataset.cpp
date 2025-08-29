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


#include "DicomWebDataset.h"

#include <OrthancException.h>

#include <boost/lexical_cast.hpp>


static const char* const VALUE = "Value";
static const char* const VR = "vr";
static const char* const SQ = "SQ";
static const char* const ALPHABETIC = "Alphabetic";


namespace OrthancStone
{
  static const Json::Value* GetValue(std::string& vr,
                                     const Json::Value& node,
                                     const Orthanc::DicomTag& tag)
  {
    char id[16];
    sprintf(id, "%04X%04X", tag.GetGroup(), tag.GetElement());

    if (node.type() != Json::objectValue)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
    }

    if (!node.isMember(id))
    {
      return NULL;
    }

    if (node[id].type() == Json::objectValue &&
        node[id].isMember(VALUE) &&
        node[id].isMember(VR) &&
        node[id][VR].type() == Json::stringValue)
    {
      vr = node[id][VR].asString();
      return &node[id][VALUE];
    }
    else
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
    }
  }


  static const Json::Value* GetSequenceArray(const Json::Value& node,
                                             const Orthanc::DicomTag& tag)
  {
    std::string vr;
    const Json::Value* value = GetValue(vr, node, tag);

    if (value != NULL &&
        vr == SQ &&
        value->type() == Json::arrayValue)
    {
      return value;
    }
    else
    {
      return NULL;
    }
  }


  const Json::Value* DicomWebDataset::LookupValue(std::string& vr,
                                                  const Orthanc::DicomPath& path) const
  {
    const Json::Value* current = &dicomweb_;

    for (size_t i = 0; i < path.GetPrefixLength(); i++)
    {
      if (path.IsPrefixUniversal(i))
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
      }

      Json::ArrayIndex index = path.GetPrefixIndex(i);

      const Json::Value* next = GetSequenceArray(*current, path.GetPrefixTag(i));
      if (next != NULL &&
          index < next->size())
      {
        current = &((*next) [index]);
      }
      else
      {
        return NULL;
      }
    }

    return GetValue(vr, *current, path.GetFinalTag());
  }


  DicomWebDataset::DicomWebDataset(const Json::Value& dicomweb) :
    dicomweb_(dicomweb)
  {
    if (dicomweb.type() != Json::objectValue)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
    }
  }


  bool DicomWebDataset::GetStringValue(std::string& result,
                                       const Orthanc::DicomPath& path) const
  {
    std::string vr;
    const Json::Value* value = LookupValue(vr, path);

    if (value == NULL)
    {
      return false;
    }
    else if (value->type() == Json::arrayValue &&
             value->size() == 1u)
    {
      if ((*value) [0].type() == Json::stringValue && (
            // This is the list of all the string value representations:
            // https://dicom.nema.org/medical/dicom/current/output/chtml/part05/sect_6.2.html
            vr == "AE" ||
            vr == "AS" ||
            vr == "CS" ||
            vr == "DA" ||
            vr == "DT" ||
            vr == "LO" ||
            vr == "LT" ||
            vr == "SH" ||
            vr == "ST" ||
            vr == "TM" ||
            vr == "UC" ||
            vr == "UI" ||
            vr == "UR" ||
            vr == "UT"))
      {
        result = (*value) [0].asString();
        return true;
      }
      else if (vr == "PN" &&
               (*value) [0].type() == Json::objectValue &&
               (*value) [0].isMember(ALPHABETIC) &&
               (*value) [0][ALPHABETIC].type() == Json::stringValue)
      {
        result = (*value) [0][ALPHABETIC].asString();
        return true;
      }
      else if ((vr == "DS" ||
                vr == "FD" ||
                vr == "FL") &&
               (*value) [0].isDouble())
      {
        result = boost::lexical_cast<std::string>((*value) [0].asDouble());
        return true;
      }
      else if ((vr == "UL" ||
                vr == "US" ||
                vr == "UV") &&
               (*value) [0].isUInt64())
      {
        result = boost::lexical_cast<std::string>((*value) [0].asUInt64());
        return true;
      }
      else if ((vr == "IS" ||
                vr == "SL" ||
                vr == "SS" ||
                vr == "SV") &&
               (*value) [0].isInt64())
      {
        result = boost::lexical_cast<std::string>((*value) [0].asInt64());
        return true;
      }
      else
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented, "Unsupported value representation: " + vr);
      }
    }
    else if (value->type() == Json::arrayValue &&
             vr == "SQ")
    {
      return false;
    }
    else
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
    }
  }


  bool DicomWebDataset::GetSequenceSize(size_t& size,
                                        const Orthanc::DicomPath& path) const
  {
    std::string vr;
    const Json::Value* value = LookupValue(vr, path);

    if (value != NULL &&
        vr == SQ &&
        value->type() == Json::arrayValue)
    {
      size = value->size();
      return true;
    }
    else
    {
      return false;
    }
  }
}
