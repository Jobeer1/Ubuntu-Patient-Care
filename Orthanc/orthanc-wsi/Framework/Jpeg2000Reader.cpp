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
#include "Jpeg2000Reader.h"

#include "ImageToolbox.h"

#include <Compatibility.h>  // For std::unique_ptr
#include <Images/ImageProcessing.h>
#include <OrthancException.h>
#include <SystemToolbox.h>

#include <cassert>
#include <string.h>
#include <openjpeg.h>

#if ORTHANC_OPENJPEG_MAJOR_VERSION == 1
#  define OPJ_CLRSPC_GRAY CLRSPC_GRAY
#  define OPJ_CLRSPC_SRGB CLRSPC_SRGB
#  define OPJ_CODEC_J2K   CODEC_J2K
#  define OPJ_CODEC_JP2   CODEC_JP2
typedef opj_dinfo_t opj_codec_t;
typedef opj_cio_t opj_stream_t;
#elif ORTHANC_OPENJPEG_MAJOR_VERSION == 2
// OK, no need for compatibility macros
#else
#  error Unsupported version of OpenJpeg
#endif


namespace OrthancWSI
{
  namespace
  {
    // Check out opj_dparameters_t::decod_format
    enum InputFormat
    {
      InputFormat_J2K = 0,
      InputFormat_JP2 = 1,
      InputFormat_JPT = 2
    };

    enum OutputFormat
    {
#if ORTHANC_OPENJPEG_MAJOR_VERSION == 1
      OutputFormat_PGX = 1
#else
      OutputFormat_PGX = 11
#endif
    };

    class OpenJpegDecoder : public boost::noncopyable
    {
    private:
      opj_dparameters_t  parameters_;
      opj_codec_t* dinfo_;

      void SetupParameters(InputFormat format)
      {
        opj_set_default_decoder_parameters(&parameters_);

        parameters_.decod_format = format;
        parameters_.cod_format = OutputFormat_PGX;

#if OPENJPEG_MAJOR_VERSION == 1
        parameters_.cp_layer = 0;
        parameters_.cp_reduce = 0;
#endif
      }

      void Finalize()
      {
        if (dinfo_ != NULL)
        {
#if ORTHANC_OPENJPEG_MAJOR_VERSION == 1
          opj_destroy_decompress(dinfo_);
#else
          opj_destroy_codec(dinfo_);
#endif
          dinfo_ = NULL;
        }
      }

    public:
      explicit OpenJpegDecoder(Jpeg2000Format format) :
        dinfo_(NULL)
      {
        switch (format)
        {
          case Jpeg2000Format_J2K:
            SetupParameters(InputFormat_J2K);
            dinfo_ = opj_create_decompress(OPJ_CODEC_J2K);
            break;

          case Jpeg2000Format_JP2:
            SetupParameters(InputFormat_JP2);
            dinfo_ = opj_create_decompress(OPJ_CODEC_JP2);
            break;

          default:
            throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
        }

        if (!dinfo_)
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
        }

#if ORTHANC_OPENJPEG_MAJOR_VERSION == 1
        opj_setup_decoder(dinfo_, &parameters_);
#else
        if (!opj_setup_decoder(dinfo_, &parameters_))
        {
          Finalize();
          throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
        }
#endif
      }

      ~OpenJpegDecoder()
      {
        Finalize();
      } 

      opj_codec_t* GetObject()
      {
        return dinfo_;
      }

      const opj_dparameters_t& GetParameters() const
      {
        return parameters_;
      }
    };


    class OpenJpegInput : public boost::noncopyable
    {
    private:
      opj_stream_t* cio_;

      const uint8_t* buffer_;
      size_t         size_;
      size_t         position_;
      
#if ORTHANC_OPENJPEG_MAJOR_VERSION == 2
      static void Free(void *userData)
      {
      }

      static OPJ_SIZE_T Read(void *target, 
                             OPJ_SIZE_T size, 
                             void *userData)
      {
        OpenJpegInput& that = *reinterpret_cast<OpenJpegInput*>(userData);
        assert(that.position_ <= that.size_);
        assert(size >= 0);

        if (that.position_ == that.size_)
        {
          // End of file
          return -1;
        }
        else
        {
          if (that.position_ + size > that.size_)
          {
            size = that.size_ - that.position_;
          }

          if (size > 0)
          {
            memcpy(target, that.buffer_ + that.position_, size);
          }

          that.position_ += size;
          return size;
        }
      }
 
      static OPJ_OFF_T Skip(OPJ_OFF_T skip, 
                            void *userData)
      {
        assert(skip >= 0);
        OpenJpegInput& that = *reinterpret_cast<OpenJpegInput*>(userData);

        if (that.position_ == that.size_)
        {
          // End of file
          return -1;
        }
        else if (that.position_ + skip > that.size_)
        {
          size_t offset = that.size_ - that.position_;
          that.position_ = that.size_;
          return offset;
        }
        else
        {
          that.position_ += skip;
          return skip;
        }
      }
 
      static OPJ_BOOL Seek(OPJ_OFF_T position, 
                           void *userData)
      {
        assert(position >= 0);
        OpenJpegInput& that = *reinterpret_cast<OpenJpegInput*>(userData);
        
        if (static_cast<size_t>(position) > that.size_)
        {
          that.position_ = that.size_;
          return false;
        }
        else
        {
          that.position_ = position;
          return true;
        }
      }
#endif

    public:
      OpenJpegInput(OpenJpegDecoder& decoder,
                    const void* buffer,
                    size_t size) :
        buffer_(reinterpret_cast<const uint8_t*>(buffer)),
        size_(size),
        position_(0)
      {
#if ORTHANC_OPENJPEG_MAJOR_VERSION == 1
        cio_ = opj_cio_open(reinterpret_cast<opj_common_ptr>(decoder.GetObject()), 
                            reinterpret_cast<unsigned char*>(const_cast<void*>(buffer)),
                            size);
#else
        cio_ = opj_stream_create(size_, 1 /* input stream */);
        if (!cio_)
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
        }

        // http://openjpeg.narkive.com/zHqG2fMe/opj-stream-set-user-data-length
        // "I'd suggest to precise in the documentation that the skip
        // and read callback functions should return -1 on end of
        // stream, and the seek callback function should return false
        // on end of stream."

        opj_stream_set_user_data(cio_, this, Free);
        opj_stream_set_user_data_length(cio_, size);
        opj_stream_set_read_function(cio_, Read);
        opj_stream_set_skip_function(cio_, Skip);
        opj_stream_set_seek_function(cio_, Seek);
#endif
    }

      ~OpenJpegInput()
      {
        if (cio_)
        {
 #if ORTHANC_OPENJPEG_MAJOR_VERSION == 1
          opj_cio_close(cio_);
#else
          opj_stream_destroy(cio_);
#endif
          cio_ = NULL;
        }
      }

      opj_stream_t* GetObject()
      {
        return cio_;
      }
    };


    class OpenJpegImage
    {
    private:
      opj_image_t* image_;
      
      Orthanc::ImageAccessor* ExtractChannel(unsigned int channel)
      {
        const unsigned int width = image_->comps[channel].w;
        const unsigned int height = image_->comps[channel].h;
        
        std::unique_ptr<Orthanc::ImageAccessor> target(
          new Orthanc::Image(Orthanc::PixelFormat_Grayscale8, width, height, false));

        const int32_t* q = image_->comps[channel].data;
        assert(q != NULL);

        for (unsigned int y = 0; y < height; y++)
        {
          uint8_t *p = reinterpret_cast<uint8_t*>(target->GetRow(y));

          for (unsigned int x = 0; x < width; x++, p++, q++)
          {
            *p = *q;
          }
        }        

        return target.release();
      }
      
      void CopyChannel(Orthanc::ImageAccessor& target,
                       unsigned int channel,
                       unsigned int targetIncrement)
      {
        const unsigned int width = target.GetWidth();
        const unsigned int height = target.GetHeight();

        if (width == static_cast<unsigned int>(image_->comps[channel].w) &&
            height == static_cast<unsigned int>(image_->comps[channel].h))
        {
          const int32_t* q = image_->comps[channel].data;
          assert(q != NULL);

          for (unsigned int y = 0; y < height; y++)
          {
            uint8_t *p = reinterpret_cast<uint8_t*>(target.GetRow(y)) + channel;

            for (unsigned int x = 0; x < width; x++, p += targetIncrement)
            {
              *p = *q;
              q++;
            }
          }
        }
        else
        {
          // This component is subsampled
          std::unique_ptr<Orthanc::ImageAccessor> source(ExtractChannel(channel));
          Orthanc::Image resized(Orthanc::PixelFormat_Grayscale8, width, height, false);
          Orthanc::ImageProcessing::Resize(resized, *source);

          assert(resized.GetWidth() == target.GetWidth() &&
                 resized.GetHeight() == target.GetHeight() &&
                 resized.GetFormat() == Orthanc::PixelFormat_Grayscale8 &&
                 source->GetFormat() == Orthanc::PixelFormat_Grayscale8);            
          
          for (unsigned int y = 0; y < height; y++)
          {
            const uint8_t *q = reinterpret_cast<const uint8_t*>(resized.GetConstRow(y));
            uint8_t *p = reinterpret_cast<uint8_t*>(target.GetRow(y)) + channel;

            for (unsigned int x = 0; x < width; x++, p += targetIncrement)
            {
              *p = *q;
              q++;
            }
          }          
        }
      }

    public:
      OpenJpegImage(OpenJpegDecoder& decoder,
                    OpenJpegInput& input) :
        image_(NULL)
      {
#if ORTHANC_OPENJPEG_MAJOR_VERSION == 1
        image_ = opj_decode(decoder.GetObject(), input.GetObject());
        if (image_ == NULL)
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
        }
#else
        if (!opj_read_header(input.GetObject(), decoder.GetObject(), &image_) ||
            image_ == NULL)
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
        }

        if (!opj_set_decode_area(decoder.GetObject(), image_, 
                                 static_cast<int32_t>(decoder.GetParameters().DA_x0),
                                 static_cast<int32_t>(decoder.GetParameters().DA_y0),
                                 static_cast<int32_t>(decoder.GetParameters().DA_x1),
                                 static_cast<int32_t>(decoder.GetParameters().DA_y1)) ||  // Decode the whole image
            !opj_decode(decoder.GetObject(), input.GetObject(), image_) ||
            !opj_end_decompress(decoder.GetObject(), input.GetObject()))
        {
          opj_image_destroy(image_);
          throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
        }
#endif
      }

      ~OpenJpegImage()
      {
        if (image_ != NULL)
        {
          opj_image_destroy(image_);
          image_ = NULL;
        }
      }

      Orthanc::ImageAccessor* ProvideImage()
      {
        if (image_->x1 < 0 ||
            image_->y1 < 0)
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
        }

        if (image_->x0 != 0 ||
            image_->y0 != 0)
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
        }

        for (unsigned int c = 0; c < static_cast<unsigned int>(image_->numcomps); c++)
        {
          if (image_->comps[c].x0 != 0 ||
              image_->comps[c].y0 != 0 ||
              image_->comps[c].dx * image_->comps[c].w != image_->x1 ||
              image_->comps[c].dy * image_->comps[c].h != image_->y1 ||
              image_->comps[c].prec != 8 ||
              image_->comps[c].sgnd != 0)
          {
            throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
          }
        }

        unsigned int width = static_cast<unsigned int>(image_->x1);
        unsigned int height = static_cast<unsigned int>(image_->y1);

        Orthanc::PixelFormat format;
        if (image_->numcomps == 1 /*&& image_->color_space != OPJ_CLRSPC_GRAY*/)
        {
          format = Orthanc::PixelFormat_Grayscale8;
        }
        else if (image_->numcomps == 3 /*&& image_->color_space == OPJ_CLRSPC_SRGB*/)
        {
          format = Orthanc::PixelFormat_RGB24;
        }
        else
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
        }

        std::unique_ptr<Orthanc::ImageAccessor> image(ImageToolbox::Allocate(format, width, height));
        
        switch (format)
        {
          case Orthanc::PixelFormat_Grayscale8:
          {
            CopyChannel(*image, 0, 1);
            break;
          }

          case Orthanc::PixelFormat_RGB24:
          {
            CopyChannel(*image, 0, 3);
            CopyChannel(*image, 1, 3);
            CopyChannel(*image, 2, 3);
            break;
          }

          default:
            throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
        }

        return image.release();
      }
    };
  }


  void Jpeg2000Reader::ReadFromMemory(const void* buffer,
                                      size_t size)
  {
    OpenJpegDecoder decoder(DetectFormatFromMemory(buffer, size));
    OpenJpegInput input(decoder, buffer, size);
    OpenJpegImage image(decoder, input);
    
    image_.reset(image.ProvideImage());
    AssignWritable(image_->GetFormat(), 
                   image_->GetWidth(),
                   image_->GetHeight(), 
                   image_->GetPitch(), 
                   image_->GetBuffer());
  }


  void Jpeg2000Reader::ReadFromMemory(const std::string& buffer)
  {
    if (buffer.empty())
    {
      ReadFromMemory(NULL, 0);
    }
    else
    {
      ReadFromMemory(buffer.c_str(), buffer.size());
    }
  }

  void Jpeg2000Reader::ReadFromFile(const std::string& filename)
  {
    // TODO Use opj_stream_create_file_stream() ?

    std::string content;
    Orthanc::SystemToolbox::ReadFile(content, filename);
  }


  Jpeg2000Format Jpeg2000Reader::DetectFormatFromMemory(const void* buffer,
                                                        size_t size)
  {
    static const char JP2_RFC3745_HEADER[] = "\x00\x00\x00\x0c\x6a\x50\x20\x20\x0d\x0a\x87\x0a";
    static const char JP2_HEADER[] = "\x0d\x0a\x87\x0a";
    static const char J2K_HEADER[] = "\xff\x4f\xff\x51";

    if (size < sizeof(JP2_RFC3745_HEADER) - 1)
    {
      return Jpeg2000Format_Unknown;
    }
     
    if (memcmp(buffer, JP2_RFC3745_HEADER, sizeof(JP2_RFC3745_HEADER) - 1) == 0 || 
        memcmp(buffer, JP2_HEADER, sizeof(JP2_HEADER) - 1) == 0)
    {
      return Jpeg2000Format_JP2;
    }
    else if (memcmp(buffer, J2K_HEADER, sizeof(J2K_HEADER) - 1) == 0)
    {
      return Jpeg2000Format_J2K;
    }
    
    return Jpeg2000Format_Unknown;
  }
}
