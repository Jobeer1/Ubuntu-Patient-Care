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

#include <stdint.h>

namespace OrthancDatabases
{
  /**
   * This class is not used for MySQL, as MySQL uses BLOB columns to
   * store files.
   **/
  class ResultFileValue : public IValue
  {
  public:
    virtual void ReadWhole(std::string& target) const = 0;
    
    virtual void ReadRange(std::string& target,
                           uint64_t start,
                           size_t length) const = 0;
    
    virtual ValueType GetType() const ORTHANC_OVERRIDE
    {
      return ValueType_ResultFile;
    }
    
    virtual IValue* Convert(ValueType target) const ORTHANC_OVERRIDE;
  };
}
