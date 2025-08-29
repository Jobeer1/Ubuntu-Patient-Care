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
#include "../../Resources/Orthanc/Stone/IOrthancConnection.h"

#include <boost/noncopyable.hpp>
#include <vector>

namespace OrthancWSI
{
  class DicomPyramidInstance : public boost::noncopyable
  {
  private:
    typedef std::pair<unsigned int, unsigned int>  FrameLocation;

    std::string                         instanceId_;
    bool                                hasCompression_;
    ImageCompression                    compression_;
    Orthanc::PixelFormat                format_;
    unsigned int                        tileWidth_;
    unsigned int                        tileHeight_;
    unsigned int                        totalWidth_;
    unsigned int                        totalHeight_;
    std::vector<FrameLocation>          frames_;
    Orthanc::PhotometricInterpretation  photometric_;
    std::string                         imageType_;
    bool                                hasBackgroundColor_;
    uint8_t                             backgroundRed_;
    uint8_t                             backgroundGreen_;
    uint8_t                             backgroundBlue_;
    bool                                hasImagedVolumeSize_;
    double                              imagedVolumeWidth_;
    double                              imagedVolumeHeight_;
    bool                                hasLevel_;
    unsigned int                        level_;

    void Load(OrthancStone::IOrthancConnection&  orthanc,
              const std::string& instanceId);

    bool Deserialize(const std::string& content);

  public:
    DicomPyramidInstance(OrthancStone::IOrthancConnection&  orthanc,
                         const std::string& instanceId,
                         bool useCache);

    const std::string& GetInstanceId() const
    {
      return instanceId_;
    }

    ImageCompression GetImageCompression(OrthancStone::IOrthancConnection& orthanc);

    Orthanc::PixelFormat GetPixelFormat() const
    {
      return format_;
    }

    Orthanc::PhotometricInterpretation GetPhotometricInterpretation() const
    {
      return photometric_;
    }

    unsigned int GetTotalWidth() const
    {
      return totalWidth_;
    }

    unsigned int GetTotalHeight() const
    {
      return totalHeight_;
    }

    unsigned int GetTileWidth() const
    {
      return tileWidth_;
    }

    unsigned int GetTileHeight() const
    {
      return tileHeight_;
    }

    size_t GetFrameCount() const
    {
      return frames_.size();
    }

    const std::string& GetImageType() const
    {
      return imageType_;
    }

    unsigned int GetFrameLocationX(size_t frame) const;

    unsigned int GetFrameLocationY(size_t frame) const;

    void Serialize(std::string& result) const;

    bool HasBackgroundColor() const
    {
      return hasBackgroundColor_;
    }

    uint8_t GetBackgroundRed() const;

    uint8_t GetBackgroundGreen() const;

    uint8_t GetBackgroundBlue() const;

    bool HasImagedVolumeSize() const
    {
      return hasImagedVolumeSize_;
    }

    double GetImagedVolumeWidth() const;

    double GetImagedVolumeHeight() const;

    void SetLevel(unsigned int level);

    bool IsLevel(unsigned int level) const;
  };
}
