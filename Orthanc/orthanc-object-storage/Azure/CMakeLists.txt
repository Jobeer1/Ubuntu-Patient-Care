# Cloud storage plugins for Orthanc
# Copyright (C) 2020-2023 Osimis S.A., Belgium
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


cmake_minimum_required(VERSION 3.3)

project(OrthancAzureBlobStorage)

set(PLUGIN_VERSION "mainline")

if (PLUGIN_VERSION STREQUAL "mainline")
  set(ORTHANC_FRAMEWORK_DEFAULT_VERSION "mainline")
  set(ORTHANC_FRAMEWORK_DEFAULT_SOURCE "hg")
else()
  set(ORTHANC_FRAMEWORK_DEFAULT_VERSION "1.12.4")
  set(ORTHANC_FRAMEWORK_DEFAULT_SOURCE "web")
endif()

set(ORTHANC_FRAMEWORK_SOURCE "${ORTHANC_FRAMEWORK_DEFAULT_SOURCE}" CACHE STRING "Source of the Orthanc framework (can be \"system\", \"hg\", \"archive\", \"web\" or \"path\")")
set(ORTHANC_FRAMEWORK_VERSION "${ORTHANC_FRAMEWORK_DEFAULT_VERSION}" CACHE STRING "Version of the Orthanc framework")
set(ORTHANC_FRAMEWORK_ARCHIVE "" CACHE STRING "Path to the Orthanc archive, if ORTHANC_FRAMEWORK_SOURCE is \"archive\"")
set(ORTHANC_FRAMEWORK_ROOT "" CACHE STRING "Path to the Orthanc source directory, if ORTHANC_FRAMEWORK_SOURCE is \"path\"")
set(ALLOW_DOWNLOADS ON)

include(CheckIncludeFileCXX)

# Download and setup the Orthanc framework

include(${CMAKE_SOURCE_DIR}/../Common/Resources/Orthanc/CMake/DownloadOrthancFramework.cmake)
include(${ORTHANC_FRAMEWORK_ROOT}/../Resources/CMake/OrthancFrameworkParameters.cmake)

set(ENABLE_GOOGLE_TEST ON)
set(ORTHANC_FRAMEWORK_PLUGIN ON)
set(ENABLE_MODULE_IMAGES OFF)
set(ENABLE_MODULE_JOBS OFF)
set(ENABLE_MODULE_DICOM OFF)

include(${ORTHANC_FRAMEWORK_ROOT}/../Resources/CMake/OrthancFrameworkConfiguration.cmake)
include(${ORTHANC_FRAMEWORK_ROOT}/../../OrthancServer/Plugins/Samples/Common/OrthancPluginsExports.cmake)

add_definitions(
    -DHAS_ORTHANC_EXCEPTION=1
    -DORTHANC_ENABLE_LOGGING=1
    -DAZURE_STORAGE_PLUGIN=1
    )
add_definitions(-DPLUGIN_VERSION="${PLUGIN_VERSION}")

include_directories(
  ${ORTHANC_FRAMEWORK_ROOT}
  ${ORTHANC_FRAMEWORK_ROOT}/../../OrthancServer/Plugins/Include
  ${ORTHANC_FRAMEWORK_ROOT}/../../OrthancServer/Plugins/Samples/Common
  )

find_package(cryptopp CONFIG REQUIRED)

# Azure stuff (from https://github.com/Microsoft/vcpkg/issues/6277)
find_package(azure-storage-blobs-cpp CONFIG REQUIRED)

# if (NOT WIN32)
#   find_package(cpprestsdk CONFIG REQUIRED)
#   find_path(WASTORAGE_INCLUDE_DIR was/blob.h)
#   find_library(WASTORAGE_LIBRARY azurestorage)
#   find_package(Boost REQUIRED COMPONENTS log)
#   find_library(UUID_LIBRARY uuid)
#   find_package(LibXml2 REQUIRED)
# else()  # inspired from https://github.com/phongcao/azure-storage-cpp-sas-sample/blob/master/CMakeLists.txt
#   find_path(WASTORAGE_INCLUDE_DIR was/blob.h)
#   find_library(CPPREST_LIBRARY
#     NAMES cpprest cpprest_2_10)
#   find_library(WASTORAGE_LIBRARY wastorage)

#   set (CMAKE_CXX_STANDARD 11)
#   set (CMAKE_CXX_STANDARD_REQUIRED ON)
#   set (CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} /EHa")
#   set (CMAKE_CXX_FLAGS_RELEASE "${CMAKE_CXX_FLAGS_RELEASE} /Zi")
#   set (CMAKE_SHARED_LINKER_FLAGS_RELEASE "${CMAKE_SHARED_LINKER_FLAGS_RELEASE} /DEBUG /OPT:REF /OPT:ICF")

#   message(INFO "WASTORAGE_INCLUDE_DIR ${WASTORAGE_INCLUDE_DIR}")

#   add_definitions(-D_NO_WASTORAGE_API=1)   # from https://github.com/Azure/azure-storage-cpp/issues/263
# endif()

# include_directories(${WASTORAGE_INCLUDE_DIR})
set(CMAKE_CXX_STANDARD 14)

set(COMMON_SOURCES
    ${CMAKE_SOURCE_DIR}/../Common/IStorage.h
    ${CMAKE_SOURCE_DIR}/../Common/BaseStorage.h
    ${CMAKE_SOURCE_DIR}/../Common/BaseStorage.cpp
    ${CMAKE_SOURCE_DIR}/../Common/EncryptionHelpers.cpp
    ${CMAKE_SOURCE_DIR}/../Common/EncryptionHelpers.h
    ${CMAKE_SOURCE_DIR}/../Common/EncryptionConfigurator.cpp
    ${CMAKE_SOURCE_DIR}/../Common/EncryptionConfigurator.h
    ${CMAKE_SOURCE_DIR}/../Common/FileSystemStorage.h
    ${CMAKE_SOURCE_DIR}/../Common/FileSystemStorage.cpp
    ${CMAKE_SOURCE_DIR}/../Common/MoveStorageJob.h
    ${CMAKE_SOURCE_DIR}/../Common/MoveStorageJob.cpp
    ${ORTHANC_FRAMEWORK_ROOT}/../../OrthancServer/Plugins/Samples/Common/OrthancPluginCppWrapper.cpp

    ${ORTHANC_CORE_SOURCES}
  )

add_library(OrthancAzureBlobStorage SHARED
    AzureBlobStoragePlugin.cpp
    AzureBlobStoragePlugin.h
    ${CMAKE_SOURCE_DIR}/../Common/StoragePlugin.cpp

    ${COMMON_SOURCES}
  )

if (COMMAND DefineSourceBasenameForTarget)
  DefineSourceBasenameForTarget(OrthancAzureBlobStorage)
endif()

set_target_properties(OrthancAzureBlobStorage PROPERTIES
  VERSION ${PLUGIN_VERSION}
  SOVERSION ${PLUGIN_VERSION}
  )

if (NOT WIN32)

  target_link_libraries(OrthancAzureBlobStorage
    PRIVATE
    cryptopp::cryptopp
    Azure::azure-storage-blobs
    ${UUID_LIBRARY} 
    ${LIBXML2_LIBRARIES} 
    )
else()
  target_link_libraries(OrthancAzureBlobStorage
    PRIVATE
    cryptopp::cryptopp
    Azure::azure-storage-blobs
    ${OPENSSL_LIBRARY}
    Winhttp.lib
    Crypt32.lib
    xmllite.lib
  )

endif()

install(
  TARGETS OrthancAzureBlobStorage
  RUNTIME DESTINATION lib    # Destination for Windows
  LIBRARY DESTINATION share/orthanc/plugins    # Destination for Linux
)


# add_executable(UnitTests
#     ${GOOGLE_TEST_SOURCES}
#     ${COMMON_SOURCES}

#     ${CMAKE_SOURCE_DIR}/../UnitTestsSources/EncryptionTests.cpp
#     ${CMAKE_SOURCE_DIR}/../UnitTestsSources/UnitTestsMain.cpp
#     )

# target_link_libraries(UnitTests
#   PRIVATE
#   cryptopp-static
#   ${GOOGLE_TEST_LIBRARIES}
#   ${WASTORAGE_LIBRARY} 
#   # ${UUID_LIBRARY} 
#   # ${Boost_LIBRARIES} 
#   # ${LIBXML2_LIBRARIES} 
#   cpprestsdk::cpprest
#   )
