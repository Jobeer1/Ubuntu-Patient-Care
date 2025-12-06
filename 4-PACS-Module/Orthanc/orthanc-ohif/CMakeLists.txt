# SPDX-FileCopyrightText: 2023-2025 Sebastien Jodogne, ICTEAM UCLouvain, Belgium
# SPDX-License-Identifier: GPL-3.0-or-later


# OHIF plugin for Orthanc
# Copyright (C) 2023-2025 Sebastien Jodogne, ICTEAM UCLouvain, Belgium
#
# This program is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.


cmake_minimum_required(VERSION 2.8...4.0)
project(OrthancOHIF)

set(ORTHANC_OHIF_VERSION "mainline")

if (ORTHANC_OHIF_VERSION STREQUAL "mainline")
  set(ORTHANC_FRAMEWORK_DEFAULT_VERSION "mainline")
  set(ORTHANC_FRAMEWORK_DEFAULT_SOURCE "hg")
else()
  set(ORTHANC_FRAMEWORK_DEFAULT_VERSION "1.12.5")
  set(ORTHANC_FRAMEWORK_DEFAULT_SOURCE "web")
endif()

set(METADATA_VERSION 2)


#####################################################################
## Parameters of the build
#####################################################################

# Generic parameters
SET(STATIC_BUILD OFF CACHE BOOL "Static build of the third-party libraries (necessary for Windows)")
SET(ALLOW_DOWNLOADS OFF CACHE BOOL "Allow CMake to download packages")
set(ORTHANC_FRAMEWORK_SOURCE "${ORTHANC_FRAMEWORK_DEFAULT_SOURCE}" CACHE STRING "Source of the Orthanc framework (can be \"system\", \"hg\", \"archive\", \"web\" or \"path\")")
set(ORTHANC_FRAMEWORK_VERSION "${ORTHANC_FRAMEWORK_DEFAULT_VERSION}" CACHE STRING "Version of the Orthanc framework")
set(ORTHANC_FRAMEWORK_ARCHIVE "" CACHE STRING "Path to the Orthanc archive, if ORTHANC_FRAMEWORK_SOURCE is \"archive\"")
set(ORTHANC_FRAMEWORK_ROOT "" CACHE STRING "Path to the Orthanc source directory, if ORTHANC_FRAMEWORK_SOURCE is \"path\"")

# Advanced parameters to fine-tune linking against system libraries
SET(USE_SYSTEM_ORTHANC_SDK ON CACHE BOOL "Use the system version of the Orthanc plugin SDK")


#####################################################################
## Download and setup the Orthanc framework
#####################################################################

include(${CMAKE_SOURCE_DIR}/Resources/Orthanc/CMake/DownloadOrthancFramework.cmake)

if (ORTHANC_FRAMEWORK_SOURCE STREQUAL "system")
  if (ORTHANC_FRAMEWORK_USE_SHARED)
    # https://cmake.org/cmake/help/latest/policy/CMP0167.html
    if (CMAKE_VERSION VERSION_GREATER "3.30")
      find_package(Boost CONFIG)
    else()
      include(FindBoost)
    endif()

    find_package(Boost COMPONENTS system thread)
    
    if (NOT Boost_FOUND)
      message(FATAL_ERROR "Unable to locate Boost on this system")
    endif()
    
    link_libraries(${Boost_LIBRARIES} jsoncpp)
  endif()
  
  link_libraries(${ORTHANC_FRAMEWORK_LIBRARIES})
  
else()
  include(${ORTHANC_FRAMEWORK_ROOT}/../Resources/CMake/OrthancFrameworkParameters.cmake)

  set(ENABLE_LOCALE OFF)         # Disable support for locales (notably in Boost)
  set(ENABLE_ZLIB ON)

  set(ENABLE_MODULE_DICOM ON CACHE INTERNAL "")
  set(ENABLE_MODULE_IMAGES OFF CACHE INTERNAL "")
  set(ENABLE_MODULE_JOBS OFF CACHE INTERNAL "")

  include(${ORTHANC_FRAMEWORK_ROOT}/../Resources/CMake/OrthancFrameworkConfiguration.cmake)
  include_directories(${ORTHANC_FRAMEWORK_ROOT})
endif()

include(${CMAKE_SOURCE_DIR}/Resources/Orthanc/Plugins/OrthancPluginsExports.cmake)


#####################################################################
## Find the Orthanc SDK
#####################################################################

if (STATIC_BUILD OR NOT USE_SYSTEM_ORTHANC_SDK)
  include_directories(${CMAKE_SOURCE_DIR}/Resources/Orthanc/Sdk-1.0.0)
else ()
  CHECK_INCLUDE_FILE_CXX(orthanc/OrthancCPlugin.h HAVE_ORTHANC_H)
  if (NOT HAVE_ORTHANC_H)
    message(FATAL_ERROR "Please install the headers of the Orthanc plugins SDK")
  endif()
endif()


#####################################################################
## Platform-specific configuration
#####################################################################

add_definitions(
  -DHAS_ORTHANC_EXCEPTION=1
  -DORTHANC_FRAMEWORK_BUILDING_PLUGIN=1
  -DORTHANC_OHIF_VERSION="${ORTHANC_OHIF_VERSION}"
  -DMETADATA_VERSION=${METADATA_VERSION}
  )

if (${CMAKE_SYSTEM_NAME} STREQUAL "Linux" OR
    ${CMAKE_SYSTEM_NAME} STREQUAL "kFreeBSD" OR
    ${CMAKE_SYSTEM_NAME} STREQUAL "FreeBSD")
  link_libraries(rt)

elseif (${CMAKE_SYSTEM_NAME} STREQUAL "Windows")
  execute_process(
    COMMAND 
    ${PYTHON_EXECUTABLE} ${ORTHANC_FRAMEWORK_ROOT}/../Resources/WindowsResources.py
    ${ORTHANC_OHIF_VERSION} "OrthancOHIF" OrthancOHIF.dll "OHIF plugin for Orthanc"
    ERROR_VARIABLE Failure
    OUTPUT_FILE ${AUTOGENERATED_DIR}/Version.rc
    )

  if (Failure)
    message(FATAL_ERROR "Error while computing the version information: ${Failure}")
  endif()

  list(APPEND AUTOGENERATED_SOURCES  ${AUTOGENERATED_DIR}/Version.rc)
endif()

if (APPLE)
  SET(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -framework CoreFoundation")
  SET(CMAKE_SHARED_LINKER_FLAGS "${CMAKE_SHARED_LINKER_FLAGS} -framework CoreFoundation")
endif()


#####################################################################
## Create the autogenerated files
#####################################################################

EmbedResources(
  APP_CONFIG_SYSTEM  ${CMAKE_SOURCE_DIR}/Sources/app-config-system.js
  APP_CONFIG_USER    ${CMAKE_SOURCE_DIR}/Sources/app-config-user.js
  ORTHANC_EXPLORER   ${CMAKE_SOURCE_DIR}/Sources/OrthancExplorer.js
  )

add_custom_command(
  OUTPUT
  ${AUTOGENERATED_DIR}/StaticAssets.cpp
  COMMAND
  ${PYTHON_EXECUTABLE}
  ${CMAKE_SOURCE_DIR}/Resources/EmbedStaticAssets.py
  ${CMAKE_SOURCE_DIR}/OHIF/dist
  ${AUTOGENERATED_DIR}/StaticAssets.cpp
  DEPENDS
  ${CMAKE_SOURCE_DIR}/OHIF/dist
  ${CMAKE_SOURCE_DIR}/Resources/EmbedStaticAssets.py
  )

list(APPEND AUTOGENERATED_SOURCES 
  ${AUTOGENERATED_DIR}/StaticAssets.cpp
  )

add_custom_target(
  AutogeneratedTarget
  DEPENDS 
  ${AUTOGENERATED_SOURCES}
  )


#####################################################################
## Create the plugin
#####################################################################

add_library(OrthancOHIF SHARED
  Sources/Plugin.cpp
  ${AUTOGENERATED_SOURCES}
  ${CMAKE_SOURCE_DIR}/Resources/Orthanc/Plugins/OrthancPluginCppWrapper.cpp
  ${ORTHANC_CORE_SOURCES_DEPENDENCIES}
  ${ORTHANC_CORE_SOURCES_INTERNAL}
  ${ORTHANC_OHIF_SOURCES}
  )

add_dependencies(OrthancOHIF AutogeneratedTarget)

message("Setting the version of the library to ${ORTHANC_OHIF_VERSION}")

set_target_properties(OrthancOHIF PROPERTIES 
  VERSION ${ORTHANC_OHIF_VERSION} 
  SOVERSION ${ORTHANC_OHIF_VERSION})

if (COMMAND DefineSourceBasenameForTarget)
  DefineSourceBasenameForTarget(OrthancOHIF)
endif()

install(
  TARGETS OrthancOHIF
  RUNTIME DESTINATION lib    # Destination for Windows
  LIBRARY DESTINATION share/orthanc/plugins    # Destination for Linux
  )
