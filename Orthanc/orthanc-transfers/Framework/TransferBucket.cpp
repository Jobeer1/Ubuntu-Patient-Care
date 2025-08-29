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


#include "TransferBucket.h"

#include <Logging.h>
#include <OrthancException.h>


namespace OrthancPlugins
{
  TransferBucket::TransferBucket() :
    totalSize_(0),
    extensible_(true)
  {
  }

    
  TransferBucket::TransferBucket(const Json::Value& serialized) :
    totalSize_(0),
    extensible_(false)
  {
    if (serialized.type() != Json::arrayValue)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
    }

    chunks_.reserve(serialized.size());

    for (Json::Value::ArrayIndex i = 0; i < serialized.size(); i++)
    {
      if (serialized[i].type() != Json::objectValue ||
          !serialized[i].isMember(KEY_ID) ||
          !serialized[i].isMember(KEY_OFFSET) ||
          !serialized[i].isMember(KEY_SIZE) ||
          serialized[i][KEY_ID].type() != Json::stringValue ||
          serialized[i][KEY_OFFSET].type() != Json::stringValue ||
          serialized[i][KEY_SIZE].type() != Json::stringValue)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
      }
      else
      {
        try
        {
          Chunk chunk;
          chunk.instanceId_ = serialized[i][KEY_ID].asString();
          chunk.offset_ = boost::lexical_cast<size_t>(serialized[i][KEY_OFFSET].asString());
          chunk.size_ = boost::lexical_cast<size_t>(serialized[i][KEY_SIZE].asString());

          chunks_.push_back(chunk);
          totalSize_ += chunk.size_;
        }
        catch (boost::bad_lexical_cast&)
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
        }
      }
    }
  }


  void TransferBucket::Serialize(Json::Value& target) const
  {
    target = Json::arrayValue;

    for (size_t i = 0; i < chunks_.size(); i++)
    {
      Json::Value item = Json::objectValue;
      item[KEY_ID] = chunks_[i].instanceId_;
      item[KEY_OFFSET] = boost::lexical_cast<std::string>(chunks_[i].offset_);
      item[KEY_SIZE] = boost::lexical_cast<std::string>(chunks_[i].size_);
      target.append(item);
    }
  }
    
  void TransferBucket::Clear()
  {
    chunks_.clear();
    totalSize_ = 0;
    extensible_ = true;
  }
    
    
  void TransferBucket::AddChunk(const DicomInstanceInfo& instance,
                                size_t chunkOffset,
                                size_t chunkSize)
  {
    if (chunkOffset + chunkSize > instance.GetSize())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }

    if (!extensible_)
    {
      LOG(ERROR) << "Cannot add a new chunk after a truncated instance";
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
    }
      
    if (!chunks_.empty() &&
        chunkOffset != 0)
    {
      LOG(ERROR) << "Only the first chunk can have non-zero offset in a transfer bucket";
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }

    if (chunkSize == 0)
    {
      // Ignore empty chunks
      return;
    }

    if (!chunks_.empty() &&
        chunkSize != instance.GetSize())
    {
      // Prevents adding new chunk after an incomplete instance
      extensible_ = false;
    }

    Chunk chunk;
    chunk.instanceId_ = instance.GetId();
    chunk.offset_ = chunkOffset;
    chunk.size_ = chunkSize;

    chunks_.push_back(chunk);
    totalSize_ += chunkSize;
  }
    

  const std::string& TransferBucket::GetChunkInstanceId(size_t index) const
  {
    if (index >= chunks_.size())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
    else
    {
      return chunks_[index].instanceId_;
    }
  }

  
  size_t TransferBucket::GetChunkOffset(size_t index) const
  {
    if (index >= chunks_.size())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
    else
    {
      return chunks_[index].offset_;
    }
  }

  
  size_t TransferBucket::GetChunkSize(size_t index) const
  {
    if (index >= chunks_.size())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
    else
    {
      return chunks_[index].size_;
    }
  }

  
  void TransferBucket::ComputePullUri(std::string& uri,
                                      BucketCompression compression) const
  {
    if (chunks_.empty())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
    }

    bool first = true;
    uri = std::string(URI_CHUNKS) + "/";

    for (size_t i = 0; i < chunks_.size(); i++)
    {
      if (first)
      {
        first = false;
      }
      else
      {
        uri += ".";
      }

      uri += chunks_[i].instanceId_;

      assert(i == 0 || chunks_[i].offset_ == 0);
    }

    uri += ("?offset=" + boost::lexical_cast<std::string>(chunks_[0].offset_) +
            "&size=" + boost::lexical_cast<std::string>(totalSize_));

    switch (compression)
    {
      case BucketCompression_None:
        uri += "&compression=none";
        break;

      case BucketCompression_Gzip:
        uri += "&compression=gzip";
        break;

      default:
        throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
  }
}
