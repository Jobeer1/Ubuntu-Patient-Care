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
#include "SingleLevelDecodedPyramid.h"
#include "../ImageToolbox.h"

#include <OrthancException.h>
#include <Images/ImageProcessing.h>

namespace OrthancWSI
{
  void SingleLevelDecodedPyramid::ReadRegion(Orthanc::ImageAccessor& target,
                                             bool& isEmpty,
                                             unsigned int level,
                                             unsigned int x,
                                             unsigned int y)
  {
    isEmpty = false;

    if (x + target.GetWidth() <= image_.GetWidth() &&
        y + target.GetHeight() <= image_.GetHeight())
    {
      Orthanc::ImageAccessor region;
      image_.GetRegion(region, x, y, target.GetWidth(), target.GetHeight());
      Orthanc::ImageProcessing::Copy(target, region);
    }
    else
    {
      Orthanc::ImageProcessing::Set(target, backgroundRed_, backgroundGreen_, backgroundBlue_, 255);

      if (x < image_.GetWidth() &&
          y < image_.GetHeight())
      {
        unsigned int w = std::min(image_.GetWidth() - x, target.GetWidth());
        unsigned int h = std::min(image_.GetHeight() - y, target.GetHeight());

        Orthanc::ImageAccessor a, b;
        image_.GetRegion(a, x, y, w, h);
        target.GetRegion(b, 0, 0, w, h);

        Orthanc::ImageProcessing::Copy(b, a);
      }
    }
  }


  SingleLevelDecodedPyramid::SingleLevelDecodedPyramid(unsigned int tileWidth,
                                                       unsigned int tileHeight) :
    tileWidth_(tileWidth),
    tileHeight_(tileHeight),
    padding_(0),
    backgroundRed_(255),
    backgroundGreen_(255),
    backgroundBlue_(255)
  {
  }


  unsigned int SingleLevelDecodedPyramid::GetLevelWidth(unsigned int level) const
  {
    if (level != 0)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }

    if (padding_ <= 1)
    {
      return image_.GetWidth();  // No padding
    }
    else
    {
      return padding_ * CeilingDivision(image_.GetWidth(), padding_);
    }
  }


  unsigned int SingleLevelDecodedPyramid::GetLevelHeight(unsigned int level) const
  {
    if (level != 0)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }

    if (padding_ <= 1)
    {
      return image_.GetHeight();  // No padding
    }
    else
    {
      return padding_ * CeilingDivision(image_.GetHeight(), padding_);
    }
  }
  

  Orthanc::PhotometricInterpretation SingleLevelDecodedPyramid::GetPhotometricInterpretation() const
  {
    switch (image_.GetFormat())
    {
      case Orthanc::PixelFormat_Grayscale8:
        return Orthanc::PhotometricInterpretation_Monochrome2;

      case Orthanc::PixelFormat_RGB24:
        return Orthanc::PhotometricInterpretation_RGB;

      default:
        throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
    }
  }


  void SingleLevelDecodedPyramid::SetPadding(unsigned int padding,
                                             uint8_t backgroundRed,
                                             uint8_t backgroundGreen,
                                             uint8_t backgroundBlue)
  {
    padding_ = padding;
    backgroundRed_ = backgroundRed;
    backgroundGreen_ = backgroundGreen;
    backgroundBlue_ = backgroundBlue;
  }
}
