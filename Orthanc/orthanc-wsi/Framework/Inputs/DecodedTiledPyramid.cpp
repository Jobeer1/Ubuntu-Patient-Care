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
#include "DecodedTiledPyramid.h"

#include "../ImageToolbox.h"

#include <Compatibility.h>  // For std::unique_ptr

#include <memory>
#include <cassert>

namespace OrthancWSI
{
  DecodedTiledPyramid::DecodedTiledPyramid()
  {
    SetBackgroundColor(255, 255, 255);
  }


  void DecodedTiledPyramid::SetBackgroundColor(uint8_t red,
                                               uint8_t green,
                                               uint8_t blue)
  {
    backgroundColor_[0] = red;
    backgroundColor_[1] = green;
    backgroundColor_[2] = blue;
  }


  void DecodedTiledPyramid::GetBackgroundColor(uint8_t& red,
                                               uint8_t& green,
                                               uint8_t& blue) const
  {
    red = backgroundColor_[0];
    green = backgroundColor_[1];
    blue = backgroundColor_[2];
  }


  Orthanc::ImageAccessor* DecodedTiledPyramid::DecodeTile(bool& isEmpty,
                                                          unsigned int level,
                                                          unsigned int tileX,
                                                          unsigned int tileY)
  {
    unsigned int x = tileX * GetTileWidth(level);
    unsigned int y = tileY * GetTileHeight(level);

    std::unique_ptr<Orthanc::ImageAccessor> tile
      (ImageToolbox::Allocate(GetPixelFormat(), GetTileWidth(level), GetTileHeight(level)));

    if (x >= GetLevelWidth(level) ||
        y >= GetLevelHeight(level))   // (*)
    {
      isEmpty = true;
      ImageToolbox::Set(*tile, backgroundColor_[0], backgroundColor_[1], backgroundColor_[2]);
      return tile.release();
    }

    bool fit = true;
    unsigned int regionWidth;
    if (x + GetTileWidth(level) <= GetLevelWidth(level))
    {
      regionWidth = GetTileWidth(level);
    }
    else
    {
      assert(GetLevelWidth(level) >= x);   // This results from (*)
      regionWidth = GetLevelWidth(level) - x;
      fit = false;
    }
    
    unsigned int regionHeight;
    if (y + GetTileHeight(level) <= GetLevelHeight(level))
    {
      regionHeight = GetTileHeight(level);
    }
    else
    {
      assert(GetLevelHeight(level) >= y);   // This results from (*)
      regionHeight = GetLevelHeight(level) - y;
      fit = false;
    }

    if (fit)
    {
      // The tile entirely lies inside the image
      ReadRegion(*tile, isEmpty, level, x, y);
    }
    else
    {
      // The tile exceeds the size of image, decode it to a temporary buffer
      std::unique_ptr<Orthanc::ImageAccessor> cropped
        (ImageToolbox::Allocate(GetPixelFormat(), regionWidth, regionHeight));
      ReadRegion(*cropped, isEmpty, level, x, y);

      // Create a white tile, and fill it with the cropped content
      ImageToolbox::Set(*tile, backgroundColor_[0], backgroundColor_[1], backgroundColor_[2]);
      ImageToolbox::Embed(*tile, *cropped, 0, 0);
    }

    return tile.release();
  }
}
