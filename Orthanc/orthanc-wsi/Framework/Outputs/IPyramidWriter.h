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

#include "../Enumerations.h"
#include <Images/ImageAccessor.h>

#include <boost/noncopyable.hpp>

namespace OrthancWSI
{
  class IPyramidWriter : public boost::noncopyable
  {
  public:
    virtual ~IPyramidWriter()
    {
    }

    virtual unsigned int GetLevelCount() const = 0;
    
    virtual Orthanc::PixelFormat GetPixelFormat() const = 0;

    virtual unsigned int GetTileWidth() const = 0;

    virtual unsigned int GetTileHeight() const = 0;

    virtual unsigned int GetCountTilesX(unsigned int level) const = 0;

    virtual unsigned int GetCountTilesY(unsigned int level) const = 0;

    virtual void WriteRawTile(const std::string& tile,
                              ImageCompression compression,
                              unsigned int level,
                              unsigned int tileX,
                              unsigned int tileY) = 0;

    virtual void EncodeTile(const Orthanc::ImageAccessor& tile,
                            unsigned int level,
                            unsigned int tileX, 
                            unsigned int tileY) = 0;
  };
}
