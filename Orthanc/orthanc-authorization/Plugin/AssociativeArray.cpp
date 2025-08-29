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

#include "AssociativeArray.h"

#include <Toolbox.h>

namespace OrthancPlugins
{
  AssociativeArray::AssociativeArray(uint32_t headersCount,
                                     const char *const *headersKeys,
                                     const char *const *headersValues,
                                     bool caseSensitiveKeys) :
    caseSensitiveKeys_(caseSensitiveKeys)
  {
    for (uint32_t i = 0; i < headersCount; i++)
    {
      std::string key = headersKeys[i];

      if (!caseSensitiveKeys)
      {
        Orthanc::Toolbox::ToLowerCase(key, headersKeys[i]);
      }
        
      map_[headersKeys[i]] = headersValues[i];
    }
  }

    
  bool AssociativeArray::GetValue(std::string& value,
                                  const std::string& key) const
  {
    if (key.empty())
    {
      return false;
    }

    Map::const_iterator found;

    if (caseSensitiveKeys_)
    {
      found = map_.find(key);
    }
    else
    {
      std::string lower;
      Orthanc::Toolbox::ToLowerCase(lower, key);
      found = map_.find(lower);
    }       

    if (found == map_.end())
    {
      return false;
    }
    else
    {
      value = found->second;
      return true;
    }
  }
}
