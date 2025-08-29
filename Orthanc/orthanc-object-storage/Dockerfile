# This is a dev Dockerfile in case you need to rebuild an osimis/orthanc image with a test
# version of the s3 plugin
# docker build -t osimis/orthanc:s3test . 

FROM osimis/orthanc-builder-base:bullseye-20220328-slim-stable as orthanc-builder-base

FROM orthanc-builder-base as build-s3-object-storage

WORKDIR /

WORKDIR /sources

# (framework version used to build the cloud storage plugins)
RUN hg clone https://orthanc.uclouvain.be/hg/orthanc/ -r "Orthanc-1.10.1" 

RUN mkdir orthanc-object-storage

COPY . /sources/orthanc-object-storage


RUN mkdir -p /build/cloud-storage/aws
WORKDIR /build/cloud-storage/aws
RUN cmake -DCMAKE_BUILD_TYPE:STRING=Release -DUSE_VCPKG_PACKAGES=OFF -DORTHANC_FRAMEWORK_SOURCE=path -DORTHANC_FRAMEWORK_ROOT=/sources/orthanc/OrthancFramework/Sources /sources/orthanc-object-storage/Aws/
RUN make -j 8


FROM osimis/orthanc:22.7.0

COPY --from=build-s3-object-storage /build/cloud-storage/aws/libOrthancAwsS3Storage.so /usr/share/orthanc/plugins-available/

RUN chmod +x /usr/share/orthanc/plugins-available/*