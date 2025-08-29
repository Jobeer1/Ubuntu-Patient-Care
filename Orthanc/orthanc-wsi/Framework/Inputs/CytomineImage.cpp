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


#include "CytomineImage.h"

#include <Compatibility.h>
#include <Images/ImageProcessing.h>
#include <Images/JpegReader.h>
#include <Images/JpegWriter.h>
#include <Images/PngReader.h>
#include <Logging.h>
#include <OrthancException.h>
#include <Toolbox.h>

#include <boost/date_time/posix_time/posix_time.hpp>
#include <boost/lexical_cast.hpp>
#include <openssl/hmac.h>


#if (OPENSSL_VERSION_NUMBER < 0x10100000L)
// OpenSSL < 1.1.0

namespace
{
  class HmacContext : public boost::noncopyable
  {
  private:
    HMAC_CTX hmac_;

  public:
    HmacContext()
    {
      HMAC_CTX_init(&hmac_);
    }

    ~HmacContext()
    {
      HMAC_CTX_cleanup(&hmac_);
    }

    HMAC_CTX* GetObject()
    {
      return &hmac_;
    }
  };
}

#else
// OpenSSL >= 1.1.0

namespace
{
  class HmacContext : public boost::noncopyable
  {
  private:
    HMAC_CTX* hmac_;

  public:
    HmacContext()
    {
      hmac_ = HMAC_CTX_new();
      if (hmac_ == NULL)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
      }
    }

    ~HmacContext()
    {
      HMAC_CTX_free(hmac_);
    }

    HMAC_CTX* GetObject()
    {
      return hmac_;
    }
  };
}

#endif


namespace OrthancWSI
{
  bool CytomineImage::GetCytomine(std::string& target,
                                  const std::string& uri,
                                  Orthanc::MimeType contentType) const
  {
    if (uri.empty() ||
        uri[0] == '/')
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }

    std::string t = Orthanc::EnumerationToString(contentType);
    
    std::string date;
    
    {
      const boost::posix_time::ptime now = boost::posix_time::second_clock::universal_time();

      std::stringstream stream;
      stream.imbue(std::locale(std::locale::classic(),
                               new boost::posix_time::time_facet("%a, %d %b %Y %H:%M:%S +0000")));
      stream << now;
      date = stream.str();
    }

    std::string auth;

    {
      const std::string token = "GET\n\n" + t + "\n" + date + "\n/" + uri;
  
      HmacContext hmac;

      unsigned char md[64];
      unsigned int length = 0;
      
      if (HMAC_Init_ex(hmac.GetObject(), privateKey_.c_str(), privateKey_.length(), EVP_sha1(), NULL) != 1 ||
          HMAC_Update(hmac.GetObject(), reinterpret_cast<const unsigned char*>(token.c_str()), token.size()) != 1 ||
          HMAC_Final(hmac.GetObject(), md, &length) != 1)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
      }

      Orthanc::Toolbox::EncodeBase64(auth, std::string(reinterpret_cast<const char*>(md), length));
    }

    Orthanc::HttpClient c(parameters_, uri);
    c.AddHeader("content-type", t);
    c.AddHeader("authorization", "CYTOMINE " + publicKey_ + ":" + auth);
    c.AddHeader("date", date);

    return c.Apply(target);
  }


  void CytomineImage::ReadRegion(Orthanc::ImageAccessor& target,
                                 bool& isEmpty,
                                 unsigned int level,
                                 unsigned int x,
                                 unsigned int y)
  {
    isEmpty = false;

    if (level != 0 ||
        x >= fullWidth_ ||
        y >= fullHeight_)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }

    unsigned int w = std::min(tileWidth_, fullWidth_ - x);
    unsigned int h = std::min(tileHeight_, fullHeight_ - y);

    std::string extension;
    Orthanc::MimeType mime;

    switch (compression_)
    {
      case ImageCompression_Png:
        extension = ".png";
        mime = Orthanc::MimeType_Png;
        break;
        
      case ImageCompression_Jpeg:
        // 20.03user 0.58system 0:32.58elapsed 63%CPU (0avgtext+0avgdata 397808maxresident)k
        extension = ".jpg";
        mime = Orthanc::MimeType_Jpeg;
        break;
        
      default:
        throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
    }
    
    const std::string uri = ("api/imageinstance/" + boost::lexical_cast<std::string>(imageId_) + "/window-" +
                             boost::lexical_cast<std::string>(x) + "-" +
                             boost::lexical_cast<std::string>(y) + "-" +
                             boost::lexical_cast<std::string>(w) + "-" +
                             boost::lexical_cast<std::string>(h) + extension);

    std::string compressedImage;
    if (!GetCytomine(compressedImage, uri, mime))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_NetworkProtocol, "Cannot read a tile from Cytomine");
    }

    std::unique_ptr<Orthanc::ImageAccessor> reader;

    switch (compression_)
    {
      case ImageCompression_Png:
        reader.reset(new Orthanc::PngReader);
        dynamic_cast<Orthanc::PngReader&>(*reader).ReadFromMemory(compressedImage);
        break;
        
      case ImageCompression_Jpeg:
        reader.reset(new Orthanc::JpegReader);
        dynamic_cast<Orthanc::JpegReader&>(*reader).ReadFromMemory(compressedImage);
        break;
        
      default:
        throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
    }

    assert(reader.get() != NULL);

    if (reader->GetWidth() != w ||
        reader->GetHeight() != h)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_NetworkProtocol, "Cytomine returned a tile of bad size");
    }

    Orthanc::ImageProcessing::Set(target, 255, 255, 255, 255);
    
    Orthanc::ImageAccessor region;
    target.GetRegion(region, 0, 0, w, h);

    Orthanc::ImageProcessing::Copy(target, *reader);
  }
  

  CytomineImage::CytomineImage(const Orthanc::WebServiceParameters& parameters,
                               const std::string& publicKey,
                               const std::string& privateKey,
                               int imageId,
                               unsigned int tileWidth,
                               unsigned int tileHeight) :
    parameters_(parameters),
    publicKey_(publicKey),
    privateKey_(privateKey),
    imageId_(imageId),
    tileWidth_(tileWidth),
    tileHeight_(tileHeight),
    compression_(ImageCompression_Jpeg)
  {
    if (tileWidth_ < 16 ||
        tileHeight_ < 16)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }

    std::string info;
    if (!GetCytomine(info, "api/imageinstance/" + boost::lexical_cast<std::string>(imageId_) + ".json", Orthanc::MimeType_Json))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_UnknownResource, "Inexistent image in Cytomine: " +
                                      boost::lexical_cast<std::string>(imageId));
    }

    const char* const WIDTH = "width";
    const char* const HEIGHT = "height";

    Json::Value json;
    if (!Orthanc::Toolbox::ReadJson(json, info) ||
        !json.isMember(WIDTH) ||
        !json.isMember(HEIGHT) ||
        json[WIDTH].type() != Json::intValue ||
        json[HEIGHT].type() != Json::intValue ||
        json[WIDTH].asInt() < 0 ||
        json[HEIGHT].asInt() < 0)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_NetworkProtocol, "Unsupported version of the Cytomine REST API");
    }

    fullWidth_ = json[WIDTH].asUInt();
    fullHeight_ = json[HEIGHT].asUInt();
    LOG(INFO) << "Reading an image of size " << fullWidth_ << "x" << fullHeight_ << " from Cytomine";
  }

  
  unsigned int CytomineImage::GetLevelWidth(unsigned int level) const
  {
    if (level == 0)
    {
      return fullWidth_;
    }
    else
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
  }

  
  unsigned int CytomineImage::GetLevelHeight(unsigned int level) const
  {
    if (level == 0)
    {
      return fullHeight_;
    }
    else
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
  }

  
  void CytomineImage::SetImageCompression(ImageCompression compression)
  {
    if (compression == ImageCompression_Jpeg ||
        compression == ImageCompression_Png)
    {
      compression_ = compression;
    }
    else
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
  }
}
