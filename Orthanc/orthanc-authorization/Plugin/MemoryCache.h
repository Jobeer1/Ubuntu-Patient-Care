/**
 * Advanced authorization plugin for Orthanc
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

#include "ICacheFactory.h"

#include <Cache/LeastRecentlyUsedIndex.h>

#include <boost/thread/mutex.hpp>

namespace OrthancPlugins
{
  class MemoryCache : public ICache
  {
  public:
    class Factory : public ICacheFactory
    {
    private:
      unsigned int   maxSize_;
      
    public:
      explicit Factory(unsigned int maxSize) :
        maxSize_(maxSize)
      {
      }
      
      virtual ICache *Create() ORTHANC_OVERRIDE
      {
        return new MemoryCache(maxSize_);
      }
    };
    
  private:
    class Payload;
    
    typedef Orthanc::LeastRecentlyUsedIndex<std::string, Payload*>  Index;

    boost::mutex  mutex_;
    unsigned int  maxSize_;
    Index         index_;
   
    void RemoveOldest();

    void InvalidateInternal(const std::string& key);
    
  public:
    explicit MemoryCache(unsigned int maxSize);
    
    ~MemoryCache();

    virtual void Invalidate(const std::string& key) ORTHANC_OVERRIDE;

    virtual void Store(const std::string& key,
                       const std::string& value,
                       unsigned int expiration /* in seconds */) ORTHANC_OVERRIDE;

    virtual bool Retrieve(std::string& value,
                          const std::string& key) ORTHANC_OVERRIDE;
  };
}
