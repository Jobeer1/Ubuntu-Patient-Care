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


#include "../Plugins/OdbcIndex.h"

static std::string connectionString_;

#include "../../Framework/Odbc/OdbcEnvironment.h"
#include "../../Framework/Plugins/IndexUnitTests.h"

#include <Logging.h>


#if defined(_WIN32)
#  include <windows.h>
#else
#  include <ltdl.h>
#  include <libltdl/lt_dlloader.h>
#endif


#if !defined(_WIN32)
extern "C"
{
  extern lt_dlvtable *dlopen_LTX_get_vtable(lt_user_data loader_data);
}
#endif


int main(int argc, char **argv)
{
  if (argc < 2)
  {
    std::cerr
      << std::endl
      << "Usage:    " << argv[0] << " <connection string>"
      << std::endl << std::endl
      << "Example:  " << argv[0] << " \"DSN=test\""
      << std::endl << std::endl;
    return -1;
  }

  for (int i = 1; i < argc; i++)
  {
    // Ignore arguments beginning with "-" to allow passing arguments
    // to Google Test such as "--gtest_filter="
    if (argv[i] != NULL &&
        argv[i][0] != '-')
    {
      connectionString_ = argv[i];
    }
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

  ::testing::InitGoogleTest(&argc, argv);
  Orthanc::Logging::Initialize();
  Orthanc::Logging::EnableInfoLevel(true);
  //Orthanc::Logging::EnableTraceLevel(true);

  OrthancDatabases::OdbcEnvironment::GlobalInitialization();

  int result = RUN_ALL_TESTS();
  
  Orthanc::Logging::Finalize();

  return result;
}
