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

#include <Compatibility.h>  // For std::unique_ptr
#include <ChunkedBuffer.h>

#include <boost/noncopyable.hpp>
#include <memory>
#include <stdint.h>

#include <dcmtk/dcmdata/dcpixseq.h>
#include <dcmtk/dcmdata/dcdatset.h>
#include <dcmtk/dcmdata/dcfilefo.h>

namespace OrthancWSI
{
  class MultiframeDicomWriter : public boost::noncopyable
  {
  private:
    ImageCompression  compression_;
    E_TransferSyntax  transferSyntax_;
    DcmDataset        sharedTags_;
    size_t            writtenSize_;
    size_t            framesCount_;
    size_t            uncompressedFrameSize_;
    unsigned int      width_;
    unsigned int      height_;

    Orthanc::ChunkedBuffer             uncompressedPixelData_;
    std::unique_ptr<DcmSequenceOfItems>  perFrameFunctionalGroups_;
    std::unique_ptr<DcmPixelSequence>    compressedPixelSequence_;
    DcmPixelItem*                      offsetTable_;
    std::unique_ptr<DcmOffsetList>       offsetList_;

    bool             isConcatenation_;
    unsigned int     countInstances_;
    unsigned int     firstFrameInInstance_;
    
    void ResetImage();

    void InjectUncompressedPixelData(DcmFileFormat& dicom);

  public:
    MultiframeDicomWriter(const DcmDataset& dataset,
                          ImageCompression compression,
                          Orthanc::PixelFormat pixelFormat,
                          unsigned int width,
                          unsigned int height,
                          unsigned int tileWidth,
                          unsigned int tileHeight,
                          Orthanc::PhotometricInterpretation photometric,
                          bool isConcatenation);

    void AddFrame(const std::string& frame,
                  DcmItem* functionalGroup);   // This takes the ownership

    void Flush(std::string& target,
               unsigned int instanceNumber);

    unsigned int GetFramesCount() const
    {
      return framesCount_;
    }

    size_t GetSize() const
    {
      return writtenSize_;
    }

    unsigned int GetTotalWidth() const
    {
      return width_;
    }

    unsigned int GetTotalHeight() const
    {
      return height_;
    }

    DcmDataset& GetSharedTags()
    {
      return sharedTags_;
    }
  };
}
