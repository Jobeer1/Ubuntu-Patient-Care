# Orthanc - A Lightweight, RESTful DICOM Store
# Copyright (C) 2012-2016 Sebastien Jodogne, Medical Physics
# Department, University Hospital of Liege, Belgium
# Copyright (C) 2017-2023 Osimis S.A., Belgium
# Copyright (C) 2024-2025 Orthanc Team SRL, Belgium
# Copyright (C) 2021-2025 Sebastien Jodogne, ICTEAM UCLouvain, Belgium
#
# This program is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License
# as published by the Free Software Foundation, either version 3 of
# the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.



#####################################################################
## Enable the Orthanc subcomponents depending on the configuration
#####################################################################

if (ENABLE_SQLITE_BACKEND)
  set(ENABLE_SQLITE ON)
endif()

if (ENABLE_POSTGRESQL_BACKEND)
  set(ENABLE_CRYPTO_OPTIONS ON)
  set(ENABLE_ZLIB ON)
  set(ENABLE_OPENSSL_ENGINES ON)
endif()

if (ENABLE_MYSQL_BACKEND)
  set(ENABLE_CRYPTO_OPTIONS ON)
  set(ENABLE_SSL ON)
  set(ENABLE_ZLIB ON)
  set(ENABLE_LOCALE ON)      # iconv is needed
  set(ENABLE_WEB_CLIENT ON)  # libcurl is needed
  set(ENABLE_OPENSSL_ENGINES ON)
endif()

if (ENABLE_ODBC_BACKEND)
endif()
  


#####################################################################
## Configure the Orthanc Framework
#####################################################################

if (ORTHANC_FRAMEWORK_SOURCE STREQUAL "system")
  if (ORTHANC_FRAMEWORK_USE_SHARED)
    # https://cmake.org/cmake/help/latest/policy/CMP0167.html
    if (CMAKE_VERSION VERSION_GREATER "3.30")
      find_package(Boost CONFIG)
    else()
      include(FindBoost)
    endif()

    find_package(Boost COMPONENTS regex thread)
    
    if (NOT Boost_FOUND)
      message(FATAL_ERROR "Unable to locate Boost on this system")
    endif()
    
    link_libraries(${Boost_LIBRARIES} jsoncpp)
  endif()

  link_libraries(${ORTHANC_FRAMEWORK_LIBRARIES})

  if (ENABLE_SQLITE_BACKEND)
    add_definitions(-DORTHANC_ENABLE_SQLITE=1)
  endif()

  # These parameters should *NOT* be modified by the user: System-wide
  # installations expect only dynamic linking
  set(USE_SYSTEM_GOOGLE_TEST ON CACHE BOOL "Use the system version of Google Test")
  set(USE_SYSTEM_OPENSSL ON CACHE BOOL "Use the system version of OpenSSL")
  set(USE_SYSTEM_PROTOBUF ON CACHE BOOL "Use the system version of Google Protocol Buffers")

  set(USE_GOOGLE_TEST_DEBIAN_PACKAGE OFF CACHE BOOL "Use the sources of Google Test shipped with libgtest-dev (Debian only)")
  mark_as_advanced(USE_GOOGLE_TEST_DEBIAN_PACKAGE)

  set(ENABLE_OPENSSL_ENGINES ON CACHE INTERNAL "")

  include(${CMAKE_CURRENT_LIST_DIR}/../Orthanc/CMake/GoogleTestConfiguration.cmake)
  include(${CMAKE_CURRENT_LIST_DIR}/../Orthanc/CMake/OpenSslConfiguration.cmake)
  include(${CMAKE_CURRENT_LIST_DIR}/../Orthanc/CMake/ProtobufConfiguration.cmake)
  
else()
  # Those modules of the Orthanc framework are not needed when dealing
  # with databases
  set(ENABLE_MODULE_IMAGES OFF)
  set(ENABLE_MODULE_JOBS OFF)
  set(ENABLE_MODULE_DICOM OFF)
  
  include(${ORTHANC_FRAMEWORK_ROOT}/../Resources/CMake/OrthancFrameworkConfiguration.cmake)
  include_directories(${ORTHANC_FRAMEWORK_ROOT})
endif()



#####################################################################
## Common source files for the databases
#####################################################################

set(ORTHANC_DATABASES_ROOT ${CMAKE_CURRENT_LIST_DIR}/../..)

set(DATABASES_SOURCES
  ${ORTHANC_DATABASES_ROOT}/Framework/Common/BinaryStringValue.cpp
  ${ORTHANC_DATABASES_ROOT}/Framework/Common/DatabaseManager.cpp
  ${ORTHANC_DATABASES_ROOT}/Framework/Common/DatabasesEnumerations.cpp
  ${ORTHANC_DATABASES_ROOT}/Framework/Common/Dictionary.cpp
  ${ORTHANC_DATABASES_ROOT}/Framework/Common/GenericFormatter.cpp
  ${ORTHANC_DATABASES_ROOT}/Framework/Common/IResult.cpp
  ${ORTHANC_DATABASES_ROOT}/Framework/Common/ImplicitTransaction.cpp
  ${ORTHANC_DATABASES_ROOT}/Framework/Common/InputFileValue.cpp
  ${ORTHANC_DATABASES_ROOT}/Framework/Common/Integer32Value.cpp
  ${ORTHANC_DATABASES_ROOT}/Framework/Common/Integer64Value.cpp
  ${ORTHANC_DATABASES_ROOT}/Framework/Common/NullValue.cpp
  ${ORTHANC_DATABASES_ROOT}/Framework/Common/Query.cpp
  ${ORTHANC_DATABASES_ROOT}/Framework/Common/ResultBase.cpp
  ${ORTHANC_DATABASES_ROOT}/Framework/Common/ResultFileValue.cpp
  ${ORTHANC_DATABASES_ROOT}/Framework/Common/RetryDatabaseFactory.cpp
  ${ORTHANC_DATABASES_ROOT}/Framework/Common/RetryDatabaseFactory.cpp
  ${ORTHANC_DATABASES_ROOT}/Framework/Common/StatementId.cpp
  ${ORTHANC_DATABASES_ROOT}/Framework/Common/Utf8StringValue.cpp
  )


#####################################################################
## Configure SQLite if need be
#####################################################################

if (ENABLE_SQLITE_BACKEND)
  list(APPEND DATABASES_SOURCES
    ${ORTHANC_DATABASES_ROOT}/Framework/SQLite/SQLiteDatabase.cpp
    ${ORTHANC_DATABASES_ROOT}/Framework/SQLite/SQLiteResult.cpp
    ${ORTHANC_DATABASES_ROOT}/Framework/SQLite/SQLiteStatement.cpp
    ${ORTHANC_DATABASES_ROOT}/Framework/SQLite/SQLiteTransaction.cpp
    )
endif()


#####################################################################
## Configure MySQL client (MariaDB) if need be
#####################################################################

if (ENABLE_MYSQL_BACKEND)
  include(${CMAKE_CURRENT_LIST_DIR}/MariaDBConfiguration.cmake)
  add_definitions(-DORTHANC_ENABLE_MYSQL=1)
  list(APPEND DATABASES_SOURCES
    ${ORTHANC_DATABASES_ROOT}/Framework/MySQL/MySQLDatabase.cpp
    ${ORTHANC_DATABASES_ROOT}/Framework/MySQL/MySQLParameters.cpp
    ${ORTHANC_DATABASES_ROOT}/Framework/MySQL/MySQLResult.cpp
    ${ORTHANC_DATABASES_ROOT}/Framework/MySQL/MySQLStatement.cpp
    ${ORTHANC_DATABASES_ROOT}/Framework/MySQL/MySQLTransaction.cpp
    ${MYSQL_CLIENT_SOURCES}
    )
else()
  unset(USE_SYSTEM_MYSQL_CLIENT CACHE)
  add_definitions(-DORTHANC_ENABLE_MYSQL=0)
endif()



#####################################################################
## Configure PostgreSQL client if need be
#####################################################################

if (ENABLE_POSTGRESQL_BACKEND)
  include(${CMAKE_CURRENT_LIST_DIR}/PostgreSQLConfiguration.cmake)
  add_definitions(-DORTHANC_ENABLE_POSTGRESQL=1)
  list(APPEND DATABASES_SOURCES
    ${ORTHANC_DATABASES_ROOT}/Framework/PostgreSQL/PostgreSQLDatabase.cpp
    ${ORTHANC_DATABASES_ROOT}/Framework/PostgreSQL/PostgreSQLLargeObject.cpp
    ${ORTHANC_DATABASES_ROOT}/Framework/PostgreSQL/PostgreSQLParameters.cpp
    ${ORTHANC_DATABASES_ROOT}/Framework/PostgreSQL/PostgreSQLResult.cpp
    ${ORTHANC_DATABASES_ROOT}/Framework/PostgreSQL/PostgreSQLStatement.cpp
    ${ORTHANC_DATABASES_ROOT}/Framework/PostgreSQL/PostgreSQLTransaction.cpp
    ${LIBPQ_SOURCES}
    )
else()
  unset(USE_SYSTEM_LIBPQ CACHE)
  add_definitions(-DORTHANC_ENABLE_POSTGRESQL=0)
endif()



#####################################################################
## Configure ODBC if need be
#####################################################################

if (ENABLE_ODBC_BACKEND)
  if ("${CMAKE_SYSTEM_NAME}" STREQUAL "Windows")
    link_libraries(odbc32)
  else()
    include(${CMAKE_CURRENT_LIST_DIR}/UnixOdbcConfiguration.cmake)
  endif()
  
  add_definitions(-DORTHANC_ENABLE_ODBC=1)
  list(APPEND DATABASES_SOURCES
    ${ORTHANC_DATABASES_ROOT}/Framework/Odbc/OdbcDatabase.cpp
    ${ORTHANC_DATABASES_ROOT}/Framework/Odbc/OdbcEnvironment.cpp
    ${ORTHANC_DATABASES_ROOT}/Framework/Odbc/OdbcPreparedStatement.cpp
    ${ORTHANC_DATABASES_ROOT}/Framework/Odbc/OdbcResult.cpp
    ${ORTHANC_DATABASES_ROOT}/Framework/Odbc/OdbcStatement.cpp
    ${LIBPQ_SOURCES}
    )
else()
  unset(USE_SYSTEM_UNIX_ODBC)
  unset(USE_SYSTEM_LTDL)
  add_definitions(-DORTHANC_ENABLE_ODBC=0)
endif()
