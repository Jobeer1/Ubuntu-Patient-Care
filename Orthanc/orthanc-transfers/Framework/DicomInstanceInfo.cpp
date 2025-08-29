/**
 * Transfers accelerator plugin for Orthanc
 * Copyright (C) 2018-2023 Osimis S.A., Belgium
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


#include "DicomInstanceInfo.h"

#include "../Resources/Orthanc/Plugins/OrthancPluginCppWrapper.h"

#include <OrthancException.h>
#include <Toolbox.h>

static const char *KEY_ID = "ID";
static const char *KEY_MD5 = "MD5";
static const char *KEY_SIZE = "Size";


namespace OrthancPlugins
{
  DicomInstanceInfo::DicomInstanceInfo(const std::string& id,
                                       const MemoryBuffer& buffer) :
    id_(id),
    size_(buffer.GetSize())
  {
    Orthanc::Toolbox::ComputeMD5(md5_, buffer.GetData(), buffer.GetSize());
  }

  
  DicomInstanceInfo::DicomInstanceInfo(const std::string& id,
                                       size_t size,
                                       const std::string& md5) :
    id_(id),
    size_(size),
    md5_(md5)
  {
  }


  DicomInstanceInfo::DicomInstanceInfo(const Json::Value& serialized)
  {
    if (serialized.type() != Json::objectValue ||
        !serialized.isMember(KEY_ID) ||
        !serialized.isMember(KEY_SIZE) ||
        !serialized.isMember(KEY_MD5) ||
        serialized[KEY_ID].type() != Json::stringValue ||
        serialized[KEY_SIZE].type() != Json::stringValue ||
        serialized[KEY_MD5].type() != Json::stringValue)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
    }
    else
    {
      id_ = serialized[KEY_ID].asString();
      md5_ = serialized[KEY_MD5].asString();
        
      try
      {
        size_ = boost::lexical_cast<size_t>(serialized[KEY_SIZE].asString());
      }
      catch (boost::bad_lexical_cast&)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);          
      }
    }
  }


  void DicomInstanceInfo::Serialize(Json::Value& target) const
  {
    target = Json::objectValue;
    target[KEY_ID] = id_;
    target[KEY_SIZE] = boost::lexical_cast<std::string>(size_);
    target[KEY_MD5] = md5_;
  }
}
