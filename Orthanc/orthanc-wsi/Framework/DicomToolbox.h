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

#if ORTHANC_ENABLE_DCMTK == 1
#  include <dcmtk/dcmdata/dcdeftag.h>
#  include <dcmtk/dcmdata/dcitem.h>
#  include <dcmtk/dcmdata/dctagkey.h>
#endif

#include <string>
#include <stdint.h>
#include <json/value.h>

namespace OrthancWSI
{
  namespace DicomToolbox
  {
#if ORTHANC_ENABLE_DCMTK == 1
    void SetStringTag(DcmItem& dataset,
                      const DcmTagKey& key,
                      const std::string& value);

    void SetUint16Tag(DcmItem& dataset,
                      const DcmTagKey& key,
                      uint16_t value);

    void SetUint32Tag(DcmItem& dataset,
                      const DcmTagKey& key,
                      uint32_t value);

    void SetAttributeTag(DcmItem& dataset,
                         const DcmTagKey& key,
                         const DcmTagKey& value);

    DcmItem* ExtractSingleSequenceItem(DcmItem& dataset,
                                       const DcmTagKey& key);

    uint16_t GetUint16Tag(DcmItem& dataset,
                          const DcmTagKey& key);

    uint32_t GetUint32Tag(DcmItem& dataset,
                          const DcmTagKey& key);

    int32_t GetInt32Tag(DcmItem& dataset,
                        const DcmTagKey& key);

    std::string GetStringTag(DcmItem& dataset,
                             const DcmTagKey& key);
#endif
  }
}
