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

#pragma once

#include "BaseAuthorizationService.h"
#include "ICacheFactory.h"

#include <Compatibility.h>  // For std::unique_ptr<>

#include <memory>

namespace OrthancPlugins
{
  /**
   * Decorator design pattern to add a cache around an IAuthorizationService
   **/
  class CachedAuthorizationService : public BaseAuthorizationService
  {
  private:
    std::unique_ptr<BaseAuthorizationService>  decorated_;
    std::unique_ptr<ICache>   cache_;
    std::unique_ptr<ICache>   cacheUserId_;

    std::string ComputeKey(OrthancPluginHttpMethod method,
                           const AccessedResource& access,
                           const Token* token,
                           const std::string& tokenValue) const;

    std::string ComputeKey(const std::string& permission,
                           const Token* token,
                           const std::string& tokenValue) const;

    virtual bool IsGrantedInternal(unsigned int& validity,
                                   OrthancPluginHttpMethod method,
                                   const AccessedResource& access,
                                   const Token* token,
                                   const std::string& tokenValue) ORTHANC_OVERRIDE;
    
    virtual bool GetUserProfileInternal(unsigned int& validity,
                                        UserProfile& profile /* out */,
                                        const Token* token,
                                        const std::string& tokenValue) ORTHANC_OVERRIDE;

    virtual bool GetUserProfileFromUserId(unsigned int& validity /* out */,
                                          UserProfile& profile /* out */,
                                          const std::string& userId) ORTHANC_OVERRIDE;

    virtual bool HasUserPermissionInternal(const std::string& permission,
                                           const UserProfile& profile) ORTHANC_OVERRIDE;


  public:
    CachedAuthorizationService(BaseAuthorizationService* decorated /* takes ownership */,
                               ICacheFactory& factory);

    virtual bool HasUserProfile() const ORTHANC_OVERRIDE
    {
      return decorated_->HasUserProfile();
    }

    virtual bool HasCreateToken() const ORTHANC_OVERRIDE
    {
      return decorated_->HasCreateToken();
    }

    virtual bool HasTokenValidation() const ORTHANC_OVERRIDE
    {
      return decorated_->HasTokenValidation();
    }

    virtual bool CreateToken(IAuthorizationService::CreatedToken& response,
                             const std::string& tokenType, 
                             const std::string& id, 
                             const std::vector<IAuthorizationService::OrthancResource>& resources,
                             const std::string& expirationDateString,
                             const uint64_t& validityDuration) ORTHANC_OVERRIDE
    {
      return decorated_->CreateToken(response,
                                     tokenType,
                                     id,
                                     resources,
                                     expirationDateString,
                                     validityDuration);
    }

    virtual bool DecodeToken(DecodedToken& response,
                             const std::string& tokenKey, 
                             const std::string& tokenValue) ORTHANC_OVERRIDE
    {
      return decorated_->DecodeToken(response,
                                     tokenKey,
                                     tokenValue);
    }

    virtual bool GetSettingsRoles(Json::Value& roles) ORTHANC_OVERRIDE
    {
      return decorated_->GetSettingsRoles(roles);
    }

    virtual bool UpdateSettingsRoles(Json::Value& response,
                                     const Json::Value& roles) ORTHANC_OVERRIDE
    {
      return decorated_->UpdateSettingsRoles(response, roles);
    }

 };
}
