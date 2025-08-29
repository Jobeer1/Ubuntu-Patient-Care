/**
 * Orthanc - A Lightweight, RESTful DICOM Store
 * Copyright (C) 2012-2016 Sebastien Jodogne, Medical Physics
 * Department, University Hospital of Liege, Belgium
 * Copyright (C) 2017-2023 Osimis S.A., Belgium
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


#include "../Resources/Orthanc/Plugins/OrthancPluginCppWrapper.h"
#include "Configuration.h"
#include "DicomWebFormatter.h"

#include <ChunkedBuffer.h>
#include <Compatibility.h>
#include <HttpServer/HttpContentNegociation.h>
#include <Logging.h>
#include <Toolbox.h>
#include <SerializationToolbox.h>
#include <MultiThreading/SharedMessageQueue.h>
#include <MultiThreading/Semaphore.h>
#include <Compression/GzipCompressor.h>

#include <memory>
#include <boost/thread/mutex.hpp>
#include <boost/thread.hpp>
#include <boost/lexical_cast.hpp>
#include <boost/algorithm/string/predicate.hpp>

static const std::string SERIES_METADATA_ATTACHMENT_ID = "4301";
static std::string WADO_BASE_PLACEHOLDER = "$WADO_BASE_PLACEHOLDER$";
static const char* const MAIN_DICOM_TAGS = "MainDicomTags";
static const char* const REQUESTED_TAGS = "RequestedTags";
static const char* const INSTANCES = "Instances";
static const char* const PATIENT_MAIN_DICOM_TAGS = "PatientMainDicomTags";

static std::string instancesMainDicomTagsList;
static boost::mutex mainDicomTagsListMutex;

static bool pluginCanUseExtendedFind_ = false;
static bool isSystemReadOnly_ = false;

void SetPluginCanUseExtendedFind(bool enable)
{
  pluginCanUseExtendedFind_ = enable;
}

bool CanUseExtendedFind()
{
  return pluginCanUseExtendedFind_;
}

void SetSystemIsReadOnly(bool isReadOnly)
{
  isSystemReadOnly_ = isReadOnly;
}

bool IsSystemReadOnly()
{
  return isSystemReadOnly_;
}

static std::string GetResourceUri(Orthanc::ResourceType level,
                                  const std::string& publicId)
{
  switch (level)
  {
    case Orthanc::ResourceType_Study:
      return "/studies/" + publicId;
      
    case Orthanc::ResourceType_Series:
      return "/series/" + publicId;
      
    case Orthanc::ResourceType_Instance:
      return "/instances/" + publicId;
      
    default:
      throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
  }
}



namespace
{
  class MultipartDicomNegotiation : public Orthanc::HttpContentNegociation::IHandler
  {
  private:
    bool&                         transcode_;
    Orthanc::DicomTransferSyntax& targetSyntax_;

  public:
    MultipartDicomNegotiation(
      bool& transcode,
      Orthanc::DicomTransferSyntax& targetSyntax /* set only if transcoding */) :
      transcode_(transcode),
      targetSyntax_(targetSyntax)
    {
    }

    virtual void Handle(const std::string& type,
                        const std::string& subtype,
                        const Orthanc::HttpContentNegociation::Dictionary& parameters) ORTHANC_OVERRIDE
    {
      assert(type == "multipart" &&
             subtype == "related");

      Orthanc::HttpContentNegociation::Dictionary::const_iterator found = parameters.find("type");

      if (found != parameters.end())
      {
        std::string s = found->second;
        Orthanc::Toolbox::ToLowerCase(s);
        if (s != "application/dicom")
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_BadRequest,
                                          "This WADO-RS plugin only supports application/dicom "
                                          "return type for DICOM retrieval (" + found->second + ")");
        }
      }

      found = parameters.find("transfer-syntax");
      if (found != parameters.end())
      {
        /**
         * The "*" case below is related to Google Healthcare API:
         * https://groups.google.com/d/msg/orthanc-users/w1Ekrsc6-U8/T2a_DoQ5CwAJ
         **/
        if (found->second == "*")
        {
          transcode_ = false;
        }
        else
        {
          transcode_ = true;

          if (!Orthanc::LookupTransferSyntax(targetSyntax_, found->second))
          {
            throw Orthanc::OrthancException(Orthanc::ErrorCode_BadRequest,
                                            "Unsupported transfer syntax in WADO-RS: " + found->second);
          }
        }
      }
    }
  };
}


static void AcceptMultipartDicom(bool& transcode,
                                 Orthanc::DicomTransferSyntax& targetSyntax /* only if transcoding */,
                                 const OrthancPluginHttpRequest* request)
{
  /**
   * Up to release 1.4 of the DICOMweb plugin, WADO-RS
   * RetrieveInstance, RetrieveSeries and RetrieveStudy did *NOT*
   * transcode if no transer syntax was explicitly provided. This was
   * because the DICOM standard didn't specify a behavior in this case
   * up to DICOM 2016b:
   * http://dicom.nema.org/medical/dicom/2016b/output/chtml/part18/sect_6.5.3.html
   *
   * However, starting with DICOM 2016c, it is explicitly stated that
   * "If transfer-syntax is not specified in the dcm-parameters the
   * origin server shall use the Explicit VR Little Endian Transfer
   * Syntax "1.2.840.10008.1.2.1" for each Instance":
   * http://dicom.nema.org/medical/dicom/2016c/output/chtml/part18/sect_6.5.3.html
   * 
   * As a consequence, starting with release 1.5 of the DICOMweb
   * plugin, transcoding to "Little Endian Explicit" takes place by
   * default. If this transcoding is not desirable, the "Accept" HTTP
   * header can be set to
   * "multipart/related;type=application/dicom;transfer-syntax=*" (note
   * the asterisk "*") in order to prevent transcoding. The same
   * convention is used by the Google Cloud Platform:
   * https://cloud.google.com/healthcare/docs/dicom
   **/

  // By default, return "multipart/related; type=application/dicom; transfer-syntax=1.2.840.10008.1.2.1"
  transcode = true;
  targetSyntax = Orthanc::DicomTransferSyntax_LittleEndianExplicit;
  
  std::string accept;
  if (OrthancPlugins::LookupHttpHeader(accept, request, "accept"))
  {
    Orthanc::HttpContentNegociation negotiation;

    MultipartDicomNegotiation dicom(transcode, targetSyntax);
    negotiation.Register("multipart/related", dicom);

    if (!negotiation.Apply(accept))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadRequest,
                                      "This WADO-RS plugin cannot generate the following content type: " + accept);
    }
  }
}


namespace
{
  class AcceptMetadataJson : public Orthanc::HttpContentNegociation::IHandler
  {
  public:
    virtual void Handle(const std::string& type,
                        const std::string& subtype,
                        const Orthanc::HttpContentNegociation::Dictionary& parameters) ORTHANC_OVERRIDE
    {
      assert(type == "application");
      assert(subtype == "json" || subtype == "dicom+json");
    }
  };

  class AcceptMetadataMultipart : public Orthanc::HttpContentNegociation::IHandler
  {
  private:
    bool& isXml_;

  public:
    explicit AcceptMetadataMultipart(bool& isXml /* out */) :
      isXml_(isXml)
    {
    }

    virtual void Handle(const std::string& type,
                        const std::string& subtype,
                        const Orthanc::HttpContentNegociation::Dictionary& parameters) ORTHANC_OVERRIDE
    {
      assert(type == "multipart" &&
             subtype == "related");

      Orthanc::HttpContentNegociation::Dictionary::const_iterator found = parameters.find("type");

      if (found != parameters.end())
      {
        if (found->second == "application/dicom+xml")
        {
          isXml_ = true;
        }
        else
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_BadRequest,
                                          "This WADO-RS plugin only supports application/dicom+xml "
                                          "type for multipart/related accept (" + found->second + ")");
        }
      }
      else
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_BadRequest,
                                        "Missing \"type\" in multipart/related accept type");
      }

      found = parameters.find("transfer-syntax");
      if (found != parameters.end())
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_BadRequest,
                                        "This WADO-RS plugin cannot change the transfer syntax to " +
                                        found->second);
      }
    }
  };
}


static void AcceptMetadata(const OrthancPluginHttpRequest* request,
                           bool& isXml)
{
  isXml = false;    // By default, return application/dicom+json

  std::string accept;
  if (OrthancPlugins::LookupHttpHeader(accept, request, "accept"))
  {
    Orthanc::HttpContentNegociation negotiation;

    AcceptMetadataJson json;
    negotiation.Register("application/json", json);
    negotiation.Register("application/dicom+json", json);

    AcceptMetadataMultipart multipart(isXml);
    negotiation.Register("multipart/related", multipart);

    if (!negotiation.Apply(accept))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadRequest,
                                      "This WADO-RS plugin cannot generate the following content type: " + accept);
    }
  }
}



namespace
{
  class BulkDataNegotiation : public Orthanc::HttpContentNegociation::IHandler
  {
  public:
    virtual void Handle(const std::string& type,
                        const std::string& subtype,
                        const Orthanc::HttpContentNegociation::Dictionary& parameters) ORTHANC_OVERRIDE
    {
      assert(type == "multipart" &&
             subtype == "related");

      Orthanc::HttpContentNegociation::Dictionary::const_iterator found = parameters.find("type");

      if (found != parameters.end())
      {
        std::string s = found->second;
        Orthanc::Toolbox::ToLowerCase(s);
        if (s != "application/octet-stream")
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_BadRequest,
                                          "This WADO-RS plugin only supports application/octet-stream "
                                          "return type for bulk data retrieval (" + found->second + ")");
        }
      }

      if (parameters.find("range") != parameters.end())
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_BadRequest,
                                        "This WADO-RS plugin does not support Range retrieval, "
                                        "it can only return entire bulk data object");
      }
    }
  };
}


static void AcceptBulkData(const OrthancPluginHttpRequest* request)
{
  // By default, return "multipart/related; type=application/octet-stream;"

  std::string accept;

  if (OrthancPlugins::LookupHttpHeader(accept, request, "accept"))
  {
    Orthanc::HttpContentNegociation negotiation;

    BulkDataNegotiation bulk;
    negotiation.Register("multipart/related", bulk);

    if (!negotiation.Apply(accept))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadRequest,
                                    "This WADO-RS plugin cannot generate the following "
                                    "bulk data type: " + accept);
    }
  }
}

class InstanceToPreload : public Orthanc::IDynamicObject
{
private:
  std::string instanceId_;
  bool transcode_;

public:
  explicit InstanceToPreload(const std::string& instanceId, bool transcode) : 
    instanceId_(instanceId),
    transcode_(transcode)
  {
  }

  virtual ~InstanceToPreload() ORTHANC_OVERRIDE
  {
  }

  const std::string& GetInstanceId() const {return instanceId_;}

  bool NeedsTranscoding() const {return transcode_;}
};


class LoadedInstance : public Orthanc::IDynamicObject
{
private:
  std::unique_ptr<OrthancPlugins::DicomInstance> dicom_;

public:
  explicit LoadedInstance(OrthancPlugins::DicomInstance* dicom) : 
    dicom_(dicom)
  {
  }

  virtual ~LoadedInstance() ORTHANC_OVERRIDE
  {
  }

  OrthancPlugins::DicomInstance* ReleaseInstance() 
  {
    return dicom_.release();
  }
};


class InstanceLoader : public boost::noncopyable
{
protected:
  bool                                  transcode_;
  Orthanc::DicomTransferSyntax          targetTransferSyntax_;

  OrthancPlugins::DicomInstance* GetAndTranscodeDicom(InstanceToPreload* instanceToLoad)
  {
    std::unique_ptr<OrthancPlugins::DicomInstance> dicom(OrthancPlugins::DicomInstance::Load(instanceToLoad->GetInstanceId(),
                                                                                             OrthancPluginLoadDicomInstanceMode_WholeDicom));
    if (transcode_ && instanceToLoad->NeedsTranscoding())
    {
      dicom.reset(dicom->Transcode(dicom->GetBuffer(),
                                    dicom->GetSize(),
                                    Orthanc::GetTransferSyntaxUid(targetTransferSyntax_)));
    }

    return dicom.release();
  }

public:
  explicit InstanceLoader(bool transcode, Orthanc::DicomTransferSyntax targetTransferSyntax)
  : transcode_(transcode),
    targetTransferSyntax_(targetTransferSyntax)
  {
  }

  virtual ~InstanceLoader()
  {
  }

  virtual void PrepareDicom(const std::string& instanceId, bool transcode) = 0;

  virtual OrthancPlugins::DicomInstance* GetNextDicom() = 0;

};


class ThreadedInstanceLoader : public InstanceLoader
{
  std::vector<boost::thread*>         threads_;

  Orthanc::SharedMessageQueue         instancesToPreload_;

  Orthanc::SharedMessageQueue         loadedInstances_;

  Orthanc::Semaphore                  bufferSemaphore_;

public:
  ThreadedInstanceLoader(size_t threadCount, bool transcode, Orthanc::DicomTransferSyntax transferSyntax)
  : InstanceLoader(transcode, transferSyntax),
    instancesToPreload_(0),
    loadedInstances_(0),
    bufferSemaphore_(3*threadCount) // to limit the number of loaded instances in memory
  {
    for (size_t i = 0; i < threadCount; i++)
    {
      threads_.push_back(new boost::thread(PreloaderWorkerThread, this));
    }
  }

  virtual ~ThreadedInstanceLoader()
  {
    Clear();
  }

  void Clear()
  {
    for (size_t i = 0; i < threads_.size(); i++)
    {
      instancesToPreload_.Enqueue(NULL);
    }

    for (size_t i = 0; i < threads_.size(); i++)
    {
      if (threads_[i]->joinable())
      {
        threads_[i]->join();
      }
      delete threads_[i];
    }

    threads_.clear();
  }

  static void PreloaderWorkerThread(ThreadedInstanceLoader* that)
  {
    static uint16_t threadCounter = 0;
    Orthanc::Logging::SetCurrentThreadName(std::string("WADO-LOAD-") + boost::lexical_cast<std::string>(threadCounter++));

    while (true)
    {
      std::unique_ptr<InstanceToPreload> instanceToPreload(dynamic_cast<InstanceToPreload*>(that->instancesToPreload_.Dequeue(0)));
      if (instanceToPreload.get() == NULL)  // that's the signal to exit the thread
      {
        return;
      }
      
      // wait for the consumers, no need to accumulate instances in memory if loaders are faster than writers
      that->bufferSemaphore_.Acquire();

      try
      {
        std::unique_ptr<OrthancPlugins::DicomInstance> dicom(that->GetAndTranscodeDicom(instanceToPreload.get()));
        that->loadedInstances_.Enqueue(new LoadedInstance(dicom.release()));
      }
      catch (Orthanc::OrthancException& e)
      {
        LOG(ERROR) << "Error while loading instances " << e.GetDetails();
        that->loadedInstances_.Enqueue(NULL);
      }
      catch (...)
      {
        LOG(ERROR) << "Unknown error while loading instances ";
        that->loadedInstances_.Enqueue(NULL);
      }

    }
  }

  virtual void PrepareDicom(const std::string& instanceId, bool transcode) ORTHANC_OVERRIDE
  {
    instancesToPreload_.Enqueue(new InstanceToPreload(instanceId, transcode));
  }

  virtual OrthancPlugins::DicomInstance* GetNextDicom() ORTHANC_OVERRIDE
  {
    std::unique_ptr<LoadedInstance> loadedInstance(dynamic_cast<LoadedInstance*>(loadedInstances_.Dequeue(0)));
    
    // unlock preloader threads to buffer the following instances
    bufferSemaphore_.Release();

    if (loadedInstance.get() != NULL)
    {
      return loadedInstance->ReleaseInstance();
    }
    else
    {
      return NULL;
    }
  }
};


class SynchronousInstanceLoader : public InstanceLoader
{
  std::list<boost::shared_ptr<InstanceToPreload> >         instancesToLoad_;

public:
  SynchronousInstanceLoader(bool transcode, Orthanc::DicomTransferSyntax transferSyntax)
  : InstanceLoader(transcode, transferSyntax)
  {
  }

  virtual ~SynchronousInstanceLoader()
  {
    Clear();
  }

  void Clear()
  {
    instancesToLoad_.clear();
  }

  virtual void PrepareDicom(const std::string& instanceId, bool transcode) ORTHANC_OVERRIDE
  {
    instancesToLoad_.push_back(boost::shared_ptr<InstanceToPreload>(new InstanceToPreload(instanceId, transcode)));
  }

  virtual OrthancPlugins::DicomInstance* GetNextDicom() ORTHANC_OVERRIDE
  {
    boost::shared_ptr<InstanceToPreload> instanceToLoad(instancesToLoad_.front());
    instancesToLoad_.pop_front();

    if (instanceToLoad.get() == NULL)
    {
      return NULL;
    }

    return GetAndTranscodeDicom(instanceToLoad.get());
  }
};


static void AnswerListOfDicomInstances(OrthancPluginRestOutput* output,
                                       Orthanc::ResourceType level,
                                       const std::string& publicId,
                                       bool transcode,
                                       Orthanc::DicomTransferSyntax targetSyntax /* only if transcoding */)
{
  Orthanc::Toolbox::ElapsedTimer perfTimer;
  size_t perfTotalSizeInBytes = 0;
  size_t perfTotalInstancesCount = 0;

  if (level != Orthanc::ResourceType_Study &&
      level != Orthanc::ResourceType_Series &&
      level != Orthanc::ResourceType_Instance)
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
  }

  OrthancPluginContext* context = OrthancPlugins::GetGlobalContext();

  Json::Value instances;

  if (level == Orthanc::ResourceType_Instance)
  {
    Json::Value tmp = Json::objectValue;
    tmp["ID"] = publicId;

    if (transcode)
    {
      std::string sourceTransferSyntax;
      if (OrthancPlugins::RestApiGetString(sourceTransferSyntax, "/instances/" + publicId + "/metadata/TransferSyntax", false))
      {
        tmp["Metadata"] = Json::objectValue;
        tmp["Metadata"]["TransferSyntax"] = sourceTransferSyntax;
      }
    }

    instances = Json::arrayValue;
    instances.append(tmp);
  }
  else
  {
    if (CanUseExtendedFind())
    {
      Json::Value toolsFindPayload;

      toolsFindPayload["Query"] = Json::objectValue;
      toolsFindPayload["ResponseContent"] = Json::arrayValue;
      toolsFindPayload["Level"] = "Instance";
      
      if (transcode)
      {
        toolsFindPayload["ResponseContent"].append("Metadata");
      }
      
      if (level == Orthanc::ResourceType_Patient)
      {
        toolsFindPayload["ParentPatient"] = publicId;
      } 
      else if (level == Orthanc::ResourceType_Study)
      {
        toolsFindPayload["ParentStudy"] = publicId;
      } 
      else if (level == Orthanc::ResourceType_Series)
      {
        toolsFindPayload["ParentSeries"] = publicId;
      }

      if (!OrthancPlugins::RestApiPost(instances, "/tools/find", toolsFindPayload, false))
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_UnknownResource, "Unable to list instances");
      }
    }
    else
    {
      if (!OrthancPlugins::RestApiGet(instances, GetResourceUri(level, publicId) + "/instances", false))
      {
        // Internal error
        OrthancPluginSendHttpStatusCode(context, output, 400);
        return;
      }

      if (transcode)
      {
        for (Json::Value::ArrayIndex i = 0; i < instances.size(); i++)
        {
          const std::string uri = "/instances/" + instances[i]["ID"].asString();

          std::string sourceTransferSyntax;
          if (OrthancPlugins::RestApiGetString(sourceTransferSyntax, uri + "/metadata/TransferSyntax", false))
          {
            instances[i]["Metadata"] = Json::objectValue;
            instances[i]["Metadata"]["TransferSyntax"] = sourceTransferSyntax;
          }
        }
      }
    }
  }

  if (OrthancPluginStartMultipartAnswer(context, output, "related", "application/dicom"))
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_NetworkProtocol);
  }

  // single threaded or multi threaded loading ?
  std::unique_ptr<InstanceLoader> loader;
  
  const unsigned int workersCount = OrthancPlugins::Configuration::GetWadoRsLoaderThreadsCount();

  if (workersCount > 0 && level != Orthanc::ResourceType_Instance)
  {
    loader.reset(new ThreadedInstanceLoader(workersCount, transcode, targetSyntax));
  }
  else
  {
    loader.reset(new SynchronousInstanceLoader(transcode, targetSyntax));
  }
  
  for (Json::Value::ArrayIndex i = 0; i < instances.size(); i++)
  {
    bool transcodeThisInstance;
    Orthanc::DicomTransferSyntax currentSyntax;

    if (!transcode || !instances[i].isMember("Metadata") || !instances[i]["Metadata"].isMember("TransferSyntax"))
    {
      transcodeThisInstance = false;      
    }
    else if (Orthanc::LookupTransferSyntax(currentSyntax, instances[i]["Metadata"]["TransferSyntax"].asString()))
    {
      transcodeThisInstance = (currentSyntax != targetSyntax);
    }
    else
    {
      transcodeThisInstance = true;
    }

    loader->PrepareDicom(instances[i]["ID"].asString(), transcodeThisInstance);
  }

  perfTotalInstancesCount = instances.size();

  for (Json::Value::ArrayIndex i = 0; i < instances.size(); i++)
  {
    std::unique_ptr<OrthancPlugins::DicomInstance> dicom(loader->GetNextDicom());

    if (dicom.get() != NULL)
    {
      if (OrthancPluginSendMultipartItem(
          context, output, reinterpret_cast<const char*>(dicom->GetBuffer()),
          dicom->GetSize()) != 0)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
      }
      perfTotalSizeInBytes += dicom->GetSize();
    }
    else
    {
      LOG(WARNING) << "Failed to load an instance";
    }
  }

  if (OrthancPlugins::Configuration::IsPerformanceLogsEnabled())
  {
    uint64_t elapsedMicrosends = perfTimer.GetElapsedMicroseconds();
    float instancesPerSeconds = float(perfTotalInstancesCount) / (float(elapsedMicrosends) / 1000000.0f);
    LOG(INFO) << "WADO-RS: elapsed: " << perfTimer.GetElapsedMicroseconds() << " us, rate: " << std::fixed << std::setprecision(2) << instancesPerSeconds << " instances/s, " << Orthanc::Toolbox::GetHumanTransferSpeed(false, perfTotalSizeInBytes, elapsedMicrosends * 1000);
  }
}



namespace
{
  class SetOfDicomInstances : public boost::noncopyable
  {
  private:
    std::vector<Orthanc::DicomMap*>  instances_;

  public:
    ~SetOfDicomInstances()
    {
      for (size_t i = 0; i < instances_.size(); i++)
      {
        assert(instances_[i] != NULL);
        delete instances_[i];
      }
    }

    size_t GetSize() const
    {
      return instances_.size();
    }

    bool ReadInstance(const std::string& publicId)
    {
      Json::Value dicomAsJson;
      
      if (OrthancPlugins::RestApiGet(dicomAsJson, "/instances/" + publicId + "/tags", false))
      {
        std::unique_ptr<Orthanc::DicomMap> instance(new Orthanc::DicomMap);
        instance->FromDicomAsJson(dicomAsJson);
        instances_.push_back(instance.release());
        
        return true;
      }
      else
      {
        return false;
      }
    }

    
    void MinorityReport(Orthanc::DicomMap& target,
                        const Orthanc::DicomTag& tag) const
    {
      typedef std::map<std::string, unsigned int>  Counters;

      Counters counters;

      for (size_t i = 0; i < instances_.size(); i++)
      {
        assert(instances_[i] != NULL);

        std::string value;
        if (instances_[i]->LookupStringValue(value, tag, false))
        {
          Counters::iterator found = counters.find(value);
          if (found == counters.end())
          {
            counters[value] = 1;
          }
          else
          {
            found->second ++;
          }
        }
      }

      if (!counters.empty())
      {
        Counters::const_iterator current = counters.begin();
          
        std::string maxValue = current->first;
        size_t maxCount = current->second;

        ++current;

        while (current != counters.end())
        {
          if (maxCount < current->second)
          {
            maxValue = current->first;
            maxCount = current->second;
          }
            
          ++current;
        }

        target.SetValue(tag, maxValue, false);

        // Take the ceiling of the number of available instances
        const size_t threshold = instances_.size() / 2 + 1;
        if (maxCount < threshold)
        {
          LOG(WARNING) << "No consensus on the value of a tag during WADO-RS Retrieve "
                       << "Metadata in Extrapolate mode: " << tag.Format();
        }
      }
    }
  };

  
  class MainDicomTagsCache : public boost::noncopyable
  {
  private:
    struct Info : public boost::noncopyable
    {
      Orthanc::DicomMap  dicom_;
      std::string        parent_;
    };
    
    typedef std::pair<std::string, Orthanc::ResourceType>  Index;
    typedef std::map<Index, Info*>                         Content;

    Content  content_;

    static bool ReadResource(Orthanc::DicomMap& dicom,
                             std::string& parent,
                             OrthancPlugins::MetadataMode mode,
                             const std::string& orthancId,
                             Orthanc::ResourceType level)
    {
      std::string uri;
      std::string parentField;

      switch (level)
      {
        case Orthanc::ResourceType_Study:
          uri = "/studies/" + orthancId + "?full";
          break;
            
        case Orthanc::ResourceType_Series:
          uri = "/series/" + orthancId + "?full";
          parentField = "ParentStudy";
          break;
            
        case Orthanc::ResourceType_Instance:
          uri = "/instances/" + orthancId + "?full";
          parentField = "ParentSeries";
          break;

        default:
          throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
      }

      Json::Value value;
      if (!OrthancPlugins::RestApiGet(value, uri, false))
      {
        return false;
      }
         

      if (value.type() != Json::objectValue ||
          !value.isMember(MAIN_DICOM_TAGS))
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
      }

      dicom.FromDicomAsJson(value[MAIN_DICOM_TAGS], false /* append */, true /* parseSequences */);

      if (level == Orthanc::ResourceType_Study)
      {
        if (value.isMember(PATIENT_MAIN_DICOM_TAGS))
        {
          dicom.FromDicomAsJson(value[PATIENT_MAIN_DICOM_TAGS], true /* append */, true /* parseSequences */);
        }
        else
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
        }
      }
        
      if (!parentField.empty())
      {
        if (value.isMember(parentField) &&
            value[parentField].type() == Json::stringValue)
        {
          parent = value[parentField].asString();
        }
        else
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
        }
      }

      
      if (mode == OrthancPlugins::MetadataMode_Extrapolate &&
          (level == Orthanc::ResourceType_Series ||
           level == Orthanc::ResourceType_Study))
      {
        std::set<Orthanc::DicomTag> tags;
        OrthancPlugins::Configuration::GetExtrapolatedMetadataTags(tags, level);

        if (!tags.empty())
        {
          /**
           * Complete the series/study-level tags, with instance-level
           * tags that are not considered as "main DICOM tags" in
           * Orthanc, but that are necessary for Web viewers, and that
           * are expected to be constant throughout all the instances of
           * the study/series. To this end, we read up to "N" DICOM
           * instances of this study/series from disk, and for the tags
           * of interest, we look at whether there is a consensus in the
           * value among these instances. Obviously, this is an
           * approximation to improve performance.
           **/

          std::set<std::string> allInstances;

          switch (level)
          {
            case Orthanc::ResourceType_Series:
              if (!value.isMember(INSTANCES) ||
                  value[INSTANCES].type() != Json::arrayValue)
              {
                throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
              }
              else
              {
                for (Json::Value::ArrayIndex i = 0; i < value[INSTANCES].size(); i++)
                {
                  if (value[INSTANCES][i].type() != Json::stringValue)
                  {
                    throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
                  }
                  else
                  {
                    allInstances.insert(value[INSTANCES][i].asString());
                  }            
                }
              }
              
              break;

            case Orthanc::ResourceType_Study:
            {
              Json::Value tmp;
              if (OrthancPlugins::RestApiGet(tmp, "/studies/" + orthancId + "/instances", false))
              {
                if (tmp.type() != Json::arrayValue)
                {
                  throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
                }

                for (Json::Value::ArrayIndex i = 0; i < tmp.size(); i++)
                {
                  if (tmp[i].type() != Json::objectValue ||
                      !tmp[i].isMember("ID") ||
                      tmp[i]["ID"].type() != Json::stringValue)
                  {
                    throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
                  }
                  else
                  {
                    allInstances.insert(tmp[i]["ID"].asString());
                  }
                }
              }
              
              break;
            }

            default:
              throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
          }

          
          // Select up to N random instances. The instances are
          // implicitly selected randomly, as the public ID of an
          // instance is a SHA-1 hash (whose domain is uniformly distributed)

          static const size_t N = 3;
          SetOfDicomInstances selectedInstances;

          for (std::set<std::string>::const_iterator it = allInstances.begin();
               selectedInstances.GetSize() < N && it != allInstances.end(); ++it)
          {
            selectedInstances.ReadInstance(*it);
          }

          for (std::set<Orthanc::DicomTag>::const_iterator
                 it = tags.begin(); it != tags.end(); ++it)
          {
            selectedInstances.MinorityReport(dicom, *it);
          }
        }
      }

      return true;
    }
    

    bool Lookup(Orthanc::DicomMap& dicom,
                std::string& parent,
                OrthancPlugins::MetadataMode mode,
                const std::string& orthancId,
                Orthanc::ResourceType level)
    {
      Content::iterator found = content_.find(std::make_pair(orthancId, level));
      
      if (found == content_.end())
      {
        std::unique_ptr<Info> info(new Info);
        if (!ReadResource(info->dicom_, info->parent_, mode, orthancId, level))
        {
          return false;
        }

        found = content_.insert(std::make_pair(std::make_pair(orthancId, level), info.release())).first;
      }

      assert(found != content_.end() &&
             found->second != NULL);
      dicom.Merge(found->second->dicom_);
      parent = found->second->parent_;

      return true;
    }


  public:
    ~MainDicomTagsCache()
    {
      for (Content::iterator it = content_.begin(); it != content_.end(); ++it)
      {
        assert(it->second != NULL);
        delete it->second;
      }
    }


    bool GetInstance(Orthanc::DicomMap& dicom,
                     OrthancPlugins::MetadataMode mode,
                     const std::string& instanceOrthancId)
    {
      std::string seriesOrthancId, studyOrthancId, nope;
      
      return (ReadResource(dicom, seriesOrthancId, mode, instanceOrthancId, Orthanc::ResourceType_Instance) &&
              Lookup(dicom, studyOrthancId, mode, seriesOrthancId, Orthanc::ResourceType_Series) &&
              Lookup(dicom, nope /* patient id is unused */, mode, studyOrthancId, Orthanc::ResourceType_Study));
    }

    bool GetSeries(Orthanc::DicomMap& dicom,
                   OrthancPlugins::MetadataMode mode,
                   const std::string& seriesOrthancId)
    {
      std::string studyOrthancId, nope;
      
      return (Lookup(dicom, studyOrthancId, mode, seriesOrthancId, Orthanc::ResourceType_Series) &&
              Lookup(dicom, nope /* patient id is unused */, mode, studyOrthancId, Orthanc::ResourceType_Study));
    }
  };
}


static void WriteInstanceMetadata(OrthancPlugins::DicomWebFormatter::HttpWriter& writer,
                                  OrthancPlugins::MetadataMode mode,
                                  MainDicomTagsCache& cache,
                                  const std::string& orthancId,
                                  const std::string& studyInstanceUid,
                                  const std::string& seriesInstanceUid,
                                  const std::string& wadoBase)
{
  assert(!orthancId.empty() &&
         !studyInstanceUid.empty() &&
         !seriesInstanceUid.empty() &&
         !wadoBase.empty());

  Orthanc::DicomMap dicom;

  if (!cache.GetInstance(dicom, mode, orthancId))
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_UnknownResource, "instance not found: " + orthancId);
  }

  switch (mode)
  {
    case OrthancPlugins::MetadataMode_MainDicomTags:
    case OrthancPlugins::MetadataMode_Extrapolate:
    {
      writer.AddOrthancMap(dicom);
      break;
    }

    case OrthancPlugins::MetadataMode_Full:
    {
      const std::string bulkRoot = (wadoBase +
                                    "studies/" + studyInstanceUid +
                                    "/series/" + seriesInstanceUid + 
                                    "/instances/" + dicom.GetStringValue(Orthanc::DICOM_TAG_SOP_INSTANCE_UID, "", false) + "/bulk");

#if ORTHANC_PLUGINS_VERSION_IS_ABOVE(1, 12, 1)
      std::unique_ptr<OrthancPlugins::DicomInstance> instance;

      try
      {
        instance.reset(OrthancPlugins::DicomInstance::Load(orthancId, OrthancPluginLoadDicomInstanceMode_EmptyPixelData));
      }
      catch (Orthanc::OrthancException& e)
      {
      }

      if (instance.get() != NULL)
      {
        writer.AddInstance(*instance, bulkRoot);
      }
#else
      // On a SSD drive, this version is twice slower than if using
      // cache (see below)

      OrthancPlugins::MemoryBuffer dicomFile;
      if (dicomFile.RestApiGet("/instances/" + orthancId + "/file", false))
      {
        writer.AddDicom(dicomFile.GetData(), dicomFile.GetSize(), bulkRoot);
      }
#endif

      break;
    }

    default:
      throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
  }
    
  
#if 0
  /**
   **/

  // TODO - Have a global setting to enable/disable caching of DICOMweb

  // TODO - Have a way to clear the "4444" attachments if Orthanc
  // version changes => Store Orthanc core version in a prefix or in
  // another attachment?
    
  OrthancPlugins::MemoryBuffer buffer;

  if (writer.IsXml())
  {
    // DICOMweb XML is not cached
    if (buffer.RestApiGet("/instances/" + orthancId + "/file", false))
    {
      writer.AddDicom(buffer.GetData(), buffer.GetSize(), bulkRoot);
    }
  }
  else
  {
    if (buffer.RestApiGet("/instances/" + orthancId + "/attachments/4444/data", false))
    {
      writer.AddDicomWebInstanceSerializedJson(buffer.GetData(), buffer.GetSize());
    }
    else if (buffer.RestApiGet("/instances/" + orthancId + "/file", false))
    {
      // "Ignore binary mode" in DICOMweb conversion if caching is
      // enabled, as the bulk root can change across executions

      std::string dicomweb;
      {
        // TODO - Avoid a global mutex => Need to change Orthanc SDK
        OrthancPlugins::DicomWebFormatter::Apply(
          dicomweb, OrthancPlugins::GetGlobalContext(), buffer.GetData(), buffer.GetSize(),
          false /* JSON */, OrthancPluginDicomWebBinaryMode_Ignore, "");
      }

      try
      {
        buffer.RestApiPut("/instances/" + orthancId + "/attachments/4444", dicomweb, false);
      }
      catch (Orthanc::OrthancException& e)
      {
        // An exception might occur if another writer has concurrently created the attachment, ignore this case
      }

      writer.AddDicomWebInstanceSerializedJson(dicomweb.c_str(), dicomweb.size());
    }
  }
#endif
}

bool LocateResource(OrthancPluginRestOutput* output,
                    std::string& orthancId,
                    std::map<std::string, std::string>& metadata, 
                    const std::string& studyInstanceUid,
                    const std::string& seriesInstanceUid,
                    const std::string& sopInstanceUid,
                    const std::string& level,
                    const OrthancPluginHttpRequest* request,
                    bool firstResourceOnly)
{
  OrthancPluginContext* context = OrthancPlugins::GetGlobalContext();

  if (request->method != OrthancPluginHttpMethod_Get)
  {
    OrthancPluginSendMethodNotAllowed(context, output, "GET");
    return false;
  }

  {
    Json::Value payload;
    Json::Value payloadQuery;

    payload["Level"] = level;
    
    if (!sopInstanceUid.empty())
    {
      payloadQuery["SOPInstanceUID"] = sopInstanceUid;
    }
    
    if (!seriesInstanceUid.empty())
    {
      payloadQuery["SeriesInstanceUID"] = seriesInstanceUid;
    }

    if (firstResourceOnly)
    {
      payload["Limit"] = 1;
    }

    payloadQuery["StudyInstanceUID"] = studyInstanceUid;
    payload["Query"] = payloadQuery;
    payload["ResponseContent"] = Json::arrayValue;
    payload["ResponseContent"].append("Metadata");

    std::map<std::string, std::string> httpHeaders;
    OrthancPlugins::GetHttpHeaders(httpHeaders, request);

    Json::Value resources;
    if (!OrthancPlugins::RestApiPost(resources, "/tools/find", payload, httpHeaders, true) ||
        resources.type() != Json::arrayValue)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
    }

    if (resources.size() == 0)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_InexistentItem,
                                      "Accessing an inexistent " + level + " with WADO-RS: " + studyInstanceUid + "/" + seriesInstanceUid + "/" + sopInstanceUid);
    }
    if (resources.size() > 1)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_InexistentItem,
                                      "Multiple " + level + " found for WADO-RS: " + studyInstanceUid + "/" + seriesInstanceUid + "/" + sopInstanceUid);
    }
    orthancId = resources[0]["ID"].asString();
    Json::Value::Members metadataMembers = resources[0]["Metadata"].getMemberNames();
    
    for (size_t i = 0; i < metadataMembers.size(); ++i)
    {
      metadata[metadataMembers[i]] = resources[0]["Metadata"][metadataMembers[i]].asString();
    }
    
    return true;
  }
}



bool LocateStudy(OrthancPluginRestOutput* output,
                 std::string& studyOrthancId,
                 std::string& studyInstanceUid,
                 const OrthancPluginHttpRequest* request)
{
  std::string sopInstanceUid;
  std::string seriesInstanceUid;
  std::map<std::string, std::string> metadata;
  studyInstanceUid = request->groups[0];

  return LocateResource(output,
                        studyOrthancId,
                        metadata,
                        studyInstanceUid,
                        seriesInstanceUid,
                        sopInstanceUid,
                        "Study",
                        request,
                        false);
}


bool LocateSeries(OrthancPluginRestOutput* output,
                  std::string& seriesOrthancId,
                  std::string& studyInstanceUid,
                  std::string& seriesInstanceUid,
                  const OrthancPluginHttpRequest* request)
{
  std::string sopInstanceUid;
  std::map<std::string, std::string> metadata;
  studyInstanceUid = request->groups[0];
  seriesInstanceUid = request->groups[1];

  return LocateResource(output,
                        seriesOrthancId,
                        metadata,
                        studyInstanceUid,
                        seriesInstanceUid,
                        sopInstanceUid,
                        "Series",
                        request,
                        false);
}


bool LocateInstance(OrthancPluginRestOutput* output,
                    std::string& instanceOrthancId,
                    std::string& studyInstanceUid,
                    std::string& seriesInstanceUid,
                    std::string& sopInstanceUid,
                    std::string& transferSyntaxMetadata,
                    const OrthancPluginHttpRequest* request)
{
  std::map<std::string, std::string> metadata;
  studyInstanceUid = request->groups[0];
  seriesInstanceUid = request->groups[1];
  sopInstanceUid = request->groups[2];

  bool ret = LocateResource(output,
                            instanceOrthancId,
                            metadata,
                            studyInstanceUid,
                            seriesInstanceUid,
                            sopInstanceUid,
                            "Instance",
                            request,
                            false);
  
  if (ret && metadata.find("TransferSyntax") != metadata.end())
  {
    transferSyntaxMetadata = metadata["TransferSyntax"];
  }
  
  return ret;
}

bool LocateOneInstance(OrthancPluginRestOutput* output,
                       std::string& instanceOrthancId,
                       std::string& studyInstanceUid,
                       std::string& seriesInstanceUid,
                       std::string& transferSyntaxMetadata,
                       const OrthancPluginHttpRequest* request)
{
  std::string sopInstanceUid;
  std::map<std::string, std::string> metadata;

  studyInstanceUid = request->groups[0];

  if (request->groupsCount > 1)
  {
    seriesInstanceUid = request->groups[1];
  }

  bool ret = LocateResource(output,
                            instanceOrthancId,
                            metadata,
                            studyInstanceUid,
                            seriesInstanceUid,
                            sopInstanceUid,
                            "Instance",
                            request,
                            true);
  
  if (ret && metadata.find("TransferSyntax") != metadata.end())
  {
    transferSyntaxMetadata = metadata["TransferSyntax"];
  }
  
  return ret;
}

void RetrieveDicomStudy(OrthancPluginRestOutput* output,
                        const char* url,
                        const OrthancPluginHttpRequest* request)
{
  bool transcode;
  Orthanc::DicomTransferSyntax targetSyntax;

  AcceptMultipartDicom(transcode, targetSyntax, request);
  
  std::string orthancId, studyInstanceUid;
  if (LocateStudy(output, orthancId, studyInstanceUid, request))
  {
    AnswerListOfDicomInstances(output, Orthanc::ResourceType_Study, orthancId, transcode, targetSyntax);
  }
}


void RetrieveDicomSeries(OrthancPluginRestOutput* output,
                         const char* url,
                         const OrthancPluginHttpRequest* request)
{
  bool transcode;
  Orthanc::DicomTransferSyntax targetSyntax;
  
  AcceptMultipartDicom(transcode, targetSyntax, request);
  
  std::string orthancId, studyInstanceUid, seriesInstanceUid;
  if (LocateSeries(output, orthancId, studyInstanceUid, seriesInstanceUid, request))
  {
    AnswerListOfDicomInstances(output, Orthanc::ResourceType_Series, orthancId, transcode, targetSyntax);
  }
}



void RetrieveDicomInstance(OrthancPluginRestOutput* output,
                           const char* url,
                           const OrthancPluginHttpRequest* request)
{
  bool transcode;
  std::string transferSyntax;
  Orthanc::DicomTransferSyntax targetSyntax;
  
  AcceptMultipartDicom(transcode, targetSyntax, request);
  
  std::string orthancId, studyInstanceUid, seriesInstanceUid, sopInstanceUid;
  if (LocateInstance(output, orthancId, studyInstanceUid, seriesInstanceUid, sopInstanceUid, transferSyntax, request))
  {
    AnswerListOfDicomInstances(output, Orthanc::ResourceType_Instance, orthancId, transcode, targetSyntax);
  }
}


static void GetChildrenIdentifiers(std::set<std::string>& target,
                                   std::string& resourceDicomUid,
                                   Orthanc::ResourceType level,
                                   const std::string& orthancId)
{
  target.clear();

  const char* childrenTag = NULL;
  const char* dicomUidTag = NULL;
  std::string uri;

  switch (level)
  {
    case Orthanc::ResourceType_Study:
      uri = "/studies/" + orthancId;
      childrenTag = "Series";
      dicomUidTag = "StudyInstanceUID";
      break;
       
    case Orthanc::ResourceType_Series:
      uri = "/series/" + orthancId;
      childrenTag = "Instances";
      dicomUidTag = "SeriesInstanceUID";
      break;

    default:
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
  }

  assert(childrenTag != NULL && dicomUidTag != NULL);
  
  Json::Value resource;
  if (OrthancPlugins::RestApiGet(resource, uri, false))
  {
    if (resource.type() != Json::objectValue || !resource.isMember(childrenTag) 
      || !resource.isMember(MAIN_DICOM_TAGS) || !resource[MAIN_DICOM_TAGS].isMember(dicomUidTag))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_NetworkProtocol);
    }

    const Json::Value& children = resource[childrenTag];
    resourceDicomUid = resource[MAIN_DICOM_TAGS][dicomUidTag].asString();

    for (Json::Value::ArrayIndex i = 0; i < children.size(); i++)
    {
      target.insert(children[i].asString());
    }
  }  
}


typedef std::map<std::string, boost::shared_ptr<Orthanc::DicomMap> >  ChildrenMainDicomMaps;

static void GetChildrenMainDicomTags(ChildrenMainDicomMaps& childrenDicomMaps,
                                     std::string& resourceDicomUid,
                                     Orthanc::ResourceType level,
                                     const std::string& orthancId)
{
  childrenDicomMaps.clear();

  const char* childrenRoute = NULL;
  const char* dicomUidTag = NULL;
  std::string uri;

  switch (level)
  {
    case Orthanc::ResourceType_Study:
      uri = "/studies/" + orthancId;
      childrenRoute = "series";
      dicomUidTag = "StudyInstanceUID";
      break;
       
    case Orthanc::ResourceType_Series:
      uri = "/series/" + orthancId;
      childrenRoute = "instances";
      dicomUidTag = "SeriesInstanceUID";
      break;

    default:
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
  }

  assert(childrenRoute != NULL && dicomUidTag != NULL);
  
  // get the resource itself
  Json::Value resource;
  if (OrthancPlugins::RestApiGet(resource, uri, false))
  {
    if (resource.type() != Json::objectValue 
      || !resource.isMember(MAIN_DICOM_TAGS) || !resource[MAIN_DICOM_TAGS].isMember(dicomUidTag))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_NetworkProtocol);
    }

    resourceDicomUid = resource[MAIN_DICOM_TAGS][dicomUidTag].asString();

    // get the children resources
    Json::Value childResources;
    if (OrthancPlugins::RestApiGet(childResources, uri + "/" + childrenRoute + "?expand&full", false))
    {
      for (Json::Value::ArrayIndex i = 0; i < childResources.size(); i++)
      {
        const Json::Value& child = childResources[i];
        Orthanc::DicomMap dicom;
        dicom.FromDicomAsJson(child[MAIN_DICOM_TAGS], false /* append */, true /* parseSequences */);
        childrenDicomMaps[child["ID"].asString()] = boost::shared_ptr<Orthanc::DicomMap>(dicom.Clone());
      }

    }

  }  
}


static const char* EXIT_WORKER_MESSAGE = "exit";

class InstanceToLoad : public Orthanc::IDynamicObject
{
private:
  std::string                  orthancId_;
  std::string                  studyInstanceUid_;
  std::string                  seriesInstanceUid_;
  std::string                  bulkRoot_;
  boost::mutex&                writerMutex_;
  OrthancPlugins::DicomWebFormatter::HttpWriter& writer_;

public:
  InstanceToLoad(const std::string& orthancId,
                 const std::string& bulkRoot,
                 boost::mutex& writerMutex,
                 OrthancPlugins::DicomWebFormatter::HttpWriter& writer,
                 const std::string& studyInstanceUid,
                 const std::string& seriesInstanceUid):
    orthancId_(orthancId),
    studyInstanceUid_(studyInstanceUid),
    seriesInstanceUid_(seriesInstanceUid),
    bulkRoot_(bulkRoot),
    writerMutex_(writerMutex),
    writer_(writer)
  {
  }

  const std::string& GetStudyInstanceUid() const
  {
    return studyInstanceUid_;
  }

  const std::string& GetSeriesInstanceUid() const
  {
    return seriesInstanceUid_;
  }

  const std::string& GetOrthancId() const
  {
    return orthancId_;
  }

  const std::string& GetBulkRoot() const
  {
    return bulkRoot_;
  }

  void SetBulkRoot(const std::string& root)
  {
    bulkRoot_ = root;
  }

  void AddInstance(const OrthancPlugins::DicomInstance& instance)
  {
    boost::mutex::scoped_lock lock(writerMutex_);
    writer_.AddInstance(instance, bulkRoot_);
  }
};


class InstanceWorkerData : public boost::noncopyable
{
private:
  Orthanc::SharedMessageQueue* instancesQueue_;
  std::string wadoBase_;

public:
  InstanceWorkerData(Orthanc::SharedMessageQueue* instancesQueue,
                     const std::string& wadoBase) :
    instancesQueue_(instancesQueue),
    wadoBase_(wadoBase)
  {
    if (instancesQueue == NULL)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_NullPointer);
    }
  }

  InstanceToLoad* Dequeue()
  {
    return dynamic_cast<InstanceToLoad*>(instancesQueue_->Dequeue(0));
  }

  const std::string& GetWadoBase() const
  {
    return wadoBase_;
  }
};

void InstanceWorkerThread(InstanceWorkerData* data)
{
  while (true)
  {
    try
    {
      std::unique_ptr<InstanceToLoad> instanceToLoad(data->Dequeue());
      if (instanceToLoad.get() == NULL)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
      }

      if (instanceToLoad->GetOrthancId() == EXIT_WORKER_MESSAGE)
      {
        return;
      }

      if (instanceToLoad->GetBulkRoot().empty()) // we are not in oneLargeQuery mode -> we must load the instance tags to get the SOPInstanceUID
      {
        Json::Value instanceResource;

        if (OrthancPlugins::RestApiGet(instanceResource, "/instances/" + instanceToLoad->GetOrthancId(), false))
        {
          instanceToLoad->SetBulkRoot((data->GetWadoBase() +
                                       "studies/" + instanceToLoad->GetStudyInstanceUid() +
                                       "/series/" + instanceToLoad->GetSeriesInstanceUid() +
                                       "/instances/" + instanceResource[MAIN_DICOM_TAGS]["SOPInstanceUID"].asString() + "/bulk"));
        }
      }

      std::unique_ptr<OrthancPlugins::DicomInstance> instance;

      try
      {
        instance.reset(OrthancPlugins::DicomInstance::Load(instanceToLoad->GetOrthancId(), OrthancPluginLoadDicomInstanceMode_EmptyPixelData));
      }
      catch (Orthanc::OrthancException& e)
      {
      }

      if (instance.get() != NULL)
      {
        instanceToLoad->AddInstance(*instance);
      }
    }
    catch(...)
    {
      // ignore errors but don't exit the thread to make sure all workers end correctly
    }
  }
}

void RetrieveSeriesMetadataInternal(std::set<std::string>& instancesIds,
                                    OrthancPlugins::DicomWebFormatter::HttpWriter& writer,
                                    MainDicomTagsCache& cache,
                                    const OrthancPlugins::MetadataMode& mode,
                                    bool isXml,
                                    const std::string& seriesOrthancId,
                                    const std::string& studyInstanceUid,
                                    const std::string& seriesInstanceUid,
                                    const std::string& wadoBase)
{
  const unsigned int workersCount =  OrthancPlugins::Configuration::GetMetadataWorkerThreadsCount();

  if (workersCount > 1 && mode == OrthancPlugins::MetadataMode_Full)
  {
    ChildrenMainDicomMaps instancesDicomMaps;
    std::string seriesDicomUid;

    if (CanUseExtendedFind()) // in this case, /series/.../instances?full has been optimized to minimize the SQL queries
    {
      GetChildrenMainDicomTags(instancesDicomMaps, seriesDicomUid, Orthanc::ResourceType_Series, seriesOrthancId);
      for (ChildrenMainDicomMaps::const_iterator it = instancesDicomMaps.begin(); it != instancesDicomMaps.end(); ++it)
      {
        instancesIds.insert(it->first);
      }
    }
    else
    {
      GetChildrenIdentifiers(instancesIds, seriesDicomUid, Orthanc::ResourceType_Series, seriesOrthancId);
    }

    // span a few workers to get the tags from the core and serialize them
    Orthanc::SharedMessageQueue instancesQueue;
    std::vector<boost::shared_ptr<boost::thread> > instancesWorkers;
    boost::mutex writerMutex;
    std::vector<boost::shared_ptr<InstanceWorkerData> > instancesWorkersData;

    for (unsigned int t = 0; t < workersCount; t++)
    {
      InstanceWorkerData* threadData = new InstanceWorkerData(&instancesQueue, wadoBase);
      instancesWorkersData.push_back(boost::shared_ptr<InstanceWorkerData>(threadData));
      instancesWorkers.push_back(boost::shared_ptr<boost::thread>(new boost::thread(InstanceWorkerThread, threadData)));
    }

    if (CanUseExtendedFind())  // we must correct the bulkRoot
    {
      for (ChildrenMainDicomMaps::const_iterator i = instancesDicomMaps.begin(); i != instancesDicomMaps.end(); ++i)
      {
        std::string bulkRoot = (wadoBase +
                                "studies/" + studyInstanceUid +
                                "/series/" + seriesInstanceUid + 
                                "/instances/" + i->second->GetStringValue(Orthanc::DICOM_TAG_SOP_INSTANCE_UID, "", false) + "/bulk");

        instancesQueue.Enqueue(new InstanceToLoad(i->first, bulkRoot, writerMutex, writer, studyInstanceUid, seriesInstanceUid));
      }
    }
    else
    {
      for (std::set<std::string>::const_iterator i = instancesIds.begin(); i != instancesIds.end(); ++i)
      {
        instancesQueue.Enqueue(new InstanceToLoad(*i, "", writerMutex, writer, studyInstanceUid, seriesInstanceUid));
      }
    }

    // send a dummy "exit" message to all workers such that they stop waiting for messages on the queue
    for (size_t i = 0; i < instancesWorkers.size(); i++)
    {
      instancesQueue.Enqueue(new InstanceToLoad(EXIT_WORKER_MESSAGE, "", writerMutex, writer, studyInstanceUid, seriesInstanceUid));
    }

    for (size_t i = 0; i < instancesWorkers.size(); i++)
    {
      if (instancesWorkers[i]->joinable())
      {
        instancesWorkers[i]->join();
      }
    }

    instancesWorkers.clear();
  }
  else
  {
    // old single threaded code
    std::set<std::string> instances;
    std::string seriesDicomUid;  // not used

    GetChildrenIdentifiers(instances, seriesDicomUid, Orthanc::ResourceType_Series, seriesOrthancId);

    for (std::set<std::string>::const_iterator i = instances.begin(); i != instances.end(); ++i)
    {
      WriteInstanceMetadata(writer, mode, cache, *i, studyInstanceUid, seriesInstanceUid, wadoBase);
    }
  }
}

void CacheSeriesMetadataInternal(std::string& serializedSeriesMetadata,
                                 OrthancPlugins::DicomWebFormatter::HttpWriter& writer,
                                 MainDicomTagsCache& cache,
                                 const std::string& studyInstanceUid, 
                                 const std::string& seriesInstanceUid, 
                                 const std::string& seriesOrthancId)
{
  Orthanc::GzipCompressor compressor;
  std::string compressedSeriesMetadata;
  std::set<std::string> instancesIds;

  // compute the series metadata with a placeholder WADO base url because, the base url might change (e.g if there are 2 Orthanc connected to the same DB)
  RetrieveSeriesMetadataInternal(instancesIds, writer, cache, OrthancPlugins::MetadataMode_Full, false /* isXml */, seriesOrthancId, studyInstanceUid, seriesInstanceUid, WADO_BASE_PLACEHOLDER);
  writer.CloseAndGetJsonOutput(serializedSeriesMetadata);

  if (!IsSystemReadOnly())
  {
    // save in attachments for future use
    Orthanc::IBufferCompressor::Compress(compressedSeriesMetadata, compressor, serializedSeriesMetadata);
    std::string instancesMd5;
    Orthanc::Toolbox::ComputeMD5(instancesMd5, instancesIds);

    std::string cacheContent = "2;" + instancesMd5 + ";" + compressedSeriesMetadata; 

    Json::Value putResult;
    std::string attachmentUrl = "/series/" + seriesOrthancId + "/attachments/" + SERIES_METADATA_ATTACHMENT_ID;

    OrthancPlugins::RestApiClient client;
    client.SetMethod(OrthancPluginHttpMethod_Get);
    client.SetPath(attachmentUrl);

    std::string etag;
    bool hasRevision = (client.Execute() &&
                        client.LookupAnswerHeader(etag, "etag"));

    client.SetMethod(OrthancPluginHttpMethod_Put);
    client.SwapRequestBody(cacheContent);

    if (hasRevision)
    {
      client.AddRequestHeader("If-Match", etag);
    }

    if (!client.Execute())
    {
      LOG(WARNING) << "DicomWEB: failed to write series metadata attachment";
    }
  }
}

void CacheSeriesMetadata(const std::string& seriesOrthancId)
{
  if (!OrthancPlugins::Configuration::IsMetadataCacheEnabled())
  {
    return;
  }

  LOG(INFO) << "DicomWEB: pre-computing the WADO-RS series metadata for series " << seriesOrthancId;

  std::string studyInstanceUid, seriesInstanceUid;
  
  Json::Value result;
  if (OrthancPlugins::RestApiGet(result, "/series/" + seriesOrthancId, false))
  {
    seriesInstanceUid = result[MAIN_DICOM_TAGS]["SeriesInstanceUID"].asString();
    if (OrthancPlugins::RestApiGet(result, "/studies/" + result["ParentStudy"].asString(), false))
    {
      studyInstanceUid = result[MAIN_DICOM_TAGS]["StudyInstanceUID"].asString();

      MainDicomTagsCache cache;
      OrthancPlugins::DicomWebFormatter::HttpWriter writer(NULL /* output */, false /* isXml */);  // we cache only the JSON format -> no need for an HttpOutput

      std::string serializedSeriesMetadataNotUsed;
      CacheSeriesMetadataInternal(serializedSeriesMetadataNotUsed, writer, cache, studyInstanceUid, seriesInstanceUid, seriesOrthancId);
    }
  }
}

void UpdateSeriesMetadataCache(OrthancPluginRestOutput* output,
                               const char* /*url*/,
                               const OrthancPluginHttpRequest* request)
{
  if (request->method != OrthancPluginHttpMethod_Post)
  {
    OrthancPluginSendMethodNotAllowed(OrthancPlugins::GetGlobalContext(), output, "POST");
    return;
  }

  if (request->groupsCount != 1)
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_BadRequest);
  }

  if (!OrthancPlugins::Configuration::IsMetadataCacheEnabled())
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_BadRequest, "The metadata cache is disabled in the Orthanc configuration.");
  }

  std::string studyId(request->groups[0]);

  LOG(INFO) << "DicomWEB: updating the series metadata cache for study " << studyId;

  Json::Value study;

  if (OrthancPlugins::RestApiGet(study, "/studies/" + studyId, false) && study.type() == Json::objectValue)
  {
    for (Json::ArrayIndex i = 0; i < study["Series"].size(); ++i)
    {
      CacheSeriesMetadata(study["Series"][i].asString());
    }
  }

  std::string answer = "{}"; 
  OrthancPluginAnswerBuffer(OrthancPlugins::GetGlobalContext(), output, answer.c_str(), answer.size(), "application/json");
}



void RetrieveSeriesMetadataInternalWithCache(OrthancPlugins::DicomWebFormatter::HttpWriter& writer,
                                             MainDicomTagsCache& cache,
                                             const OrthancPlugins::MetadataMode& mode,
                                             bool isXml,
                                             const std::string& seriesOrthancId,
                                             const std::string& studyInstanceUid,
                                             const std::string& seriesInstanceUid,
                                             const std::string& wadoBase)
{
  if (OrthancPlugins::Configuration::IsMetadataCacheEnabled() &&
      mode == OrthancPlugins::MetadataMode_Full && 
      !isXml)
  {
    // check if we already have computed the series metadata and saved them in an attachment
    std::string serializedSeriesMetadata;
    std::string cacheContent;
    bool hasBeenReadFromCache = false;
    Orthanc::GzipCompressor compressor;

    std::string attachmentUrl = "/series/" + seriesOrthancId + "/attachments/" + SERIES_METADATA_ATTACHMENT_ID;

    if (OrthancPlugins::RestApiGetString(cacheContent, attachmentUrl + "/data", false))
    {
      if (boost::starts_with(cacheContent, "2;"))  // version 2, cacheContent is "2;sorted-instances-list-md5;compressedSeriesMetadata"
      {
        // check that the instances count have not changed since we have saved the data in cache 
        // StableSeries event will always overwrite it but this is usefull if retrieving the metadata while
        // the instances are being received
        // Note: we can not use Toolbox::SplitString because the compressed metadata contain a lot of ";"
        const char* secondSemiColon = strchr(&cacheContent[2], ';');
        std::string instancesMd5InCache(&cacheContent[2], secondSemiColon - &cacheContent[2]);
        std::string compressedSeriesMetadata(secondSemiColon + 1, cacheContent.size() - (secondSemiColon+1 - cacheContent.c_str()));
        
        Json::Value seriesInfo;

        if (!OrthancPlugins::RestApiGet(seriesInfo, "/series/" + seriesOrthancId, false))
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_UnknownResource);
        }
        std::set<std::string> currentInstancesIds;
        Orthanc::SerializationToolbox::ReadSetOfStrings(currentInstancesIds, seriesInfo, "Instances");
        std::string currentInstancesMd5;
        Orthanc::Toolbox::ComputeMD5(currentInstancesMd5, currentInstancesIds);

        if (currentInstancesMd5 == instancesMd5InCache)
        {
          Orthanc::IBufferCompressor::Uncompress(serializedSeriesMetadata, compressor, compressedSeriesMetadata);

          hasBeenReadFromCache = true;
        }
      }
    }

    if (!hasBeenReadFromCache)  // regenerate and overwrite current cache
    {
      MainDicomTagsCache tmpCache;
      OrthancPlugins::DicomWebFormatter::HttpWriter tmpWriter(NULL /* output */, false /* isXml */);  // we cache only the JSON format -> no need for an HttpOutput

      CacheSeriesMetadataInternal(serializedSeriesMetadata, tmpWriter, tmpCache, studyInstanceUid, seriesInstanceUid, seriesOrthancId);
    }

    boost::replace_all(serializedSeriesMetadata, WADO_BASE_PLACEHOLDER, wadoBase);

    writer.AddDicomWebSeriesSerializedJson(serializedSeriesMetadata.c_str(), serializedSeriesMetadata.size());
  }
  else
  {
    std::set<std::string> instancesIdsNotUsed;
    RetrieveSeriesMetadataInternal(instancesIdsNotUsed, writer, cache, mode, isXml, seriesOrthancId, studyInstanceUid, seriesInstanceUid, wadoBase);
  }

}


void RetrieveSeriesMetadata(OrthancPluginRestOutput* output,
                            const char* /*url*/,
                            const OrthancPluginHttpRequest* request)
{
  bool isXml;
  AcceptMetadata(request, isXml);

  const OrthancPlugins::MetadataMode mode =
    OrthancPlugins::Configuration::GetMetadataMode(Orthanc::ResourceType_Series);
    
  MainDicomTagsCache cache;
  OrthancPlugins::DicomWebFormatter::HttpWriter writer(output, isXml);

  std::string seriesOrthancId, studyInstanceUid, seriesInstanceUid;

  if (LocateSeries(output, seriesOrthancId, studyInstanceUid, seriesInstanceUid, request))
  {
    std::string wadoBase = OrthancPlugins::Configuration::GetBasePublicUrl(request);
    RetrieveSeriesMetadataInternalWithCache(writer, cache, mode, isXml, seriesOrthancId, studyInstanceUid, seriesInstanceUid, wadoBase);
  }

  writer.Send();
}


void RetrieveStudyMetadata(OrthancPluginRestOutput* output,
                           const char* url,
                           const OrthancPluginHttpRequest* request)
{
  bool isXml;
  AcceptMetadata(request, isXml);

  const OrthancPlugins::MetadataMode mode =
    OrthancPlugins::Configuration::GetMetadataMode(Orthanc::ResourceType_Study);

  MainDicomTagsCache cache;

  std::string studyOrthancId, studyInstanceUid;
  if (LocateStudy(output, studyOrthancId, studyInstanceUid, request))
  {
    OrthancPlugins::DicomWebFormatter::HttpWriter writer(output, isXml);

    std::string wadoBase = OrthancPlugins::Configuration::GetBasePublicUrl(request);
    
    std::set<std::string> series;
    std::string studyDicomUid;
    GetChildrenIdentifiers(series, studyDicomUid, Orthanc::ResourceType_Study, studyOrthancId);

    for (std::set<std::string>::const_iterator s = series.begin(); s != series.end(); ++s)
    {
      std::set<std::string> instances;
      std::string seriesDicomUid;
      GetChildrenIdentifiers(instances, seriesDicomUid, Orthanc::ResourceType_Series, *s);

      RetrieveSeriesMetadataInternalWithCache(writer, cache, mode, isXml, *s, studyDicomUid, seriesDicomUid, wadoBase);
    }

    writer.Send();
  }
}


void RetrieveInstanceMetadata(OrthancPluginRestOutput* output,
                              const char* url,
                              const OrthancPluginHttpRequest* request)
{
  bool isXml;
  std::string transferSyntax;

  AcceptMetadata(request, isXml);

  MainDicomTagsCache cache;

  std::string orthancId, studyInstanceUid, seriesInstanceUid, sopInstanceUid;
  if (LocateInstance(output, orthancId, studyInstanceUid, seriesInstanceUid, sopInstanceUid, transferSyntax, request))
  {
    OrthancPlugins::DicomWebFormatter::HttpWriter writer(output, isXml);
    WriteInstanceMetadata(writer, OrthancPlugins::MetadataMode_Full, cache, orthancId, studyInstanceUid,
                          seriesInstanceUid, OrthancPlugins::Configuration::GetBasePublicUrl(request));
    writer.Send();
  }
}


void RetrieveBulkData(OrthancPluginRestOutput* output,
                      const char* url,
                      const OrthancPluginHttpRequest* request)
{
  OrthancPluginContext* context = OrthancPlugins::GetGlobalContext();
  std::string transferSyntax;

  AcceptBulkData(request);

  std::string orthancId, studyInstanceUid, seriesInstanceUid, sopInstanceUid;
  OrthancPlugins::MemoryBuffer content;
  if (LocateInstance(output, orthancId, studyInstanceUid, seriesInstanceUid, sopInstanceUid, transferSyntax, request) &&
      content.RestApiGet("/instances/" + orthancId + "/file", false))
  {
    std::string bulk(request->groups[3]);

    std::vector<std::string> path;
    Orthanc::Toolbox::TokenizeString(path, bulk, '/');

    // Map the bulk data URI to the Orthanc "/instances/.../content/..." built-in URI
    std::string orthanc = "/instances/" + orthancId + "/content";

    Orthanc::DicomTag tmp(0, 0);
    
    if (path.size() == 1 &&
        Orthanc::DicomTag::ParseHexadecimal(tmp, path[0].c_str()) &&
        tmp == Orthanc::DICOM_TAG_PIXEL_DATA)
    {
      // Accessing pixel data: Return the raw content of the fragments in a multipart stream.
      // TODO - Is this how DICOMweb should work?
      orthanc += "/" + Orthanc::DICOM_TAG_PIXEL_DATA.Format();

      Json::Value frames;
      if (OrthancPlugins::RestApiGet(frames, orthanc, false))
      {
        if (frames.type() != Json::arrayValue ||
            OrthancPluginStartMultipartAnswer(context, output, "related", "application/octet-stream") != 0)
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_Plugin);
        }

        for (Json::Value::ArrayIndex i = 0; i < frames.size(); i++)
        {
          std::string frame;
          
          if (frames[i].type() != Json::stringValue ||
              !OrthancPlugins::RestApiGetString(frame, orthanc + "/" + frames[i].asString(), false) ||
              OrthancPluginSendMultipartItem(context, output, frame.c_str(), frame.size()) != 0)
          {
            throw Orthanc::OrthancException(Orthanc::ErrorCode_Plugin);
          }
        }
      }
      else
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InexistentItem);
      }      
    }
    else
    {
      if (path.size() % 2 != 1)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_BadRequest,
                                        "Bulk data URI in WADO-RS should have an odd number of items: " + bulk);
      }

      for (size_t i = 0; i < path.size() / 2; i++)
      {
        int index;

        try
        {
          index = boost::lexical_cast<int>(path[2 * i + 1]);
        }
        catch (boost::bad_lexical_cast&)
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_BadRequest,
                                          "Bad sequence index in bulk data URI: " + bulk);
        }

        orthanc += "/" + path[2 * i] + "/" + boost::lexical_cast<std::string>(index - 1);
      }

      orthanc += "/" + path.back();

      std::string result; 
      if (OrthancPlugins::RestApiGetString(result, orthanc, false))
      {
        if (OrthancPluginStartMultipartAnswer(context, output, "related", "application/octet-stream") != 0 ||
            OrthancPluginSendMultipartItem(context, output, result.c_str(), result.size()) != 0)
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_Plugin);
        }
      }
      else
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InexistentItem);
      }
    }
  }
}
