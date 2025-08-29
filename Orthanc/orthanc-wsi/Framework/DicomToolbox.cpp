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


#include "PrecompiledHeadersWSI.h"
#include "DicomToolbox.h"

#include <Compatibility.h>  // For std::unique_ptr
#include <Logging.h>
#include <OrthancException.h>
#include <Toolbox.h>

#if ORTHANC_ENABLE_DCMTK == 1
#  include <dcmtk/dcmdata/dcelem.h>
#  include <dcmtk/dcmdata/dcitem.h>
#  include <dcmtk/dcmdata/dcsequen.h>
#  include <dcmtk/dcmdata/dcvrat.h>
#endif

namespace OrthancWSI
{
  namespace DicomToolbox
  {
#if ORTHANC_ENABLE_DCMTK == 1
    void SetStringTag(DcmItem& dataset,
                      const DcmTagKey& key,
                      const std::string& value)
    {
      if (!dataset.tagExists(key) &&
          !dataset.putAndInsertString(key, value.c_str()).good())
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
      }
    }

    void SetUint16Tag(DcmItem& dataset,
                      const DcmTagKey& key,
                      uint16_t value)
    {
      if (!dataset.tagExists(key) &&
          !dataset.putAndInsertUint16(key, value).good())
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
      }
    }


    void SetUint32Tag(DcmItem& dataset,
                      const DcmTagKey& key,
                      uint32_t value)
    {
      if (!dataset.tagExists(key) &&
          !dataset.putAndInsertUint32(key, value).good())
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
      }
    }


    void SetAttributeTag(DcmItem& dataset,
                         const DcmTagKey& key,
                         const DcmTagKey& value)
    {
      if (!dataset.tagExists(key))
      {
        std::unique_ptr<DcmAttributeTag> tag(new DcmAttributeTag(key));
        
        if (!tag->putTagVal(value).good() ||
            !dataset.insert(tag.release()).good())
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
        }
      }
    }


    DcmItem* ExtractSingleSequenceItem(DcmItem& dataset,
                                       const DcmTagKey& key)
    {
      DcmElement* element = NULL;
      if (!dataset.findAndGetElement(key, element).good() ||
          element == NULL)
      {
        return NULL;
      }

      if (element->getVR() != EVR_SQ)
      {
        DcmTag tag(key);
        LOG(ERROR) << "The following element in the DICOM dataset is not a sequence as expected: " << tag.getTagName();
        throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
      }

      DcmSequenceOfItems& sequence = dynamic_cast<DcmSequenceOfItems&>(*element);
      if (sequence.card() != 1)
      {
        LOG(ERROR) << "Bad number of elements in the sequence (it must contain exactly 1 element)";
        throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
      }

      return sequence.getItem(0);
    }


    uint16_t GetUint16Tag(DcmItem& dataset,
                          const DcmTagKey& key)
    {
      uint16_t value;
      if (dataset.findAndGetUint16(key, value).good())
      {
        return value;
      }
      else
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InexistentTag);
      }
    }


    uint32_t GetUint32Tag(DcmItem& dataset,
                          const DcmTagKey& key)
    {
      Uint32 value;
      if (dataset.findAndGetUint32(key, value).good())
      {
        return value;
      }
      else
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InexistentTag);
      }
    }


    int32_t GetInt32Tag(DcmItem& dataset,
                        const DcmTagKey& key)
    {
      Sint32 value;
      if (dataset.findAndGetSint32(key, value).good())
      {
        return value;
      }
      else
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InexistentTag);
      }
    }


    std::string GetStringTag(DcmItem& dataset,
                             const DcmTagKey& key)
    {
      const char* value = NULL;
      if (dataset.findAndGetString(key, value).good() &&
          value != NULL)
      {
        return Orthanc::Toolbox::StripSpaces(value);
      }
      else
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InexistentTag);
      }
    }
#endif
  }
}
