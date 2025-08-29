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

#include "Internals/BucketMapper.h"

#include <list>
#include <vector>


namespace OrthancStone
{
  class BucketAccumulator1D : public boost::noncopyable
  {
  private:
    struct Bucket
    {
      size_t             count_;
      std::list<double>  values_;

      Bucket() :
        count_(0)
      {
      }
    };
    
    Internals::BucketMapper  mapper_;
    std::vector<Bucket>      buckets_;
    bool                     storeValues_;

  public:
    BucketAccumulator1D(double minValue,
                        double maxValue,
                        size_t countBuckets,
                        bool storeValues);

    size_t GetSize() const
    {
      return mapper_.GetSize();
    }

    double GetBucketLow(size_t i) const
    {
      return mapper_.GetBucketLow(i);
    }

    double GetBucketHigh(size_t i) const
    {
      return mapper_.GetBucketHigh(i);
    }

    double GetBucketCenter(size_t i) const
    {
      return mapper_.GetBucketCenter(i);
    }
    
    size_t GetBucketContentSize(size_t i) const;

    size_t GetBucketIndex(double value) const
    {
      return mapper_.GetBucketIndex(value);
    }

    void AddValue(double value);

    size_t FindBestBucket() const;

    double ComputeBestCenter() const
    {
      return GetBucketCenter(FindBestBucket());
    }

    double ComputeBestMedian() const;
  };
}
