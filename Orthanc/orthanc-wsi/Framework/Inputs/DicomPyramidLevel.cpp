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
#include "DicomPyramidLevel.h"

#include "../ImageToolbox.h"

#include <Logging.h>
#include <OrthancException.h>

#include <boost/lexical_cast.hpp>

namespace OrthancWSI
{
  DicomPyramidLevel::TileContent& DicomPyramidLevel::GetTileContent(unsigned int tileX,
                                                                    unsigned int tileY)
  {
    if (tileX >= countTilesX_ ||
        tileY >= countTilesY_)
    {
      LOG(ERROR) << "Tile location (" << tileX << "," << tileY << ") is outside the image";
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
    }

    return tiles_[tileY * countTilesX_ + tileX];
  }

  void DicomPyramidLevel::RegisterFrame(DicomPyramidInstance& instance,
                                        unsigned int frame)
  {
    unsigned int tileX = instance.GetFrameLocationX(frame);
    unsigned int tileY = instance.GetFrameLocationY(frame);
    TileContent& tile = GetTileContent(tileX, tileY);

    if (tile.instance_ != NULL)
    {
      LOG(ERROR) << "Tile with location (" << tileX << "," 
                 << tileY << ") is indexed twice in level of size "
                 << totalWidth_ << "x" << totalHeight_;
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
    }

    tile.instance_ = &instance;
    tile.frame_ = frame;
  }


  bool DicomPyramidLevel::LookupTile(TileContent& tile,
                                     unsigned int tileX,
                                     unsigned int tileY) const
  {
    const TileContent& tmp = const_cast<DicomPyramidLevel&>(*this).GetTileContent(tileX, tileY);

    if (tmp.instance_ == NULL)
    {
      return false;
    }
    else
    {
      tile = tmp;
      return true;
    }
  }


  DicomPyramidLevel::DicomPyramidLevel(DicomPyramidInstance& instance) :
    totalWidth_(instance.GetTotalWidth()),
    totalHeight_(instance.GetTotalHeight()),
    tileWidth_(instance.GetTileWidth()),
    tileHeight_(instance.GetTileHeight())
  {
    if (totalWidth_ == 0 ||
        totalHeight_ == 0)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }

    countTilesX_ = CeilingDivision(totalWidth_, tileWidth_);
    countTilesY_ = CeilingDivision(totalHeight_, tileHeight_);
    tiles_.resize(countTilesX_ * countTilesY_);
      
    AddInstance(instance);
  }


  void DicomPyramidLevel::AddInstance(DicomPyramidInstance& instance)
  {
    if (instance.GetTotalWidth() != totalWidth_ ||
        instance.GetTotalHeight() != totalHeight_ ||
        instance.GetTileWidth() != tileWidth_ ||
        instance.GetTileHeight() != tileHeight_)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_IncompatibleImageSize);
    }

    for (size_t frame = 0; frame < instance.GetFrameCount(); frame++)
    {
      RegisterFrame(instance, frame);
    }
  }


  bool DicomPyramidLevel::DownloadRawTile(std::string& raw /* out */,
                                          Orthanc::PixelFormat& format /* out */,
                                          ImageCompression& compression /* out */,
                                          OrthancStone::IOrthancConnection& orthanc,
                                          unsigned int tileX,
                                          unsigned int tileY) const
  {
    TileContent tile;
    if (LookupTile(tile, tileX, tileY))
    {
      assert(tile.instance_ != NULL);
      DicomPyramidInstance& instance = *tile.instance_;

      compression = instance.GetImageCompression(orthanc);
      format = instance.GetPixelFormat();

      if (compression == ImageCompression_UseOrthancPreview)
      {
        // If the WSI viewer plugin has no built-in support for this transfer syntax,
        // use the decoding primitives offered by the Orthanc core
        std::string uri = ("/instances/" + instance.GetInstanceId() +
                           "/frames/" + boost::lexical_cast<std::string>(tile.frame_) + "/preview");
        orthanc.RestApiGet(raw, uri);

        if (ImageToolbox::HasPngSignature(raw))  // In theory, Orthanc should always generate PNG by default
        {
          compression = ImageCompression_Png;
          return true;
        }
        else if (ImageToolbox::HasJpegSignature(raw))
        {
          compression = ImageCompression_Jpeg;
          return true;
        }
        else
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError, "Cannot decode a preview image generated by the Orthanc core");
        }
      }
      else
      {
        std::string uri = ("/instances/" + instance.GetInstanceId() +
                           "/frames/" + boost::lexical_cast<std::string>(tile.frame_) + "/raw");
        orthanc.RestApiGet(raw, uri);
        return true;
      }
    }
    else
    {
      return false;
    }
  }
}
