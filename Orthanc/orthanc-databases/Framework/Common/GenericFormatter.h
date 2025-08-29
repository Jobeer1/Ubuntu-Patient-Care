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

#include "Query.h"

#include <Compatibility.h>

#include <set>

namespace OrthancDatabases
{
  class GenericFormatter : public Query::IParameterFormatter
  {
  private:
    Dialect                   autoincrementDialect_;
    Dialect                   namedDialect_;
    std::vector<std::string>  parametersName_;
    std::vector<ValueType>    parametersType_;
      
  public:
    explicit GenericFormatter(Dialect dialect) :
      autoincrementDialect_(dialect),
      namedDialect_(dialect)
    {
    }

    Dialect GetDialect() const;

    Dialect GetAutoincrementDialect() const
    {
      return autoincrementDialect_;
    }

    void SetAutoincrementDialect(Dialect dialect)
    {
      autoincrementDialect_ = dialect;
    }
    
    Dialect GetNamedDialect() const
    {
      return namedDialect_;
    }

    void SetNamedDialect(Dialect dialect)
    {
      namedDialect_ = dialect;
    }
    
    virtual void Format(std::string& target,
                        const std::string& source,
                        ValueType type) ORTHANC_OVERRIDE;

    size_t GetParametersCount() const
    {
      return parametersName_.size();
    }

    const std::string& GetParameterName(size_t index) const;

    ValueType GetParameterType(size_t index) const;
  };
}
