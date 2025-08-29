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

#include "PyramidWriterBase.h"
#include "MultiframeDicomWriter.h"
#include "../Targets/IFileTarget.h"
#include "../ImagedVolumeParameters.h"

namespace OrthancWSI
{
  class DicomPyramidWriter : public PyramidWriterBase
  {
  private:
    std::vector<MultiframeDicomWriter*>  writers_;

    boost::mutex       mutex_;   // Protects the access to "writers_"
    IFileTarget&       target_;
    const DcmDataset&  dataset_;
    size_t             maxSize_;
    size_t             countTiles_;
    unsigned int       countInstances_;
      
    const ImagedVolumeParameters&       volume_;
    Orthanc::PhotometricInterpretation  photometric_;

    void FlushInternal(MultiframeDicomWriter& writer,
                       bool force);

    DcmItem* CreateFunctionalGroup(unsigned int frame,
                                   unsigned int x, 
                                   unsigned int y,
                                   unsigned int totalWidth,
                                   unsigned int totalHeight,
                                   float physicalZ) const;

  protected:
    virtual void WriteRawTileInternal(const std::string& tile,
                                      const Level& level,
                                      unsigned int x,
                                      unsigned int y) ORTHANC_OVERRIDE;

    virtual void AddLevelInternal(const Level& level) ORTHANC_OVERRIDE
    {
    }

    virtual void EncodeTileInternal(std::string& encoded,
                                    const Orthanc::ImageAccessor& tile) ORTHANC_OVERRIDE;

  public:
    DicomPyramidWriter(IFileTarget&  target,
                       const DcmDataset& dataset,
                       Orthanc::PixelFormat pixelFormat,
                       ImageCompression compression,
                       unsigned int tileWidth,
                       unsigned int tileHeight,
                       size_t maxSize,   // If "0", no automatic flushing
                       const ImagedVolumeParameters&  volume,
                       Orthanc::PhotometricInterpretation photometric);

    virtual ~DicomPyramidWriter();

    virtual void Flush() ORTHANC_OVERRIDE;
  };
}
