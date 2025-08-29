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


#pragma once

#include <string>
#include <json/value.h>

namespace OrthancPlugins
{
  class MemoryBuffer;
  
  class DicomInstanceInfo
  {
  private:
    std::string   id_;
    size_t        size_;
    std::string   md5_;

  public:
    DicomInstanceInfo() :
      size_(0)
    {
    }

    DicomInstanceInfo(const std::string& id,
                      const MemoryBuffer& buffer);

    DicomInstanceInfo(const std::string& id,
                      size_t size,
                      const std::string& md5);

    explicit DicomInstanceInfo(const Json::Value& serialized);

    const std::string& GetId() const
    {
      return id_;
    }

    size_t GetSize() const
    {
      return size_;
    }

    const std::string& GetMD5() const
    {
      return md5_;
    }

    void Serialize(Json::Value& target) const;
  };
}
