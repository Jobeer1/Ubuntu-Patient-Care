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


#include "GoogleStoragePlugin.h"

#include "google/cloud/storage/client.h"

#include <Logging.h>

// Create aliases to make the code easier to read.
namespace gcs = google::cloud::storage;


class GoogleStoragePlugin : public BaseStorage
{
public:

  std::string         bucketName_;
  google::cloud::storage::Client mainClient_; // the client that is created at startup.  Each thread should copy it when it needs it. (from the doc: Instances of this class created via copy-construction or copy-assignment share the underlying pool of connections. Access to these copies via multiple threads is guaranteed to work. Two threads operating on the same instance of this class is not guaranteed to work.)
  bool                storageContainsUnknownFiles_;

public:

  GoogleStoragePlugin(const std::string& nameForLogs, 
                      const std::string& bucketName,
                      google::cloud::storage::Client& mainClient,
                      bool enableLegacyStorageStructure,
                      bool storageContainsUnknownFiles
                      );

  virtual IWriter* GetWriterForObject(const char* uuid, OrthancPluginContentType type, bool encryptionEnabled) ORTHANC_OVERRIDE;
  virtual IReader* GetReaderForObject(const char* uuid, OrthancPluginContentType type, bool encryptionEnabled) ORTHANC_OVERRIDE;
  virtual void DeleteObject(const char* uuid, OrthancPluginContentType type, bool encryptionEnabled) ORTHANC_OVERRIDE;
  virtual bool HasFileExists() ORTHANC_OVERRIDE {return false;};
};


class Writer : public IStorage::IWriter
{
  std::string   path_;
  gcs::Client   client_;
  std::string   bucketName_;
  gcs::ObjectWriteStream stream_;
public:
  Writer(const std::string& bucketName, const std::string& path, gcs::Client& client)
    : path_(path),
      client_(client),
      bucketName_(bucketName)
  {
  }

  virtual ~Writer()
  {
  }

  virtual void Write(const char* data, size_t size) ORTHANC_OVERRIDE
  {
    stream_ = client_.WriteObject(bucketName_, path_);

    if (stream_)
    {
      stream_.write(data, size);
      stream_.Close();

      if (!stream_.metadata())
      {
        throw StoragePluginException("GoogleCloudStorage: error while writing file " + std::string(path_) + ": " + stream_.metadata().status().message());
      }
    }
    else
    {
      throw StoragePluginException("GoogleCloudStorage: error while opening/writing file " + std::string(path_) + ": " + stream_.metadata().status().message());
    }
  }
};


class Reader : public IStorage::IReader
{
  std::list<std::string>  paths_;
  gcs::Client             client_;
  std::string             bucketName_;

public:
  Reader(const std::string& bucketName, const std::list<std::string>& paths, gcs::Client& client)
    : paths_(paths),
      client_(client),
      bucketName_(bucketName)
  {
  }

  virtual ~Reader()
  {

  }

  virtual size_t GetSize() ORTHANC_OVERRIDE
  {
    std::string firstExceptionMessage;

    for (auto& path: paths_)
    {
      try
      {
        return _GetSize(path);
      }
      catch (StoragePluginException& ex)
      {
        if (firstExceptionMessage.empty())
        {
          firstExceptionMessage = ex.what();
        }
        //ignore to retry
      }
    }
    throw StoragePluginException(firstExceptionMessage);
  }

  virtual void ReadWhole(char* data, size_t size) ORTHANC_OVERRIDE
  {
    std::string firstExceptionMessage;

    for (auto& path: paths_)
    {
      try
      {
        return _ReadWhole(path, data, size);
      }
      catch (StoragePluginException& ex)
      {
        if (firstExceptionMessage.empty())
        {
          firstExceptionMessage = ex.what();
        }
        //ignore to retry
      }
    }
    throw StoragePluginException(firstExceptionMessage);
  }

  virtual void ReadRange(char* data, size_t size, size_t fromOffset) ORTHANC_OVERRIDE
  {
    std::string firstExceptionMessage;

    for (auto& path: paths_)
    {
      try
      {
        return _ReadRange(path, data, size, fromOffset);
      }
      catch (StoragePluginException& ex)
      {
        if (firstExceptionMessage.empty())
        {
          firstExceptionMessage = ex.what();
        }
        //ignore to retry
      }
    }
    throw StoragePluginException(firstExceptionMessage);
  }

private:
  void _ReadWhole(const std::string& path, char* data, size_t size)
  {
    auto reader = client_.ReadObject(bucketName_, path);

    if (!reader)
    {
      throw StoragePluginException("error while opening/reading file " + std::string(path) + ": " + reader.status().message());
    }

    reader.read(data, size);

    if (!reader)
    {
      throw StoragePluginException("error while reading file " + std::string(path) + ": " + reader.status().message());
    }
  }

  void _ReadRange(const std::string& path, char* data, size_t size, size_t fromOffset)
  {
    auto reader = client_.ReadObject(bucketName_, path, gcs::ReadRange(fromOffset, fromOffset + size));

    if (!reader)
    {
      throw StoragePluginException("error while opening/reading file " + std::string(path) + ": " + reader.status().message());
    }

    reader.read(data, size);

    if (!reader)
    {
      throw StoragePluginException("error while reading file " + std::string(path) + ": " + reader.status().message());
    }
  }

  size_t _GetSize(const std::string& path)
  {
    auto objectMetadata = client_.GetObjectMetadata(bucketName_, path);

    if (objectMetadata)
    {
      std::uint64_t fileSize = static_cast<int64_t>(objectMetadata->size());

      return fileSize;
    }
    else
    {
      throw StoragePluginException("error while getting the size of " + std::string(path) + ": " + objectMetadata.status().message());
    }
  }

};



const char* GoogleStoragePluginFactory::GetStoragePluginName()
{
  return "Google Cloud Storage";
}

const char* GoogleStoragePluginFactory::GetStorageDescription()
{
  return "Stores the Orthanc storage area in Google Cloud";
}

IStorage* GoogleStoragePluginFactory::CreateStorage(const std::string& nameForLogs, const OrthancPlugins::OrthancConfiguration& orthancConfig)
{
  bool enableLegacyStorageStructure;
  bool storageContainsUnknownFiles;

  if (!orthancConfig.IsSection(GetConfigurationSectionName()))
  {
    LOG(WARNING) << GetStoragePluginName() << " plugin, section missing.  Plugin is not enabled.";
    return nullptr;
  }

  OrthancPlugins::OrthancConfiguration pluginSection;
  orthancConfig.GetSection(pluginSection, GetConfigurationSectionName());

  if (!BaseStorage::ReadCommonConfiguration(enableLegacyStorageStructure, storageContainsUnknownFiles, pluginSection))
  {
    return nullptr;
  }

  std::string pathToGoogleCredentials;

  if (!pluginSection.LookupStringValue(pathToGoogleCredentials, "ServiceAccountFile"))
  {
    LOG(ERROR) << "GoogleCloudStorage/ServiceAccountFile configuration missing.  Unable to initialize plugin";
    return nullptr;
  }

  std::string googleBucketName;
  if (!pluginSection.LookupStringValue(googleBucketName, "BucketName"))
  {
    LOG(ERROR) << "GoogleCloudStorage/BucketName configuration missing.  Unable to initialize plugin";
    return nullptr;
  }

  // Use service account credentials from a JSON keyfile:
  auto creds = gcs::oauth2::CreateServiceAccountCredentialsFromJsonFilePath(pathToGoogleCredentials);
  if (!creds)
  {
    LOG(ERROR) << "GoogleCloudStorage plugin: unable to validate credentials.  Check the ServiceAccountFile: " << creds.status().message();
    return nullptr;
  }

  // Create a client to communicate with Google Cloud Storage.
  google::cloud::StatusOr<gcs::Client> mainClient = gcs::Client(gcs::ClientOptions(*creds));

  if (!mainClient)
  {
    LOG(ERROR) << "GoogleCloudStorage plugin: unable to create client: " << mainClient.status().message();
    return nullptr;
  }

  return new GoogleStoragePlugin(nameForLogs, googleBucketName, mainClient.value(), enableLegacyStorageStructure, storageContainsUnknownFiles);
}

GoogleStoragePlugin::GoogleStoragePlugin(const std::string& nameForLogs, const std::string &bucketName, google::cloud::storage::Client& mainClient, bool enableLegacyStorageStructure, bool storageContainsUnknownFiles)
  : BaseStorage(nameForLogs, enableLegacyStorageStructure),
    bucketName_(bucketName),
    mainClient_(mainClient),
    storageContainsUnknownFiles_(storageContainsUnknownFiles)
{

}

IStorage::IWriter* GoogleStoragePlugin::GetWriterForObject(const char* uuid, OrthancPluginContentType type, bool encryptionEnabled)
{
  return new Writer(bucketName_, GetPath(uuid, type, encryptionEnabled), mainClient_);
}

IStorage::IReader* GoogleStoragePlugin::GetReaderForObject(const char* uuid, OrthancPluginContentType type, bool encryptionEnabled)
{
  std::list<std::string> paths;
  paths.push_back(GetPath(uuid, type, encryptionEnabled, false));
  if (storageContainsUnknownFiles_)
  {
    paths.push_back(GetPath(uuid, type, encryptionEnabled, true));
  }

  return new Reader(bucketName_, paths, mainClient_);
}

void GoogleStoragePlugin::DeleteObject(const char* uuid, OrthancPluginContentType type, bool encryptionEnabled)
{
  gcs::Client client(mainClient_);

  std::string path = GetPath(uuid, type, encryptionEnabled);

  auto deletionStatus = client.DeleteObject(bucketName_, path);

  if (!deletionStatus.ok())
  {
    throw StoragePluginException("GoogleCloudStorage: error while deleting file " + std::string(path) + ": " + deletionStatus.message());
  }
}
