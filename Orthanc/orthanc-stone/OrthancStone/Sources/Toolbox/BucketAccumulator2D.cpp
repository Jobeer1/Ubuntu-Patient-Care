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


#include "BucketAccumulator2D.h"

#include "LinearAlgebra.h"

#include <OrthancException.h>


namespace OrthancStone
{
  size_t BucketAccumulator2D::FindBestInternal() const
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

  
  size_t BucketAccumulator2D::EncodeIndex(size_t x,
                                          size_t y) const
  {
    if (x >= mapperX_.GetSize() ||
        y >= mapperX_.GetSize())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
    else
    {
      return x + y * mapperX_.GetSize();
    }
  }

  
  void BucketAccumulator2D::DecodeIndex(size_t& x,
                                        size_t& y,
                                        size_t index) const
  {
    assert(buckets_.size() == mapperX_.GetSize() * mapperY_.GetSize());
    
    if (index >= buckets_.size())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
    else
    {
      x = index % mapperX_.GetSize();
      y = index / mapperX_.GetSize();
    }
  }


  BucketAccumulator2D::BucketAccumulator2D(double minValueX,
                                           double maxValueX,
                                           size_t countBucketsX,
                                           double minValueY,
                                           double maxValueY,
                                           size_t countBucketsY,
                                           bool storeValues) :
    mapperX_(minValueX, maxValueX, countBucketsX),
    mapperY_(minValueY, maxValueY, countBucketsY),
    buckets_(countBucketsX * countBucketsY),
    storeValues_(storeValues)
  {
  }


  void BucketAccumulator2D::GetSize(size_t& x,
                                    size_t& y) const
  {
    x = mapperX_.GetSize();
    y = mapperY_.GetSize();
  }


  size_t BucketAccumulator2D::GetBucketContentSize(size_t x,
                                                   size_t y) const
  {
    return buckets_[EncodeIndex(x, y)].count_;
  }


  void BucketAccumulator2D::GetBucketIndex(size_t& bucketX,
                                           size_t& bucketY,
                                           double valueX,
                                           double valueY) const
  {
    bucketX = mapperX_.GetBucketIndex(valueX);
    bucketY = mapperY_.GetBucketIndex(valueY);
  }

  
  void BucketAccumulator2D::AddValue(double valueX,
                                     double valueY)
  {
    size_t x = mapperX_.GetBucketIndex(valueX);
    size_t y = mapperY_.GetBucketIndex(valueY);
    
    Bucket& bucket = buckets_[EncodeIndex(x, y)];

    bucket.count_++;

    if (storeValues_)
    {
      bucket.valuesX_.push_back(valueX);
      bucket.valuesY_.push_back(valueY);
    }
  }


  void BucketAccumulator2D::ComputeBestCenter(double& x,
                                              double& y) const
  {
    size_t bucketX, bucketY;
    FindBestBucket(bucketX, bucketY);
    x = mapperX_.GetBucketCenter(bucketX);
    y = mapperY_.GetBucketCenter(bucketY);
  }


  void BucketAccumulator2D::ComputeBestMedian(double& x,
                                              double& y) const
  {
    if (!storeValues_)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
    }
    
    const std::list<double>& valuesX = buckets_[FindBestInternal()].valuesX_;
    const std::list<double>& valuesY = buckets_[FindBestInternal()].valuesY_;

    std::vector<double> v;
    v.reserve(valuesX.size());
    for (std::list<double>::const_iterator it = valuesX.begin(); it != valuesX.end(); ++it)
    {
      v.push_back(*it);
    }

    x = LinearAlgebra::ComputeMedian(v);

    v.clear();
    v.reserve(valuesY.size());
    for (std::list<double>::const_iterator it = valuesY.begin(); it != valuesY.end(); ++it)
    {
      v.push_back(*it);
    }

    y = LinearAlgebra::ComputeMedian(v);
  }


  void BucketAccumulator2D::Print(FILE* fp) const
  {
    fprintf(fp, "         ");
    
    for (size_t x = 0; x < mapperX_.GetSize(); x++)
    {
      fprintf(fp, "%7.2f ", mapperX_.GetBucketCenter(x));
    }

    fprintf(fp, "\n");
    
    for (size_t y = 0; y < mapperY_.GetSize(); y++)
    {
      fprintf(fp, "%7.2f: ", mapperY_.GetBucketCenter(y));

      for (size_t x = 0; x < mapperX_.GetSize(); x++)
      {
        fprintf(fp, "%7ld ", static_cast<long>(GetBucketContentSize(x, y)));
      }

      fprintf(fp, "\n");
    }
  }
}
