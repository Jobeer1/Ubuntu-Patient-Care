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

#include <Compatibility.h>

#include <vector>


namespace OrthancWSI
{
  class OnTheFlyPyramid : public DecodedTiledPyramid
  {
  private:
    std::unique_ptr<Orthanc::ImageAccessor>  baseLevel_;
    std::vector<Orthanc::ImageAccessor*>     higherLevels_;
    unsigned int                             tileWidth_;
    unsigned int                             tileHeight_;

  protected:
    void ReadRegion(Orthanc::ImageAccessor &target,
                    bool &isEmpty,
                    unsigned level,
                    unsigned x,
                    unsigned y) ORTHANC_OVERRIDE;

  public:
    OnTheFlyPyramid(Orthanc::ImageAccessor* baseLevel /* takes ownership */,
                    unsigned int tileWidth,
                    unsigned int tileHeight,
                    bool smooth);

    virtual ~OnTheFlyPyramid();

    const Orthanc::ImageAccessor& GetLevel(unsigned int level) const;

    unsigned GetLevelCount() const ORTHANC_OVERRIDE
    {
      return higherLevels_.size() + 1 /* base level */;
    }

    unsigned GetLevelWidth(unsigned int level) const ORTHANC_OVERRIDE
    {
      return GetLevel(level).GetWidth();
    }

    unsigned GetLevelHeight(unsigned int level) const ORTHANC_OVERRIDE
    {
      return GetLevel(level).GetHeight();
    }

    unsigned GetTileWidth(unsigned int level) const ORTHANC_OVERRIDE
    {
      return tileWidth_;
    }

    unsigned GetTileHeight(unsigned level) const ORTHANC_OVERRIDE
    {
      return tileHeight_;
    }

    Orthanc::PixelFormat GetPixelFormat() const ORTHANC_OVERRIDE
    {
      return baseLevel_->GetFormat();
    }

    Orthanc::PhotometricInterpretation GetPhotometricInterpretation() const ORTHANC_OVERRIDE
    {
      return Orthanc::PhotometricInterpretation_RGB;
    }

    size_t GetMemoryUsage() const ORTHANC_OVERRIDE;
  };
}
