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


#include "PrecompiledHeadersWSI.h"
#include "ImageToolbox.h"

#include "Jpeg2000Reader.h"
#include "Jpeg2000Writer.h"

#include <Compatibility.h>  // For std::unique_ptr
#include <OrthancException.h>
#include <Images/ImageProcessing.h>
#include <Images/PngReader.h>
#include <Images/PngWriter.h>
#include <Images/JpegReader.h>
#include <Images/JpegWriter.h>
#include <Logging.h>

#include <limits>
#include <string.h>
#include <memory>


namespace OrthancWSI
{
  namespace ImageToolbox
  {
    bool IsNear(double a,
                double b)
    {
      return IsNear(a, b, 10.0 * std::numeric_limits<float>::epsilon());
    }


    bool IsNear(double a,
                double b,
                double threshold)
    {
      return std::abs(a - b) < threshold;
    }


    Orthanc::ImageAccessor* Allocate(Orthanc::PixelFormat format,
                                     unsigned int width,
                                     unsigned int height)
    {
      return new Orthanc::Image(format, width, height, false);
    }


    void Embed(const Orthanc::ImageAccessor& target,
               const Orthanc::ImageAccessor& source,
               unsigned int x,
               unsigned int y)
    {
      if (target.GetFormat() != source.GetFormat())
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_IncompatibleImageFormat);
      }

      if (x >= target.GetWidth() ||
          y >= target.GetHeight())
      {
        return;
      }

      unsigned int h = std::min(source.GetHeight(), target.GetHeight() - y);
      unsigned int w = std::min(source.GetWidth(), target.GetWidth() - x);

      Orthanc::ImageAccessor targetRegion, sourceRegion;
      target.GetRegion(targetRegion, x, y, w, h);
      source.GetRegion(sourceRegion, 0, 0, w, h);
      
      Orthanc::ImageProcessing::Copy(targetRegion, sourceRegion);
    }



    void Set(Orthanc::ImageAccessor& image,
             uint8_t r,
             uint8_t g,
             uint8_t b)
    {
      switch (image.GetFormat())
      {
        case Orthanc::PixelFormat_Grayscale8:
        {
#if ORTHANC_FRAMEWORK_VERSION_IS_ABOVE(1, 9, 0)
          Orthanc::ImageProcessing::Set(image, r, g, b, 0 /* alpha is ignored */);
#else
          uint8_t grayscale = (2126 * static_cast<uint16_t>(r) + 
                               7152 * static_cast<uint16_t>(g) +
                               0722 * static_cast<uint16_t>(b)) / 10000;
          Orthanc::ImageProcessing::Set(image, grayscale);
#endif
          break;
        }

        case Orthanc::PixelFormat_RGB24:
          Orthanc::ImageProcessing::Set(image, r, g, b, 0 /* alpha is ignored */);
          break;

        default:
          throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
      }
    }


    Orthanc::ImageAccessor* DecodeTile(const std::string& source,
                                       ImageCompression compression)
    {
      switch (compression)
      {
        case ImageCompression_Png:
        {
          std::unique_ptr<Orthanc::PngReader> reader(new Orthanc::PngReader);
          reader->ReadFromMemory(source);
          return reader.release();
        }

        case ImageCompression_Jpeg:
        {
          std::unique_ptr<Orthanc::JpegReader> reader(new Orthanc::JpegReader);
          reader->ReadFromMemory(source);
          return reader.release();
        }

        case ImageCompression_Jpeg2000:
        {
          std::unique_ptr<Jpeg2000Reader> reader(new Jpeg2000Reader);
          reader->ReadFromMemory(source);
          return reader.release();
        }

        default:
          throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
      }
    }


    Orthanc::ImageAccessor* DecodeRawTile(const std::string& source,
                                          Orthanc::PixelFormat format,
                                          unsigned int width,
                                          unsigned int height)
    {
      unsigned int bpp = GetBytesPerPixel(format);

      if (bpp * width * height != source.size())
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_IncompatibleImageSize);
      }

      Orthanc::ImageAccessor accessor;
      accessor.AssignReadOnly(format, width, height, bpp * width, source.empty() ? NULL : source.c_str());

      return Orthanc::Image::Clone(accessor);
    }


    void EncodeUncompressedTile(std::string& target,
                                const Orthanc::ImageAccessor& source)
    {
      unsigned int pitch = GetBytesPerPixel(source.GetFormat()) * source.GetWidth();
      target.resize(pitch * source.GetHeight());

      const unsigned int height = source.GetHeight();
      for (unsigned int i = 0; i < height; i++)
      {
        memcpy(&target[i * pitch], source.GetConstRow(i), pitch);
      }
    }


    void EncodeTile(std::string& target,
                    const Orthanc::ImageAccessor& source,
                    ImageCompression compression,
                    uint8_t quality)
    {
      if (compression == ImageCompression_None)
      {
        EncodeUncompressedTile(target, source);
      }
      else
      {
        std::unique_ptr<Orthanc::IImageWriter> writer;

        switch (compression)
        {
          case ImageCompression_Png:
            writer.reset(new Orthanc::PngWriter);
            break;

          case ImageCompression_Jpeg:
            writer.reset(new Orthanc::JpegWriter);
            dynamic_cast<Orthanc::JpegWriter&>(*writer).SetQuality(quality);
            break;

          case ImageCompression_Jpeg2000:
            writer.reset(new Jpeg2000Writer);
            break;

          default:
            throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
        }

        Orthanc::IImageWriter::WriteToMemory(*writer, target, source);
      }
    }


    void ChangeTileCompression(std::string& target,
                               const std::string& source,
                               ImageCompression sourceCompression,
                               ImageCompression targetCompression,
                               uint8_t quality)
    {
      if (sourceCompression == targetCompression)
      {
        target = source;
      }
      else
      {
        std::unique_ptr<Orthanc::ImageAccessor> decoded(DecodeTile(source, sourceCompression));
        EncodeTile(target, *decoded, targetCompression, quality);
      }
    }


    Orthanc::ImageAccessor* Render(ITiledPyramid& pyramid,
                                   unsigned int level)
    {
      std::unique_ptr<Orthanc::ImageAccessor> result(Allocate(pyramid.GetPixelFormat(), 
                                                              pyramid.GetLevelWidth(level),
                                                              pyramid.GetLevelHeight(level)));

      LOG(INFO) << "Rendering a tiled image of size "
                << result->GetWidth() << "x" << result->GetHeight();

      const unsigned int width = result->GetWidth();
      const unsigned int height = result->GetHeight();
      
      for (unsigned int y = 0; y < height; y += pyramid.GetTileHeight(level))
      {
        for (unsigned int x = 0; x < width; x += pyramid.GetTileWidth(level))
        {
          bool isEmpty;  // Unused in this case
          std::unique_ptr<Orthanc::ImageAccessor> tile(
            pyramid.DecodeTile(isEmpty, level,
                               x / pyramid.GetTileWidth(level),
                               y / pyramid.GetTileHeight(level)));
          Embed(*result, *tile, x, y);
        }
      }

      return result.release();
    }


    void CheckConstantTileSize(const ITiledPyramid& source)
    {
      if (source.GetLevelCount() == 0)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_IncompatibleImageSize,
                                        "Input pyramid has no level");
      }
      else
      {
        for (unsigned int level = 0; level < source.GetLevelCount(); level++)
        {
          if (source.GetTileWidth(level) != source.GetTileWidth(0) ||
              source.GetTileHeight(level) != source.GetTileHeight(0))
          {
            throw Orthanc::OrthancException(Orthanc::ErrorCode_IncompatibleImageSize,
                                            "The DICOMizer requires that the input pyramid has constant "
                                            "tile sizes across all its levels, which is not the case");
          } 
        }
      }
    }


    void ConvertJpegYCbCrToRgb(Orthanc::ImageAccessor& image)
    {
#if defined(ORTHANC_FRAMEWORK_VERSION_IS_ABOVE) && ORTHANC_FRAMEWORK_VERSION_IS_ABOVE(1, 9, 0)
      Orthanc::ImageProcessing::ConvertJpegYCbCrToRgb(image);
#else
#  if defined(__GNUC__) || defined(__clang__)
#    warning You are using an old version of the Orthanc framework
#  endif
      const unsigned int width = image.GetWidth();
      const unsigned int height = image.GetHeight();
      const unsigned int pitch = image.GetPitch();
        
      if (image.GetFormat() != Orthanc::PixelFormat_RGB24 ||
          pitch < 3 * width)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_IncompatibleImageFormat);
      }

      for (unsigned int y = 0; y < height; y++)
      {
        uint8_t* p = reinterpret_cast<uint8_t*>(image.GetRow(y));
          
        for (unsigned int x = 0; x < width; x++, p += 3)
        {
          const float Y  = p[0];
          const float Cb = p[1];
          const float Cr = p[2];

          const float result[3] = {
            Y                             + 1.402f    * (Cr - 128.0f),
            Y - 0.344136f * (Cb - 128.0f) - 0.714136f * (Cr - 128.0f),
            Y + 1.772f    * (Cb - 128.0f)
          };

          for (uint8_t i = 0; i < 3 ; i++)
          {
            if (result[i] < 0)
            {
              p[i] = 0;
            }
            else if (result[i] > 255)
            {
              p[i] = 255;
            }
            else
            {
              p[i] = static_cast<uint8_t>(result[i]);
            }
          }    
        }
      }
#endif
    }


    ImageCompression Convert(Orthanc::MimeType type)
    {
      switch (type)
      {
        case Orthanc::MimeType_Png:
          return ImageCompression_Png;

        case Orthanc::MimeType_Jpeg:
          return ImageCompression_Jpeg;

        case Orthanc::MimeType_Jpeg2000:
          return ImageCompression_Jpeg2000;

        default:
          throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
      }
    }


    bool HasPngSignature(const std::string& buffer)
    {
      if (buffer.size() < 8)
      {
        return false;
      }
      else
      {
        // https://en.wikipedia.org/wiki/PNG#File_header
        // https://en.wikipedia.org/wiki/List_of_file_signatures
        const uint8_t* p = reinterpret_cast<const uint8_t*>(buffer.data());
        return (p[0] == 0x89 &&
                p[1] == 0x50 &&
                p[2] == 0x4e &&
                p[3] == 0x47 &&
                p[4] == 0x0d &&
                p[5] == 0x0a &&
                p[6] == 0x1a &&
                p[7] == 0x0a);
      }
    }


    bool HasJpegSignature(const std::string& buffer)
    {
      if (buffer.size() < 18)
      {
        return false;
      }
      else
      {
        // https://en.wikipedia.org/wiki/List_of_file_signatures
        const uint8_t* p = reinterpret_cast<const uint8_t*>(buffer.data());
        if (p[0] != 0xff ||
            p[1] != 0xd8 ||
            p[2] != 0xff)
        {
          return false;
        }

        // This is only a rough guess!
        return (p[3] == 0xdb ||
                p[3] == 0xe0 ||
                p[3] == 0xee ||
                p[3] == 0xe1);
      }
    }
  }
}
