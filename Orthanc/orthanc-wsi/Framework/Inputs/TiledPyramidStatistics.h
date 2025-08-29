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

#include "ITiledPyramid.h"

#include <boost/thread/mutex.hpp>

namespace OrthancWSI
{
  class TiledPyramidStatistics : public ITiledPyramid
  {
  private:
    boost::mutex   mutex_;
    ITiledPyramid& source_;  // This is a facade design pattern
    unsigned int   countRawAccesses_;
    unsigned int   countDecodedTiles_;

  public:
    explicit TiledPyramidStatistics(ITiledPyramid& source);   // Takes ownership

    virtual ~TiledPyramidStatistics();

    virtual unsigned int GetLevelCount() const ORTHANC_OVERRIDE
    {
      return source_.GetLevelCount();
    }

    virtual unsigned int GetLevelWidth(unsigned int level)  const ORTHANC_OVERRIDE
    {
      return source_.GetLevelWidth(level);
    }

    virtual unsigned int GetLevelHeight(unsigned int level) const ORTHANC_OVERRIDE
    {
      return source_.GetLevelHeight(level);
    }

    virtual unsigned int GetTileWidth(unsigned int level) const ORTHANC_OVERRIDE
    {
      return source_.GetTileWidth(level);
    }
    
    virtual unsigned int GetTileHeight(unsigned int level) const ORTHANC_OVERRIDE
    {
      return source_.GetTileHeight(level);
    }

    virtual Orthanc::PixelFormat GetPixelFormat() const ORTHANC_OVERRIDE
    {
      return source_.GetPixelFormat();
    }

    virtual bool ReadRawTile(std::string& tile,
                             ImageCompression& compression,
                             unsigned int level,
                             unsigned int tileX,
                             unsigned int tileY) ORTHANC_OVERRIDE;

    virtual Orthanc::ImageAccessor* DecodeTile(bool& isEmpty,
                                               unsigned int level,
                                               unsigned int tileX,
                                               unsigned int tileY) ORTHANC_OVERRIDE;

    virtual Orthanc::PhotometricInterpretation GetPhotometricInterpretation() const ORTHANC_OVERRIDE
    {
      return source_.GetPhotometricInterpretation();
    }
  };
}
