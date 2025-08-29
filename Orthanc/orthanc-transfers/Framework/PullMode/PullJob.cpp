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


#include "PullJob.h"

#include "BucketPullQuery.h"
#include "../HttpQueries/HttpQueriesRunner.h"
#include "../TransferScheduler.h"

#include <Compatibility.h>  // For std::unique_ptr
#include <Logging.h>


namespace OrthancPlugins
{
  class PullJob::CommitState : public IState
  {
  private:
    const PullJob&               job_;
    std::unique_ptr<DownloadArea>  area_;

  public:
    CommitState(const PullJob& job,
                DownloadArea* area /* takes ownership */) :
      job_(job),
      area_(area)
    {
    }

    virtual StateUpdate* Step()
    {
      area_->Commit();
      return StateUpdate::Success();
    }

    virtual void Stop(OrthancPluginJobStopReason reason)
    {
    }
  };


  class PullJob::PullBucketsState : public IState
  {
  private:
    const PullJob&                    job_;
    JobInfo&                          info_;
    HttpQueriesQueue                  queue_;
    std::unique_ptr<DownloadArea>       area_;
    std::unique_ptr<HttpQueriesRunner>  runner_;

    void UpdateInfo()
    {
      size_t scheduledQueriesCount, completedQueriesCount;
      uint64_t uploadedSize, downloadedSize;
      queue_.GetStatistics(scheduledQueriesCount, completedQueriesCount, downloadedSize, uploadedSize);

      info_.SetContent("DownloadedSizeMB", ConvertToMegabytes(downloadedSize));
      info_.SetContent("CompletedHttpQueries", static_cast<unsigned int>(completedQueriesCount));

      if (runner_.get() != NULL)
      {
        float speed;
        runner_->GetSpeed(speed);
        info_.SetContent("NetworkSpeedKBs", static_cast<unsigned int>(speed));
      }
            
      // The "2" below corresponds to the "LookupInstancesState"
      // and "CommitState" steps (which prevents division by zero)
      info_.SetProgress(static_cast<float>(1 /* LookupInstancesState */ + completedQueriesCount) / 
                        static_cast<float>(2 + scheduledQueriesCount));
    }

  public:
    PullBucketsState(const PullJob&  job,
                     JobInfo& info,
                     const TransferScheduler& scheduler) :
      job_(job),
      info_(info),
      area_(new DownloadArea(scheduler))
    {
      const std::string baseUrl = job.peers_.GetPeerUrl(job.query_.GetPeer());

      std::vector<TransferBucket> buckets;
      scheduler.ComputePullBuckets(buckets, job.targetBucketSize_, 2 * job.targetBucketSize_,
                                   baseUrl, job.query_.GetCompression());
      area_.reset(new DownloadArea(scheduler));

      queue_.SetMaxRetries(job.maxHttpRetries_);
      queue_.Reserve(buckets.size());
        
      for (size_t i = 0; i < buckets.size(); i++)
      {
        queue_.Enqueue(new BucketPullQuery(*area_, buckets[i], job.query_.GetPeer(), job.query_.GetCompression()));
      }

      info_.SetContent("TotalInstances", static_cast<unsigned int>(scheduler.GetInstancesCount()));
      info_.SetContent("TotalSizeMB", ConvertToMegabytes(scheduler.GetTotalSize()));
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
          return StateUpdate::Next(new CommitState(job_, area_.release()));

        case HttpQueriesQueue::Status_Failure:
          return StateUpdate::Failure();

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
    

  class PullJob::LookupInstancesState : public IState
  {
  private:
    const PullJob&  job_;
    JobInfo&        info_;

  public:
    LookupInstancesState(const PullJob& job,
                         JobInfo& info) :
      job_(job),
      info_(info)
    {
      if (job_.query_.HasOriginator())
      {
        info_.SetContent("Originator", job_.query_.GetOriginator());  
      }
      info_.SetContent("Resources", job_.query_.GetResources());
      info_.SetContent("Peer", job_.query_.GetPeer());
      info_.SetContent("Compression", EnumerationToString(job_.query_.GetCompression()));
    }

    virtual StateUpdate* Step()
    {
      std::string lookup;
      Orthanc::Toolbox::WriteFastJson(lookup, job_.query_.GetResources());

      Json::Value answer;
      std::map<std::string, std::string> headers;
      job_.query_.GetHttpHeaders(headers);

      headers["Content-Type"] = "application/json";

      if (!DoPostPeer(answer, job_.peers_, job_.peerIndex_, URI_LOOKUP, lookup, job_.maxHttpRetries_, headers))
      {
        LOG(ERROR) << "Cannot retrieve the list of instances to pull from peer \"" 
                   << job_.query_.GetPeer()
                   << "\" (check that it has the transfers accelerator plugin installed)";
        return StateUpdate::Failure();
      } 

      if (answer.type() != Json::objectValue ||
          !answer.isMember(KEY_INSTANCES) ||
          !answer.isMember(KEY_ORIGINATOR_UUID) ||
          answer[KEY_INSTANCES].type() != Json::arrayValue ||
          answer[KEY_ORIGINATOR_UUID].type() != Json::stringValue)
      {
        LOG(ERROR) << "Bad network protocol from peer: " << job_.query_.GetPeer();
        return StateUpdate::Failure();
      }

      if (job_.query_.HasOriginator() &&
          job_.query_.GetOriginator() != answer[KEY_ORIGINATOR_UUID].asString())
      {
        LOG(ERROR) << "Invalid originator, check out the \"" << KEY_REMOTE_SELF
                   << "\" configuration option of peer: " << job_.query_.GetPeer();
        return StateUpdate::Failure();
      }

      TransferScheduler  scheduler;

      for (Json::Value::ArrayIndex i = 0; i < answer[KEY_INSTANCES].size(); i++)
      {
        DicomInstanceInfo instance(answer[KEY_INSTANCES][i]);
        scheduler.AddInstance(instance);
      }

      if (scheduler.GetInstancesCount() == 0)
      {
        // We're already done: No instance to be retrieved
        return StateUpdate::Success();
      }
      else
      {
        return StateUpdate::Next(new PullBucketsState(job_, info_, scheduler));
      }
    }

    virtual void Stop(OrthancPluginJobStopReason reason)
    {
    }
  };


  StatefulOrthancJob::StateUpdate* PullJob::CreateInitialState(JobInfo& info)
  {
    return StateUpdate::Next(new LookupInstancesState(*this, info));
  }
    
    
  PullJob::PullJob(const TransferQuery& query,
                   size_t threadsCount,
                   size_t targetBucketSize,
                   unsigned int maxHttpRetries) :
    StatefulOrthancJob(JOB_TYPE_PULL),
    query_(query),
    threadsCount_(threadsCount),
    targetBucketSize_(targetBucketSize),
    maxHttpRetries_(maxHttpRetries)
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
