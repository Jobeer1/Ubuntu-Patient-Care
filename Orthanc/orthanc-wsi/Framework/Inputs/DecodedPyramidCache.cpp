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


#include "../PrecompiledHeadersWSI.h"
#include "DecodedPyramidCache.h"


static std::unique_ptr<OrthancWSI::DecodedPyramidCache>  singleton_;

namespace OrthancWSI
{
  class DecodedPyramidCache::CachedPyramid : public boost::noncopyable
  {
  private:
    std::unique_ptr<DecodedTiledPyramid>  pyramid_;
    size_t                                memory_;

  public:
    explicit CachedPyramid(DecodedTiledPyramid* pyramid) :
      pyramid_(pyramid)
    {
      if (pyramid == NULL)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_NullPointer);
      }
      else
      {
        memory_ = pyramid->GetMemoryUsage();
      }
    }

    DecodedTiledPyramid& GetPyramid() const
    {
      assert(pyramid_ != NULL);
      return *pyramid_;
    }

    size_t GetMemoryUsage() const
    {
      return memory_;
    }
  };


  bool DecodedPyramidCache::SanityCheck()
  {
    return (cache_.GetSize() < maxCount_);
  }


  void DecodedPyramidCache::MakeRoom(size_t memory)
  {
    // Mutex must be locked

    while (cache_.GetSize() >= maxCount_ ||
           (!cache_.IsEmpty() &&
            maxMemory_ != 0 &&
            memoryUsage_ + memory > maxMemory_))
    {
      CachedPyramid* oldest = NULL;
      cache_.RemoveOldest(oldest);

      if (oldest == NULL)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
      }
      else
      {
        memoryUsage_ -= oldest->GetMemoryUsage();
        delete oldest;
      }
    }

    assert(SanityCheck());
  }


  DecodedPyramidCache::CachedPyramid * DecodedPyramidCache::Store(FrameIdentifier identifier,
                                                                  DecodedTiledPyramid *pyramid)
  {
    // Mutex must be locked

    std::unique_ptr<CachedPyramid> payload(new CachedPyramid(pyramid));
    CachedPyramid* result;

    if (cache_.Contains(identifier, result))
    {
      // This element has already been cached by another thread
      if (result == NULL)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
      }

      // Tag the series as the most recently used
      cache_.MakeMostRecent(identifier);

      return result;
    }
    else
    {
      result = payload.get();

      MakeRoom(payload->GetMemoryUsage());

      memoryUsage_ += payload->GetMemoryUsage();

      // Add a new element to the cache and make it the most
      // recently used entry
      cache_.Add(identifier, payload.release());

      assert(SanityCheck());
      return result;
    }
  }


  DecodedPyramidCache::DecodedPyramidCache(IPyramidFetcher *fetcher,
                                               size_t maxCount,
                                               size_t maxMemory):
    fetcher_(fetcher),
    maxCount_(maxCount),
    maxMemory_(maxMemory),  // 256 MB
    memoryUsage_(0)
  {
    if (fetcher == NULL)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_NullPointer);
    }

    if (maxCount == 0)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }

    assert(SanityCheck());
  }


  DecodedPyramidCache::~DecodedPyramidCache()
  {
    while (!cache_.IsEmpty())
    {
      CachedPyramid* pyramid = NULL;
      cache_.RemoveOldest(pyramid);

      if (pyramid != NULL)
      {
        delete pyramid;
      }
    }
  }


  void DecodedPyramidCache::InitializeInstance(IPyramidFetcher *fetcher,
                                                 size_t maxSize,
                                                 size_t maxMemory)
  {
    if (singleton_.get() == NULL)
    {
      singleton_.reset(new DecodedPyramidCache(fetcher, maxSize, maxMemory));
    }
    else
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
    }
  }


  void DecodedPyramidCache::FinalizeInstance()
  {
    if (singleton_.get() == NULL)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
    }
    else
    {
      singleton_.reset(NULL);
    }
  }


  DecodedPyramidCache & DecodedPyramidCache::GetInstance()
  {
    if (singleton_.get() == NULL)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
    }
    else
    {
      return *singleton_;
    }
  }


  DecodedPyramidCache::Accessor::Accessor(DecodedPyramidCache& that,
                                            const std::string &instanceId,
                                            unsigned int frameNumber):
    lock_(that.mutex_),
    identifier_(instanceId, frameNumber),
    pyramid_(NULL)
  {
    if (that.cache_.Contains(identifier_, pyramid_))
    {
      if (pyramid_ == NULL)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
      }

      // Tag the series as the most recently used
      that.cache_.MakeMostRecent(identifier_);
    }
    else
    {
      // Unlock the mutex as creating the pyramid is a time-consuming operation
      lock_.unlock();

      std::unique_ptr<DecodedTiledPyramid> payload(that.fetcher_->Fetch(instanceId, frameNumber));

      // Re-lock, as we now modify the cache
      lock_.lock();
      pyramid_ = that.Store(identifier_, payload.release());
    }
  }


  DecodedTiledPyramid & DecodedPyramidCache::Accessor::GetPyramid() const
  {
    if (IsValid())
    {
      return pyramid_->GetPyramid();
    }
    else
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
    }
  }
}
