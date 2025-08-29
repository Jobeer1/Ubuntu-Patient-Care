# Advanced authorization plugin for Orthanc
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


cmake_minimum_required(VERSION 2.8)

project(OrthancAuthorization)

set(ORTHANC_PLUGIN_VERSION "mainline")

if (ORTHANC_PLUGIN_VERSION STREQUAL "mainline")
  set(ORTHANC_FRAMEWORK_VERSION "mainline")
  set(ORTHANC_FRAMEWORK_DEFAULT_SOURCE "hg")
else()
  set(ORTHANC_FRAMEWORK_VERSION "1.12.2")
  set(ORTHANC_FRAMEWORK_DEFAULT_SOURCE "web")
endif()

# Parameters of the build
set(STATIC_BUILD OFF CACHE BOOL "Static build of the third-party libraries (necessary for Windows)")
set(ALLOW_DOWNLOADS OFF CACHE BOOL "Allow CMake to download packages")
set(ORTHANC_FRAMEWORK_SOURCE "${ORTHANC_FRAMEWORK_DEFAULT_SOURCE}" CACHE STRING "Source of the Orthanc source code (can be \"hg\", \"archive\", \"web\" or \"path\")")
set(ORTHANC_FRAMEWORK_ARCHIVE "" CACHE STRING "Path to the Orthanc archive, if ORTHANC_FRAMEWORK_SOURCE is \"archive\"")
set(ORTHANC_FRAMEWORK_ROOT "" CACHE STRING "Path to the Orthanc source directory, if ORTHANC_FRAMEWORK_SOURCE is \"path\"")

# Advanced parameters to fine-tune linking against system libraries
set(USE_SYSTEM_ORTHANC_SDK ON CACHE BOOL "Use the system version of the Orthanc plugin SDK")
set(ORTHANC_SDK_VERSION "1.12.9" CACHE STRING "Version of the Orthanc plugin SDK to use, if not using the system version (can be \"1.11.3\", \"1.12.4\", \"1.12.9\",or \"framework\")")

# Download and setup the Orthanc framework
include(${CMAKE_SOURCE_DIR}/Resources/Orthanc/CMake/DownloadOrthancFramework.cmake)

if (ORTHANC_FRAMEWORK_SOURCE STREQUAL "system")
  if (ORTHANC_FRAMEWORK_USE_SHARED)
    include(FindBoost)
    find_package(Boost COMPONENTS regex system)
    
    if (NOT Boost_FOUND)
      message(FATAL_ERROR "Unable to locate Boost on this system")
    endif()
    
    link_libraries(${Boost_LIBRARIES} jsoncpp)
  endif()
  
  link_libraries(${ORTHANC_FRAMEWORK_LIBRARIES})

  set(USE_SYSTEM_GOOGLE_TEST ON CACHE BOOL "Use the system version of Google Test")
  set(USE_GOOGLE_TEST_DEBIAN_PACKAGE OFF CACHE BOOL "Use the sources of Google Test shipped with libgtest-dev (Debian only)")
  mark_as_advanced(USE_GOOGLE_TEST_DEBIAN_PACKAGE)
  include(${CMAKE_SOURCE_DIR}/Resources/Orthanc/CMake/GoogleTestConfiguration.cmake)

else()
  include(${ORTHANC_FRAMEWORK_ROOT}/../Resources/CMake/OrthancFrameworkParameters.cmake)

  set(ENABLE_LOCALE OFF)           # Disable support for locales (notably in Boost)
  set(ENABLE_GOOGLE_TEST ON)
  set(ENABLE_MODULE_IMAGES OFF)
  set(ENABLE_MODULE_JOBS OFF)
  set(ENABLE_MODULE_DICOM OFF)
  set(ENABLE_WEB_CLIENT ON)
  
  include(${ORTHANC_FRAMEWORK_ROOT}/../Resources/CMake/OrthancFrameworkConfiguration.cmake)
  include_directories(${ORTHANC_FRAMEWORK_ROOT})
endif()


include(${CMAKE_SOURCE_DIR}/Resources/Orthanc/Plugins/OrthancPluginsExports.cmake)


# Check that the Orthanc SDK headers are available
if (STATIC_BUILD OR NOT USE_SYSTEM_ORTHANC_SDK)
  if (ORTHANC_SDK_VERSION STREQUAL "1.11.3")
    include_directories(${CMAKE_SOURCE_DIR}/Resources/Orthanc/Sdk-1.11.3)
  elseif (ORTHANC_SDK_VERSION STREQUAL "1.12.4")
    include_directories(${CMAKE_SOURCE_DIR}/Resources/Orthanc/Sdk-1.12.4)
  elseif (ORTHANC_SDK_VERSION STREQUAL "1.12.9")
    include_directories(${CMAKE_SOURCE_DIR}/Resources/Orthanc/Sdk-1.12.9)
  elseif (ORTHANC_SDK_VERSION STREQUAL "framework")
    include_directories(${ORTHANC_FRAMEWORK_ROOT}/../../OrthancServer/Plugins/Include)
  else()
    message(FATAL_ERROR "Unsupported version of the Orthanc plugin SDK: ${ORTHANC_SDK_VERSION}")
  endif()

else ()
  CHECK_INCLUDE_FILE_CXX(orthanc/OrthancCPlugin.h HAVE_ORTHANC_H)
  if (NOT HAVE_ORTHANC_H)
    message(FATAL_ERROR "Please install the headers of the Orthanc plugins SDK")
  endif()
endif()


if (${CMAKE_SYSTEM_NAME} STREQUAL "Linux" OR
    ${CMAKE_SYSTEM_NAME} STREQUAL "kFreeBSD" OR
    ${CMAKE_SYSTEM_NAME} STREQUAL "FreeBSD")
  link_libraries(rt)
elseif (${CMAKE_SYSTEM_NAME} STREQUAL "Windows")
  execute_process(
    COMMAND 
    ${PYTHON_EXECUTABLE} ${ORTHANC_FRAMEWORK_ROOT}/../Resources/WindowsResources.py
    ${ORTHANC_PLUGIN_VERSION} "OrthancAuthorization" OrthancAuthorization.dll "Advanced authorization plugin for Orthanc"
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

add_definitions(
  -DHAS_ORTHANC_EXCEPTION=1
  -DORTHANC_ENABLE_LOGGING_PLUGIN=1
  )

set(ADDITIONAL_RESOURCES
  DEFAULT_CONFIGURATION  ${CMAKE_SOURCE_DIR}/Plugin/DefaultConfiguration.json
  )

EmbedResources(
  --no-upcase-check
  ${ADDITIONAL_RESOURCES}
  )

# As the embedded resources are shared by both the "UnitTests" and the
# "OrthancAuthorization" targets, avoid race conditions in the code
# generation by adding a target between them
add_custom_target(
  AutogeneratedTarget
  DEPENDS 
  ${AUTOGENERATED_SOURCES}
  )

set(PLUGIN_SOURCES
  ${CMAKE_SOURCE_DIR}/Plugin/AccessedResource.cpp
  ${CMAKE_SOURCE_DIR}/Plugin/AssociativeArray.cpp
  ${CMAKE_SOURCE_DIR}/Plugin/AuthorizationParserBase.cpp
  ${CMAKE_SOURCE_DIR}/Plugin/AuthorizationWebService.cpp
  ${CMAKE_SOURCE_DIR}/Plugin/CachedAuthorizationService.cpp
  ${CMAKE_SOURCE_DIR}/Plugin/DefaultAuthorizationParser.cpp
  ${CMAKE_SOURCE_DIR}/Plugin/Enumerations.cpp
  ${CMAKE_SOURCE_DIR}/Plugin/MemoryCache.cpp
  ${CMAKE_SOURCE_DIR}/Plugin/OrthancResource.cpp
  ${CMAKE_SOURCE_DIR}/Plugin/PermissionParser.cpp
  ${CMAKE_SOURCE_DIR}/Plugin/Plugin.cpp
  ${CMAKE_SOURCE_DIR}/Plugin/ResourceHierarchyCache.cpp
  ${CMAKE_SOURCE_DIR}/Plugin/Token.cpp
  ${CMAKE_SOURCE_DIR}/Resources/Orthanc/Plugins/OrthancPluginCppWrapper.cpp
  ${ORTHANC_CORE_SOURCES}
  ${AUTOGENERATED_SOURCES}
)


add_library(OrthancAuthorization SHARED
  ${PLUGIN_SOURCES}
)

if (COMMAND DefineSourceBasenameForTarget)
  DefineSourceBasenameForTarget(OrthancAuthorization)
endif()

add_dependencies(OrthancAuthorization AutogeneratedTarget)

message("Setting the version of the plugin to ${ORTHANC_PLUGIN_VERSION}")
add_definitions(-DORTHANC_PLUGIN_VERSION="${ORTHANC_PLUGIN_VERSION}")

set_target_properties(OrthancAuthorization PROPERTIES 
  VERSION ${ORTHANC_PLUGIN_VERSION} 
  SOVERSION ${ORTHANC_PLUGIN_VERSION})

install(
  TARGETS OrthancAuthorization
  RUNTIME DESTINATION lib    # Destination for Windows
  LIBRARY DESTINATION share/orthanc/plugins    # Destination for Linux
  )

add_executable(UnitTests
  ${PLUGIN_SOURCES}
  ${ORTHANC_CORE_SOURCES}
  ${GOOGLE_TEST_SOURCES}
  UnitTestsSources/UnitTestsMain.cpp
  )

# add_dependencies(UnitTests AutogeneratedTarget)

target_include_directories(UnitTests PUBLIC ${ORTHANC_FRAMEWORK_ROOT})
target_compile_definitions(UnitTests PUBLIC
  -DHAS_ORTHANC_EXCEPTION=1
  -DORTHANC_ENABLE_LOGGING_PLUGIN=1
  -DBUILD_UNIT_TESTS=1
  )

target_link_libraries(UnitTests
  ${GOOGLE_TEST_LIBRARIES}
  # ${AUTOGENERATED_SOURCES}
  )
