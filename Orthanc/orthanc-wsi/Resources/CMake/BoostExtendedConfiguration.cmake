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


SET(ORTHANC_BOOST_COMPONENTS program_options)

include(${ORTHANC_FRAMEWORK_ROOT}/../Resources/CMake/BoostConfiguration.cmake)

if (BOOST_STATIC)
  set(BOOST_EXTENDED_SOURCES
    ${BOOST_SOURCES_DIR}/libs/program_options/src/cmdline.cpp
    ${BOOST_SOURCES_DIR}/libs/program_options/src/config_file.cpp
    ${BOOST_SOURCES_DIR}/libs/program_options/src/convert.cpp
    ${BOOST_SOURCES_DIR}/libs/program_options/src/options_description.cpp
    ${BOOST_SOURCES_DIR}/libs/program_options/src/parsers.cpp
    ${BOOST_SOURCES_DIR}/libs/program_options/src/positional_options.cpp
    ${BOOST_SOURCES_DIR}/libs/program_options/src/split.cpp
    ${BOOST_SOURCES_DIR}/libs/program_options/src/utf8_codecvt_facet.cpp
    ${BOOST_SOURCES_DIR}/libs/program_options/src/value_semantic.cpp
    ${BOOST_SOURCES_DIR}/libs/program_options/src/variables_map.cpp
    #${BOOST_SOURCES_DIR}/libs/program_options/src/winmain.cpp
    )
  add_definitions(-DBOOST_PROGRAM_OPTIONS_NO_LIB)
endif()

