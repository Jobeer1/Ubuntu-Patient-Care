# SPDX-FileCopyrightText: 2020-2023 Osimis S.A., 2024-2025 Orthanc Team SRL, 2021-2025 Sebastien Jodogne, ICTEAM UCLouvain
# SPDX-License-Identifier: AGPL-3.0-or-later

##
## Python plugin for Orthanc
## Copyright (C) 2020-2023 Osimis S.A., Belgium
## Copyright (C) 2024-2025 Orthanc Team SRL, Belgium
## Copyright (C) 2021-2025 Sebastien Jodogne, ICTEAM UCLouvain, Belgium
##
## This program is free software: you can redistribute it and/or
## modify it under the terms of the GNU Affero General Public License
## as published by the Free Software Foundation, either version 3 of
## the License, or (at your option) any later version.
##
## This program is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## Affero General Public License for more details.
##
## You should have received a copy of the GNU Affero General Public License
## along with this program. If not, see <http://www.gnu.org/licenses/>.
##


cmake_minimum_required(VERSION 2.8)
project(OrthancPython)

set(PLUGIN_VERSION "mainline")

if (PLUGIN_VERSION STREQUAL "mainline")
  set(ORTHANC_FRAMEWORK_DEFAULT_VERSION "mainline")
  set(ORTHANC_FRAMEWORK_DEFAULT_SOURCE "hg")
else()
  set(ORTHANC_FRAMEWORK_DEFAULT_VERSION "1.12.9")
  set(ORTHANC_FRAMEWORK_DEFAULT_SOURCE "web")
endif()

set(ORTHANC_SDK_DEFAULT_VERSION "1.12.9")

# This list must correspond to the content of "./Resources/SyncOrthancFolder.py"
set(ORTHANC_SDK_AVAILABLE_VERSIONS "1.7.2" "1.10.0" "1.12.6" "1.12.9")


#####################################################################
## Parameters of the build
#####################################################################

if (NOT ${CMAKE_SYSTEM_NAME} STREQUAL "Darwin")
  # The Python version cannot be controlled on OS X (yet)
  set(PYTHON_VERSION "3.13" CACHE STRING "Version of Python to be used")
endif()

if (${CMAKE_SYSTEM_NAME} STREQUAL "Windows")
  # Windows-specific options
  set(PYTHON_WINDOWS_ROOT "" CACHE STRING "")
  set(PYTHON_LIBRARY_NAME "" CACHE STRING "")
  set(PYTHON_WINDOWS_USE_RELEASE_LIBS ON CACHE BOOL "Use the release Python libraries when building with Microsoft Visual Studio, even when compiling in _DEBUG mode (set it to OFF if you require linking to a Python debug build)")
endif()

# Generic parameters
set(STATIC_BUILD OFF CACHE BOOL "Static build of the third-party libraries (necessary for Windows)")
set(ALLOW_DOWNLOADS OFF CACHE BOOL "Allow CMake to download packages")
set(ORTHANC_FRAMEWORK_SOURCE "${ORTHANC_FRAMEWORK_DEFAULT_SOURCE}" CACHE STRING "Source of the Orthanc framework (can be \"system\", \"hg\", \"archive\", \"web\" or \"path\")")
set(ORTHANC_FRAMEWORK_VERSION "${ORTHANC_FRAMEWORK_DEFAULT_VERSION}" CACHE STRING "Version of the Orthanc framework")
set(ORTHANC_FRAMEWORK_ARCHIVE "" CACHE STRING "Path to the Orthanc archive, if ORTHANC_FRAMEWORK_SOURCE is \"archive\"")
set(ORTHANC_FRAMEWORK_ROOT "" CACHE STRING "Path to the Orthanc source directory, if ORTHANC_FRAMEWORK_SOURCE is \"path\"")

# Advanced parameters to fine-tune linking against system libraries
set(USE_SYSTEM_ORTHANC_SDK ON CACHE BOOL "Use the system-wide version of the Orthanc plugin SDK")

# Generate the documentation about the "ORTHANC_SDK_VERSION" option
set(tmp "Version of the Orthanc plugin SDK to use, if not using the system version (can be")
foreach(version IN LISTS ORTHANC_SDK_AVAILABLE_VERSIONS)
  set(tmp "${tmp} ${version},")
endforeach()
set(tmp "${tmp} \"framework\", or \"path\")")

set(ORTHANC_SDK_VERSION "${ORTHANC_SDK_DEFAULT_VERSION}" CACHE STRING "${tmp}")
set(ORTHANC_SDK_PATH "" CACHE STRING "Path to the orthanc/OrthancCPlugin.h file, if ORTHANC_SDK_VERSION is set to \"path\"")


#####################################################################
## Download and setup the Orthanc framework
#####################################################################

include(${CMAKE_SOURCE_DIR}/Resources/Orthanc/CMake/DownloadOrthancFramework.cmake)

if (ORTHANC_FRAMEWORK_SOURCE STREQUAL "system")
  include(FindBoost)
  find_package(Boost COMPONENTS filesystem regex thread)

  if (NOT Boost_FOUND)
    message(FATAL_ERROR "Unable to locate Boost on this system")
  endif()

  link_libraries(${Boost_LIBRARIES} jsoncpp)

else()
  include(${ORTHANC_FRAMEWORK_ROOT}/../Resources/CMake/OrthancFrameworkParameters.cmake)

  set(ENABLE_MODULE_IMAGES OFF CACHE INTERNAL "")
  set(ENABLE_MODULE_JOBS OFF CACHE INTERNAL "")
  set(ENABLE_MODULE_DICOM OFF CACHE INTERNAL "")

  include(${ORTHANC_FRAMEWORK_ROOT}/../Resources/CMake/OrthancFrameworkConfiguration.cmake)
  include_directories(${ORTHANC_FRAMEWORK_ROOT})
endif()


include(${CMAKE_SOURCE_DIR}/Resources/Orthanc/Plugins/OrthancPluginsExports.cmake)


#####################################################################
## Configure the Python library
#####################################################################

include(CheckIncludeFile)
include(CheckIncludeFileCXX)
include(CheckIncludeFiles)
include(CheckLibraryExists)

if(CMAKE_VERSION VERSION_GREATER "3.11")
  find_package(Python REQUIRED COMPONENTS Interpreter)
  set(PYTHON_EXECUTABLE ${Python_EXECUTABLE})
else()
  include(FindPythonInterp)
  find_package(PythonInterp REQUIRED)
endif()


if (${CMAKE_SYSTEM_NAME} STREQUAL "Darwin")
  find_package(PythonLibs)
  if (NOT PYTHONLIBS_FOUND)
    message(FATAL_ERROR "Cannot find the Python libraries")
  endif()

  message("Python library - Found version: ${PYTHONLIBS_VERSION_STRING}")
  message("Python library - Path to include directory: ${PYTHON_INCLUDE_DIRS}")
  message("Python library - Shared library: ${PYTHON_LIBRARIES}")

else()
  string(REGEX REPLACE "^([0-9]*)\\.([0-9]*)$" "\\1" PYTHON_VERSION_MAJOR ${PYTHON_VERSION})
  string(REGEX REPLACE "^([0-9]*)\\.([0-9]*)$" "\\2" PYTHON_VERSION_MINOR ${PYTHON_VERSION})

  if (NOT PYTHON_VERSION STREQUAL
      "${PYTHON_VERSION_MAJOR}.${PYTHON_VERSION_MINOR}")
    message(FATAL_ERROR "Error in the (x.y) format of the Python version: ${PYTHON_VERSION}")
  endif()

  if (${CMAKE_SYSTEM_NAME} STREQUAL "Windows")
    if ("${PYTHON_LIBRARY_NAME}" STREQUAL "")
      if (MSVC)
        set(Prefix "")
        set(Suffix ".lib")
        if(PYTHON_WINDOWS_USE_RELEASE_LIBS)
          add_definitions(-DORTHANC_PYTHON_WINDOWS_USE_RELEASE_LIBS=1)
        endif()
      else()
        list(GET CMAKE_FIND_LIBRARY_PREFIXES 0 Prefix)
        set(Suffix ".a")
      endif()
      
      set(PYTHON_LIBRARY_NAME ${Prefix}python${PYTHON_VERSION_MAJOR}${PYTHON_VERSION_MINOR}${Suffix})
    endif()
    
    if (CMAKE_COMPILER_IS_GNUCXX AND
        "${CMAKE_SIZEOF_VOID_P}" STREQUAL "8" AND
        "${PYTHON_VERSION}" STREQUAL "2.7")
      # Fix for MinGW 64bit: https://stackoverflow.com/a/19867426/881731
      add_definitions(-DMS_WIN64)
    endif()
    
    set(PYTHON_INCLUDE_DIRS ${PYTHON_WINDOWS_ROOT}/include)
    set(PYTHON_LIBRARIES ${PYTHON_WINDOWS_ROOT}/libs/${PYTHON_LIBRARY_NAME})
    
    execute_process(
      COMMAND 
      ${PYTHON_EXECUTABLE} ${ORTHANC_FRAMEWORK_ROOT}/../Resources/WindowsResources.py
      ${PLUGIN_VERSION} "Python plugin" OrthancPython.dll
      "Plugin to create Orthanc plugins using Python"
      ERROR_VARIABLE Failure
      OUTPUT_FILE ${CMAKE_CURRENT_BINARY_DIR}/Version.rc
      )

    if (Failure)
      message(FATAL_ERROR "Error while computing the version information: ${Failure}")
    endif()

    list(APPEND AUTOGENERATED_SOURCES
      ${CMAKE_CURRENT_BINARY_DIR}/Version.rc
      )

  else()
    find_package(PkgConfig REQUIRED)
    pkg_check_modules(PYTHON_1 python-${PYTHON_VERSION}-embed)

    if (PYTHON_1_FOUND)
      set(PYTHON_INCLUDE_DIRS ${PYTHON_1_INCLUDE_DIRS})
      set(PYTHON_LIBRARIES ${PYTHON_1_LIBRARIES})
    else()
      pkg_check_modules(PYTHON_2 REQUIRED python-${PYTHON_VERSION})
      set(PYTHON_INCLUDE_DIRS ${PYTHON_2_INCLUDE_DIRS})
      set(PYTHON_LIBRARIES ${PYTHON_2_LIBRARIES})
    endif()
  endif()
endif()


#####################################################################
## Find the Orthanc SDK
#####################################################################

if (STATIC_BUILD OR NOT USE_SYSTEM_ORTHANC_SDK)
  if (ORTHANC_SDK_VERSION STREQUAL "framework")
    include_directories(${ORTHANC_FRAMEWORK_ROOT}/../../OrthancServer/Plugins/Include)
    set(ORTHANC_SDK ${ORTHANC_FRAMEWORK_ROOT}/../../OrthancServer/Plugins/Include/orthanc/OrthancCPlugin.h)

  elseif (ORTHANC_SDK_VERSION STREQUAL "path")
    include_directories(${ORTHANC_SDK_PATH})
    set(ORTHANC_SDK ${ORTHANC_SDK_PATH}/orthanc/OrthancCPlugin.h)

  else()
    list(FIND ORTHANC_SDK_AVAILABLE_VERSIONS ${ORTHANC_SDK_VERSION} tmp)
    if (tmp EQUAL -1)
      message(FATAL_ERROR "The source distribution of this plugin does not contain Orthanc SDK ${ORTHANC_SDK_VERSION}")
    endif()

    include_directories(${CMAKE_SOURCE_DIR}/Resources/Orthanc/Sdk-${ORTHANC_SDK_VERSION})
    set(ORTHANC_SDK ${CMAKE_SOURCE_DIR}/Resources/Orthanc/Sdk-${ORTHANC_SDK_VERSION}/orthanc/OrthancCPlugin.h)
  endif()

else()
  find_path(ORTHANC_SDK_SYSTEM_DIR OrthancCPlugin.h
    /usr/
    /usr/local/
    PATH_SUFFIXES include/orthanc
    )

  if (${ORTHANC_SDK_SYSTEM_DIR} STREQUAL "ORTHANC_SDK_SYSTEM_DIR-NOTFOUND")
    message(FATAL_ERROR "Cannot locate the orthanc/OrthancCPlugin.h header")
  endif()

  set(ORTHANC_SDK ${ORTHANC_SDK_SYSTEM_DIR}/OrthancCPlugin.h)
endif()


#####################################################################
## Auto-generate the wrapper
#####################################################################

set(ORTHANC_CODE_MODEL ${CMAKE_SOURCE_DIR}/Resources/Orthanc/OrthancPluginCodeModel.json)

add_custom_command(
  OUTPUT
  ${CMAKE_CURRENT_BINARY_DIR}/orthanc.pyi
  ${AUTOGENERATED_DIR}/sdk/sdk.cpp
  ${AUTOGENERATED_DIR}/sdk/sdk.h

  COMMAND
  ${PYTHON_EXECUTABLE}
  ${CMAKE_SOURCE_DIR}/CodeAnalysis/GenerateOrthancSDK.py
  --sdk ${ORTHANC_SDK}
  --model ${ORTHANC_CODE_MODEL}
  --target ${AUTOGENERATED_DIR}/sdk/

  COMMAND
  ${CMAKE_COMMAND} -E copy
  ${AUTOGENERATED_DIR}/sdk/orthanc.pyi
  ${CMAKE_CURRENT_BINARY_DIR}/orthanc.pyi

  DEPENDS
  ${CMAKE_SOURCE_DIR}/CodeAnalysis/
  ${ORTHANC_SDK}
  ${ORTHANC_CODE_MODEL}
  )

list(APPEND AUTOGENERATED_SOURCES
  ${AUTOGENERATED_DIR}/sdk/sdk.cpp
  )

add_custom_target(
  AutogeneratedTarget
  DEPENDS
  ${AUTOGENERATED_SOURCES}
  )



#####################################################################
## Build the plugin
#####################################################################

add_definitions(
  -DHAS_ORTHANC_EXCEPTION=0
  )

include_directories(
  ${AUTOGENERATED_DIR}/sdk/
  ${CMAKE_SOURCE_DIR}/Resources/Orthanc/Plugins/
  ${CMAKE_SOURCE_DIR}/Sources/
  ${PYTHON_INCLUDE_DIRS}
  )

add_library(OrthancPython SHARED
  ${AUTOGENERATED_SOURCES}
  Sources/DicomScpCallbacks.cpp
  Sources/ICallbackRegistration.cpp
  Sources/IncomingHttpRequestFilter.cpp
  Sources/IncomingInstanceFilter.cpp
  Sources/OnChangeCallback.cpp
  Sources/OnStoredInstanceCallback.cpp
  Sources/Plugin.cpp
  Sources/PythonBytes.cpp
  Sources/PythonFunction.cpp
  Sources/PythonLock.cpp
  Sources/PythonModule.cpp
  Sources/PythonObject.cpp
  Sources/PythonString.cpp
  Sources/PythonThreadsAllower.cpp
  Sources/ReceivedInstanceCallback.cpp
  Sources/RestCallbacks.cpp
  Sources/StorageArea.cpp
  Sources/StorageCommitmentScpCallback.cpp

  # Third-party sources
  ${CMAKE_SOURCE_DIR}/Resources/Orthanc/Plugins/OrthancPluginCppWrapper.cpp
  ${BOOST_SOURCES}
  ${JSONCPP_SOURCES}
  )

if (CMAKE_CXX_COMPILER_ID STREQUAL "Clang" OR
    CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
  # Don't report warnings about deprecated functions in the Orthanc SDK
  set_source_files_properties(
    ${AUTOGENERATED_DIR}/sdk/sdk.cpp
    COMPILE_FLAGS -Wno-deprecated-declarations)
endif()

if (COMMAND DefineSourceBasenameForTarget)
  DefineSourceBasenameForTarget(OrthancPython)
endif()

add_dependencies(OrthancPython AutogeneratedTarget)

target_link_libraries(OrthancPython ${PYTHON_LIBRARIES})

add_definitions(
  -DPLUGIN_NAME="python"
  -DPLUGIN_VERSION="${PLUGIN_VERSION}"
  )

set_target_properties(OrthancPython PROPERTIES 
  VERSION ${PLUGIN_VERSION} 
  SOVERSION ${PLUGIN_VERSION}
  )

install(
  TARGETS OrthancPython
  RUNTIME DESTINATION lib    # Destination for Windows
  LIBRARY DESTINATION share/orthanc/plugins    # Destination for Linux
  )

install(
  FILES ${CMAKE_CURRENT_BINARY_DIR}/orthanc.pyi
  DESTINATION .
  )
