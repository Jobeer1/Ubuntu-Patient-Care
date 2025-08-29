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

// These includes are necessary for compilation on OS X
#include <unistd.h>
#include <vector>
#include <map>
#include <cmath>
#include <Enumerations.h>

// Get "ntohl()" defined
#if defined(_WIN32)
#  include <winsock.h>
#else
#  include <arpa/inet.h>
#endif

// PostgreSQL includes
#include <pg_config.h>

#if !defined(PG_VERSION_NUM)
#  error PG_VERSION_NUM is not defined
#endif

#if PG_VERSION_NUM >= 110000
#  include <catalog/pg_type_d.h>
#else
#  include <postgres.h>
#  undef LOG  // This one comes from <postgres.h>, and conflicts with <Core/Logging.h>
#  include <catalog/pg_type.h>
#endif

#include <libpq-fe.h>
