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


#include "BucketMapper.h"

#include <OrthancException.h>

#include <cassert>
#include <cmath>


namespace OrthancStone
{
  namespace Internals
  {
    BucketMapper::BucketMapper(double minValue,
                               double maxValue,
                               size_t bucketsCount) :
      minValue_(minValue),
      maxValue_(maxValue),
      bucketsCount_(bucketsCount)
    {
      if (minValue >= maxValue ||
          bucketsCount == 0)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
      }
    }


    void BucketMapper::CheckIndex(size_t i) const
    {
      if (i >= bucketsCount_)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
      }
    }


    double BucketMapper::GetBucketLow(size_t i) const
    {
      CheckIndex(i);
      double alpha = static_cast<double>(i) / static_cast<double>(bucketsCount_);
      return (1.0 - alpha) * minValue_ + alpha * maxValue_;
    }

    
    double BucketMapper::GetBucketHigh(size_t i) const
    {
      CheckIndex(i);
      double alpha = static_cast<double>(i + 1) / static_cast<double>(bucketsCount_);
      return (1.0 - alpha) * minValue_ + alpha * maxValue_;
    }

    
    double BucketMapper::GetBucketCenter(size_t i) const
    {
      CheckIndex(i);
      double alpha = (static_cast<double>(i) + 0.5) / static_cast<double>(bucketsCount_);
      return (1.0 - alpha) * minValue_ + alpha * maxValue_;
    }

    
    size_t BucketMapper::GetBucketIndex(double value) const
    {
      if (value < minValue_ ||
          value > maxValue_)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
      }
      else
      {
        double tmp = (value - minValue_) / (maxValue_ - minValue_) * static_cast<double>(bucketsCount_);
        assert(tmp >= 0 && tmp <= static_cast<double>(bucketsCount_));

        size_t bucket = static_cast<unsigned int>(std::floor(tmp));
        if (bucket == bucketsCount_)  // This is the case if "value == maxValue_"
        {
          return bucketsCount_ - 1;
        }
        else
        {
          return bucket;
        }
      }
    }
  }
}
