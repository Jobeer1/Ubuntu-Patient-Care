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


namespace OrthancWSI
{
  /**
   * This class acts as a wrapper for "cropped" tiled images, where
   * the tiles at the right or at the bottom might not have the same
   * dimensions of the other slides.
   **/
  class DecodedTiledPyramid : public ITiledPyramid
  {
  private:
    uint8_t  backgroundColor_[3];

  protected:
    // Subclasses can assume that the requested region is fully inside
    // the image, and that target has the proper size to store the
    // region. Pay attention to implement mutual exclusion in subclasses.
    virtual void ReadRegion(Orthanc::ImageAccessor& target,
                            bool& isEmpty,
                            unsigned int level,
                            unsigned int x,
                            unsigned int y) = 0;

  public:
    DecodedTiledPyramid();

    void SetBackgroundColor(uint8_t red,
                            uint8_t green,
                            uint8_t blue);

    void GetBackgroundColor(uint8_t& red,
                            uint8_t& green,
                            uint8_t& blue) const;

    virtual Orthanc::ImageAccessor* DecodeTile(bool& isEmpty,
                                               unsigned int level,
                                               unsigned int tileX,
                                               unsigned int tileY) ORTHANC_OVERRIDE;

    virtual bool ReadRawTile(std::string& tile,
                             ImageCompression& compression,
                             unsigned int level,
                             unsigned int tileX,
                             unsigned int tileY) ORTHANC_OVERRIDE
    {
      return false;   // No access to the raw tiles
    }

    virtual size_t GetMemoryUsage() const = 0;
  };
}
