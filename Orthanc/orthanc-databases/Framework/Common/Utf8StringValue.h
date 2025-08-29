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
  // Represents an UTF-8 string
  class Utf8StringValue : public IValue
  {
  private:
    std::string  utf8_;
    bool isNull_;

  public:
    explicit Utf8StringValue(const std::string& utf8) :
      utf8_(utf8),
      isNull_(false)
    {
    }

    explicit Utf8StringValue() :
      isNull_(true)
    {
    }

    virtual bool IsNull() const ORTHANC_OVERRIDE
    {
      return isNull_;
    }
    
    const std::string& GetContent() const
    {
      return utf8_;
    }

    virtual ValueType GetType() const ORTHANC_OVERRIDE
    {
      return ValueType_Utf8String;
    }
    
    virtual IValue* Convert(ValueType target) const ORTHANC_OVERRIDE;
  };
}
