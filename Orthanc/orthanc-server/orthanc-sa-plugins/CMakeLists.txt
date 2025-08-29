# Orthanc SA Integration Plugins
# CMake configuration for South African healthcare plugins

cmake_minimum_required(VERSION 3.16)
project(OrthancSAPlugins)

# Set C++ standard
set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find Orthanc framework
if (NOT ORTHANC_FRAMEWORK_SOURCE)
  set(ORTHANC_FRAMEWORK_SOURCE "path" CACHE STRING "Path to Orthanc framework source")
endif()

# Include Orthanc framework
include(${ORTHANC_FRAMEWORK_SOURCE}/Resources/CMake/OrthancFrameworkParameters.cmake)
include(${ORTHANC_FRAMEWORK_SOURCE}/Resources/CMake/OrthancFrameworkConfiguration.cmake)

# Plugin configuration
set(PLUGIN_VERSION "1.0.0")
set(PLUGIN_DESCRIPTION "South African Healthcare Integration for Orthanc")

# Common plugin sources
set(COMMON_SOURCES
  ${CMAKE_SOURCE_DIR}/common/SACommon.cpp
  ${CMAKE_SOURCE_DIR}/database/SADatabaseAbstraction.cpp
  ${CMAKE_SOURCE_DIR}/database/SADatabaseFactory.cpp
  ${CMAKE_SOURCE_DIR}/database/SADatabaseExtension.cpp
)

# Auth Bridge Plugin
add_library(OrthancSAAuthBridge SHARED
  ${COMMON_SOURCES}
  auth-bridge/AuthBridgePlugin.cpp
  auth-bridge/SessionManager.cpp
  auth-bridge/TwoFactorAuth.cpp
)

# Find required libraries
find_package(PkgConfig REQUIRED)
pkg_check_modules(JSONCPP jsoncpp)
find_package(OpenSSL REQUIRED)
find_package(CURL REQUIRED)

# Database libraries (optional - only link if available)
find_package(MySQL QUIET)
find_package(PostgreSQL QUIET)
find_library(FIREBIRD_LIBRARY NAMES fbclient)
find_package(ODBC QUIET)  # For SQL Server
find_library(ORACLE_LIBRARY NAMES clntsh)  # For Oracle

target_link_libraries(OrthancSAAuthBridge 
  ${ORTHANC_FRAMEWORK_LIBRARIES}
  ${JSONCPP_LIBRARIES}
  OpenSSL::SSL
  OpenSSL::Crypto
  ${CURL_LIBRARIES}
)

# Link database libraries if available
if(MySQL_FOUND)
  target_link_libraries(OrthancSAAuthBridge ${MySQL_LIBRARIES})
  target_compile_definitions(OrthancSAAuthBridge PRIVATE HAVE_MYSQL)
endif()

if(PostgreSQL_FOUND)
  target_link_libraries(OrthancSAAuthBridge ${PostgreSQL_LIBRARIES})
  target_compile_definitions(OrthancSAAuthBridge PRIVATE HAVE_POSTGRESQL)
endif()

if(FIREBIRD_LIBRARY)
  target_link_libraries(OrthancSAAuthBridge ${FIREBIRD_LIBRARY})
  target_compile_definitions(OrthancSAAuthBridge PRIVATE HAVE_FIREBIRD)
endif()

if(ODBC_FOUND)
  target_link_libraries(OrthancSAAuthBridge ${ODBC_LIBRARIES})
  target_compile_definitions(OrthancSAAuthBridge PRIVATE HAVE_SQLSERVER)
endif()

if(ORACLE_LIBRARY)
  target_link_libraries(OrthancSAAuthBridge ${ORACLE_LIBRARY})
  target_compile_definitions(OrthancSAAuthBridge PRIVATE HAVE_ORACLE)
endif()

# SA Compliance Plugin  
add_library(OrthancSACompliance SHARED
  ${COMMON_SOURCES}
  sa-compliance/SACompliancePlugin.cpp
  sa-compliance/HPCSAIntegration.cpp
  sa-compliance/POPIAIntegration.cpp
  sa-compliance/MedicalAidValidator.cpp
)

target_link_libraries(OrthancSACompliance ${ORTHANC_FRAMEWORK_LIBRARIES})

# Localization Plugin
add_library(OrthancSALocalization SHARED
  ${COMMON_SOURCES}
  localization/LocalizationPlugin.cpp
  localization/TerminologyDB.cpp
  localization/LanguageManager.cpp
)

target_link_libraries(OrthancSALocalization ${ORTHANC_FRAMEWORK_LIBRARIES})

# Set plugin properties
set_target_properties(OrthancSAAuthBridge PROPERTIES
  VERSION ${PLUGIN_VERSION}
  SOVERSION 1
)

set_target_properties(OrthancSACompliance PROPERTIES
  VERSION ${PLUGIN_VERSION}
  SOVERSION 1
)

set_target_properties(OrthancSALocalization PROPERTIES
  VERSION ${PLUGIN_VERSION}
  SOVERSION 1
)

# Installation
install(TARGETS OrthancSAAuthBridge OrthancSACompliance OrthancSALocalization
  LIBRARY DESTINATION lib/orthanc/plugins
)