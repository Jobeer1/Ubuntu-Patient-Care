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

#include "DecodedTiledPyramid.h"

namespace OrthancWSI
{
  class SingleLevelDecodedPyramid : public DecodedTiledPyramid
  {
  private:
    Orthanc::ImageAccessor  image_;
    unsigned int            tileWidth_;
    unsigned int            tileHeight_;
    unsigned int            padding_;
    uint8_t                 backgroundRed_;
    uint8_t                 backgroundGreen_;
    uint8_t                 backgroundBlue_;

  protected:
    void SetImage(const Orthanc::ImageAccessor& image)
    {
      image.GetReadOnlyAccessor(image_);
    }

    virtual void ReadRegion(Orthanc::ImageAccessor& target,
                            bool& isEmpty,
                            unsigned int level,
                            unsigned int x,
                            unsigned int y) ORTHANC_OVERRIDE;

  public:
    SingleLevelDecodedPyramid(unsigned int tileWidth,
                              unsigned int tileHeight);

    virtual unsigned int GetTileWidth(unsigned int level) const ORTHANC_OVERRIDE
    {
      return tileWidth_;
    }

    virtual unsigned int GetTileHeight(unsigned int level) const ORTHANC_OVERRIDE
    {
      return tileHeight_;
    }

    virtual unsigned int GetLevelCount() const ORTHANC_OVERRIDE
    {
      return 1;
    }

    virtual unsigned int GetLevelWidth(unsigned int level) const ORTHANC_OVERRIDE;

    virtual unsigned int GetLevelHeight(unsigned int level) const ORTHANC_OVERRIDE;

    virtual Orthanc::PixelFormat GetPixelFormat() const ORTHANC_OVERRIDE
    {
      return image_.GetFormat();
    }

    virtual Orthanc::PhotometricInterpretation GetPhotometricInterpretation() const ORTHANC_OVERRIDE;

    void SetPadding(unsigned int padding,
                    uint8_t backgroundRed,
                    uint8_t backgroundGreen,
                    uint8_t backgroundBlue);

    size_t GetMemoryUsage() const ORTHANC_OVERRIDE
    {
      return image_.GetSize();
    }
  };
}
