#!/bin/bash

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


# This maintenance script downloads the AWS packages.
#
# NB: Older version numbers can be obtained from
# https://github.com/aws/aws-sdk-cpp/blob/main/prefetch_crt_dependency.sh


set -e

AWS_CHECKSUMS_VERSION=0.1.18       # https://github.com/awslabs/aws-checksums/tags
AWS_CRT_CPP_VERSION=0.24.1         # https://github.com/awslabs/aws-crt-cpp/tags
AWS_C_AUTH_VERSION=0.7.22          # https://github.com/awslabs/aws-c-auth/tags
AWS_C_CAL_VERSION=0.7.0            # https://github.com/awslabs/aws-c-cal/tags
AWS_C_COMMON_VERSION=0.9.23        # https://github.com/awslabs/aws-c-common/tags
AWS_C_COMPRESSION_VERSION=0.2.18   # https://github.com/awslabs/aws-c-compression/tags
AWS_C_EVENT_STREAM_VERSION=0.4.2   # https://github.com/awslabs/aws-c-event-stream/tags
AWS_C_HTTP_VERSION=0.8.2           # https://github.com/awslabs/aws-c-http/tags
AWS_C_IO_VERSION=0.14.9            # https://github.com/awslabs/aws-c-io/tags
AWS_C_MQTT_VERSION=0.10.4          # https://github.com/awslabs/aws-c-mqtt/tags
AWS_C_S3_VERSION=0.5.10            # https://github.com/awslabs/aws-c-s3/tags
AWS_C_SDKUTILS_VERSION=0.1.16      # https://github.com/awslabs/aws-c-sdkutils/tags
AWS_SDK_CPP_VERSION=1.11.178       # https://github.com/awslabs/aws-sdk-cpp/tags

TARGET=/tmp/aws

if [ -d "${TARGET}" ]; then
    echo "Directory exists, giving up: ${TARGET}"
    exit -1
fi

mkdir -p ${TARGET}

wget https://github.com/awslabs/aws-checksums/archive/refs/tags/v${AWS_CHECKSUMS_VERSION}.tar.gz \
     -O ${TARGET}/aws-checksums-${AWS_CHECKSUMS_VERSION}.tar.gz
wget https://github.com/awslabs/aws-crt-cpp/archive/refs/tags/v${AWS_CRT_CPP_VERSION}.tar.gz \
     -O ${TARGET}/aws-crt-cpp-${AWS_CRT_CPP_VERSION}.tar.gz
wget https://github.com/awslabs/aws-c-auth/archive/refs/tags/v${AWS_C_AUTH_VERSION}.tar.gz \
     -O ${TARGET}/aws-c-auth-${AWS_C_AUTH_VERSION}.tar.gz
wget https://github.com/awslabs/aws-c-cal/archive/refs/tags/v${AWS_C_CAL_VERSION}.tar.gz \
     -O ${TARGET}/aws-c-cal-${AWS_C_CAL_VERSION}.tar.gz
wget https://github.com/awslabs/aws-c-common/archive/refs/tags/v${AWS_C_COMMON_VERSION}.tar.gz \
     -O ${TARGET}/aws-c-common-${AWS_C_COMMON_VERSION}.tar.gz
wget https://github.com/awslabs/aws-c-compression/archive/refs/tags/v${AWS_C_COMPRESSION_VERSION}.tar.gz \
     -O ${TARGET}/aws-c-compression-${AWS_C_COMPRESSION_VERSION}.tar.gz
wget https://github.com/awslabs/aws-c-event-stream/archive/refs/tags/v${AWS_C_EVENT_STREAM_VERSION}.tar.gz \
     -O ${TARGET}/aws-c-event-stream-${AWS_C_EVENT_STREAM_VERSION}.tar.gz
wget https://github.com/awslabs/aws-c-http/archive/refs/tags/v${AWS_C_HTTP_VERSION}.tar.gz \
     -O ${TARGET}/aws-c-http-${AWS_C_HTTP_VERSION}.tar.gz
wget https://github.com/awslabs/aws-c-io/archive/refs/tags/v${AWS_C_IO_VERSION}.tar.gz \
     -O ${TARGET}/aws-c-io-${AWS_C_IO_VERSION}.tar.gz
wget https://github.com/awslabs/aws-c-mqtt/archive/refs/tags/v${AWS_C_MQTT_VERSION}.tar.gz \
     -O ${TARGET}/aws-c-mqtt-${AWS_C_MQTT_VERSION}.tar.gz
wget https://github.com/awslabs/aws-c-s3/archive/refs/tags/v${AWS_C_S3_VERSION}.tar.gz \
     -O ${TARGET}/aws-c-s3-${AWS_C_S3_VERSION}.tar.gz
wget https://github.com/awslabs/aws-c-sdkutils/archive/refs/tags/v${AWS_C_SDKUTILS_VERSION}.tar.gz \
     -O ${TARGET}/aws-c-sdkutils-${AWS_C_SDKUTILS_VERSION}.tar.gz
wget https://github.com/awslabs/aws-sdk-cpp/archive/refs/tags/${AWS_SDK_CPP_VERSION}.tar.gz \
     -O ${TARGET}/aws-sdk-cpp-${AWS_SDK_CPP_VERSION}.tar.gz
