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


#include "ActivePushTransactions.h"

#include "../DownloadArea.h"

#include <Compatibility.h>  // For std::unique_ptr
#include <Logging.h>


namespace OrthancPlugins
{
  class ActivePushTransactions::Transaction : public boost::noncopyable
  {
  private:
    DownloadArea                 area_;
    std::vector<TransferBucket>  buckets_;
    BucketCompression            compression_;

  public:
    Transaction(const std::vector<DicomInstanceInfo>& instances,
                const std::vector<TransferBucket>& buckets,
                BucketCompression compression) :
      area_(instances),
      buckets_(buckets),
      compression_(compression)
    {
    }

    DownloadArea& GetDownloadArea()
    {
      return area_;
    }

    BucketCompression GetCompression() const
    {
      return compression_;
    }

    const TransferBucket& GetBucket(size_t index) const
    {
      if (index >= buckets_.size())
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
      }
      else
      {
        return buckets_[index];
      }
    }

    void Store(size_t bucketIndex,
               const void* data,
               size_t size)
    {
      area_.WriteBucket(GetBucket(bucketIndex), data, size, compression_);
    }
  };
    

  void ActivePushTransactions::FinalizeTransaction(const std::string& transactionUuid,
                                                   bool commit)
  {
    boost::mutex::scoped_lock  lock(mutex_);

    Content::iterator found = content_.find(transactionUuid);
    if (found == content_.end())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_UnknownResource);
    }

    assert(found->second != NULL);
    if (commit)
    {
      found->second->GetDownloadArea().Commit();
    }

    delete found->second;
    content_.erase(found);
    index_.Invalidate(transactionUuid);
  }


  ActivePushTransactions::~ActivePushTransactions()
  {
    for (Content::iterator it = content_.begin(); it != content_.end(); ++it)
    {
      LOG(WARNING) << "Discarding an uncommitted push transaction "
                   << "in the transfers accelerator: " << it->first;
        
      assert(it->second != NULL);
      delete it->second;
    }
  }
    

  void ActivePushTransactions::ListTransactions(std::vector<std::string>& target)
  {
    boost::mutex::scoped_lock  lock(mutex_);

    target.clear();
    target.reserve(content_.size());

    for (Content::const_iterator it = content_.begin();
         it != content_.end(); ++it)
    {
      target.push_back(it->first);
    }
  }

  
  std::string ActivePushTransactions::CreateTransaction(const std::vector<DicomInstanceInfo>& instances,
                                                        const std::vector<TransferBucket>& buckets,
                                                        BucketCompression compression)
  {
    std::string uuid = Orthanc::Toolbox::GenerateUuid();
    std::unique_ptr<Transaction> tmp(new Transaction(instances, buckets, compression));

    LOG(INFO) << "Creating transaction to receive " << instances.size()
              << " instances (" << ConvertToMegabytes(tmp->GetDownloadArea().GetTotalSize())
              << "MB) in push mode: " << uuid;
      
    {
      boost::mutex::scoped_lock  lock(mutex_);

      // Drop the oldest active transaction, if not enough place
      if (content_.size() == maxSize_)
      {
        std::string oldest = index_.RemoveOldest();

        Content::iterator transaction = content_.find(oldest);
        assert(transaction != content_.end() &&
               transaction->second != NULL);

        delete transaction->second;
        content_.erase(transaction);

        LOG(WARNING) << "An inactive push transaction has been discarded: " << oldest;
      }

      index_.Add(uuid);
      content_[uuid] = tmp.release();
    }

    return uuid;
  }
    

  void ActivePushTransactions::Store(const std::string& transactionUuid,
                                     size_t bucketIndex,
                                     const void* data,
                                     size_t size)
  {
    boost::mutex::scoped_lock  lock(mutex_);

    Content::iterator found = content_.find(transactionUuid);
    if (found == content_.end())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_UnknownResource);
    }
      
    assert(found->second != NULL);

    index_.MakeMostRecent(transactionUuid);
      
    found->second->Store(bucketIndex, data, size);
  }
}
