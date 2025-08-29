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


#pragma once

#include <Images/ImageAccessor.h>

#include <list>

namespace OrthancStone
{
  class BitmapLayout : public boost::noncopyable
  {
  private:
    class Block;

    typedef std::list<Block*>  Blocks;

    Blocks        blocks_;
    int           left_;
    int           top_;
    int           right_;
    int           bottom_;

  public:
    BitmapLayout();

    ~BitmapLayout();

    int GetLeft() const
    {
      return left_;
    }

    int GetTop() const
    {
      return top_;
    }

    int GetRight() const
    {
      return right_;
    }

    int GetBottom() const
    {
      return bottom_;
    }

    unsigned int GetWidth() const;

    unsigned int GetHeight() const;

    const Orthanc::ImageAccessor& AddBlock(int x,
                                           int y,
                                           Orthanc::ImageAccessor* bitmap /* takes ownership */);

    Orthanc::ImageAccessor* Render(Orthanc::PixelFormat format) const;
  };
}
