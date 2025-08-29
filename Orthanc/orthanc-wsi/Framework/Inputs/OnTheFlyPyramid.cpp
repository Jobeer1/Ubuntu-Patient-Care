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
#include "OnTheFlyPyramid.h"

#include <OrthancException.h>

#include <cassert>
#include <Images/Image.h>
#include <Images/ImageProcessing.h>


namespace OrthancWSI
{
  void OnTheFlyPyramid::ReadRegion(Orthanc::ImageAccessor &target,
                                   bool &isEmpty,
                                   unsigned level,
                                   unsigned x,
                                   unsigned y)
  {
    isEmpty = false;

    const Orthanc::ImageAccessor& source = GetLevel(level);

    if (target.GetWidth() > tileWidth_ ||
      target.GetHeight() > tileHeight_ ||
      x + target.GetWidth() > source.GetWidth() ||
      y + target.GetHeight() > source.GetHeight())
    {
      // This should be handled by the base class
      throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
    }
    else
    {
      Orthanc::ImageAccessor from;
      source.GetRegion(from, x, y, target.GetWidth(), target.GetHeight());
      Orthanc::ImageProcessing::Copy(target, from);
    }
  }


  OnTheFlyPyramid::OnTheFlyPyramid(Orthanc::ImageAccessor *baseLevel,
                                   unsigned int tileWidth,
                                   unsigned int tileHeight,
                                   bool smooth) :
    tileWidth_(tileWidth),
    tileHeight_(tileHeight)
  {
    if (baseLevel == NULL)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_NullPointer);
    }

    std::unique_ptr<Orthanc::ImageAccessor> protection(baseLevel);

    if (protection->GetFormat() == Orthanc::PixelFormat_RGB24)
    {
      baseLevel_.reset(protection.release());
    }
    else
    {
      baseLevel_.reset(new Orthanc::Image(Orthanc::PixelFormat_RGB24, protection->GetWidth(), protection->GetHeight(), false));
      Orthanc::ImageProcessing::Convert(*baseLevel_, *protection);
    }

    Orthanc::ImageAccessor* current = baseLevel_.get();
    while (current->GetWidth() > tileWidth_ ||
           current->GetHeight() > tileHeight_)
    {
      std::unique_ptr<Orthanc::ImageAccessor> next;

      if (smooth)
      {
        std::unique_ptr<Orthanc::ImageAccessor> smoothed(Orthanc::Image::Clone(*current));
        Orthanc::ImageProcessing::SmoothGaussian5x5(*smoothed, false);
        next.reset(Orthanc::ImageProcessing::Halve(*smoothed, false));
      }
      else
      {
        next.reset(Orthanc::ImageProcessing::Halve(*current, false));
      }

      higherLevels_.push_back(next.release());
      current = higherLevels_.back();
    }
  }


  OnTheFlyPyramid::~OnTheFlyPyramid()
  {
    for (size_t i = 0; i < higherLevels_.size(); i++)
    {
      assert(higherLevels_[i] != NULL);
      delete higherLevels_[i];
    }
  }


  const Orthanc::ImageAccessor & OnTheFlyPyramid::GetLevel(unsigned int level) const
  {
    if (level >= GetLevelCount())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
    else if (level == 0)
    {
      assert(baseLevel_.get() != NULL);
      return *baseLevel_;
    }
    else
    {
      assert(higherLevels_[level - 1] != NULL);
      return *higherLevels_[level - 1];
    }
  }


  size_t OnTheFlyPyramid::GetMemoryUsage() const
  {
    size_t memory = baseLevel_->GetSize();

    for (size_t i= 0; i < higherLevels_.size(); i++)
    {
      assert(higherLevels_[i] != NULL);
      memory += higherLevels_[i]->GetSize();
    }

    return memory;
  }
}
