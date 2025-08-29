/**
 * Transfers accelerator plugin for Orthanc
 * Copyright (C) 2018-2023 Osimis S.A., Belgium
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


#include "OrthancInstancesCache.h"

#include <Compatibility.h>  // For std::unique_ptr
#include <Logging.h>

namespace OrthancPlugins
{
  void OrthancInstancesCache::CacheAccessor::CheckValid() const
  {
    if (instance_ == NULL)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
    }
  }
      

  OrthancInstancesCache::CacheAccessor::CacheAccessor(OrthancInstancesCache& cache,
                                                      const std::string& instanceId) :
    lock_(cache.mutex_),
    instance_(NULL)
  {
    cache.CheckInvariants();
      
    if (cache.index_.Contains(instanceId))
    {
      // Move the instance at the end of the LRU recycling
      cache.index_.MakeMostRecent(instanceId);
        
      Content::const_iterator instance = cache.content_.find(instanceId);
      assert(instance != cache.content_.end() &&
             instance->first == instanceId &&
             instance->second != NULL);

      instance_ = instance->second;
    }
  }


  const DicomInstanceInfo& OrthancInstancesCache::CacheAccessor::GetInfo() const
  {
    CheckValid();
    return instance_->GetInfo();
  }


  void OrthancInstancesCache::CacheAccessor::GetChunk(std::string& chunk,
                                                      std::string& md5,
                                                      size_t offset,
                                                      size_t size)
  {
    CheckValid();
    return instance_->GetChunk(chunk, md5, offset, size);
  }


  void OrthancInstancesCache::CheckInvariants()
  {
#ifndef NDEBUG  
    size_t s = 0;

    assert(content_.size() == index_.GetSize());
      
    for (Content::const_iterator it = content_.begin();
         it != content_.end(); ++it)
    {
      assert(it->second != NULL);
      s += it->second->GetInfo().GetSize();

      assert(index_.Contains(it->first));
    }

    assert(s == memorySize_);
      
    if (memorySize_ > maxMemorySize_)
    {
      // It is only allowed to overtake the max memory size if the
      // cache contains a single, large DICOM instance
      assert(index_.GetSize() == 1 &&
             content_.size() == 1 &&
             memorySize_ == (content_.begin())->second->GetInfo().GetSize());
    }
#endif
  }


  void OrthancInstancesCache::RemoveOldest()
  {
    CheckInvariants();

    assert(!index_.IsEmpty());

    std::string oldest = index_.RemoveOldest();

    Content::iterator instance = content_.find(oldest);
    assert(instance != content_.end() &&
           instance->second != NULL);

    memorySize_ -= instance->second->GetInfo().GetSize();
    delete instance->second;
    content_.erase(instance);
  }


  void OrthancInstancesCache::Store(const std::string& instanceId,
                                    std::unique_ptr<SourceDicomInstance>& instance)
  {
    if (instance.get() == NULL)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_NullPointer);
    }
      
    if (index_.Contains(instanceId))
    {
      // This instance has been read by another thread since the cache
      // lookup, give up
      index_.MakeMostRecent(instanceId);
      return;
    }
    else
    {
      // Make room in the cache for the new instance
      while (!index_.IsEmpty() &&
             memorySize_ + instance->GetInfo().GetSize() > maxMemorySize_)
      {
        RemoveOldest();
      }

      CheckInvariants();

      index_.AddOrMakeMostRecent(instanceId);
      memorySize_ += instance->GetInfo().GetSize();
      content_[instanceId] = instance.release();

      CheckInvariants();
    }
  }
    

  OrthancInstancesCache::OrthancInstancesCache() :
    memorySize_(0),
    maxMemorySize_(512 * MB)  // 512 MB by default
  {
  }
    

  OrthancInstancesCache::~OrthancInstancesCache()
  {
    CheckInvariants();
      
    for (Content::iterator it = content_.begin();
         it != content_.end(); ++it)
    {
      assert(it->second != NULL);
      delete it->second;
    }
  }
  

  size_t OrthancInstancesCache::GetMemorySize() 
  {
    boost::mutex::scoped_lock lock(mutex_);
    return memorySize_;
  }
    

  size_t OrthancInstancesCache::GetMaxMemorySize()
  {
    boost::mutex::scoped_lock lock(mutex_);
    return maxMemorySize_;
  }
    

  void OrthancInstancesCache::SetMaxMemorySize(size_t size)
  {
    if (size <= 0)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
    
    boost::mutex::scoped_lock lock(mutex_);

    while (memorySize_ > size)
    {
      RemoveOldest();
    }

    maxMemorySize_ = size;
    CheckInvariants();      
  }


  void OrthancInstancesCache::GetInstanceInfo(size_t& size,
                                              std::string& md5,
                                              const std::string& instanceId)
  {
    // Check whether the instance is part of the cache
    {
      CacheAccessor accessor(*this, instanceId);
      if (accessor.IsValid())
      {
        size = accessor.GetInfo().GetSize();
        md5 = accessor.GetInfo().GetMD5();
        return;
      }
    }
      
    // The instance was not in the cache, load it
    std::unique_ptr<SourceDicomInstance> instance(new SourceDicomInstance(instanceId));
    size = instance->GetInfo().GetSize();
    md5 = instance->GetInfo().GetMD5();

    // Store the just-loaded DICOM instance into the cache
    {
      boost::mutex::scoped_lock lock(mutex_);
      Store(instanceId, instance);
    }
  }
      
    
  void OrthancInstancesCache::GetChunk(std::string& chunk,
                                       std::string& md5,
                                       const std::string& instanceId,
                                       size_t offset,
                                       size_t size)
  {
    // Check whether the instance is part of the cache
    {
      CacheAccessor accessor(*this, instanceId);
      if (accessor.IsValid())
      {
        // keeping this log for future (see TODO) LOG(INFO) << "++++ Chunk for " << instanceId << " is in cache";
        accessor.GetChunk(chunk, md5, offset, size);
        return;
      }
    }
      
    // The instance was not in the cache, load it
    std::unique_ptr<SourceDicomInstance> instance(new SourceDicomInstance(instanceId));
    instance->GetChunk(chunk, md5, offset, size);

    // Store the just-loaded DICOM instance into the cache
    {
      // keeping this log for future (see TODO) LOG(ERROR) << "---- Chunk for " << instanceId << " not in cache -> adding it";
      boost::mutex::scoped_lock lock(mutex_);
      Store(instanceId, instance);
    }
  }    


  void OrthancInstancesCache::GetChunk(std::string& chunk,
                                       std::string& md5,
                                       const TransferBucket& bucket,
                                       size_t chunkIndex)
  {
    GetChunk(chunk, md5, bucket.GetChunkInstanceId(chunkIndex),
             bucket.GetChunkOffset(chunkIndex),
             bucket.GetChunkSize(chunkIndex));
  }
}
