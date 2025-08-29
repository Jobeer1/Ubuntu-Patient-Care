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
#include "OpenSlideLibrary.h"

#include <Compatibility.h>  // For std::unique_ptr
#include <Logging.h>
#include <Images/Image.h>
#include <OrthancException.h>

#include <memory>

namespace OrthancWSI
{
  static std::unique_ptr<OpenSlideLibrary>  globalLibrary_;


  OpenSlideLibrary::OpenSlideLibrary(const std::string& path) :
    library_(path)
  {
    close_ = (FunctionClose) library_.GetFunction("openslide_close");
    getLevelCount_ = (FunctionGetLevelCount) library_.GetFunction("openslide_get_level_count");
    getLevelDimensions_ = (FunctionGetLevelDimensions) library_.GetFunction("openslide_get_level_dimensions");
    getLevelDownsample_ = (FunctionGetLevelDownsample) library_.GetFunction("openslide_get_level_downsample");
    open_ = (FunctionOpen) library_.GetFunction("openslide_open");
    readRegion_ = (FunctionReadRegion) library_.GetFunction("openslide_read_region");
    getPropertyNames_ = (FunctionGetPropertyNames) library_.GetFunction("openslide_get_property_names");
    getPropertyValue_ = (FunctionGetPropertyValue) library_.GetFunction("openslide_get_property_value");
  }


  OpenSlideLibrary::Image::Level::Level() : 
    width_(0),
    height_(0), 
    downsample_(1)
  {
  }


  OpenSlideLibrary::Image::Level::Level(int64_t width,
                                        int64_t height,
                                        double downsample) :
    width_(static_cast<unsigned int>(width)),
    height_(static_cast<unsigned int>(height)),
    downsample_(downsample)
  {
    if (width < 0 ||
        height < 0 ||
        downsample <= 0)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
    }

    if (static_cast<int64_t>(width_) != width ||
        static_cast<int64_t>(height_) != height)
    {
      LOG(ERROR) << "The whole-slide image is too large";
      throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
    }
  }


  void OpenSlideLibrary::Image::Initialize(const std::string& path)
  {
    handle_ = that_.open_(path.c_str());
    if (handle_ == NULL)
    {
      LOG(ERROR) << "Cannot open an image with OpenSlide: " << path;
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
    }

    try
    {
      LOG(INFO) << "Opening an image with OpenSlide: " << path;

      int32_t tmp = that_.getLevelCount_(handle_);
      if (tmp <= 0)
      {
        LOG(ERROR) << "Image with no pyramid level";
        throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
      }

      levels_.resize(tmp);

      for (int32_t level = 0; level < tmp; level++)
      {
        int64_t width, height;
        that_.getLevelDimensions_(handle_, level, &width, &height);

        double downsample = that_.getLevelDownsample_(handle_, level);

        levels_[level] = Level(width, height, downsample);
      }

      for (size_t i = 1; i < levels_.size(); i++)
      {
        if (levels_[i].width_ >= levels_[i - 1].width_ ||
            levels_[i].height_ >= levels_[i - 1].height_)
        {
          // This is not a pyramid with levels of decreasing sizes
          // (level "0" must be the finest level)
          LOG(ERROR) << "The pyramid does not have levels of strictly decreasing sizes";
          throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
        }
      }
    }
    catch (Orthanc::OrthancException&)
    {
      Close();
      throw;
    }
  }


  OpenSlideLibrary::Image::Image(OpenSlideLibrary& that,
                                 const std::string& path) :
    that_(that),
    handle_(NULL)
  {
    Initialize(path);
  }


  OpenSlideLibrary::Image::Image(const std::string& path) :
    that_(OpenSlideLibrary::GetInstance()),
    handle_(NULL)
  {
    Initialize(path);

    const char* const* properties = that_.getPropertyNames_(handle_);
    if (properties == NULL)
    {
      that_.close_(handle_);
      throw Orthanc::OrthancException(Orthanc::ErrorCode_NullPointer);
    }

    for (size_t i = 0; properties[i] != NULL; i++)
    {
      const char* value = that_.getPropertyValue_(handle_, properties[i]);
      if (value == NULL)
      {
        that_.close_(handle_);
        throw Orthanc::OrthancException(Orthanc::ErrorCode_NullPointer);
      }
      else
      {
        properties_[properties[i]] = value;
      }
    }
  }


  void OpenSlideLibrary::Image::Close()
  {
    if (handle_ != NULL)
    {
      that_.close_(handle_);
      handle_ = NULL;
    }
  }


  void OpenSlideLibrary::Image::CheckLevel(unsigned int level) const
  {
    if (level >= levels_.size())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
  }


  double OpenSlideLibrary::Image::GetLevelDownsample(unsigned int level) const
  {
    CheckLevel(level);
    return levels_[level].downsample_;
  }


  unsigned int OpenSlideLibrary::Image::GetLevelWidth(unsigned int level) const
  {
    CheckLevel(level);
    return levels_[level].width_;
  }


  unsigned int OpenSlideLibrary::Image::GetLevelHeight(unsigned int level) const
  {
    CheckLevel(level);
    return levels_[level].height_;
  }


  Orthanc::ImageAccessor* OpenSlideLibrary::Image::ReadRegion(unsigned int level,
                                                              uint64_t x,
                                                              uint64_t y,
                                                              unsigned int width,
                                                              unsigned int height)
  {
    CheckLevel(level);

    // Create a new image, with minimal pitch so as to be compatible with OpenSlide API
    std::unique_ptr<Orthanc::ImageAccessor> region(new Orthanc::Image(Orthanc::PixelFormat_BGRA32, width, height, true));

    if (region->GetWidth() != 0 &&
        region->GetHeight() != 0)
    {
      double zoom = levels_[level].downsample_;
      x = static_cast<uint64_t>(zoom * static_cast<double>(x));
      y = static_cast<uint64_t>(zoom * static_cast<double>(y));
          
      that_.readRegion_(handle_, reinterpret_cast<uint32_t*>(region->GetBuffer()),
                        x, y, level, region->GetWidth(), region->GetHeight());
    }

    return region.release();
  }


  OpenSlideLibrary& OpenSlideLibrary::GetInstance()
  {
    if (globalLibrary_.get() == NULL)
    {
      LOG(ERROR) << "OpenSlide has not been initialized, use the \"--openslide\" command-line option";
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
    }
    else
    {
      return *globalLibrary_;
    }
  }


  void OpenSlideLibrary::Initialize(const std::string& path)
  {
    globalLibrary_.reset(new OpenSlideLibrary(path));
  }


  void OpenSlideLibrary::Finalize()
  {
    globalLibrary_.reset(NULL);
  }


  bool OpenSlideLibrary::Image::LookupProperty(std::string& value,
                                               const std::string& property) const
  {
    std::map<std::string, std::string>::const_iterator found = properties_.find(property);

    if (found == properties_.end())
    {
      return false;
    }
    else
    {
      value = found->second;
      return true;
    }
  }
}
