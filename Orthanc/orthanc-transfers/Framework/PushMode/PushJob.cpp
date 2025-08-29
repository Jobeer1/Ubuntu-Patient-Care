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


#include "PushJob.h"

#include "BucketPushQuery.h"
#include "../HttpQueries/HttpQueriesRunner.h"
#include "../TransferScheduler.h"

#include <boost/algorithm/string.hpp> // For boost::iequals and boost::split
#include <Compatibility.h> // For std::unique_ptr
#include <Logging.h>

namespace OrthancPlugins
{

  /**
   * This is a helper function to extract cookie name and value into a single
   * string from the response http headers.  The extracted cookie string can
   * then be used to set the "Cookie" header in subsequent requests.
   *
   * Orthanc appears not to support multiple "Set-Cookie" headers in the
   * response, so only the last `set-cookie` header is included in the headers
   * map. This means that if the server responds with multiple cookies, only the
   * last one will be extracted.
   *
   * This is a very simlified implementation for use by the Accelerator plugin.
   * It is not a substitute for a full cookie jar implementation. However, with
   * the Authenication plugin, a simplified implementation where any cookie from
   * the initial request can be used in the finite number of subsequent
   * requests is sufficient.
   */
  static std::string ExtractCookiesFromHeaders(const std::map<std::string, std::string> &headers)
  {
    // an array of cookies returned by the server
    std::vector<std::string> cookies;

    for (std::map<std::string, std::string>::const_iterator it = headers.begin(); it != headers.end(); ++it)
    {
      // Check if the header is a Set-Cookie header (case-insensitive)
      if (boost::iequals(it->first, "set-cookie"))
      {
        // Set-Cookie headers are formatted as:
        // Set-Cookie: <cookie-name>=<cookie-value>; <attributes>
        // or
        // Set-Cookie: <cookie-name>=<cookie-value>
        //
        // We only need the cookie name and value, so we split on ';'
        // and take the first part

        // Split the cookie string by ';' and take the first part (the actual cookie)
        std::vector<std::string> tokens;
        Orthanc::Toolbox::SplitString(tokens, it->second, ';');
        
        if (!tokens.empty())
        {
          std::string cookie = tokens[0];
          std::string trimmedCookie = boost::trim_copy(cookie);
          cookies.push_back(trimmedCookie);
        }
      }
    }

    // Join all cookies with "; "
    std::ostringstream result;
    for (size_t i = 0; i < cookies.size(); ++i)
    {
      if (i > 0)
      {
        result << "; ";
      }
      
      result << cookies[i];
    }

    return result.str();
  }

  class PushJob::FinalState : public IState
  {
  private:
    const PushJob&  job_;
    JobInfo&        info_;
    std::string     transactionUri_;
    bool            isCommit_;
    /**
     * Stores any cookies to be sent in the http request. These
     * cookies are obtained from the response headers of the
     * initialisation request for the push job.
     */
    std::string     cookieHeader_;

  public:
    FinalState(const PushJob& job,
               JobInfo& info,
               const std::string& transactionUri,
               bool isCommit,
               const std::string &cookieHeader) :
      job_(job),
      info_(info),
      transactionUri_(transactionUri),
      isCommit_(isCommit),
      cookieHeader_(cookieHeader)
    {
    }

    virtual StateUpdate* Step()
    {
      Json::Value answer;
      bool success = false;
      std::map<std::string, std::string> headers;
      job_.query_.GetHttpHeaders(headers);

      if (!cookieHeader_.empty())
      {
        headers["Cookie"] = cookieHeader_;
      }

      if (isCommit_)
      {
        success = DoPostPeer(answer, job_.peers_, job_.peerIndex_, transactionUri_ + "/commit", "", job_.maxHttpRetries_, headers, job_.commitTimeout_);
      }
      else
      {
        success = DoDeletePeer(job_.peers_, job_.peerIndex_, transactionUri_, job_.maxHttpRetries_, headers);
      }
        
      if (!success)
      {
        if (isCommit_)
        {
          LOG(ERROR) << "Cannot commit push transaction on remote peer: " // TODO: add job ID
                     << job_.query_.GetPeer();
        }
          
        return StateUpdate::Failure();
      }
      else if (isCommit_)
      {
        return StateUpdate::Success();
      }
      else
      {
        return StateUpdate::Failure();
      }
    }

    virtual void Stop(OrthancPluginJobStopReason reason)
    {
    }
  };


  class PushJob::PushBucketsState : public IState
  {
  private:
    const PushJob&                     job_;
    JobInfo&                           info_;
    std::string                        transactionUri_;
    HttpQueriesQueue                   queue_;
    std::unique_ptr<HttpQueriesRunner> runner_;
    /**
     * Stores any cookies to be sent in the http request. These
     * cookies are obtained from the response headers of the
     * initialisation request for the push job.
     */
    std::string                        cookieHeader_;

    void UpdateInfo()
    {
      size_t scheduledQueriesCount, completedQueriesCount;
      uint64_t uploadedSize, downloadedSize;
      queue_.GetStatistics(scheduledQueriesCount, completedQueriesCount, downloadedSize, uploadedSize);

      info_.SetContent("UploadedSizeMB", ConvertToMegabytes(uploadedSize));
      info_.SetContent("CompletedHttpQueries", static_cast<unsigned int>(completedQueriesCount));

      if (runner_.get() != NULL)
      {
        float speed;
        runner_->GetSpeed(speed);
        info_.SetContent("NetworkSpeedKBs", static_cast<unsigned int>(speed));
      }
            
      // The "2" below corresponds to the "CreateTransactionState"
      // and "FinalState" steps (which prevents division by zero)
      info_.SetProgress(static_cast<float>(1 /* CreateTransactionState */ + completedQueriesCount) / 
                        static_cast<float>(2 + scheduledQueriesCount));
    }

  public:
    PushBucketsState(const PushJob&  job,
                     JobInfo& info,
                     const std::string& transactionUri,
                     const std::vector<TransferBucket>& buckets,
                     const std::string& cookieHeader) : 
      job_(job),
      info_(info),
      transactionUri_(transactionUri),
      cookieHeader_(cookieHeader)
    {
      std::map<std::string, std::string> headers;
      job_.query_.GetHttpHeaders(headers);

      headers["Content-Type"] = "application/octet-stream";
      if (!cookieHeader_.empty())
      {
        headers["Cookie"] = cookieHeader_;
      }

      queue_.SetMaxRetries(job.maxHttpRetries_);
      queue_.Reserve(buckets.size());
        
      for (size_t i = 0; i < buckets.size(); i++)
      {
        queue_.Enqueue(new BucketPushQuery(job.cache_, buckets[i], job.query_.GetPeer(),
                                           transactionUri_, i, job.query_.GetCompression(), headers));
      }

      UpdateInfo();
    }
      
    virtual StateUpdate* Step()
    {
      if (runner_.get() == NULL)
      {
        runner_.reset(new HttpQueriesRunner(queue_, job_.threadsCount_));
      }

      HttpQueriesQueue::Status status = queue_.WaitComplete(200);

      UpdateInfo();

      switch (status)
      {
        case HttpQueriesQueue::Status_Running:
          return StateUpdate::Continue();

        case HttpQueriesQueue::Status_Success:
          // Commit transaction on remote peer
          return StateUpdate::Next(new FinalState(job_, info_, transactionUri_, true, cookieHeader_));

        case HttpQueriesQueue::Status_Failure:
          // Discard transaction on remote peer
          return StateUpdate::Next(new FinalState(job_, info_, transactionUri_, false, cookieHeader_));

        default:
          throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
      }        
    }

    virtual void Stop(OrthancPluginJobStopReason reason)
    {
      // Cancel the running download threads
      runner_.reset();
    }
  };


  class PushJob::CreateTransactionState : public IState
  {
  private:
    const PushJob&                job_;
    JobInfo&                      info_;
    std::string                   createTransaction_;
    std::vector<TransferBucket>   buckets_;

  public:
    CreateTransactionState(const PushJob& job,
                           JobInfo& info) :
      job_(job),
      info_(info)
    {
      TransferScheduler scheduler;
      scheduler.ParseListOfResources(job_.cache_, job_.query_.GetResources());

      Json::Value push;      
      scheduler.FormatPushTransaction(push, buckets_,
                                      job.targetBucketSize_, 2 * job.targetBucketSize_,
                                      job_.query_.GetCompression());

      Orthanc::Toolbox::WriteFastJson(createTransaction_, push);

      info_.SetContent("Resources", job_.query_.GetResources());
      info_.SetContent("Peer", job_.query_.GetPeer());
      info_.SetContent("Compression", EnumerationToString(job_.query_.GetCompression()));
      info_.SetContent("TotalInstances", static_cast<unsigned int>(scheduler.GetInstancesCount()));
      info_.SetContent("TotalSizeMB", ConvertToMegabytes(scheduler.GetTotalSize()));
    }

    virtual StateUpdate* Step()
    {
      Json::Value answer;
      std::map<std::string, std::string> headers;
      std::map<std::string, std::string> answerHeaders;
      job_.query_.GetHttpHeaders(headers);

      headers["Content-Type"] = "application/json";

      if (!DoPostPeer(answer, answerHeaders, job_.peers_, job_.peerIndex_, URI_PUSH, createTransaction_, job_.maxHttpRetries_, headers, job_.commitTimeout_))
      {
        LOG(ERROR) << "Cannot create a push transaction to peer \"" 
                   << job_.query_.GetPeer()
                   << "\" (check that it has the transfers accelerator plugin installed)";
        return StateUpdate::Failure();
      } 

      if (answer.type() != Json::objectValue ||
          !answer.isMember(KEY_PATH) ||
          answer[KEY_PATH].type() != Json::stringValue)
      {
        LOG(ERROR) << "Bad network protocol from peer: " << job_.query_.GetPeer();
        return StateUpdate::Failure();
      }

      std::string transactionUri = answer[KEY_PATH].asString();
      /**
       * Some load balancers such as AWS Application Load Balancer use Sticky
       * Session Cookies, which are set by the load balancer on a request. If
       * subsequent requests include these cookies, then the load balancer will
       * route the request to the same backend server.
       *
       * This is important for the Accelerated Transfers plugin as the push
       * transactions are statefull, meaning all requests (initialisation, each
       * bucket and commit) must be sent to the same backend server, otherwise
       * the transfer job will fail.
       *
       * In order to support cookie based sticky sessions, we need to extract the
       * cookies from the initilisation request and include them in the
       * subsequent requests for this transfer job.answerHeaders
       *
       * Currently, the answerHeaders maps only contains 1 Set-Cookie headers
       * (the last one).  This is a limitation of the current HttpClient
       * implementation. Meaning that any subsequent requests in this transfer
       * job will only include the last `Set-Cookie` header from the initial
       * request.
       *
       * The cookieHeader is passed into each subsequent JobStates
       * (PushBucketsState and FinalState) so that the cookies are included in
       * the headers of each request.
       */
      std::string cookieHeader = ExtractCookiesFromHeaders(answerHeaders);

      return StateUpdate::Next(new PushBucketsState(job_, info_, transactionUri, buckets_, cookieHeader));
    }

    virtual void Stop(OrthancPluginJobStopReason reason)
    {
    }
  };


  StatefulOrthancJob::StateUpdate* PushJob::CreateInitialState(JobInfo& info)
  {
    return StateUpdate::Next(new CreateTransactionState(*this, info));
  }
    
    
  PushJob::PushJob(const TransferQuery& query,
                   OrthancInstancesCache& cache,
                   size_t threadsCount,
                   size_t targetBucketSize,
                   unsigned int maxHttpRetries,
                   unsigned int commitTimeout) :
    StatefulOrthancJob(JOB_TYPE_PUSH),
    cache_(cache),
    query_(query),
    threadsCount_(threadsCount),
    targetBucketSize_(targetBucketSize),
    maxHttpRetries_(maxHttpRetries),
    commitTimeout_(commitTimeout)
  {
    if (!peers_.LookupName(peerIndex_, query_.GetPeer()))
    {
      LOG(ERROR) << "Unknown Orthanc peer: " << query_.GetPeer();
      throw Orthanc::OrthancException(Orthanc::ErrorCode_UnknownResource);
    }

    Json::Value serialized;
    query.Serialize(serialized);
    UpdateSerialized(serialized);
  }
}
