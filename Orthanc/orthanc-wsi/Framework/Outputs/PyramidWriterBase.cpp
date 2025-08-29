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
#include "PyramidWriterBase.h"

#include "../ImageToolbox.h"
#include <OrthancException.h>
#include <Logging.h>

namespace OrthancWSI
{
  PyramidWriterBase::Level PyramidWriterBase::GetLevel(unsigned int level) const
  {
    boost::mutex::scoped_lock lock(const_cast<PyramidWriterBase&>(*this).mutex_);

    if (level >= levels_.size())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
    else
    {
      return levels_[level];
    }
  }


  PyramidWriterBase::PyramidWriterBase(Orthanc::PixelFormat pixelFormat,
                                       ImageCompression compression,
                                       unsigned int tileWidth,
                                       unsigned int tileHeight) :
    pixelFormat_(pixelFormat),
    compression_(compression),
    tileWidth_(tileWidth),
    tileHeight_(tileHeight),
    jpegQuality_(90),   // Default JPEG quality
    first_(true)
  {
  }


  void PyramidWriterBase::SetJpegQuality(int quality)
  {
    if (quality <= 0 || quality > 100)
    {
      LOG(ERROR) << "The JPEG quality must be in range [1;100], but " << quality << " is provided";
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }

    jpegQuality_ = quality;
  }


  void PyramidWriterBase::AddLevel(unsigned int width,
                                   unsigned int height)
  {
    boost::mutex::scoped_lock lock(mutex_);
      
    if (!first_)
    {
      LOG(ERROR) << "Cannot add pyramid levels after some tile has already been written";
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
    }

    if (!levels_.empty())
    {
      const Level& previous = levels_[levels_.size() - 1];

      if (width >= previous.width_ ||
          height >= previous.height_ ||
          width == 0 ||
          height == 0)
      {
        LOG(ERROR) << "Levels must have strictly decreasing sizes";
        throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
      }
    }

    Level level;
    level.z_ = levels_.size();
    level.width_ = width;
    level.height_ = height;
    level.countTilesX_ = CeilingDivision(width, tileWidth_);
    level.countTilesY_ = CeilingDivision(height, tileHeight_);
    levels_.push_back(level);

    AddLevelInternal(level);
  }


  unsigned int PyramidWriterBase::GetLevelCount() const
  {
    boost::mutex::scoped_lock lock(const_cast<PyramidWriterBase&>(*this).mutex_);
    return levels_.size();
  }


  void PyramidWriterBase::WriteRawTile(const std::string& tile,
                                       ImageCompression compression,
                                       unsigned int z,
                                       unsigned int x,
                                       unsigned int y)
  {
    first_ = false;

    const Level level = GetLevel(z);

    if (compression != compression_)
    {
      std::string recoded;
      ImageToolbox::ChangeTileCompression(recoded, tile, compression, compression_, jpegQuality_);
      WriteRawTileInternal(recoded, level, x, y);
    }
    else
    {
      WriteRawTileInternal(tile, level, x, y);
    }
  }


  void PyramidWriterBase::EncodeTile(const Orthanc::ImageAccessor& tile,
                                     unsigned int z,
                                     unsigned int x, 
                                     unsigned int y)
  {
    first_ = false;

    const Level level = GetLevel(z);

    std::string raw;
    EncodeTileInternal(raw, tile);

    WriteRawTileInternal(raw, level, x, y);
  }
}
