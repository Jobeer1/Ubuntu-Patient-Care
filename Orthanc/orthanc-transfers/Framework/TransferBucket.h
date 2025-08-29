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

#include "DicomInstanceInfo.h"
#include "TransferToolbox.h"

namespace OrthancPlugins
{
  class TransferBucket
  {
  private:
    struct Chunk
    {
      std::string  instanceId_;
      size_t       offset_;
      size_t       size_;
    };

    std::vector<Chunk>  chunks_;
    size_t              totalSize_;
    bool                extensible_;

  public:
    TransferBucket();

    explicit TransferBucket(const Json::Value& serialized);

    size_t GetTotalSize() const
    {
      return totalSize_;
    }

    void Reserve(size_t size)
    {
      chunks_.reserve(size);
    }
    
    size_t GetChunksCount() const
    {
      return chunks_.size();
    }

    void Serialize(Json::Value& target) const;
    
    void Clear();
    
    void AddChunk(const DicomInstanceInfo& instance,
                  size_t chunkOffset,
                  size_t chunkSize);
    
    const std::string& GetChunkInstanceId(size_t index) const;

    size_t GetChunkOffset(size_t index) const;

    size_t GetChunkSize(size_t index) const;

    void ComputePullUri(std::string& uri,
                        BucketCompression compression) const;
  };
}
