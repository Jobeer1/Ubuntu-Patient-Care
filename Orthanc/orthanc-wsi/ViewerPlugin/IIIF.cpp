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


#include "../Framework/PrecompiledHeadersWSI.h"
#include "IIIF.h"

#include "DicomPyramidCache.h"
#include "RawTile.h"
#include "../Resources/Orthanc/Plugins/OrthancPluginCppWrapper.h"

#include <Images/Image.h>
#include <Images/ImageProcessing.h>
#include <Logging.h>
#include <SerializationToolbox.h>

#include <boost/math/special_functions/round.hpp>

#include "../Framework/Inputs/DecodedPyramidCache.h"


static const char* const ROWS = "0028,0010";
static const char* const COLUMNS = "0028,0011";


static std::string  iiifPublicUrl_;
static bool         iiifForcePowersOfTwoScaleFactors_ = false;


static void GeneratePyramidInfo(Json::Value& result,
                                const OrthancWSI::ITiledPyramid& pyramid,
                                const std::string& logName)
{
  if (pyramid.GetLevelCount() == 0)
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
  }

  if (pyramid.GetTileWidth(0) != pyramid.GetTileHeight(0))
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_IncompatibleImageFormat,
                                    "IIIF doesn't support non-isotropic tile sizes");
  }

  for (unsigned int i = 1; i < pyramid.GetLevelCount(); i++)
  {
    if (pyramid.GetTileWidth(i) != pyramid.GetTileWidth(0) ||
        pyramid.GetTileHeight(i) != pyramid.GetTileHeight(0))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_IncompatibleImageFormat,
                                      "IIIF doesn't support levels with varying tile sizes");
    }
  }

  Json::Value sizes = Json::arrayValue;
  Json::Value scaleFactors = Json::arrayValue;

  unsigned int power = 1;

  for (unsigned int i = 0; i < pyramid.GetLevelCount(); i++)
  {
    /**
     * According to the IIIF Image API 3.0 specification,
     * "scaleFactors" is: "The set of resolution scaling factors for
     * the image's predefined tiles, expressed as POSITIVE INTEGERS by
     * which to divide the full size of the image. For example, a
     * scale factor of 4 indicates that the service can efficiently
     * deliver images at 1/4 or 25% of the height and width of the
     * full image." => We can only serve the levels for which the full
     * width/height of the image is divisible by the width/height of
     * the level.
     **/
    if (pyramid.GetLevelWidth(0) % pyramid.GetLevelWidth(i) == 0 &&
        pyramid.GetLevelHeight(0) % pyramid.GetLevelHeight(i) == 0)
    {
      unsigned int scaleFactor = pyramid.GetLevelWidth(0) / pyramid.GetLevelWidth(i);

      if (!iiifForcePowersOfTwoScaleFactors_ ||
          scaleFactor == power)
      {
        Json::Value level;
        level["width"] = pyramid.GetLevelWidth(i);
        level["height"] = pyramid.GetLevelHeight(i);
        sizes.append(level);

        scaleFactors.append(scaleFactor);

        power *= 2;
      }
      else
      {
        LOG(WARNING) << "IIIF - Dropping level " << i << " of " << logName
                     << ", as it doesn't follow the powers-of-two pattern";
      }
    }
    else
    {
      LOG(WARNING) << "IIIF - Dropping level " << i << " of " << logName
                   << ", as the full width/height ("
                   << pyramid.GetLevelWidth(0) << "x" << pyramid.GetLevelHeight(0)
                   << ") of the image is not an integer multiple of the level width/height ("
                   << pyramid.GetLevelWidth(i) << "x" << pyramid.GetLevelHeight(i) << ")";
    }
  }

  /**
   * Reversing the order of the "sizes" field seems to be necessary
   * for recent version of OpenSeadragon (>= 4.1.0) and Mirador (>=
   * 4.0.0). This fix was included in release 2.1 of the WSI plugin.
   * https://github.com/openseadragon/openseadragon/issues/2379
   **/
  Json::Value reversedSizes = Json::arrayValue;
  for (Json::Value::ArrayIndex i = sizes.size(); i > 0; i--)
  {
    reversedSizes.append(sizes[i - 1]);
  }

  Json::Value tiles;
  tiles["width"] = pyramid.GetTileWidth(0);
  tiles["height"] = pyramid.GetTileHeight(0);
  tiles["scaleFactors"] = scaleFactors;

  result = Json::objectValue;
  result["@context"] = "http://iiif.io/api/image/3/context.json";
  result["profile"] = "level0";
  result["protocol"] = "http://iiif.io/api/image";
  result["type"] = "ImageService3";

  result["width"] = pyramid.GetLevelWidth(0);
  result["height"] = pyramid.GetLevelHeight(0);
  result["sizes"] = reversedSizes;
  result["tiles"].append(tiles);
}


void ServeIIIFSeriesPyramidInfo(OrthancPluginRestOutput* output,
                                const char* url,
                                const OrthancPluginHttpRequest* request)
{
  const std::string seriesId(request->groups[0]);

  LOG(INFO) << "IIIF: Image API call to whole-slide pyramid of series " << seriesId;

  Json::Value result;

  {
    OrthancWSI::DicomPyramidCache::Locker locker(seriesId);
    GeneratePyramidInfo(result, locker.GetPyramid(), "series " + seriesId);
  }

  result["id"] = iiifPublicUrl_ + "tiles/" + seriesId;

  std::string s = result.toStyledString();
  OrthancPluginAnswerBuffer(OrthancPlugins::GetGlobalContext(), output, s.c_str(), s.size(), Orthanc::EnumerationToString(Orthanc::MimeType_Json));
}


namespace
{
  class RegionParameters
  {
  private:
    bool        isFull_;
    uint32_t    x_;
    uint32_t    y_;
    uint32_t    regionWidth_;
    uint32_t    regionHeight_;
    uint32_t    cropWidth_;
    uint32_t    cropHeight_;

    void CheckNotFull() const
    {
      if (isFull_)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
      }
    }

  public:
    RegionParameters(const std::string& region,
                     const std::string& size,
                     const std::string& rotation,
                     const std::string& quality,
                     const std::string& format) :
      isFull_(true),
      x_(0),
      y_(0),
      regionWidth_(0),
      regionHeight_(0),
      cropWidth_(0),
      cropHeight_(0)
    {
      if (rotation != "0")
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented, "IIIF - Unsupported rotation: " + rotation);
      }

      if (quality != "default")
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented, "IIIF - Unsupported quality: " + quality);
      }

      if (format != "jpg")
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented, "IIIF - Unsupported format: " + format);
      }

      if (region == "full")
      {
        isFull_ = true;
      }
      else
      {
        isFull_ = false;

        std::vector<std::string> tokens;
        Orthanc::Toolbox::TokenizeString(tokens, region, ',');

        if (tokens.size() != 4 ||
            !Orthanc::SerializationToolbox::ParseUnsignedInteger32(x_, tokens[0]) ||
            !Orthanc::SerializationToolbox::ParseUnsignedInteger32(y_, tokens[1]) ||
            !Orthanc::SerializationToolbox::ParseUnsignedInteger32(regionWidth_, tokens[2]) ||
            !Orthanc::SerializationToolbox::ParseUnsignedInteger32(regionHeight_, tokens[3]))
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented, "IIIF - Invalid (x,y,width,height) region, found: " + region);
        }

        Orthanc::Toolbox::TokenizeString(tokens, size, ',');

        bool ok = false;
        if (tokens.size() == 2 &&
            Orthanc::SerializationToolbox::ParseUnsignedInteger32(cropWidth_, tokens[0]))
        {
          if (tokens[1].empty())
          {
            cropHeight_ = cropWidth_;
            ok = true;
          }
          else if (Orthanc::SerializationToolbox::ParseUnsignedInteger32(cropHeight_, tokens[1]))
          {
            ok = true;
          }
        }

        if (!ok)
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented, "IIIF - Invalid (width,height) crop, found: " + size);
        }
      }
    }

    bool IsFull() const
    {
      return isFull_;
    }

    uint32_t GetX() const
    {
      CheckNotFull();
      return x_;
    }

    uint32_t GetY() const
    {
      CheckNotFull();
      return y_;
    }

    uint32_t GetRegionWidth() const
    {
      CheckNotFull();
      return regionWidth_;
    }

    uint32_t GetRegionHeight() const
    {
      CheckNotFull();
      return regionHeight_;
    }

    uint32_t GetCropWidth() const
    {
      CheckNotFull();
      return cropWidth_;
    }

    uint32_t GetCropHeight() const
    {
      CheckNotFull();
      return cropHeight_;
    }
  };


  class RegionRenderer : public boost::noncopyable
  {
  private:
    RegionParameters                         parameters_;
    std::unique_ptr<OrthancWSI::RawTile>     rawTile_;
    std::unique_ptr<Orthanc::ImageAccessor>  toCrop_;

    static unsigned int GetPhysicalTileWidth(const OrthancWSI::ITiledPyramid& pyramid,
                                             unsigned int level)
    {
      return static_cast<unsigned int>(boost::math::iround(static_cast<float>(pyramid.GetTileWidth(level)) *
                                                           static_cast<float>(pyramid.GetLevelWidth(0)) /
                                                           static_cast<float>(pyramid.GetLevelWidth(level))));
    }

    static unsigned int GetPhysicalTileHeight(const OrthancWSI::ITiledPyramid& pyramid,
                                              unsigned int level)
    {
      return static_cast<unsigned int>(boost::math::iround(static_cast<float>(pyramid.GetTileHeight(level)) *
                                                           static_cast<float>(pyramid.GetLevelHeight(0)) /
                                                           static_cast<float>(pyramid.GetLevelHeight(level))));
    }

  public:
    RegionRenderer(const RegionParameters& parameters,
                   OrthancWSI::ITiledPyramid& pyramid) :
      parameters_(parameters)
    {
      unsigned int level;
      for (level = 0; level < pyramid.GetLevelCount(); level++)
      {
        const unsigned int physicalTileWidth = GetPhysicalTileWidth(pyramid, level);
        const unsigned int physicalTileHeight = GetPhysicalTileHeight(pyramid, level);

        if (parameters.GetX() % physicalTileWidth == 0 &&
            parameters.GetY() % physicalTileHeight == 0 &&
            parameters.GetRegionWidth() <= physicalTileWidth &&
            parameters.GetRegionHeight() <= physicalTileHeight &&
            parameters.GetX() + parameters.GetRegionWidth() <= pyramid.GetLevelWidth(0) &&
            parameters.GetY() + parameters.GetRegionHeight() <= pyramid.GetLevelHeight(0))
        {
          break;
        }
      }

      if (level == pyramid.GetLevelCount())
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_BadRequest, "IIIF - Cannot locate the level of interest");
      }
      else if (parameters.GetCropWidth() > pyramid.GetTileWidth(level))
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_BadRequest, "IIIF - Request for a cropping that is too large for the tile size");
      }
      else
      {
        const unsigned int tileX = parameters.GetX() / GetPhysicalTileWidth(pyramid, level);
        const unsigned int tileY = parameters.GetY() / GetPhysicalTileHeight(pyramid, level);
        rawTile_.reset(new OrthancWSI::RawTile(pyramid, level, tileX, tileY));

        if (rawTile_->IsEmpty())
        {
          bool isEmpty;
          toCrop_.reset(pyramid.DecodeTile(isEmpty, level, tileX, tileY));
          if (isEmpty)
          {
            toCrop_.reset(NULL);
          }
          else
          {
            rawTile_.reset(NULL);
          }
        }
        else
        {
          assert(rawTile_->GetTileWidth() == pyramid.GetTileWidth(level));
          assert(rawTile_->GetTileHeight() == pyramid.GetTileHeight(level));

          if (!rawTile_->IsEmpty() &&
              (parameters.GetCropWidth() < pyramid.GetTileWidth(level) ||
               parameters.GetCropHeight() < pyramid.GetTileHeight(level)))
          {
            toCrop_.reset(rawTile_->Decode());
            rawTile_.reset(NULL);
          }
        }
      }
    }

    void Answer(OrthancPluginRestOutput* output)
    {
      if (rawTile_.get() != NULL)
      {
        assert(toCrop_.get() == NULL);

        if (rawTile_->IsEmpty())
        {
          if (parameters_.GetCropWidth() < rawTile_->GetTileWidth() ||
              parameters_.GetCropHeight() < rawTile_->GetTileHeight())
          {
            OrthancWSI::RawTile::AnswerBackgroundTile(output, parameters_.GetCropWidth(), parameters_.GetCropHeight());
          }
          else
          {
            OrthancWSI::RawTile::AnswerBackgroundTile(output, rawTile_->GetTileWidth(), rawTile_->GetTileHeight());
          }
        }
        else
        {
          // Level 0 Compliance of IIIF expects JPEG files
          rawTile_->Answer(output, Orthanc::MimeType_Jpeg);
        }
      }
      else if (toCrop_.get() != NULL)
      {
        assert(rawTile_.get() == NULL);

        if (parameters_.GetCropWidth() > toCrop_->GetWidth() ||
            parameters_.GetCropHeight() > toCrop_->GetHeight())
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_BadRequest, "IIIF - Asking to crop outside of the tile size");
        }

        Orthanc::ImageAccessor cropped;
        toCrop_->GetRegion(cropped, 0, 0, parameters_.GetCropWidth(), parameters_.GetCropHeight());

        std::string encoded;
        OrthancWSI::RawTile::Encode(encoded, cropped, Orthanc::MimeType_Jpeg);

        OrthancPluginAnswerBuffer(OrthancPlugins::GetGlobalContext(), output, encoded.c_str(),
                                  encoded.size(), Orthanc::EnumerationToString(Orthanc::MimeType_Jpeg));
      }
      else
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
      }
    }
  };
}


static Orthanc::ImageAccessor* RenderFullImage(OrthancWSI::ITiledPyramid& pyramid)
{
  const unsigned int level = pyramid.GetLevelCount() - 1;

  std::unique_ptr<Orthanc::ImageAccessor> full(new Orthanc::Image(Orthanc::PixelFormat_RGB24, pyramid.GetLevelWidth(level), pyramid.GetLevelHeight(level), false));
  Orthanc::ImageProcessing::Set(*full, 255, 255, 255, 0);

  const unsigned int nx = OrthancWSI::CeilingDivision(pyramid.GetLevelWidth(level), pyramid.GetTileWidth(level));
  const unsigned int ny = OrthancWSI::CeilingDivision(pyramid.GetLevelHeight(level), pyramid.GetTileHeight(level));
  for (unsigned int ty = 0; ty < ny; ty++)
  {
    const unsigned int y = ty * pyramid.GetTileHeight(level);
    const unsigned int height = std::min(pyramid.GetTileHeight(level), full->GetHeight() - y);

    for (unsigned int tx = 0; tx < nx; tx++)
    {
      const unsigned int x = tx * pyramid.GetTileWidth(level);

      bool isEmpty;  // Unused
      std::unique_ptr<Orthanc::ImageAccessor> tile(pyramid.DecodeTile(isEmpty, level, tx, ty));

      const unsigned int width = std::min(pyramid.GetTileWidth(level), full->GetWidth() - x);

      Orthanc::ImageAccessor source, target;
      tile->GetRegion(source, 0, 0, width, height);
      full->GetRegion(target, x, y, width, height);

      Orthanc::ImageProcessing::Copy(target, source);
    }
  }

  return full.release();
}


void ServeIIIFTiledImageTile(OrthancPluginRestOutput* output,
                             const char* url,
                             const OrthancPluginHttpRequest* request)
{
  const std::string seriesId(request->groups[0]);
  const std::string region(request->groups[1]);
  const std::string size(request->groups[2]);
  const std::string rotation(request->groups[3]);
  const std::string quality(request->groups[4]);
  const std::string format(request->groups[5]);

  LOG(INFO) << "IIIF: Image API call to tile of series " << seriesId << ": "
            << "region=" << region << "; size=" << size << "; rotation="
            << rotation << "; quality=" << quality << "; format=" << format;

  const RegionParameters parameters(region, size, rotation, quality, format);

  if (parameters.IsFull())
  {
    std::unique_ptr<Orthanc::ImageAccessor> image;

    {
      OrthancWSI::DicomPyramidCache::Locker locker(seriesId);
      image.reset(RenderFullImage(locker.GetPyramid()));
    }

    std::string encoded;
    OrthancWSI::RawTile::Encode(encoded, *image, Orthanc::MimeType_Jpeg);

    OrthancPluginAnswerBuffer(OrthancPlugins::GetGlobalContext(), output, encoded.c_str(),
                              encoded.size(), Orthanc::EnumerationToString(Orthanc::MimeType_Jpeg));
  }
  else
  {
    std::unique_ptr<RegionRenderer> renderer;

    {
      OrthancWSI::DicomPyramidCache::Locker locker(seriesId);
      renderer.reset(new RegionRenderer(parameters, locker.GetPyramid()));
    }

    renderer->Answer(output);
  }
}


static void AddCanvas(Json::Value& manifest,
                      const std::string& resourceBase,
                      const std::string& imageService,
                      unsigned int page,
                      unsigned int width,
                      unsigned int height,
                      const std::string& description)
{
  const std::string base = iiifPublicUrl_ + resourceBase;

  Json::Value service;
  service["id"] = iiifPublicUrl_ + imageService;
  service["profile"] = "level0";
  service["type"] = "ImageService3";

  Json::Value body;
  body["id"] = iiifPublicUrl_ + imageService + "/full/max/0/default.jpg";
  body["type"] = "Image";
  body["format"] = Orthanc::EnumerationToString(Orthanc::MimeType_Jpeg);
  body["height"] = height;
  body["width"] = width;
  body["service"].append(service);

  Json::Value annotation;
  annotation["id"] = base + "/annotation/p" + boost::lexical_cast<std::string>(page) + "-image";
  annotation["type"] = "Annotation";
  annotation["motivation"] = "painting";
  annotation["body"] = body;
  annotation["target"] = base + "/canvas/p" + boost::lexical_cast<std::string>(page);

  Json::Value annotationPage;
  annotationPage["id"] = base + "/page/p" + boost::lexical_cast<std::string>(page) + "/1";
  annotationPage["type"] = "AnnotationPage";
  annotationPage["items"].append(annotation);

  Json::Value canvas;
  canvas["id"] = annotation["target"];
  canvas["type"] = "Canvas";
  canvas["width"] = width;
  canvas["height"] = height;
  canvas["label"]["en"].append(description);
  canvas["items"].append(annotationPage);

  manifest["items"].append(canvas);
}


static std::string GetTagValue(const Json::Value& tags,
                               const std::string& key)
{
  if (tags.isMember(key))
  {
    return tags[key].asString();
  }
  else
  {
    return "";
  }
}


static void FillManifest(Json::Value& manifest,
                         const std::string& base,
                         const Json::Value& study,
                         const Json::Value& series)
{
  static const char* const MAIN_DICOM_TAGS = "MainDicomTags";

  manifest["@context"] = "http://iiif.io/api/presentation/3/context.json";
  manifest["id"] = base + "/manifest.json";
  manifest["type"] = "Manifest";
  manifest["label"]["en"].append(GetTagValue(study[MAIN_DICOM_TAGS], "StudyDate") + " - " +
                                 GetTagValue(series[MAIN_DICOM_TAGS], "Modality") + " - " +
                                 GetTagValue(study[MAIN_DICOM_TAGS], "StudyDescription") + " - " +
                                 GetTagValue(series[MAIN_DICOM_TAGS], "SeriesDescription"));
}


void ServeIIIFManifest(OrthancPluginRestOutput* output,
                       const char* url,
                       const OrthancPluginHttpRequest* request)
{
  static const char* const KEY_INSTANCES = "Instances";
  static const char* const SOP_CLASS_UID = "0008,0016";
  static const char* const SLICES_SHORT = "SlicesShort";

  const std::string seriesId(request->groups[0]);

  LOG(INFO) << "IIIF: Presentation API call to series " << seriesId;

  Json::Value study, series;
  if (!OrthancPlugins::RestApiGet(series, "/series/" + seriesId, false) ||
      !OrthancPlugins::RestApiGet(study, "/series/" + seriesId + "/study", false))
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_UnknownResource);
  }

  if (study.type() != Json::objectValue ||
      series.type() != Json::objectValue ||
      !series.isMember(KEY_INSTANCES) ||
      series[KEY_INSTANCES].type() != Json::arrayValue ||
      series[KEY_INSTANCES].size() == 0u ||
      series[KEY_INSTANCES][0].type() != Json::stringValue)
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
  }

  Json::Value oneInstance;
  if (!OrthancPlugins::RestApiGet(oneInstance, "/instances/" + series[KEY_INSTANCES][0].asString() + "/tags?short", false) ||
      oneInstance.type() != Json::objectValue ||
      !oneInstance.isMember(SOP_CLASS_UID) ||
      oneInstance[SOP_CLASS_UID].type() != Json::stringValue)
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_UnknownResource);
  }

  const std::string sopClassUid = Orthanc::Toolbox::StripSpaces(oneInstance[SOP_CLASS_UID].asString());

  Json::Value manifest;
  FillManifest(manifest, iiifPublicUrl_ + "series/" + seriesId, study, series);

  if (sopClassUid == OrthancWSI::VL_WHOLE_SLIDE_MICROSCOPY_IMAGE_STORAGE_IOD)
  {
    /**
     * This is based on IIIF cookbook: "Support Deep Viewing with Basic
     * Use of a IIIF Image Service."
     * https://iiif.io/api/cookbook/recipe/0005-image-service/
     **/
    unsigned int width, height;

    {
      OrthancWSI::DicomPyramidCache::Locker locker(seriesId);
      width = locker.GetPyramid().GetLevelWidth(0);
      height = locker.GetPyramid().GetLevelHeight(0);
    }

    AddCanvas(manifest, seriesId, "tiles/" + seriesId, 1, width, height, "");
  }
  else
  {
    /**
     * This is based on IIIF cookbook: "Simple Manifest - Book"
     * https://iiif.io/api/cookbook/recipe/0009-book-1/
     **/

    manifest["behavior"].append("individuals");

    uint32_t width, height;
    if (!oneInstance.isMember(COLUMNS) ||
        !oneInstance.isMember(ROWS) ||
        oneInstance[COLUMNS].type() != Json::stringValue ||
        oneInstance[ROWS].type() != Json::stringValue ||
        !Orthanc::SerializationToolbox::ParseFirstUnsignedInteger32(width, oneInstance[COLUMNS].asString()) ||
        !Orthanc::SerializationToolbox::ParseFirstUnsignedInteger32(height, oneInstance[ROWS].asString()))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_UnknownResource);
    }

    Json::Value orderedSlices;
    if (!OrthancPlugins::RestApiGet(orderedSlices, "/series/" + seriesId + "/ordered-slices", false))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_UnknownResource);
    }

    if (orderedSlices.type() != Json::objectValue ||
        !orderedSlices.isMember(SLICES_SHORT) ||
        orderedSlices[SLICES_SHORT].type() != Json::arrayValue)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
    }

    const Json::Value& slicesShort = orderedSlices[SLICES_SHORT];

    unsigned int page = 1;
    for (Json::ArrayIndex instance = 0; instance < slicesShort.size(); instance++)
    {
      if (slicesShort[instance].type() != Json::arrayValue ||
          slicesShort[instance].size() != 3u ||
          slicesShort[instance][0].type() != Json::stringValue ||
          slicesShort[instance][1].type() != Json::intValue ||
          slicesShort[instance][2].type() != Json::intValue)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
      }

      const std::string instanceId = slicesShort[instance][0].asString();
      const unsigned int start = slicesShort[instance][1].asUInt();
      const unsigned int count = slicesShort[instance][2].asUInt();

      for (unsigned int frame = start; frame < start + count; frame++, page++)
      {
        AddCanvas(manifest, instanceId, "frames/" + instanceId + "/" + boost::lexical_cast<std::string>(frame),
                  page, width, height, "");
      }
    }
  }

  std::string s = manifest.toStyledString();
  OrthancPluginAnswerBuffer(OrthancPlugins::GetGlobalContext(), output, s.c_str(), s.size(), Orthanc::EnumerationToString(Orthanc::MimeType_Json));
}


void ServeIIIFFrameInfo(OrthancPluginRestOutput* output,
                        const char* url,
                        const OrthancPluginHttpRequest* request)
{
  const std::string instanceId(request->groups[0]);
  const std::string frame(request->groups[1]);

  LOG(INFO) << "IIIF: Image API call to manifest of instance " << instanceId << " at frame " << frame;

  Json::Value instance;
  if (!OrthancPlugins::RestApiGet(instance, "/instances/" + instanceId + "/tags?short", false))
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_UnknownResource);
  }

  uint32_t width, height;
  if (!instance.isMember(COLUMNS) ||
      !instance.isMember(ROWS) ||
      instance[COLUMNS].type() != Json::stringValue ||
      instance[ROWS].type() != Json::stringValue ||
      !Orthanc::SerializationToolbox::ParseFirstUnsignedInteger32(width, instance[COLUMNS].asString()) ||
      !Orthanc::SerializationToolbox::ParseFirstUnsignedInteger32(height, instance[ROWS].asString()))
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_UnknownResource);
  }

  Json::Value tile;
  tile["height"] = height;
  tile["width"] = width;
  tile["scaleFactors"].append(1);

  Json::Value result;
  result["@context"] = "http://iiif.io/api/image/3/context.json";
  result["profile"] = "level0";
  result["protocol"] = "http://iiif.io/api/image";
  result["type"] = "ImageService3";

  result["id"] = iiifPublicUrl_ + "frames/" + instanceId + "/" + frame;
  result["width"] = width;
  result["height"] = height;
  result["tiles"].append(tile);

  std::string s = result.toStyledString();
  OrthancPluginAnswerBuffer(OrthancPlugins::GetGlobalContext(), output, s.c_str(), s.size(), Orthanc::EnumerationToString(Orthanc::MimeType_Json));
}


void ServeIIIFFrameImage(OrthancPluginRestOutput* output,
                         const char* url,
                         const OrthancPluginHttpRequest* request)
{
  const std::string instanceId(request->groups[0]);
  const std::string frame(request->groups[1]);

  LOG(INFO) << "IIIF: Image API call to JPEG of instance " << instanceId << " at frame " << frame;

  std::map<std::string, std::string> httpHeaders;
  httpHeaders["Accept"] = Orthanc::EnumerationToString(Orthanc::MimeType_Jpeg);

  std::string jpeg;
  if (!OrthancPlugins::RestApiGetString(jpeg, "/instances/" + instanceId + "/frames/" + frame + "/preview", httpHeaders, false))
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_UnknownResource);
  }

  OrthancPluginAnswerBuffer(OrthancPlugins::GetGlobalContext(), output, jpeg.empty() ? NULL : jpeg.c_str(),
                            jpeg.size(), Orthanc::EnumerationToString(Orthanc::MimeType_Jpeg));
}


void ServeIIIFFramePyramidManifest(OrthancPluginRestOutput* output,
                                   const char* url,
                                   const OrthancPluginHttpRequest* request)
{
  const std::string instanceId(request->groups[0]);

  unsigned int frameNumber;
  if (!Orthanc::SerializationToolbox::ParseUnsignedInteger32(frameNumber, request->groups[1]))
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_UnknownResource);
  }

  LOG(INFO) << "IIIF: Presentation API call to frame " << frameNumber << " of instance " << instanceId;

  Json::Value instance, study, series;
  if (!OrthancPlugins::RestApiGet(instance, "/instances/" + instanceId, false) ||
      !OrthancPlugins::RestApiGet(series, "/instances/" + instanceId + "/series", false) ||
      !OrthancPlugins::RestApiGet(study, "/instances/" + instanceId + "/study", false))
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_UnknownResource);
  }

  if (instance.type() != Json::objectValue ||
      series.type() != Json::objectValue ||
      study.type() != Json::objectValue)
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
  }

  const std::string resourceBase = "frames-pyramids/" + instanceId + "/" + boost::lexical_cast<std::string>(frameNumber);

  Json::Value manifest;
  FillManifest(manifest, iiifPublicUrl_ + resourceBase, study, series);

  /**
   * This is based on IIIF cookbook: "Support Deep Viewing with Basic
   * Use of a IIIF Image Service."
   * https://iiif.io/api/cookbook/recipe/0005-image-service/
   **/
  unsigned int width, height;

  {
    OrthancWSI::DecodedPyramidCache::Accessor accessor(OrthancWSI::DecodedPyramidCache::GetInstance(), instanceId, frameNumber);
    width = accessor.GetPyramid().GetLevelWidth(0);
    height = accessor.GetPyramid().GetLevelHeight(0);
  }

  AddCanvas(manifest, resourceBase, resourceBase, 1, width, height, "");

  std::string s = manifest.toStyledString();
  OrthancPluginAnswerBuffer(OrthancPlugins::GetGlobalContext(), output, s.c_str(), s.size(), Orthanc::EnumerationToString(Orthanc::MimeType_Json));
}


void ServeIIIFFramePyramidInfo(OrthancPluginRestOutput* output,
                               const char* url,
                               const OrthancPluginHttpRequest* request)
{
  const std::string instanceId(request->groups[0]);
  unsigned int frameNumber;
  if (!Orthanc::SerializationToolbox::ParseUnsignedInteger32(frameNumber, request->groups[1]))
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_UnknownResource);
  }

  LOG(INFO) << "IIIF: Image API call to whole-slide pyramid of frame " << frameNumber << " of instance " << instanceId;

  Json::Value result;

  {
    OrthancWSI::DecodedPyramidCache::Accessor accessor(OrthancWSI::DecodedPyramidCache::GetInstance(), instanceId, frameNumber);
    GeneratePyramidInfo(result, accessor.GetPyramid(), "instance " + instanceId + " (frame " + boost::lexical_cast<std::string>(frameNumber) + ")");
  }

  result["id"] = iiifPublicUrl_ + "frames-pyramids/" + instanceId + "/" + boost::lexical_cast<std::string>(frameNumber);

  std::string s = result.toStyledString();
  OrthancPluginAnswerBuffer(OrthancPlugins::GetGlobalContext(), output, s.c_str(), s.size(), Orthanc::EnumerationToString(Orthanc::MimeType_Json));
}


void ServeIIIFFramePyramidTile(OrthancPluginRestOutput* output,
                               const char* url,
                               const OrthancPluginHttpRequest* request)
{
  const std::string instanceId(request->groups[0]);
  const std::string region(request->groups[2]);
  const std::string size(request->groups[3]);
  const std::string rotation(request->groups[4]);
  const std::string quality(request->groups[5]);
  const std::string format(request->groups[6]);

  unsigned int frameNumber;
  if (!Orthanc::SerializationToolbox::ParseUnsignedInteger32(frameNumber, request->groups[1]))
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_UnknownResource);
  }

  LOG(INFO) << "IIIF: Image API call to tile of frame " << frameNumber << " in instance " << instanceId << ": "
            << "region=" << region << "; size=" << size << "; rotation="
            << rotation << "; quality=" << quality << "; format=" << format;

  const RegionParameters parameters(region, size, rotation, quality, format);

  if (parameters.IsFull())
  {
    std::unique_ptr<Orthanc::ImageAccessor> image;

    {
      OrthancWSI::DecodedPyramidCache::Accessor accessor(OrthancWSI::DecodedPyramidCache::GetInstance(), instanceId, frameNumber);
      image.reset(RenderFullImage(accessor.GetPyramid()));
    }

    std::string encoded;
    OrthancWSI::RawTile::Encode(encoded, *image, Orthanc::MimeType_Jpeg);

    OrthancPluginAnswerBuffer(OrthancPlugins::GetGlobalContext(), output, encoded.c_str(),
                              encoded.size(), Orthanc::EnumerationToString(Orthanc::MimeType_Jpeg));
  }
  else
  {
    std::unique_ptr<RegionRenderer> renderer;

    {
      OrthancWSI::DecodedPyramidCache::Accessor accessor(OrthancWSI::DecodedPyramidCache::GetInstance(), instanceId, frameNumber);
      renderer.reset(new RegionRenderer(parameters, accessor.GetPyramid()));
    }

    renderer->Answer(output);
  }
}


void InitializeIIIF(const std::string& iiifPublicUrl)
{
  iiifPublicUrl_ = iiifPublicUrl;

  OrthancPlugins::RegisterRestCallback<ServeIIIFSeriesPyramidInfo>("/wsi/iiif/tiles/([0-9a-f-]+)/info.json", true);
  OrthancPlugins::RegisterRestCallback<ServeIIIFTiledImageTile>("/wsi/iiif/tiles/([0-9a-f-]+)/([0-9a-z,:]+)/([0-9a-z,!:]+)/([0-9,!]+)/([a-z]+)\\.([a-z]+)", true);
  OrthancPlugins::RegisterRestCallback<ServeIIIFManifest>("/wsi/iiif/series/([0-9a-f-]+)/manifest.json", true);
  OrthancPlugins::RegisterRestCallback<ServeIIIFFrameInfo>("/wsi/iiif/frames/([0-9a-f-]+)/([0-9]+)/info.json", true);
  OrthancPlugins::RegisterRestCallback<ServeIIIFFrameImage>("/wsi/iiif/frames/([0-9a-f-]+)/([0-9]+)/full/max/0/default.jpg", true);

  // New in WSI 3.0
  OrthancPlugins::RegisterRestCallback<ServeIIIFFramePyramidManifest>("/wsi/iiif/frames-pyramids/([0-9a-f-]+)/([0-9]+)/manifest.json", true);
  OrthancPlugins::RegisterRestCallback<ServeIIIFFramePyramidInfo>("/wsi/iiif/frames-pyramids/([0-9a-f-]+)/([0-9]+)/info.json", true);
  OrthancPlugins::RegisterRestCallback<ServeIIIFFramePyramidTile>("/wsi/iiif/frames-pyramids/([0-9a-f-]+)/([0-9]+)/([0-9a-z,:]+)/([0-9a-z,!:]+)/([0-9,!]+)/([a-z]+)\\.([a-z]+)", true);
}

void SetIIIFForcePowersOfTwoScaleFactors(bool force)
{
  iiifForcePowersOfTwoScaleFactors_ = force;
}
