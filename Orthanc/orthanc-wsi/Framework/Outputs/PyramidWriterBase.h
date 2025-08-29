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

#include "IPyramidWriter.h"

#include <boost/thread.hpp>

namespace OrthancWSI
{
  class PyramidWriterBase : public IPyramidWriter
  {
  protected:
    struct Level
    {
      unsigned int  z_;
      unsigned int  width_;
      unsigned int  height_;
      unsigned int  countTilesX_;
      unsigned int  countTilesY_;
    };

    // WARNING: The following method can be called from multiple
    // threads, locking must be implemented in derived classes.
    virtual void WriteRawTileInternal(const std::string& tile,
                                      const Level& level,
                                      unsigned int tileX,
                                      unsigned int tileY) = 0;

    // This function is invoked before any call to WriteRawTileInternal()
    virtual void AddLevelInternal(const Level& level) = 0;

    virtual void EncodeTileInternal(std::string& encoded,
                                    const Orthanc::ImageAccessor& tile) = 0;

  private:
    boost::mutex          mutex_;   // This mutex protects access to the levels
    Orthanc::PixelFormat  pixelFormat_;
    ImageCompression      compression_;
    unsigned int          tileWidth_;
    unsigned int          tileHeight_;
    uint8_t               jpegQuality_;
    std::vector<Level>    levels_;
    bool                  first_;

    Level GetLevel(unsigned int level) const;

  public:
    PyramidWriterBase(Orthanc::PixelFormat pixelFormat,
                      ImageCompression compression,
                      unsigned int tileWidth,
                      unsigned int tileHeight);

    uint8_t GetJpegQuality() const
    {
      return jpegQuality_;
    }

    void SetJpegQuality(int quality);

    void AddLevel(unsigned int width,
                  unsigned int height);
    
    virtual unsigned int GetTileWidth() const ORTHANC_OVERRIDE
    {
      return tileWidth_;
    }

    virtual unsigned int GetTileHeight() const ORTHANC_OVERRIDE
    {
      return tileHeight_;
    }

    virtual unsigned int GetCountTilesX(unsigned int level) const ORTHANC_OVERRIDE
    {
      return GetLevel(level).countTilesX_;
    }

    virtual unsigned int GetCountTilesY(unsigned int level) const ORTHANC_OVERRIDE
    {
      return GetLevel(level).countTilesY_;
    }

    virtual unsigned int GetLevelCount() const ORTHANC_OVERRIDE;

    ImageCompression GetImageCompression() const
    {
      return compression_;
    }

    virtual void WriteRawTile(const std::string& tile,
                              ImageCompression compression,
                              unsigned int z,
                              unsigned int tileX,
                              unsigned int tileY) ORTHANC_OVERRIDE;

    virtual void EncodeTile(const Orthanc::ImageAccessor& tile,
                            unsigned int z,
                            unsigned int tileX, 
                            unsigned int tileY) ORTHANC_OVERRIDE;

    virtual Orthanc::PixelFormat GetPixelFormat() const ORTHANC_OVERRIDE
    {
      return pixelFormat_;
    }

    virtual void Flush() = 0;
  };
}
