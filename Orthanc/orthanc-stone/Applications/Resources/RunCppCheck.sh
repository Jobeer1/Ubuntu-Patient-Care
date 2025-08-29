#!/bin/bash

# Stone of Orthanc
# Copyright (C) 2012-2016 Sebastien Jodogne, Medical Physics
# Department, University Hospital of Liege, Belgium
# Copyright (C) 2017-2023 Osimis S.A., Belgium
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


set -ex

CPPCHECK=cppcheck

if [ $# -ge 1 ]; then
    CPPCHECK=$1
fi

cat <<EOF > /tmp/cppcheck-suppressions.txt
assertWithSideEffect:../../OrthancStone/Sources/Loaders/OrthancMultiframeVolumeLoader.cpp:341
assertWithSideEffect:../../OrthancStone/Sources/Loaders/OrthancMultiframeVolumeLoader.cpp:342
constParameter:../../RenderingPlugin/Sources/Plugin.cpp:778
stlFindInsert:../../Applications/Samples/WebAssembly/SingleFrameViewer/SingleFrameViewerApplication.h
stlFindInsert:../../Applications/StoneWebViewer/WebAssembly/StoneWebViewer.cpp:1389
stlFindInsert:../../Applications/StoneWebViewer/WebAssembly/StoneWebViewer.cpp:672
unpreciseMathCall:../../OrthancStone/Sources/Scene2D/Internals/CairoFloatTextureRenderer.cpp
unpreciseMathCall:../../OrthancStone/Sources/Scene2D/LookupTableTextureSceneLayer.cpp
unreadVariable:../../OrthancStone/Sources/Platforms/Sdl/SdlViewport.cpp:159
unreadVariable:../../OrthancStone/Sources/Platforms/Sdl/SdlViewport.cpp:213
unusedFunction
EOF

${CPPCHECK} --enable=all --quiet --std=c++11 \
            --suppressions-list=/tmp/cppcheck-suppressions.txt \
            -DHAS_ORTHANC_EXCEPTION=1 \
            -DORTHANC_BUILDING_FRAMEWORK_LIBRARY=1 \
            -DORTHANC_ENABLE_BASE64=1 \
            -DORTHANC_ENABLE_CIVETWEB=0 \
            -DORTHANC_ENABLE_CURL=1 \
            -DORTHANC_ENABLE_DCMTK=1 \
            -DORTHANC_ENABLE_DCMTK_JPEG=1 \
            -DORTHANC_ENABLE_DCMTK_JPEG_LOSSLESS=1 \
            -DORTHANC_ENABLE_GLEW=1 \
            -DORTHANC_ENABLE_JPEG=1 \
            -DORTHANC_ENABLE_LOCALE=1 \
            -DORTHANC_ENABLE_LOGGING=1 \
            -DORTHANC_ENABLE_LOGGING_STDIO=1 \
            -DORTHANC_ENABLE_MD5=1 \
            -DORTHANC_ENABLE_MONGOOSE=0 \
            -DORTHANC_ENABLE_OPENGL=1 \
            -DORTHANC_ENABLE_PKCS11=0 \
            -DORTHANC_ENABLE_PNG=1 \
            -DORTHANC_ENABLE_PUGIXML=1 \
            -DORTHANC_ENABLE_SDL=1 \
            -DORTHANC_ENABLE_SSL=1 \
            -DORTHANC_ENABLE_THREADS=1 \
            -DORTHANC_ENABLE_WASM=1 \
            -DORTHANC_ENABLE_ZLIB=1 \
            -DORTHANC_SANDBOXED=0 \
            -D__GNUC__ \
            -D__cplusplus=201103 \
            -D__linux__ \
            -DEM_ASM \
            -UNDEBUG \
            -I${HOME}/Subversion/orthanc/OrthancFramework/Sources \
            -I${HOME}/Subversion/orthanc/OrthancServer/Plugins/Include/ \
            \
            ../../Applications/Samples \
            ../../Applications/StoneWebViewer \
            ../../OrthancStone/Sources \
            ../../RenderingPlugin/Sources \
            \
            -i ../../Applications/Samples/RtViewerPlugin/i \
            -i ../../Applications/Samples/Sdl/i \
            -i ../../Applications/Samples/WebAssembly/i \
            -i ../../Applications/StoneWebViewer/Plugin/i \
            -i ../../Applications/StoneWebViewer/WebAssembly/StoneModule/i \
            -i ../../Applications/StoneWebViewer/WebAssembly/i \
            -i ../../Applications/StoneWebViewer/WebAssembly/debug/ \
            \
            2>&1
