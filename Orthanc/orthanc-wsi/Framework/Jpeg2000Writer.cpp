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
#include "Jpeg2000Writer.h"

#include <ChunkedBuffer.h>
#include <OrthancException.h>

#include <openjpeg.h>
#include <string.h>
#include <vector>

#if ORTHANC_OPENJPEG_MAJOR_VERSION == 1
#  define OPJ_CLRSPC_GRAY CLRSPC_GRAY
#  define OPJ_CLRSPC_SRGB CLRSPC_SRGB
#  define OPJ_CODEC_J2K   CODEC_J2K
typedef opj_cinfo_t opj_codec_t;
typedef opj_cio_t opj_stream_t;
#elif ORTHANC_OPENJPEG_MAJOR_VERSION == 2
#else
#error Unsupported version of OpenJpeg
#endif

namespace OrthancWSI
{
  namespace
  {
    class OpenJpegImage : public boost::noncopyable
    {
    private:
      std::vector<opj_image_cmptparm_t> components_;
      COLOR_SPACE colorspace_;
      opj_image_t* image_;

      void SetupComponents(unsigned int width,
                           unsigned int height,
                           Orthanc::PixelFormat format)
      {
        switch (format)
        {
          case Orthanc::PixelFormat_Grayscale8:
            colorspace_ = OPJ_CLRSPC_GRAY;
            components_.resize(1);
            break;

          case Orthanc::PixelFormat_RGB24:
            colorspace_ = OPJ_CLRSPC_SRGB;
            components_.resize(3);
            break;

          default:
            throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
        }

        for (size_t i = 0; i < components_.size(); i++)
        {
          memset(&components_[i], 0, sizeof(opj_image_cmptparm_t));
          components_[i].dx = 1;
          components_[i].dy = 1;
          components_[i].x0 = 0;
          components_[i].y0 = 0;
          components_[i].w = width;
          components_[i].h = height;
          components_[i].prec = 8;
          components_[i].bpp = 8;
          components_[i].sgnd = 0;
        }
      }

      void CopyRGB24(unsigned int width,
                     unsigned int height,
                     unsigned int pitch,
                     const void* buffer)
      {
        int32_t* r = image_->comps[0].data;
        int32_t* g = image_->comps[1].data;
        int32_t* b = image_->comps[2].data;

        for (unsigned int y = 0; y < height; y++)
        {
          const uint8_t *p = reinterpret_cast<const uint8_t*>(buffer) + y * pitch;

          for (unsigned int x = 0; x < width; x++)
          {
            *r = p[0];
            *g = p[1];
            *b = p[2];
            p += 3;
            r++;
            g++;
            b++;
          }
        }
      }

      void CopyGrayscale8(unsigned int width,
                          unsigned int height,
                          unsigned int pitch,
                          const void* buffer)
      {
        int32_t* q = image_->comps[0].data;

        for (unsigned int y = 0; y < height; y++)
        {
          const uint8_t *p = reinterpret_cast<const uint8_t*>(buffer) + y * pitch;

          for (unsigned int x = 0; x < width; x++)
          {
            *q = *p;
            p++;
            q++;
          }
        }        
      }

    public:
      OpenJpegImage(unsigned int width,
                    unsigned int height,
                    unsigned int pitch,
                    Orthanc::PixelFormat format,
                    const void* buffer) : image_(NULL)
      {
        SetupComponents(width, height, format);

        image_ = opj_image_create(components_.size(), &components_[0], colorspace_);
        if (!image_)
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
        }

        image_->x0 = 0;
        image_->y0 = 0;
        image_->x1 = width;
        image_->y1 = height;

        switch (format)
        {
          case Orthanc::PixelFormat_Grayscale8:
            CopyGrayscale8(width, height, pitch, buffer);
            break;

          case Orthanc::PixelFormat_RGB24:
            CopyRGB24(width, height, pitch, buffer);
            break;

          default:
            throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
        }
      }


      ~OpenJpegImage()
      {
        if (image_)
        {
          opj_image_destroy(image_);
          image_ = NULL;
        }
      }


      opj_image_t* GetObject()
      {
        return image_;
      }
    };


    class OpenJpegEncoder : public boost::noncopyable
    {
    private:
      opj_codec_t* cinfo_;

    public:
      OpenJpegEncoder(opj_cparameters_t& parameters,
                      OpenJpegImage& image) : cinfo_(NULL)
      {
        cinfo_ = opj_create_compress(OPJ_CODEC_J2K);
        if (!cinfo_)
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
        }

        opj_setup_encoder(cinfo_, &parameters, image.GetObject());
      }

      ~OpenJpegEncoder()
      {
        if (cinfo_ != NULL)
        {
#if ORTHANC_OPENJPEG_MAJOR_VERSION == 1
          opj_destroy_compress(cinfo_);
#else
          opj_destroy_codec(cinfo_);
#endif
          cinfo_ = NULL;
        }
      } 

      opj_codec_t* GetObject()
      {
        return cinfo_;
      }
    };


    class OpenJpegOutput : public boost::noncopyable
    {
    private:
      opj_stream_t* cio_;

#if ORTHANC_OPENJPEG_MAJOR_VERSION == 2
      Orthanc::ChunkedBuffer buffer_;

      static void Free(void *userData)
      {
      }

      static OPJ_SIZE_T Write(void *buffer, 
                              OPJ_SIZE_T size,
                              void *userData)
      {
        OpenJpegOutput* that = reinterpret_cast<OpenJpegOutput*>(userData);
        that->buffer_.AddChunk(reinterpret_cast<const char*>(buffer), size);
        return size;
      }
#endif

    public:
      explicit OpenJpegOutput(OpenJpegEncoder& encoder) :
        cio_(NULL)
      {
#if ORTHANC_OPENJPEG_MAJOR_VERSION == 1
        cio_ = opj_cio_open(reinterpret_cast<opj_common_ptr>(encoder.GetObject()), NULL, 0);
#else
        cio_ = opj_stream_default_create(0 /* output stream */);
        if (!cio_)
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
        }

        opj_stream_set_user_data(cio_, this, Free);
        opj_stream_set_write_function(cio_, Write);
#endif
      }

      ~OpenJpegOutput()
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

      void Flatten(std::string& target)
      {
#if ORTHANC_OPENJPEG_MAJOR_VERSION == 1
          target.assign(reinterpret_cast<const char*>(cio_->buffer), cio_tell(cio_));
#else
          buffer_.Flatten(target);
#endif
      }
    };
  }


  static void SetupParameters(opj_cparameters_t& parameters,
                              Orthanc::PixelFormat format,
                              bool isLossless)
  {
    opj_set_default_encoder_parameters(&parameters);
    parameters.cp_disto_alloc = 1;

    if (isLossless)
    {
      parameters.tcp_numlayers = 1;
      parameters.tcp_rates[0] = 0;
    }
    else
    {
      parameters.tcp_numlayers = 5;
      parameters.tcp_rates[0] = 1920;
      parameters.tcp_rates[1] = 480;
      parameters.tcp_rates[2] = 120;
      parameters.tcp_rates[3] = 30;
      parameters.tcp_rates[4] = 10;
      parameters.irreversible = 1;

      if (format == Orthanc::PixelFormat_RGB24 ||
          format == Orthanc::PixelFormat_RGBA32)
      {
        // This must be set to 1 if the number of color channels is >= 3
        parameters.tcp_mct = 1;
      }
    }

    parameters.cp_comment = const_cast<char*>("");
  }


  void Jpeg2000Writer::WriteToMemoryInternal(std::string& compressed,
                                             unsigned int width,
                                             unsigned int height,
                                             unsigned int pitch,
                                             Orthanc::PixelFormat format,
                                             const void* buffer)
  {
    if (format != Orthanc::PixelFormat_Grayscale8 &&
        format != Orthanc::PixelFormat_RGB24 &&
        format != Orthanc::PixelFormat_RGBA32)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }

    opj_cparameters_t parameters;
    SetupParameters(parameters, format, isLossless_);

    OpenJpegImage image(width, height, pitch, format, buffer);
    OpenJpegEncoder encoder(parameters, image);
    OpenJpegOutput output(encoder);

#if ORTHANC_OPENJPEG_MAJOR_VERSION == 1
    if (!opj_encode(encoder.GetObject(), output.GetObject(), image.GetObject(), parameters.index))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
    }
#else
    if (!opj_start_compress(encoder.GetObject(), image.GetObject(), output.GetObject()) ||
        !opj_encode(encoder.GetObject(), output.GetObject()) ||
        !opj_end_compress(encoder.GetObject(), output.GetObject()))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
    }
#endif

    output.Flatten(compressed);
  }
}
