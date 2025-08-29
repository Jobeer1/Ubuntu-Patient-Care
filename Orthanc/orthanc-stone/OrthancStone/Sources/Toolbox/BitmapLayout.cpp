/**
 * Stone of Orthanc
 * Copyright (C) 2012-2016 Sebastien Jodogne, Medical Physics
 * Department, University Hospital of Liege, Belgium
 * Copyright (C) 2017-2023 Osimis S.A., Belgium
 * Copyright (C) 2021-2025 Sebastien Jodogne, ICTEAM UCLouvain, Belgium
 *
 * This program is free software: you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public License
 * as published by the Free Software Foundation, either version 3 of
 * the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this program. If not, see
 * <http://www.gnu.org/licenses/>.
 **/


#include "BitmapLayout.h"

#include <Images/Image.h>
#include <Images/ImageProcessing.h>
#include <OrthancException.h>

#include <cassert>

namespace OrthancStone
{
  class BitmapLayout::Block : public boost::noncopyable
  {
  private:
    int  x_;
    int  y_;
    std::unique_ptr<Orthanc::ImageAccessor>  bitmap_;

  public:
    Block(int x,
          int y,
          Orthanc::ImageAccessor* bitmap) :
      x_(x),
      y_(y),
      bitmap_(bitmap)
    {
      if (bitmap == NULL)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_NullPointer);
      }
    }

    int GetX() const
    {
      return x_;
    }

    int GetY() const
    {
      return y_;
    }

    const Orthanc::ImageAccessor& GetBitmap() const
    {
      return *bitmap_;
    }
  };


  BitmapLayout::BitmapLayout() :
    left_(0),
    top_(0),
    right_(0),
    bottom_(0)
  {
  }


  BitmapLayout::~BitmapLayout()
  {
    for (Blocks::iterator it = blocks_.begin(); it != blocks_.end(); ++it)
    {
      assert(*it != NULL);
      delete *it;
    }
  }


  unsigned int BitmapLayout::GetWidth() const
  {
    assert(left_ <= right_);
    return static_cast<unsigned int>(right_ - left_ + 1);
  }


  unsigned int BitmapLayout::GetHeight() const
  {
    assert(top_ <= bottom_);
    return static_cast<unsigned int>(bottom_ - top_ + 1);
  }


  const Orthanc::ImageAccessor& BitmapLayout::AddBlock(int x,
                                                       int y,
                                                       Orthanc::ImageAccessor* bitmap)
  {
    if (bitmap == NULL)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_NullPointer);
    }

    blocks_.push_back(new Block(x, y, bitmap));

    left_ = std::min(left_, x);
    top_ = std::min(top_, x);
    right_ = std::max(right_, x + static_cast<int>(bitmap->GetWidth()) - 1);
    bottom_ = std::max(bottom_, y + static_cast<int>(bitmap->GetHeight()) - 1);

    return *bitmap;
  }


  Orthanc::ImageAccessor* BitmapLayout::Render(Orthanc::PixelFormat format) const
  {
    std::unique_ptr<Orthanc::ImageAccessor> layout(
      new Orthanc::Image(format, GetWidth(), GetHeight(), true /* to be used as OpenGL texture */));

    Orthanc::ImageProcessing::Set(*layout, 0);

    for (Blocks::const_iterator it = blocks_.begin(); it != blocks_.end(); ++it)
    {
      assert(*it != NULL);

      Orthanc::ImageAccessor region;
      assert((*it)->GetX() >= GetLeft());
      assert((*it)->GetY() >= GetTop());

      layout->GetRegion(region, static_cast<unsigned int>((*it)->GetX() + GetLeft()),
                        static_cast<unsigned int>((*it)->GetY() + GetTop()),
                        (*it)->GetBitmap().GetWidth(), (*it)->GetBitmap().GetHeight());

      Orthanc::ImageProcessing::Convert(region, (*it)->GetBitmap());
    }

    return layout.release();
  }
}
