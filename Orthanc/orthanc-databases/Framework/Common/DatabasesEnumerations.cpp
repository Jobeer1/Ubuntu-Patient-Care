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


#include "DatabasesEnumerations.h"

#include <OrthancException.h>

namespace OrthancDatabases
{
  const char* EnumerationToString(ValueType type)
  {
    switch (type)
    {
      case ValueType_BinaryString:
        return "BinaryString";
        
      case ValueType_InputFile:
        return "InputFile";
        
      case ValueType_Integer64:
        return "Integer64";
        
      case ValueType_Null:
        return "Null";
        
      case ValueType_ResultFile:
        return "ResultFile";
        
      case ValueType_Utf8String:
        return "Utf8String";

      default:
        throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
  }   
}
