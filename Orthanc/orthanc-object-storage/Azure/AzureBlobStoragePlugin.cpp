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


#include "AzureBlobStoragePlugin.h"

#include <azure/storage/blobs.hpp>
#include <boost/lexical_cast.hpp>
#include <boost/algorithm/string.hpp>
// #include "cpprest/rawptrstream.h"
// #include "cpprest/details/basic_types.h"

#include <Logging.h>

// Create aliases to make the code easier to read.
namespace as = Azure::Storage::Blobs;

class AzureBlobStoragePlugin : public BaseStorage
{
public:

  as::BlobContainerClient       blobClient_;
  bool                        storageContainsUnknownFiles_;

public:

  AzureBlobStoragePlugin(const std::string& nameForLogs,  
                         const as::BlobContainerClient& blobClient, 
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
  as::BlobContainerClient client_;

public:
  Writer(const std::string& path, const as::BlobContainerClient& client)
    : path_(path),
      client_(client)
  {
  }

  virtual ~Writer()
  {
  }

  virtual void Write(const char* data, size_t size) ORTHANC_OVERRIDE
  {
    try
    {
      as::BlockBlobClient blobClient = client_.GetBlockBlobClient(path_);
      blobClient.UploadFrom(reinterpret_cast<const uint8_t*>(data), size);
    }
    catch (std::exception& ex)
    {
      throw StoragePluginException("AzureBlobStorage: error writing file " + std::string(path_) + ": " + ex.what());
    }
  }
};


class Reader : public IStorage::IReader
{
  std::string path_;
  as::BlobContainerClient client_;
  int64_t size_;

public:
  Reader(const std::list<std::string>& paths, const as::BlobContainerClient& client)
    : client_(client)
  {
    std::string firstExceptionMessage;

    for (auto& path: paths)
    {
      try
      {
        as::BlockBlobClient blobClient = client_.GetBlockBlobClient(path);
        auto properties = blobClient.GetProperties().Value;
        size_ = properties.BlobSize;
        path_ = path;
        return;
      }
      catch (std::exception& ex)
      {
        if (firstExceptionMessage.empty())
        {
          firstExceptionMessage = "AzureBlobStorage: error opening file for reading " + std::string(path) + ": " + ex.what();
        }
        //ignore to retry
      }
    }
    throw StoragePluginException(firstExceptionMessage);
  }

  virtual ~Reader()
  {
  }

  virtual size_t GetSize() ORTHANC_OVERRIDE
  {
    try
    {
      return static_cast<size_t>(size_);
    }
    catch (std::exception& ex)
    {
      throw StoragePluginException("AzureBlobStorage: error while reading file " + std::string(path_) + ": " + ex.what());
    }
  }

  virtual void ReadWhole(char* data, size_t size) ORTHANC_OVERRIDE
  {
    try
    {
      as::BlockBlobClient blobClient = client_.GetBlockBlobClient(path_);
      blobClient.DownloadTo(reinterpret_cast<uint8_t*>(data), static_cast<int64_t>(size));
    }
    catch (std::exception& ex)
    {
      throw StoragePluginException("AzureBlobStorage: error while reading file " + std::string(path_) + ": " + ex.what());
    }
  }

  virtual void ReadRange(char* data, size_t size, size_t fromOffset) ORTHANC_OVERRIDE
  {
    try
    {
      as::BlockBlobClient blobClient = client_.GetBlockBlobClient(path_);
      as::DownloadBlobToOptions options;
      options.Range = Azure::Core::Http::HttpRange();
      options.Range.Value().Length = static_cast<int64_t>(size);
      options.Range.Value().Offset = static_cast<int64_t>(fromOffset);

      blobClient.DownloadTo(reinterpret_cast<uint8_t*>(data), static_cast<int64_t>(size), options);
    }
    catch (std::exception& ex)
    {
      throw StoragePluginException("AzureBlobStorage: error while reading partial file " + std::string(path_) + ": " + ex.what());
    }
  }
};



const char* AzureBlobStoragePluginFactory::GetStoragePluginName()
{
  return "Azure Blob Storage";
}

const char* AzureBlobStoragePluginFactory::GetStorageDescription()
{
  return "Stores the Orthanc storage area in Azure Blob";
}


// bool IsSasTokenAccountLevel(utility::string_t sasToken)
// {
//   // Use cpprestsdk's utility::string_t here since the expected argument is the return value of
//   // as::storage_credentials::sas_token(), which is type utility::string_t (which is a std::wstring on Windows and a std::string on Linux)
//   size_t newIdx = 0;
//   size_t prevIdx = 0;
//   while ((newIdx = sasToken.find('&', prevIdx)) != utility::string_t::npos)
//   {
//     utility::string_t kvpair = sasToken.substr(prevIdx, newIdx - prevIdx);
//     prevIdx = newIdx + 1; // start next time from char after '&'

//     size_t equalsIdx = kvpair.find('=');
//     utility::string_t key = kvpair.substr(0, equalsIdx);
//   #ifdef WIN32
//     const wchar_t* srt = L"srt";
//   #else
//     const char* srt = "srt";
//   #endif
//     if (key == srt) // only account SAS has this parameter
//       return true;

//   }

//   return false;
// }

IStorage* AzureBlobStoragePluginFactory::CreateStorage(const std::string& nameForLogs, const OrthancPlugins::OrthancConfiguration& orthancConfig)
{
  std::string connectionString;
  std::string containerName;
  bool enableLegacyStorageStructure;
  bool storageContainsUnknownFiles;
  bool createContainerIfNotExists;

  if (orthancConfig.IsSection(GetConfigurationSectionName()))
  {
    OrthancPlugins::OrthancConfiguration pluginSection;
    orthancConfig.GetSection(pluginSection, GetConfigurationSectionName());

    if (!BaseStorage::ReadCommonConfiguration(enableLegacyStorageStructure, storageContainsUnknownFiles, pluginSection))
    {
      return nullptr;
    }

    if (!pluginSection.LookupStringValue(connectionString, "ConnectionString"))
    {
      LOG(ERROR) << "AzureBlobStorage/ConnectionString configuration missing.  Unable to initialize plugin";
      return nullptr;
    }

    if (!pluginSection.LookupStringValue(containerName, "ContainerName"))
    {
      LOG(ERROR) << "AzureBlobStorage/ContainerName configuration missing.  Unable to initialize plugin";
      return nullptr;
    }

    boost::trim(connectionString); // without that, if there's an EOL in the string, it fails with "provided uri is invalid"
    boost::trim(containerName);

    createContainerIfNotExists = pluginSection.GetBooleanValue("CreateContainerIfNotExists", true);
  }
  else if (orthancConfig.IsSection("BlobStorage")) // backward compatibility with the old plugin:
  {
    LOG(WARNING) << "AzureBlobStorage: you're using an old configuration format for the plugin.";

    OrthancPlugins::OrthancConfiguration pluginSection;
    orthancConfig.GetSection(pluginSection, "BlobStorage");

    std::string accountName;
    std::string accountKey;

    if (!pluginSection.LookupStringValue(containerName, "ContainerName"))
    {
      LOG(ERROR) << "BlobStorage/AccountName configuration missing.  Unable to initialize plugin";
      return nullptr;
    }

    if (!pluginSection.LookupStringValue(accountName, "AccountName"))
    {
      LOG(ERROR) << "BlobStorage/AccountName configuration missing.  Unable to initialize plugin";
      return nullptr;
    }

    if (!pluginSection.LookupStringValue(accountKey, "AccountKey"))
    {
      LOG(ERROR) << "BlobStorage/ContainerName configuration missing.  Unable to initialize plugin";
      return nullptr;
    }

    std::ostringstream connectionStringBuilder;
    connectionStringBuilder << "DefaultEndpointsProtocol=https;AccountName=" << accountName << ";AccountKey=" << accountKey;
    connectionString = connectionStringBuilder.str();

    createContainerIfNotExists = pluginSection.GetBooleanValue("CreateContainerIfNotExists", true);
  }
  else
  {
    LOG(WARNING) << GetStoragePluginName() << " plugin, section missing.  Plugin is not enabled.";
    return nullptr;
  }

  try
  {
    LOG(INFO) << "Connecting to Azure storage ...";

    as::BlobContainerClient client = as::BlobContainerClient::CreateFromConnectionString(connectionString, containerName);
    LOG(INFO) << "Blob client created";

    if (createContainerIfNotExists)
    {
      // Note: in version up to 2.1.2, we had this code:
      // // blobContainer.create_if_not_exists() throws an error if a service SAS (for a blob container)
      // // was used in the connectionString.
      // // Only allow the use of this function when using storage account-level credentials, whether
      // // through accountName/accountKey combo or account SAS.
      // if ((storageAccount.credentials().is_account_key() ||
      //      (storageAccount.credentials().is_sas() && IsSasTokenAccountLevel(storageAccount.credentials().sas_token())))
      //     && createContainerIfNotExists)

      auto createResult = client.CreateIfNotExists();
      if (createResult.Value.Created)
      {
        LOG(WARNING) << "Blob Storage Area container has been created.  **** check in the Azure console that your container is private ****";
      }
    }

    LOG(INFO) << "Blob storage initialized";

    return new AzureBlobStoragePlugin(nameForLogs, client, enableLegacyStorageStructure, storageContainsUnknownFiles);
  }
  catch (const std::exception& e)
  {
    LOG(ERROR) << "AzureBlobStorage plugin: failed to initialize plugin: " << e.what();
    return nullptr;
  }

}

AzureBlobStoragePlugin::AzureBlobStoragePlugin(const std::string& nameForLogs, const as::BlobContainerClient& blobClient, bool enableLegacyStorageStructure, bool storageContainsUnknownFiles)
  : BaseStorage(nameForLogs, enableLegacyStorageStructure),
    blobClient_(blobClient),
    storageContainsUnknownFiles_(storageContainsUnknownFiles)
{

}

IStorage::IWriter* AzureBlobStoragePlugin::GetWriterForObject(const char* uuid, OrthancPluginContentType type, bool encryptionEnabled)
{
  return new Writer(GetPath(uuid, type, encryptionEnabled), blobClient_);
}

IStorage::IReader* AzureBlobStoragePlugin::GetReaderForObject(const char* uuid, OrthancPluginContentType type, bool encryptionEnabled)
{
  std::list<std::string> paths;
  paths.push_back(GetPath(uuid, type, encryptionEnabled, false));
  if (storageContainsUnknownFiles_)
  {
    paths.push_back(GetPath(uuid, type, encryptionEnabled, true));
  }

  return new Reader(paths, blobClient_);
}

void AzureBlobStoragePlugin::DeleteObject(const char* uuid, OrthancPluginContentType type, bool encryptionEnabled)
{
  std::string path = GetPath(uuid, type, encryptionEnabled);

  try
  {
    as::BlockBlobClient blobClient = blobClient_.GetBlockBlobClient(path);
    blobClient.Delete();
  }
  catch (std::exception& ex)
  {
    throw StoragePluginException("AzureBlobStorage: error while deleting file " + std::string(path) + ": " + ex.what());
  }
}
