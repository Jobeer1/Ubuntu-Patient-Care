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


#include "../PrecompiledHeadersWSI.h"
#include "OpenSlidePyramid.h"

#include <Compatibility.h>  // For std::unique_ptr
#include <Images/ImageProcessing.h>
#include <OrthancException.h>
#include <SerializationToolbox.h>
#include <Logging.h>

#include <boost/math/special_functions/round.hpp>
#include <memory>

namespace OrthancWSI
{
  // Test whether the full alpha channel (if any) equals 255
  static bool IsFullyTransparent(const Orthanc::ImageAccessor& source)
  {
    if (source.GetFormat() == Orthanc::PixelFormat_BGRA32 ||
        source.GetFormat() == Orthanc::PixelFormat_RGBA32)
    {
      const unsigned int width = source.GetWidth();
      const unsigned int height = source.GetHeight();

      bool isEmpty = true;

      for (unsigned int yy = 0; yy < height && isEmpty; yy++)
      {
        const uint8_t* p = reinterpret_cast<const uint8_t*>(source.GetConstRow(yy));
        for (unsigned int xx = 0; xx < width && isEmpty; xx++)
        {
          if (p[3] != 0)
          {
            isEmpty = false;
          }

          p += 4;
        }
      }

      return isEmpty;
    }
    else
    {
      return false;
    }
  }


  void OpenSlidePyramid::ReadRegion(Orthanc::ImageAccessor& target,
                                    bool& isEmpty,
                                    unsigned int level,
                                    unsigned int x,
                                    unsigned int y)
  {
    std::unique_ptr<Orthanc::ImageAccessor> source(image_.ReadRegion(level, x, y, target.GetWidth(), target.GetHeight()));

    if (target.GetWidth() != source->GetWidth() ||
        target.GetHeight() != source->GetHeight())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_IncompatibleImageSize);
    }

    isEmpty = IsFullyTransparent(*source);

    const unsigned int width = source->GetWidth();
    const unsigned int height = source->GetHeight();

    if (target.GetFormat() == Orthanc::PixelFormat_RGB24 &&
        source->GetFormat() == Orthanc::PixelFormat_BGRA32)
    {
      // Implements alpha blending: https://en.wikipedia.org/wiki/Alpha_compositing#Alpha_blending

      uint8_t backgroundRed, backgroundGreen, backgroundBlue;
      GetBackgroundColor(backgroundRed, backgroundGreen, backgroundBlue);

      for (unsigned int yy = 0; yy < height; yy++)
      {
        const uint8_t* p = reinterpret_cast<const uint8_t*>(source->GetConstRow(yy));
        uint8_t* q = reinterpret_cast<uint8_t*>(target.GetRow(yy));
        for (unsigned int xx = 0; xx < width; xx++)
        {
          /**
             Alpha blending using integer arithmetics only (16 bits avoids overflows)

             p = (1 - alpha) * background + alpha * value
             <=> p = (1 - p[3] / 255) * background + p[3] / 255 * value
             <=> p = ((255 - p[3]) * background + p[3] * value) / 255

           **/

          uint16_t alpha = p[3];
          q[0] = static_cast<uint8_t>(((255 - alpha) * backgroundRed + alpha * p[2]) / 255);
          q[1] = static_cast<uint8_t>(((255 - alpha) * backgroundGreen + alpha * p[1]) / 255);
          q[2] = static_cast<uint8_t>(((255 - alpha) * backgroundBlue + alpha * p[0]) / 255);

          p += 4;
          q += 3;
        }
      }
    }
    else
    {
      Orthanc::ImageProcessing::Convert(target, *source);
    }
  }


  OpenSlidePyramid::OpenSlidePyramid(const std::string& path,
                                     unsigned int tileWidth,
                                     unsigned int tileHeight) :
    image_(path),
    tileWidth_(tileWidth),
    tileHeight_(tileHeight)
  {
  }


  bool OpenSlidePyramid::LookupImagedVolumeSize(float& width,
                                                float& height) const
  {
    std::string s;
    double mppx;
    double mppy;

    if (image_.LookupProperty(s, "openslide.mpp-x") &&
        Orthanc::SerializationToolbox::ParseDouble(mppx, s) &&
        image_.LookupProperty(s, "openslide.mpp-y") &&
        Orthanc::SerializationToolbox::ParseDouble(mppy, s))
    {
      // In the 2 lines below, remember to switch X/Y when going from physical to pixel coordinates!
      width = mppy / 1000.0 * static_cast<double>(image_.GetLevelHeight(0));
      height = mppx / 1000.0 * static_cast<double>(image_.GetLevelWidth(0));
      return true;
    }
    else
    {
      return false;
    }
  }


  size_t OpenSlidePyramid::GetMemoryUsage() const
  {
    size_t countPixels = 0;

    for (unsigned int i = 0; i < image_.GetLevelCount(); i++)
    {
      countPixels += image_.GetLevelWidth(i) * image_.GetLevelHeight(i);
    }

    return countPixels * Orthanc::GetBytesPerPixel(Orthanc::PixelFormat_RGBA32);
  }
}
