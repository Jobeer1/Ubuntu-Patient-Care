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

#include "PluginContext.h"
#include "../Framework/HttpQueries/DetectTransferPlugin.h"
#include "../Framework/PullMode/PullJob.h"
#include "../Framework/PushMode/PushJob.h"
#include "../Framework/TransferScheduler.h"

#include <EmbeddedResources.h>

#include <Compatibility.h>  // For std::unique_ptr
#include <ChunkedBuffer.h>
#include <Compression/GzipCompressor.h>
#include <Logging.h>
#include <Toolbox.h>


static bool DisplayPerformanceWarning()
{
  (void) DisplayPerformanceWarning;   // Disable warning about unused function
  LOG(WARNING) << "Performance warning in transfers accelerator: "
               << "Non-release build, runtime debug assertions are turned on";
  return true;
}


static size_t ReadSizeArgument(const OrthancPluginHttpRequest* request,
                               uint32_t index)
{
  std::string value(request->getValues[index]);

  try
  {
    int tmp = boost::lexical_cast<int>(value);
    if (tmp >= 0)
    {
      return static_cast<size_t>(tmp);
    }
  }
  catch (boost::bad_lexical_cast&)
  {
  }

  LOG(ERROR) << "The \"" << request->getKeys[index]
             << "\" GET argument must be a positive integer: " << value;
  throw Orthanc::OrthancException(Orthanc::ErrorCode_BadParameterType);
}


void ServeChunks(OrthancPluginRestOutput* output,
                 const char* url,
                 const OrthancPluginHttpRequest* request)
{
  OrthancPlugins::PluginContext& context = OrthancPlugins::PluginContext::GetInstance();
  
  if (request->method != OrthancPluginHttpMethod_Get)
  {
    OrthancPluginSendMethodNotAllowed(OrthancPlugins::GetGlobalContext(), output, "GET");
    return;
  }
  
  assert(request->groupsCount == 1);

  std::vector<std::string> instances;
  Orthanc::Toolbox::TokenizeString(instances, std::string(request->groups[0]), '.');

  size_t offset = 0;
  size_t requestedSize = 0;
  OrthancPlugins::BucketCompression compression = OrthancPlugins::BucketCompression_None;

  for (uint32_t i = 0; i < request->getCount; i++)
  {
    std::string key(request->getKeys[i]);

    if (key == "offset")
    {
      offset = ReadSizeArgument(request, i);
    }
    else if (key == "size")
    {
      requestedSize = ReadSizeArgument(request, i);
    }
    else if (key == "compression")
    {
      compression = OrthancPlugins::StringToBucketCompression(request->getValues[i]);
    }
    else
    {
      LOG(INFO) << "Ignored GET argument: " << key;
    }
  }


  // Limit the number of clients
  Orthanc::Semaphore::Locker lock(context.GetSemaphore());

  Orthanc::ChunkedBuffer buffer;

  for (size_t i = 0; i < instances.size() && (requestedSize == 0 ||
                                              buffer.GetNumBytes() < requestedSize); i++)
  {
    size_t instanceSize;

    {
      std::string md5;  // Ignored
      context.GetCache().GetInstanceInfo(instanceSize, md5, instances[i]);
    }

    if (offset >= instanceSize)
    {
      offset -= instanceSize;
    }
    else
    {
      size_t toRead;
      
      if (requestedSize == 0)
      {
        toRead = instanceSize - offset;
      }
      else
      {
        toRead = requestedSize - buffer.GetNumBytes();

        if (toRead > instanceSize - offset)
        {
          toRead = instanceSize - offset;
        }
      }

      std::string chunk;

      {
        std::string md5;  // Ignored
        context.GetCache().GetChunk(chunk, md5, instances[i], offset, toRead);
      }
        
      buffer.AddChunk(chunk);
      offset = 0;

      assert(requestedSize == 0 ||
             buffer.GetNumBytes() <= requestedSize);
    }
  }

  std::string chunk;
  buffer.Flatten(chunk);
  

  switch (compression)
  {
    case OrthancPlugins::BucketCompression_None:
    {
      OrthancPluginAnswerBuffer(OrthancPlugins::GetGlobalContext(), output, chunk.c_str(),
                                chunk.size(), "application/octet-stream");
      break;
    }

    case OrthancPlugins::BucketCompression_Gzip:
    {
      std::string compressed;
      Orthanc::GzipCompressor gzip;
      //gzip.SetCompressionLevel(9);
      Orthanc::IBufferCompressor::Compress(compressed, gzip, chunk);
      OrthancPluginAnswerBuffer(OrthancPlugins::GetGlobalContext(), output, compressed.c_str(),
                                compressed.size(), "application/gzip");
      break;
    }

    default:
      throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
  }
}



static bool ParsePostBody(Json::Value& body,
                          OrthancPluginRestOutput* output,
                          const OrthancPluginHttpRequest* request)
{
  if (request->method != OrthancPluginHttpMethod_Post)
  {
    OrthancPluginSendMethodNotAllowed(OrthancPlugins::GetGlobalContext(), output, "POST");
    return false;
  }
  else if (Orthanc::Toolbox::ReadJson(body, request->body, request->bodySize))
  {
    return true;
  }
  else
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
  }
}


void LookupInstances(OrthancPluginRestOutput* output,
                     const char* url,
                     const OrthancPluginHttpRequest* request)
{
  OrthancPlugins::PluginContext& context = OrthancPlugins::PluginContext::GetInstance();
  
  Json::Value resources;
  if (!ParsePostBody(resources, output, request))
  {
    return;
  }
  
  OrthancPlugins::TransferScheduler scheduler;
  scheduler.ParseListOfResources(context.GetCache(), resources);

  Json::Value answer = Json::objectValue;
  answer[KEY_INSTANCES] = Json::arrayValue;
  answer[KEY_ORIGINATOR_UUID] = context.GetPluginUuid();
  answer["CountInstances"] = static_cast<uint32_t>(scheduler.GetInstancesCount());
  answer["TotalSize"] = boost::lexical_cast<std::string>(scheduler.GetTotalSize());
  answer["TotalSizeMB"] = OrthancPlugins::ConvertToMegabytes(scheduler.GetTotalSize());

  std::vector<OrthancPlugins::DicomInstanceInfo> instances;
  scheduler.ListInstances(instances);

  for (size_t i = 0; i < instances.size(); i++)
  {
    Json::Value instance;
    instances[i].Serialize(instance);
    answer[KEY_INSTANCES].append(instance);
  }
  
  std::string s;
  Orthanc::Toolbox::WriteFastJson(s, answer);  
  OrthancPluginAnswerBuffer(OrthancPlugins::GetGlobalContext(), output, s.c_str(), s.size(), "application/json");
}



static void SubmitJob(OrthancPluginRestOutput* output,
                      OrthancPlugins::OrthancJob* job,
                      int priority)
{
  std::string id = OrthancPlugins::OrthancJob::Submit(job, priority);

  Json::Value result = Json::objectValue;
  result[KEY_ID] = id;
  result[KEY_PATH] = std::string(URI_JOBS) + "/" + id;

  std::string s = result.toStyledString();
  OrthancPluginAnswerBuffer(OrthancPlugins::GetGlobalContext(), output, s.c_str(), s.size(), "application/json");
}



void SchedulePull(OrthancPluginRestOutput* output,
                  const char* url,
                  const OrthancPluginHttpRequest* request)
{
  const OrthancPlugins::PluginContext& context = OrthancPlugins::PluginContext::GetInstance();
  
  Json::Value body;
  if (!ParsePostBody(body, output, request))
  {
    return;
  }

  OrthancPlugins::TransferQuery query(body);

  SubmitJob(output, new OrthancPlugins::PullJob(query, context.GetThreadsCount(),
                                                context.GetTargetBucketSize(),
                                                context.GetMaxHttpRetries()),
            query.GetPriority());
}



void CreatePush(OrthancPluginRestOutput* output,
                const char* url,
                const OrthancPluginHttpRequest* request)
{
  OrthancPlugins::PluginContext& context = OrthancPlugins::PluginContext::GetInstance();
  
  Json::Value query;
  if (!ParsePostBody(query, output, request))
  {
    return;
  }
  
  if (query.type() != Json::objectValue ||
      !query.isMember(KEY_BUCKETS) ||
      !query.isMember(KEY_COMPRESSION) ||
      !query.isMember(KEY_INSTANCES) ||
      query[KEY_BUCKETS].type() != Json::arrayValue ||
      query[KEY_COMPRESSION].type() != Json::stringValue ||
      query[KEY_INSTANCES].type() != Json::arrayValue)
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
  }

  std::vector<OrthancPlugins::DicomInstanceInfo> instances;
  instances.reserve(query[KEY_INSTANCES].size());
  
  for (Json::Value::ArrayIndex i = 0; i < query[KEY_INSTANCES].size(); i++)
  {
    OrthancPlugins::DicomInstanceInfo instance(query[KEY_INSTANCES][i]);
    instances.push_back(instance);
  }

  std::vector<OrthancPlugins::TransferBucket> buckets;
  buckets.reserve(query[KEY_BUCKETS].size());
  
  for (Json::Value::ArrayIndex i = 0; i < query[KEY_BUCKETS].size(); i++)
  {
    OrthancPlugins::TransferBucket bucket(query[KEY_BUCKETS][i]);
    buckets.push_back(bucket);
  }

  OrthancPlugins::BucketCompression compression =
    OrthancPlugins::StringToBucketCompression(query[KEY_COMPRESSION].asString());
                                              
  std::string id = context.GetActivePushTransactions().CreateTransaction
    (instances, buckets, compression);
  
  Json::Value result = Json::objectValue;
  result[KEY_ID] = id;
  result[KEY_PATH] = std::string(URI_PUSH) + "/" + id;

  std::string s = result.toStyledString();
  OrthancPluginAnswerBuffer(OrthancPlugins::GetGlobalContext(), output, s.c_str(), s.size(), "application/json");
}


void StorePush(OrthancPluginRestOutput* output,
               const char* url,
               const OrthancPluginHttpRequest* request)
{
  OrthancPlugins::PluginContext& context = OrthancPlugins::PluginContext::GetInstance();
  
  if (request->method != OrthancPluginHttpMethod_Put)
  {
    OrthancPluginSendMethodNotAllowed(OrthancPlugins::GetGlobalContext(), output, "PUT");
    return;
  }

  assert(request->groupsCount == 2);
  std::string transaction(request->groups[0]);
  std::string chunk(request->groups[1]);

  size_t chunkIndex;
  
  try
  {
    chunkIndex = boost::lexical_cast<size_t>(chunk);
  }
  catch (boost::bad_lexical_cast&)
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_UnknownResource);
  }

  context.GetActivePushTransactions().Store
    (transaction, chunkIndex, request->body, request->bodySize);

  std::string s = "{}";
  OrthancPluginAnswerBuffer(OrthancPlugins::GetGlobalContext(), output, s.c_str(), s.size(), "application/json");
}


void CommitPush(OrthancPluginRestOutput* output,
                const char* url,
                const OrthancPluginHttpRequest* request)
{
  OrthancPlugins::PluginContext& context = OrthancPlugins::PluginContext::GetInstance();
  
  if (request->method != OrthancPluginHttpMethod_Post)
  {
    OrthancPluginSendMethodNotAllowed(OrthancPlugins::GetGlobalContext(), output, "POST");
    return;
  }

  assert(request->groupsCount == 1);
  std::string transaction(request->groups[0]);

  context.GetActivePushTransactions().Commit(transaction);

  std::string s = "{}";
  OrthancPluginAnswerBuffer(OrthancPlugins::GetGlobalContext(), output, s.c_str(), s.size(), "application/json");
}


void DiscardPush(OrthancPluginRestOutput* output,
                 const char* url,
                 const OrthancPluginHttpRequest* request)
{
  OrthancPlugins::PluginContext& context = OrthancPlugins::PluginContext::GetInstance();
  
  if (request->method != OrthancPluginHttpMethod_Delete)
  {
    OrthancPluginSendMethodNotAllowed(OrthancPlugins::GetGlobalContext(), output, "DELETE");
    return;
  }

  assert(request->groupsCount == 1);
  std::string transaction(request->groups[0]);

  context.
    GetActivePushTransactions().Discard(transaction);

  std::string s = "{}";
  OrthancPluginAnswerBuffer(OrthancPlugins::GetGlobalContext(), output, s.c_str(), s.size(), "application/json");
}



void ScheduleSend(OrthancPluginRestOutput* output,
                  const char* url,
                  const OrthancPluginHttpRequest* request)
{
  OrthancPlugins::PluginContext& context = OrthancPlugins::PluginContext::GetInstance();
  
  Json::Value body;
  if (!ParsePostBody(body, output, request))
  {
    return;
  }

  OrthancPlugins::TransferQuery query(body);

  OrthancPlugins::OrthancPeers peers;
  
  std::string remoteSelf;  // For pull mode
  bool pullMode = peers.LookupUserProperty(remoteSelf, query.GetPeer(), KEY_REMOTE_SELF);

  LOG(INFO) << "Sending resources to peer \"" << query.GetPeer() << "\" using "
            << (pullMode ? "pull" : "push") << " mode";

  if (pullMode)
  {
    Json::Value lookup = Json::objectValue;
    lookup[KEY_RESOURCES] = query.GetResources();
    lookup[KEY_COMPRESSION] = OrthancPlugins::EnumerationToString(query.GetCompression());
    lookup[KEY_ORIGINATOR_UUID] = context.GetPluginUuid();
    lookup[KEY_PEER] = remoteSelf;

    std::string s;
    Orthanc::Toolbox::WriteFastJson(s, lookup);  

    Json::Value answer;
    std::map<std::string, std::string> headers;
    query.GetHttpHeaders(headers);

    if (DoPostPeer(answer, peers, query.GetPeer(), URI_PULL, s, context.GetMaxHttpRetries(), headers) &&
        answer.type() == Json::objectValue &&
        answer.isMember(KEY_ID) &&
        answer.isMember(KEY_PATH) &&
        answer[KEY_ID].type() == Json::stringValue &&
        answer[KEY_PATH].type() == Json::stringValue)
    {
      const std::string peer = peers.GetPeerUrl(query.GetPeer());

      Json::Value result = Json::objectValue;
      result[KEY_PEER] = query.GetPeer();
      result[KEY_REMOTE_JOB] = answer[KEY_ID].asString();
      result[KEY_URL] = peer + answer[KEY_PATH].asString();

      s = result.toStyledString();
      OrthancPluginAnswerBuffer(OrthancPlugins::GetGlobalContext(), output, s.c_str(), s.size(), "application/json");
    }
    else
    {
      LOG(ERROR) << "Cannot trigger send DICOM instances using pull mode to peer: " << query.GetPeer()
                 << " (check out remote logs, and that transfer plugin is installed)";
      throw Orthanc::OrthancException(Orthanc::ErrorCode_NetworkProtocol);
    }
  }
  else
  {
    SubmitJob(output, new OrthancPlugins::PushJob(query, context.GetCache(),
                                                  context.GetThreadsCount(),
                                                  context.GetTargetBucketSize(),
                                                  context.GetMaxHttpRetries(),
                                                  context.GetPeerCommitTimeout()),
              query.GetPriority());
  }
}


OrthancPluginJob* Unserializer(const char* jobType,
                               const char* serialized)
{
  OrthancPlugins::PluginContext& context = OrthancPlugins::PluginContext::GetInstance();
  
  if (jobType == NULL ||
      serialized == NULL)
  {
    return NULL;
  }

  std::string type(jobType);

  if (type != JOB_TYPE_PULL &&
      type != JOB_TYPE_PUSH)
  {
    return NULL;
  }

  try
  {
    std::string tmp(serialized);

    Json::Value source;
    if (Orthanc::Toolbox::ReadJson(source, tmp))
    {
      OrthancPlugins::TransferQuery query(source);

      std::unique_ptr<OrthancPlugins::OrthancJob> job;

      if (type == JOB_TYPE_PULL)
      {
        job.reset(new OrthancPlugins::PullJob(query,
                                              context.GetThreadsCount(),
                                              context.GetTargetBucketSize(),
                                              context.GetMaxHttpRetries()));
      }
      else if (type == JOB_TYPE_PUSH)
      {
        job.reset(new OrthancPlugins::PushJob(query,
                                              context.GetCache(),
                                              context.GetThreadsCount(),
                                              context.GetTargetBucketSize(),
                                              context.GetMaxHttpRetries(),
                                              context.GetPeerCommitTimeout()));
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
    LOG(ERROR) << "Error while unserializing a job from the transfers accelerator plugin: "
               << e.What();
    return NULL;
  }
  catch (...)
  {
    LOG(ERROR) << "Error while unserializing a job from the transfers accelerator plugin";
    return NULL;
  }
}



void ServePeers(OrthancPluginRestOutput* output,
                const char* url,
                const OrthancPluginHttpRequest* request)
{
  const OrthancPlugins::PluginContext& context = OrthancPlugins::PluginContext::GetInstance();
  
  if (request->method != OrthancPluginHttpMethod_Get)
  {
    OrthancPluginSendMethodNotAllowed(OrthancPlugins::GetGlobalContext(), output, "GET");
    return;
  }

  OrthancPlugins::DetectTransferPlugin::Result detection;
  OrthancPlugins::DetectTransferPlugin::Apply
    (detection, context.GetThreadsCount(), context.GetPeerConnectivityTimeout());

  Json::Value result = Json::objectValue;

  OrthancPlugins::OrthancPeers peers;

  for (OrthancPlugins::DetectTransferPlugin::Result::const_iterator
         it = detection.begin(); it != detection.end(); ++it)
  {
    if (it->second)
    {
      std::string remoteSelf;

      if (peers.LookupUserProperty(remoteSelf, it->first, KEY_REMOTE_SELF))
      {    
        result[it->first] = "bidirectional";
      }
      else
      {
        result[it->first] = "installed";
      }
    }
    else
    {
      result[it->first] = "disabled";
    }
  }

  std::string s = result.toStyledString();
  OrthancPluginAnswerBuffer(OrthancPlugins::GetGlobalContext(), output, s.c_str(), s.size(), "application/json");
}



extern "C"
{
  ORTHANC_PLUGINS_API int32_t OrthancPluginInitialize(OrthancPluginContext* context)
  {
    OrthancPlugins::SetGlobalContext(context, PLUGIN_NAME);

#if ORTHANC_FRAMEWORK_VERSION_IS_ABOVE(1, 12, 4)
    Orthanc::Logging::InitializePluginContext(context, PLUGIN_NAME);
#else
    Orthanc::Logging::InitializePluginContext(context);
#endif
    
    assert(DisplayPerformanceWarning());
    
    /* Check the version of the Orthanc core */
    if (OrthancPluginCheckVersion(context) == 0)
    {
      LOG(ERROR) << "Your version of Orthanc (" 
                 << context->orthancVersion << ") must be above "
                 << ORTHANC_PLUGINS_MINIMAL_MAJOR_NUMBER << "."
                 << ORTHANC_PLUGINS_MINIMAL_MINOR_NUMBER << "."
                 << ORTHANC_PLUGINS_MINIMAL_REVISION_NUMBER
                 << " to run this plugin";
      return -1;
    }

    OrthancPlugins::SetDescription(PLUGIN_NAME, "Accelerates transfers and provides "
                                   "storage commitment between Orthanc peers");

    try
    {
      size_t threadsCount = 4;
      size_t targetBucketSize = 4096;  // In KB
      size_t maxPushTransactions = 4;
      size_t memoryCacheSize = 512;    // In MB
      unsigned int maxHttpRetries = 0;
      unsigned int peerConnectivityTimeout = 2;
      unsigned int peerCommitTimeout = 600;
    
      {
        OrthancPlugins::OrthancConfiguration config;

        if (config.IsSection(KEY_PLUGIN_CONFIGURATION))
        {
          OrthancPlugins::OrthancConfiguration plugin;
          config.GetSection(plugin, KEY_PLUGIN_CONFIGURATION);

          threadsCount = plugin.GetUnsignedIntegerValue("Threads", threadsCount);
          targetBucketSize = plugin.GetUnsignedIntegerValue("BucketSize", targetBucketSize);
          memoryCacheSize = plugin.GetUnsignedIntegerValue("CacheSize", memoryCacheSize);
          maxPushTransactions = plugin.GetUnsignedIntegerValue("MaxPushTransactions", maxPushTransactions);
          maxHttpRetries = plugin.GetUnsignedIntegerValue("MaxHttpRetries", maxHttpRetries);
          peerConnectivityTimeout = plugin.GetUnsignedIntegerValue("PeerConnectivityTimeout", peerConnectivityTimeout);
          peerCommitTimeout = plugin.GetUnsignedIntegerValue("PeerCommitTimeout", peerCommitTimeout);
        }
      }

      OrthancPlugins::PluginContext::Initialize(threadsCount, targetBucketSize * KB, maxPushTransactions,
                                                memoryCacheSize * MB, maxHttpRetries, peerConnectivityTimeout, peerCommitTimeout);
    
      OrthancPlugins::RegisterRestCallback<ServeChunks>
        (std::string(URI_CHUNKS) + "/([.0-9a-f-]+)", true);

      OrthancPlugins::RegisterRestCallback<LookupInstances>
        (URI_LOOKUP, true);

      OrthancPlugins::RegisterRestCallback<SchedulePull>
        (URI_PULL, true);

      OrthancPlugins::RegisterRestCallback<ScheduleSend>
        (URI_SEND, true);

      OrthancPlugins::RegisterRestCallback<ServePeers>
        (URI_PEERS, true);

      if (maxPushTransactions != 0)
      {
        // If no push transaction is allowed, their URIs are disabled
        OrthancPlugins::RegisterRestCallback<CreatePush>
          (URI_PUSH, true);

        OrthancPlugins::RegisterRestCallback<StorePush>
          (std::string(URI_PUSH) + "/([.0-9a-f-]+)/([0-9]+)", true);

        OrthancPlugins::RegisterRestCallback<CommitPush>
          (std::string(URI_PUSH) + "/([.0-9a-f-]+)/commit", true);
    
        OrthancPlugins::RegisterRestCallback<DiscardPush>
          (std::string(URI_PUSH) + "/([.0-9a-f-]+)", true);
      }

      OrthancPluginRegisterJobsUnserializer(context, Unserializer);

      /* Extend the default Orthanc Explorer with custom JavaScript */
      std::string explorer;
      Orthanc::EmbeddedResources::GetFileResource
        (explorer, Orthanc::EmbeddedResources::ORTHANC_EXPLORER);
      OrthancPlugins::ExtendOrthancExplorer(PLUGIN_NAME, explorer);
    }
    catch (Orthanc::OrthancException& e)
    {
      LOG(ERROR) << "Cannot initialize transfers accelerator plugin: " << e.What();
      return -1;
    }

    return 0;
  }


  ORTHANC_PLUGINS_API void OrthancPluginFinalize()
  {
    LOG(WARNING) << "Transfers accelerator plugin is finalizing";

    try
    {
      OrthancPlugins::PluginContext::Finalize();
    }
    catch (Orthanc::OrthancException& e)
    {
      LOG(ERROR) << "Error while finalizing the transfers accelerator plugin: " << e.What();
    }
  }


  ORTHANC_PLUGINS_API const char* OrthancPluginGetName()
  {
    return PLUGIN_NAME;
  }


  ORTHANC_PLUGINS_API const char* OrthancPluginGetVersion()
  {
    return ORTHANC_PLUGIN_VERSION;
  }
}
