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
#include "OpenSlideLibrary.h"

namespace OrthancWSI
{
  class OpenSlidePyramid : public DecodedTiledPyramid
  {
  private:
    OpenSlideLibrary::Image  image_;
    unsigned int             tileWidth_;
    unsigned int             tileHeight_;

  protected:
    virtual void ReadRegion(Orthanc::ImageAccessor& target,
                            bool& isEmpty,
                            unsigned int level,
                            unsigned int x,
                            unsigned int y) ORTHANC_OVERRIDE;

  public:
    OpenSlidePyramid(const std::string& path,
                     unsigned int tileWidth,
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
      return image_.GetLevelCount();
    }

    virtual unsigned int GetLevelWidth(unsigned int level) const ORTHANC_OVERRIDE
    {
      return image_.GetLevelWidth(level);
    }

    virtual unsigned int GetLevelHeight(unsigned int level) const ORTHANC_OVERRIDE
    {
      return image_.GetLevelHeight(level);
    }

    virtual Orthanc::PixelFormat GetPixelFormat() const ORTHANC_OVERRIDE
    {
      return Orthanc::PixelFormat_RGB24;
    }

    virtual Orthanc::PhotometricInterpretation GetPhotometricInterpretation() const ORTHANC_OVERRIDE
    {
      return Orthanc::PhotometricInterpretation_RGB;
    }

    bool LookupImagedVolumeSize(float& width,
                                float& height) const;

    size_t GetMemoryUsage() const ORTHANC_OVERRIDE;
  };
}
