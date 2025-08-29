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

#include "PyramidWithRawTiles.h"
#include "DicomPyramidInstance.h"
#include "DicomPyramidLevel.h"

namespace OrthancWSI
{
  class DicomPyramid : public PyramidWithRawTiles
  {
  private:
    struct Comparator;

    OrthancStone::IOrthancConnection&   orthanc_;
    std::string                         seriesId_;
    std::vector<DicomPyramidInstance*>  instances_;
    std::vector<DicomPyramidLevel*>     levels_;
    uint8_t                             backgroundRed_;
    uint8_t                             backgroundGreen_;
    uint8_t                             backgroundBlue_;

    void Clear();

    void RegisterInstances(const std::string& seriesId,
                           bool useCache);

    void Check(const std::string& seriesId) const;

    void CheckLevel(size_t level) const;

  public:
    DicomPyramid(OrthancStone::IOrthancConnection& orthanc,
                 const std::string& seriesId,
                 bool useCache);

    virtual ~DicomPyramid()
    {
      Clear();
    }

    const std::string& GetSeriesId() const
    {
      return seriesId_;
    }

    virtual unsigned int GetLevelCount() const ORTHANC_OVERRIDE
    {
      return levels_.size();
    }

    virtual unsigned int GetLevelWidth(unsigned int level) const ORTHANC_OVERRIDE;

    virtual unsigned int GetLevelHeight(unsigned int level) const ORTHANC_OVERRIDE;

    virtual unsigned int GetTileWidth(unsigned int level) const ORTHANC_OVERRIDE;

    virtual unsigned int GetTileHeight(unsigned int level) const ORTHANC_OVERRIDE;

    virtual bool ReadRawTile(std::string& tile,
                             ImageCompression& compression,
                             unsigned int level,
                             unsigned int tileX,
                             unsigned int tileY) ORTHANC_OVERRIDE;

    virtual Orthanc::PixelFormat GetPixelFormat() const ORTHANC_OVERRIDE;

    virtual Orthanc::PhotometricInterpretation GetPhotometricInterpretation() const ORTHANC_OVERRIDE;

    uint8_t GetBackgroundRed() const
    {
      return backgroundRed_;
    }

    uint8_t GetBackgroundGreen() const
    {
      return backgroundGreen_;
    }

    uint8_t GetBackgroundBlue() const
    {
      return backgroundBlue_;
    }

    bool LookupImagedVolumeSize(double& width,
                                double& height) const;
  };
}
