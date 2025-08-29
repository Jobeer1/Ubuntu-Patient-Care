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

#include "IAuthorizationService.h"

#include <Compatibility.h>


namespace OrthancPlugins
{
  class CachedAuthorizationService;

  class BaseAuthorizationService : public IAuthorizationService
  {
    friend CachedAuthorizationService;
  protected:
    virtual bool IsGrantedInternal(unsigned int& validity,
                                   OrthancPluginHttpMethod method,
                                   const AccessedResource& access,
                                   const Token* token,
                                   const std::string& tokenValue) = 0;
    
    virtual bool GetUserProfileInternal(unsigned int& validity,
                                        UserProfile& profile /* out */,
                                        const Token* token,
                                        const std::string& tokenValue) = 0;

    virtual bool HasUserPermissionInternal(const std::string& permission,
                                           const UserProfile& profile) = 0;

  public:
    virtual ~BaseAuthorizationService()
    {
    }
    
    virtual bool IsGranted(unsigned int& validity,
                           OrthancPluginHttpMethod method,
                           const AccessedResource& access,
                           const Token& token,
                           const std::string& tokenValue) ORTHANC_OVERRIDE
    {
      return IsGrantedInternal(validity, method, access, &token, tokenValue);
    }
    
    virtual bool IsGrantedToAnonymousUser(unsigned int& validity,
                                          OrthancPluginHttpMethod method,
                                          const AccessedResource& access) ORTHANC_OVERRIDE
    {
      return IsGrantedInternal(validity, method, access, NULL, "");
    }

    virtual bool GetUserProfile(unsigned int& validity,
                                UserProfile& profile /* out */,
                                const Token& token,
                                const std::string& tokenValue) ORTHANC_OVERRIDE
    {
      return GetUserProfileInternal(validity, profile, &token, tokenValue);
    }

    virtual bool GetAnonymousUserProfile(unsigned int& validity /* out */,
                                         UserProfile& profile /* out */) ORTHANC_OVERRIDE
    {
      return GetUserProfileInternal(validity, profile, NULL, "");
    }

    virtual bool HasUserPermission(const std::set<std::string>& anyOfPermissions,
                                   const UserProfile& profile) ORTHANC_OVERRIDE
    {
      if (anyOfPermissions.size() == 0)
      {
        return true;
      }

      for (std::set<std::string>::const_iterator it = anyOfPermissions.begin(); it != anyOfPermissions.end(); ++it)
      {
        if (HasUserPermissionInternal(*it, profile))
        {
          return true;
        }
      }
      return false;
    }

  };
}
