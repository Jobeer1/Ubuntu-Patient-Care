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

#include "../TransferBucket.h"

#include <Cache/LeastRecentlyUsedIndex.h>

#include <boost/thread/mutex.hpp>

namespace OrthancPlugins
{
  class ActivePushTransactions : public boost::noncopyable
  {
  private:
    class Transaction;
    
    typedef Orthanc::LeastRecentlyUsedIndex<std::string>  Index;
    typedef std::map<std::string, Transaction*>           Content;

    boost::mutex  mutex_;
    Content       content_;
    Index         index_;
    size_t        maxSize_;

    void FinalizeTransaction(const std::string& transactionUuid,
                             bool commit);

  public:
    explicit ActivePushTransactions(size_t maxSize) :
      maxSize_(maxSize)
    {
    }

    ~ActivePushTransactions();
    
    void ListTransactions(std::vector<std::string>& target);

    std::string CreateTransaction(const std::vector<DicomInstanceInfo>& instances,
                                  const std::vector<TransferBucket>& buckets,
                                  BucketCompression compression);

    void Store(const std::string& transactionUuid,
               size_t bucketIndex,
               const void* data,
               size_t size);

    void Commit(const std::string& transactionUuid)
    {
      FinalizeTransaction(transactionUuid, true);
    }

    void Discard(const std::string& transactionUuid)
    {
      FinalizeTransaction(transactionUuid, false);
    }
  };
}
