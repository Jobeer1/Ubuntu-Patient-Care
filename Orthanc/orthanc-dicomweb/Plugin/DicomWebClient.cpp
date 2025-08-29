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


#include "DicomWebClient.h"

#include "../Resources/Orthanc/Plugins/OrthancPluginCppWrapper.h"
#include "DicomWebServers.h"

#include <ChunkedBuffer.h>
#include <Compatibility.h>
#include <HttpServer/MultipartStreamReader.h>
#include <Logging.h>
#include <Toolbox.h>

#include <list>
#include <set>
#include <boost/lexical_cast.hpp>


#include <boost/thread.hpp>
#include <boost/algorithm/string/predicate.hpp>


static const std::string HAS_WADO_RS_UNIVERSAL_TRANSFER_SYNTAX = "HasWadoRsUniversalTransferSyntax";
        

class SingleFunctionJob : public OrthancPlugins::OrthancJob
{
public:
  class JobContext : public boost::noncopyable
  {
  private:
    SingleFunctionJob&  that_;

  public:
    explicit JobContext(SingleFunctionJob& that) :
      that_(that)
    {
    }

    void SetContent(const std::string& key,
                    const Json::Value& value)
    {
      that_.SetContent(key, value);
    }

    void SetProgress(unsigned int position,
                     unsigned int maxPosition)
    {
      boost::mutex::scoped_lock lock(that_.mutex_);

      if (maxPosition == 0 || 
          position > maxPosition)
      {
        that_.UpdateProgress(1);
      }
      else
      {
        that_.UpdateProgress(static_cast<float>(position) / static_cast<float>(maxPosition));
      }
    }
  };


  class IFunction : public boost::noncopyable
  {
  public:
    virtual ~IFunction()
    {
    }

    virtual void Execute(JobContext& context) = 0;
  };


  class IFunctionFactory : public boost::noncopyable
  {
  public:
    virtual ~IFunctionFactory()
    {
    }

    // Called when the job is paused or canceled. WARNING:
    // "CancelFunction()" will be invoked while "Execute()" is
    // running. Mutex is probably necessary.
    virtual void CancelFunction() = 0;

    virtual void PauseFunction() = 0;

    virtual IFunction* CreateFunction() = 0;
  };


protected:
  void SetFactory(IFunctionFactory& factory)
  {
    boost::mutex::scoped_lock lock(mutex_);

    if (factory_ != NULL)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
    }
    else
    {
      factory_ = &factory;
    }
  }
  

private:
  enum FunctionResult
  {
    FunctionResult_Running,
    FunctionResult_Done,
    FunctionResult_Failure
  };

  boost::mutex                  mutex_;
  FunctionResult                functionResult_;  // Can only be modified by the "Worker()" function
  std::unique_ptr<boost::thread>  worker_;
  Json::Value                   content_;
  IFunctionFactory*             factory_;
  bool                          stopping_;

  void JoinWorker()
  {
    assert(factory_ != NULL);

    if (worker_.get() != NULL)
    {
      if (worker_->joinable())
      {
        worker_->join();
      }

      worker_.reset();
    }
  }

  void StartWorker()
  {
    assert(factory_ != NULL);

    if (worker_.get() == NULL)
    {
      stopping_ = false;
      worker_.reset(new boost::thread(Worker, this, factory_));
    }
  }

  // void SetContent(const std::string& key,
  //                 const std::string& value)
  // {
  //   boost::mutex::scoped_lock lock(mutex_);
  //   content_[key] = value;
  //   UpdateContent(content_);
  // }

  void SetContent(const std::string& key,
                  const Json::Value& value)
  {
    boost::mutex::scoped_lock lock(mutex_);
    content_[key] = value;
    UpdateContent(content_);
  }

  static void Worker(SingleFunctionJob* job,
                     IFunctionFactory* factory)
  {
    assert(job != NULL && factory != NULL);

    try
    {
      JobContext context(*job);

      std::unique_ptr<IFunction> function(factory->CreateFunction());
      function->Execute(context);

      {
        boost::mutex::scoped_lock lock(job->mutex_);
        job->functionResult_ = FunctionResult_Done;
      }
    }
    catch (Orthanc::OrthancException& e)
    {
      LOG(ERROR) << "Error in a job: " << e.What();

      {
        boost::mutex::scoped_lock lock(job->mutex_);

        job->functionResult_ = FunctionResult_Failure;

        if (!job->stopping_)
        {
          // Don't report exceptions that are a consequence of stopping the function
          job->content_["FunctionErrorCode"] = e.GetErrorCode();
          job->content_["FunctionErrorDescription"] = e.What();
          if (e.HasDetails())
          {
            job->content_["FunctionErrorDetails"] = e.GetDetails();
          }
          job->UpdateContent(job->content_);
        }
      }
    }
  }  

public:
  explicit SingleFunctionJob(const std::string& jobName) :
    OrthancJob(jobName),
    functionResult_(FunctionResult_Running),
    content_(Json::objectValue),
    factory_(NULL),
    stopping_(false)
  {
  }

  virtual ~SingleFunctionJob()
  {
    if (worker_.get() != NULL)
    {
      LOG(ERROR) << "Classes deriving from SingleFunctionJob must "
                 << "explicitly call Finalize() in their destructor";
      Finalize();
    }
  }

  void Finalize()
  {
    try
    {
      Stop(OrthancPluginJobStopReason_Canceled);
    }
    catch (Orthanc::OrthancException&)
    {
    }
  }

  virtual OrthancPluginJobStepStatus Step() ORTHANC_OVERRIDE
  {
    if (factory_ == NULL)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
    }

    FunctionResult result;

    {
      boost::mutex::scoped_lock lock(mutex_);
      result = functionResult_;
    }

    switch (result)
    {
      case FunctionResult_Running:
        StartWorker();
        boost::this_thread::sleep(boost::posix_time::milliseconds(500));
        return OrthancPluginJobStepStatus_Continue;

      case FunctionResult_Done:
        JoinWorker();
        return OrthancPluginJobStepStatus_Success;

      case FunctionResult_Failure:
        JoinWorker();
        return OrthancPluginJobStepStatus_Failure;

      default:
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
    }
  }

  virtual void Stop(OrthancPluginJobStopReason reason) ORTHANC_OVERRIDE
  {
    if (factory_ == NULL)
    {
      return;
    }
    else if (reason == OrthancPluginJobStopReason_Paused ||
             reason == OrthancPluginJobStopReason_Canceled)
    {
      stopping_ = true;

      if (reason == OrthancPluginJobStopReason_Paused)
      {
        factory_->PauseFunction();
      }
      else
      {
        factory_->CancelFunction();
      }

      JoinWorker();

      // Be ready for the next possible call to "Step()" that will resume the function
      functionResult_ = FunctionResult_Running;
    }
  }

  virtual void Reset() ORTHANC_OVERRIDE
  {
    boost::mutex::scoped_lock lock(mutex_);

    assert(worker_.get() == NULL);
    functionResult_ = FunctionResult_Running;
    content_ = Json::objectValue;
    ClearContent();
  }
};




static const std::string MULTIPART_RELATED = "multipart/related";



static void SubmitJob(OrthancPluginRestOutput* output,
                      OrthancPlugins::OrthancJob* job,
                      const Json::Value& body,
                      bool defaultSynchronous)
{
  std::unique_ptr<OrthancPlugins::OrthancJob> protection(job);

  bool synchronous;

  bool b;
  if (OrthancPlugins::LookupBooleanValue(b, body, "Synchronous"))
  {
    synchronous = b;
  }
  else if (OrthancPlugins::LookupBooleanValue(b, body, "Asynchronous"))
  {
    synchronous = !b;
  }
  else
  {
    synchronous = defaultSynchronous;
  }

  int priority;
  if (!OrthancPlugins::LookupIntegerValue(priority, body, "Priority"))
  {
    priority = 0;
  }

  Json::Value answer;

  if (synchronous)
  {
    OrthancPlugins::OrthancJob::SubmitAndWait(answer, protection.release(), priority);
  }
  else
  {
    std::string jobId = OrthancPlugins::OrthancJob::Submit(protection.release(), priority);

    answer = Json::objectValue;
    answer["ID"] = jobId;
    answer["Path"] = OrthancPlugins::RemoveMultipleSlashes
      ("../" + OrthancPlugins::Configuration::GetOrthancApiRoot() + "/jobs/" + jobId);
  }

  std::string s = answer.toStyledString();
  OrthancPluginAnswerBuffer(OrthancPlugins::GetGlobalContext(),
                            output, s.c_str(), s.size(), "application/json");    
}


static void AddInstance(std::list<std::string>& target,
                        const Json::Value& instance)
{
  std::string id;
  if (OrthancPlugins::LookupStringValue(id, instance, "ID"))
  {
    target.push_back(id);
  }
  else
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
  }
}


static bool GetSequenceSize(size_t& result,
                            const Json::Value& answer,
                            const std::string& tag,
                            bool isMandatory,
                            const std::string& server)
{
  const Json::Value* value = NULL;

  std::string upper, lower;
  Orthanc::Toolbox::ToUpperCase(upper, tag);
  Orthanc::Toolbox::ToLowerCase(lower, tag);
  
  if (answer.isMember(upper))
  {
    value = &answer[upper];
  }
  else if (answer.isMember(lower))
  {
    value = &answer[lower];
  }
  else if (isMandatory)
  {
    throw Orthanc::OrthancException(
      Orthanc::ErrorCode_NetworkProtocol,
      "The STOW-RS JSON response from DICOMweb server " + server + 
      " does not contain the mandatory tag " + upper);
  }
  else
  {
    return false;
  }

  if (value->type() != Json::objectValue ||
      (value->isMember("Value") &&
       (*value) ["Value"].type() != Json::arrayValue))
  {
    throw Orthanc::OrthancException(
      Orthanc::ErrorCode_NetworkProtocol,
      "Unable to parse STOW-RS JSON response from DICOMweb server " + server);
  }

  if (value->isMember("Value"))
  {
    result = (*value) ["Value"].size();
  }
  else
  {
    result = 0;
  }

  return true;
}



static void CheckStowAnswer(const Json::Value& response,
                            const std::string& serverName,
                            size_t instancesCount)
{
  if (response.type() != Json::objectValue ||
      !response.isMember("00081199"))
  {
    throw Orthanc::OrthancException(
      Orthanc::ErrorCode_NetworkProtocol,
      "Unable to parse STOW-RS JSON response from DICOMweb server " + serverName);
  }

  size_t size;
  if (!GetSequenceSize(size, response, "00081199", true, serverName) ||
      size != instancesCount)
  {
    throw Orthanc::OrthancException(
      Orthanc::ErrorCode_NetworkProtocol,
      "The STOW-RS server was only able to receive " + 
      boost::lexical_cast<std::string>(size) + " instances out of " +
      boost::lexical_cast<std::string>(instancesCount));
  }

  if (GetSequenceSize(size, response, "00081198", false, serverName) &&
      size != 0)
  {
    throw Orthanc::OrthancException(
      Orthanc::ErrorCode_NetworkProtocol,
      "The response from the STOW-RS server contains " + 
      boost::lexical_cast<std::string>(size) + 
      " items in its Failed SOP Sequence (0008,1198) tag");
  }

  if (GetSequenceSize(size, response, "0008119A", false, serverName) &&
      size != 0)
  {
    throw Orthanc::OrthancException(
      Orthanc::ErrorCode_NetworkProtocol,
      "The response from the STOW-RS server contains " + 
      boost::lexical_cast<std::string>(size) + 
      " items in its Other Failures Sequence (0008,119A) tag");
  }
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


static void ParseStowRequest(std::list<std::string>& instances /* out */,
                             std::map<std::string, std::string>& httpHeaders /* out */,
                             Json::Value& resourcesForJobContent /* out */,
                             const Json::Value& body /* in */)
{
  static const char* RESOURCES = "Resources";
  static const char* HTTP_HEADERS = "HttpHeaders";

  if (body.type() != Json::objectValue ||
      !body.isMember(RESOURCES) ||
      body[RESOURCES].type() != Json::arrayValue)
  {
    throw Orthanc::OrthancException(
      Orthanc::ErrorCode_BadFileFormat,
      "A request to the DICOMweb STOW-RS client must provide a JSON object "
      "with the field \"" + std::string(RESOURCES) + 
      "\" containing an array of resources to be sent");
  }

  OrthancPlugins::ParseAssociativeArray(httpHeaders, body, HTTP_HEADERS);

  const Json::Value& resources = body[RESOURCES];

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
      // AddInstance(instances, tmpResource);
      instances.push_back(resource);
      AddResourceForJobContent(resourcesForJobContent, Orthanc::ResourceType_Instance, resource);
    }
    // This was not an instance, successively try with series/studies/patients
    else if ((OrthancPlugins::RestApiGet(tmpResource, "/series/" + resource, false) &&
              OrthancPlugins::RestApiGet(tmpInstances, "/series/" + resource + "/instances?expand=false", false)) ||
             (OrthancPlugins::RestApiGet(tmpResource, "/studies/" + resource, false) &&
              OrthancPlugins::RestApiGet(tmpInstances, "/studies/" + resource + "/instances?expand=false", false)) ||
             (OrthancPlugins::RestApiGet(tmpResource, "/patients/" + resource, false) &&
              OrthancPlugins::RestApiGet(tmpInstances, "/patients/" + resource + "/instances?expand=false", false)))
    {
      if (tmpInstances.type() != Json::arrayValue)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
      }

      AddResourceForJobContent(resourcesForJobContent, Orthanc::StringToResourceType(tmpResource["Type"].asString().c_str()), resource);

      for (Json::Value::ArrayIndex j = 0; j < tmpInstances.size(); j++)
      {
        // AddInstance(instances, tmpInstances[j]);
        instances.push_back(tmpInstances[j].asString());
        AddResourceForJobContent(resourcesForJobContent, Orthanc::ResourceType_Instance, tmpInstances[j].asString());
      }
    }
    else
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_UnknownResource);
    }   
  }
}


class StowClientJob :
  public SingleFunctionJob,
  private SingleFunctionJob::IFunctionFactory
{
private:
  enum Action
  {
    Action_None,
    Action_Pause,
    Action_Cancel
  };
  
  boost::mutex                 mutex_;
  std::string                  serverName_;
  std::vector<std::string>     instances_;
  OrthancPlugins::HttpHeaders  headers_;
  std::string                  boundary_;
  size_t                       position_;
  Action                       action_;
  size_t                       networkSize_;
  bool                         debug_;
  Json::Value                  resourcesForJobContent_;

  bool ReadNextInstance(std::string& dicom,
                        JobContext& context)
  {
    boost::mutex::scoped_lock lock(mutex_);

    if (action_ != Action_None)
    {
      return false;
    }

    while (position_ < instances_.size())
    {
      context.SetProgress(position_, instances_.size());
      
      size_t i = position_++;

      if (debug_)
      {
        boost::this_thread::sleep(boost::posix_time::milliseconds(100));
      }

      if (OrthancPlugins::RestApiGetString(dicom, "/instances/" + instances_[i] + "/file", false))
      {
        networkSize_ += dicom.size();
        context.SetContent("NetworkSizeMB", boost::lexical_cast<std::string>
                           (networkSize_ / static_cast<uint64_t>(1024 * 1024)));

        return true;
      }
    }

    return false;
  }


  class RequestBody : public OrthancPlugins::HttpClient::IRequestBody
  {
  private:
    StowClientJob&  that_;
    JobContext&     context_;
    std::string     boundary_;
    bool            done_;
    size_t          processedSize_;

  public:
    RequestBody(StowClientJob& that,
                JobContext& context) :
      that_(that),
      context_(context),
      boundary_(that.boundary_),
      done_(false),
      processedSize_(0)
    {
    }

    virtual bool ReadNextChunk(std::string& chunk) ORTHANC_OVERRIDE
    {
      if (done_)
      {
        context_.SetProgress(1, 1);
        return false;
      }
      else
      {
        std::string dicom;

        if (that_.ReadNextInstance(dicom, context_))
        {
          chunk = ("--" + boundary_ + "\r\n" +
                   "Content-Type: application/dicom\r\n" +
                   "Content-Length: " + boost::lexical_cast<std::string>(dicom.size()) + 
                   "\r\n\r\n" + dicom + "\r\n");
        }
        else
        {
          done_ = true;
          chunk = ("--" + boundary_ + "--");
        }

        //boost::this_thread::sleep(boost::posix_time::seconds(1));

        processedSize_ += chunk.size();
        
        return true;
      }
    }

    size_t GetProcessedSize() const
    {
      return processedSize_;
    }
  };


  class F : public IFunction
  {
  private:
    StowClientJob& that_;

  public:
    explicit F(StowClientJob& that) :
      that_(that)
    {
    }

    virtual void Execute(JobContext& context)
    {
      std::string serverName;
      size_t startPosition;

      // The lifetime of "body" should be larger than "client"
      std::unique_ptr<RequestBody> body;
      std::unique_ptr<OrthancPlugins::HttpClient> client;

      {
        boost::mutex::scoped_lock lock(that_.mutex_);
        context.SetContent("InstancesCount", boost::lexical_cast<std::string>(that_.instances_.size()));
        context.SetContent("Resources", that_.GetResourcesForJobContent());
        context.SetContent("Server", that_.GetServerName());
        serverName = that_.serverName_;
        
        startPosition = that_.position_;        
        body.reset(new RequestBody(that_, context));

        client.reset(new OrthancPlugins::HttpClient);
        std::map<std::string, std::string> userProperties;
        OrthancPlugins::DicomWebServers::GetInstance().ConfigureHttpClient(*client, userProperties, serverName, "/studies");
        client->SetMethod(OrthancPluginHttpMethod_Post);
        client->AddHeaders(that_.headers_);
      }

      OrthancPlugins::HttpHeaders answerHeaders;
      Json::Value answerBody;

      assert(client.get() != NULL);
      client->SetBody(*body);

      try
      {
        client->Execute(answerHeaders, answerBody);
      }
      catch (Orthanc::OrthancException&)
      {
        if (client->GetHttpStatus() == 411)
        {
          /**
           * "Length required" error. This might indicate an older
           * version of Orthanc (<= 1.5.6) that does not support
           * chunked transfers, or a version of Orthanc <= 1.7.2 that
           * supports chunk transfers, but cannot receive multipart
           * messages larger than 2GB. The latter problem is fixed by:
           * https://orthanc.uclouvain.be/hg/orthanc/rev/36257d6f348f
           **/
          if (client->IsChunkedTransfersAllowed())
          {
            LOG(ERROR) << "The remote DICOMweb server \"" << serverName << "\" does not support chunked transfers "
                       << "(this might indicate Orthanc <= 1.5.6), set configuration option \"ChunkedTransfers\" "
                       << "to \"false\" in the configuration (or upgrade remote Orthanc if applicable)";
          }
          else if (body->GetProcessedSize() >= 2 * static_cast<uint64_t>(1024 * 1024 * 1024))
          {
            LOG(ERROR) << "Cannot send a study larger than 2GB (chunked transfer is disabled) using STOW-RS, "
                       << "this might indicate that the remote DICOMweb server is Orthanc <= 1.7.2 "
                       << "(if so, please upgrade the remote Orthanc)";
          }
          else
          {
            LOG(ERROR) << "Cannot send a study of " << (body->GetProcessedSize() / (1024 * 1024))
                       << "MB with STOW-RS (chunked transfer is disabled), check out the logs of the remote modality";
          }
        }

        throw;
      }

      {
        boost::mutex::scoped_lock lock(that_.mutex_);
        size_t endPosition = that_.position_;
        CheckStowAnswer(answerBody, serverName, endPosition - startPosition);

        if (that_.action_ == Action_Cancel)
        {
          that_.position_ = 0;
        }
      }
    }
  };
  

  virtual void CancelFunction() ORTHANC_OVERRIDE
  {
    boost::mutex::scoped_lock lock(mutex_);
    action_ = Action_Cancel;
  }
  

  virtual void PauseFunction() ORTHANC_OVERRIDE
  {
    boost::mutex::scoped_lock lock(mutex_);
    action_ = Action_Pause;
  }

  
  virtual IFunction* CreateFunction() ORTHANC_OVERRIDE
  {
    action_ = Action_None;
    return new F(*this);
  }

  
public:
  StowClientJob(const std::string& serverName,
                const std::list<std::string>& instances,
                const OrthancPlugins::HttpHeaders& headers,
                const Json::Value& resourcesForJobContent) :
    SingleFunctionJob("DicomWebStowClient"),
    serverName_(serverName),
    headers_(headers),
    position_(0),
    action_(Action_None),
    networkSize_(0),
    debug_(false),
    resourcesForJobContent_(resourcesForJobContent)
  {
    SetFactory(*this);

    instances_.reserve(instances.size());

    for (std::list<std::string>::const_iterator
           it = instances.begin(); it != instances.end(); ++it)
    {
      instances_.push_back(*it);
    }

    {
      OrthancPlugins::OrthancString tmp;
      tmp.Assign(OrthancPluginGenerateUuid(OrthancPlugins::GetGlobalContext()));

      if (tmp.GetContent() == NULL)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError,
                                        "Cannot generate a UUID");
      }

      tmp.ToString(boundary_);
    }

    boundary_ = (boundary_ + "-" + boundary_);  // Make the boundary longer

    headers_["Accept"] = "application/dicom+json";
    headers_["Expect"] = "";
    headers_["Content-Type"] = "multipart/related; type=\"application/dicom\"; boundary=" + boundary_;
  }

  void SetDebug(bool debug)
  {
    debug_ = debug;
  }

  const Json::Value& GetResourcesForJobContent()
  {
    return resourcesForJobContent_;
  }

  const std::string& GetServerName()
  {
    return serverName_;
  }
};



void StowClient(OrthancPluginRestOutput* output,
                const char* /*url*/,
                const OrthancPluginHttpRequest* request)
{
  OrthancPluginContext* context = OrthancPlugins::GetGlobalContext();

  if (request->method != OrthancPluginHttpMethod_Post)
  {
    OrthancPluginSendMethodNotAllowed(context, output, "POST");
    return;
  }

  if (request->groupsCount != 1)
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_BadRequest);
  }

  std::string serverName(request->groups[0]);

  Json::Value body;
  OrthancPlugins::ParseJsonBody(body, request);

  std::list<std::string> instances;
  std::map<std::string, std::string> httpHeaders;
  Json::Value resourcesForJobContent;
  ParseStowRequest(instances, httpHeaders, resourcesForJobContent, body);

  LOG(INFO) << "Sending " << boost::lexical_cast<std::string>(instances.size()) <<
               " instances using STOW-RS to DICOMweb server: " << serverName;

  std::unique_ptr<StowClientJob> job(new StowClientJob(serverName, instances, httpHeaders, resourcesForJobContent));

  bool debug;
  if (OrthancPlugins::LookupBooleanValue(debug, body, "Debug"))
  {
    job->SetDebug(debug);
  }
  
  Json::Value answer;
  SubmitJob(output, job.release(), body, 
            true /* synchronous by default, for compatibility with <= 0.6 */);
}



static void ParseGetFromServer(std::string& uri,
                               std::map<std::string, std::string>& additionalHeaders,
                               const Json::Value& resource)
{
  static const char* URI = "Uri";
  static const char* HTTP_HEADERS = "HttpHeaders";
  static const char* GET_ARGUMENTS = "Arguments";

  std::string tmp;
  if (resource.type() != Json::objectValue ||
      !OrthancPlugins::LookupStringValue(tmp, resource, URI))
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat,
                                    "A request to the DICOMweb client must provide a JSON object "
                                    "with the field \"Uri\" containing the URI of interest");
  }

  std::map<std::string, std::string> getArguments;
  OrthancPlugins::ParseAssociativeArray(getArguments, resource, GET_ARGUMENTS); 
  OrthancPlugins::DicomWebServers::UriEncode(uri, tmp, getArguments);

  OrthancPlugins::ParseAssociativeArray(additionalHeaders, resource, HTTP_HEADERS);
}



static void ConfigureGetFromServer(OrthancPlugins::HttpClient& client,
                                   const OrthancPluginHttpRequest* request)
{
  if (request->method != OrthancPluginHttpMethod_Post)
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
  }

  Json::Value body;
  OrthancPlugins::ParseJsonBody(body, request);

  std::string uri;
  std::map<std::string, std::string> additionalHeaders;
  ParseGetFromServer(uri, additionalHeaders, body);

  std::map<std::string, std::string> userProperties;
  OrthancPlugins::DicomWebServers::GetInstance().ConfigureHttpClient(client, userProperties, request->groups[0], uri);
  client.AddHeaders(additionalHeaders);
}



void GetFromServer(OrthancPluginRestOutput* output,
                   const char* /*url*/,
                   const OrthancPluginHttpRequest* request)
{
  OrthancPluginContext* context = OrthancPlugins::GetGlobalContext();

  if (request->method != OrthancPluginHttpMethod_Post)
  {
    OrthancPluginSendMethodNotAllowed(context, output, "POST");
    return;
  }

  OrthancPlugins::HttpClient client;
  ConfigureGetFromServer(client, request);
  
  std::map<std::string, std::string> answerHeaders;
  std::string answer;
  client.Execute(answerHeaders, answer);

  std::string contentType = "application/octet-stream";

  for (std::map<std::string, std::string>::const_iterator
         it = answerHeaders.begin(); it != answerHeaders.end(); ++it)
  {
    std::string key = it->first;
    Orthanc::Toolbox::ToLowerCase(key);

    if (key == "content-type")
    {
      contentType = it->second;
    }
    else if (key == "transfer-encoding" ||
             key == "content-length" ||
             key == "connection")
    {
      // Do not forward these headers
    }
    else
    {
      OrthancPluginSetHttpHeader(context, output, it->first.c_str(), it->second.c_str());
    }
  }

  OrthancPluginAnswerBuffer(context, output, answer.empty() ? NULL : answer.c_str(), 
                            answer.size(), contentType.c_str());
}


void GetFromServer(Json::Value& result,
                   const OrthancPluginHttpRequest* request)
{
  OrthancPlugins::HttpClient client;
  ConfigureGetFromServer(client, request);

  std::map<std::string, std::string> answerHeaders;
  client.Execute(answerHeaders, result);
}





class WadoRetrieveAnswer : 
  public OrthancPlugins::HttpClient::IAnswer,
  private Orthanc::MultipartStreamReader::IHandler
{
private:
  enum State
  {
    State_Headers,
    State_Body,
    State_Canceled
  };

  bool                                           debug_;
  boost::mutex                                   mutex_;
  State                                          state_;
  std::list<std::string>                         instances_;
  std::unique_ptr<Orthanc::MultipartStreamReader>  reader_;
  uint64_t                                       networkSize_;

  virtual void HandlePart(const Orthanc::MultipartStreamReader::HttpHeaders& headers,
                          const void* part,
                          size_t size) ORTHANC_OVERRIDE
  {
    std::string contentType;
    if (!Orthanc::MultipartStreamReader::GetMainContentType(contentType, headers))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_NetworkProtocol,
                                      "Missing Content-Type for a part of WADO-RS answer");
    }

    size_t pos = contentType.find(';');
    if (pos != std::string::npos)
    {
      contentType = contentType.substr(0, pos);
    }

    contentType = Orthanc::Toolbox::StripSpaces(contentType);
    if (!boost::iequals(contentType, "application/dicom"))
    {
      throw Orthanc::OrthancException(
        Orthanc::ErrorCode_NetworkProtocol,
        "Parts of a WADO-RS retrieve should have \"application/dicom\" type, but received: " + contentType);
    }

    OrthancPlugins::MemoryBuffer tmp;
    tmp.RestApiPost("/instances", part, size, false);

    Json::Value result;
    tmp.ToJson(result);

    std::string id;
    if (OrthancPlugins::LookupStringValue(id, result, "ID"))
    {
      instances_.push_back(id);
    }
    else
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);      
    }

    if (debug_)
    {
      boost::this_thread::sleep(boost::posix_time::milliseconds(50));
    }
  }

public:
  WadoRetrieveAnswer() :
    debug_(false),
    state_(State_Headers),
    networkSize_(0)
  {
  }

  virtual ~WadoRetrieveAnswer()
  {
  }

  void SetDebug(bool debug)
  {
    debug_ = debug;
  }

  void Close()
  {
    boost::mutex::scoped_lock lock(mutex_);

    if (state_ != State_Canceled &&
        reader_.get() != NULL)
    {
      reader_->CloseStream();
    }
  }

  virtual void AddHeader(const std::string& key,
                         const std::string& value) ORTHANC_OVERRIDE
  {
    boost::mutex::scoped_lock lock(mutex_);

    if (state_ == State_Canceled)
    {
      return;
    }
    else if (state_ != State_Headers)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
    }

    if (boost::iequals(key, "Content-Type"))
    {
      if (reader_.get() != NULL)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_NetworkProtocol,
                                        "Received twice a Content-Type header in WADO-RS");
      }

      std::string contentType, subType, boundary;

      if (!Orthanc::MultipartStreamReader::ParseMultipartContentType
          (contentType, subType, boundary, value))
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_NetworkProtocol,
                                        "Cannot parse the Content-Type for WADO-RS: " + value);
      }

      if (!boost::iequals(contentType, MULTIPART_RELATED))
      {
        throw Orthanc::OrthancException(
          Orthanc::ErrorCode_NetworkProtocol,
          "The remote WADO-RS server answers with a \"" + contentType +
          "\" Content-Type, but \"" + MULTIPART_RELATED + "\" is expected");
      }

      reader_.reset(new Orthanc::MultipartStreamReader(boundary));
      reader_->SetHandler(*this);

      if (debug_)
      {
        reader_->SetBlockSize(1024 * 64);
      }
    }
  }

  virtual void AddChunk(const void* data,
                        size_t size) ORTHANC_OVERRIDE
  {
    boost::mutex::scoped_lock lock(mutex_);

    if (state_ == State_Canceled)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_CanceledJob);
    }
    else if (reader_.get() == NULL)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_NetworkProtocol,
                                      "No Content-Type provided by the remote WADO-RS server, "
                                      "your remote DICOMweb server might need client option \"" +
                                      HAS_WADO_RS_UNIVERSAL_TRANSFER_SYNTAX + "\" set to \"false\"");
    }
    else
    {
      state_ = State_Body;
      networkSize_ += size;
      reader_->AddChunk(data, size);
    }
  }

  void GetReceivedInstances(std::list<std::string>& target)
  {
    boost::mutex::scoped_lock lock(mutex_);
    target = instances_;
  }

  void Cancel()
  {
    boost::mutex::scoped_lock lock(mutex_);
    LOG(ERROR) << "A WADO-RS retrieve job has been canceled, expect \"Error in the network protocol\" errors";
    state_ = State_Canceled;
  }

  uint64_t GetNetworkSize()
  {
    boost::mutex::scoped_lock lock(mutex_);
    return networkSize_;
  }
};





class WadoRetrieveJob : 
  public SingleFunctionJob,
  private SingleFunctionJob::IFunctionFactory
{
private:
  class Resource : public boost::noncopyable
  {
  private:
    std::string                        uri_;
    std::map<std::string, std::string> additionalHeaders_;

  public:
    explicit Resource(const std::string& uri) :
      uri_(uri)
    {
    }

    Resource(const std::string& uri,
             const std::map<std::string, std::string>& additionalHeaders) :
      uri_(uri),
      additionalHeaders_(additionalHeaders)
    {
    }

    const std::string& GetUri() const
    {
      return uri_;
    }

    const std::map<std::string, std::string>& GetAdditionalHeaders() const
    {
      return additionalHeaders_;
    }
  };


  class F : public IFunction
  {
  private:
    WadoRetrieveJob&   that_;

  public:
    explicit F(WadoRetrieveJob& that) :
      that_(that)
    {
    }

    virtual void Execute(JobContext& context)
    {
      for (;;)
      {
        OrthancPlugins::HttpClient client;

        if (that_.SetupNextResource(client, context))
        {
          client.Execute(*that_.answer_);
          that_.CloseResource(context);
        }
        else
        {
          return;   // We're done
        }
      }
    }
  };


  boost::mutex            mutex_;
  std::string             serverName_;
  size_t                  position_;
  std::vector<Resource*>  resources_;
  bool                    stopped_;
  std::list<std::string>  retrievedInstances_;
  std::unique_ptr<WadoRetrieveAnswer>  answer_;
  uint64_t                networkSize_;
  bool                    debug_;

  bool SetupNextResource(OrthancPlugins::HttpClient& client,
                         JobContext& context)
  {
    boost::mutex::scoped_lock lock(mutex_);

    if (stopped_ ||
        position_ == resources_.size())
    {
      return false;
    }
    else
    {
      context.SetProgress(position_, resources_.size());

      answer_.reset(new WadoRetrieveAnswer);
      answer_->SetDebug(debug_);

      const Resource* resource = resources_[position_++];
      if (resource == NULL)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
      }

      const std::map<std::string, std::string>& headers = resource->GetAdditionalHeaders();

      std::map<std::string, std::string> userProperties;
      OrthancPlugins::DicomWebServers::GetInstance().ConfigureHttpClient
        (client, userProperties, serverName_, resource->GetUri());
      client.AddHeaders(headers);

      /**
       * From documentation of Google Healthcare API: "The response's
       * default transfer syntax is Little Endian Explicit. As a
       * result, if the file was uploaded using a compressed transfer
       * syntax, the returned object will be decompressed. This can
       * negatively impact performance and lead to errors for transfer
       * syntaxes that the Cloud Healthcare API doesn't support. To
       * avoid these issues, and if the returned object's transfer
       * syntax does not matter to your application, use the [...]
       * Accept Header."
       * https://cloud.google.com/healthcare/docs/dicom
       * https://groups.google.com/d/msg/orthanc-users/w1Ekrsc6-U8/T2a_DoQ5CwAJ
       *
       * WARNING - This breaks compatibility with Orthanc servers
       * equiped with DICOMweb <= 1.0, as can be seen in integration
       * test "Orthanc.test_server_retrieve". The configuration option
       * "HasWadoRsUniversalTransferSyntax" enables compatibility with
       * DICOMweb <= 1.0.
       **/

      if (headers.find("Accept") == headers.end())
      {
        bool hasUniversal;
          
        // The "Accept" field was not provided in the "HttpHeaders"
        // field of the POST body of: "/dicom-web/servers/.../retrieve"
        std::map<std::string, std::string>::const_iterator found = 
          userProperties.find(HAS_WADO_RS_UNIVERSAL_TRANSFER_SYNTAX);

        if (found == userProperties.end())
        {
          hasUniversal = true;  // By default, assume "true"
        }
        else if (found->second == "true" ||
                 found->second == "1")
        {
          hasUniversal = true;
        }
        else if (found->second == "false" ||
                 found->second == "0")
        {
          hasUniversal = false;
        }
        else
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange,
                                          "Configuration option \"" + HAS_WADO_RS_UNIVERSAL_TRANSFER_SYNTAX +
                                          "\" of remote DICOMweb server \"" + serverName_ +
                                          "\" must be a Boolean, found: " + found->second);
        }
        
        if (hasUniversal)
        {
          client.AddHeader("Accept", "multipart/related; type=\"application/dicom\"; transfer-syntax=*");
        }
      }

      return true;
    }
  }


  void CloseResource(JobContext& context)
  {
    boost::mutex::scoped_lock lock(mutex_);
    answer_->Close();

    std::list<std::string> instances;
    answer_->GetReceivedInstances(instances);
    networkSize_ += answer_->GetNetworkSize();

    answer_.reset();

    retrievedInstances_.splice(retrievedInstances_.end(), instances);

    context.SetProgress(position_, resources_.size());
    context.SetContent("NetworkUsageMB", boost::lexical_cast<std::string>
                       (networkSize_ / static_cast<uint64_t>(1024 * 1024)));
    context.SetContent("ReceivedInstancesCount", boost::lexical_cast<std::string>(retrievedInstances_.size()));
  }


  virtual void CancelFunction() ORTHANC_OVERRIDE
  {
    boost::mutex::scoped_lock lock(mutex_);

    stopped_ = true;
    if (answer_.get() != NULL)
    {      
      answer_->Cancel();
    }
  }

  virtual void PauseFunction() ORTHANC_OVERRIDE
  {
    // This type of job cannot be paused
    CancelFunction();
  }

  virtual IFunction* CreateFunction() ORTHANC_OVERRIDE
  {
    // This type of job cannot be paused: If restarting, always go
    // back to the beginning

    stopped_ = false;
    position_ = 0;
    retrievedInstances_.clear();

    return new F(*this);
  }

public:
  explicit WadoRetrieveJob(const std::string& serverName) :
    SingleFunctionJob("DicomWebWadoRetrieveClient"),
    serverName_(serverName),
    position_(0),
    stopped_(false),
    networkSize_(0),
    debug_(false)
  {
    SetFactory(*this);
  }

  virtual ~WadoRetrieveJob()
  {
    SingleFunctionJob::Finalize();

    for (size_t i = 0; i < resources_.size(); i++)
    {
      assert(resources_[i] != NULL);
      delete resources_[i];
    }
  }

  void SetDebug(bool debug)
  {
    debug_ = debug;
  }

  /*void AddResource(const std::string& uri)
  {
    resources_.push_back(new Resource(uri));
    }*/

  void AddResource(const std::string& uri,
                   const std::map<std::string, std::string>& additionalHeaders)
  {
    resources_.push_back(new Resource(uri, additionalHeaders));
  }

  void AddResourceFromRequest(const Json::Value& resource)
  {
    std::string uri;
    std::map<std::string, std::string> additionalHeaders;
    ParseGetFromServer(uri, additionalHeaders, resource);

    resources_.push_back(new Resource(uri, additionalHeaders));
  }
};


void WadoRetrieveClient(OrthancPluginRestOutput* output,
                        const char* url,
                        const OrthancPluginHttpRequest* request)
{
  if (request->method != OrthancPluginHttpMethod_Post)
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
  }

  if (request->groupsCount != 1)
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_BadRequest);
  }

  std::string serverName(request->groups[0]);

  Json::Value body;
  OrthancPlugins::ParseJsonBody(body, request);

  std::unique_ptr<WadoRetrieveJob>  job(new WadoRetrieveJob(serverName));
  job->AddResourceFromRequest(body);

  bool debug;
  if (OrthancPlugins::LookupBooleanValue(debug, body, "Debug"))
  {
    job->SetDebug(debug);
  }

  SubmitJob(output, job.release(), body, false /* asynchronous by default */);
}



void RetrieveFromServer(OrthancPluginRestOutput* output,
                        const char* url,
                        const OrthancPluginHttpRequest* request)
{
  static const char* const GET_ARGUMENTS = "GetArguments";
  static const char* const HTTP_HEADERS = "HttpHeaders";
  static const char* const RESOURCES = "Resources";
  static const char* const STUDY = "Study";
  static const char* const SERIES = "Series";
  static const char* const INSTANCE = "Instance";

  if (request->method != OrthancPluginHttpMethod_Post)
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
  }

  if (request->groupsCount != 1)
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_BadRequest);
  }

  std::string serverName(request->groups[0]);

  Json::Value body;
  OrthancPlugins::ParseJsonBody(body, request);

  std::map<std::string, std::string> getArguments;
  OrthancPlugins::ParseAssociativeArray(getArguments, body, GET_ARGUMENTS); 

  std::map<std::string, std::string> additionalHeaders;
  OrthancPlugins::ParseAssociativeArray(additionalHeaders, body, HTTP_HEADERS);

  std::unique_ptr<WadoRetrieveJob> job(new WadoRetrieveJob(serverName));

  if (body.type() != Json::objectValue ||
      !body.isMember(RESOURCES) ||
      body[RESOURCES].type() != Json::arrayValue)
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat,
                                    "The body must be a JSON object containing an array \"" + 
                                    std::string(RESOURCES) + "\"");
  }

  const Json::Value& resources = body[RESOURCES];

  for (Json::Value::ArrayIndex i = 0; i < resources.size(); i++)
  {
    std::string study;
    if (!OrthancPlugins::LookupStringValue(study, resources[i], STUDY))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat,
                                      "Missing \"Study\" field in the body");
    }

    std::string series;
    if (!OrthancPlugins::LookupStringValue(series, resources[i], SERIES))
    {
      series.clear();
    }

    std::string instance;
    if (!OrthancPlugins::LookupStringValue(instance, resources[i], INSTANCE))
    {
      instance.clear();
    }

    if (series.empty() &&
        !instance.empty())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat,
                                      "Missing \"Series\" field in the body, as \"Instance\" is present");
    }

    std::string tmp = "/studies/" + study;

    if (!series.empty())
    {
      tmp += "/series/" + series;
    }

    if (!instance.empty())
    {
      tmp += "/instances/" + instance;
    }

    std::string uri;
    OrthancPlugins::DicomWebServers::UriEncode(uri, tmp, getArguments);

    job->AddResource(uri, additionalHeaders);
  }

  bool debug;
  if (OrthancPlugins::LookupBooleanValue(debug, body, "Debug"))
  {
    job->SetDebug(debug);
  }

  SubmitJob(output, job.release(), body, 
            true /* synchronous by default, for compatibility with <= 0.6 */);
}

