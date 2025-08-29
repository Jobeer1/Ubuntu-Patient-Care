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


#include "RectanglesIntegerProjection.h"

#include <OrthancException.h>

#include <algorithm>
#include <cassert>


namespace OrthancStone
{
  namespace Internals
  {
    class RectanglesIntegerProjection::Endpoint
    {
    private:
      size_t  intervalIndex_;
      double  value_;
      bool    isLow_;

    public:
      Endpoint(size_t intervalIndex,
               double value,
               bool isLow) :
        intervalIndex_(intervalIndex),
        value_(value),
        isLow_(isLow)
      {
      }

      bool operator< (const Endpoint& other) const
      {
        if (value_ < other.value_)
        {
          return true;
        }
        else if (value_ == other.value_)
        {
          return static_cast<int>(isLow_) < static_cast<int>(other.isLow_);
        }
        else
        {
          return false;
        }
      }

      size_t GetIntervalIndex() const
      {
        return intervalIndex_;
      }

      double GetValue() const
      {
        return value_;
      }

      bool IsLow() const
      {
        return isLow_;
      }
    };


    RectanglesIntegerProjection::RectanglesIntegerProjection(const std::list<Extent2D>& rectangles,
                                                             bool isHorizontal)
    {
      std::vector<Endpoint> endpoints;
      endpoints.reserve(2 * rectangles.size());
      
      size_t count = 0;
      for (std::list<Extent2D>::const_iterator it = rectangles.begin(); it != rectangles.end(); ++it)
      {
        if (!it->IsEmpty())
        {
          if (isHorizontal)
          {
            assert(it->GetX1() < it->GetX2());
            endpoints.push_back(Endpoint(count, it->GetX1(), true));
            endpoints.push_back(Endpoint(count, it->GetX2(), false));
          }
          else
          {
            assert(it->GetY1() < it->GetY2());
            endpoints.push_back(Endpoint(count, it->GetY1(), true));
            endpoints.push_back(Endpoint(count, it->GetY2(), false));
          }

          assert(endpoints[endpoints.size() - 2] < endpoints[endpoints.size() - 1]);
          
          count++;
        }
      }

      std::sort(endpoints.begin(), endpoints.end());

      intervalsLow_.resize(count);
      intervalsHigh_.resize(count);
      endpointsToDouble_.reserve(count);

      for (size_t i = 0; i < endpoints.size(); i++)
      {
        if (endpointsToDouble_.empty() ||
            endpointsToDouble_.back() < endpoints[i].GetValue())
        {
          endpointsToDouble_.push_back(endpoints[i].GetValue());
        }

        size_t intervalIndex = endpoints[i].GetIntervalIndex();
        
        if (endpoints[i].IsLow())
        {
          intervalsLow_[intervalIndex] = endpointsToDouble_.size() - 1;
        }
        else
        {
          intervalsHigh_[intervalIndex] = endpointsToDouble_.size() - 1;
        }
      }

      for (size_t i = 0; i < intervalsLow_.size(); i++)
      {
        assert(intervalsLow_[i] < intervalsHigh_[i]);
      }
    }


    double RectanglesIntegerProjection::GetEndpointCoordinate(size_t index) const
    {
      if (index >= endpointsToDouble_.size())
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
      }
      else
      {
        return endpointsToDouble_[index];
      }
    }

    
    size_t RectanglesIntegerProjection::GetProjectedRectanglesCount() const
    {
      assert(intervalsLow_.size() == intervalsHigh_.size());
      return intervalsLow_.size();
    }

    
    size_t RectanglesIntegerProjection::GetProjectedRectangleLow(size_t index) const
    {
      if (index >= GetProjectedRectanglesCount())
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
      }
      else
      {
        return intervalsLow_[index];
      }
    }

    
    size_t RectanglesIntegerProjection::GetProjectedRectangleHigh(size_t index) const
    {
      if (index >= GetProjectedRectanglesCount())
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
      }
      else
      {
        return intervalsHigh_[index];
      }
    }
  }
}
