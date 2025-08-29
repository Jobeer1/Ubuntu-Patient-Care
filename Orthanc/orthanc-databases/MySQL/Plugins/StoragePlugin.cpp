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


#include "MySQLStorageArea.h"
#include "../../Framework/MySQL/MySQLDatabase.h"
#include "../../Framework/Plugins/PluginInitialization.h"

#include <HttpClient.h>
#include <Logging.h>
#include <Toolbox.h>

#define ORTHANC_PLUGIN_NAME "mysql-storage"


extern "C"
{
  ORTHANC_PLUGINS_API int32_t OrthancPluginInitialize(OrthancPluginContext* context)
  {
    if (!OrthancDatabases::InitializePlugin(context, ORTHANC_PLUGIN_NAME, "MySQL", false))
    {
      return -1;
    }

    Orthanc::Toolbox::InitializeOpenSsl();
    Orthanc::HttpClient::GlobalInitialize();

    OrthancPlugins::OrthancConfiguration configuration;

    if (!configuration.IsSection("MySQL"))
    {
      LOG(WARNING) << "No available configuration for the MySQL storage area plugin";
      return 0;
    }

    OrthancPlugins::OrthancConfiguration mysql;
    configuration.GetSection(mysql, "MySQL");

    bool enable;
    if (!mysql.LookupBooleanValue(enable, "EnableStorage") ||
        !enable)
    {
      LOG(WARNING) << "The MySQL storage area is currently disabled, set \"EnableStorage\" "
                   << "to \"true\" in the \"MySQL\" section of the configuration file of Orthanc";
      return 0;
    }

    try
    {
      OrthancDatabases::MySQLParameters parameters(mysql, configuration);
      OrthancDatabases::StorageBackend::Register(
        context, new OrthancDatabases::MySQLStorageArea(parameters, false /* don't clear database */));
    }
    catch (Orthanc::OrthancException& e)
    {
      LOG(ERROR) << e.What();
      return -1;
    }
    catch (...)
    {
      LOG(ERROR) << "Native exception while initializing the plugin";
      return -1;
    }

    return 0;
  }


  ORTHANC_PLUGINS_API void OrthancPluginFinalize()
  {
    LOG(WARNING) << "MySQL storage area is finalizing";

    OrthancDatabases::StorageBackend::Finalize();
    OrthancDatabases::MySQLDatabase::GlobalFinalization();
    Orthanc::HttpClient::GlobalFinalize();
    Orthanc::Toolbox::FinalizeOpenSsl();
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
