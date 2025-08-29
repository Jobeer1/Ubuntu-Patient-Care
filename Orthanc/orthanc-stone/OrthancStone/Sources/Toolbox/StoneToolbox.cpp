/**
 * Stone of Orthanc
 * Copyright (C) 2012-2016 Sebastien Jodogne, Medical Physics
 * Department, University Hospital of Liege, Belgium
 * Copyright (C) 2017-2023 Osimis S.A., Belgium
 * Copyright (C) 2021-2025 Sebastien Jodogne, ICTEAM UCLouvain, Belgium
 *
 * This program is free software: you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public License
 * as published by the Free Software Foundation, either version 3 of
 * the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this program. If not, see
 * <http://www.gnu.org/licenses/>.
 **/


#include "StoneToolbox.h"

namespace OrthancStone
{
  namespace StoneToolbox
  {
    std::string JoinUrl(const std::string& base,
                        const std::string& path)
    {
      size_t end = base.size();
      while (end > 0 &&
             base[end - 1] == '/')
      {
        end--;
      }

      size_t start = 0;
      while (start < path.size() &&
             path[start] == '/')
      {
        start++;
      }

      return base.substr(0, end) + "/" + path.substr(start);
    }


#if ORTHANC_ENABLE_DCMTK == 1
    void CopyDicomTag(Orthanc::DicomMap& target,
                      const Orthanc::ParsedDicomFile& source,
                      const Orthanc::DicomTag& tag)
    {
      std::string s;
      if (source.GetTagValue(s, tag))
      {
        target.SetValue(tag, s, false);
      }
    }
#endif


#if ORTHANC_ENABLE_DCMTK == 1
    void ExtractMainDicomTags(Orthanc::DicomMap& target,
                              const Orthanc::ParsedDicomFile& source)
    {
      target.Clear();

      std::set<Orthanc::DicomTag> tags;
      Orthanc::DicomMap::GetAllMainDicomTags(tags);

      for (std::set<Orthanc::DicomTag>::const_iterator it = tags.begin(); it != tags.end(); ++it)
      {
        CopyDicomTag(target, source, *it);
      }
    }
#endif
  }
}
