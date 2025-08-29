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
#include "PyramidReader.h"

#include "../ImageToolbox.h"

#include <Compatibility.h>  // For std::unique_ptr
#include <Logging.h>
#include <OrthancException.h>

#include <cassert>

namespace OrthancWSI
{
  class PyramidReader::SourceTile : public boost::noncopyable
  {
  private: 
    PyramidReader&    that_;
    unsigned int      tileX_;
    unsigned int      tileY_;
    bool              hasRawTile_;
    std::string       rawTile_;
    ImageCompression  rawTileCompression_;
    bool              isEmpty_;

    std::unique_ptr<Orthanc::ImageAccessor>  decoded_;

    bool IsRepaintNeeded() const
    {
      return (that_.parameters_.IsRepaintBackground() &&
              ((tileX_ + 1) * that_.sourceTileWidth_ > that_.levelWidth_ ||
               (tileY_ + 1) * that_.sourceTileHeight_ > that_.levelHeight_));
    }

    void RepaintBackground()
    {
      assert(decoded_.get() != NULL);
      LOG(INFO) << "Repainting background of tile ("
                << tileX_ << "," << tileY_ << ") at level " << that_.level_;

      if ((tileY_ + 1) * that_.sourceTileHeight_ > that_.levelHeight_)
      {
        // Bottom overflow
        assert(tileY_ * that_.sourceTileHeight_ < that_.levelHeight_);

        unsigned int bottom = that_.levelHeight_ - tileY_ * that_.sourceTileHeight_;
        Orthanc::ImageAccessor a;
        decoded_->GetRegion(a, 0, bottom,
                            that_.sourceTileWidth_, 
                            that_.sourceTileHeight_ - bottom);
        ImageToolbox::Set(a, 
                          that_.parameters_.GetBackgroundColorRed(),
                          that_.parameters_.GetBackgroundColorGreen(),
                          that_.parameters_.GetBackgroundColorBlue());

      }

      if ((tileX_ + 1) * that_.sourceTileWidth_ > that_.levelWidth_)
      {
        // Right overflow
        assert(tileX_ * that_.sourceTileWidth_ < that_.levelWidth_);

        unsigned int right = that_.levelWidth_ - tileX_ * that_.sourceTileWidth_;
        Orthanc::ImageAccessor a;
        decoded_->GetRegion(a, right, 0, 
                            that_.sourceTileWidth_ - right, 
                            that_.sourceTileHeight_);
        ImageToolbox::Set(a,
                          that_.parameters_.GetBackgroundColorRed(),
                          that_.parameters_.GetBackgroundColorGreen(),
                          that_.parameters_.GetBackgroundColorBlue());
      }
    }


  public:
    SourceTile(PyramidReader& that,
               unsigned int tileX,
               unsigned int tileY) :
      that_(that),
      tileX_(tileX),
      tileY_(tileY)
    {
      if (!that_.parameters_.IsForceReencode() &&
          !IsRepaintNeeded() &&
          that_.source_.ReadRawTile(rawTile_, rawTileCompression_, that_.level_, tileX, tileY))
      {
        hasRawTile_ = true;
        isEmpty_ = false;
      }
      else
      {
        hasRawTile_ = false;

        decoded_.reset(that_.source_.DecodeTile(isEmpty_, that_.level_, tileX, tileY));
        if (decoded_.get() == NULL)
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
        }

        RepaintBackground();
      }
    }

    bool HasRawTile(ImageCompression& compression) const
    {
      if (hasRawTile_)
      {
        compression = rawTileCompression_;
        return true;
      }
      else
      {
        return false;
      }
    }

    const std::string& GetRawTile() const
    {
      if (hasRawTile_)
      {
        return rawTile_;
      }
      else
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
      }
    }

    const Orthanc::ImageAccessor& GetDecodedTile()
    {
      if (decoded_.get() == NULL)
      {
        if (!hasRawTile_)
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
        }

        decoded_.reset(ImageToolbox::DecodeTile(rawTile_, rawTileCompression_));
        if (decoded_.get() == NULL)
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
        }
          
        RepaintBackground();
      }

      return *decoded_;
    }

    bool IsEmpty() const
    {
      return isEmpty_;
    }
  };


  Orthanc::ImageAccessor& PyramidReader::GetOutsideTile()
  {
    if (outside_.get() == NULL)
    {
      outside_.reset(ImageToolbox::Allocate(source_.GetPixelFormat(), targetTileWidth_, targetTileHeight_));
      ImageToolbox::Set(*outside_,
                        parameters_.GetBackgroundColorRed(),
                        parameters_.GetBackgroundColorGreen(),
                        parameters_.GetBackgroundColorBlue());
    }

    return *outside_;
  }


  void PyramidReader::CheckTileSize(const Orthanc::ImageAccessor& tile) const
  {
    if (tile.GetWidth() != sourceTileWidth_ ||
        tile.GetHeight() != sourceTileHeight_)
    {
      LOG(ERROR) << "One tile in the input image has size " << tile.GetWidth() << "x" << tile.GetHeight() 
                 << " instead of required " << sourceTileWidth_ << "x" << sourceTileHeight_;
      throw Orthanc::OrthancException(Orthanc::ErrorCode_IncompatibleImageSize);
    }
  }


  void PyramidReader::CheckTileSize(const std::string& tile,
                                    ImageCompression compression) const
  {
    if (parameters_.IsSafetyCheck())
    {
      std::unique_ptr<Orthanc::ImageAccessor> decoded(ImageToolbox::DecodeTile(tile, compression));
      CheckTileSize(*decoded);
    }
  }


  PyramidReader::SourceTile& PyramidReader::AccessSourceTile(const Location& location)
  {
    Cache::iterator found = cache_.find(location);
    if (found != cache_.end())
    {
      return *found->second;
    }
    else
    {
      SourceTile *tile = new SourceTile(*this, location.first, location.second);
      cache_[location] = tile;
      return *tile;
    }
  }


  PyramidReader::Location PyramidReader::MapTargetToSourceLocation(unsigned int tileX,
                                                                   unsigned int tileY)
  {
    return std::make_pair(tileX / (sourceTileWidth_ / targetTileWidth_),
                          tileY / (sourceTileHeight_ / targetTileHeight_));
  }


  PyramidReader::PyramidReader(ITiledPyramid& source,
                               unsigned int level,
                               unsigned int targetTileWidth,
                               unsigned int targetTileHeight,
                               const DicomizerParameters& parameters) :
    source_(source),
    level_(level),
    levelWidth_(source.GetLevelWidth(level)),
    levelHeight_(source.GetLevelHeight(level)),
    sourceTileWidth_(source.GetTileWidth(level)),
    sourceTileHeight_(source.GetTileHeight(level)),
    targetTileWidth_(targetTileWidth),
    targetTileHeight_(targetTileHeight),
    parameters_(parameters)
  {
    if (sourceTileWidth_ % targetTileWidth_ != 0 ||
        sourceTileHeight_ % targetTileHeight_ != 0)
    {
      LOG(ERROR) << "When resampling the tile size, it must be a integer divisor of the original tile size";
      throw Orthanc::OrthancException(Orthanc::ErrorCode_IncompatibleImageSize);
    }
  }


  PyramidReader::~PyramidReader()
  {
    for (Cache::iterator it = cache_.begin(); it != cache_.end(); ++it)
    {
      assert(it->second != NULL);
      delete it->second;
    }
  }


  const std::string* PyramidReader::GetRawTile(ImageCompression& compression,
                                               unsigned int tileX,
                                               unsigned int tileY)
  {
    if (sourceTileWidth_ != targetTileWidth_ ||
        sourceTileHeight_ != targetTileHeight_)
    {
      return NULL;
    }

    SourceTile& source = AccessSourceTile(MapTargetToSourceLocation(tileX, tileY));

    if (source.HasRawTile(compression))
    {
      CheckTileSize(source.GetRawTile(), compression);
      return &source.GetRawTile();
    }
    else
    {
      return NULL;
    }
  }


  void PyramidReader::GetDecodedTile(Orthanc::ImageAccessor& target,
                                     bool& isEmpty,
                                     unsigned int tileX,
                                     unsigned int tileY)
  {
    if (tileX * targetTileWidth_ >= levelWidth_ ||
        tileY * targetTileHeight_ >= levelHeight_)
    {
      // Accessing a tile out of the source image
      GetOutsideTile().GetReadOnlyAccessor(target);
      isEmpty = true;
    }
    else
    {
      SourceTile& source = AccessSourceTile(MapTargetToSourceLocation(tileX, tileY));
      const Orthanc::ImageAccessor& tile = source.GetDecodedTile();

      CheckTileSize(tile);

      assert(sourceTileWidth_ % targetTileWidth_ == 0 &&
             sourceTileHeight_ % targetTileHeight_ == 0);

      unsigned int xx = tileX % (sourceTileWidth_ / targetTileWidth_);
      unsigned int yy = tileY % (sourceTileHeight_ / targetTileHeight_);

      const uint8_t* bytes = 
        reinterpret_cast<const uint8_t*>(tile.GetConstRow(yy * targetTileHeight_)) +
        GetBytesPerPixel(tile.GetFormat()) * xx * targetTileWidth_;

      target.AssignReadOnly(tile.GetFormat(),
                            targetTileWidth_,
                            targetTileHeight_,
                            tile.GetPitch(), bytes);
      isEmpty = source.IsEmpty();
    }
  }
}
