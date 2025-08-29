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


#include <orthanc/OrthancCPlugin.h>
#include <OrthancPluginCppWrapper.h>

#include "EncryptionConfigurator.h"

#include <Logging.h>

bool ReadMasterKey(uint32_t& id, std::string& keyPath, const Json::Value& node)
{
  if (!node.isArray() || node.size() != 2 || !node[0].isUInt() || !node[1].isString())
  {
    LOG(WARNING) << "Encryption: Invalid master key configuration";
    return false;
  }

  id = node[0].asUInt();
  keyPath = node[1].asString();

  return true;
}


EncryptionHelpers* EncryptionConfigurator::CreateEncryptionHelpers(const OrthancPlugins::OrthancConfiguration& cryptoSection)
{
  bool enabled = cryptoSection.GetBooleanValue("Enable", true);

  if (!enabled)
  {
    return nullptr;
  }

  Json::Value cryptoJson = cryptoSection.GetJson();

  if (!cryptoJson.isMember("MasterKey") || !cryptoJson["MasterKey"].isArray())
  {
    LOG(WARNING) << "Encryption: MasterKey missing.  Unable to initialize encryption";
    return nullptr;
  }

  unsigned int maxConcurrentInputSizeInMb = cryptoSection.GetUnsignedIntegerValue("MaxConcurrentInputSize", 1024);

  std::unique_ptr<EncryptionHelpers> crypto(new EncryptionHelpers(maxConcurrentInputSizeInMb * 1024*1024));

  uint32_t masterKeyId;
  std::string masterKeyPath;

  if (!ReadMasterKey(masterKeyId, masterKeyPath, cryptoJson["MasterKey"]))
  {
    return nullptr;
  }
  crypto->SetCurrentMasterKey(masterKeyId, masterKeyPath);

  if (cryptoJson.isMember("PreviousMasterKeys") && cryptoJson["PreviousMasterKeys"].isArray())
  {
    for (size_t i = 0; i < cryptoJson["PreviousMasterKeys"].size(); i++)
    {
      uint32_t keyId;
      std::string keyPath;
      if (!ReadMasterKey(keyId, keyPath, cryptoJson["PreviousMasterKeys"][(unsigned int)i]))
      {
          return nullptr;
      }
      crypto->AddPreviousMasterKey(keyId, keyPath);
    }
  }

  return crypto.release();
}
