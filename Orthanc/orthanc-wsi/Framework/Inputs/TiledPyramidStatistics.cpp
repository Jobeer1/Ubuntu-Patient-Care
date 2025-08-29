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
#include "TiledPyramidStatistics.h"

#include <Logging.h>


namespace OrthancWSI
{
  TiledPyramidStatistics::TiledPyramidStatistics(ITiledPyramid& source) :
    source_(source),
    countRawAccesses_(0),
    countDecodedTiles_(0)
  {
  }


  TiledPyramidStatistics::~TiledPyramidStatistics()
  {
    LOG(WARNING) << "Closing the input image (" 
                 << countRawAccesses_ << " raw accesses to the tiles, "
                 << countDecodedTiles_ << " decoded tiles)";
  }


  bool TiledPyramidStatistics::ReadRawTile(std::string& tile,
                                           ImageCompression& compression,
                                           unsigned int level,
                                           unsigned int tileX,
                                           unsigned int tileY)
  {
    if (source_.ReadRawTile(tile, compression, level, tileX, tileY))
    {
      boost::mutex::scoped_lock lock(mutex_);
      countRawAccesses_++;
      return true;
    }
    else
    {
      return false;
    }
  }


  Orthanc::ImageAccessor* TiledPyramidStatistics::DecodeTile(bool& isEmpty,
                                                             unsigned int level,
                                                             unsigned int tileX,
                                                             unsigned int tileY)
  {
    {
      boost::mutex::scoped_lock lock(mutex_);
      countDecodedTiles_++;
    }

    return source_.DecodeTile(isEmpty, level, tileX, tileY);
  }
}
