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

#include "MemoryCache.h"

namespace OrthancPlugins
{
  class MemoryCache::Payload : public boost::noncopyable
  {
  private:
    bool                     hasExpiration_;
    boost::posix_time::ptime expiration_;
    std::string              value_;

  public:
    Payload(const std::string& value,
            unsigned int validity) :
      value_(value)
    {
      if (validity == 0)
      {
        hasExpiration_ = false;
      }
      else
      {
        hasExpiration_ = true;
        expiration_ = (boost::posix_time::second_clock::local_time() +
                       boost::posix_time::seconds(validity));
      }
    }

    bool HasExpired() const
    {
      return (hasExpiration_ &&
              boost::posix_time::second_clock::local_time() >= expiration_);
    }
      
    bool GetValue(std::string& target) const
    {
      if (HasExpired())
      {
        return false;
      }
      else
      {
        target = value_;
        return true;          
      }
    }
  };
    
   
  void MemoryCache::RemoveOldest()
  {
    Payload* payload = NULL;
    index_.RemoveOldest(payload);
    assert(payload != NULL);
    delete payload;
  }

  
  void MemoryCache::InvalidateInternal(const std::string& key)
  {
    Payload* payload = NULL;

    if (index_.Contains(key, payload))
    {
      assert(payload != NULL);
      delete payload;
      index_.Invalidate(key);
    }
  }
    

  MemoryCache::MemoryCache(unsigned int maxSize) :
    maxSize_(maxSize)
  {
    if (maxSize_ == 0)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
  }

    
  MemoryCache::~MemoryCache()
  {
    while (!index_.IsEmpty())
    {
      RemoveOldest();
    }
  }
    

  void MemoryCache::Invalidate(const std::string& key)
  {
    boost::mutex::scoped_lock lock(mutex_);
    InvalidateInternal(key);
  }


  void MemoryCache::Store(const std::string& key,
                          const std::string& value,
                          unsigned int expiration /* in seconds */)
  {
    boost::mutex::scoped_lock lock(mutex_);

    InvalidateInternal(key);

    if (index_.GetSize() == maxSize_)
    {
      // The cache is full: Make some room
      RemoveOldest();
    }
        
    index_.Add(key, new Payload(value, expiration));
  }


  bool MemoryCache::Retrieve(std::string& value,
                             const std::string& key)
  {
    boost::mutex::scoped_lock lock(mutex_);

    Payload* payload = NULL;
      
    if (!index_.Contains(key, payload))
    {
      return false;
    }
      
    assert(payload != NULL);
      
    if (payload->GetValue(value))
    {
      index_.MakeMostRecent(key);
      return true;
    }
    else
    {
      // The value has expired in the cache: Invalidate it
      delete payload;
      index_.Invalidate(key);
      return false;
    }
  }
}
