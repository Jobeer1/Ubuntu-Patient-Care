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

#include "IValue.h"

#include <Compatibility.h>

namespace OrthancDatabases
{
  class BinaryStringValue : public IValue
  {
  private:
    std::string  content_;
    bool isNull_;

  public:
    BinaryStringValue() :
      isNull_(true)
    {
    }

    explicit BinaryStringValue(const std::string& content) :
      content_(content),
      isNull_(false)
    {
    }

    BinaryStringValue(const void* data,
                      size_t size);

    const std::string& GetContent() const
    {
      return content_;
    }

    const void* GetBuffer() const
    {
      return (content_.empty() ? NULL : content_.c_str());
    }

    size_t GetSize() const
    {
      return content_.size();
    }

    void Swap(std::string& other)
    {
      content_.swap(other);
    }

    virtual ValueType GetType() const ORTHANC_OVERRIDE
    {
      return ValueType_BinaryString;
    }
    
    virtual IValue* Convert(ValueType target) const ORTHANC_OVERRIDE;

    virtual bool IsNull() const ORTHANC_OVERRIDE
    {
      return isNull_;
    }
  };
}
