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

#if defined(_WIN32)
#  include <windows.h>  // Used in "sql.h"
#endif

#include <boost/noncopyable.hpp>
#include <sql.h>
#include <string>


namespace OrthancDatabases
{
  class OdbcEnvironment : public boost::noncopyable
  {
  private:
    SQLHENV  handle_;

  public:
    OdbcEnvironment();

    virtual ~OdbcEnvironment();

    SQLHENV GetHandle()
    {
      return handle_;
    }

    static std::string FormatError(SQLHANDLE handle,
                                   SQLSMALLINT type);

    static void GlobalInitialization();
  };
}
