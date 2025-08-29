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



#pragma once

#include "IndexBackend.h"


#if defined(ORTHANC_PLUGINS_VERSION_IS_ABOVE)         // Macro introduced in Orthanc 1.3.1
#  if ORTHANC_PLUGINS_VERSION_IS_ABOVE(1, 9, 2)

namespace OrthancDatabases
{  
  /**
   * @brief Bridge between C and C++ database engines.
   * 
   * Class creating the bridge between the C low-level primitives for
   * custom database engines, and the high-level IDatabaseBackend C++
   * interface, for Orthanc >= 1.9.2.
   **/
  class DatabaseBackendAdapterV3
  {
  private:
    class Output;
    
    // This class cannot be instantiated
    DatabaseBackendAdapterV3()
    {
    }

  public:
    class Transaction;

    class Factory : public IDatabaseBackendOutput::IFactory
    {
    public:
      virtual IDatabaseBackendOutput* CreateOutput() ORTHANC_OVERRIDE;
    };

    static void Register(IndexBackend* backend,
                         size_t countConnections,
                         unsigned int maxDatabaseRetries,
                         unsigned int housekeepingDelaySeconds);

    static void Finalize();
  };
}

#  endif
#endif
