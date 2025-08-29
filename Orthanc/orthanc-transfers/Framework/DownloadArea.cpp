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


#include "DownloadArea.h"

#include "../Resources/Orthanc/Plugins/OrthancPluginCppWrapper.h"

#include <Compression/GzipCompressor.h>
#include <Logging.h>
#include <SystemToolbox.h>

#include <boost/filesystem.hpp>
#include <boost/filesystem/fstream.hpp>

namespace OrthancPlugins
{
  class DownloadArea::Instance::Writer : public boost::noncopyable
  {
  private:
    boost::filesystem::ofstream stream_;
        
  public:
    Writer(Orthanc::TemporaryFile& f,
           bool create) 
    {
      if (create)
      {
        // Create the file.
        stream_.open(f.GetPath(), std::ofstream::out | std::ofstream::binary);
      }
      else
      {
        // Open the existing file to modify it. The "in" mode is
        // necessary, otherwise previous content is lost by
        // truncation (as an ofstream defaults to std::ios::trunc,
        // the flag to truncate the existing content).
        stream_.open(f.GetPath(), std::ofstream::in | std::ofstream::out | std::ofstream::binary);
      }

      if (!stream_.good())
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_CannotWriteFile, std::string("Unable to write to ") + f.GetPath());
      }
    }

    void Write(size_t offset,
               const void* data,
               size_t size)
    {
      stream_.seekp(offset);
      stream_.write(reinterpret_cast<const char*>(data), size);
    }
  };


  DownloadArea::Instance::Instance(const DicomInstanceInfo& info) :
    info_(info)
  {
    Writer writer(file_, true);

    // Create a sparse file of expected size
    if (info_.GetSize() != 0)
    {
      writer.Write(info_.GetSize() - 1, "", 1);
    }
  }


  void DownloadArea::Instance::WriteChunk(size_t offset,
                                          const void* data,
                                          size_t size)
  {
    if (offset + size > info_.GetSize())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange, "WriteChunk out of bounds");
    }
    else if (size > 0)
    {
      Writer writer(file_, false);
      writer.Write(offset, data, size);
    }
  }

  
  void DownloadArea::Instance::Commit(bool simulate) const
  {
    std::string content;
    Orthanc::SystemToolbox::ReadFile(content, file_.GetPath());

    std::string md5;
    Orthanc::Toolbox::ComputeMD5(md5, content);

    if (md5 == info_.GetMD5())
    {
      if (!simulate)
      {
        Json::Value result;
        if (!RestApiPost(result, "/instances", 
                         content.empty() ? NULL : content.c_str(), content.size(),
                         false))
        {
          LOG(ERROR) << "Cannot import a transfered DICOM instance into Orthanc: "
                     << info_.GetId();
          throw Orthanc::OrthancException(Orthanc::ErrorCode_CorruptedFile);
        }
      }
    }
    else
    {
      LOG(ERROR) << "Bad MD5 sum in a transfered DICOM instance: " << info_.GetId();
      throw Orthanc::OrthancException(Orthanc::ErrorCode_CorruptedFile);
    }
  }


  void DownloadArea::Clear()
  {
    for (Instances::iterator it = instances_.begin(); 
         it != instances_.end(); ++it)
    {
      if (it->second != NULL)
      {
        delete it->second;
        it->second = NULL;
      }
    }

    instances_.clear();
  }


  DownloadArea::Instance& DownloadArea::LookupInstance(const std::string& id)
  {
    Instances::iterator it = instances_.find(id);

    if (it == instances_.end())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_UnknownResource, "Unknown instance");
    }
    else if (it->first != id ||
             it->second == NULL)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
    }
    else
    {
      return *it->second;
    }
  }


  void DownloadArea::WriteUncompressedBucket(const TransferBucket& bucket,
                                             const void* data,
                                             size_t size)
  {
    if (size != bucket.GetTotalSize())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_NetworkProtocol, 
        "WriteUncompressedBucket: " + boost::lexical_cast<std::string>(size) + " != " + boost::lexical_cast<std::string>(bucket.GetTotalSize()));
    }

    if (size == 0)
    {
      return;
    }

    size_t pos = 0;

    for (size_t i = 0; i < bucket.GetChunksCount(); i++)
    {
      size_t chunkSize = bucket.GetChunkSize(i);
      size_t offset = bucket.GetChunkOffset(i);

      if (pos + chunkSize > size)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
      }

      Instance& instance = LookupInstance(bucket.GetChunkInstanceId(i));
      instance.WriteChunk(offset, reinterpret_cast<const char*>(data) + pos, chunkSize);

      pos += chunkSize;
    }

    if (pos != size)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
    }
  }


  void DownloadArea::Setup(const std::vector<DicomInstanceInfo>& instances)
  {
    totalSize_ = 0;
      
    for (size_t i = 0; i < instances.size(); i++)
    {
      const std::string& id = instances[i].GetId();
        
      assert(instances_.find(id) == instances_.end());
      instances_[id] = new Instance(instances[i]);

      totalSize_ += instances[i].GetSize();
    }
  }
    

  void DownloadArea::CommitInternal(bool simulate)
  {
    boost::mutex::scoped_lock lock(mutex_);
      
    for (Instances::iterator it = instances_.begin(); 
         it != instances_.end(); ++it)
    {
      if (it->second != NULL)
      {
        it->second->Commit(simulate);
        delete it->second;
        it->second = NULL;
      }
      else
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
      }
    }
  }


  DownloadArea::DownloadArea(const TransferScheduler& scheduler)
  {
    std::vector<DicomInstanceInfo> instances;
    scheduler.ListInstances(instances);
    Setup(instances);
  }


  void DownloadArea::WriteBucket(const TransferBucket& bucket,
                                 const void* data,
                                 size_t size,
                                 BucketCompression compression)
  {
    boost::mutex::scoped_lock lock(mutex_);
      
    switch (compression)
    {
      case BucketCompression_None:
        WriteUncompressedBucket(bucket, data, size);
        break;
          
      case BucketCompression_Gzip:
      {
        std::string uncompressed;
        Orthanc::GzipCompressor compressor;
        compressor.Uncompress(uncompressed, data, size);
        WriteUncompressedBucket(bucket, uncompressed.c_str(), uncompressed.size());
        break;
      }

      default:          
        throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
  }


  void DownloadArea::WriteInstance(const std::string& instanceId,
                                   const void* data,
                                   size_t size)
  {
    std::string md5;
    Orthanc::Toolbox::ComputeMD5(md5, data, size);
      
    {
      boost::mutex::scoped_lock lock(mutex_);

      Instances::const_iterator it = instances_.find(instanceId);
      if (it == instances_.end() ||
          it->second == NULL ||
          it->second->GetInfo().GetId() != instanceId ||
          it->second->GetInfo().GetSize() != size ||
          it->second->GetInfo().GetMD5() != md5)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_CorruptedFile);
      }
      else
      {
        it->second->WriteChunk(0, data, size);
      }
    }
  }


  void DownloadArea::CheckMD5()
  {
    LOG(INFO) << "Checking MD5 sum without committing (testing)";
    CommitInternal(true);
  }


  void DownloadArea::Commit()
  {
    LOG(INFO) << "Importing transfered DICOM files from the temporary download area into Orthanc";
    CommitInternal(false);
  }
}
