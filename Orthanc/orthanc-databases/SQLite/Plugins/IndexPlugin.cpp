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


#include "SQLiteIndex.h"
#include "../../Framework/Plugins/PluginInitialization.h"

#include <Logging.h>

#if ORTHANC_PLUGINS_VERSION_IS_ABOVE(1, 12, 0)
#  include <google/protobuf/any.h>
#  include <google/protobuf/stubs/common.h>
#endif

#define ORTHANC_PLUGIN_NAME "sqlite-index"


extern "C"
{
  ORTHANC_PLUGINS_API int32_t OrthancPluginInitialize(OrthancPluginContext* context)
  {
#if ORTHANC_PLUGINS_VERSION_IS_ABOVE(1, 12, 0)
    GOOGLE_PROTOBUF_VERIFY_VERSION;
#endif

    if (!OrthancDatabases::InitializePlugin(context, ORTHANC_PLUGIN_NAME, "SQLite", true))
    {
      return -1;
    }

#if 0
    OrthancPlugins::OrthancConfiguration configuration;

    if (!configuration.IsSection("SQLite"))
    {
      LOG(WARNING) << "No available configuration for the SQLite index plugin";
      return 0;
    }

    OrthancPlugins::OrthancConfiguration sqlite;
    configuration.GetSection(sqlite, "SQLite");

    bool enable;
    if (!sqlite.LookupBooleanValue(enable, "EnableIndex") ||
        !enable)
    {
      LOG(WARNING) << "The SQLite index is currently disabled, set \"EnableIndex\" "
                   << "to \"true\" in the \"SQLite\" section of the configuration file of Orthanc";
      return 0;
    }
#endif

    try
    {
      /* Register the SQLite index into Orthanc */
      OrthancDatabases::IndexBackend::Register(
        new OrthancDatabases::SQLiteIndex(context, "index.db"),   // TODO parameter
        1 /* only 1 connection is possible with SQLite */,
        false /* useDynamicConnectionPool */,
        0 /* no collision is possible, as SQLite has a global lock */,
        0 /* housekeeping delay, unused for SQLite */);
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
    LOG(WARNING) << "SQLite index is finalizing";
    OrthancDatabases::IndexBackend::Finalize();

#if ORTHANC_PLUGINS_VERSION_IS_ABOVE(1, 12, 0)
    google::protobuf::ShutdownProtobufLibrary();
#endif
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
