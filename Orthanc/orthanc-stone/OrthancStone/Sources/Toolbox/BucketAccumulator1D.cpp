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


#include "BucketAccumulator1D.h"

#include "LinearAlgebra.h"

#include <OrthancException.h>


namespace OrthancStone
{
  BucketAccumulator1D::BucketAccumulator1D(double minValue,
                                           double maxValue,
                                           size_t countBuckets,
                                           bool storeValues) :
    mapper_(minValue, maxValue, countBuckets),
    buckets_(countBuckets),
    storeValues_(storeValues)
  {
  }

  
  size_t BucketAccumulator1D::GetBucketContentSize(size_t i) const
  {
    mapper_.CheckIndex(i);
    return buckets_[i].count_;
  }


  void BucketAccumulator1D::AddValue(double value)
  {
    Bucket& bucket = buckets_[mapper_.GetBucketIndex(value)];

    bucket.count_++;

    if (storeValues_)
    {
      bucket.values_.push_back(value);
    }
  }

  
  size_t BucketAccumulator1D::FindBestBucket() const
  {
    size_t best = 0;

    for (size_t i = 0; i < buckets_.size(); i++)
    {
      if (buckets_[i].count_ > buckets_[best].count_)
      {
        best = i;
      }
    }
    
    return best;
  }


  double BucketAccumulator1D::ComputeBestMedian() const
  {
    if (!storeValues_)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
    }
    
    const std::list<double>& values = buckets_[FindBestBucket()].values_;

    std::vector<double> v;
    v.reserve(values.size());
    for (std::list<double>::const_iterator it = values.begin(); it != values.end(); ++it)
    {
      v.push_back(*it);
    }

    return LinearAlgebra::ComputeMedian(v);
  }
}
