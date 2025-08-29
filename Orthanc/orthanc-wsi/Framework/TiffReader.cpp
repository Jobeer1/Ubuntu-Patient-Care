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


#include "TiffReader.h"

#include <Logging.h>
#include <OrthancException.h>

namespace OrthancWSI
{
  TiffReader::TiffReader(const std::string& path)
  {
    tiff_ = TIFFOpen(path.c_str(), "r");
    if (tiff_ == NULL)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_InexistentFile,
                                      "libtiff cannot open: " + path);
    }
  }


  TiffReader::~TiffReader()
  {
    if (tiff_)
    {
      TIFFClose(tiff_);
      tiff_ = NULL;
    }
  }


  bool TiffReader::GetCurrentDirectoryInformation(ImageCompression& compression,
                                                  Orthanc::PixelFormat& pixelFormat,
                                                  Orthanc::PhotometricInterpretation& photometric)
  {
    uint16_t c;
    if (!TIFFGetField(tiff_, TIFFTAG_COMPRESSION, &c))
    {
      return false;
    }

    switch (c)
    {
      case COMPRESSION_NONE:
        compression = ImageCompression_None;
        break;

      case COMPRESSION_JPEG:
        compression = ImageCompression_Jpeg;
        break;

      default:
        return false;
    }

    // http://www.awaresystems.be/imaging/tiff/tifftags/baseline.html

    uint16_t channels, photometricTiff, bpp, planar;
    if (!TIFFGetField(tiff_, TIFFTAG_SAMPLESPERPIXEL, &channels) ||
        channels == 0 ||
        !TIFFGetField(tiff_, TIFFTAG_PHOTOMETRIC, &photometricTiff) ||
        !TIFFGetField(tiff_, TIFFTAG_BITSPERSAMPLE, &bpp) ||
        !TIFFGetField(tiff_, TIFFTAG_PLANARCONFIG, &planar))
    {
      return false;
    }

    if (compression == ImageCompression_Jpeg &&
        channels == 3 &&     // This is a color image
        bpp == 8 &&
        planar == PLANARCONFIG_CONTIG)  // This is interleaved RGB
    {
      pixelFormat = Orthanc::PixelFormat_RGB24;

      switch (photometricTiff)
      {
        case PHOTOMETRIC_YCBCR:
          photometric = Orthanc::PhotometricInterpretation_YBRFull422;
          break;

        case PHOTOMETRIC_RGB:
          photometric = Orthanc::PhotometricInterpretation_RGB;
          break;

        default:
          LOG(ERROR) << "Unknown photometric interpretation in TIFF: " << photometricTiff;
          return false;
      }
    }
    else if (compression == ImageCompression_None &&
             channels == 3 &&     // This is a color image
             bpp == 8 &&
             planar == PLANARCONFIG_CONTIG)  // This is interleaved RGB
    {
      pixelFormat = Orthanc::PixelFormat_RGB24;
      photometric = Orthanc::PhotometricInterpretation_RGB;
    }
    else if (compression == ImageCompression_Jpeg &&
             channels == 1 &&     // This is a grayscale image
             bpp == 8)
    {
      pixelFormat = Orthanc::PixelFormat_Grayscale8;
      photometric = Orthanc::PhotometricInterpretation_Monochrome2;
    }
    else
    {
      return false;
    }

    return true;
  }
}
