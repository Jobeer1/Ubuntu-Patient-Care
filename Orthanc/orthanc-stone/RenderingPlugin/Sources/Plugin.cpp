/**
 * Stone of Orthanc
 * Copyright (C) 2012-2016 Sebastien Jodogne, Medical Physics
 * Department, University Hospital of Liege, Belgium
 * Copyright (C) 2017-2023 Osimis S.A., Belgium
 * Copyright (C) 2021-2025 Sebastien Jodogne, ICTEAM UCLouvain, Belgium
 *
 * This program is free software: you can redistribute it and/or
 * modify it under the terms of the GNU General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 * 
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program. If not, see <http://www.gnu.org/licenses/>.
 **/


#include "OrthancPluginConnection.h"
#include "../Resources/Orthanc/Plugins/OrthancPluginCppWrapper.h"

#include "../../OrthancStone/Sources/Toolbox/AffineTransform2D.h"
#include "../../OrthancStone/Sources/Toolbox/DicomInstanceParameters.h"
#include "../../OrthancStone/Sources/Toolbox/DicomStructureSet.h"

#include <Cache/MemoryObjectCache.h>
#include <Images/Image.h>
#include <Images/ImageProcessing.h>
#include <Images/NumpyWriter.h>
#include <Logging.h>
#include <SerializationToolbox.h>
#include <Toolbox.h>

#include <boost/math/constants/constants.hpp>


static const char* const INSTANCES = "Instances";  
static const char* const RT_STRUCT_IOD = "1.2.840.10008.5.1.4.1.1.481.3";
static const char* const SOP_CLASS_UID = "0008,0016";
static const char* const STRUCTURES = "Structures";


class DicomStructureCache : public boost::noncopyable
{
private:
  class Item : public Orthanc::ICacheable
  {
  private:
    std::unique_ptr<OrthancStone::DicomStructureSet> rtstruct_;

  public:
    explicit Item(OrthancStone::DicomStructureSet* rtstruct) :
      rtstruct_(rtstruct)
    {
      if (rtstruct == NULL)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_NullPointer);
      }
    }
    
    virtual size_t GetMemoryUsage() const ORTHANC_OVERRIDE
    {
      return 1;
    }

    OrthancStone::DicomStructureSet& GetRtStruct() const
    {
      return *rtstruct_;
    }
  };

  Orthanc::MemoryObjectCache   cache_;

  DicomStructureCache()  // Singleton design pattern
  {
  }
  
public:
  void Invalidate(const std::string& instanceId)
  {
    cache_.Invalidate(instanceId);
  }

  void SetMaximumNumberOfItems(size_t items)
  {
    cache_.SetMaximumSize(items);
  }

  static DicomStructureCache& GetSingleton()
  {
    static DicomStructureCache instance;
    return instance;
  }

  class Accessor : public boost::noncopyable
  {
  private:
    DicomStructureCache& that_;
    std::string instanceId_;
    Orthanc::MemoryObjectCache::Accessor  lock_;
    std::unique_ptr<OrthancStone::DicomStructureSet>  notCached_;

  public:
    Accessor(DicomStructureCache& that,
             const std::string& instanceId) :
      that_(that),
      instanceId_(instanceId),
      lock_(that.cache_, instanceId, true /* unique, as "GetRtStruct()" is mutable */)
    {
      if (!lock_.IsValid())
      {
        OrthancStone::OrthancPluginConnection connection;
        OrthancStone::FullOrthancDataset dataset(connection, "/instances/" + instanceId + "/tags?ignore-length=3006-0050");
        notCached_.reset(new OrthancStone::DicomStructureSet(dataset));
      }
    }

    ~Accessor()
    {
      if (!lock_.IsValid())
      {
        assert(notCached_.get() != NULL);
      
        try
        {
          that_.cache_.Acquire(instanceId_, new Item(notCached_.release()));
        }
        catch (Orthanc::OrthancException& e)
        {
          LOG(ERROR) << "Cannot insert RT-STRUCT into cache: " << e.What();
        }
      }
    }

    const std::string& GetInstanceId() const
    {
      return instanceId_;
    }

    OrthancStone::DicomStructureSet& GetRtStruct() const
    {
      if (lock_.IsValid())
      {
        return dynamic_cast<Item&>(lock_.GetValue()).GetRtStruct();
      }
      else
      {
        assert(notCached_.get() != NULL);
        return *notCached_;
      }
    }
  };
};


static Orthanc::PixelFormat Convert(OrthancPluginPixelFormat format)
{
  switch (format)
  {
    case OrthancPluginPixelFormat_RGB24:
      return Orthanc::PixelFormat_RGB24;

    case OrthancPluginPixelFormat_Grayscale8:
      return Orthanc::PixelFormat_Grayscale8;

    case OrthancPluginPixelFormat_Grayscale16:
      return Orthanc::PixelFormat_Grayscale16;

    case OrthancPluginPixelFormat_SignedGrayscale16:
      return Orthanc::PixelFormat_SignedGrayscale16;

    default:
      throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
  }
}


static bool ParseBoolean(const std::string& key,
                         const std::string& value)
{
  bool result;
  
  if (Orthanc::SerializationToolbox::ParseBoolean(result, value))
  {
    return result;
  }
  else
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange,
                                    "Bad value for " + key + ": " + value);
  }
}


static double ParseDouble(const std::string& key,
                         const std::string& value)
{
  double result;
  
  if (Orthanc::SerializationToolbox::ParseDouble(result, value))
  {
    return result;
  }
  else
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange,
                                    "Bad value for " + key + ": " + value);
  }
}


static unsigned int ParseUnsignedInteger(const std::string& key,
                                         const std::string& value)
{
  uint32_t result;
  
  if (Orthanc::SerializationToolbox::ParseUnsignedInteger32(result, value))
  {
    return result;
  }
  else
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange,
                                    "Bad value for " + key + ": " + value);
  }
}



class DataAugmentationParameters : public boost::noncopyable
{
private:
  double       angleRadians_;
  double       scaling_;
  double       offsetX_;
  double       offsetY_;
  bool         flipX_;
  bool         flipY_;
  bool         hasResize_;
  unsigned int targetWidth_;
  unsigned int targetHeight_;
  bool         hasInterpolation_;
  OrthancStone::ImageInterpolation  interpolation_;

  void ApplyInternal(Orthanc::ImageAccessor& target,
                     const Orthanc::ImageAccessor& source)
  {
    if (source.GetWidth() == 0 ||
        source.GetHeight() == 0)
    {
      Orthanc::ImageProcessing::Set(target, 0);  // Clear the image
    }
    else if (target.GetWidth() == 0 ||
             target.GetHeight() == 0)
    {
      // Nothing to do
    }
    else
    {
      OrthancStone::AffineTransform2D transform = ComputeTransform(source.GetWidth(), source.GetHeight());
      
      OrthancStone::ImageInterpolation interpolation;

      if (hasInterpolation_)
      {
        interpolation = interpolation_;
      }
      else if (source.GetFormat() == Orthanc::PixelFormat_RGB24)
      {
        // Bilinear interpolation for color images is not implemented yet
        interpolation = OrthancStone::ImageInterpolation_Nearest;
      }
      else
      {
        interpolation = OrthancStone::ImageInterpolation_Bilinear;
      }

      transform.Apply(target, source, interpolation, true /* clear */);
    }
  }    


  Orthanc::ImageAccessor* ApplyUnchecked(const Orthanc::ImageAccessor& source)
  {
    std::unique_ptr<Orthanc::ImageAccessor> target;
    
    if (hasResize_)
    {
      target.reset(new Orthanc::Image(source.GetFormat(), targetWidth_, targetHeight_, false));
    }
    else
    {
      target.reset(new Orthanc::Image(source.GetFormat(), source.GetWidth(), source.GetHeight(), false));
    }
    
    ApplyInternal(*target, source);
    return target.release();
  }


public:
  DataAugmentationParameters()
  {
    Clear();
  }
  

  void Clear()
  {
    angleRadians_ = 0;
    scaling_ = 1;
    offsetX_ = 0;
    offsetY_ = 0;
    flipX_ = false;
    flipY_ = false;
    hasResize_ = false;
    targetWidth_ = 0;
    targetHeight_ = 0;
    hasInterpolation_ = false;
    interpolation_ = OrthancStone::ImageInterpolation_Nearest;
  }

  
  OrthancStone::AffineTransform2D ComputeTransform(unsigned int sourceWidth,
                                                   unsigned int sourceHeight) const
  {
    unsigned int w = (hasResize_ ? targetWidth_ : sourceWidth);
    unsigned int h = (hasResize_ ? targetHeight_ : sourceHeight);

    if (w == 0 ||
        h == 0 ||
        sourceWidth == 0 ||
        sourceHeight == 0)
    {
      // Division by zero
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
    
    double r = std::min(static_cast<double>(w) / static_cast<double>(sourceWidth),
                        static_cast<double>(h) / static_cast<double>(sourceHeight));

    OrthancStone::AffineTransform2D resize = OrthancStone::AffineTransform2D::Combine(
      OrthancStone::AffineTransform2D::CreateOffset(static_cast<double>(w) / 2.0,
                                                    static_cast<double>(h) / 2.0),
      OrthancStone::AffineTransform2D::CreateScaling(r, r));

    OrthancStone::AffineTransform2D dataAugmentation = OrthancStone::AffineTransform2D::Combine(
      OrthancStone::AffineTransform2D::CreateScaling(scaling_, scaling_),
      OrthancStone::AffineTransform2D::CreateOffset(offsetX_, offsetY_),
      OrthancStone::AffineTransform2D::CreateRotation(angleRadians_),
      OrthancStone::AffineTransform2D::CreateOffset(-static_cast<double>(sourceWidth) / 2.0,
                                                    -static_cast<double>(sourceHeight) / 2.0),
      OrthancStone::AffineTransform2D::CreateFlip(flipX_, flipY_, sourceWidth, sourceHeight));

    return OrthancStone::AffineTransform2D::Combine(resize, dataAugmentation);
  }
  
  
  bool ParseParameter(const std::string& key,
                      const std::string& value)
  {
    if (key == "angle")
    {
      double angle = ParseDouble(key, value);
      angleRadians_ = angle / 180.0 * boost::math::constants::pi<double>();
      return true;
    }
    else if (key == "scaling")
    {
      scaling_ = ParseDouble(key, value);
      return true;
    }
    else if (key == "offset-x")
    {
      offsetX_ = ParseDouble(key, value);
      return true;
    }
    else if (key == "offset-y")
    {
      offsetY_ = ParseDouble(key, value);
      return true;
    }
    else if (key == "flip-x")
    {
      flipX_ = ParseBoolean(key, value);
      return true;
    }
    else if (key == "flip-y")
    {
      flipY_ = ParseBoolean(key, value);
      return true;
    }
    else if (key == "resize")
    {
      std::vector<std::string> tokens;
      Orthanc::Toolbox::TokenizeString(tokens, value, ',');
      if (tokens.size() != 2)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange,
                                        "Must provide two integers separated by commas in " + key + ": " + value);
      }
      else
      {
        targetWidth_ = ParseUnsignedInteger(key, tokens[0]);
        targetHeight_ = ParseUnsignedInteger(key, tokens[1]);
        hasResize_ = true;
        return true;
      }
    }
    else if (key == "interpolation")
    {
      if (value == "nearest")
      {
        interpolation_ = OrthancStone::ImageInterpolation_Nearest;
      }
      else if (value == "bilinear")
      {
        interpolation_ = OrthancStone::ImageInterpolation_Bilinear;
      }
      else
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange,
                                        "Unknown interpolation (must be \"nearest\" or \"bilinear\"): " + value);
      }

      hasInterpolation_ = true;
      return true;
    }
    else
    {
      return false;
    }
  }

  
  Orthanc::ImageAccessor* Apply(const Orthanc::ImageAccessor& source)
  {
    if (source.GetFormat() != Orthanc::PixelFormat_RGB24 &&
        source.GetFormat() != Orthanc::PixelFormat_Float32)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_IncompatibleImageFormat);
    }
    else
    {
      return ApplyUnchecked(source);
    }
  }

  
  Orthanc::ImageAccessor* ApplyBinaryMask(const Orthanc::ImageAccessor& source)
  {
    if (source.GetFormat() != Orthanc::PixelFormat_Grayscale8)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_IncompatibleImageFormat,
                                      "A segmentation mask should be a grayscale image");
    }
    else
    {
      std::unique_ptr<Orthanc::ImageAccessor> target(ApplyUnchecked(source));

      const unsigned int h = target->GetHeight();
      const unsigned int w = target->GetWidth();

      // Apply thresholding to get back a binary image
      for (unsigned int y = 0; y < h; y++)
      {
        uint8_t* p = reinterpret_cast<uint8_t*>(target->GetRow(y));
        for (unsigned int x = 0; x < w; x++, p++)
        {
          if (*p < 128)
          {
            *p = 0;
          }
          else
          {
            *p = 255;
          }
        }
      }

      return target.release();
    }
  }
};


static OrthancStone::DicomInstanceParameters* GetInstanceParameters(const std::string& orthancId)
{
  OrthancPlugins::MemoryBuffer tags;
  if (!tags.RestApiGet("/instances/" + orthancId + "/tags", false))
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_InexistentItem);
  }

  Json::Value json;
  tags.ToJson(json);

  Orthanc::DicomMap m;
  m.FromDicomAsJson(json);

  return new OrthancStone::DicomInstanceParameters(m);
}


static void AnswerNumpyImage(OrthancPluginRestOutput* output,
                             const Orthanc::ImageAccessor& image,
                             bool compress)
{
  std::string answer;
  Orthanc::NumpyWriter writer;
  writer.SetCompressed(compress);
  Orthanc::IImageWriter::WriteToMemory(writer, answer, image);
  
  OrthancPluginAnswerBuffer(OrthancPlugins::GetGlobalContext(), output,
                            answer.c_str(), answer.size(), "application/octet-stream");
}


static void RenderNumpyFrame(OrthancPluginRestOutput* output,
                             const char* url,
                             const OrthancPluginHttpRequest* request)
{
  DataAugmentationParameters dataAugmentation;
  bool compress = false;

  for (uint32_t i = 0; i < request->getCount; i++)
  {
    std::string key(request->getKeys[i]);
    std::string value(request->getValues[i]);

    if (!dataAugmentation.ParseParameter(key, value))
    {
      if (key == "compress")
      {
        compress = ParseBoolean(key, value);
      }
      else
      {
        LOG(WARNING) << "Unsupported option for data augmentation: " << key;
      }
    }
  }

  std::unique_ptr<OrthancStone::DicomInstanceParameters> parameters(GetInstanceParameters(request->groups[0]));
  
  OrthancPlugins::MemoryBuffer dicom;
  dicom.GetDicomInstance(request->groups[0]);

  unsigned int frame = boost::lexical_cast<unsigned int>(request->groups[1]);
  
  OrthancPlugins::OrthancImage image;
  image.DecodeDicomImage(dicom.GetData(), dicom.GetSize(), frame);
  
  Orthanc::ImageAccessor source;
  source.AssignReadOnly(Convert(image.GetPixelFormat()), image.GetWidth(), image.GetHeight(),
                        image.GetPitch(), image.GetBuffer());

  std::unique_ptr<Orthanc::ImageAccessor> modified;

  if (parameters->GetSopClassUid() == OrthancStone::SopClassUid_DicomSeg)
  {
    modified.reset(dataAugmentation.ApplyBinaryMask(source));
  }
  else if (source.GetFormat() == Orthanc::PixelFormat_RGB24)
  {
    modified.reset(dataAugmentation.Apply(source));
  }
  else
  {
    std::unique_ptr<Orthanc::ImageAccessor> converted(parameters->ConvertToFloat(source));
    assert(converted.get() != NULL);
    
    modified.reset(dataAugmentation.Apply(*converted));
  }

  assert(modified.get() != NULL);
  AnswerNumpyImage(output, *modified, compress);
}


static bool IsRtStruct(const std::string& instanceId)
{
  std::string s;
  if (OrthancPlugins::RestApiGetString(s, "/instances/" + instanceId + "/content/" + SOP_CLASS_UID, false) &&
      !s.empty())
  {
    if (s[s.size() - 1] == '\0')  // Deal with DICOM padding
    {
      s.resize(s.size() - 1);
    }
    
    return s == RT_STRUCT_IOD;
  }
  else
  {
    return false;
  }
}


static void ListRtStruct(OrthancPluginRestOutput* output,
                         const char* url,
                         const OrthancPluginHttpRequest* request)
{
  // This is a quick version of "/tools/find" on "SOPClassUID" (the
  // latter would load all the DICOM files from disk)

  Json::Value series;
  OrthancPlugins::RestApiGet(series, "/series?expand", false);

  if (series.type() != Json::arrayValue)
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
  }

  Json::Value answer = Json::arrayValue;

  for (Json::Value::ArrayIndex i = 0; i < series.size(); i++)
  {
    if (series[i].type() != Json::objectValue ||
        !series[i].isMember(INSTANCES) ||
        series[i][INSTANCES].type() != Json::arrayValue)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
    }
    
    const Json::Value& instances = series[i][INSTANCES];

    for (Json::Value::ArrayIndex j = 0; j < instances.size(); j++)
    {
      if (instances[j].type() != Json::stringValue)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
      }
    }
    
    if (instances.size() > 0 &&
        IsRtStruct(instances[0].asString()))
    {
      for (Json::Value::ArrayIndex j = 0; j < instances.size(); j++)
      {
        answer.append(instances[j].asString());
      }
    }
  }

  std::string s = answer.toStyledString();
  OrthancPluginAnswerBuffer(OrthancPlugins::GetGlobalContext(), output, s.c_str(), s.size(), "application/json");
}


static void GetRtStruct(OrthancPluginRestOutput* output,
                        const char* url,
                        const OrthancPluginHttpRequest* request)
{
  DicomStructureCache::Accessor accessor(DicomStructureCache::GetSingleton(), request->groups[0]);

  Json::Value answer;
  answer[STRUCTURES] = Json::arrayValue;

  for (size_t i = 0; i < accessor.GetRtStruct().GetStructuresCount(); i++)
  {
    Json::Value color = Json::arrayValue;
    color.append(accessor.GetRtStruct().GetStructureColor(i).GetRed());
    color.append(accessor.GetRtStruct().GetStructureColor(i).GetGreen());
    color.append(accessor.GetRtStruct().GetStructureColor(i).GetBlue());
    
    Json::Value structure;
    structure["Name"] = accessor.GetRtStruct().GetStructureName(i);
    structure["Interpretation"] = accessor.GetRtStruct().GetStructureInterpretation(i);
    structure["Color"] = color;
    
    answer[STRUCTURES].append(structure);
  }

  std::set<std::string> sopInstanceUids;
  accessor.GetRtStruct().GetReferencedInstances(sopInstanceUids);

  answer[INSTANCES] = Json::arrayValue;
  for (std::set<std::string>::const_iterator it = sopInstanceUids.begin(); it != sopInstanceUids.end(); ++it)
  {
    OrthancPlugins::OrthancString s;
    s.Assign(OrthancPluginLookupInstance(OrthancPlugins::GetGlobalContext(), it->c_str()));

    std::string t;
    s.ToString(t);

    answer[INSTANCES].append(t);
  }

  std::string s = answer.toStyledString();
  OrthancPluginAnswerBuffer(OrthancPlugins::GetGlobalContext(), output, s.c_str(), s.size(), "application/json");
}



static void RenderRtStruct(OrthancPluginRestOutput* output,
                           const char* url,
                           const OrthancPluginHttpRequest* request)
{
  class XorFiller : public Orthanc::ImageProcessing::IPolygonFiller
  {
  private:
    Orthanc::Image  image_;

  public:
    XorFiller(unsigned int width,
              unsigned int height) :
      image_(Orthanc::PixelFormat_Grayscale8, width, height, false)
    {
      Orthanc::ImageProcessing::Set(image_, 0);
    }

    Orthanc::ImageAccessor& GetImage()
    {
      return image_;
    }

    virtual void Fill(int y,
                      int x1,
                      int x2) ORTHANC_OVERRIDE
    {
      assert(x1 <= x2);

      if (y >= 0 &&
          y < static_cast<int>(image_.GetHeight()))
      {
        x1 = std::max(x1, 0);
        x2 = std::min(x2, static_cast<int>(image_.GetWidth()) - 1);

        uint8_t* p = reinterpret_cast<uint8_t*>(image_.GetRow(y)) + x1;

        for (int i = x1; i <= x2; i++, p++)
        {
          *p = (*p ^ 0xff);
        }
      }
    }
  };

  
  class HorizontalSegment
  {
  private:
    int  y_;
    int  x1_;
    int  x2_;
    
  public:
    HorizontalSegment(int y,
                      int x1,
                      int x2) :
      y_(y),
      x1_(std::min(x1, x2)),
      x2_(std::max(x1, x2))
    {
    }
    
    int GetY() const
    {
      return y_;
    }
    
    int GetX1() const
    {
      return x1_;
    }
    
    int GetX2() const
    {
      return x2_;
    }

    void Fill(Orthanc::ImageAccessor& image) const
    {
      assert(x1_ <= x2_);

      if (y_ >= 0 &&
          y_ < static_cast<int>(image.GetHeight()))
      {
        int a = std::max(x1_, 0);
        int b = std::min(x2_, static_cast<int>(image.GetWidth()) - 1);

        uint8_t* p = reinterpret_cast<uint8_t*>(image.GetRow(y_)) + a;

        for (int i = a; i <= b; i++, p++)
        {
          *p = 0xff;
        }
      }
    }
  };


  DataAugmentationParameters dataAugmentation;
  std::vector<std::string> structureNames;
  std::string instanceId;
  bool compress = false;

  for (uint32_t i = 0; i < request->getCount; i++)
  {
    std::string key(request->getKeys[i]);
    std::string value(request->getValues[i]);

    if (!dataAugmentation.ParseParameter(key, value))
    {
      if (key == "structure")
      {
        Orthanc::Toolbox::TokenizeString(structureNames, value, ',');
      }
      else if (key == "instance")
      {
        instanceId = value;
      }
      else if (key == "compress")
      {
        compress = ParseBoolean(key, value);
      }
      else
      {
        LOG(WARNING) << "Unsupported option: " << key;
      }
    }
  }

  if (structureNames.empty())
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_NetworkProtocol,
                                    "Missing option \"structure\" to provide the names of the structures of interest");
  }

  if (instanceId.empty())
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_NetworkProtocol,
                                    "Missing option \"instance\" to provide the Orthanc identifier of the instance of interest");
  }
  
  std::unique_ptr<OrthancStone::DicomInstanceParameters> parameters(GetInstanceParameters(instanceId));

  typedef std::list< std::vector<OrthancStone::Vector> > Polygons;

  Polygons polygons;

  {
    DicomStructureCache::Accessor accessor(DicomStructureCache::GetSingleton(), request->groups[0]);

    for (size_t i = 0; i < structureNames.size(); i++)
    {
      size_t structureIndex;
      if (accessor.GetRtStruct().LookupStructureName(structureIndex, structureNames[i]))
      {
        Polygons p;
        accessor.GetRtStruct().GetStructurePoints(p, structureIndex, parameters->GetSopInstanceUid());
        polygons.splice(polygons.begin(), p);
      }
      else
      {
        LOG(WARNING) << "Missing structure name \"" << structureNames[i]
                     << "\" in RT-STRUCT: " << parameters->GetSopInstanceUid();
      }
    }
  }

  // We use a "XOR" filler for the polygons in order to deal with holes in the RT-STRUCT
  XorFiller filler(parameters->GetWidth(), parameters->GetHeight());
  OrthancStone::AffineTransform2D transform = dataAugmentation.ComputeTransform(parameters->GetWidth(), parameters->GetHeight());
  
  std::list<HorizontalSegment> horizontalSegments;
  
  for (std::list< std::vector<OrthancStone::Vector> >::const_iterator
         it = polygons.begin(); it != polygons.end(); ++it)
  {
    std::vector<Orthanc::ImageProcessing::ImagePoint> points;
    points.reserve(it->size());

    for (size_t i = 0; i < it->size(); i++)
    {
      // The (0.5, 0.5) offset is due to the fact that DICOM
      // coordinates are expressed wrt. the CENTER of the voxels
      
      double x, y;
      parameters->GetGeometry().ProjectPoint(x, y, (*it) [i]);
      x = x / parameters->GetPixelSpacingX() + 0.5;
      y = y / parameters->GetPixelSpacingY() + 0.5;
      
      transform.Apply(x, y);

      points.push_back(Orthanc::ImageProcessing::ImagePoint(std::floor(x), std::floor(y)));
    }
    
    Orthanc::ImageProcessing::FillPolygon(filler, points);

    for (size_t i = 0; i < points.size(); i++)
    {
      size_t next = (i + 1) % points.size();
      if (points[i].GetY() == points[next].GetY())
      {
        horizontalSegments.push_back(HorizontalSegment(points[i].GetY(), points[i].GetX(), points[next].GetX()));
      }
    }
  }

  /**
   * We repeat the filling of the horizontal segments. This is
   * important to deal with horizontal edges that are seen in one
   * direction, then in the reverse direction within the same polygon,
   * which can typically be seen in RT-STRUCT with holes. If this step
   * is not done, only the starting point and the ending point of the
   * segments are drawn.
   **/
  for (std::list<HorizontalSegment>::const_iterator it = horizontalSegments.begin();
       it != horizontalSegments.end(); ++it)
  {
    it->Fill(filler.GetImage());
  }
  
  AnswerNumpyImage(output, filler.GetImage(), compress);
}



OrthancPluginErrorCode OnChangeCallback(OrthancPluginChangeType changeType,
                                        OrthancPluginResourceType resourceType,
                                        const char* resourceId)
{
  switch (changeType)
  {
    case OrthancPluginChangeType_Deleted:
      if (resourceType == OrthancPluginResourceType_Instance)
      {
        DicomStructureCache::GetSingleton().Invalidate(resourceId);
      }
      
      break;

    case OrthancPluginChangeType_OrthancStarted:
    {
      DicomStructureCache::Accessor accessor(DicomStructureCache::GetSingleton(), "54460695-ba3885ee-ddf61ac0-f028e31d-a6e474d9");
      OrthancStone::LinearAlgebra::Print(accessor.GetRtStruct().GetEstimatedNormal());
      printf("Slice thickness: %f\n", accessor.GetRtStruct().GetEstimatedSliceThickness());
      break;
    }

    default:
      break;
  }

  return OrthancPluginErrorCode_Success;
}


extern "C"
{
  ORTHANC_PLUGINS_API int32_t OrthancPluginInitialize(OrthancPluginContext* context)
  {
    OrthancPlugins::SetGlobalContext(context);

#if ORTHANC_FRAMEWORK_VERSION_IS_ABOVE(1, 7, 2)
    Orthanc::Logging::InitializePluginContext(context);
#else
    Orthanc::Logging::Initialize(context);
#endif

    /* Check the version of the Orthanc core */
    if (OrthancPluginCheckVersion(context) == 0)
    {
      char info[1024];
      sprintf(info, "Your version of Orthanc (%s) must be above %d.%d.%d to run this plugin",
              context->orthancVersion,
              ORTHANC_PLUGINS_MINIMAL_MAJOR_NUMBER,
              ORTHANC_PLUGINS_MINIMAL_MINOR_NUMBER,
              ORTHANC_PLUGINS_MINIMAL_REVISION_NUMBER);
      OrthancPluginLogError(context, info);
      return -1;
    }

    try
    {
      DicomStructureCache::GetSingleton().SetMaximumNumberOfItems(1024);  // Cache up to 1024 RT-STRUCT instances
      
      OrthancPlugins::RegisterRestCallback<RenderNumpyFrame>("/stone/instances/([^/]+)/frames/([0-9]+)/numpy", true);
      OrthancPlugins::RegisterRestCallback<ListRtStruct>("/stone/rt-struct", true);
      OrthancPlugins::RegisterRestCallback<GetRtStruct>("/stone/rt-struct/([^/]+)/info", true);
      OrthancPlugins::RegisterRestCallback<RenderRtStruct>("/stone/rt-struct/([^/]+)/numpy", true);
      OrthancPluginRegisterOnChangeCallback(context, OnChangeCallback);
    }
    catch (...)
    {
      OrthancPlugins::LogError("Exception while initializing the Stone Web viewer plugin");
      return -1;
    }

    return 0;
  }


  ORTHANC_PLUGINS_API void OrthancPluginFinalize()
  {
  }


  ORTHANC_PLUGINS_API const char* OrthancPluginGetName()
  {
    return PLUGIN_NAME;
  }


  ORTHANC_PLUGINS_API const char* OrthancPluginGetVersion()
  {
    return PLUGIN_VERSION;
  }
}
