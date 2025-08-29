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

#include "../Extent2D.h"

#include <boost/noncopyable.hpp>
#include <list>
#include <vector>

namespace OrthancStone
{
  namespace Internals
  {
    class RectanglesIntegerProjection : public boost::noncopyable
    {
    private:
      class Endpoint;

      std::vector<double>  endpointsToDouble_;
      std::vector<size_t>  intervalsLow_;
      std::vector<size_t>  intervalsHigh_;

    public:
      RectanglesIntegerProjection(const std::list<Extent2D>& rectangles,
                                  bool isHorizontal);
      
      size_t GetEndpointsCount() const
      {
        return endpointsToDouble_.size();
      }

      double GetEndpointCoordinate(size_t index) const;
      
      size_t GetProjectedRectanglesCount() const;
      
      size_t GetProjectedRectangleLow(size_t index) const;
      
      size_t GetProjectedRectangleHigh(size_t index) const;
    };
  }
}
