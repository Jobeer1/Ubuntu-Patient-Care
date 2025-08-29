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


cmake_minimum_required(VERSION 2.8...4.0)
project(OrthancWSIApplications)

include(${CMAKE_SOURCE_DIR}/../Resources/CMake/Version.cmake)


#####################################################################
## Parameters of the build
#####################################################################

# Generic parameters
SET(STATIC_BUILD OFF CACHE BOOL "Static build of the third-party libraries (necessary for Windows)")
SET(ALLOW_DOWNLOADS OFF CACHE BOOL "Allow CMake to download packages")
SET(ENABLE_PROFILING OFF CACHE BOOL "Whether to enable the generation of profiling information with gprof")

# Advanced parameters to fine-tune linking against system libraries
SET(USE_SYSTEM_LIBTIFF ON CACHE BOOL "Use the system version of libtiff")
SET(USE_SYSTEM_OPENJPEG ON CACHE BOOL "Use the system version of OpenJpeg")



#####################################################################
## Configure mandatory third-party components
#####################################################################

SET(ORTHANC_WSI_DIR ${CMAKE_CURRENT_LIST_DIR}/..)
SET(USE_OPENJPEG_JP2 ON)

include(${CMAKE_SOURCE_DIR}/../Resources/Orthanc/CMake/DownloadOrthancFramework.cmake)  

if (ORTHANC_FRAMEWORK_SOURCE STREQUAL "system")
  if (ORTHANC_FRAMEWORK_USE_SHARED)    
    # https://cmake.org/cmake/help/latest/policy/CMP0167.html
    if (CMAKE_VERSION VERSION_GREATER "3.30")
      find_package(Boost CONFIG)
    else()
      include(FindBoost)
    endif()

    find_package(Boost COMPONENTS filesystem program_options regex system thread date_time)
    
    if (NOT Boost_FOUND)
      message(FATAL_ERROR "Unable to locate Boost on this system")
    endif()

    include(FindDCMTK)
    link_libraries(${Boost_LIBRARIES} ${DCMTK_LIBRARIES} jsoncpp crypto)
  endif()
  
  link_libraries(${ORTHANC_FRAMEWORK_LIBRARIES})
  
else()
  include_directories(${ORTHANC_FRAMEWORK_ROOT})

  UNSET(STANDALONE_BUILD CACHE)
  SET(STANDALONE_BUILD ON)       # Embed DCMTK's dictionaries for static builds

  include(${ORTHANC_FRAMEWORK_ROOT}/../Resources/CMake/OrthancFrameworkParameters.cmake)

  SET(ENABLE_CRYPTO_OPTIONS ON)
  SET(ENABLE_DCMTK ON)
  SET(ENABLE_DCMTK_JPEG OFF)          # Disable DCMTK's support for JPEG, that clashes with libtiff
  SET(ENABLE_DCMTK_JPEG_LOSSLESS ON)  # Enable DCMTK's support for JPEG-LS (was disabled in WSI <= 3.1)
  SET(ENABLE_DCMTK_TRANSCODING ON)    # Enable DCMTK's support for transcoding (was disabled in WSI <= 3.1)
  SET(ENABLE_DCMTK_NETWORKING OFF)    # Disable DCMTK's support for DICOM networking
  SET(ENABLE_JPEG ON)
  SET(ENABLE_LOCALE ON)               # Enable support for locales (notably in Boost)
  SET(ENABLE_OPENSSL_ENGINES ON)
  SET(ENABLE_PNG ON)
  SET(ENABLE_SSL ON)
  SET(ENABLE_WEB_CLIENT ON)
  SET(ENABLE_ZLIB ON)

  include(${ORTHANC_FRAMEWORK_ROOT}/../Resources/CMake/VisualStudioPrecompiledHeaders.cmake)
  include(${ORTHANC_FRAMEWORK_ROOT}/../Resources/CMake/OrthancFrameworkConfiguration.cmake)

  include(${ORTHANC_WSI_DIR}/Resources/CMake/BoostExtendedConfiguration.cmake)

  if (STATIC_BUILD OR NOT USE_SYSTEM_DCMTK)
    # This is a backport of changeset: https://orthanc.uclouvain.be/hg/orthanc/rev/97d69fb5958e
    # TODO - Remove after next upgrade to Orthanc framework > 1.12.7
    include_directories(
      ${DCMTK_SOURCES_DIR}/dcmimgle/include
      )
  endif()
endif()




# Include components specific to WSI
include(${ORTHANC_WSI_DIR}/Resources/CMake/OpenJpegConfiguration.cmake)
include(${ORTHANC_WSI_DIR}/Resources/CMake/LibTiffConfiguration.cmake)



#####################################################################
## Create the list of the source files that depend upon the
## precompiled headers
#####################################################################

set(ORTHANC_WSI_SOURCES
  ${ORTHANC_WSI_DIR}/Framework/Algorithms/PyramidReader.cpp
  ${ORTHANC_WSI_DIR}/Framework/Algorithms/ReconstructPyramidCommand.cpp
  ${ORTHANC_WSI_DIR}/Framework/Algorithms/TranscodeTileCommand.cpp
  ${ORTHANC_WSI_DIR}/Framework/ColorSpaces.cpp
  ${ORTHANC_WSI_DIR}/Framework/DicomToolbox.cpp
  ${ORTHANC_WSI_DIR}/Framework/DicomizerParameters.cpp
  ${ORTHANC_WSI_DIR}/Framework/Enumerations.cpp
  ${ORTHANC_WSI_DIR}/Framework/ImageToolbox.cpp
  ${ORTHANC_WSI_DIR}/Framework/ImagedVolumeParameters.cpp
  ${ORTHANC_WSI_DIR}/Framework/Inputs/CytomineImage.cpp
  ${ORTHANC_WSI_DIR}/Framework/Inputs/DecodedPyramidCache.cpp
  ${ORTHANC_WSI_DIR}/Framework/Inputs/DecodedTiledPyramid.cpp
  ${ORTHANC_WSI_DIR}/Framework/Inputs/DicomPyramid.cpp
  ${ORTHANC_WSI_DIR}/Framework/Inputs/DicomPyramidInstance.cpp
  ${ORTHANC_WSI_DIR}/Framework/Inputs/DicomPyramidLevel.cpp
  ${ORTHANC_WSI_DIR}/Framework/Inputs/HierarchicalTiff.cpp
  ${ORTHANC_WSI_DIR}/Framework/Inputs/OnTheFlyPyramid.cpp
  ${ORTHANC_WSI_DIR}/Framework/Inputs/OpenSlideLibrary.cpp
  ${ORTHANC_WSI_DIR}/Framework/Inputs/OpenSlidePyramid.cpp
  ${ORTHANC_WSI_DIR}/Framework/Inputs/PlainTiff.cpp
  ${ORTHANC_WSI_DIR}/Framework/Inputs/PyramidWithRawTiles.cpp
  ${ORTHANC_WSI_DIR}/Framework/Inputs/SingleLevelDecodedPyramid.cpp
  ${ORTHANC_WSI_DIR}/Framework/Inputs/TiledPyramidStatistics.cpp
  ${ORTHANC_WSI_DIR}/Framework/Jpeg2000Reader.cpp
  ${ORTHANC_WSI_DIR}/Framework/Jpeg2000Writer.cpp
  ${ORTHANC_WSI_DIR}/Framework/MultiThreading/BagOfTasksProcessor.cpp
  ${ORTHANC_WSI_DIR}/Framework/Outputs/DicomPyramidWriter.cpp
  ${ORTHANC_WSI_DIR}/Framework/Outputs/HierarchicalTiffWriter.cpp
  ${ORTHANC_WSI_DIR}/Framework/Outputs/InMemoryTiledImage.cpp
  ${ORTHANC_WSI_DIR}/Framework/Outputs/MultiframeDicomWriter.cpp
  ${ORTHANC_WSI_DIR}/Framework/Outputs/PyramidWriterBase.cpp
  ${ORTHANC_WSI_DIR}/Framework/Outputs/TruncatedPyramidWriter.cpp
  ${ORTHANC_WSI_DIR}/Framework/Targets/FolderTarget.cpp
  ${ORTHANC_WSI_DIR}/Framework/Targets/OrthancTarget.cpp
  ${ORTHANC_WSI_DIR}/Framework/TiffReader.cpp
  )

EmbedResources(
  ${DCMTK_DICTIONARIES}
  BRIGHTFIELD_OPTICAL_PATH  ${ORTHANC_WSI_DIR}/Resources/BrightfieldOpticalPath.json
  SAMPLE_DATASET            ${ORTHANC_WSI_DIR}/Resources/SampleDataset.json
  SRGB_ICC_PROFILE          ${ORTHANC_WSI_DIR}/Resources/sRGB.icc
  )

add_definitions(
  -DORTHANC_ENABLE_LOGGING_PLUGIN=0
  )


#####################################################################
## Setup precompiled headers for Microsoft Visual Studio
#####################################################################

if (MSVC)
  add_definitions(-DORTHANC_USE_PRECOMPILED_HEADERS=1)

  set(TMP
    ${ORTHANC_CORE_SOURCES_INTERNAL}
    ${ORTHANC_DICOM_SOURCES_INTERNAL}
    )
  
  ADD_VISUAL_STUDIO_PRECOMPILED_HEADERS(
    "PrecompiledHeaders.h" "${ORTHANC_FRAMEWORK_ROOT}/PrecompiledHeaders.cpp"
    TMP ORTHANC_CORE_PCH)

  ADD_VISUAL_STUDIO_PRECOMPILED_HEADERS(
    "PrecompiledHeadersWSI.h" "${ORTHANC_WSI_DIR}/Framework/PrecompiledHeadersWSI.cpp"
    ORTHANC_WSI_SOURCES ORTHANC_WSI_PCH)

  source_group(ThirdParty\\OrthancCore FILES ${ORTHANC_CORE_SOURCES})
endif()


#####################################################################
## Create the static library containing the framework
#####################################################################

add_library(OrthancWSIFramework STATIC
  ${ORTHANC_WSI_PCH}
  ${ORTHANC_WSI_SOURCES}

  ${ORTHANC_CORE_PCH}
  ${ORTHANC_CORE_SOURCES_INTERNAL}
  ${ORTHANC_CORE_SOURCES_DEPENDENCIES}
  ${ORTHANC_DICOM_SOURCES_INTERNAL}
  ${ORTHANC_DICOM_SOURCES_DEPENDENCIES}
  ${AUTOGENERATED_SOURCES}
  ${BOOST_EXTENDED_SOURCES}

  ${ORTHANC_WSI_DIR}/Resources/Orthanc/Stone/DicomDatasetReader.cpp
  ${ORTHANC_WSI_DIR}/Resources/Orthanc/Stone/FullOrthancDataset.cpp
  ${ORTHANC_WSI_DIR}/Resources/Orthanc/Stone/IOrthancConnection.cpp
  ${ORTHANC_WSI_DIR}/Resources/Orthanc/Stone/OrthancHttpConnection.cpp
  ${ORTHANC_WSI_DIR}/Resources/Orthanc/StoneToolbox.cpp

  # Mandatory components
  ${LIBTIFF_SOURCES}
  ${OPENJPEG_SOURCES}
  )

if (COMMAND DefineSourceBasenameForTarget)
  DefineSourceBasenameForTarget(OrthancWSIFramework)
endif()


#####################################################################
## Build the WSI DICOM-izer
#####################################################################

# Create the Windows resources, if need be
if (${CMAKE_SYSTEM_NAME} STREQUAL "Windows")
  execute_process(
    COMMAND 
    ${PYTHON_EXECUTABLE} ${ORTHANC_FRAMEWORK_ROOT}/../Resources/WindowsResources.py
    ${ORTHANC_WSI_VERSION} OrthancWSIDicomizer OrthancWSIDicomizer.exe "Companion tool to Orthanc for whole-slide imaging"
    ERROR_VARIABLE Failure
    OUTPUT_FILE ${AUTOGENERATED_DIR}/OrthancWSIDicomizer.rc
    )

  if (Failure)
    message(FATAL_ERROR "Error while computing the version information: ${Failure}")
  endif()

  set(DICOMIZER_RESOURCES ${AUTOGENERATED_DIR}/OrthancWSIDicomizer.rc)
endif()


add_executable(OrthancWSIDicomizer
  Dicomizer.cpp
  ApplicationToolbox.cpp
  ${DICOMIZER_RESOURCES}
  )

if (COMMAND DefineSourceBasenameForTarget)
  DefineSourceBasenameForTarget(OrthancWSIDicomizer)
endif()

target_link_libraries(OrthancWSIDicomizer OrthancWSIFramework ${DCMTK_LIBRARIES})

install(
  TARGETS OrthancWSIDicomizer
  RUNTIME DESTINATION bin
  )


#####################################################################
## Build the DICOM-to-TIFF conversion tool
#####################################################################

# Create the Windows resources, if need be
if (${CMAKE_SYSTEM_NAME} STREQUAL "Windows")
  execute_process(
    COMMAND 
    ${PYTHON_EXECUTABLE} ${ORTHANC_FRAMEWORK_ROOT}/../Resources/WindowsResources.py
    ${ORTHANC_WSI_VERSION} OrthancWSIDicomToTiff OrthancWSIDicomToTiff.exe "Companion tool to Orthanc for whole-slide imaging"
    ERROR_VARIABLE Failure
    OUTPUT_FILE ${AUTOGENERATED_DIR}/OrthancWSIDicomToTiff.rc
    )

  if (Failure)
    message(FATAL_ERROR "Error while computing the version information: ${Failure}")
  endif()

  set(DICOM_TO_TIFF_RESOURCES ${AUTOGENERATED_DIR}/OrthancWSIDicomToTiff.rc)
endif()


add_executable(OrthancWSIDicomToTiff
  DicomToTiff.cpp
  ApplicationToolbox.cpp
  ${DICOM_TO_TIFF_RESOURCES}
  )

if (COMMAND DefineSourceBasenameForTarget)
  DefineSourceBasenameForTarget(OrthancWSIDicomToTiff)
endif()

target_link_libraries(OrthancWSIDicomToTiff OrthancWSIFramework ${DCMTK_LIBRARIES})

install(
  TARGETS OrthancWSIDicomToTiff
  RUNTIME DESTINATION bin
  )


#####################################################################
## Generate the documentation if Doxygen is present
#####################################################################

find_package(Doxygen)
if (DOXYGEN_FOUND)
  configure_file(
    ${ORTHANC_WSI_DIR}/Resources/OrthancWSI.doxygen
    ${CMAKE_CURRENT_BINARY_DIR}/OrthancWSI.doxygen
    @ONLY)

  add_custom_target(doc
    ${DOXYGEN_EXECUTABLE} ${CMAKE_CURRENT_BINARY_DIR}/OrthancWSI.doxygen
    COMMENT "Generating documentation with Doxygen" VERBATIM
    )
else()
  message("Doxygen not found. The documentation will not be built.")
endif()
