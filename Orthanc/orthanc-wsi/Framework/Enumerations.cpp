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
#include "Enumerations.h"

#include "Jpeg2000Reader.h"

#include <Logging.h>
#include <OrthancException.h>
#include <SystemToolbox.h>
#include <Toolbox.h>

#include <string.h>
#include <boost/algorithm/string/predicate.hpp>

#define HEADER(s) (const void*) (s), sizeof(s)-1

namespace OrthancWSI
{
  const char* EnumerationToString(ImageCompression compression)
  {
    switch (compression)
    {
      case ImageCompression_Unknown:
        return "Unknown";

      case ImageCompression_None:
        return "Raw image";

      case ImageCompression_Png:
        return "PNG";

      case ImageCompression_Jpeg:
        return "JPEG";

      case ImageCompression_Jpeg2000:
        return "JPEG2000";

      case ImageCompression_Tiff:
        return "TIFF";

      case ImageCompression_Dicom:
        return "DICOM";

      case ImageCompression_JpegLS:
        return "JPEG-LS";

      default:
        throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
  }


  static bool MatchHeader(const void* actual,
                          size_t actualSize,
                          const void* expected,
                          size_t expectedSize)
  {
    if (actualSize < expectedSize)
    {
      return false;
    }
    else
    {
      return memcmp(actual, expected, expectedSize) == 0;
    }
  }


  ImageCompression DetectFormatFromFile(const std::string& path)
  {
    std::string lower;
    Orthanc::Toolbox::ToLowerCase(lower, path);

    std::string header;
    Orthanc::SystemToolbox::ReadHeader(header, path, 256);

    ImageCompression tmp = DetectFormatFromMemory(header.c_str(), header.size());
    if (tmp != ImageCompression_Unknown)
    {
      if (tmp == ImageCompression_Jpeg &&
          boost::algorithm::ends_with(lower, ".mrxs"))
      {
        /**
         * Special case of MIRAX / 3DHISTECH images, that contain a JPEG
         * thumbnail, and that are thus confused with JPEG.
         * https://bitbucket.org/sjodogne/orthanc/issues/163/
         **/
        
        LOG(WARNING) << "The file extension \".mrxs\" indicates a MIRAX / 3DHISTECH image, "
                     << "skipping auto-detection of the file format";
        return ImageCompression_Unknown;
      }
      else if (tmp == ImageCompression_Tiff &&
               boost::algorithm::ends_with(lower, ".ndpi"))
      {
        LOG(WARNING) << "The file extension \".ndpi\" indicates a Hamamatsu image, "
                     << "use the flag \"--force-openslide 1\" if you do not have enough RAM to store the entire image";
        return ImageCompression_Tiff;
      }
      else if (tmp == ImageCompression_Tiff &&
               boost::algorithm::ends_with(lower, ".scn"))
      {
        LOG(WARNING) << "The file extension \".scn\" indicates a Leica image, "
                     << "use the flag \"--reencode 1\" or \"--force-openslide 1\" if you encounter problems";
        return ImageCompression_Tiff;
      }
      else
      {
        return tmp;
      }
    }

    // Cannot detect the format using the header, fallback to the use
    // of the filename extension
    
    if (boost::algorithm::ends_with(lower, ".jpeg") ||
        boost::algorithm::ends_with(lower, ".jpg"))
    {
      return ImageCompression_Jpeg;
    }

    if (boost::algorithm::ends_with(lower, ".png"))
    {
      return ImageCompression_Png;
    }

    if (boost::algorithm::ends_with(lower, ".tiff") ||
        boost::algorithm::ends_with(lower, ".tif"))
    {
      return ImageCompression_Tiff;
    }

    if (boost::algorithm::ends_with(lower, ".jp2") ||
        boost::algorithm::ends_with(lower, ".j2k"))
    {
      return ImageCompression_Jpeg2000;
    }

    if (boost::algorithm::ends_with(lower, ".dcm"))
    {
      return ImageCompression_Dicom;
    }

    return ImageCompression_Unknown;
  }


  ImageCompression DetectFormatFromMemory(const void* buffer,
                                          size_t size) 
  {
    if (MatchHeader(buffer, size, HEADER("\377\330\377")))
    {
      return ImageCompression_Jpeg;
    }

    if (MatchHeader(buffer, size, HEADER("\xff\x4f\xff\x51")) ||
        MatchHeader(buffer, size, HEADER("\x00\x00\x00\x0c\x6a\x50\x20\x20\x0d\x0a\x87\x0a")))
    {
      return ImageCompression_Jpeg2000;
    }

    if (MatchHeader(buffer, size, HEADER("\211PNG\r\n\032\n")))
    {
      return ImageCompression_Png;
    }

    if (MatchHeader(buffer, size, HEADER("\115\115\000\052")) ||
        MatchHeader(buffer, size, HEADER("\111\111\052\000")) ||
        MatchHeader(buffer, size, HEADER("\115\115\000\053\000\010\000\000")) ||
        MatchHeader(buffer, size, HEADER("\111\111\053\000\010\000\000\000")))
    {
      return ImageCompression_Tiff;
    }

    if (size >= 128 + 4 &&
        MatchHeader(reinterpret_cast<const uint8_t*>(buffer) + 128, size - 128, HEADER("DICM")))
    {
      bool ok = true;
      for (size_t i = 0; ok && i < 128; i++)
      {
        if (reinterpret_cast<const uint8_t*>(buffer)[i] != 0)
        {
          ok = false;
        }
      }

      if (ok)
      {
        return ImageCompression_Dicom;
      }
    }        

    Jpeg2000Format jpeg2000 = Jpeg2000Reader::DetectFormatFromMemory(buffer, size);
    if (jpeg2000 == Jpeg2000Format_JP2 ||
        jpeg2000 == Jpeg2000Format_J2K)
    {
      return ImageCompression_Jpeg2000;
    }
    
    return ImageCompression_Unknown;
  }
}
