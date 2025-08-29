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

#include "../Framework/Inputs/DecodedPyramidCache.h"
#include "../Resources/Orthanc/Stone/IOrthancConnection.h"


namespace OrthancWSI
{
  class OrthancPyramidFrameFetcher : public DecodedPyramidCache::IPyramidFetcher
  {
  private:
    std::unique_ptr<OrthancStone::IOrthancConnection>  orthanc_;
    bool                                               smooth_;
    unsigned int                                       tileWidth_;
    unsigned int                                       tileHeight_;
    unsigned int                                       paddingX_;
    unsigned int                                       paddingY_;
    uint8_t                                            defaultBackgroundRed_;
    uint8_t                                            defaultBackgroundGreen_;
    uint8_t                                            defaultBackgroundBlue_;

  public:
    OrthancPyramidFrameFetcher(OrthancStone::IOrthancConnection* orthanc,
                               bool smooth);

    unsigned int GetTileWidth() const
    {
      return tileWidth_;
    }

    void SetTileWidth(unsigned int tileWidth);

    unsigned int GetTileHeight() const
    {
      return tileHeight_;
    }

    void SetTileHeight(unsigned int tileHeight);

    unsigned int GetPaddingX() const
    {
      return paddingX_;
    }

    // "0" or "1" implies no padding
    void SetPaddingX(unsigned int paddingX)
    {
      paddingX_ = paddingX;
    }

    unsigned int GetPaddingY() const
    {
      return paddingY_;
    }

    // "0" or "1" implies no padding
    void SetPaddingY(unsigned int paddingY)
    {
      paddingY_ = paddingY;
    }

    void SetDefaultBackgroundColor(uint8_t red,
                                   uint8_t green,
                                   uint8_t blue);

    DecodedTiledPyramid* Fetch(const std::string &instanceId,
                               unsigned frameNumber) ORTHANC_OVERRIDE;
  };
}
