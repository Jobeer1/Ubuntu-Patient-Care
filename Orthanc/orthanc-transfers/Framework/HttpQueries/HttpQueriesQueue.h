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

#include "IHttpQuery.h"

#include "../../Resources/Orthanc/Plugins/OrthancPluginCppWrapper.h"

#include <boost/thread/mutex.hpp>
#include <boost/thread/condition_variable.hpp>


namespace OrthancPlugins
{
  class HttpQueriesQueue : public boost::noncopyable
  {
  public:
    enum Status
    {
      Status_Running,
      Status_Success,
      Status_Failure
    };

  private:
    OrthancPeers                  peers_;
    boost::mutex                  mutex_;
    boost::condition_variable     completed_;
    std::vector<IHttpQuery*>      queries_;
    unsigned int                  maxRetries_;

    size_t                        position_;
    uint64_t                      downloadedSize_;   // GET answers + POST answers
    uint64_t                      uploadedSize_;     // PUT body + POST body
    size_t                        successQueries_;
    bool                          isFailure_;


    Status GetStatusInternal() const;

  public:
    HttpQueriesQueue();

    ~HttpQueriesQueue();

    OrthancPeers& GetOrthancPeers()
    {
      return peers_;
    }

    unsigned int GetMaxRetries();

    void SetMaxRetries(unsigned int maxRetries);

    void Reserve(size_t size);

    void Reset();

    void Enqueue(IHttpQuery* query);  // Takes ownership

    bool ExecuteOneQuery(size_t& networkTraffic);

    Status WaitComplete(unsigned int timeoutMS);
    
    void WaitComplete();

    void GetStatistics(size_t& scheduledQueriesCount,
                       size_t& successQueriesCount,
                       uint64_t& downloadedSize,
                       uint64_t& uploadedSize);
  };
}
