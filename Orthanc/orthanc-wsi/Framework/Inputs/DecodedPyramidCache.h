/**
 * Orthanc - A Lightweight, RESTful DICOM Store
 * Copyright (C) 2012-2016 Sebastien Jodogne, Medical Physics
 * Department, University Hospital of Liege, Belgium
 * Copyright (C) 2017-2023 Osimis S.A., Belgium
 * Copyright (C) 2024-2025 Orthanc Team SRL, Belgium
 * Copyright (C) 2021-2025 Sebastien Jodogne, ICTEAM UCLouvain, Belgium
 *
 * This program is free software: you can redistribute it and/or
 * modify it under the terms of the GNU Affero General Public License
 * as published by the Free Software Foundation, either version 3 of
 * the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program. If not, see <http://www.gnu.org/licenses/>.
 **/


#pragma once

#include "DecodedTiledPyramid.h"

#include <Cache/LeastRecentlyUsedIndex.h>

#include <boost/thread/mutex.hpp>


namespace OrthancWSI
{
  class DecodedPyramidCache : public boost::noncopyable
  {
  public:
    class IPyramidFetcher : public boost::noncopyable
    {
    public:
      virtual ~IPyramidFetcher()
      {
      }

      virtual DecodedTiledPyramid* Fetch(const std::string& instanceId,
                                         unsigned int frameNumber) = 0;
    };

  private:
    class CachedPyramid;

    typedef std::pair<std::string, unsigned int> FrameIdentifier;  // Associates an instance ID with a frame number

    typedef Orthanc::LeastRecentlyUsedIndex<FrameIdentifier, CachedPyramid*>  Cache;

    std::unique_ptr<IPyramidFetcher> fetcher_;

    boost::mutex  mutex_;
    size_t        maxCount_;
    size_t        maxMemory_;
    size_t        memoryUsage_;
    Cache         cache_;

    bool SanityCheck();

    void MakeRoom(size_t memory);

    CachedPyramid* Store(FrameIdentifier identifier,
                         DecodedTiledPyramid* pyramid);

    DecodedPyramidCache(IPyramidFetcher* fetcher /* takes ownership */,
                          size_t maxCount,
                          size_t maxMemory);

  public:
    ~DecodedPyramidCache();

    static void InitializeInstance(IPyramidFetcher* fetcher,
                                   size_t maxSize,
                                   size_t maxMemory);

    static void FinalizeInstance();

    static DecodedPyramidCache& GetInstance();

    class Accessor : public boost::noncopyable
    {
    private:
      boost::mutex::scoped_lock lock_;
      FrameIdentifier           identifier_;
      CachedPyramid*            pyramid_;

    public:
      Accessor(DecodedPyramidCache& that,
               const std::string& instanceId,
               unsigned int frameNumber);

      bool IsValid() const
      {
        return pyramid_ != NULL;
      }

      const std::string& GetInstanceId() const
      {
        return identifier_.first;
      }

      unsigned int GetFrameNumber() const
      {
        return identifier_.second;
      }

      DecodedTiledPyramid& GetPyramid() const;
    };
  };
}
