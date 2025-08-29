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
#include "../TiffReader.h"

#include <vector>
#include <boost/thread.hpp>

namespace OrthancWSI
{
  class HierarchicalTiff : public PyramidWithRawTiles
  {
  private:
    struct Level
    {
      tdir_t    directory_;
      unsigned int  width_;
      unsigned int  height_;
      std::string  headers_;
      std::string  description_;

      Level(TIFF* tiff,
            tdir_t    directory,
            unsigned int  width,
            unsigned int  height);
    };

    struct Comparator;

    boost::mutex          mutex_;
    TiffReader            reader_;
    Orthanc::PixelFormat  pixelFormat_;
    ImageCompression      compression_;
    unsigned int          tileWidth_;
    unsigned int          tileHeight_;
    std::vector<Level>    levels_;
    Orthanc::PhotometricInterpretation  photometric_;

    void CheckLevel(unsigned int level) const;

  public:
    explicit HierarchicalTiff(const std::string& path);

    virtual unsigned int GetLevelCount() const ORTHANC_OVERRIDE
    {
      return levels_.size();
    }

    virtual unsigned int GetLevelWidth(unsigned int level) const ORTHANC_OVERRIDE;

    virtual unsigned int GetLevelHeight(unsigned int level) const ORTHANC_OVERRIDE;

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

    virtual Orthanc::PixelFormat GetPixelFormat() const ORTHANC_OVERRIDE
    {
      return pixelFormat_;
    }

    virtual Orthanc::PhotometricInterpretation GetPhotometricInterpretation() const ORTHANC_OVERRIDE
    {
      return photometric_;
    }

    ImageCompression GetImageCompression()
    {
      return compression_;
    }

    bool LookupImagedVolumeSize(double& width,
                                double& height) const;
  };
}
