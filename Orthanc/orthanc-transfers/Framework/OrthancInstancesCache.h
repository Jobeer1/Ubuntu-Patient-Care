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


#pragma once

#include "SourceDicomInstance.h"
#include "TransferBucket.h"

#include <Cache/LeastRecentlyUsedIndex.h>
#include <Compatibility.h>  // For std::unique_ptr

#include <boost/thread/mutex.hpp>

namespace OrthancPlugins
{
  class OrthancInstancesCache : public boost::noncopyable
  {
  private:
    class CacheAccessor : public boost::noncopyable
    {
    private:
      boost::mutex::scoped_lock  lock_;
      SourceDicomInstance       *instance_;

      void CheckValid() const;
      
    public:
      CacheAccessor(OrthancInstancesCache& cache,
                    const std::string& instanceId);

      bool IsValid() const
      {
        return instance_ != NULL;
      }

      const DicomInstanceInfo& GetInfo() const;

      void GetChunk(std::string& chunk,
                    std::string& md5,
                    size_t offset,
                    size_t size);
    };

    
    typedef Orthanc::LeastRecentlyUsedIndex<std::string>  Index;
    typedef std::map<std::string, SourceDicomInstance*>   Content;

    boost::mutex   mutex_;
    Index          index_;
    Content        content_;
    size_t         memorySize_;
    size_t         maxMemorySize_;


    // The mutex must be locked!
    void CheckInvariants();
    
    // The mutex must be locked!
    void RemoveOldest();

    // The mutex must be locked!
    void Store(const std::string& instanceId,
               std::unique_ptr<SourceDicomInstance>& instance);
    

  public:
    OrthancInstancesCache();

    ~OrthancInstancesCache();

    size_t GetMemorySize();

    size_t GetMaxMemorySize();

    void SetMaxMemorySize(size_t size);
    
    void GetInstanceInfo(size_t& size,
                         std::string& md5,
                         const std::string& instanceId);
    
    void GetChunk(std::string& chunk,
                  std::string& md5,
                  const std::string& instanceId,
                  size_t offset,
                  size_t size);

    void GetChunk(std::string& chunk,
                  std::string& md5,
                  const TransferBucket& bucket,
                  size_t chunkIndex);
  };
}
