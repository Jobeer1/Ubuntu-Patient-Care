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


#include "GenericFormatter.h"

#include <OrthancException.h>

#include <boost/lexical_cast.hpp>

namespace OrthancDatabases
{
  Dialect GenericFormatter::GetDialect() const
  {
    if (autoincrementDialect_ != namedDialect_)
    {
      // The two dialects do not match because of a previous call to
      // SetAutoincrementDialect() or SetNamedDialect()
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
    }
    else
    {
      return namedDialect_;
    }
  }
  

  void GenericFormatter::Format(std::string& target,
                                const std::string& source,
                                ValueType type)
  {
    if (source.empty())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
    else if (source == "AUTOINCREMENT")
    {
      if (GetParametersCount() != 0)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls,
                                        "The AUTOINCREMENT argument must always be the first");
      }
      
      switch (autoincrementDialect_)
      {
        case Dialect_PostgreSQL:
          target = "DEFAULT, ";
          break;

        case Dialect_MySQL:
        case Dialect_SQLite:
          target = "NULL, ";
          break;

        case Dialect_MSSQL:
          target.clear();  // The IDENTITY field must not be filled in MSSQL
          break;

        default:
          throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
      }
    }
    else
    {
      switch (namedDialect_)
      {
        case Dialect_PostgreSQL:
          target = "$" + boost::lexical_cast<std::string>(parametersName_.size() + 1);
          break;

        case Dialect_MySQL:
        case Dialect_SQLite:
        case Dialect_MSSQL:
          target = "?";
          break;

        default:
          throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
      }

      parametersName_.push_back(source);
      parametersType_.push_back(type);
    }
  }


  const std::string& GenericFormatter::GetParameterName(size_t index) const
  {
    if (index >= parametersName_.size())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
    else
    {
      return parametersName_[index];
    }
  }

    
  ValueType GenericFormatter::GetParameterType(size_t index) const
  {
    if (index >= parametersType_.size())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
    else
    {
      return parametersType_[index];
    }
  }
}
