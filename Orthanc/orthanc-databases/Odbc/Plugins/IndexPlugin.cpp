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


#include "OdbcIndex.h"

#include "../../Framework/Odbc/OdbcEnvironment.h"
#include "../../Framework/Plugins/PluginInitialization.h"
#include "../../Resources/Orthanc/Plugins/OrthancPluginCppWrapper.h"

#include <Logging.h>

#define ORTHANC_PLUGIN_NAME "odbc-index"


#if defined(_WIN32)
#  ifdef _MSC_VER
#    pragma message("Warning: Strings have not been tested on Windows (UTF-16 issues ahead)!")
#  else
#    warning Strings have not been tested on Windows (UTF-16 issues ahead)!
#  endif
#  include <windows.h>
#else
#  include <ltdl.h>
#  include <libltdl/lt_dlloader.h>
#endif


#if ORTHANC_PLUGINS_VERSION_IS_ABOVE(1, 12, 0)
#  include <google/protobuf/any.h>
#  include <google/protobuf/stubs/common.h>
#endif


static const char* const KEY_ODBC = "Odbc";


extern "C"
{
#if !defined(_WIN32)
  extern lt_dlvtable *dlopen_LTX_get_vtable(lt_user_data loader_data);
#endif

  
  ORTHANC_PLUGINS_API int32_t OrthancPluginInitialize(OrthancPluginContext* context)
  {
#if ORTHANC_PLUGINS_VERSION_IS_ABOVE(1, 12, 0)
    GOOGLE_PROTOBUF_VERIFY_VERSION;
#endif

    if (!OrthancDatabases::InitializePlugin(context, ORTHANC_PLUGIN_NAME, "ODBC", true))
    {
      return -1;
    }

#if !defined(_WIN32)
    lt_dlinit();
    
    /**
     * The following call is necessary for "libltdl" to access the
     * "dlopen()" primitives if statically linking. Otherwise, only the
     * "preopen" primitives are available.
     **/
    lt_dlloader_add(dlopen_LTX_get_vtable(NULL));
#endif
    
    OrthancPlugins::OrthancConfiguration configuration;

    if (!configuration.IsSection(KEY_ODBC))
    {
      LOG(WARNING) << "No available configuration for the ODBC index plugin";
      return 0;
    }

    OrthancPlugins::OrthancConfiguration odbc;
    configuration.GetSection(odbc, KEY_ODBC);

    bool enable;
    if (!odbc.LookupBooleanValue(enable, "EnableIndex") ||
        !enable)
    {
      LOG(WARNING) << "The ODBC index is currently disabled, set \"EnableIndex\" "
                   << "to \"true\" in the \"" << KEY_ODBC << "\" section of the configuration file of Orthanc";
      return 0;
    }

    OrthancDatabases::OdbcEnvironment::GlobalInitialization();

    try
    {
      const std::string connectionString = odbc.GetStringValue("IndexConnectionString", "");
      const unsigned int countConnections = odbc.GetUnsignedIntegerValue("IndexConnectionsCount", 1);
      const unsigned int maxConnectionRetries = odbc.GetUnsignedIntegerValue("MaximumConnectionRetries", 10);
      const unsigned int connectionRetryInterval = odbc.GetUnsignedIntegerValue("ConnectionRetryInterval", 5);
      const unsigned int housekeepingDelaySeconds = 5;  // TODO - PARAMETER

      if (connectionString.empty())
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange,
                                        "No connection string provided for the ODBC index");
      }

      bool readOnly = configuration.GetBooleanValue("ReadOnly", false);

      if (readOnly)
      {
        LOG(WARNING) << "READ-ONLY SYSTEM: the Database plugin is working in read-only mode";
      }

      std::unique_ptr<OrthancDatabases::OdbcIndex> index(new OrthancDatabases::OdbcIndex(context, connectionString, readOnly));
      index->SetMaxConnectionRetries(maxConnectionRetries);
      index->SetConnectionRetryInterval(connectionRetryInterval);

      OrthancDatabases::IndexBackend::Register(index.release(),
                                               countConnections,
                                               false /* useDynamicConnectionPool */,
                                               maxConnectionRetries,
                                               housekeepingDelaySeconds);
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
    LOG(WARNING) << "ODBC index is finalizing";
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
