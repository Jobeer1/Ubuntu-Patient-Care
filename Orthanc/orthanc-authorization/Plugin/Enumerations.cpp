/**
 * Advanced authorization plugin for Orthanc
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


#include "Enumerations.h"

#include <OrthancException.h>
#include <Toolbox.h>

namespace OrthancPlugins
{
  std::string EnumerationToString(AccessLevel level)
  {
    switch (level)
    {
      case AccessLevel_Patient:
        return "patient";
        
      case AccessLevel_Study:
        return "study";
        
      case AccessLevel_Series:
        return "series";
        
      case AccessLevel_Instance:
        return "instance";
        
      case AccessLevel_System:
        return "system";
        
      default:
        throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
  }


  AccessLevel StringToAccessLevel(const std::string& level)
  {
    std::string tmp;
    Orthanc::Toolbox::ToLowerCase(tmp, level);

    if (tmp == "patient" ||
        tmp == "patients")
    {
      return AccessLevel_Patient;
    }
    else if (tmp == "study" ||
             tmp == "studies")
    {
      return AccessLevel_Study;
    }
    else if (tmp == "series")
    {
      return AccessLevel_Series;
    }
    else if (tmp == "instance" ||
             tmp == "instances")
    {
      return AccessLevel_Instance;
    }
    else if (tmp == "system")
    {
      return AccessLevel_System;
    }
    else
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange, std::string("Invalid access level: ") + tmp);
    }
  }

  OrthancPluginResourceType StringToResourceType(const char* type)
  {
    std::string s(type);
    Orthanc::Toolbox::ToUpperCase(s);

    if (s == "PATIENT" || s == "PATIENTS")
    {
      return OrthancPluginResourceType_Patient;
    }
    else if (s == "STUDY" || s == "STUDIES")
    {
      return OrthancPluginResourceType_Study;
    }
    else if (s == "SERIES")
    {
      return OrthancPluginResourceType_Series;
    }
    else if (s == "INSTANCE"  || s == "IMAGE" || 
             s == "INSTANCES" || s == "IMAGES")
    {
      return OrthancPluginResourceType_Instance;
    }

    throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange, std::string("Invalid resource type '") + type + "'");
  }

}
