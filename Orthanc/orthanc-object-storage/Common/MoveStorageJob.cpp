/**
 * Cloud storage plugins for Orthanc
 * Copyright (C) 2020-2023 Osimis S.A., Belgium
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

#include "MoveStorageJob.h"
#include "Logging.h"
#include "StoragePlugin.h"


MoveStorageJob::MoveStorageJob(const std::string& targetStorage,
                               const std::vector<std::string>& instances,
                               const Json::Value& resourceForJobContent,
                               bool cryptoEnabled)
  : OrthancPlugins::OrthancJob(JOB_TYPE_MOVE_STORAGE),
    targetStorage_(targetStorage),
    instances_(instances),
    processedInstancesCount_(0),
    resourceForJobContent_(resourceForJobContent),
    fileSystemStorage_(NULL),
    objectStorage_(NULL),
    cryptoEnabled_(cryptoEnabled)
{
  UpdateContent(resourceForJobContent);
  
  Json::Value serialized;
  Serialize(serialized);
  UpdateSerialized(serialized);
}

void MoveStorageJob::Serialize(Json::Value& target) const
{
  target[KEY_CONTENT] = resourceForJobContent_;
  target[KEY_TARGET_STORAGE] = targetStorage_;
  target[KEY_INSTANCES] = Json::arrayValue;

  for (size_t i = 0; i < instances_.size(); ++i)
  {
    target[KEY_INSTANCES].append(instances_[i]);
  }

}

void MoveStorageJob::SetStorages(IStorage* fileSystemStorage, IStorage* objectStorage)
{
  fileSystemStorage_ = fileSystemStorage;
  objectStorage_ = objectStorage;
}

static bool MoveAttachment(const std::string& uuid, int type, IStorage* sourceStorage, IStorage* targetStorage, bool cryptoEnabled)
{
  std::vector<char> buffer;
  
  // read from source storage
  try
  {
    if (sourceStorage->HasFileExists() && !sourceStorage->FileExists(uuid, static_cast<OrthancPluginContentType>(type), cryptoEnabled))
    {
      LOG(INFO) << "Move attachment: " << sourceStorage->GetNameForLogs() << " " << uuid
                << " of type " << boost::lexical_cast<std::string>(type) << ", skipping, file is not on the source anymore";
      return true;
    }
    else if (targetStorage->HasFileExists() && targetStorage->FileExists(uuid, static_cast<OrthancPluginContentType>(type), cryptoEnabled))
    {
      LOG(INFO) << "Move attachment: " << targetStorage->GetNameForLogs() << " " << uuid
                << " of type " << boost::lexical_cast<std::string>(type) << ", skipping, file already on the target";
      return true;
    }
    else
    {
      LOG(INFO) << "Move attachment: " << sourceStorage->GetNameForLogs() << ": reading attachment "
                << uuid << " of type " << boost::lexical_cast<std::string>(type);
    }

    std::unique_ptr<IStorage::IReader> reader(sourceStorage->GetReaderForObject(uuid.c_str(), static_cast<OrthancPluginContentType>(type), cryptoEnabled));

    size_t fileSize = reader->GetSize();
    buffer.resize(fileSize);

    reader->ReadWhole(buffer.data(), fileSize);
  }
  catch (StoragePluginException& ex)
  {
    LOG(INFO) << "Move attachment: " << sourceStorage->GetNameForLogs() << ": error while reading attachment " << uuid
              << " of type " << boost::lexical_cast<std::string>(type) << ", this likely means that the file is already on the right storage";
    return true;
  }

  // write to target storage
  if (buffer.size() > 0)
  {
    try
    {
      std::unique_ptr<IStorage::IWriter> writer(targetStorage->GetWriterForObject(uuid.c_str(), static_cast<OrthancPluginContentType>(type), cryptoEnabled));

      writer->Write(buffer.data(), buffer.size());
    }
    catch (StoragePluginException& ex)
    {
      LOG(ERROR) << "Move attachment: " << targetStorage->GetNameForLogs() << ": error while writing attachment "
                 << uuid << " of type " << boost::lexical_cast<std::string>(type) << ": " << ex.what();
      return false;
    }
  }

  // everything went well so far, we can delete from source storage
  if (buffer.size() > 0)
  {
    try
    {
      sourceStorage->DeleteObject(uuid.c_str(), static_cast<OrthancPluginContentType>(type), cryptoEnabled);
    }
    catch (StoragePluginException& ex)
    {
      LOG(ERROR) << "Move attachment: " << sourceStorage->GetNameForLogs() << ": error while deleting attachment "
                 << uuid << " of type " << boost::lexical_cast<std::string>(type) << ": " << ex.what();
      return false;
    }
  }
  return true;
}

static bool MoveInstance(const std::string& instanceId, IStorage* sourceStorage, IStorage* targetStorage, bool cryptoEnabled)
{
  LOG(INFO) << "Moving instance from " << sourceStorage->GetNameForLogs() << " to " << targetStorage->GetNameForLogs();

  Json::Value attachmentsList;
  OrthancPlugins::RestApiGet(attachmentsList, std::string("/instances/") + instanceId + "/attachments?full", false);

  Json::Value::Members attachmentsMembers = attachmentsList.getMemberNames();
  bool success = true;

  for (size_t i = 0; i < attachmentsMembers.size(); i++)
  {
    int attachmentId = attachmentsList[attachmentsMembers[i]].asInt();

    Json::Value attachmentInfo;
    OrthancPlugins::RestApiGet(attachmentInfo, std::string("/instances/") + instanceId + "/attachments/" + boost::lexical_cast<std::string>(attachmentId) + "/info", false);

    std::string attachmentUuid = attachmentInfo["Uuid"].asString();

    // now we have the uuid and type.  We actually don't know where the file is but we'll try to move it anyway to the requested target
    success &= MoveAttachment(attachmentUuid, attachmentId, sourceStorage, targetStorage, cryptoEnabled);
  }

  return success;
}

OrthancPluginJobStepStatus MoveStorageJob::Step()
{
  if (processedInstancesCount_ < instances_.size())
  {
    IStorage* sourceStorage = (targetStorage_ == STORAGE_TYPE_FILE_SYSTEM ? objectStorage_ : fileSystemStorage_);
    IStorage* targetStorage = (targetStorage_ == STORAGE_TYPE_FILE_SYSTEM ? fileSystemStorage_ : objectStorage_);

    if (MoveInstance(instances_[processedInstancesCount_], sourceStorage, targetStorage, cryptoEnabled_))
    {
      processedInstancesCount_++;
      UpdateProgress((float)processedInstancesCount_/(float)instances_.size());
      
      return OrthancPluginJobStepStatus_Continue;
    }
    else
    {
      return OrthancPluginJobStepStatus_Failure;
    }
  }

  return OrthancPluginJobStepStatus_Success;
}

void MoveStorageJob::Stop(OrthancPluginJobStopReason reason)
{
}
    
void MoveStorageJob::Reset()
{
  processedInstancesCount_ = 0;
}
