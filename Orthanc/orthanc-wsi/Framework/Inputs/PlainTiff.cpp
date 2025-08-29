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


#include "PlainTiff.h"

#include "../ImageToolbox.h"
#include "../TiffReader.h"

#include <Images/Image.h>
#include <Images/ImageProcessing.h>
#include <Logging.h>
#include <OrthancException.h>

#include <cassert>
#include <string.h>


namespace OrthancWSI
{
  PlainTiff::PlainTiff(const std::string& path,
                       unsigned int tileWidth,
                       unsigned int tileHeight) :
    SingleLevelDecodedPyramid(tileWidth, tileHeight)
  {
    TiffReader reader(path);

    // Look for the largest sub-image
    bool first = true;
    unsigned int width = 0;
    unsigned int height = 0;
    tdir_t largest = 0;

    tdir_t pos = 0;

    do
    {
      uint32_t w, h, tw, th;

      if (TIFFSetDirectory(reader.GetTiff(), pos) &&
          !TIFFGetField(reader.GetTiff(), TIFFTAG_TILEWIDTH, &tw) &&   // Must not be a tiled image
          !TIFFGetField(reader.GetTiff(), TIFFTAG_TILELENGTH, &th) &&  // Must not be a tiled image
          TIFFGetField(reader.GetTiff(), TIFFTAG_IMAGEWIDTH, &w) &&
          TIFFGetField(reader.GetTiff(), TIFFTAG_IMAGELENGTH, &h) &&
          w > 0 &&
          h > 0)
      {
        if (first)
        {
          first = false;
          width = w;
          height = h;
          largest = pos;
        }
        else if (w > width &&
                 h > height)
        {
          width = w;
          height = h;
          largest = pos;
        }
      }

      pos++;
    }
    while (TIFFReadDirectory(reader.GetTiff()));

    if (first)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat, "This is an empty TIFF image");
    }

    // Back to the largest directory
    if (!TIFFSetDirectory(reader.GetTiff(), largest))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_CorruptedFile);
    }

    ImageCompression compression;
    Orthanc::PixelFormat pixelFormat;
    Orthanc::PhotometricInterpretation photometric;

    if (!reader.GetCurrentDirectoryInformation(compression, pixelFormat, photometric))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
    }

    if (pixelFormat != Orthanc::PixelFormat_RGB24)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
    }

    LOG(INFO) << "Size of the source plain TIFF image: " << width << "x" << height;

    decoded_.reset(new Orthanc::Image(pixelFormat, width, height, false));

    std::string strip;
    strip.resize(TIFFStripSize(reader.GetTiff()));

    const size_t stripPitch = width * Orthanc::GetBytesPerPixel(pixelFormat);

    if (strip.empty() ||
        stripPitch == 0 ||
        strip.size() < stripPitch ||
        strip.size() % stripPitch != 0)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
    }

    const size_t stripHeight = (strip.size() / stripPitch);
    const size_t stripCount = CeilingDivision(height, stripHeight);

    if (TIFFNumberOfStrips(reader.GetTiff()) != stripCount)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
    }

    for (unsigned int i = 0; i < stripCount; i++)
    {
      TIFFReadEncodedStrip(reader.GetTiff(), i, &strip[0], static_cast<tsize_t>(-1));

      const unsigned int y = i * stripHeight;

      const uint8_t* p = reinterpret_cast<const uint8_t*>(&strip[0]);
      uint8_t* q = reinterpret_cast<uint8_t*>(decoded_->GetRow(y));

      for (unsigned j = 0; j < stripHeight && y + j < height; j++)
      {
        memcpy(q, p, stripPitch);
        p += stripPitch;
        q += decoded_->GetPitch();
      }
    }

    if (photometric == Orthanc::PhotometricInterpretation_YBRFull422)
    {
      ImageToolbox::ConvertJpegYCbCrToRgb(*decoded_);
    }

    SetImage(*decoded_);
  }
}
