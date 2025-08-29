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

#include <Images/ImageAccessor.h>
#include <SharedLibrary.h>

#include <map>
#include <vector>

namespace OrthancWSI
{
  class OpenSlideLibrary : public boost::noncopyable
  {
  private:
    typedef void*   (*FunctionClose) (void*);
    typedef int32_t (*FunctionGetLevelCount) (void*);
    typedef void    (*FunctionGetLevelDimensions) (void*, int32_t, int64_t*, int64_t*);
    typedef double  (*FunctionGetLevelDownsample) (void*, int32_t);
    typedef void*   (*FunctionOpen) (const char*);
    typedef void    (*FunctionReadRegion) (void*, uint32_t*, int64_t, int64_t, int32_t, int64_t, int64_t);

    // New in WSI 2.0
    typedef const char* const* (*FunctionGetPropertyNames) (void*);
    typedef const char*        (*FunctionGetPropertyValue) (void*, const char*);

    Orthanc::SharedLibrary      library_;
    FunctionClose               close_;
    FunctionGetLevelCount       getLevelCount_;
    FunctionGetLevelDimensions  getLevelDimensions_;
    FunctionGetLevelDownsample  getLevelDownsample_;
    FunctionOpen                open_;
    FunctionReadRegion          readRegion_;
    FunctionGetPropertyNames    getPropertyNames_;
    FunctionGetPropertyValue    getPropertyValue_;

  public:
    explicit OpenSlideLibrary(const std::string& path);

    static OpenSlideLibrary& GetInstance();

    static void Initialize(const std::string& path);

    static void Finalize();

    class Image : public boost::noncopyable
    {
    private:
      struct Level
      {
        unsigned int  width_;
        unsigned int  height_;
        double        downsample_;

        Level();

        Level(int64_t width,
              int64_t height,
              double downsample);
      };

      OpenSlideLibrary&                   that_;
      void*                               handle_;
      std::vector<Level>                  levels_;
      std::map<std::string, std::string>  properties_;

      void Initialize(const std::string& path);

      void Close();

      void CheckLevel(unsigned int level) const;

    public:
      Image(OpenSlideLibrary& that,
            const std::string& path);

      explicit Image(const std::string& path);

      ~Image()
      {
        Close();
      }

      unsigned int GetLevelCount() const
      {
        return levels_.size();
      }

      double GetLevelDownsample(unsigned int level) const;

      unsigned int GetLevelWidth(unsigned int level) const;

      unsigned int GetLevelHeight(unsigned int level) const;

      Orthanc::ImageAccessor* ReadRegion(unsigned int level,
                                         uint64_t x,
                                         uint64_t y,
                                         unsigned int width,
                                         unsigned int height);

      bool LookupProperty(std::string& value,
                          const std::string& property) const;
    };
  };
}
