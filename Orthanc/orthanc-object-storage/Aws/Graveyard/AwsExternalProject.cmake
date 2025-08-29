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


##
## Building the C++ SDK for Amazon AWS
## WARNING: This is *not* compatible with Ninja (yet)
##
if (STATIC_AWS_CLIENT)
  set(Flags -DBUILD_SHARED_LIBS=OFF)  # Create static library
else()
  set(Flags -DBUILD_SHARED_LIBS=ON)
endif()

include(ExternalProject)
externalproject_add(AwsSdkCpp
  GIT_REPOSITORY https://github.com/aws/aws-sdk-cpp
  GIT_TAG 1.8.127

  CMAKE_ARGS
  -DBUILD_ONLY=s3   #-DBUILD_ONLY=s3;transfer
  -DCMAKE_BUILD_TYPE:STRING=${CMAKE_BUILD_TYPE}
  -DENABLE_TESTING=OFF
  ${Flags}

  UPDATE_COMMAND ""    # Don't run "cmake" on AWS each time "make/ninja" is run
  INSTALL_COMMAND ""   # No install
  )

ExternalProject_Get_Property(AwsSdkCpp SOURCE_DIR)
include_directories(
  ${SOURCE_DIR}/aws-cpp-sdk-core/include/
  ${SOURCE_DIR}/aws-cpp-sdk-s3/include/
  )

ExternalProject_Get_Property(AwsSdkCpp BINARY_DIR)
if (STATIC_AWS_CLIENT)
  set(AWSSDK_LINK_LIBRARIES
    ${BINARY_DIR}/aws-cpp-sdk-s3/libaws-cpp-sdk-s3.a
    ${BINARY_DIR}/aws-cpp-sdk-core/libaws-cpp-sdk-core.a
    ${BINARY_DIR}/.deps/install/lib/libaws-c-event-stream.a
    ${BINARY_DIR}/.deps/install/lib/libaws-checksums.a
    ${BINARY_DIR}/.deps/install/lib/libaws-c-common.a
    curl
    crypto
    )
  if (CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    list(APPEND AWSSDK_LINK_LIBRARIES
      gcc   # for "undefined reference to `__cpu_model'" on Ubuntu 16.04
      )
  endif()
else()
  set(AWSSDK_LINK_LIBRARIES
    ${BINARY_DIR}/aws-cpp-sdk-core/libaws-cpp-sdk-core.so
    ${BINARY_DIR}/aws-cpp-sdk-s3/libaws-cpp-sdk-s3.so
    )
endif()
