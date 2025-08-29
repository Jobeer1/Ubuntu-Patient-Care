/**
 * Indexer plugin for Orthanc
 * Copyright (C) 2021-2025 Sebastien Jodogne, ICTEAM UCLouvain, Belgium
 *
 * This program is free software: you can redistribute it and/or
 * modify it under the terms of the GNU General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program. If not, see <http://www.gnu.org/licenses/>.
 **/


#include "IndexerDatabase.h"
#include "StorageArea.h"

#include "../Resources/Orthanc/Plugins/OrthancPluginCppWrapper.h"

#include <DicomFormat/DicomInstanceHasher.h>
#include <DicomFormat/DicomMap.h>
#include <Logging.h>
#include <SerializationToolbox.h>
#include <SystemToolbox.h>

#include <boost/filesystem.hpp>
#include <boost/thread.hpp>
#include <stack>

#define ORTHANC_PLUGIN_NAME  "indexer"


static std::list<std::string>        folders_;
static IndexerDatabase               database_;
static std::unique_ptr<StorageArea>  storageArea_;
static unsigned int                  intervalSeconds_;


static bool ComputeInstanceId(std::string& instanceId,
                              const void* dicom,
                              size_t size)
{
  if (size > 0 &&
      Orthanc::DicomMap::IsDicomFile(dicom, size))
  {
    try
    {
      OrthancPlugins::OrthancString s;
      s.Assign(OrthancPluginDicomBufferToJson(OrthancPlugins::GetGlobalContext(), dicom, size,
                                              OrthancPluginDicomToJsonFormat_Short,
                                              OrthancPluginDicomToJsonFlags_None, 256));
    
      Json::Value json;
      s.ToJson(json);
    
      static const char* const PATIENT_ID = "0010,0020";
      static const char* const STUDY_INSTANCE_UID = "0020,000d";
      static const char* const SERIES_INSTANCE_UID = "0020,000e";
      static const char* const SOP_INSTANCE_UID = "0008,0018";
    
      Orthanc::DicomInstanceHasher hasher(
        json.isMember(PATIENT_ID) ? Orthanc::SerializationToolbox::ReadString(json, PATIENT_ID) : "",
        Orthanc::SerializationToolbox::ReadString(json, STUDY_INSTANCE_UID),
        Orthanc::SerializationToolbox::ReadString(json, SERIES_INSTANCE_UID),
        Orthanc::SerializationToolbox::ReadString(json, SOP_INSTANCE_UID));

      instanceId = hasher.HashInstance();
      return true;
    }
    catch (Orthanc::OrthancException&)
    {
      return false;
    }
  }
  else
  {
    return false;
  }
}



static void ProcessFile(const std::string& path,
                        const std::time_t time,
                        const uintmax_t size)
{
  std::string oldInstanceId;
  IndexerDatabase::FileStatus status = database_.LookupFile(oldInstanceId, path, time, size);

  if (status == IndexerDatabase::FileStatus_New ||
      status == IndexerDatabase::FileStatus_Modified)
  {
    if (status == IndexerDatabase::FileStatus_Modified)
    {
      database_.RemoveFile(path);
    }
    
    std::string dicom;
    Orthanc::SystemToolbox::ReadFile(dicom, path);

    std::string instanceId;
    if (!dicom.empty() &&
        ComputeInstanceId(instanceId, dicom.c_str(), dicom.size()))
    {
      LOG(INFO) << "New DICOM file detected by the indexer plugin: " << path;

      // The following line must be *before* the "RestApiDelete()" to
      // deal with the case of having two copies of the same DICOM
      // file in the indexed folders, but with different timestamps
      database_.AddDicomInstance(path, time, size, instanceId);
        
      if (status == IndexerDatabase::FileStatus_Modified)
      {
        OrthancPlugins::RestApiDelete("/instances/" + oldInstanceId, false);
      }
    
      try
      {
        Json::Value upload;
        OrthancPlugins::RestApiPost(upload, "/instances", dicom, false);
      }
      catch (Orthanc::OrthancException&)
      {
      }
    }
    else
    {
      LOG(INFO) << "Skipping indexing of non-DICOM file: " << path;
      database_.AddNonDicomFile(path, time, size);

      if (status == IndexerDatabase::FileStatus_Modified)
      {
        OrthancPlugins::RestApiDelete("/instances/" + oldInstanceId, false);
      }
    }
  }
}


static void LookupDeletedFiles()
{
  class Visitor : public IndexerDatabase::IFileVisitor
  {
  private:
    typedef std::pair<std::string, std::string>  DeletedDicom;
    
    std::list<DeletedDicom>  deletedDicom_;
    
  public:
    virtual void VisitInstance(const std::string& path,
                               bool isDicom,
                               const std::string& instanceId) ORTHANC_OVERRIDE
    {
      if (!Orthanc::SystemToolbox::IsRegularFile(path) &&
          isDicom)
      {
        deletedDicom_.push_back(std::make_pair(path, instanceId));
      }
    }

    void ExecuteDelete()
    {
      for (std::list<DeletedDicom>::const_iterator
             it = deletedDicom_.begin(); it != deletedDicom_.end(); ++it)
      {
        const std::string& path = it->first;
        const std::string& instanceId = it->second;

        if (database_.RemoveFile(path))
        {
          OrthancPlugins::RestApiDelete("/instances/" + instanceId, false);      
        }
      }
    }
  };  

  Visitor visitor;
  database_.Apply(visitor);
  visitor.ExecuteDelete();
}


static void MonitorDirectories(bool* stop, unsigned int intervalSeconds)
{
  for (;;)
  {
    std::stack<boost::filesystem::path> s;

    for (std::list<std::string>::const_iterator it = folders_.begin();
         it != folders_.end(); ++it)
    {
      s.push(*it);
    }

    while (!s.empty())
    {
      if (*stop)
      {
        return;
      }
      
      boost::filesystem::path d = s.top();
      s.pop();

      boost::filesystem::directory_iterator current;
    
      try
      {
        current = boost::filesystem::directory_iterator(d);
      }
      catch (boost::filesystem::filesystem_error&)
      {
        LOG(WARNING) << "Indexer plugin cannot read directory: " << d.string();
        continue;
      }

      const boost::filesystem::directory_iterator end;
    
      while (current != end)
      {
        try
        {
          const boost::filesystem::file_status status = boost::filesystem::status(current->path());
          
          switch (status.type())
          {
            case boost::filesystem::regular_file:
            case boost::filesystem::reparse_file:
              try
              {
                ProcessFile(current->path().string(),
                            boost::filesystem::last_write_time(current->path()),
                            boost::filesystem::file_size(current->path()));
              }
              catch (Orthanc::OrthancException& e)
              {
                LOG(ERROR) << e.What();
              }              
              break;
          
            case boost::filesystem::directory_file:
              s.push(current->path());
              break;
          
            default:
              break;
          }
        }
        catch (boost::filesystem::filesystem_error&)
        {
        }

        ++current;
      }
    }

    try
    {
      LookupDeletedFiles();
    }
    catch (Orthanc::OrthancException& e)
    {
      LOG(ERROR) << e.What();
    }
    
    for (unsigned int i = 0; i < intervalSeconds * 10; i++)
    {
      if (*stop)
      {
        return;
      }
      
      boost::this_thread::sleep(boost::posix_time::milliseconds(100));
    }
  }
}


static OrthancPluginErrorCode StorageCreate(const char *uuid,
                                            const void *content,
                                            int64_t size,
                                            OrthancPluginContentType type)
{
  try
  {
    std::string instanceId;
    if (type == OrthancPluginContentType_Dicom &&
        ComputeInstanceId(instanceId, content, size) &&
        database_.AddAttachment(uuid, instanceId))
    {
      // This attachment corresponds to an external DICOM file that is
      // stored in one of the indexed folders, only store a link to it
    }
    else
    {
      // This attachment must be stored in the internal storage area
      storageArea_->Create(uuid, content, size);
    }
    
    return OrthancPluginErrorCode_Success;
  }
  catch (Orthanc::OrthancException& e)
  {
    LOG(ERROR) << e.What();
    return static_cast<OrthancPluginErrorCode>(e.GetErrorCode());
  }
  catch (...)
  {
    return OrthancPluginErrorCode_InternalError;
  }
}



static bool LookupExternalDicom(std::string& externalPath,
                                const char *uuid,
                                OrthancPluginContentType type)
{
  return (type == OrthancPluginContentType_Dicom &&
          database_.LookupAttachment(externalPath, uuid));
}


static OrthancPluginErrorCode StorageReadRange(OrthancPluginMemoryBuffer64 *target,
                                               const char *uuid,
                                               OrthancPluginContentType type,
                                               uint64_t rangeStart)
{
  try
  {
    std::string externalPath;
    if (LookupExternalDicom(externalPath, uuid, type))
    {
      StorageArea::ReadRangeFromPath(target, externalPath, rangeStart);
    }
    else
    {
      storageArea_->ReadRange(target, uuid, rangeStart);
    }
    
    return OrthancPluginErrorCode_Success;
  }
  catch (Orthanc::OrthancException& e)
  {
    LOG(ERROR) << e.What();
    return static_cast<OrthancPluginErrorCode>(e.GetErrorCode());
  }
  catch (...)
  {
    return OrthancPluginErrorCode_InternalError;
  }
}


static OrthancPluginErrorCode StorageReadWhole(OrthancPluginMemoryBuffer64 *target,
                                               const char *uuid,
                                               OrthancPluginContentType type)
{
  try
  {
    std::string externalPath;
    if (LookupExternalDicom(externalPath, uuid, type))
    {
      StorageArea::ReadWholeFromPath(target, externalPath);
    }
    else
    {
      storageArea_->ReadWhole(target, uuid);
    }

    return OrthancPluginErrorCode_Success;
  }
  catch (Orthanc::OrthancException& e)
  {
    LOG(ERROR) << e.What();
    return static_cast<OrthancPluginErrorCode>(e.GetErrorCode());
  }
  catch (...)
  {
    return OrthancPluginErrorCode_InternalError;
  }
}


static OrthancPluginErrorCode StorageRemove(const char *uuid,
                                            OrthancPluginContentType type)
{
  try
  {
    std::string externalPath;
    if (LookupExternalDicom(externalPath, uuid, type))
    {
      database_.RemoveAttachment(uuid);
    }
    else
    {
      database_.RemoveAttachment(uuid);
      storageArea_->RemoveAttachment(uuid);
    }
    
    return OrthancPluginErrorCode_Success;
  }
  catch (Orthanc::OrthancException& e)
  {
    LOG(ERROR) << e.What();
    return static_cast<OrthancPluginErrorCode>(e.GetErrorCode());
  }
  catch (...)
  {
    return OrthancPluginErrorCode_InternalError;
  }
}


static OrthancPluginErrorCode OnChangeCallback(OrthancPluginChangeType changeType,
                                               OrthancPluginResourceType resourceType,
                                               const char* resourceId)
{
  static bool stop_;
  static boost::thread thread_;

  switch (changeType)
  {
    case OrthancPluginChangeType_OrthancStarted:
      stop_ = false;
      thread_ = boost::thread(MonitorDirectories, &stop_, intervalSeconds_);
      break;

    case OrthancPluginChangeType_OrthancStopped:
      stop_ = true;
      if (thread_.joinable())
      {
        thread_.join();
      }
      
      break;

    default:
      break;
  }

  return OrthancPluginErrorCode_Success;
}
      

extern "C"
{
  ORTHANC_PLUGINS_API int32_t OrthancPluginInitialize(OrthancPluginContext* context)
  {
    OrthancPlugins::SetGlobalContext(context);
    Orthanc::Logging::InitializePluginContext(context);
    Orthanc::Logging::EnableInfoLevel(true);

    /* Check the version of the Orthanc core */
    if (OrthancPluginCheckVersion(context) == 0)
    {
      OrthancPlugins::ReportMinimalOrthancVersion(ORTHANC_PLUGINS_MINIMAL_MAJOR_NUMBER,
                                                  ORTHANC_PLUGINS_MINIMAL_MINOR_NUMBER,
                                                  ORTHANC_PLUGINS_MINIMAL_REVISION_NUMBER);
      return -1;
    }

    OrthancPlugins::SetDescription(ORTHANC_PLUGIN_NAME, "Synchronize Orthanc with directories containing DICOM files.");

    OrthancPlugins::OrthancConfiguration configuration;

    OrthancPlugins::OrthancConfiguration indexer;
    configuration.GetSection(indexer, "Indexer");

    bool enabled = indexer.GetBooleanValue("Enable", false);
    if (enabled)
    {
      try
      {
        static const char* const DATABASE = "Database";
        static const char* const FOLDERS = "Folders";
        static const char* const INDEX_DIRECTORY = "IndexDirectory";
        static const char* const ORTHANC_STORAGE = "OrthancStorage";
        static const char* const STORAGE_DIRECTORY = "StorageDirectory";
        static const char* const INTERVAL = "Interval";

        intervalSeconds_ = indexer.GetUnsignedIntegerValue(INTERVAL, 10 /* 10 seconds by default */);
        
        if (!indexer.LookupListOfStrings(folders_, FOLDERS, true) ||
            folders_.empty())
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange,
                                          "Missing configuration option for Indexer plugin: " + std::string(FOLDERS));
        }

        for (std::list<std::string>::const_iterator it = folders_.begin();
             it != folders_.end(); ++it)
        {
          LOG(WARNING) << "The Indexer plugin will monitor the content of folder: " << *it;
        }

        std::string path;
        if (!indexer.LookupStringValue(path, DATABASE))
        {
          std::string folder;
          if (!configuration.LookupStringValue(folder, INDEX_DIRECTORY))
          {
            folder = configuration.GetStringValue(STORAGE_DIRECTORY, ORTHANC_STORAGE);
          }

          Orthanc::SystemToolbox::MakeDirectory(folder);
          path = (boost::filesystem::path(folder) / "indexer-plugin.db").string();
        }
        
        LOG(WARNING) << "Path to the database of the Indexer plugin: " << path;
        database_.Open(path);

        storageArea_.reset(new StorageArea(configuration.GetStringValue(STORAGE_DIRECTORY, ORTHANC_STORAGE)));
      }
      catch (Orthanc::OrthancException& e)
      {
        return -1;
      }
      catch (...)
      {
        LOG(ERROR) << "Native exception while initializing the plugin";
        return -1;
      }

      OrthancPluginRegisterOnChangeCallback(context, OnChangeCallback);
      OrthancPluginRegisterStorageArea2(context, StorageCreate, StorageReadWhole, StorageReadRange, StorageRemove);
    }
    else
    {
      OrthancPlugins::LogWarning("OrthancIndexer is disabled");
    }

    return 0;
  }


  ORTHANC_PLUGINS_API void OrthancPluginFinalize()
  {
    OrthancPlugins::LogWarning("Folder indexer plugin is finalizing");
  }


  ORTHANC_PLUGINS_API const char* OrthancPluginGetName()
  {
    return ORTHANC_PLUGIN_NAME;
  }


  ORTHANC_PLUGINS_API const char* OrthancPluginGetVersion()
  {
    return ORTHANC_PLUGIN_VERSION;
  }
}
