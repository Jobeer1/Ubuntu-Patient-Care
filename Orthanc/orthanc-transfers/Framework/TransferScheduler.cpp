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


#include "TransferScheduler.h"

#include "../Resources/Orthanc/Plugins/OrthancPluginCppWrapper.h"

#include <Logging.h>
#include <OrthancException.h>


namespace OrthancPlugins
{
  void TransferScheduler::AddResource(OrthancInstancesCache& cache, 
                                      Orthanc::ResourceType level,
                                      const std::string& id)
  {
    Json::Value resource;

    std::string base;
    switch (level)
    {
      case Orthanc::ResourceType_Patient:
        base = "patients";
        break;

      case Orthanc::ResourceType_Study:
        base = "studies";
        break;

      case Orthanc::ResourceType_Series:
        base = "series";
        break;

      default:
        throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }

    if (RestApiGet(resource, "/" + base + "/" + id + "/instances", false))
    {
      if (resource.type() != Json::arrayValue)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
      }

      for (Json::Value::ArrayIndex i = 0; i < resource.size(); i++)
      {
        if (resource[i].type() != Json::objectValue ||
            !resource[i].isMember(KEY_ID) ||
            resource[i][KEY_ID].type() != Json::stringValue)
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
        }

        AddInstance(cache, resource[i][KEY_ID].asString());
      }
    }
    else
    {
      std::string s = Orthanc::EnumerationToString(level);
      Orthanc::Toolbox::ToLowerCase(s);
      LOG(WARNING) << "Missing " << s << ": " << id;
      throw Orthanc::OrthancException(Orthanc::ErrorCode_UnknownResource);
    }
  }


  void TransferScheduler::ComputeBucketsInternal(std::vector<TransferBucket>& target,
                                                 size_t groupThreshold,
                                                 size_t separateThreshold,
                                                 const std::string& baseUrl,  /* only needed in pull mode */
                                                 BucketCompression compression /* only needed in pull mode */) const
  {
    if (groupThreshold > separateThreshold ||
        separateThreshold == 0)  // (*)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }

    target.clear();

    std::list<std::string>  toGroup_;

    for (Instances::const_iterator it = instances_.begin();
         it != instances_.end(); ++it)
    {
      size_t size = it->second.GetSize();

      if (size < groupThreshold)
      {
        toGroup_.push_back(it->first);
      }
      else if (size < separateThreshold)
      {
        // Send the whole instance as it is
        TransferBucket bucket;
        bucket.AddChunk(it->second, 0, size);
        target.push_back(bucket);
      }
      else
      {
        // Divide this large instance as a set of chunks
        size_t chunksCount;

        if (size % separateThreshold == 0)
        {
          chunksCount = size / separateThreshold;
        }
        else
        {
          chunksCount = size / separateThreshold + 1;
        }

        assert(chunksCount != 0);  // This follows from (*)

        size_t chunkSize = size / chunksCount;
        size_t offset = 0;

        for (size_t i = 0; i < chunksCount; i++, offset += chunkSize)
        {
          TransferBucket bucket;

          if (i == chunksCount - 1)
          {
            // The last chunk must contain all the remaining bytes
            // of the instance (correction of rounding effects)
            bucket.AddChunk(it->second, offset, size - offset);
          }
          else
          {
            bucket.AddChunk(it->second, offset, chunkSize);
          }

          target.push_back(bucket);
        }
      }
    }

    // Grouping the remaining small instances, preventing the
    // download URL from getting too long: "If you keep URLs under
    // 2000 characters, they'll work in virtually any combination of
    // client and server software."
    // https://stackoverflow.com/a/417184/881731

    static const size_t MAX_URL_LENGTH = 2000 - 44 /* size of an Orthanc identifier (SHA-1) */;

    TransferBucket bucket;

    for (std::list<std::string>::const_iterator it = toGroup_.begin();
         it != toGroup_.end(); ++it)
    {
      Instances::const_iterator instance = instances_.find(*it);
      assert(instance != instances_.end());
        
      bucket.AddChunk(instance->second, 0, instance->second.GetSize());
        
      bool full = (bucket.GetTotalSize() >= groupThreshold);
        
      if (!full && !baseUrl.empty())
      {
        std::string uri;
        bucket.ComputePullUri(uri, compression);

        std::string url = baseUrl + uri;
        full = (url.length() >= MAX_URL_LENGTH);
      }

      if (full)
      {
        target.push_back(bucket);
        bucket.Clear();
      }
    }

    if (bucket.GetChunksCount() > 0)
    {
      target.push_back(bucket);
    }
  }


  void TransferScheduler::AddInstance(OrthancInstancesCache& cache, 
                                      const std::string& instanceId)
  {
    size_t size;
    std::string md5;
    cache.GetInstanceInfo(size, md5, instanceId);
          
    AddInstance(DicomInstanceInfo(instanceId, size, md5));
  }
    

  void TransferScheduler::AddInstance(const DicomInstanceInfo& info)
  {
    instances_[info.GetId()] = info;
  }

    
  void TransferScheduler::ParseListOfResources(OrthancInstancesCache& cache, 
                                               const Json::Value& resources)
  {
    if (resources.type() != Json::arrayValue)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
    }

    for (Json::Value::ArrayIndex i = 0; i < resources.size(); i++)
    {
      if (resources[i].type() != Json::objectValue ||
          !resources[i].isMember(KEY_LEVEL) ||
          !resources[i].isMember(KEY_ID) ||
          resources[i][KEY_LEVEL].type() != Json::stringValue ||
          resources[i][KEY_ID].type() != Json::stringValue)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
      }
      else
      {
        Orthanc::ResourceType level = Orthanc::StringToResourceType(resources[i][KEY_LEVEL].asCString());

        switch (level)
        {
          case Orthanc::ResourceType_Patient:
            AddPatient(cache, resources[i][KEY_ID].asString());
            break;

          case Orthanc::ResourceType_Study:
            AddStudy(cache, resources[i][KEY_ID].asString());
            break;

          case Orthanc::ResourceType_Series:
            AddSeries(cache, resources[i][KEY_ID].asString());
            break;

          case Orthanc::ResourceType_Instance:
            AddInstance(cache, resources[i][KEY_ID].asString());
            break;

          default:
            throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
        }
      }
    }
  }

    
  void TransferScheduler::ListInstances(std::vector<DicomInstanceInfo>& target) const
  {
    target.clear();
    target.reserve(instances_.size());

    for (Instances::const_iterator it = instances_.begin();
         it != instances_.end(); ++it)
    {
      assert(it->first == it->second.GetId());
      target.push_back(it->second);
    }
  }


  size_t TransferScheduler::GetTotalSize() const
  {
    size_t size = 0;

    for (Instances::const_iterator it = instances_.begin();
         it != instances_.end(); ++it)
    {
      size += it->second.GetSize();
    }

    return size;
  }


  void TransferScheduler::ComputePullBuckets(std::vector<TransferBucket>& target,
                                             size_t groupThreshold,
                                             size_t separateThreshold,
                                             const std::string& baseUrl,
                                             BucketCompression compression) const
  {
    ComputeBucketsInternal(target, groupThreshold, separateThreshold, baseUrl, compression);
  }


  void TransferScheduler::FormatPushTransaction(Json::Value& target,
                                                std::vector<TransferBucket>& buckets,
                                                size_t groupThreshold,
                                                size_t separateThreshold,
                                                BucketCompression compression) const
  {
    ComputeBucketsInternal(buckets, groupThreshold, separateThreshold, "", BucketCompression_None);

    target = Json::objectValue;

    Json::Value tmp = Json::arrayValue;
      
    for (Instances::const_iterator it = instances_.begin();
         it != instances_.end(); ++it)
    {
      Json::Value item;
      it->second.Serialize(item);
      tmp.append(item);
    }

    target[KEY_INSTANCES] = tmp;

    tmp = Json::arrayValue;

    for (size_t i = 0; i < buckets.size(); i++)
    {
      Json::Value item;
      buckets[i].Serialize(item);
      tmp.append(item);
    }

    target[KEY_BUCKETS] = tmp;

    switch (compression)
    {
      case BucketCompression_Gzip: 
        target[KEY_COMPRESSION] = "gzip";
        break;

      case BucketCompression_None: 
        target[KEY_COMPRESSION] = "none";
        break;

      default:
        throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
  }
}
