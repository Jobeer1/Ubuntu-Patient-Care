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


#if GOOGLE_STORAGE_PLUGIN==1
#  include "../Google/GoogleStoragePlugin.h"
#  define StoragePluginFactory GoogleStoragePluginFactory
#elif AZURE_STORAGE_PLUGIN==1
#  include "../Azure/AzureBlobStoragePlugin.h"
#  define StoragePluginFactory AzureBlobStoragePluginFactory
#elif AWS_STORAGE_PLUGIN==1
#  include "../Aws/AwsS3StoragePlugin.h"
#  define StoragePluginFactory AwsS3StoragePluginFactory
#else
#  pragma message(error  "define a plugin")
#endif

#include <string.h>
#include <stdio.h>
#include <string>

#include <iostream>
#include <boost/filesystem.hpp>
#include <boost/filesystem/fstream.hpp>

#include "../Common/EncryptionHelpers.h"
#include "../Common/EncryptionConfigurator.h"
#include "../Common/FileSystemStorage.h"

#include <Logging.h>
#include <SystemToolbox.h>
#include "MoveStorageJob.h"
#include "StoragePlugin.h"
#include <Toolbox.h>

#ifdef _WIN32
// This is a hotfix for: https://orthanc.uclouvain.be/hg/orthanc/rev/e4d9a872998f
#  undef ORTHANC_PLUGINS_API
#  define ORTHANC_PLUGINS_API __declspec(dllexport)
#endif


static std::unique_ptr<IStorage> primaryStorage;
static std::unique_ptr<IStorage> secondaryStorage;

static std::unique_ptr<EncryptionHelpers> crypto;
static bool cryptoEnabled = false;
static std::string fileSystemRootPath;
static std::string objectsRootPath;
static std::string hybridModeNameForLogs = "";

typedef enum 
{
  HybridMode_WriteToFileSystem,       // write to disk, try to read first from disk and then, from object-storage
  HybridMode_WriteToObjectStorage,    // write to object storage, try to read first from object storage and then, from disk
  HybridMode_Disabled                 // read and write only from/to object-storage
} HybridMode;  

static HybridMode hybridMode = HybridMode_Disabled;

static bool IsReadFromDisk()
{
  return hybridMode != HybridMode_Disabled;
}

static bool IsHybridModeEnabled()
{
  return hybridMode != HybridMode_Disabled;
}

typedef void LogErrorFunction(const std::string& message);

static void LogErrorAsWarning(const std::string& message)
{
  LOG(WARNING) << message;
}

static void LogErrorAsError(const std::string& message)
{
  LOG(ERROR) << message;
}



static OrthancPluginErrorCode StorageCreate(const char* uuid,
                                            const void* content,
                                            int64_t size,
                                            OrthancPluginContentType type)
{
  try
  {
    Orthanc::Toolbox::ElapsedTimer timer;
    LOG(INFO) << primaryStorage->GetNameForLogs() << ": creating attachment " << uuid
              << " of type " << boost::lexical_cast<std::string>(type);
    std::unique_ptr<IStorage::IWriter> writer(primaryStorage->GetWriterForObject(uuid, type, cryptoEnabled));

    if (cryptoEnabled)
    {
      std::string encryptedFile;

      try
      {
        crypto->Encrypt(encryptedFile, (const char*)content, size);
      }
      catch (EncryptionException& ex)
      {
        LOG(ERROR) << primaryStorage->GetNameForLogs() << ": error while encrypting object " << uuid << ": " << ex.what();
        return OrthancPluginErrorCode_StorageAreaPlugin;
      }

      writer->Write(encryptedFile.data(), encryptedFile.size());
    }
    else
    {
      writer->Write(reinterpret_cast<const char*>(content), size);
    }
    LOG(INFO) << primaryStorage->GetNameForLogs() << ": created attachment " << uuid
              << " (" << timer.GetHumanTransferSpeed(true, size) << ")";
  }
  catch (StoragePluginException& ex)
  {
    LOG(ERROR) << primaryStorage->GetNameForLogs() << ": error while creating object " << uuid << ": " << ex.what();
    return OrthancPluginErrorCode_StorageAreaPlugin;
  }

  return OrthancPluginErrorCode_Success;
}


static OrthancPluginErrorCode StorageReadRange(IStorage* storage,
                                               LogErrorFunction logErrorFunction,
                                               OrthancPluginMemoryBuffer64* target, // Memory buffer where to store the content of the range.  The memory buffer is allocated and freed by Orthanc. The length of the range of interest corresponds to the size of this buffer.
                                               const char* uuid,
                                               OrthancPluginContentType type,
                                               uint64_t rangeStart)
{
  assert(!cryptoEnabled);

  try
  {
    Orthanc::Toolbox::ElapsedTimer timer;
    LOG(INFO) << storage->GetNameForLogs() << ": reading range of attachment " << uuid
              << " of type " << boost::lexical_cast<std::string>(type);
    
    std::unique_ptr<IStorage::IReader> reader(storage->GetReaderForObject(uuid, type, cryptoEnabled));
    reader->ReadRange(reinterpret_cast<char*>(target->data), target->size, rangeStart);
    
    LOG(INFO) << storage->GetNameForLogs() << ": read range of attachment " << uuid
              << " (" << timer.GetHumanTransferSpeed(true, target->size) << ")";
    return OrthancPluginErrorCode_Success;
  }
  catch (StoragePluginException& ex)
  {
    logErrorFunction(std::string(StoragePluginFactory::GetStoragePluginName()) + ": error while reading object " + std::string(uuid) + ": " + std::string(ex.what()));
    return OrthancPluginErrorCode_StorageAreaPlugin;
  }
}

static OrthancPluginErrorCode StorageReadRange(OrthancPluginMemoryBuffer64* target, // Memory buffer where to store the content of the range.  The memory buffer is allocated and freed by Orthanc. The length of the range of interest corresponds to the size of this buffer.
                                               const char* uuid,
                                               OrthancPluginContentType type,
                                               uint64_t rangeStart)
{
  OrthancPluginErrorCode res = StorageReadRange(primaryStorage.get(),
                                                (IsHybridModeEnabled() ? LogErrorAsWarning : LogErrorAsError), // log errors as warning on first try
                                                target,
                                                uuid,
                                                type,
                                                rangeStart);

  if (res != OrthancPluginErrorCode_Success && IsHybridModeEnabled())
  {
    res = StorageReadRange(secondaryStorage.get(),
                           LogErrorAsError, // log errors as errors on second try
                           target,
                           uuid,
                           type,
                           rangeStart);
  }
  return res;
}



static OrthancPluginErrorCode StorageReadWhole(IStorage* storage,
                                               LogErrorFunction logErrorFunction,
                                               OrthancPluginMemoryBuffer64* target, // Memory buffer where to store the content of the file. It must be allocated by the plugin using OrthancPluginCreateMemoryBuffer64(). The core of Orthanc will free it.
                                               const char* uuid,
                                               OrthancPluginContentType type)
{
  try
  {
    Orthanc::Toolbox::ElapsedTimer timer;
    LOG(INFO) << storage->GetNameForLogs() << ": reading whole attachment " << uuid
              << " of type " << boost::lexical_cast<std::string>(type);
    std::unique_ptr<IStorage::IReader> reader(storage->GetReaderForObject(uuid, type, cryptoEnabled));

    size_t fileSize = reader->GetSize();
    size_t size;

    if (cryptoEnabled)
    {
      size = fileSize - crypto->OVERHEAD_SIZE;
    }
    else
    {
      size = fileSize;
    }

    if (size <= 0)
    {
      logErrorFunction(storage->GetNameForLogs() + ": error while reading object " + std::string(uuid) + ", size of file is too small: " + boost::lexical_cast<std::string>(fileSize) + " bytes");
      return OrthancPluginErrorCode_StorageAreaPlugin;
    }

    if (OrthancPluginCreateMemoryBuffer64(OrthancPlugins::GetGlobalContext(), target, size) != OrthancPluginErrorCode_Success)
    {
      logErrorFunction(storage->GetNameForLogs() + ": error while reading object " + std::string(uuid) + ", cannot allocate memory of size " + boost::lexical_cast<std::string>(size) + " bytes");
      return OrthancPluginErrorCode_StorageAreaPlugin;
    }

    if (cryptoEnabled)
    {
      std::vector<char> encrypted(fileSize);
      reader->ReadWhole(encrypted.data(), fileSize);

      try
      {
        crypto->Decrypt(reinterpret_cast<char*>(target->data), encrypted.data(), fileSize);
      }
      catch (EncryptionException& ex)
      {
        logErrorFunction(storage->GetNameForLogs() + ": error while decrypting object " + std::string(uuid) + ": " + ex.what());
        return OrthancPluginErrorCode_StorageAreaPlugin;
      }
    }
    else
    {
      reader->ReadWhole(reinterpret_cast<char*>(target->data), fileSize);
    }

    LOG(INFO) << storage->GetNameForLogs() << ": read whole attachment " << uuid
              << " (" << timer.GetHumanTransferSpeed(true, fileSize) << ")";
  }
  catch (StoragePluginException& ex)
  {
    logErrorFunction(storage->GetNameForLogs() + ": error while reading object " + std::string(uuid) + ": " + ex.what());
    return OrthancPluginErrorCode_StorageAreaPlugin;
  }

  return OrthancPluginErrorCode_Success;
}

static OrthancPluginErrorCode StorageReadWhole(OrthancPluginMemoryBuffer64* target, // Memory buffer where to store the content of the file. It must be allocated by the plugin using OrthancPluginCreateMemoryBuffer64(). The core of Orthanc will free it.
                                               const char* uuid,
                                               OrthancPluginContentType type)
{
  OrthancPluginErrorCode res = StorageReadWhole(primaryStorage.get(),
                                                (IsHybridModeEnabled() ? LogErrorAsWarning : LogErrorAsError), // log errors as warning on first try
                                                target,
                                                uuid,
                                                type);

  if (res != OrthancPluginErrorCode_Success && IsHybridModeEnabled())
  {
    res = StorageReadWhole(secondaryStorage.get(),
                           LogErrorAsError, // log errors as errors on second try
                           target,
                           uuid,
                           type);
  }
  return res;
}

static OrthancPluginErrorCode StorageReadWholeLegacy(void** content,
                                                     int64_t* size,
                                                     const char* uuid,
                                                     OrthancPluginContentType type)
{
  OrthancPluginMemoryBuffer64 buffer;
  OrthancPluginErrorCode result = StorageReadWhole(&buffer, uuid, type); // will allocate OrthancPluginMemoryBuffer64

  if (result == OrthancPluginErrorCode_Success)
  {
    *size = buffer.size;
    *content = buffer.data; // orthanc will free the buffer (we don't have to delete it ourselves)
  }

  return result;
}


static OrthancPluginErrorCode StorageRemove(IStorage* storage,
                                            LogErrorFunction logErrorFunction,
                                            const char* uuid,
                                            OrthancPluginContentType type)
{
  try
  {
    LOG(INFO) << storage->GetNameForLogs() << ": deleting attachment " << uuid
              << " of type " << boost::lexical_cast<std::string>(type);
    storage->DeleteObject(uuid, type, cryptoEnabled);
    if ((storage == primaryStorage.get()) && IsHybridModeEnabled())
    {
      // not 100% sure the file has been deleted, try the secondary plugin
      return OrthancPluginErrorCode_StorageAreaPlugin; 
    }
    
    return OrthancPluginErrorCode_Success;
  }
  catch (StoragePluginException& ex)
  {
    logErrorFunction(std::string(StoragePluginFactory::GetStoragePluginName()) + ": error while deleting object " + std::string(uuid) + ": " + std::string(ex.what()));
    return OrthancPluginErrorCode_StorageAreaPlugin;
  }
}

static OrthancPluginErrorCode StorageRemove(const char* uuid,
                                            OrthancPluginContentType type)
{
  OrthancPluginErrorCode res = StorageRemove(primaryStorage.get(),
                                             (IsHybridModeEnabled() ? LogErrorAsWarning : LogErrorAsError), // log errors as warning on first try
                                             uuid,
                                             type);

  if (res != OrthancPluginErrorCode_Success && IsHybridModeEnabled())
  {
    res = StorageRemove(secondaryStorage.get(),
                        LogErrorAsError, // log errors as errors on second try
                        uuid,
                        type);
  }
  return res;
}


static MoveStorageJob* CreateMoveStorageJob(const std::string& targetStorage, const std::vector<std::string>& instances, const Json::Value& resourcesForJobContent)
{
  std::unique_ptr<MoveStorageJob> job(new MoveStorageJob(targetStorage, instances, resourcesForJobContent, cryptoEnabled));

  if (hybridMode == HybridMode_WriteToFileSystem)
  {
    job->SetStorages(primaryStorage.get(), secondaryStorage.get());
  }
  else
  {
    job->SetStorages(secondaryStorage.get(), primaryStorage.get());
  }

  return job.release();
}


static void AddResourceForJobContent(Json::Value& resourcesForJobContent /* out */, Orthanc::ResourceType resourceType, const std::string& resourceId)
{
  const char* resourceGroup = Orthanc::GetResourceTypeText(resourceType, true, true);

  if (!resourcesForJobContent.isMember(resourceGroup))
  {
    resourcesForJobContent[resourceGroup] = Json::arrayValue;
  }
  
  resourcesForJobContent[resourceGroup].append(resourceId);
}

void MoveStorage(OrthancPluginRestOutput* output,
                 const char* /*url*/,
                 const OrthancPluginHttpRequest* request)
{
  OrthancPluginContext* context = OrthancPlugins::GetGlobalContext();

  if (request->method != OrthancPluginHttpMethod_Post)
  {
    OrthancPluginSendMethodNotAllowed(context, output, "POST");
    return;
  }

  Json::Value requestPayload;

  if (!OrthancPlugins::ReadJson(requestPayload, request->body, request->bodySize))
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat, "A JSON payload was expected");
  }

  std::vector<std::string> instances;
  Json::Value resourcesForJobContent;

  if (requestPayload.type() != Json::objectValue ||
      !requestPayload.isMember(KEY_RESOURCES) ||
      requestPayload[KEY_RESOURCES].type() != Json::arrayValue)
  {
    throw Orthanc::OrthancException(
      Orthanc::ErrorCode_BadFileFormat,
      "A request to the move-storage endpoint must provide a JSON object "
      "with the field \"" + std::string(KEY_RESOURCES) + 
      "\" containing an array of resources to be sent");
  }

  if (!requestPayload.isMember(KEY_TARGET_STORAGE)
      || requestPayload[KEY_TARGET_STORAGE].type() != Json::stringValue
      || (requestPayload[KEY_TARGET_STORAGE].asString() != STORAGE_TYPE_FILE_SYSTEM && requestPayload[KEY_TARGET_STORAGE].asString() != STORAGE_TYPE_OBJECT_STORAGE))
  {
    throw Orthanc::OrthancException(
      Orthanc::ErrorCode_BadFileFormat,
      "A request to the move-storage endpoint must provide a JSON object "
      "with the field \"" + std::string(KEY_TARGET_STORAGE) + 
      "\" set to \"" + std::string(STORAGE_TYPE_FILE_SYSTEM) + "\" or \"" + std::string(STORAGE_TYPE_OBJECT_STORAGE) +  "\"");
  }

  const std::string& targetStorage = requestPayload[KEY_TARGET_STORAGE].asString();
  const Json::Value& resources = requestPayload[KEY_RESOURCES];

  // Extract information about all the child instances
  for (Json::Value::ArrayIndex i = 0; i < resources.size(); i++)
  {
    if (resources[i].type() != Json::stringValue)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
    }

    std::string resource = resources[i].asString();
    if (resource.empty())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_UnknownResource);
    }

    // Test whether this resource is an instance
    Json::Value tmpResource;
    Json::Value tmpInstances;
    if (OrthancPlugins::RestApiGet(tmpResource, "/instances/" + resource, false))
    {
      instances.push_back(resource);
      AddResourceForJobContent(resourcesForJobContent, Orthanc::ResourceType_Instance, resource);
    }
    // This was not an instance, successively try with series/studies/patients
    else if ((OrthancPlugins::RestApiGet(tmpResource, "/series/" + resource, false) &&
              OrthancPlugins::RestApiGet(tmpInstances, "/series/" + resource + "/instances", false)) ||
             (OrthancPlugins::RestApiGet(tmpResource, "/studies/" + resource, false) &&
              OrthancPlugins::RestApiGet(tmpInstances, "/studies/" + resource + "/instances", false)) ||
             (OrthancPlugins::RestApiGet(tmpResource, "/patients/" + resource, false) &&
              OrthancPlugins::RestApiGet(tmpInstances, "/patients/" + resource + "/instances", false)))
    {
      if (tmpInstances.type() != Json::arrayValue)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
      }

      AddResourceForJobContent(resourcesForJobContent, Orthanc::StringToResourceType(tmpResource["Type"].asString().c_str()), resource);

      for (Json::Value::ArrayIndex j = 0; j < tmpInstances.size(); j++)
      {
        instances.push_back(tmpInstances[j]["ID"].asString());
      }
    }
    else
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_UnknownResource);
    }   
  }

  LOG(INFO) << "Moving " << instances.size() << " instances to " << targetStorage;

  std::unique_ptr<MoveStorageJob> job(CreateMoveStorageJob(targetStorage, instances, resourcesForJobContent));

  OrthancPlugins::OrthancJob::SubmitFromRestApiPost(output, requestPayload, job.release());
}

OrthancPluginJob* JobUnserializer(const char* jobType,
                                  const char* serialized)
{
  if (jobType == NULL ||
      serialized == NULL)
  {
    return NULL;
  }

  std::string type(jobType);

  if (type != JOB_TYPE_MOVE_STORAGE)
  {
    return NULL;
  }

  try
  {
    std::string tmp(serialized);

    Json::Value source;
    if (Orthanc::Toolbox::ReadJson(source, tmp))
    {
      std::unique_ptr<OrthancPlugins::OrthancJob> job;

      if (type == JOB_TYPE_MOVE_STORAGE)
      {
        std::vector<std::string> instances;

        for (size_t i = 0; i < source[KEY_INSTANCES].size(); ++i)
        {
          instances.push_back(source[KEY_INSTANCES][static_cast<int>(i)].asString());
        }

        job.reset(CreateMoveStorageJob(source[KEY_TARGET_STORAGE].asString(), instances, source[KEY_CONTENT]));
      }

      if (job.get() == NULL)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
      }
      else
      {
        return OrthancPlugins::OrthancJob::Create(job.release());
      }
    }
    else
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
    }
  }
  catch (Orthanc::OrthancException& e)
  {
    LOG(ERROR) << "Error while unserializing a job from the " << StoragePluginFactory::GetStoragePluginName() << " plugin: "
               << e.What();
    return NULL;
  }
  catch (...)
  {
    LOG(ERROR) << "Error while unserializing a job from the " << StoragePluginFactory::GetStoragePluginName() << " plugin";
    return NULL;
  }
}


extern "C"
{
  ORTHANC_PLUGINS_API int32_t OrthancPluginInitialize(OrthancPluginContext* context)
  {
    OrthancPlugins::SetGlobalContext(context);

#if ORTHANC_FRAMEWORK_VERSION_IS_ABOVE(1, 12, 4)
    Orthanc::Logging::InitializePluginContext(context, StoragePluginFactory::GetStoragePluginName());
#elif ORTHANC_FRAMEWORK_VERSION_IS_ABOVE(1, 7, 2)
    Orthanc::Logging::InitializePluginContext(context);
#else
    Orthanc::Logging::Initialize(context);
#endif

    /* Check the version of the Orthanc core */
    if (OrthancPluginCheckVersion(context) == 0)
    {
      char info[1024];
      sprintf(info, "Your version of Orthanc (%s) must be above %d.%d.%d to run this plugin",
              context->orthancVersion,
              ORTHANC_PLUGINS_MINIMAL_MAJOR_NUMBER,
              ORTHANC_PLUGINS_MINIMAL_MINOR_NUMBER,
              ORTHANC_PLUGINS_MINIMAL_REVISION_NUMBER);
      LOG(ERROR) << info;
      return -1;
    }

    Orthanc::InitializeFramework("", false);

    OrthancPlugins::OrthancConfiguration orthancConfig;

    LOG(WARNING) << StoragePluginFactory::GetStoragePluginName() << " plugin is initializing";
    OrthancPlugins::SetDescription(StoragePluginFactory::GetStoragePluginName(), StoragePluginFactory::GetStorageDescription());

    try
    {
      const char* pluginSectionName = StoragePluginFactory::GetConfigurationSectionName();
      static const char* const ENCRYPTION_SECTION = "StorageEncryption";

      if (!orthancConfig.IsSection(pluginSectionName))
      {
        LOG(WARNING) << StoragePluginFactory::GetStoragePluginName() << ": no \"" << pluginSectionName
                     << "\" section found in configuration, plugin is disabled";
        return 0;
      }

      OrthancPlugins::OrthancConfiguration pluginSection;
      orthancConfig.GetSection(pluginSection, pluginSectionName);

      bool migrationFromFileSystemEnabled = pluginSection.GetBooleanValue("MigrationFromFileSystemEnabled", false);
      std::string hybridModeString = pluginSection.GetStringValue("HybridMode", "Disabled");

      if (migrationFromFileSystemEnabled && hybridModeString == "Disabled")
      {
        hybridMode = HybridMode_WriteToObjectStorage;
        LOG(WARNING) << StoragePluginFactory::GetStoragePluginName() << ": 'MigrationFromFileSystemEnabled' configuration is deprecated, use 'HybridMode': 'WriteToObjectStorage' instead";
      }
      else if (hybridModeString == "WriteToObjectStorage")
      {
        hybridMode = HybridMode_WriteToObjectStorage;
        LOG(WARNING) << StoragePluginFactory::GetStoragePluginName() << ": WriteToObjectStorage HybridMode is enabled: writing to object-storage, try reading first from object-storage and, then, from file system";
      }
      else if (hybridModeString == "WriteToFileSystem")
      {
        hybridMode = HybridMode_WriteToFileSystem;
        LOG(WARNING) << StoragePluginFactory::GetStoragePluginName() << ": WriteToFileSystem HybridMode is enabled: writing to file system, try reading first from file system and, then, from object-storage";
      }
      else
      {
        LOG(WARNING) << StoragePluginFactory::GetStoragePluginName() << ": HybridMode is disabled: writing to object-storage and reading only from object-storage";
      }

      if (IsReadFromDisk())
      {
        fileSystemRootPath = orthancConfig.GetStringValue("StorageDirectory", "OrthancStorageNotDefined");
        LOG(WARNING) << StoragePluginFactory::GetStoragePluginName() << ": HybridMode: reading from file system is enabled, source: " << fileSystemRootPath;
      }

      objectsRootPath = pluginSection.GetStringValue("RootPath", std::string());

      if (objectsRootPath.size() >= 1 && objectsRootPath[0] == '/')
      {
        LOG(ERROR) << StoragePluginFactory::GetStoragePluginName() << ": The RootPath shall not start with a '/': " << objectsRootPath;
        return -1;
      }

      std::string objecstStoragePluginName = StoragePluginFactory::GetStoragePluginName();
      if (hybridMode == HybridMode_WriteToFileSystem)
      {
        objecstStoragePluginName += " (Secondary: object-storage)";
      }
      else if (hybridMode == HybridMode_WriteToObjectStorage)
      {
        objecstStoragePluginName += " (Primary: object-storage)";
      }

      std::unique_ptr<IStorage> objectStoragePlugin(StoragePluginFactory::CreateStorage(objecstStoragePluginName, orthancConfig));

      if (objectStoragePlugin.get() == nullptr)
      {
        return -1;
      }

      objectStoragePlugin->SetRootPath(objectsRootPath);

      std::unique_ptr<IStorage> fileSystemStoragePlugin;
      if (IsHybridModeEnabled())
      {
        bool fsync = orthancConfig.GetBooleanValue("SyncStorageArea", true);

        std::string filesystemStoragePluginName = StoragePluginFactory::GetStoragePluginName();
        if (hybridMode == HybridMode_WriteToFileSystem)
        {
          filesystemStoragePluginName += " (Primary: file-system)";
        }
        else if (hybridMode == HybridMode_WriteToObjectStorage)
        {
          filesystemStoragePluginName += " (Secondary: file-system)";
        }

        fileSystemStoragePlugin.reset(new FileSystemStoragePlugin(filesystemStoragePluginName, fileSystemRootPath, fsync));
      }

      if (hybridMode == HybridMode_Disabled || hybridMode == HybridMode_WriteToObjectStorage)
      {
        primaryStorage.reset(objectStoragePlugin.release());
        
        if (hybridMode == HybridMode_WriteToObjectStorage)
        {
          secondaryStorage.reset(fileSystemStoragePlugin.release());
        }
      }
      else if (hybridMode == HybridMode_WriteToFileSystem)
      {
        primaryStorage.reset(fileSystemStoragePlugin.release());
        secondaryStorage.reset(objectStoragePlugin.release());
      }

      if (pluginSection.IsSection(ENCRYPTION_SECTION))
      {
        OrthancPlugins::OrthancConfiguration cryptoSection;
        pluginSection.GetSection(cryptoSection, ENCRYPTION_SECTION);

        crypto.reset(EncryptionConfigurator::CreateEncryptionHelpers(cryptoSection));
        cryptoEnabled = crypto.get() != nullptr;
      }

      if (cryptoEnabled)
      {
        LOG(WARNING) << StoragePluginFactory::GetStoragePluginName() << ": client-side encryption is enabled";
      }
      else
      {
        LOG(WARNING) << StoragePluginFactory::GetStoragePluginName() << ": client-side encryption is disabled";
      }


      if (IsHybridModeEnabled())
      {
        OrthancPlugins::RegisterRestCallback<MoveStorage>("/move-storage", true);
        OrthancPluginRegisterJobsUnserializer(context, JobUnserializer);
      }

      if (cryptoEnabled)
      {
        // with encrypted file, we can not support ReadRange.  Therefore, we register the old interface
        OrthancPluginRegisterStorageArea(context, StorageCreate, StorageReadWholeLegacy, StorageRemove);
      }
      else
      {
        OrthancPluginRegisterStorageArea2(context, StorageCreate, StorageReadWhole, StorageReadRange, StorageRemove);
      }
    }
    catch (Orthanc::OrthancException& e)
    {
      LOG(ERROR) << "Exception while creating the object storage plugin: " << e.What();
      return -1;
    }

    return 0;
  }


  ORTHANC_PLUGINS_API void OrthancPluginFinalize()
  {
    LOG(WARNING) << StoragePluginFactory::GetStoragePluginName() << " plugin is finalizing";
    primaryStorage.reset();
    secondaryStorage.reset();
    Orthanc::FinalizeFramework();
  }


  ORTHANC_PLUGINS_API const char* OrthancPluginGetName()
  {
    return StoragePluginFactory::GetStoragePluginName();
  }


  ORTHANC_PLUGINS_API const char* OrthancPluginGetVersion()
  {
    return PLUGIN_VERSION;
  }
}

