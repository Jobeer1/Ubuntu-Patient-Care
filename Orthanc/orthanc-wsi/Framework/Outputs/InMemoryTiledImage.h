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
#include "../Outputs/IPyramidWriter.h"

#include <map>
#include <boost/thread.hpp>

namespace OrthancWSI
{
  class InMemoryTiledImage : 
    public ITiledPyramid, 
    public IPyramidWriter
  {
  private:
    typedef std::pair<unsigned int, unsigned int>        Location;
    typedef std::map<Location, Orthanc::ImageAccessor*>  Tiles;

    boost::mutex          mutex_;
    Orthanc::PixelFormat  format_;
    unsigned int          countTilesX_;
    unsigned int          countTilesY_;
    unsigned int          tileWidth_;
    unsigned int          tileHeight_;
    Tiles                 tiles_;
    Orthanc::PhotometricInterpretation  photometric_;

  public:
    InMemoryTiledImage(Orthanc::PixelFormat format,
                       unsigned int countTilesX,
                       unsigned int countTilesY,
                       unsigned int tileWidth,
                       unsigned int tileHeight,
                       Orthanc::PhotometricInterpretation photometric);

    virtual ~InMemoryTiledImage();

    virtual unsigned int GetLevelCount() const ORTHANC_OVERRIDE
    {
      return 1;
    }

    virtual unsigned int GetCountTilesX(unsigned int level) const ORTHANC_OVERRIDE;

    virtual unsigned int GetCountTilesY(unsigned int level) const ORTHANC_OVERRIDE;

    virtual unsigned int GetLevelWidth(unsigned int level) const ORTHANC_OVERRIDE;

    virtual unsigned int GetLevelHeight(unsigned int level) const ORTHANC_OVERRIDE;

    // From IPyramidWriter (if used as an output)
    virtual unsigned int GetTileWidth() const ORTHANC_OVERRIDE
    {
      return tileWidth_;
    }

    virtual unsigned int GetTileHeight() const ORTHANC_OVERRIDE
    {
      return tileHeight_;
    }

    // From ITiledPyramid (if used as an input)
    virtual unsigned int GetTileWidth(unsigned int level) const ORTHANC_OVERRIDE
    {
      return tileWidth_;
    }

    virtual unsigned int GetTileHeight(unsigned int level) const ORTHANC_OVERRIDE
    {
      return tileHeight_;
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

    virtual Orthanc::PixelFormat GetPixelFormat() const ORTHANC_OVERRIDE
    {
      return format_;
    }

    virtual void WriteRawTile(const std::string& raw,
                              ImageCompression compression,
                              unsigned int level,
                              unsigned int tileX,
                              unsigned int tileY) ORTHANC_OVERRIDE;

    virtual void EncodeTile(const Orthanc::ImageAccessor& tile,
                            unsigned int level,
                            unsigned int tileX,
                            unsigned int tileY) ORTHANC_OVERRIDE;

    virtual Orthanc::PhotometricInterpretation GetPhotometricInterpretation() const ORTHANC_OVERRIDE
    {
      return photometric_;
    }
  };
}
