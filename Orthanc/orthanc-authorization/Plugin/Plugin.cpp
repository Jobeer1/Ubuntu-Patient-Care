/**
 * Advanced authorization plugin for Orthanc
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

#include "AssociativeArray.h"
#include "DefaultAuthorizationParser.h"
#include "CachedAuthorizationService.h"
#include "AuthorizationWebService.h"
#include "PermissionParser.h"
#include "MemoryCache.h"
#include "../Resources/Orthanc/Plugins/OrthancPluginCppWrapper.h"

#include <Compatibility.h>  // For std::unique_ptr<>
#include <Logging.h>
#include <Toolbox.h>
#include <SerializationToolbox.h>
#include <EmbeddedResources.h>
#include "Enumerations.h"

#define ORTHANC_PLUGIN_NAME  "authorization"


// Configuration of the authorization plugin
static bool resourceTokensEnabled_ = false;
static bool userTokensEnabled_ = false;
static bool enableAuditLogs_ = false;
static std::unique_ptr<OrthancPlugins::IAuthorizationParser> authorizationParser_;
static std::unique_ptr<OrthancPlugins::IAuthorizationService> authorizationService_;
static std::unique_ptr<OrthancPlugins::PermissionParser> permissionParser_;
static std::set<std::string> uncheckedResources_;
static std::list<std::string> uncheckedFolders_;
static std::set<OrthancPlugins::Token> tokens_;
static std::set<OrthancPlugins::AccessLevel> uncheckedLevels_;


static std::string JoinStrings(const std::set<std::string>& values)
{
  std::string out;
  Orthanc::Toolbox::JoinStrings(out, values, "|");
  return out;
}


// For Orthanc prior to 1.12.2, we can not use the Forbidden error code and report the error ourselves
static void SendForbiddenError(const char* message, OrthancPluginRestOutput* output)
{
  OrthancPluginContext* context = OrthancPlugins::GetGlobalContext();

  OrthancPluginSendHttpStatus(context, output, 403, message, strlen(message));
}


static void MergeJson(Json::Value &a,
                      const Json::Value &b)
{
  // The semantics of this function is not generic enough to be included in the Orthanc framework
  if (!a.isObject() || !b.isObject())
  {
    return;
  }

  Json::Value::Members members = b.getMemberNames();

  for (size_t i = 0; i < members.size(); i++)
  {
    std::string key = members[i];

    if (!a[key].isNull() &&
        a[key].type() == Json::objectValue &&
        b[key].type() == Json::objectValue)
    {
      MergeJson(a[key], b[key]);
    }
    else
    {
      a[key] = b[key];
    }
  }
}


static const char* KEY_USER_DATA = "UserData";
static const char* KEY_USER_ID = "AuditLogsUserId";
static const char* KEY_PAYLOAD = "Payload";
static const char* KEY_BEFORE_TAGS = "TagsBeforeModification";

static bool GetUserIdFromUserData(std::string& userId, const Json::Value& payload)
{
  if (payload.isMember(KEY_USER_DATA) && payload[KEY_USER_DATA].isObject() 
    && payload[KEY_USER_DATA].isMember(KEY_USER_ID) && payload[KEY_USER_DATA][KEY_USER_ID].isString())
  {
    userId = payload[KEY_USER_DATA][KEY_USER_ID].asString();
    return true;
  }
  return false;
}

static void SetUserIdInUserdata(Json::Value& payload, const std::string& userId)
{
  if (!payload.isMember(KEY_USER_DATA))
  {
    payload[KEY_USER_DATA] = Json::objectValue;
  }
  payload[KEY_USER_DATA][KEY_USER_ID] = userId;
}

struct AuditLog
{
  std::string userId;
  OrthancPluginResourceType resourceType;
  std::string resourceId;
  std::string action;
  Json::Value logData;

  AuditLog(const std::string& userId,
           const OrthancPluginResourceType& resourceType,
           const std::string& resourceId,
           const std::string& action,
           const Json::Value& logData) :
    userId(userId),
    resourceType(resourceType),
    resourceId(resourceId),
    action(action),
    logData(logData)
  {
  }
};

static void RecordAuditLog(const std::string& userId,
                           const OrthancPluginResourceType& resourceType,
                           const std::string& resourceId,
                           const std::string& action,
                           const Json::Value& logData)
{
  if (!enableAuditLogs_)
  {
    // This function should not be called if audit logs are disabled
    throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
  }

#if ORTHANC_PLUGINS_VERSION_IS_ABOVE(1, 12, 9)
  // Audit logs are only available since Orthanc 1.12.9
  std::string serializedLogData;
  const void* logDataPtr = NULL;
  uint32_t logDataSize = 0;
  
  if (!logData.isNull())
  {
    Orthanc::Toolbox::WriteFastJson(serializedLogData, logData);
    logDataPtr = reinterpret_cast<const void*>(serializedLogData.c_str());
    logDataSize = serializedLogData.size();
  }

  OrthancPluginEmitAuditLog(OrthancPlugins::GetGlobalContext(),
                            ORTHANC_PLUGIN_NAME,
                            userId.c_str(),
                            resourceType,
                            resourceId.c_str(),
                            action.c_str(),
                            logDataPtr,
                            logDataSize);
#else
  LOG(WARNING) << "AUDIT-LOG: " << userId << " / " << action << " on " << resourceType << ":" << resourceId << ", " << logData.toStyledString();
#endif
}

static void RecordAuditLog(const AuditLog& auditLog)
{
  RecordAuditLog(auditLog.userId,
                 auditLog.resourceType,
                 auditLog.resourceId,
                 auditLog.action,
                 auditLog.logData);
}


static void RecordAuditLogs(const std::list<AuditLog>& auditLogs)
{
  for (std::list<AuditLog>::const_iterator it = auditLogs.begin(); it != auditLogs.end(); ++it)
  {
    RecordAuditLog(*it);
  }
}

class TokenAndValue
{
private:
  OrthancPlugins::Token token_;
  std::string value_;

public:
  TokenAndValue(const OrthancPlugins::Token& token, const std::string& value) :
    token_(token),
    value_(value)
  {
  }

  const OrthancPlugins::Token& GetToken() const
  {
    return token_;
  }

  const std::string& GetValue() const
  {
    return value_;
  }
};

bool HasAccessToAllLabels(const OrthancPlugins::IAuthorizationService::UserProfile& profile)
{
  return (profile.authorizedLabels.find("*") != profile.authorizedLabels.end());
}

bool HasAccessToSomeLabels(const OrthancPlugins::IAuthorizationService::UserProfile& profile)
{
  return (profile.authorizedLabels.size() > 0);
}

static bool HasAuthorizedLabelsForResource(bool& granted,
                                           const OrthancPlugins::IAuthorizationParser::AccessedResources& accesses,
                                           const OrthancPlugins::IAuthorizationService::UserProfile& profile)
{
  granted = false;

  if (HasAccessToAllLabels(profile))
  {
    granted = true;
    return true; // we could check labels
  }

  // Loop over all the accessed resources to ensure access is
  // granted to each of them
  for (OrthancPlugins::IAuthorizationParser::AccessedResources::const_iterator
      access = accesses.begin(); access != accesses.end(); ++access)
  {
    // Ignored the access levels that are unchecked
    // (cf. "UncheckedLevels" option)
    if (uncheckedLevels_.find(access->GetLevel()) == uncheckedLevels_.end())
    {
      std::string msg = std::string("Testing whether access to ") + OrthancPlugins::EnumerationToString(access->GetLevel()) + " \"" + access->GetOrthancId() + "\" is allowed wrt Labels for User '" + profile.name + "'";
      const std::set<std::string>& resourceLabels = access->GetLabels();
      std::set<std::string> authorizedResourceLabels;

      Orthanc::Toolbox::GetIntersection(authorizedResourceLabels, resourceLabels, profile.authorizedLabels);

      if (authorizedResourceLabels.size() == 0)
      {
        LOG(INFO) << msg << " -> not granted, no authorized labels";
        granted = false;
        return true; // we could check labels
      }
      else
      {
        LOG(INFO) << msg << " -> granted, at least one authorized labels";
        granted = true;
        return true; // we could check labels
      }
    }
  }

  // This method only checks if a resource is accessible thanks to its labels.  If we could not check it, we always return false !!
  return false; // we could not check labels
}


static bool CheckAuthorizedLabelsForResource(bool& granted,
                                             const std::string& uri,
                                             OrthancPluginHttpMethod method,
                                             const OrthancPlugins::AssociativeArray& getArguments,
                                             const OrthancPlugins::IAuthorizationService::UserProfile& profile)
{
  granted = false;

  if (HasAccessToAllLabels(profile))
  {
    granted = true;
    return true; // we could check labels
  }

  if (authorizationParser_.get() != NULL &&
      authorizationService_.get() != NULL)
  {
    // Parse the resources that are accessed through this URI
    OrthancPlugins::IAuthorizationParser::AccessedResources accesses;

    if (!authorizationParser_->Parse(accesses, uri, getArguments.GetMap()))
    {
      return false;  // Unable to parse this URI, we could not check labels
    }

    if (authorizationParser_->IsListOfResources(uri) && method == OrthancPluginHttpMethod_Get)
    {
      granted = false;  // if a user does not have access to all labels, he can not have access to a list of resources
      return true; // we could check labels
    }

    return HasAuthorizedLabelsForResource(granted, accesses, profile);
  }

  // This method only checks if a resource is accessible thanks to its labels.  If we could not check it, we always return false !!
  return false; // we could not check labels
}


static void GetAuthTokens(std::vector<TokenAndValue>& authTokens, 
                          uint32_t headersCount,
                          const char *const *headersKeys,
                          const char *const *headersValues,
                          uint32_t getArgumentsCount,
                          const char *const *getArgumentsKeys,
                          const char *const *getArgumentsValues)  // the tokens that are set in this request
{
  // Extract auth tokens from headers and url get arguments
  ////////////////////////////////////////////////////////////////

  OrthancPlugins::AssociativeArray headers(headersCount, headersKeys, headersValues, false);
  OrthancPlugins::AssociativeArray getArguments(getArgumentsCount, getArgumentsKeys, getArgumentsValues, true);

  for (std::set<OrthancPlugins::Token>::const_iterator token = tokens_.begin(); token != tokens_.end(); ++token)
  {
    std::string value;

    bool hasValue = false;
    switch (token->GetType())
    {
      case OrthancPlugins::TokenType_HttpHeader:
        hasValue = headers.GetValue(value, token->GetKey());
        break;

      case OrthancPlugins::TokenType_GetArgument:
        hasValue = getArguments.GetValue(value, token->GetKey());
        break;

      default:
        throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
    
    if (hasValue)
    {
      authTokens.push_back(TokenAndValue(*token, value));
    }
  }
}

static bool IsResourceAccessGranted(const std::vector<TokenAndValue>& authTokens,
                                    OrthancPluginHttpMethod method,
                                    const OrthancPlugins::AccessedResource& access)
{
  // Ignored the access levels that are unchecked
  // (cf. "UncheckedLevels" option)
  if (uncheckedLevels_.find(access.GetLevel()) == uncheckedLevels_.end())
  {
    std::string msg = std::string("Testing whether access to ") + OrthancPlugins::EnumerationToString(access.GetLevel()) + " \"" + access.GetOrthancId() + "\" is allowed with a resource token";
    LOG(INFO) << msg;

    bool granted = false;

    if (authTokens.empty())
    {
      unsigned int validity;  // ignored
      granted = authorizationService_->IsGrantedToAnonymousUser(validity, method, access);
    }
    else
    {
      // Loop over all the authorization tokens in the request until finding one that is granted
      for (size_t i = 0; i < authTokens.size(); ++i)
      {
        unsigned int validity;  // ignored
        if (authorizationService_->IsGranted(validity, method, access, authTokens[i].GetToken(), authTokens[i].GetValue()))
        {
          granted = true;
          break;
        }
      }
    }

    if (!granted)
    {
      LOG(INFO) << msg << " -> not granted";
      return false;
    }
    else
    {
      LOG(INFO) << msg << " -> granted";
      return true;
    }
  }

  return false;
}

static void RecordResourceAccessInternal(const OrthancPlugins::IAuthorizationService::UserProfile& profile,
                                         const OrthancPlugins::IAuthorizationParser::AccessedResources& accesses,
                                         const std::string& action,
                                         const Json::Value& logData)
{
  for (OrthancPlugins::IAuthorizationParser::AccessedResources::const_iterator it = accesses.begin(); it != accesses.end(); ++it)
  {
    if (it->GetLevel() == OrthancPlugins::AccessLevel_Study)
    {
      RecordAuditLog(profile.userId, OrthancPluginResourceType_Study, it->GetOrthancId(), action, logData);
    }
  }
}

static void RecordResourceAccess(const OrthancPlugins::IAuthorizationService::UserProfile& profile,
                                 const std::string& uri,
                                 OrthancPluginHttpMethod method,
                                 const OrthancPlugins::AssociativeArray& getArguments)
{
  // Identify the resource
  OrthancPlugins::IAuthorizationParser::AccessedResources accesses;

  if (authorizationParser_->Parse(accesses, uri, getArguments.GetMap()))
  {
    boost::smatch what;

    // Identify the action
    boost::regex archive("^/(patients|studies|series|instances)/([a-f0-9-]+)/(archive|media)$");
    
    if (boost::regex_match(uri, what, archive))
    {
      RecordResourceAccessInternal(profile, accesses, "download", Json::nullValue);
    }
  }

}

static bool TestRequiredPermissions(bool& hasUserRequiredPermissions, 
                                    const std::set<std::string>& requiredPermissions, 
                                    const OrthancPlugins::IAuthorizationService::UserProfile& profile,
                                    const std::string& msg, 
                                    const char* uri,
                                    OrthancPluginHttpMethod method,
                                    const OrthancPlugins::AssociativeArray& getArguments
                                    )
{
  if (authorizationService_->HasUserPermission(requiredPermissions, profile))
  {
    LOG(INFO) << msg << " -> granted to user '" << profile.name << "'";
    hasUserRequiredPermissions = true;

    // check labels permissions
    std::string msg2 = std::string("Testing whether user has the authorized_labels to access '") + uri + "'";

    bool hasAuthorizedLabelsForResource = false;
    if (CheckAuthorizedLabelsForResource(hasAuthorizedLabelsForResource, uri, method, getArguments, profile))
    {
      if (hasAuthorizedLabelsForResource)
      {
        LOG(INFO) << msg2 << " -> granted";

        if (enableAuditLogs_)
        {
          RecordResourceAccess(profile, uri, method, getArguments);
        }
      }
      else
      {
        LOG(INFO) << msg2 << " -> not granted";
        return false; // the labels for this resource prevents access -> stop checking now !
      }
    }
  }
  else
  {
    LOG(INFO) << msg << " -> not granted";
    hasUserRequiredPermissions = false;
  }
  
  return true;
}

static int32_t FilterHttpRequests(OrthancPluginHttpMethod method,
                                  const char *uri,
                                  const char *ip,
                                  uint32_t headersCount,
                                  const char *const *headersKeys,
                                  const char *const *headersValues,
                                  uint32_t getArgumentsCount,
                                  const char *const *getArgumentsKeys,
                                  const char *const *getArgumentsValues)
{
  try
  {
    // Allow GET accesses to unchecked resources/folders (usually static resources)
    ////////////////////////////////////////////////////////////////

    if (method == OrthancPluginHttpMethod_Get)
    {
      if (uncheckedResources_.find(uri) != uncheckedResources_.end())
      {
        return 1;
      }

      for (std::list<std::string>::const_iterator
             it = uncheckedFolders_.begin(); it != uncheckedFolders_.end(); ++it)
      {
        if (Orthanc::Toolbox::StartsWith(uri, *it))
        {
          return 1;
        }
      }
    }

    std::vector<TokenAndValue> authTokens;  // the tokens that are set in this request
    GetAuthTokens(authTokens, headersCount, headersKeys, headersValues, getArgumentsCount, getArgumentsKeys, getArgumentsValues);

    OrthancPlugins::AssociativeArray getArguments(getArgumentsCount, getArgumentsKeys, getArgumentsValues, true);

    // Based on the tokens, check if the user has access based on its permissions and the mapping between urls and permissions
    ////////////////////////////////////////////////////////////////
    bool hasUserRequiredPermissions = false;
    std::string userId;

    if (permissionParser_.get() != NULL &&
      authorizationService_.get() != NULL) 
    {
      std::set<std::string> requiredPermissions;
      std::string matchedPattern;
      if (permissionParser_->Parse(requiredPermissions, matchedPattern, method, uri))
      {
        if (authTokens.empty())
        {
          std::string msg = std::string("Testing whether anonymous user has any of the required permissions '") + JoinStrings(requiredPermissions) + "' required to match '" + matchedPattern + "'";

          OrthancPlugins::IAuthorizationService::UserProfile anonymousProfile;
          unsigned int validityNotUsed;
          authorizationService_->GetUserProfile(validityNotUsed, anonymousProfile, OrthancPlugins::Token(OrthancPlugins::TokenType_None, ""), "");
          userId = "anonymous";

          LOG(INFO) << msg; 
          if (!TestRequiredPermissions(hasUserRequiredPermissions, requiredPermissions, anonymousProfile, msg, uri, method, getArguments))
          {
            return 0; // the labels for this resource prevents access -> stop checking now !
          }

          // continue in order to check if there is a resource token that could grant access to the resource
        }
        else
        {
          for (size_t i = 0; i < authTokens.size(); ++i)
          {
            std::string msg = std::string("Testing whether user has the required permissions '") + JoinStrings(requiredPermissions) + "' based on the HTTP header '" + authTokens[i].GetToken().GetKey() + "' required to match '" + matchedPattern + "'";

            LOG(INFO) << msg;
            OrthancPlugins::IAuthorizationService::UserProfile profile;
            unsigned int validityNotUsed;
            authorizationService_->GetUserProfile(validityNotUsed, profile, authTokens[i].GetToken(), authTokens[i].GetValue());

            if (!profile.userId.empty())
            {
              userId = profile.userId;
            }

            if (!TestRequiredPermissions(hasUserRequiredPermissions, requiredPermissions, profile, msg, uri, method, getArguments))
            {
              return 0; // the labels for this resource prevents access -> stop checking now !
            }

          }
        }
      }
    }

    // no need to check for resource token if the user has access and if the labels checking has not prevented access
    if (hasUserRequiredPermissions)
    {
      return 1;
    }

    // If we get till here, it means that we have a resource token -> check that the resource is accessible
    ////////////////////////////////////////////////////////////////

    if (resourceTokensEnabled_ &&
        authorizationService_.get() != NULL)
    {
      // Parse the resources that are accessed through this URI
      OrthancPlugins::IAuthorizationParser::AccessedResources accesses;

      if (!authorizationParser_->Parse(accesses, uri, getArguments.GetMap()))
      {
        return 0;  // Unable to parse this URI
      }

      // Loop over all the accessed resources to ensure access is
      // granted to each of them
      int checkedResources = 0;
      int grantedResources = 0;

      for (OrthancPlugins::IAuthorizationParser::AccessedResources::const_iterator
             access = accesses.begin(); access != accesses.end(); ++access)
      {
        if (uncheckedLevels_.find(access->GetLevel()) == uncheckedLevels_.end())
        {
          checkedResources++;
          if (IsResourceAccessGranted(authTokens, method, *access))
          {
            grantedResources++;
          }  
        }
      }

      if (checkedResources > 0 && grantedResources == checkedResources)
      {
        return 1;
      }

      // Calling one of this "search" uri with a resource-token is authorized (since we override these routes in this plugin) but
      // the results will be empty.  We want to avoid 403 errors in OHIF when requesting prior studies.
      // TODO: In the future, we shall be able to return the studies that are authorized by the resource-token.
      if (strcmp(uri, "/dicom-web/studies") == 0 && method == OrthancPluginHttpMethod_Get)
      {
        return 1;
      }
    }
      
    // By default, forbid access to all the resources
    return 0;
  }
  catch (std::runtime_error& e)
  {
    LOG(ERROR) << e.what();
    return OrthancPluginErrorCode_Success;  // Ignore error
  }
  catch (Orthanc::OrthancException& e)
  {
    LOG(ERROR) << e.What();
    return OrthancPluginErrorCode_Success;  // Ignore error
  }
  catch (...)
  {
    LOG(ERROR) << "Unhandled internal exception";
    return OrthancPluginErrorCode_Success;  // Ignore error
  }
}

  
#if !ORTHANC_PLUGINS_VERSION_IS_ABOVE(1, 2, 1)
static int32_t FilterHttpRequestsFallback(OrthancPluginHttpMethod method,
                                          const char *uri,
                                          const char *ip,
                                          uint32_t headersCount,
                                          const char *const *headersKeys,
                                          const char *const *headersValues)
{
  // Fallback wrapper function for Orthanc <= 1.2.0, where the GET
  // arguments were not available in the HTTP filters
  return FilterHttpRequests(method, uri, ip,
                            headersCount, headersKeys, headersValues,
                            0, NULL, NULL);
}
#endif


static OrthancPluginErrorCode OnChangeCallback(OrthancPluginChangeType changeType,
                                               OrthancPluginResourceType resourceType,
                                               const char* resourceId)
{
  try
  {
    if (authorizationParser_.get() == NULL || !enableAuditLogs_)
    {
      return OrthancPluginErrorCode_Success;
    }

    switch(changeType)
    {
      case OrthancPluginChangeType_JobSuccess:
      {
        Json::Value job;
        if (OrthancPlugins::RestApiGet(job, std::string("/jobs/") + resourceId, false))
        {
          if (job["Type"].asString() == "ResourceModification")
          {
            Json::Value jobContent = job["Content"];
            std::string sourceResourceId = jobContent["ParentResources"][0].asString();
            std::string modifiedResourceId = jobContent["ID"].asString();
            OrthancPluginResourceType jobResourceType = OrthancPlugins::StringToResourceType(jobContent["Type"].asString().c_str());

            bool isAnonymization = jobContent.isMember("IsAnonymization") && jobContent["IsAnonymization"].asBool();
            // LOG(WARNING) << jobContent.toStyledString();

            std::string userId;
            if (GetUserIdFromUserData(userId, job))
            {
              {
                // attach a log to the source study
                Json::Value logData;
                logData["ModifiedResourceId"] = modifiedResourceId;
                logData["ModifiedResourceType"] = jobResourceType;

                RecordAuditLog(userId,
                                jobResourceType,
                                sourceResourceId,
                                (isAnonymization ? "success-anonymization-job" : "success-modification-job"),
                                logData);
              }
              
              // attach a log to the modified study
              if (sourceResourceId != modifiedResourceId)
              {
                Json::Value logData;
                logData["SourceResourceId"] = sourceResourceId;
                logData["SourceResourceType"] = jobResourceType;

                RecordAuditLog(userId,
                                jobResourceType,
                                modifiedResourceId,
                                (isAnonymization ? "new-study-from-anonymization-job" : "new-study-from-modification-job"), 
                                logData);
              }
            }            
          }

        }

        return OrthancPluginErrorCode_Success;
      }
      case OrthancPluginChangeType_JobFailure:
      {
        return OrthancPluginErrorCode_Success;
      }

      case OrthancPluginChangeType_Deleted:
      {
        switch (resourceType)
        {
          case OrthancPluginResourceType_Patient:
            authorizationParser_->Invalidate(Orthanc::ResourceType_Patient, resourceId);
            break;

          case OrthancPluginResourceType_Study:
            authorizationParser_->Invalidate(Orthanc::ResourceType_Study, resourceId);
            break;

          case OrthancPluginResourceType_Series:
            authorizationParser_->Invalidate(Orthanc::ResourceType_Series, resourceId);
            break;

          case OrthancPluginResourceType_Instance:
            authorizationParser_->Invalidate(Orthanc::ResourceType_Instance, resourceId);
            break;

          default:
            break;
        }
      }
      default:
        return OrthancPluginErrorCode_Success;    
    }
       
    return OrthancPluginErrorCode_Success;
  }
  catch (std::runtime_error& e)
  {
    LOG(ERROR) << e.what();
    return OrthancPluginErrorCode_Success;  // Ignore error
  }
  catch (Orthanc::OrthancException& e)
  {
    LOG(ERROR) << e.What();
    return OrthancPluginErrorCode_Success;  // Ignore error
  }
  catch (...)
  {
    LOG(ERROR) << "Unhandled internal exception";
    return OrthancPluginErrorCode_Success;  // Ignore error
  }
}

bool GetUserNameFromUserId(std::string& userName, 
                           const std::string& userId)
{
  unsigned int validity; // not used
  OrthancPlugins::IAuthorizationService::UserProfile profile;

  if (authorizationService_->GetUserProfileFromUserId(validity, profile, userId))
  {
    userName = profile.name;
    return true;
  }

  return false;
}

bool GetUserProfileInternal_(OrthancPlugins::IAuthorizationService::UserProfile& profile, 
                             const OrthancPlugins::AssociativeArray& headers,
                             const OrthancPlugins::AssociativeArray& getArguments,
                             bool ignoreEmptyValues)
{
  for (std::set<OrthancPlugins::Token>::const_iterator
          token = tokens_.begin(); token != tokens_.end(); ++token)
  {
    OrthancPlugins::IAuthorizationService::UserProfile tryProfile;

    std::string value;
    switch (token->GetType())
    {
      case OrthancPlugins::TokenType_HttpHeader:
        headers.GetValue(value, token->GetKey());
        break;

      case OrthancPlugins::TokenType_GetArgument:
        getArguments.GetValue(value, token->GetKey());
        break;

      default:
        throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
    
    if (ignoreEmptyValues && value.empty())
    {
      continue;
    }

    unsigned int validity; // not used
    if (authorizationService_->GetUserProfile(validity, tryProfile, *token, value))
    {
      profile = tryProfile;
      return true;
    }
  }

  return false;
}


bool GetUserProfileInternal(OrthancPlugins::IAuthorizationService::UserProfile& profile, const OrthancPluginHttpRequest* request)
{
  OrthancPlugins::AssociativeArray headers
    (request->headersCount, request->headersKeys, request->headersValues, false);

  OrthancPlugins::AssociativeArray getArguments
    (request->getCount, request->getKeys, request->getValues, true);

  // Loop over all the authorization tokens stored in the HTTP
  // headers, until finding one that is granted.
  // But, first process only the tokens with a value to avoid getting identified as anonymous too fast !
  if (GetUserProfileInternal_(profile, headers, getArguments, true))
  {
    return true;
  }

  return GetUserProfileInternal_(profile, headers, getArguments, false);
}

void AdjustToolsFindQueryLabels(Json::Value& query, const OrthancPlugins::IAuthorizationService::UserProfile& profile)
{
  std::set<std::string> labelsToFind;
  std::string labelsConstraint = "Invalid";

  if (query.isMember("Labels") && query.isMember("LabelsConstraint"))
  {
    Orthanc::SerializationToolbox::ReadSetOfStrings(labelsToFind, query, "Labels");
    labelsConstraint = Orthanc::SerializationToolbox::ReadString(query, "LabelsConstraint");
  }
  else if (query.isMember("Labels") || query.isMember("LabelsConstraint"))
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_ForbiddenAccess, "Auth plugin: unable to transform tools/find query, both 'Labels' and 'LabelsConstraint' must be defined together if one of them is defined.");
  }

  if (!HasAccessToSomeLabels(profile))
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_ForbiddenAccess, "Auth plugin: unable to call tools/find when the user does not have access to any labels.");
  }
  else if (profile.authorizedLabels.size() > 0)
  {
    // if the user has access to all labels: no need to transform the tools/find body, we keep it as is
    if (!HasAccessToAllLabels(profile))
    { // the user does not have access to all labels -> transform the tools/find body

      if (labelsToFind.size() == 0)
      {
        if (profile.authorizedLabels.size() > 0)
        {
          query.removeMember("Labels");
          Orthanc::SerializationToolbox::WriteSetOfStrings(query, profile.authorizedLabels, "Labels");
          query["LabelsConstraint"] = "Any";
        }
      }
      else if (labelsConstraint == "All")
      {
        if (profile.authorizedLabels.size() > 0)
        {
          if (!Orthanc::Toolbox::IsSetInSet(labelsToFind, profile.authorizedLabels))
          {
            throw Orthanc::OrthancException(Orthanc::ErrorCode_ForbiddenAccess, "Auth plugin: unable to transform tools/find query with 'All' labels constraint when the user does not have access to all listed labels.");
          }
        }
      }
      else if (labelsConstraint == "Any")
      {
        if (profile.authorizedLabels.size() > 0)
        {
          std::set<std::string> newLabelsToFind;
          Orthanc::Toolbox::GetIntersection(newLabelsToFind, labelsToFind, profile.authorizedLabels);

          if (newLabelsToFind.size() == 0)
          {
            throw Orthanc::OrthancException(Orthanc::ErrorCode_ForbiddenAccess, "Auth plugin: unable to transform tools/find query with 'Any' labels constraint when none of the labels to find is authorized for the user.");                
          }

          query.removeMember("Labels");
          Orthanc::SerializationToolbox::WriteSetOfStrings(query, newLabelsToFind, "Labels");
        }
      }
      else if (labelsConstraint == "None")
      {
        if (profile.authorizedLabels.size() > 0)
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_ForbiddenAccess, "Auth plugin: unable to transform tools/find query with 'None' labels constraint.");
        }
      }
    }
  }
}

bool GetStudyInstanceUIDFromQuery(std::string& studyInstanceUID, const Json::Value& body)
{

  if (!body.isMember("Query"))
  {
    return false;
  }

  if (body["Query"].isMember("StudyInstanceUID"))
  {
    studyInstanceUID = body["Query"]["StudyInstanceUID"].asString();
  }
  else if (body["Query"].isMember("0020,000d"))
  {
    studyInstanceUID = body["Query"]["0020,000d"].asString();
  }
  else if (body["Query"].isMember("0020,000D"))
  {
    studyInstanceUID = body["Query"]["0020,000D"].asString();
  }
  else if (body["Query"].isMember("0020000D"))
  {
    studyInstanceUID = body["Query"]["0020000D"].asString();
  }
  else
  {
    return false;
  }

  return true;
}

void GetStudyOrthancIdFromStudyInstanceUID(std::vector<std::string>& studyOrthancIds, const std::string& studyInstanceUID)
{
  studyOrthancIds.clear();
  Json::Value response;
  if (OrthancPlugins::RestApiPost(response, "/tools/lookup", studyInstanceUID, false))
  {
    for (Json::ArrayIndex i = 0; i < response.size(); ++i)
    {
      if (response[i]["Type"] == "Study")
      {
        studyOrthancIds.push_back(response[i]["ID"].asString());
      }
    }
  }
}

void FilterAuthorizedLabels(Json::Value& labels, const OrthancPlugins::IAuthorizationService::UserProfile& profile)
{
  if (HasAccessToAllLabels(profile))
  {
    return;
  }
  else
  {
    std::set<std::string> inLabelsSet;
    std::set<std::string> outLabelsSet;

    Orthanc::SerializationToolbox::ReadSetOfStrings(inLabelsSet, labels);

    Orthanc::Toolbox::GetIntersection(outLabelsSet, inLabelsSet, profile.authorizedLabels);

    Orthanc::SerializationToolbox::WriteSetOfStrings(labels, outLabelsSet);
  }
}


void FilterLabelsInResourceObject(Json::Value& resource, const OrthancPlugins::IAuthorizationService::UserProfile& profile)
{
  if (resource.isMember("Labels"))
  {
    FilterAuthorizedLabels(resource["Labels"], profile);
  }
}


void FilterLabelsInResourceArray(Json::Value& resources, const OrthancPlugins::IAuthorizationService::UserProfile& profile)
{
  for (Json::ArrayIndex i = 0; i < resources.size(); ++i)
  {
    if (resources[i].isObject())
    {
      FilterLabelsInResourceObject(resources[i], profile);
    }
  }
}


void ToolsFindOrCountResources(OrthancPluginRestOutput* output,
                               const char* /*url*/,
                               const OrthancPluginHttpRequest* request,
                               const char* nativeUrl,
                               bool filterLabelsInResponse)
{
  OrthancPluginContext* context = OrthancPlugins::GetGlobalContext();

  try
  {
    if (request->method != OrthancPluginHttpMethod_Post)
    {
      OrthancPluginSendMethodNotAllowed(context, output, "POST");
    }
    else
    {
      // The filtering to this route is performed by this plugin as it is done for any other route before we get here.

      Json::Value query;
      if (!OrthancPlugins::ReadJson(query, request->body, request->bodySize))
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat, "A JSON payload was expected");
      }

      // If the logged in user has restrictions on the labels he can access, modify the tools/find payload before reposting it to Orthanc
      OrthancPlugins::IAuthorizationService::UserProfile profile;
      if (GetUserProfileInternal(profile, request) && HasAccessToSomeLabels(profile))
      {
        Orthanc::ResourceType queryLevel = Orthanc::StringToResourceType(query["Level"].asString().c_str());

        if (queryLevel == Orthanc::ResourceType_Study)
        {
          AdjustToolsFindQueryLabels(query, profile);
        }
        else if (queryLevel == Orthanc::ResourceType_Patient && !HasAccessToAllLabels(profile))
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_ForbiddenAccess, "Auth plugin: unable to call tools/find at Patient level when the user does not have access to ALL labels.");
        }
        else if (queryLevel == Orthanc::ResourceType_Series || queryLevel == Orthanc::ResourceType_Instance)
        {
          std::string studyInstanceUID;

          if (!HasAccessToAllLabels(profile)) // no need to adjust anything if the user has access to all labels
          {
            if (!GetStudyInstanceUIDFromQuery(studyInstanceUID, query))
            {
              throw Orthanc::OrthancException(Orthanc::ErrorCode_ForbiddenAccess, "Auth plugin: unable to call tools/find at Series or Instance level when the user does not have access to ALL labels or when there is no StudyInstanceUID in the query.");
            }

            // since this is a series/instance find, make sure the user has access to the parent study
            std::vector<std::string> studyOrthancIds;
            GetStudyOrthancIdFromStudyInstanceUID(studyOrthancIds, studyInstanceUID);

            if (studyOrthancIds.size() != 1)
            {
              throw Orthanc::OrthancException(Orthanc::ErrorCode_ForbiddenAccess, "Auth plugin: when using tools/find at Series or Instance level, unable to get the orthanc ID of StudyInstanceUID specified in the query. Found " + boost::lexical_cast<std::string>(studyOrthancIds.size()) + " orthanc studies with this StudyInstanceUID");          
            }

            bool granted = false;
            OrthancPlugins::IAuthorizationParser::AccessedResources accessedResources;
            authorizationParser_->AddDicomStudy(accessedResources, studyInstanceUID);

            if (!HasAuthorizedLabelsForResource(granted, accessedResources, profile))
            {
              throw Orthanc::OrthancException(Orthanc::ErrorCode_ForbiddenAccess, "Auth plugin: when using tools/find at Series or Instance level, unable to check resource access based on the authorized_labels.");
            }

            if (!granted)
            {
              throw Orthanc::OrthancException(Orthanc::ErrorCode_ForbiddenAccess, "Auth plugin: when using tools/find at Series or Instance level, the user shall have access to the parent study.");
            }
          }
        }
      }
      else // anonymous user profile or resource token
      {
        std::string studyInstanceUID;

        // If anonymous user profile, it might be a resource token e.g accessing /dicom-web/studies/.../metadata 
        // -> extract the StudyInstanceUID from the query and send the token for validation to the auth-service
        // If there is no StudyInstanceUID, then, return an empty list
        if (!GetStudyInstanceUIDFromQuery(studyInstanceUID, query))
        {
          // If there is no StudyInstaceUID, this might still be a call to /dicom-web/studies?PatientID=... e.g. from OHIF
          // in this case, let's complement the query to filter against the StudyInstanceUIDs from the resource token and
          // "add" &StudyInstanceUID=1.2|1.3|1.4 in the query if there are multiple studies in the resource token

          std::vector<TokenAndValue> authTokens;  // the tokens that are set in this request
          GetAuthTokens(authTokens, request->headersCount, request->headersKeys, request->headersValues, request->getCount, request->getKeys, request->getValues);

          for (std::vector<TokenAndValue>::const_iterator it = authTokens.begin(); it != authTokens.end(); ++it)
          {
            OrthancPlugins::IAuthorizationService::DecodedToken decodedToken;
            if (authorizationService_->DecodeToken(decodedToken,
                                                   it->GetToken().GetKey(),
                                                   it->GetValue()))
            {
              if (decodedToken.resourcesDicomIds.size() > 0)
              {
                std::string joinedStudyInstanceUids;
                Orthanc::Toolbox::JoinStrings(joinedStudyInstanceUids, decodedToken.resourcesDicomIds, "|");
                
                LOG(WARNING) << "Auth plugin: adding StudyInstanceUID constrains based on the resources/dicom-uid in the token.";
                // LOG(INFO) << joinedStudyInstanceUids;

                query["Query"]["StudyInstanceUID"] = joinedStudyInstanceUids;

                Json::Value result;
                if (OrthancPlugins::RestApiPost(result, nativeUrl, query, false))
                {
                  OrthancPlugins::AnswerJson(result, output);
                  return;
                }
              }
            }
            else
            {
              throw Orthanc::OrthancException(Orthanc::ErrorCode_ForbiddenAccess, "Auth plugin: unable to call tools/find when the user does not have access to any labels and if there is no StudyInstanceUID in the query and the auth-service does not implement /tokens/decode.");
            }
          }

          // old code prior to 0.9.2: 
          throw Orthanc::OrthancException(Orthanc::ErrorCode_ForbiddenAccess, "Auth plugin: unable to call tools/find when the user does not have access to any labels and if there is no StudyInstanceUID in the query or in the resource token.");
        }

        std::vector<std::string> studyOrthancIds;
        GetStudyOrthancIdFromStudyInstanceUID(studyOrthancIds, studyInstanceUID);

        if (studyOrthancIds.size() != 1)
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_ForbiddenAccess, "Auth plugin: when using tools/find with a resource token, unable to get the orthanc ID of StudyInstanceUID specified in the query. Found " + boost::lexical_cast<std::string>(studyOrthancIds.size()) + " orthanc studies with this StudyInstanceUID");          
        }

        std::vector<TokenAndValue> authTokens;  // the tokens that are set in this request
        GetAuthTokens(authTokens, request->headersCount, request->headersKeys, request->headersValues, request->getCount, request->getKeys, request->getValues);

        std::set<std::string> labels;
        OrthancPlugins::AccessedResource accessedResource(Orthanc::ResourceType_Study, studyOrthancIds[0], studyInstanceUID, labels);
        if (!IsResourceAccessGranted(authTokens, request->method, accessedResource))
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_ForbiddenAccess, "Auth plugin: when using tools/find with a resource token, the resource must grant access to the StudyInstanceUID specified in the query.");
        }

      }

      Json::Value result;

      if (OrthancPlugins::RestApiPost(result, nativeUrl, query, false))
      {
        if (filterLabelsInResponse)
        {
          FilterLabelsInResourceArray(result, profile);
        }
        OrthancPlugins::AnswerJson(result, output);
      }

    }

  }
  catch(const Orthanc::OrthancException& e)
  {
    // this error is not yet supported in Orthanc 1.12.1
    if (e.GetErrorCode() == Orthanc::ErrorCode_ForbiddenAccess && !OrthancPlugins::CheckMinimalOrthancVersion(1, 12, 2))
    {
      SendForbiddenError(e.GetDetails(), output);
    }
    else
    {
      throw;
    }
  }
}

void ToolsFind(OrthancPluginRestOutput* output,
               const char* url,
               const OrthancPluginHttpRequest* request)
{
  ToolsFindOrCountResources(output, url, request, "/tools/find", true);
}

void ToolsCountResources(OrthancPluginRestOutput* output,
                         const char* url,
                         const OrthancPluginHttpRequest* request)
{
  ToolsFindOrCountResources(output, url, request, "/tools/count-resources", false);
}

void UploadInstancesWithAuditLogs(OrthancPluginRestOutput* output,
                                  const char* url,
                                  const OrthancPluginHttpRequest* request)
{
  OrthancPluginContext* context = OrthancPlugins::GetGlobalContext();

  // always forward to core
  OrthancPlugins::RestApiClient coreApi(url, request);
  coreApi.ExecuteAndForwardAnswer(context, output);

  if (request->method == OrthancPluginHttpMethod_Post)
  {
    OrthancPlugins::IAuthorizationService::UserProfile profile;
    Json::Value coreResponse;

    if (GetUserProfileInternal(profile, request) && coreApi.GetAnswerJson(coreResponse))
    {
      RecordAuditLog(profile.userId, OrthancPluginResourceType_Study, coreResponse["ParentStudy"].asString(), "uploaded-instance", coreResponse["ID"].asString());
    }
    else
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ForbiddenAccess, "Auth plugin: no user profile found, unable to handle POST to /instances with audit logs enabled.");
    }
  }
}


void ModifyAnonymizeWithAuditLogs(OrthancPluginRestOutput* output,
                                  const char* url,
                                  const OrthancPluginHttpRequest* request,
                                  bool isModification)
{
  OrthancPluginContext* context = OrthancPlugins::GetGlobalContext();
  OrthancPluginResourceType resourceType = OrthancPlugins::StringToResourceType(request->groups[0]);
  std::string resourceId = request->groups[1];

  OrthancPlugins::RestApiClient coreApi(url, request);

  Json::Value payload;
  if (!OrthancPlugins::ReadJson(payload, request->body, request->bodySize))
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat, "A JSON payload was expected");
  }

  // Either there is a userId in UserData or the request comes from a user with profile
  OrthancPlugins::IAuthorizationService::UserProfile profile;
  std::string userId;

  // LOG(WARNING) << payload.toStyledString();

  if (GetUserProfileInternal(profile, request) && !profile.userId.empty())
  {
    userId = profile.userId;  
  } 
  else if (!GetUserIdFromUserData(userId, payload))
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_ForbiddenAccess, "Auth plugin: no user profile or UserData found, unable to handle anonymize/modify with audit logs enabled.");
  }

  if ((payload.isMember("Synchronous") && !payload["Synchronous"].asBool())
    || (payload.isMember("Asynchronous") && !payload["Asynchronous"].asBool()))
  {
    Json::Value logData;
    logData[KEY_PAYLOAD] = payload;
    
    // add UserData to the job payload to know who has modified the data.  The handling of the log will then happen in the OnChange handler
    SetUserIdInUserdata(payload, userId);
    std::string modifiedPayload = payload.toStyledString();
    coreApi.SetRequestBody(modifiedPayload);

    if (isModification)
    {
      // log the tags before modification (but not for anonymizations)
      Json::Value resourceBefore;
      if (resourceType == OrthancPluginResourceType_Study && OrthancPlugins::RestApiGet(resourceBefore, "/studies/" + resourceId, false))
      {
        Json::Value studyTagsBefore = resourceBefore["MainDicomTags"];
        Json::Value patientTagsBefore = resourceBefore["PatientMainDicomTags"];
        MergeJson(studyTagsBefore, patientTagsBefore);

        logData[KEY_BEFORE_TAGS] = studyTagsBefore;
      }
      else
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError, "Auth plugin: TODO: unable to handle anonymize/modify other levels than studies with audit logs enabled.");
      }
    }

    // in any case, record that this resource is being modified/anonymized and record the payload
    RecordAuditLog(userId, 
                   resourceType, 
                   resourceId, 
                   (isModification ? "start-modification-job" : "start-anonymization-job"), 
                   logData);

    if (coreApi.Execute())
    {
      coreApi.ForwardAnswer(context, output);
    }
  }
  else
  {
    Json::Value coreResponse;

    // if it is synchronous, perform the modification and record the log directly
    if (coreApi.Execute())
    {
      coreApi.ForwardAnswer(context, output);
    }
    
    if (coreApi.GetAnswerJson(coreResponse))
    {
      LOG(WARNING) << "TODO AUDIT-LOG synchronous modification " << coreResponse.toStyledString(); // TODO 
    }
  }
}

void BulkModifyAnonymizeWithAuditLogs(OrthancPluginRestOutput* output,
                                      const char* url,
                                      const OrthancPluginHttpRequest* request)
{
  throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented, "Auth plugin: Not implemented: Currently unable to perform bulk modification/anonymization with audit logs enabled.");
}


void ModifyWithAuditLogs(OrthancPluginRestOutput* output,
                         const char* url,
                         const OrthancPluginHttpRequest* request)
{
  ModifyAnonymizeWithAuditLogs(output, url, request, true);
}

void AnonymizeWithAuditLogs(OrthancPluginRestOutput* output,
                            const char* url,
                            const OrthancPluginHttpRequest* request)
{
  ModifyAnonymizeWithAuditLogs(output, url, request, false);
}

void LabelWithAuditLogs(OrthancPluginRestOutput* output,
                        const char* url,
                        const OrthancPluginHttpRequest* request)
{
  OrthancPluginContext* context = OrthancPlugins::GetGlobalContext();
  OrthancPluginResourceType resourceType = OrthancPlugins::StringToResourceType(request->groups[0]);
  std::string resourceId = request->groups[1];
  std::string label = request->groups[2];

  OrthancPlugins::RestApiClient coreApi(url, request);

  if (!enableAuditLogs_ || request->method == OrthancPluginHttpMethod_Get)
  {
    coreApi.ExecuteAndForwardAnswer(context, output);
    return;
  }
  else
  {
    OrthancPlugins::IAuthorizationService::UserProfile profile;
    std::string userId;

    if (GetUserProfileInternal(profile, request) && !profile.userId.empty())
    {
      userId = profile.userId;  
    }
    else
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ForbiddenAccess, "Auth plugin: no user profile or UserData found, unable to delete/put label with audit logs enabled.");
    }
    
    std::string action;
    if (request->method == OrthancPluginHttpMethod_Delete)
    {
      action = "deleted-label";
    }
    else if (request->method == OrthancPluginHttpMethod_Put)
    {
      action = "added-label";
    }
    
    if (coreApi.Execute())
    {
      RecordAuditLog(userId, 
                     resourceType, 
                     resourceId, 
                     action, 
                     label);
      
      coreApi.ForwardAnswer(context, output);
      return;
    }
  }
}


void GetAuditLogs(OrthancPluginRestOutput* output,
                  const char* url,
                  const OrthancPluginHttpRequest* request)
{
  OrthancPluginContext* context = OrthancPlugins::GetGlobalContext();

  bool isOutputCsv = false;

  OrthancPlugins::HttpHeaders requestHeaders;
  OrthancPlugins::GetHttpHeaders(requestHeaders, request);

  OrthancPlugins::GetArguments getArguments;
  OrthancPlugins::GetGetArguments(getArguments, request);

  if (getArguments.find("format") != getArguments.end())
  {
    isOutputCsv = getArguments["format"] == "csv";
  }
  
  if (!isOutputCsv && (requestHeaders.find("accept") != requestHeaders.end()))
  {
    std::string acceptHeader = requestHeaders["accept"];
    Orthanc::Toolbox::ToLowerCase(acceptHeader);
    
    isOutputCsv = acceptHeader.find("text/csv") != std::string::npos;
  }

  OrthancPlugins::RestApiClient coreApi("/plugins/postgresql/audit-logs", request);
  coreApi.SetAfterPlugins(true);
  coreApi.SetRequestHeader("Accept", "application/json"); // the postgresql plugin only knows about the json format

  if (request->method != OrthancPluginHttpMethod_Get)
  {
    OrthancPluginSendMethodNotAllowed(context, output, "GET");
    return;
  }

  Json::Value response;

  if (coreApi.Execute() && coreApi.GetAnswerJson(response))
  {
    // transform the response: replace user-id by user-name
    for (Json::ArrayIndex i = 0; i < response.size(); ++i)
    {
      const std::string& userId = response[i]["UserId"].asString();
      std::string userName;
      if (GetUserNameFromUserId(userName, userId))
      {
        response[i]["UserName"] = userName;
      }
      else
      {
        response[i]["UserName"] = userId;
      }
    }

    if (!isOutputCsv)
    {
      OrthancPlugins::AnswerJson(response, output);
    }
    else
    {
      std::vector<std::string> lines;

      std::vector<std::string> firstLineColumns;
      firstLineColumns.push_back("Timestamp");
      firstLineColumns.push_back("UserId");
      firstLineColumns.push_back("UserName");
      firstLineColumns.push_back("ResourceId");
      firstLineColumns.push_back("Action");
      firstLineColumns.push_back("LogData");

      std::string firstLine;
      Orthanc::Toolbox::JoinStrings(firstLine, firstLineColumns,";");
      lines.push_back(firstLine);

      for (Json::ArrayIndex i = 0; i < response.size(); ++i)
      {
        std::vector<std::string> lineColumns;
        std::string line;

        const Json::Value& log = response[i];
        lineColumns.push_back(log["Timestamp"].asString());
        lineColumns.push_back(log["UserId"].asString());
        lineColumns.push_back(log["UserName"].asString());
        lineColumns.push_back(log["ResourceId"].asString());
        lineColumns.push_back(log["Action"].asString());
        
        std::string logData;
        Orthanc::Toolbox::WriteFastJson(logData, log["LogData"]);
        boost::replace_all(logData, "\n", "");
        lineColumns.push_back(logData);

        Orthanc::Toolbox::JoinStrings(line, lineColumns,";");
        lines.push_back(line);
      }
      
      std::string csv;
      Orthanc::Toolbox::JoinStrings(csv, lines, "\n");

      OrthancPluginSetHttpHeader(context, output, "Content-disposition", "filename=\"audit-logs.csv\"");
      OrthancPlugins::AnswerString(csv, "text/csv", output);
    }
  }
}


OrthancPluginResourceType IdentifyResourceType(const std::string& resourceId)
{
  Json::Value v;

  if (OrthancPlugins::RestApiGet(v, "/studies/" + resourceId, false))
  {
    return OrthancPluginResourceType_Study;
  }
  if (OrthancPlugins::RestApiGet(v, "/patients/" + resourceId, false))
  {
    return OrthancPluginResourceType_Patient;
  }
  if (OrthancPlugins::RestApiGet(v, "/series/" + resourceId, false))
  {
    return OrthancPluginResourceType_Series;
  }
  if (OrthancPlugins::RestApiGet(v, "/instances/" + resourceId, false))
  {
    return OrthancPluginResourceType_Instance;
  }

  return OrthancPluginResourceType_None;
}


void GetResourceDeletionAuditLogs(std::list<AuditLog>& auditLogs,
                                  OrthancPluginResourceType resourceType,
                                  const std::string& resourceId,
                                  const OrthancPluginHttpRequest* request)
{
  OrthancPlugins::IAuthorizationService::UserProfile profile;
  std::string userId;

  if (GetUserProfileInternal(profile, request) && !profile.userId.empty())
  {
    userId = profile.userId;  
  }
  else
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_ForbiddenAccess, "Auth plugin: no user profile or UserData found, unable to delete a resource with audit logs enabled.");
  }
  
  Json::Value logData;

  switch (resourceType)
  {
    case OrthancPluginResourceType_Patient:
      {
        auditLogs.push_back(AuditLog(userId, resourceType, resourceId, "deleted-patient", logData));

        // find all child studies and add the log to each of them
        Json::Value patient;
        if (OrthancPlugins::RestApiGet(patient, "/patients/" + resourceId, false))
        {
          for (Json::ArrayIndex i = 0; i < patient["Studies"].size(); ++i)
          {
            auditLogs.push_back(AuditLog(userId, OrthancPluginResourceType_Study, patient["Studies"][i].asString(), "deleted-parent-patient", Json::nullValue));
          }
        }
      
      }; break;
    case OrthancPluginResourceType_Study:
      {
        auditLogs.push_back(AuditLog(userId, resourceType, resourceId, "deleted-study", logData));
      }; break;
    case OrthancPluginResourceType_Series:
      {
        auditLogs.push_back(AuditLog(userId, resourceType, resourceId, "deleted-series", logData));

        // add a log in the parent study 
        Json::Value parentStudy;
        if (OrthancPlugins::RestApiGet(parentStudy, "/series/" + resourceId + "/study", false))
        {
          auditLogs.push_back(AuditLog(userId, OrthancPluginResourceType_Study, parentStudy["ID"].asString(), "deleted-child-series", Json::nullValue));
        }
      }; break;
    case OrthancPluginResourceType_Instance:
      {
        auditLogs.push_back(AuditLog(userId, resourceType, resourceId, "deleted-instance", logData));

        // add a log in the parent study 
        Json::Value parentStudy;
        if (OrthancPlugins::RestApiGet(parentStudy, "/instances/" + resourceId + "/study", false))
        {
          auditLogs.push_back(AuditLog(userId, OrthancPluginResourceType_Study, parentStudy["ID"].asString(), "deleted-child-instance", Json::nullValue));
        }
      }; break;
    default:
      throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
  }
}

void DeleteResourceWithAuditLogs(OrthancPluginRestOutput* output,
                                 const char* url,
                                 const OrthancPluginHttpRequest* request)
{
  assert(request->method == OrthancPluginHttpMethod_Delete);

  OrthancPluginContext* context = OrthancPlugins::GetGlobalContext();
  OrthancPluginResourceType resourceType = OrthancPlugins::StringToResourceType(request->groups[0]);
  std::string resourceId = request->groups[1];
  
  std::list<AuditLog> auditLogs;
  GetResourceDeletionAuditLogs(auditLogs, resourceType, resourceId, request);

  OrthancPlugins::RestApiClient coreApi(url, request);
  
  if (coreApi.Execute())
  {
    RecordAuditLogs(auditLogs);

    coreApi.ForwardAnswer(context, output);
    return;
  }
}


void BulkDeleteWithAuditLogs(OrthancPluginRestOutput* output,
                             const char* url,
                             const OrthancPluginHttpRequest* request)
{
  OrthancPluginContext* context = OrthancPlugins::GetGlobalContext();

  if (request->method != OrthancPluginHttpMethod_Post)
  {
    OrthancPluginSendMethodNotAllowed(context, output, "POST");
  }

  Json::Value payload;
  if (!OrthancPlugins::ReadJson(payload, request->body, request->bodySize) || !payload.isMember("Resources"))
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat, "A JSON payload was expected");
  }

  std::list<AuditLog> auditLogs;

  for (Json::ArrayIndex i = 0; i < payload["Resources"].size(); ++i)
  {
    std::string resourceId = payload["Resources"][i].asString();
    OrthancPluginResourceType resourceType = IdentifyResourceType(resourceId);
    GetResourceDeletionAuditLogs(auditLogs, resourceType, resourceId, request);
  }

  OrthancPlugins::RestApiClient coreApi(url, request);
  
  if (coreApi.Execute())
  {
    RecordAuditLogs(auditLogs);

    coreApi.ForwardAnswer(context, output);
    return;
  }

}


void ToolsLabels(OrthancPluginRestOutput* output,
                 const char* /*url*/,
                 const OrthancPluginHttpRequest* request)
{
  OrthancPluginContext* context = OrthancPlugins::GetGlobalContext();

  try
  {
    if (request->method != OrthancPluginHttpMethod_Get)
    {
      OrthancPluginSendMethodNotAllowed(context, output, "GET");
    }
    else
    {
      // The filtering to this route is performed by this plugin as it is done for any other route before we get here

      // If the logged in user has restrictions on the labels he can access, modify the tools/labels response before answering
      OrthancPlugins::IAuthorizationService::UserProfile profile;
      if (GetUserProfileInternal(profile, request))
      {
        if (!HasAccessToSomeLabels(profile))
        {
          Json::Value emptyLabels;
          OrthancPlugins::AnswerJson(emptyLabels, output);
          return;
        }

        Json::Value jsonLabels;
        if (OrthancPlugins::RestApiGet(jsonLabels, "/tools/labels", false))
        {
          FilterAuthorizedLabels(jsonLabels, profile);
          OrthancPlugins::AnswerJson(jsonLabels, output);
        }
      }
      else
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_ForbiddenAccess, "Auth plugin: no user profile found, access to tools/labels is forbidden.");
      }
    }
  }
  catch(const Orthanc::OrthancException& e)
  {
    // this error is not yet supported in Orthanc 1.12.1
    if (e.GetErrorCode() == Orthanc::ErrorCode_ForbiddenAccess && !OrthancPlugins::CheckMinimalOrthancVersion(1, 12, 2))
    {
      SendForbiddenError(e.GetDetails(), output);
    }
    else
    {
      throw;
    }
  }
}

typedef void (*JsonLabelsFilter) (Json::Value& labels, 
                                  const OrthancPlugins::IAuthorizationService::UserProfile& profile);


// calls the core api and filter the "Labels" in the response
void FilterLabelsFromGetCoreUrl(OrthancPluginRestOutput* output,
                                const char* url,
                                const OrthancPluginHttpRequest* request,
                                JsonLabelsFilter jsonLabelsFilter)
{
  OrthancPluginContext* context = OrthancPlugins::GetGlobalContext();

  if (request->method != OrthancPluginHttpMethod_Get)
  {
    OrthancPlugins::RestApiClient coreApi(url, request);
    coreApi.ExecuteAndForwardAnswer(context, output);
  }
  else
  {
    // The filtering to this route is performed by this plugin as it is done for any other route before we get here so we don't care about authorization here.

    // If the logged in user has restrictions on the labels he can access, modify the "Labels" field in the response before answering
    OrthancPlugins::IAuthorizationService::UserProfile profile;
    GetUserProfileInternal(profile, request);

    Json::Value response;

    OrthancPlugins::RestApiClient coreApi(url, request);

    if (coreApi.Execute() && coreApi.GetAnswerJson(response))
    {
      jsonLabelsFilter(response, profile);
      OrthancPlugins::AnswerJson(response, output);
    }
  }
}


void FilterLabelsFromSingleResource(OrthancPluginRestOutput* output,
                                    const char* url,
                                    const OrthancPluginHttpRequest* request)
{
  FilterLabelsFromGetCoreUrl(output, url, request, FilterLabelsInResourceObject);
}

void GetOrDeleteMainResource(OrthancPluginRestOutput* output,
                                    const char* url,
                                    const OrthancPluginHttpRequest* request)
{
  if (enableAuditLogs_ && request->method == OrthancPluginHttpMethod_Delete)
  {
    DeleteResourceWithAuditLogs(output, url, request);
  }
  else
  {
    FilterLabelsFromSingleResource(output, url, request);
  }
}

void FilterLabelsFromResourceList(OrthancPluginRestOutput* output,
                                    const char* url,
                                    const OrthancPluginHttpRequest* request)
{
  FilterLabelsFromGetCoreUrl(output, url, request, FilterLabelsInResourceArray);
}

void FilterLabelsFromResourceLabels(OrthancPluginRestOutput* output,
                                    const char* url,
                                    const OrthancPluginHttpRequest* request)
{
  FilterLabelsFromGetCoreUrl(output, url, request, FilterAuthorizedLabels);
}


void CreateToken(OrthancPluginRestOutput* output,
                 const char* /*url*/,
                 const OrthancPluginHttpRequest* request)
{
  OrthancPluginContext* context = OrthancPlugins::GetGlobalContext();

  if (request->method != OrthancPluginHttpMethod_Put)
  {
    OrthancPluginSendMethodNotAllowed(context, output, "PUT");
  }
  else
  {
    // The filtering to this route is performed by this plugin as it is done for any other route before we get here.
    // Since the route contains the tokenType, we can allow/forbid creating them based on the url

    // simply forward the request to the auth-service
    std::string tokenType;
    if (request->groupsCount == 1)
    {
      tokenType = request->groups[0];
    }
    else
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
    }

    // convert from Orthanc flavored API to WebService API
    Json::Value body;
    if (!OrthancPlugins::ReadJson(body, request->body, request->bodySize))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat, "A JSON payload was expected");
    }

    std::string id;
    std::vector<OrthancPlugins::IAuthorizationService::OrthancResource> resources;
    std::string expirationDateString;
    uint64_t validityDuration;

    if (body.isMember("ID"))
    {
      id = body["ID"].asString();
    }

    for (Json::ArrayIndex i = 0; i < body["Resources"].size(); ++i)
    {
      const Json::Value& jsonResource = body["Resources"][i];
      OrthancPlugins::IAuthorizationService::OrthancResource resource;

      if (jsonResource.isMember("DicomUid"))
      {
        resource.dicomUid = jsonResource["DicomUid"].asString();
      }

      if (jsonResource.isMember("OrthancId"))
      {
        resource.orthancId = jsonResource["OrthancId"].asString();
      }

      if (jsonResource.isMember("Url"))
      {
        resource.url = jsonResource["Url"].asString();
      }

      resource.level = jsonResource["Level"].asString();
      resources.push_back(resource);
    }

    if (body.isMember("ExpirationDate"))
    {
      expirationDateString = body["ExpirationDate"].asString();
    }

    if (body.isMember("ValidityDuration"))
    {
      validityDuration = body["ValidityDuration"].asUInt64();
    }

    OrthancPlugins::IAuthorizationService::CreatedToken createdToken;
    if (authorizationService_->CreateToken(createdToken,
                                           tokenType,
                                           id,
                                           resources,
                                           expirationDateString,
                                           validityDuration))
    {
      Json::Value createdJsonToken;
      createdJsonToken["Token"] = createdToken.token;
      
      if (!createdToken.url.empty())
      {
        createdJsonToken["Url"] = createdToken.url;
      }
      else
      {
        createdJsonToken["Url"] = Json::nullValue;
      }

      OrthancPlugins::AnswerJson(createdJsonToken, output);
    }
    

  }
}

void DecodeToken(OrthancPluginRestOutput* output,
                 const char* /*url*/,
                 const OrthancPluginHttpRequest* request)
{
  OrthancPluginContext* context = OrthancPlugins::GetGlobalContext();

  if (request->method != OrthancPluginHttpMethod_Post)
  {
    OrthancPluginSendMethodNotAllowed(context, output, "POST");
  }
  else
  {
    // convert from Orthanc flavored API to WebService API
    Json::Value body;
    if (!OrthancPlugins::ReadJson(body, request->body, request->bodySize))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat, "A JSON payload was expected");
    }

    OrthancPlugins::IAuthorizationService::DecodedToken decodedToken;
    if (authorizationService_->DecodeToken(decodedToken,
                                           body["TokenKey"].asString(),
                                           body["TokenValue"].asString()))
    {
      Json::Value decodedJsonToken;
      
      if (!decodedToken.redirectUrl.empty())
      {
        decodedJsonToken["RedirectUrl"] = decodedToken.redirectUrl;
      }

      if (!decodedToken.errorCode.empty())
      {
        decodedJsonToken["ErrorCode"] = decodedToken.errorCode;
      }

      if (!decodedToken.tokenType.empty())
      {
        decodedJsonToken["TokenType"] = decodedToken.tokenType;
      }

      decodedJsonToken["ResourcesDicomIds"] = Json::arrayValue;
      for (std::set<std::string>::const_iterator it = decodedToken.resourcesDicomIds.begin(); it != decodedToken.resourcesDicomIds.end(); ++it)
      {
        decodedJsonToken["ResourcesDicomIds"].append(*it);
      }

      decodedJsonToken["ResourcesOrthancIds"] = Json::arrayValue;
      for (std::set<std::string>::const_iterator it = decodedToken.resourcesOrthancIds.begin(); it != decodedToken.resourcesOrthancIds.end(); ++it)
      {
        decodedJsonToken["ResourcesOrthancIds"].append(*it);
      }

      OrthancPlugins::AnswerJson(decodedJsonToken, output);
    }
  }
}


void GetUserProfile(OrthancPluginRestOutput* output,
                    const char* /*url*/,
                    const OrthancPluginHttpRequest* request)
{
  OrthancPluginContext* context = OrthancPlugins::GetGlobalContext();

  if (request->method != OrthancPluginHttpMethod_Get)
  {
    OrthancPluginSendMethodNotAllowed(context, output, "GET");
  }
  else
  {
    OrthancPlugins::IAuthorizationService::UserProfile profile;
    if (GetUserProfileInternal(profile, request))
    {
      Json::Value jsonProfile;
      jsonProfile["name"] = profile.name;
      jsonProfile["permissions"] = Json::arrayValue;
      jsonProfile["groups"] = Json::arrayValue;
      
      for (std::set<std::string>::const_iterator it = profile.permissions.begin(); it != profile.permissions.end(); ++it)
      {
        jsonProfile["permissions"].append(*it);
      }
      for (std::set<std::string>::const_iterator it = profile.authorizedLabels.begin(); it != profile.authorizedLabels.end(); ++it)
      {
        jsonProfile["authorized-labels"].append(*it);
      }
      for (std::set<std::string>::const_iterator it = profile.groups.begin(); it != profile.groups.end(); ++it)
      {
        jsonProfile["groups"].append(*it);
      }

      if (!profile.userId.empty())
      {
        jsonProfile["user-id"] = profile.userId;
      }

      OrthancPlugins::AnswerJson(jsonProfile, output);
    }
  }
}


void AuthSettingsRoles(OrthancPluginRestOutput* output,
                       const char* /*url*/,
                       const OrthancPluginHttpRequest* request)
{
  OrthancPluginContext* context = OrthancPlugins::GetGlobalContext();

  if (authorizationService_.get() == NULL) // this is not suppposed to happen
  {
    OrthancPlugins::AnswerHttpError(404, output);
    return;
  }

  if (request->method == OrthancPluginHttpMethod_Get)
  {
    Json::Value roles;
    
    if (!authorizationService_->GetSettingsRoles(roles))
    {
      LOG(WARNING) << "Could not retrieve roles from the auth-service.  The auth-service might not provide this feature or is not configured correctly.";
    }

    OrthancPlugins::AnswerJson(roles, output);
  }
  else if (request->method == OrthancPluginHttpMethod_Put)
  {
    Json::Value roles;
    Json::Value response;

    if (!OrthancPlugins::ReadJson(roles, request->body, request->bodySize))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat, "A JSON payload was expected");
    }

    if (!authorizationService_->UpdateSettingsRoles(response, roles))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError, "Could not update roles in the auth-service", true);
    }
    OrthancPlugins::AnswerJson(response, output);
  }
  else
  {
    OrthancPluginSendMethodNotAllowed(context, output, "GET,PUT");
  }
}


void GetPermissionList(OrthancPluginRestOutput* output,
                       const char* /*url*/,
                       const OrthancPluginHttpRequest* request)
{
  OrthancPluginContext* context = OrthancPlugins::GetGlobalContext();

  if (request->method != OrthancPluginHttpMethod_Get)
  {
    OrthancPluginSendMethodNotAllowed(context, output, "GET");
  }
  else
  {
    std::set<std::string> permissionsList = permissionParser_->GetPermissionsList();

    Json::Value response = Json::arrayValue;
    Orthanc::SerializationToolbox::WriteSetOfStrings(response, permissionsList);

    OrthancPlugins::AnswerJson(response, output);
  }
}


extern "C"
{
  ORTHANC_PLUGINS_API int32_t OrthancPluginInitialize(OrthancPluginContext* context)
  {
    OrthancPlugins::SetGlobalContext(context, ORTHANC_PLUGIN_NAME);
    OrthancPluginLogWarning(context, "Initializing the authorization plugin");

    /* Check the version of the Orthanc core */
    if (OrthancPluginCheckVersion(context) == 0)
    {
      OrthancPlugins::ReportMinimalOrthancVersion(ORTHANC_PLUGINS_MINIMAL_MAJOR_NUMBER,
                                                  ORTHANC_PLUGINS_MINIMAL_MINOR_NUMBER,
                                                  ORTHANC_PLUGINS_MINIMAL_REVISION_NUMBER);
      return -1;
    }

#if ORTHANC_FRAMEWORK_VERSION_IS_ABOVE(1, 12, 4)
    Orthanc::Logging::InitializePluginContext(context, ORTHANC_PLUGIN_NAME);
#elif ORTHANC_FRAMEWORK_VERSION_IS_ABOVE(1, 7, 2)
    Orthanc::Logging::InitializePluginContext(context);
#else
    Orthanc::Logging::Initialize(context);
#endif
    
    OrthancPlugins::SetDescription(ORTHANC_PLUGIN_NAME, "Advanced authorization plugin for Orthanc.");

    try
    {
      static const char* const PLUGIN_SECTION = "Authorization";

      OrthancPlugins::OrthancConfiguration orthancFullConfiguration;

      // read default configuration
      std::string defaultConfigurationFileContent;
      Orthanc::EmbeddedResources::GetFileResource(defaultConfigurationFileContent, Orthanc::EmbeddedResources::DEFAULT_CONFIGURATION);
      Json::Value pluginJsonDefaultConfiguration;
      OrthancPlugins::ReadJsonWithoutComments(pluginJsonDefaultConfiguration, defaultConfigurationFileContent);
      Json::Value pluginJsonConfiguration = pluginJsonDefaultConfiguration[PLUGIN_SECTION];

      OrthancPlugins::OrthancConfiguration pluginProvidedConfiguration;

      if (orthancFullConfiguration.IsSection(PLUGIN_SECTION))
      {
        // get the configuration provided by the user
        orthancFullConfiguration.GetSection(pluginProvidedConfiguration, PLUGIN_SECTION);

        // merge it with the default configuration.  This is a way to apply the all default values in a single step
        MergeJson(pluginJsonConfiguration, pluginProvidedConfiguration.GetJson());

        // recreate a OrthancConfiguration object from the merged configuration
        OrthancPlugins::OrthancConfiguration pluginConfiguration(pluginJsonConfiguration, PLUGIN_SECTION);

        // TODO - The size of the caches is set to 10,000 items. Maybe add a configuration option?
        OrthancPlugins::MemoryCache::Factory factory(10000);

        std::string dicomWebRoot = "/dicom-web/";
        std::string oe2Root = "/ui/";

        bool hasBasicAuthEnabled = orthancFullConfiguration.GetBooleanValue("AuthenticationEnabled", "true");

        if (orthancFullConfiguration.IsSection("DicomWeb"))
        {
          OrthancPlugins::OrthancConfiguration dicomWeb;
          dicomWeb.GetSection(orthancFullConfiguration, "DicomWeb");
          dicomWebRoot = dicomWeb.GetStringValue("Root", "/dicom-web/");
        }

        if (orthancFullConfiguration.IsSection("OrthancExplorer2"))
        {
          OrthancPlugins::OrthancConfiguration oe2;
          oe2.GetSection(orthancFullConfiguration, "OrthancExplorer2");
          oe2Root = oe2.GetStringValue("Root", "/ui/");
        }

        std::list<std::string> tmp;

        pluginConfiguration.LookupListOfStrings(tmp, "TokenHttpHeaders", true);
        for (std::list<std::string>::const_iterator
               it = tmp.begin(); it != tmp.end(); ++it)
        {
          tokens_.insert(OrthancPlugins::Token(OrthancPlugins::TokenType_HttpHeader, *it));
        }

        pluginConfiguration.LookupListOfStrings(tmp, "TokenGetArguments", true);

#if ORTHANC_PLUGINS_VERSION_IS_ABOVE(1, 3, 0)  
        for (std::list<std::string>::const_iterator
               it = tmp.begin(); it != tmp.end(); ++it)
        {
          tokens_.insert(OrthancPlugins::Token(OrthancPlugins::TokenType_GetArgument, *it));
        }
#else
        if (!tmp.empty())
        {
          throw Orthanc::OrthancException(
            Orthanc::ErrorCode_Plugin,
            "The option \"TokenGetArguments\" of the authorization plugin "
            "is only valid if compiled against Orthanc >= 1.3.0"
        }
#endif

        enableAuditLogs_ = pluginConfiguration.GetBooleanValue("EnableAuditLogs", false);


        pluginConfiguration.LookupSetOfStrings(uncheckedResources_, "UncheckedResources", false);
        pluginConfiguration.LookupListOfStrings(uncheckedFolders_, "UncheckedFolders", false);

        std::string urlTokenDecoder;
        std::string urlTokenValidation;
        std::string urlTokenCreationBase;
        std::string urlUserProfile;
        std::string urlSettingsRole;
        std::string urlRoot;

        static const char* const WEB_SERVICE_ROOT = "WebServiceRootUrl";

        if (pluginConfiguration.LookupStringValue(urlRoot, WEB_SERVICE_ROOT))
        {
          urlTokenDecoder = Orthanc::Toolbox::JoinUri(urlRoot, "/tokens/decode");
          urlTokenValidation = Orthanc::Toolbox::JoinUri(urlRoot, "/tokens/validate");
          urlTokenCreationBase = Orthanc::Toolbox::JoinUri(urlRoot, "/tokens/");
          urlUserProfile = Orthanc::Toolbox::JoinUri(urlRoot, "/user/get-profile");
          urlSettingsRole = Orthanc::Toolbox::JoinUri(urlRoot, "/settings/roles");
        }
        else 
        {
          static const char* const WEB_SERVICE_TOKEN_DECODER = "WebServiceTokenDecoderUrl";
          static const char* const WEB_SERVICE_TOKEN_VALIDATION = "WebServiceTokenValidationUrl";
          static const char* const WEB_SERVICE_TOKEN_CREATION_BASE = "WebServiceTokenCreationBaseUrl";
          static const char* const WEB_SERVICE_USER_PROFILE = "WebServiceUserProfileUrl";
          static const char* const WEB_SERVICE_SETTINGS_ROLES = "WebServiceSettingsRolesUrl";
          static const char* const WEB_SERVICE_TOKEN_VALIDATION_LEGACY = "WebService";

          pluginConfiguration.LookupStringValue(urlTokenValidation, WEB_SERVICE_TOKEN_VALIDATION);
          pluginConfiguration.LookupStringValue(urlTokenDecoder, WEB_SERVICE_TOKEN_DECODER);
          if (urlTokenValidation.empty())
          {
            pluginConfiguration.LookupStringValue(urlTokenValidation, WEB_SERVICE_TOKEN_VALIDATION_LEGACY);
          }

          pluginConfiguration.LookupStringValue(urlTokenCreationBase, WEB_SERVICE_TOKEN_CREATION_BASE);
          pluginConfiguration.LookupStringValue(urlUserProfile, WEB_SERVICE_USER_PROFILE);
          pluginConfiguration.LookupStringValue(urlSettingsRole, WEB_SERVICE_SETTINGS_ROLES);
        }

        authorizationParser_.reset(new OrthancPlugins::DefaultAuthorizationParser(factory, dicomWebRoot));

        if (!urlTokenValidation.empty())
        {
          LOG(WARNING) << "Authorization plugin: url defined for Token Validation: " << urlTokenValidation << ", resource tokens validation is enabled";
          resourceTokensEnabled_ = true;
        }
        else
        {
          LOG(WARNING) << "Authorization plugin: no url defined for Token Validation, resource tokens validation is disabled";
          resourceTokensEnabled_ = false;
        }

        if (!urlUserProfile.empty())
        {
          LOG(WARNING) << "Authorization plugin: url defined for User Profile: " << urlUserProfile << ", user tokens validation is enabled";
          userTokensEnabled_ = true;
          
          static const char* const PERMISSIONS = "Permissions";
          if (!pluginConfiguration.GetJson().isMember(PERMISSIONS))
          {
            throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat, "Authorization plugin: Missing required \"" + std::string(PERMISSIONS) + 
              "\" option since you have defined the \"" + std::string(WEB_SERVICE_ROOT) + "\" option");
          }
          permissionParser_.reset
            (new OrthancPlugins::PermissionParser(dicomWebRoot, oe2Root));

          permissionParser_->Add(pluginConfiguration.GetJson()[PERMISSIONS], authorizationParser_.get());

          static const char* const EXTRA_PERMISSIONS = "ExtraPermissions";
          if (pluginConfiguration.GetJson().isMember(EXTRA_PERMISSIONS))
          {
            permissionParser_->Add(pluginConfiguration.GetJson()[EXTRA_PERMISSIONS], authorizationParser_.get());
          }
        }
        else
        {
          LOG(WARNING) << "Authorization plugin: no url defined for User Profile" << ", user tokens validation is disabled";
          userTokensEnabled_ = false;
        }

        if (!urlTokenCreationBase.empty())
        {
          LOG(WARNING) << "Authorization plugin: base url defined for Token Creation : " << urlTokenCreationBase;
        }
        else
        {
          LOG(WARNING) << "Authorization plugin: no base url defined for Token Creation";
        }

        if (!urlSettingsRole.empty())
        {
          LOG(WARNING) << "Authorization plugin: settings-roles url defined : " << urlSettingsRole;
        }
        else
        {
          LOG(WARNING) << "Authorization plugin: no settings-roles url defined";
        }

        if (!resourceTokensEnabled_ && permissionParser_.get() == NULL)
        {
          if (hasBasicAuthEnabled)
          {
            LOG(WARNING) << "Authorization plugin: No Token Validation or User Profile url defined -> will only be able to generate tokens.  All API routes are accessible to all registered users.";
          }
          else
          {
            LOG(WARNING) << "Authorization plugin: ----------- insecure setup ---------- No Token Validation or User Profile url defined -> will only be able to generate tokens.  Authentication is not enabled -> anyone will have access to all API routes.";
          }
        }

        std::set<std::string> standardConfigurations;
        if (pluginConfiguration.LookupSetOfStrings(standardConfigurations, "StandardConfigurations", false))
        {
          if (standardConfigurations.find("osimis-web-viewer") != standardConfigurations.end())
          {
            uncheckedFolders_.push_back("/osimis-viewer/app/");
            uncheckedFolders_.push_back("/osimis-viewer/languages/");
            uncheckedResources_.insert("/osimis-viewer/config.js");

            tokens_.insert(OrthancPlugins::Token(OrthancPlugins::TokenType_HttpHeader, "token"));
            tokens_.insert(OrthancPlugins::Token(OrthancPlugins::TokenType_GetArgument, "token"));  // for download links in Webviewer
          }

          if (standardConfigurations.find("stone-webviewer") != standardConfigurations.end())
          {
            uncheckedFolders_.push_back("/stone-webviewer/");
            uncheckedResources_.insert("/system");        // for Stone to check that Orthanc is the server providing the data

            tokens_.insert(OrthancPlugins::Token(OrthancPlugins::TokenType_HttpHeader, "Authorization"));
          }

          if (standardConfigurations.find("orthanc-explorer-2") != standardConfigurations.end())
          {
            uncheckedFolders_.push_back("/ui/app/");
            uncheckedFolders_.push_back("/ui/landing/");
            uncheckedResources_.insert("/");                                      // for the redirect to /ui/app/
            uncheckedResources_.insert("/ui/api/pre-login-configuration");        // for the UI to know, i.e. if Keycloak is enabled or not
            uncheckedResources_.insert("/ui/api/configuration");
            uncheckedResources_.insert("/auth/user/profile");

            tokens_.insert(OrthancPlugins::Token(OrthancPlugins::TokenType_HttpHeader, "Authorization"));  // for basic-auth
            tokens_.insert(OrthancPlugins::Token(OrthancPlugins::TokenType_HttpHeader, "token"));          // for keycloak
            tokens_.insert(OrthancPlugins::Token(OrthancPlugins::TokenType_GetArgument, "token"));         // for download links in OE2
          }

          if (standardConfigurations.find("ohif") != standardConfigurations.end())
          {
            uncheckedFolders_.push_back("/ohif/");

            tokens_.insert(OrthancPlugins::Token(OrthancPlugins::TokenType_HttpHeader, "Authorization"));
          }

          if (standardConfigurations.find("volview") != standardConfigurations.end())
          {
            uncheckedFolders_.push_back("/volview/");

            tokens_.insert(OrthancPlugins::Token(OrthancPlugins::TokenType_HttpHeader, "Authorization"));
          }

          if (standardConfigurations.find("volview") != standardConfigurations.end())
          {
            uncheckedFolders_.push_back("/volview/");

            tokens_.insert(OrthancPlugins::Token(OrthancPlugins::TokenType_HttpHeader, "Authorization"));
          }

        }

        std::string checkedLevelString;
        if (pluginConfiguration.LookupStringValue(checkedLevelString, "CheckedLevel"))
        {
          OrthancPlugins::AccessLevel checkedLevel = OrthancPlugins::StringToAccessLevel(checkedLevelString);
          if (checkedLevel == OrthancPlugins::AccessLevel_Instance) 
          {
            uncheckedLevels_.insert(OrthancPlugins::AccessLevel_System);
            uncheckedLevels_.insert(OrthancPlugins::AccessLevel_Patient);
            uncheckedLevels_.insert(OrthancPlugins::AccessLevel_Study);
            uncheckedLevels_.insert(OrthancPlugins::AccessLevel_Series);
          }
          else if (checkedLevel == OrthancPlugins::AccessLevel_Series) 
          {
            uncheckedLevels_.insert(OrthancPlugins::AccessLevel_System);
            uncheckedLevels_.insert(OrthancPlugins::AccessLevel_Patient);
            uncheckedLevels_.insert(OrthancPlugins::AccessLevel_Study);
            uncheckedLevels_.insert(OrthancPlugins::AccessLevel_Instance);
          }
          else if (checkedLevel == OrthancPlugins::AccessLevel_Study) 
          {
            uncheckedLevels_.insert(OrthancPlugins::AccessLevel_System);
            uncheckedLevels_.insert(OrthancPlugins::AccessLevel_Patient);
            uncheckedLevels_.insert(OrthancPlugins::AccessLevel_Series);
            uncheckedLevels_.insert(OrthancPlugins::AccessLevel_Instance);
          }
          else if (checkedLevel == OrthancPlugins::AccessLevel_Patient) 
          {
            uncheckedLevels_.insert(OrthancPlugins::AccessLevel_System);
            uncheckedLevels_.insert(OrthancPlugins::AccessLevel_Study);
            uncheckedLevels_.insert(OrthancPlugins::AccessLevel_Series);
            uncheckedLevels_.insert(OrthancPlugins::AccessLevel_Instance);
          }
        }

        if (pluginConfiguration.LookupListOfStrings(tmp, "UncheckedLevels", false))
        {
          if (uncheckedLevels_.size() == 0)
          {
            for (std::list<std::string>::const_iterator
                  it = tmp.begin(); it != tmp.end(); ++it)
            {
              uncheckedLevels_.insert(OrthancPlugins::StringToAccessLevel(*it));
            }
          }
          else
          {
            LOG(ERROR) << "Authorization plugin: you may only provide one of 'CheckedLevel' or 'UncheckedLevels' configurations";
            return -1;
          }
        }

        std::unique_ptr<OrthancPlugins::AuthorizationWebService> webService(new OrthancPlugins::AuthorizationWebService(urlTokenValidation,
                                                                                                                        urlTokenCreationBase,
                                                                                                                        urlUserProfile,
                                                                                                                        urlTokenDecoder,
                                                                                                                        urlSettingsRole));

        std::string webServiceIdentifier;
        if (pluginConfiguration.LookupStringValue(webServiceIdentifier, "WebServiceIdentifier"))
        {
          webService->SetIdentifier(webServiceIdentifier);
        }

        std::string webServiceUsername;
        std::string webServicePassword;
        if (pluginConfiguration.LookupStringValue(webServiceUsername, "WebServiceUsername") && pluginConfiguration.LookupStringValue(webServicePassword, "WebServicePassword"))
        {
          webService->SetCredentials(webServiceUsername, webServicePassword);
        }

        authorizationService_.reset
          (new OrthancPlugins::CachedAuthorizationService
           (webService.release(), factory));

        if (!urlTokenValidation.empty() || enableAuditLogs_)
        {
          OrthancPluginRegisterOnChangeCallback(context, OnChangeCallback);
        }
        
        if (!urlTokenDecoder.empty())
        {
          OrthancPlugins::RegisterRestCallback<DecodeToken>("/auth/tokens/decode", true);
        }

        if (!urlUserProfile.empty())
        {
          OrthancPlugins::RegisterRestCallback<GetUserProfile>("/auth/user/profile", true);
          OrthancPlugins::RegisterRestCallback<ToolsFind>("/tools/find", true);
          OrthancPlugins::RegisterRestCallback<ToolsCountResources>("/tools/count-resources", true);
          OrthancPlugins::RegisterRestCallback<ToolsLabels>("/tools/labels", true);
          OrthancPlugins::RegisterRestCallback<AuthSettingsRoles>("/auth/settings/roles", true);
          OrthancPlugins::RegisterRestCallback<GetPermissionList>("/auth/settings/permissions", true);

          OrthancPlugins::RegisterRestCallback<GetOrDeleteMainResource>("/(patients|studies|series)/([^/]*)", true);  // this includes auditLogs

          OrthancPlugins::RegisterRestCallback<FilterLabelsFromSingleResource>("/instances/([^/]*)/patient", true);
          OrthancPlugins::RegisterRestCallback<FilterLabelsFromSingleResource>("/instances/([^/]*)/study", true);
          OrthancPlugins::RegisterRestCallback<FilterLabelsFromSingleResource>("/instances/([^/]*)/series", true);
          OrthancPlugins::RegisterRestCallback<FilterLabelsFromSingleResource>("/series/([^/]*)/patient", true);
          OrthancPlugins::RegisterRestCallback<FilterLabelsFromSingleResource>("/series/([^/]*)/study", true);
          OrthancPlugins::RegisterRestCallback<FilterLabelsFromSingleResource>("/studies/([^/]*)/patient", true);

          OrthancPlugins::RegisterRestCallback<FilterLabelsFromResourceLabels>("/instances/([^/]*)/labels", true);
          OrthancPlugins::RegisterRestCallback<FilterLabelsFromResourceLabels>("/series/([^/]*)/labels", true);
          OrthancPlugins::RegisterRestCallback<FilterLabelsFromResourceLabels>("/studies/([^/]*)/labels", true);
          OrthancPlugins::RegisterRestCallback<FilterLabelsFromResourceLabels>("/patients/([^/]*)/labels", true);

          OrthancPlugins::RegisterRestCallback<FilterLabelsFromResourceList>("/series/([^/]*)/instances", true);
          OrthancPlugins::RegisterRestCallback<FilterLabelsFromResourceList>("/studies/([^/]*)/instances", true);
          OrthancPlugins::RegisterRestCallback<FilterLabelsFromResourceList>("/studies/([^/]*)/series", true);
          OrthancPlugins::RegisterRestCallback<FilterLabelsFromResourceList>("/patients/([^/]*)/instances", true);
          OrthancPlugins::RegisterRestCallback<FilterLabelsFromResourceList>("/patients/([^/]*)/series", true);
          OrthancPlugins::RegisterRestCallback<FilterLabelsFromResourceList>("/patients/([^/]*)/studies", true);

          if (enableAuditLogs_)
          {
            OrthancPlugins::RegisterRestCallback<UploadInstancesWithAuditLogs>("/instances", true);
            OrthancPlugins::RegisterRestCallback<AnonymizeWithAuditLogs>("/(patients|studies|series)/([^/]*)/anonymize", true);
            OrthancPlugins::RegisterRestCallback<ModifyWithAuditLogs>("/(patients|studies|series)/([^/]*)/modify", true);
            OrthancPlugins::RegisterRestCallback<LabelWithAuditLogs>("/(patients|studies|series)/([^/]*)/labels/([^/]*)", true);
            OrthancPlugins::RegisterRestCallback<BulkDeleteWithAuditLogs>("/tools/bulk-delete", true);
            OrthancPlugins::RegisterRestCallback<BulkModifyAnonymizeWithAuditLogs>("/tools/bulk-modify", true);
            OrthancPlugins::RegisterRestCallback<BulkModifyAnonymizeWithAuditLogs>("/tools/bulk-anonymize", true);
            OrthancPlugins::RegisterRestCallback<GetAuditLogs>("/auth/audit-logs", true);

            // Note: other "actions" that do not modify the data like download-archive are logged in the HTTP filter (see RecordResourceAccess())

            // TODO
            // /modalities/move
            // /modalities/store
            // /archive + create-archive
            // /media + create-media + create-media-extended

          }
        }

        if (!urlTokenCreationBase.empty())
        {
          OrthancPlugins::RegisterRestCallback<CreateToken>("/auth/tokens/(.*)", true);
        }

        if (resourceTokensEnabled_ || userTokensEnabled_)
        {
          // Disabled because of this: https://discourse.orthanc-server.org/t/user-based-access-control-with-label-based-resource-access/5454
          // if (hasBasicAuthEnabled)
          // {
          //   throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat, "Authorization plugin: you are using the plugin to grant access to resources or handle user permissions.  This is not compatible with \"AuthenticationEnabled\" = true");
          // }

          LOG(WARNING) << "Authorization plugin: Registering Incoming HTTP Request Filter";

#if ORTHANC_PLUGINS_VERSION_IS_ABOVE(1, 2, 1)
          OrthancPluginRegisterIncomingHttpRequestFilter2(context, FilterHttpRequests);
#else
          OrthancPluginRegisterIncomingHttpRequestFilter(context, FilterHttpRequestsFallback);
#endif
        }

      }
      else
      {
        LOG(WARNING) << "No section \"" << PLUGIN_SECTION << "\" in the configuration file, "
                     << "the authorization plugin is disabled";
      }
    }
    catch (Orthanc::OrthancException& e)
    {
      LOG(ERROR) << e.What();
      return -1;
    }
    
    return 0;
  }


  ORTHANC_PLUGINS_API void OrthancPluginFinalize()
  {
    authorizationParser_.reset(NULL);
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
