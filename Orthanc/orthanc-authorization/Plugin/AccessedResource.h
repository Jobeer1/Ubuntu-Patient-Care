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

#pragma once

#include "Enumerations.h"
#include <set>

namespace OrthancPlugins
{
  class AccessedResource
  {
  private:
    AccessLevel    level_;
    std::string    orthancId_;
    std::string    dicomUid_;
    std::set<std::string> labels_;

  public:
    AccessedResource(AccessLevel level,
                     const std::string& orthancId,
                     const std::string& dicomUid,
                     const std::set<std::string>& labels
                     );

    AccessedResource(Orthanc::ResourceType level,
                     const std::string& orthancId,
                     const std::string& dicomUid,
                     const std::set<std::string>& labels);

    AccessLevel GetLevel() const
    {
      return level_;
    }

    const std::string& GetOrthancId() const
    {
      return orthancId_;
    }

    const std::string& GetDicomUid() const;

    const std::set<std::string>& GetLabels() const;
  };
}
