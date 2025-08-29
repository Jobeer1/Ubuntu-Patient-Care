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
#include "ImagedVolumeParameters.h"

#include <OrthancException.h>

namespace OrthancWSI
{
  ImagedVolumeParameters::ImagedVolumeParameters() :
    hasWidth_(false),
    hasHeight_(false),
    width_(0),
    height_(0),

    // Typical parameters for a specimen, in millimeters
    depth_(1),
    offsetX_(20),
    offsetY_(40)
  {
  }


  float ImagedVolumeParameters::GetWidth() const
  {
    if (hasWidth_)
    {
      return width_;
    }
    else
    {
      return 15;  // Typical width of a specimen
    }
  }


  float ImagedVolumeParameters::GetHeight() const
  {
    if (hasHeight_)
    {
      return height_;
    }
    else
    {
      return 15;  // Typical height of a specimen
    }
  }


  void ImagedVolumeParameters::SetWidth(float width)
  {
    if (width <= 0)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
    else
    {
      width_ = width;
      hasWidth_ = true;
    }
  }
    

  void ImagedVolumeParameters::SetHeight(float height)
  {
    if (height <= 0)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
    else
    {
      height_ = height;
      hasHeight_ = true;
    }
  }

    
  void ImagedVolumeParameters::SetDepth(float depth)
  {
    if (depth <= 0)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }

    depth_ = depth;
  }
    

  void ImagedVolumeParameters::GetLocation(float& physicalX,
                                           float& physicalY,
                                           unsigned int imageX,
                                           unsigned int imageY,
                                           unsigned int totalWidth,
                                           unsigned int totalHeight) const
  {
    if (imageX >= totalWidth ||
        imageY >= totalHeight)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }

    // WARNING: The physical X/Y axes are switched wrt. the image X/Y
    physicalX = offsetX_ - GetHeight() * static_cast<float>(imageX) / static_cast<float>(totalWidth);
    physicalY = offsetY_ - GetWidth() * static_cast<float>(imageY) / static_cast<float>(totalHeight);
  }
}
