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

#include <stddef.h>  // For size_t
#include <vector>
#include <list>


namespace OrthancStone
{
  namespace Internals
  {
    /**
     * This is an oriented 2D line with unsigned integer coordinates.
     **/
    class OrientedIntegerLine2D
    {
    private:
      size_t  x1_;
      size_t  y1_;
      size_t  x2_;
      size_t  y2_;

    public:
      OrientedIntegerLine2D(size_t x1,
                            size_t y1,
                            size_t x2,
                            size_t y2);

      bool IsVertical() const
      {
        return (x1_ == x2_);
      }

      bool IsHorizontal() const
      {
        return (y1_ == y2_);
      }

      bool IsEmpty() const
      {
        return (x1_ == x2_ &&
                y1_ == y2_);
      }

      size_t GetX1() const
      {
        return x1_;
      }

      size_t GetY1() const
      {
        return y1_;
      }

      size_t GetX2() const
      {
        return x2_;
      }

      size_t GetY2() const
      {
        return y2_;
      }

      bool IsDownward() const
      {
        return (y1_ < y2_);
      }

      typedef std::list< std::pair<size_t, size_t> >  Chain;
      
      static void ExtractChains(std::list<Chain>& chains,
                                const std::vector<OrientedIntegerLine2D>& edges);
    };
  }
}
