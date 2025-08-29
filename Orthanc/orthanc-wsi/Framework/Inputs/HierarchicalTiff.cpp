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
#include "HierarchicalTiff.h"

#include "../ImageToolbox.h"

#include <Logging.h>
#include <OrthancException.h>
#include <SerializationToolbox.h>
#include <Toolbox.h>

#include <iostream>
#include <algorithm>
#include <cassert>
#include <string.h>

namespace OrthancWSI
{
  HierarchicalTiff::Level::Level(TIFF* tiff,
                                 tdir_t    directory,
                                 unsigned int  width,
                                 unsigned int  height) :
    directory_(directory),
    width_(width),
    height_(height)
  {
    // Read the JPEG headers shared at that level, if any
    uint8_t *tables = NULL;
    uint32_t size;
    if (TIFFGetField(tiff, TIFFTAG_JPEGTABLES, &size, &tables) &&
        size > 0 && 
        tables != NULL)
    {
      // Look for the EOI (end-of-image) tag == FF D9
      // https://en.wikipedia.org/wiki/JPEG_File_Interchange_Format

      bool found = false;

      for (size_t i = 0; i + 1 < size; i++)
      {
        if (tables[i] == 0xff &&
            tables[i + 1] == 0xd9)
        {
          headers_.assign(reinterpret_cast<const char*>(tables), i);
          found = true;
        }
      }

      if (!found)
      {
        headers_.assign(reinterpret_cast<const char*>(tables), size);
      }
    }

    // Read the image description, if any
    const char* description = NULL;
    if (TIFFGetField(tiff, TIFFTAG_IMAGEDESCRIPTION, &description))
    {
      description_.assign(description);
    }
    else
    {
      description_.clear();
    }
  }

  struct HierarchicalTiff::Comparator
  {
    bool operator() (const HierarchicalTiff::Level& a,
                     const HierarchicalTiff::Level& b) const
    {
      return a.width_ > b.width_;
    }
  };


  void HierarchicalTiff::CheckLevel(unsigned int level) const
  {
    if (level >= levels_.size())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
  }


  HierarchicalTiff::HierarchicalTiff(const std::string& path) :
    reader_(path),
    tileWidth_(0),
    tileHeight_(0)
  {
    bool first = true;
    tdir_t pos = 0;

    do
    {
      uint32_t w, h, tw, th;
      ImageCompression compression;
      Orthanc::PixelFormat pixelFormat;
      Orthanc::PhotometricInterpretation photometric;

      if (TIFFSetDirectory(reader_.GetTiff(), pos) &&
          TIFFGetField(reader_.GetTiff(), TIFFTAG_IMAGEWIDTH, &w) &&
          TIFFGetField(reader_.GetTiff(), TIFFTAG_IMAGELENGTH, &h) &&
          TIFFGetField(reader_.GetTiff(), TIFFTAG_TILEWIDTH, &tw) &&
          TIFFGetField(reader_.GetTiff(), TIFFTAG_TILELENGTH, &th) &&
          w > 0 &&
          h > 0 &&
          tw > 0 &&
          th > 0 &&
          reader_.GetCurrentDirectoryInformation(compression, pixelFormat, photometric))
      {
        if (first)
        {
          tileWidth_ = tw;
          tileHeight_ = th;
          compression_ = compression;
          pixelFormat_ = pixelFormat;
          photometric_ = photometric;
          first = false;
        }
        else if (tw != tileWidth_ ||
                 th != tileHeight_ ||
                 compression_ != compression ||
                 pixelFormat_ != pixelFormat ||
                 photometric_ != photometric)
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat,
                                          "The tile size or compression of the TIFF file varies along levels, this is not supported");
        }

        levels_.push_back(Level(reader_.GetTiff(), pos, w, h));
      }

      pos++;
    }
    while (TIFFReadDirectory(reader_.GetTiff()));

    if (levels_.size() == 0)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat, "This is not a tiled TIFF image");
    }

    std::sort(levels_.begin(), levels_.end(), Comparator());
  }


  unsigned int HierarchicalTiff::GetLevelWidth(unsigned int level) const
  {
    CheckLevel(level);
    return levels_[level].width_;
  }


  unsigned int HierarchicalTiff::GetLevelHeight(unsigned int level) const
  {
    CheckLevel(level);
    return levels_[level].height_;
  }


  bool HierarchicalTiff::ReadRawTile(std::string& tile,
                                     ImageCompression& compression,
                                     unsigned int level,
                                     unsigned int tileX,
                                     unsigned int tileY)
  {
    boost::mutex::scoped_lock lock(mutex_);

    CheckLevel(level);

    compression = compression_;

    // Make the TIFF context point to the level of interest
    if (!TIFFSetDirectory(reader_.GetTiff(), levels_[level].directory_))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_CorruptedFile);
    }

    // Get the index of the tile
    ttile_t index = TIFFComputeTile(reader_.GetTiff(), tileX * tileWidth_, tileY * tileHeight_, 0 /*z*/, 0 /*sample*/);

    // Read the raw tile
    toff_t *sizes;
    if (!TIFFGetField(reader_.GetTiff(), TIFFTAG_TILEBYTECOUNTS, &sizes))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_CorruptedFile);
    }

    std::string raw;
    raw.resize(sizes[index]);

    tsize_t read = TIFFReadRawTile(reader_.GetTiff(), index, &raw[0], raw.size());
    if (read != static_cast<tsize_t>(sizes[index]))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_CorruptedFile);
    }

    const std::string& headers = levels_[level].headers_;

    // Possibly prepend the raw tile with the shared JPEG headers
    if (headers.empty() ||
        compression_ != ImageCompression_Jpeg)
    {
      tile.swap(raw);   // Same as "tile.assign(raw)", but optimizes memory
    }
    else
    {
      assert(compression_ == ImageCompression_Jpeg);

      // Check that the raw JPEG tile starts with the SOI (start-of-image) tag == FF D8
      if (raw.size() < 2 ||
          static_cast<uint8_t>(raw[0]) != 0xff ||
          static_cast<uint8_t>(raw[1]) != 0xd8)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_CorruptedFile);
      }

      if (photometric_ == Orthanc::PhotometricInterpretation_RGB &&
          pixelFormat_ == Orthanc::PixelFormat_RGB24)
      {
        /**
         * Insert an Adobe APP14 marker with the "transform" flag set
         * to value 0, which indicates to the JPEG decoder that
         * "3-channel images are assumed to be RGB". Section 18 of
         * "Supporting the DCT Filters in PostScript Level 2 -
         * Technical Note #5116":
         * https://stackoverflow.com/a/9658206/881731
         * https://docs.oracle.com/javase/6/docs/api/javax/imageio/metadata/doc-files/jpeg_metadata.html
         * https://www.pdfa.org/wp-content/uploads/2020/07/5116.DCT_Filter.pdf
         **/
        static const uint8_t APP14[] = {
          0xff, 0xee,  /* JPEG Marker for Adobe segment: http://www.ozhiker.com/electronics/pjmt/jpeg_info/app_segments.html */
          0x00, 0x0e,  /* Length (without the JPEG marker) == 0x0e == 14 bytes */
          0x41, 0x64, 0x6f, 0x62, 0x65, /* "Adobe" string in ASCII */
          0x00, 0x64,  /* Version == Two-byte DCTEncode/DCTDecode version number == 0x64 */
          0x80, 0x00,  /* Two-byte "flags0" 0x8000 bit: Encoder used Blend=1 downsampling */
          0x00, 0x00,  /* Two-byte "flags1": Set to zero */
          0x00         /* One-byte color transform code == 0  <== This is the important one */
        };
        assert(sizeof(APP14) == 16);

        tile.resize(headers.size() + sizeof(APP14) + raw.size() - 2);
        memcpy(&tile[0], &headers[0], headers.size());
        memcpy(&tile[0] + headers.size(), APP14, sizeof(APP14));
        memcpy(&tile[0] + headers.size() + sizeof(APP14), &raw[2], raw.size() - 2);
      }
      else
      {
        tile.resize(headers.size() + raw.size() - 2);
        memcpy(&tile[0], &headers[0], headers.size());
        memcpy(&tile[0] + headers.size(), &raw[2], raw.size() - 2);
      }
    }
    
    return true;
  }


  bool HierarchicalTiff::LookupImagedVolumeSize(double& width,
                                                double& height) const
  {
    static const char* const APERIO_DESCRIPTION = "Aperio ";
    static const char* const MPP = "MPP";

    bool found = false;

    for (size_t i = 0; i < levels_.size(); i++)
    {
      if (Orthanc::Toolbox::StartsWith(levels_[i].description_, APERIO_DESCRIPTION))
      {
        std::vector<std::string> tokens;
        Orthanc::Toolbox::TokenizeString(tokens, levels_[i].description_, '|');

        for (size_t j = 0; j < tokens.size(); j++)
        {
          std::vector<std::string> assignment;
          Orthanc::Toolbox::TokenizeString(assignment, tokens[j], '=');
          if (assignment.size() == 2)
          {
            const std::string key = Orthanc::Toolbox::StripSpaces(assignment[0]);
            const std::string value = Orthanc::Toolbox::StripSpaces(assignment[1]);

            double mpp;
            if (key == MPP &&
                Orthanc::SerializationToolbox::ParseDouble(mpp, value))
            {
              // In the lines below, remember to switch X/Y when going from physical to pixel coordinates!
              double thisHeight = static_cast<double>(levels_[i].width_) * mpp / 1000.0;
              double thisWidth = static_cast<double>(levels_[i].height_) * mpp / 1000.0;

              if (!found)
              {
                found = true;
                width = thisWidth;
                height = thisHeight;
              }
              else if (!ImageToolbox::IsNear(thisWidth, width) ||
                       !ImageToolbox::IsNear(thisHeight, height))
              {
                LOG(WARNING) << "Inconsistency in the Aperio metadata regarding the size of the imaged volume";
                return false;
              }
            }
          }
        }
      }
    }

    return found;
  }
}
