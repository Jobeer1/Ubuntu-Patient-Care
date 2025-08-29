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


#include "../PrecompiledHeadersWSI.h"
#include "HierarchicalTiffWriter.h"

#include "../ImageToolbox.h"

#include <Logging.h>
#include <OrthancException.h>
#include <TemporaryFile.h>

namespace OrthancWSI
{
  class HierarchicalTiffWriter::PendingTile
  {
  private:
    HierarchicalTiffWriter&  that_;
    unsigned int             level_;
    unsigned int             tileX_;
    unsigned int             tileY_;
    Orthanc::TemporaryFile   file_;
      
  public:
    PendingTile(HierarchicalTiffWriter& that,
                unsigned int level,
                unsigned int tileX,
                unsigned int tileY,
                const std::string& tile) :
      that_(that),
      level_(level),
      tileX_(tileX),
      tileY_(tileY)
    {
      file_.Write(tile);
    }

    unsigned int GetLevel() const
    {
      return level_;
    }

    unsigned int GetTileX() const
    {
      return tileX_;
    }

    unsigned int GetTileY() const
    {
      return tileY_;
    }

    void Store(TIFF* tiff)
    {
      std::string tile;
      file_.Read(tile);
      that_.StoreTile(tile, tileX_, tileY_);
    }
  };


  struct HierarchicalTiffWriter::Comparator
  {
    inline bool operator() (PendingTile* const& a,
                            PendingTile* const& b)
    {
      if (a->GetLevel() < b->GetLevel())
      {
        return true;
      }

      if (a->GetLevel() > b->GetLevel())
      {
        return false;
      }

      if (a->GetTileY() < b->GetTileY())
      {
        return true;
      }

      if (a->GetTileY() > b->GetTileY())
      {
        return false;
      }

      return a->GetTileX() < b->GetTileX();
    }
  };


  static uint8_t GetUint8(const std::string& tile,
                          size_t index)
  {
    if (index >= tile.size())
    {
      return 0;
    }
    else
    {
      return static_cast<uint8_t>(tile[index]);
    }
  }

 
#if 0
  static uint16_t GetUint16(const std::string& tile,
                            size_t index)
  {
    if (index + 1 >= tile.size())
    {
      return 0;
    }
    else
    {
      return static_cast<uint16_t>(tile[index]) * 256 + static_cast<uint16_t>(tile[index + 1]);
    }
  }
#endif


  static void CheckJpegTile(const std::string& tile,
                            Orthanc::PixelFormat pixelFormat)
  {
    // Check the sampling by accessing the "Start of Frame" header of JPEG

    if (tile.size() < 3 ||
        static_cast<uint8_t>(tile[0]) != 0xff ||
        static_cast<uint8_t>(tile[1]) != 0xd8 ||
        static_cast<uint8_t>(tile[2]) != 0xff)
    {
      LOG(WARNING) << "The source image does not contain JPEG tiles";
      return;
    }

    // Look for the "Start of Frame" header (FF C0)
    for (size_t i = 2; i + 1 < tile.size(); i++)
    {
      if (static_cast<uint8_t>(tile[i]) == 0xff &&
          static_cast<uint8_t>(tile[i + 1]) == 0xc0)
      {
        uint8_t numberOfComponents = GetUint8(tile, i + 9);
          
        switch (pixelFormat)
        {
          case Orthanc::PixelFormat_Grayscale8:
            if (numberOfComponents != 1)
            {
              LOG(WARNING) << "The source image does not contain a grayscale image as expected";
            }
            break;

          case Orthanc::PixelFormat_RGB24:
          {
            if (numberOfComponents != 3)
            {
              LOG(WARNING) << "The source image does not contain a RGB24 color image as expected";
            }

            // Read the header corresponding to the first component
            const size_t component = 0;
            const size_t offset = i + 10 + component * 3; 
            const uint8_t sampling = GetUint8(tile, offset + 1);
            const int samplingH = sampling / 16;
            const int samplingV = sampling % 16;

            LOG(WARNING) << "The source image uses chroma sampling " << samplingH << ":" << samplingV;

            if (samplingH != 2 ||
                samplingV != 2)
            {
              LOG(WARNING) << "The source image has not a chroma sampling of 2:2, "
                           << "you should consider using option \"--reencode\"";
            }

            break;
          }

          default:
            break;
        }
      }
    }
  }


 
  void HierarchicalTiffWriter::StoreTile(const std::string& tile,
                                         unsigned int tileX,
                                         unsigned int tileY)
  {
    // Get the index of the tile
    ttile_t index = TIFFComputeTile(tiff_, tileX * GetTileWidth(), tileY * GetTileHeight(), 0 /*z*/, 0 /*sample*/);

    if (TIFFWriteRawTile(tiff_, index, tile.size() ? const_cast<char*>(&tile[0]) : NULL, tile.size()) != 
        static_cast<tsize_t>(tile.size()))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_CannotWriteFile);
    }

    if (isFirst_ &&
        GetImageCompression() == ImageCompression_Jpeg)
    {
      CheckJpegTile(tile, GetPixelFormat());
    }

    isFirst_ = false;
  }


  void HierarchicalTiffWriter::ConfigureLevel(const Level& level,
                                              bool createLevel)
  {
    if (createLevel && TIFFWriteDirectory(tiff_) != 1)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_CannotWriteFile);
    }

    if (TIFFFlush(tiff_) != 1)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_CannotWriteFile);
    }

    currentLevel_ = level.z_;
    nextX_ = 0;
    nextY_ = 0;

    switch (GetImageCompression())
    {
      case ImageCompression_Jpeg:
      {
        uint16_t c = COMPRESSION_JPEG;

        if (TIFFSetField(tiff_, TIFFTAG_COMPRESSION, c) != 1)
        {
          Close();
          throw Orthanc::OrthancException(Orthanc::ErrorCode_CannotWriteFile);
        }

        break;
      }

      default:
        throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
    }


    switch (GetPixelFormat())
    {
      case Orthanc::PixelFormat_RGB24:
      {
        uint16_t samplesPerPixel = 3;
        uint16_t photometric;
        uint16_t planar = PLANARCONFIG_CONTIG;   // Interleaved RGB
        uint16_t bpp = 8;
        uint16_t subsampleHorizontal = 2;
        uint16_t subsampleVertical = 2;

        switch (photometric_)
        {
          case Orthanc::PhotometricInterpretation_YBRFull422:
            photometric = PHOTOMETRIC_YCBCR;
            break;

          case Orthanc::PhotometricInterpretation_RGB:
            photometric = PHOTOMETRIC_RGB;
            break;

          default:
            throw Orthanc::OrthancException(
              Orthanc::ErrorCode_ParameterOutOfRange,
              "Unsupported photometric interpreation: " +
              std::string(Orthanc::EnumerationToString(photometric_)));
        }
  
        if (TIFFSetField(tiff_, TIFFTAG_SAMPLESPERPIXEL, samplesPerPixel) != 1 ||
            TIFFSetField(tiff_, TIFFTAG_PHOTOMETRIC, photometric) != 1 ||
            TIFFSetField(tiff_, TIFFTAG_BITSPERSAMPLE, bpp) != 1 ||
            TIFFSetField(tiff_, TIFFTAG_PLANARCONFIG, planar) != 1 ||
            TIFFSetField(tiff_, TIFFTAG_YCBCRSUBSAMPLING, subsampleHorizontal, subsampleVertical) != 1)
        {
          Close();
          throw Orthanc::OrthancException(Orthanc::ErrorCode_CannotWriteFile);
        }

        break;
      }

      case Orthanc::PixelFormat_Grayscale8:
      {
        uint16_t samplesPerPixel = 1;
        uint16_t bpp = 8;
        uint16_t photometric = PHOTOMETRIC_MINISBLACK;

        if (TIFFSetField(tiff_, TIFFTAG_SAMPLESPERPIXEL, samplesPerPixel) != 1 ||
            TIFFSetField(tiff_, TIFFTAG_PHOTOMETRIC, photometric) != 1 ||
            TIFFSetField(tiff_, TIFFTAG_BITSPERSAMPLE, bpp) != 1)
        {
          Close();
          throw Orthanc::OrthancException(Orthanc::ErrorCode_CannotWriteFile);
        }

        break;
      }

      default:
        throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
    }

    uint32_t w = level.width_;
    uint32_t h = level.height_;
    uint32_t tw = GetTileWidth();
    uint32_t th = GetTileHeight();

    if (TIFFSetField(tiff_, TIFFTAG_IMAGEWIDTH, w) != 1 ||
        TIFFSetField(tiff_, TIFFTAG_IMAGELENGTH, h) != 1 ||
        TIFFSetField(tiff_, TIFFTAG_TILEWIDTH, tw) != 1 ||
        TIFFSetField(tiff_, TIFFTAG_TILELENGTH, th) != 1)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_CannotWriteFile);
    }          
  }


  void HierarchicalTiffWriter::AdvanceToNextTile()
  {
    assert(currentLevel_ < levels_.size());

    nextX_ += 1;
    if (nextX_ >= levels_[currentLevel_].countTilesX_)
    {
      nextX_ = 0;
      nextY_ += 1;

      if (nextY_ >= levels_[currentLevel_].countTilesY_)
      {
        currentLevel_ += 1;

        if (currentLevel_ < levels_.size())
        {
          ConfigureLevel(levels_[currentLevel_], true);
        }
      }
    }
  }


  void HierarchicalTiffWriter::ScanPending()
  {
    std::sort(pending_.begin(), pending_.end(), Comparator());

    while (currentLevel_ < levels_.size() &&
           !pending_.empty() &&
           pending_.front()->GetLevel() == currentLevel_ &&
           pending_.front()->GetTileX() == nextX_ &&
           pending_.front()->GetTileY() == nextY_)
    {
      pending_.front()->Store(tiff_);
      delete pending_.front();
      pending_.pop_front();
      AdvanceToNextTile();
    }
  }
          

  void HierarchicalTiffWriter::WriteRawTileInternal(const std::string& tile,
                                                    const Level& level,
                                                    unsigned int tileX,
                                                    unsigned int tileY)
  {
    boost::mutex::scoped_lock lock(mutex_);

    if (level.z_ == currentLevel_ &&
        tileX == nextX_ &&
        tileY == nextY_)
    {
      StoreTile(tile, tileX, tileY);
      AdvanceToNextTile();
      ScanPending();
    }
    else
    {
      pending_.push_back(new PendingTile(*this, level.z_, tileX, tileY, tile));
    }
  }

        
  void HierarchicalTiffWriter::AddLevelInternal(const Level& level)
  {
    if (level.z_ == 0)
    {
      // Configure the finest level on initialization
      ConfigureLevel(level, false);
    }

    levels_.push_back(level);
  }


  void HierarchicalTiffWriter::EncodeTileInternal(std::string& encoded,
                                                  const Orthanc::ImageAccessor& tile)
  {
    ImageToolbox::EncodeTile(encoded, tile, GetImageCompression(), GetJpegQuality());
  }


  HierarchicalTiffWriter::HierarchicalTiffWriter(const std::string& path,
                                                 Orthanc::PixelFormat pixelFormat, 
                                                 ImageCompression compression,
                                                 unsigned int tileWidth,
                                                 unsigned int tileHeight,
                                                 Orthanc::PhotometricInterpretation photometric) :
    PyramidWriterBase(pixelFormat, compression, tileWidth, tileHeight),
    currentLevel_(0),
    nextX_(0),
    nextY_(0),
    isFirst_(true),
    photometric_(photometric)
  {
    tiff_ = TIFFOpen(path.c_str(), "w");
    if (tiff_ == NULL)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_CannotWriteFile);
    }
  }


  HierarchicalTiffWriter::~HierarchicalTiffWriter()
  {
    if (pending_.size())
    {
      LOG(ERROR) << "Some tiles (" << pending_.size() << ") were not written to the TIFF file";
    }

    for (size_t i = 0; i < pending_.size(); i++)
    {
      if (pending_[i])
      {
        delete pending_[i];
      }
    }

    Close();
  }


  void HierarchicalTiffWriter::Flush()
  {
    boost::mutex::scoped_lock lock(mutex_);
    ScanPending();
  }
}
