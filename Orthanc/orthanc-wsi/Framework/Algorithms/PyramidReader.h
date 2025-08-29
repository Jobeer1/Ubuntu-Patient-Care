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


#pragma once

#include "../Inputs/ITiledPyramid.h"
#include "../DicomizerParameters.h"

#include <Compatibility.h>  // For std::unique_ptr

#include <map>
#include <memory>

namespace OrthancWSI
{
  // This class is not thread-safe
  class PyramidReader : public boost::noncopyable
  {
  private:
    class SourceTile;

    typedef std::pair<unsigned int, unsigned int>  Location;
    typedef std::map<Location, SourceTile*>        Cache;

    ITiledPyramid&  source_;
    unsigned int    level_;
    unsigned int    levelWidth_;
    unsigned int    levelHeight_;
    unsigned int    sourceTileWidth_;
    unsigned int    sourceTileHeight_;
    unsigned int    targetTileWidth_;
    unsigned int    targetTileHeight_;
    const DicomizerParameters& parameters_;

    Cache           cache_;

    std::unique_ptr<Orthanc::ImageAccessor>  outside_;


    Orthanc::ImageAccessor& GetOutsideTile();

    void CheckTileSize(const Orthanc::ImageAccessor& tile) const;

    void CheckTileSize(const std::string& tile,
                       ImageCompression compression) const;

    SourceTile& AccessSourceTile(const Location& location);

    Location MapTargetToSourceLocation(unsigned int tileX,
                                       unsigned int tileY);

  public:
    PyramidReader(ITiledPyramid& source,
                  unsigned int level,
                  unsigned int targetTileWidth,
                  unsigned int targetTileHeight,
                  const DicomizerParameters& parameters);

    ~PyramidReader();

    const DicomizerParameters& GetParameters() const
    {
      return parameters_;
    }

    Orthanc::PixelFormat GetPixelFormat() const
    {
      return source_.GetPixelFormat();
    }

    const std::string* GetRawTile(ImageCompression& compression,
                                  unsigned int tileX,
                                  unsigned int tileY);

    void GetDecodedTile(Orthanc::ImageAccessor& target,
                        bool& isEmpty,
                        unsigned int tileX,
                        unsigned int tileY);  
  };
}
