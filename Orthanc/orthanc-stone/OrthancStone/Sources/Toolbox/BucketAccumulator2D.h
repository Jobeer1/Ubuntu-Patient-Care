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
#include <stdio.h>
#include <vector>


namespace OrthancStone
{
  class BucketAccumulator2D : public boost::noncopyable
  {
  private:
    struct Bucket
    {
      size_t             count_;
      std::list<double>  valuesX_;
      std::list<double>  valuesY_;

      Bucket() :
        count_(0)
      {
      }
    };
    
    Internals::BucketMapper  mapperX_;
    Internals::BucketMapper  mapperY_;
    std::vector<Bucket>      buckets_;
    bool                     storeValues_;

    size_t FindBestInternal() const;

    size_t EncodeIndex(size_t x,
                       size_t y) const;

    void DecodeIndex(size_t& x,
                     size_t& y,
                     size_t index) const;

  public:
    BucketAccumulator2D(double minValueX,
                        double maxValueX,
                        size_t countBucketsX,
                        double minValueY,
                        double maxValueY,
                        size_t countBucketsY,
                        bool storeValues);

    void GetSize(size_t& x,
                 size_t& y) const;

    double GetBucketLowX(size_t i) const
    {
      return mapperX_.GetBucketLow(i);
    }

    double GetBucketHighX(size_t i) const
    {
      return mapperX_.GetBucketHigh(i);
    }

    double GetBucketCenterX(size_t i) const
    {
      return mapperX_.GetBucketCenter(i);
    }

    double GetBucketLowY(size_t i) const
    {
      return mapperY_.GetBucketLow(i);
    }

    double GetBucketHighY(size_t i) const
    {
      return mapperY_.GetBucketHigh(i);
    }

    double GetBucketCenterY(size_t i) const
    {
      return mapperY_.GetBucketCenter(i);
    }

    size_t GetBucketContentSize(size_t x,
                                size_t y) const;

    void GetBucketIndex(size_t& bucketX,
                        size_t& bucketY,
                        double valueX,
                        double valueY) const;

    void AddValue(double valueX,
                  double valueY);

    void FindBestBucket(size_t& bucketX,
                        size_t& bucketY) const
    {
      DecodeIndex(bucketX, bucketY, FindBestInternal());
    }

    void ComputeBestCenter(double& x,
                           double& y) const;

    void ComputeBestMedian(double& x,
                           double& y) const;

    void Print(FILE* fp) const;
  };
}
