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


#include "HttpQueriesQueue.h"

#include <Logging.h>
#include <OrthancException.h>

namespace OrthancPlugins
{
  HttpQueriesQueue::Status HttpQueriesQueue::GetStatusInternal() const
  {
    if (successQueries_ == queries_.size())
    {
      return Status_Success;
    }
    else if (isFailure_)
    {
      return Status_Failure;
    }
    else
    {
      return Status_Running;
    }
  }


  HttpQueriesQueue::HttpQueriesQueue() :
    maxRetries_(0)
  {
    Reset();
  }

    
  HttpQueriesQueue::~HttpQueriesQueue()
  {
    for (size_t i = 0; i < queries_.size(); i++)
    {
      assert(queries_[i] != NULL);
      delete queries_[i];
    }
  }

    
  unsigned int HttpQueriesQueue::GetMaxRetries()
  {
    boost::mutex::scoped_lock lock(mutex_);
    return maxRetries_;
  }

    
  void HttpQueriesQueue::SetMaxRetries(unsigned int maxRetries)
  {
    boost::mutex::scoped_lock lock(mutex_);
    maxRetries_ = maxRetries;
  }

    
  void HttpQueriesQueue::Reserve(size_t size)
  {
    boost::mutex::scoped_lock lock(mutex_);
    queries_.reserve(size);
  }

    
  void HttpQueriesQueue::Reset()
  {
    boost::mutex::scoped_lock lock(mutex_);
    position_ = 0;
    downloadedSize_ = 0;
    uploadedSize_ = 0;
    successQueries_ = 0;
    isFailure_ = false;
  }
    

  void HttpQueriesQueue::Enqueue(IHttpQuery* query)
  {
    if (query == NULL)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_NullPointer);
    }
    else
    {
      boost::mutex::scoped_lock lock(mutex_);
      queries_.push_back(query);
    }
  }
    

  bool HttpQueriesQueue::ExecuteOneQuery(size_t& networkTraffic)
  {
    networkTraffic = 0;
      
    unsigned int maxRetries;
    IHttpQuery* query = NULL;

    {
      boost::mutex::scoped_lock lock(mutex_);

      maxRetries = maxRetries_;
        
      if (position_ == queries_.size() ||
          isFailure_)
      {
        return false;
      }
      else
      {
        query = queries_[position_];
        position_ ++;
      }
    }

    std::string body;

    if (query->GetMethod() == Orthanc::HttpMethod_Post ||
        query->GetMethod() == Orthanc::HttpMethod_Put)
    {
      query->ReadBody(body);              
    }       
    
    std::map<std::string, std::string> headers;
    query->GetHttpHeaders(headers);

    unsigned int retry = 0;

    for (;;)
    {
      MemoryBuffer answer;

      bool success;

      try
      {
        switch (query->GetMethod())
        {
          case Orthanc::HttpMethod_Get:
            success = peers_.DoGet(answer, query->GetPeer(), query->GetUri(), headers);
            break;

          case Orthanc::HttpMethod_Post:
            success = peers_.DoPost(answer, query->GetPeer(), query->GetUri(), body, headers);
            break;

          case Orthanc::HttpMethod_Put:
            success = peers_.DoPut(query->GetPeer(), query->GetUri(), body, headers);
            break;

          case Orthanc::HttpMethod_Delete:
            success = peers_.DoDelete(query->GetPeer(), query->GetUri(), headers);
            break;

          default:
            throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
        }
      }
      catch (Orthanc::OrthancException& e)
      {
        LOG(ERROR) << "Unhandled exception during an HTTP query to peer \"" 
                   << query->GetPeer() <<  " " << query->GetUri() + "\": " << e.What();
        success = false;
      }

      if (success)
      {
        size_t downloaded = 0;
        size_t uploaded = 0;

        if (query->GetMethod() == Orthanc::HttpMethod_Get ||
            query->GetMethod() == Orthanc::HttpMethod_Post)
        {
          query->HandleAnswer(answer.GetData(), answer.GetSize());
          downloaded = answer.GetSize();
        }

        if (query->GetMethod() == Orthanc::HttpMethod_Put ||
            query->GetMethod() == Orthanc::HttpMethod_Post)
        {
          uploaded = body.size();
        }
          
        networkTraffic = downloaded + uploaded;
            
        {
          boost::mutex::scoped_lock lock(mutex_);
          downloadedSize_ += downloaded;
          uploadedSize_ += uploaded;
          successQueries_ ++;

          if (successQueries_ == queries_.size())
          {
            completed_.notify_all();
          }

          return true;
        }
      }
      else
      {
        // Error: Let's retry
        retry ++;

        if (retry <= maxRetries)
        {
          // Wait 1 second before retrying
          boost::this_thread::sleep(boost::posix_time::seconds(1));
        }
        else
        {
          if (maxRetries > 0)
          {
            LOG(ERROR) << "Reached the maximum number of retries for a HTTP query to peer " << query->GetPeer() <<  " " << query->GetUri();
          }

          {
            boost::mutex::scoped_lock lock(mutex_);
            isFailure_ = true;
            completed_.notify_all();
          }

          return false;
        }
      }
    }
  }


  HttpQueriesQueue::Status HttpQueriesQueue::WaitComplete(unsigned int timeoutMS)
  {
    boost::mutex::scoped_lock lock(mutex_);

    Status status = GetStatusInternal();

    if (status == Status_Running)
    {
      completed_.timed_wait(lock, boost::posix_time::milliseconds(timeoutMS));
      return GetStatusInternal();
    }
    else
    {
      return status;
    }
  }


  void HttpQueriesQueue::WaitComplete()
  {
    boost::mutex::scoped_lock lock(mutex_);

    while (GetStatusInternal() == Status_Running)
    {
      completed_.timed_wait(lock, boost::posix_time::milliseconds(200));
    }
  }


  void HttpQueriesQueue::GetStatistics(size_t& scheduledQueriesCount,
                                       size_t& successQueriesCount,
                                       uint64_t& downloadedSize,
                                       uint64_t& uploadedSize)
  {
    boost::mutex::scoped_lock lock(mutex_);
    scheduledQueriesCount = queries_.size();
    successQueriesCount = successQueries_;
    downloadedSize = downloadedSize_;
    uploadedSize = uploadedSize_;
  }
}
