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


#pragma once

#if !defined(ORTHANC_ENABLE_DCMTK)
#  error The macro ORTHANC_ENABLE_DCMTK must be defined
#endif

#if ORTHANC_ENABLE_DCMTK == 1
#  include <DicomParsing/ParsedDicomFile.h>
#endif

#include <string>

namespace OrthancStone
{
  namespace StoneToolbox
  {
    std::string JoinUrl(const std::string& base,
                        const std::string& path);

#if ORTHANC_ENABLE_DCMTK == 1
    void CopyDicomTag(Orthanc::DicomMap& target,
                      const Orthanc::ParsedDicomFile& source,
                      const Orthanc::DicomTag& tag);
#endif

#if ORTHANC_ENABLE_DCMTK == 1
    void ExtractMainDicomTags(Orthanc::DicomMap& target,
                              const Orthanc::ParsedDicomFile& source);
#endif
  }
}
