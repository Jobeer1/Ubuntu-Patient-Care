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


set(BASE_URL "https://orthanc.uclouvain.be/downloads/third-party-downloads")

DownloadPackage(
  "102a4386a022f26a3b604e3852fffba8"
  "${BASE_URL}/bootstrap-5.3.3.zip"
  "${CMAKE_CURRENT_BINARY_DIR}/bootstrap-5.3.3")

DownloadPackage(
  "8242afdc5bd44105d9dc9e6535315484"
  "${BASE_URL}/dicom-web/vuejs-2.6.10.tar.gz"
  "${CMAKE_CURRENT_BINARY_DIR}/vue-2.6.10")

DownloadPackage(
  "3e2b4e1522661f7fcf8ad49cb933296c"
  "${BASE_URL}/dicom-web/axios-0.19.0.tar.gz"
  "${CMAKE_CURRENT_BINARY_DIR}/axios-0.19.0")

DownloadPackage(
  "a6145901f233f7d54165d8ade779082e"
  "${BASE_URL}/dicom-web/Font-Awesome-4.7.0.tar.gz"
  "${CMAKE_CURRENT_BINARY_DIR}/Font-Awesome-4.7.0")


if (BUILD_BABEL_POLYFILL)
  set(BABEL_POLYFILL_SOURCES_DIR ${CMAKE_CURRENT_BINARY_DIR}/node_modules/babel-polyfill/dist)

  if (NOT IS_DIRECTORY "${BABEL_POLYFILL_SOURCES_DIR}")
    execute_process(
      COMMAND ${NPM_EXECUTABLE} install babel-polyfill
      WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
      RESULT_VARIABLE Failure
      OUTPUT_QUIET
      )
    
    if (Failure)
      message(FATAL_ERROR "Error while running 'npm install' on babel-polyfill")
    endif()
  endif()
else()

  ## curl -L https://unpkg.com/babel-polyfill@6.26.0/dist/polyfill.min.js | gzip > babel-polyfill-6.26.0.min.js.gz

  set(BABEL_POLYFILL_SOURCES_DIR ${CMAKE_CURRENT_BINARY_DIR})
  DownloadCompressedFile(
    "49f7bad4176d715ce145e75c903988ef"
    "${BASE_URL}/dicom-web/babel-polyfill-6.26.0.min.js.gz"
    "${CMAKE_CURRENT_BINARY_DIR}/polyfill.min.js")

endif()


set(JAVASCRIPT_LIBS_DIR  ${CMAKE_CURRENT_BINARY_DIR}/javascript-libs)
file(MAKE_DIRECTORY ${JAVASCRIPT_LIBS_DIR})

file(COPY
  ${BABEL_POLYFILL_SOURCES_DIR}/polyfill.min.js
  ${CMAKE_CURRENT_BINARY_DIR}/axios-0.19.0/dist/axios.min.js
  ${CMAKE_CURRENT_BINARY_DIR}/axios-0.19.0/dist/axios.min.map
  ${CMAKE_CURRENT_BINARY_DIR}/bootstrap-5.3.3/dist/js/bootstrap.min.js
  ${CMAKE_CURRENT_BINARY_DIR}/vue-2.6.10/dist/vue.min.js
  DESTINATION
  ${JAVASCRIPT_LIBS_DIR}/js
  )

file(COPY
  ${CMAKE_CURRENT_BINARY_DIR}/Font-Awesome-4.7.0/css/font-awesome.min.css
  ${CMAKE_CURRENT_BINARY_DIR}/bootstrap-5.3.3/dist/css/bootstrap.min.css
  ${CMAKE_CURRENT_BINARY_DIR}/bootstrap-5.3.3/dist/css/bootstrap.min.css.map
  DESTINATION
  ${JAVASCRIPT_LIBS_DIR}/css
  )

file(COPY
  ${CMAKE_CURRENT_BINARY_DIR}/Font-Awesome-4.7.0/fonts/FontAwesome.otf
  ${CMAKE_CURRENT_BINARY_DIR}/Font-Awesome-4.7.0/fonts/fontawesome-webfont.eot
  ${CMAKE_CURRENT_BINARY_DIR}/Font-Awesome-4.7.0/fonts/fontawesome-webfont.svg
  ${CMAKE_CURRENT_BINARY_DIR}/Font-Awesome-4.7.0/fonts/fontawesome-webfont.ttf
  ${CMAKE_CURRENT_BINARY_DIR}/Font-Awesome-4.7.0/fonts/fontawesome-webfont.woff
  ${CMAKE_CURRENT_BINARY_DIR}/Font-Awesome-4.7.0/fonts/fontawesome-webfont.woff2
  DESTINATION
  ${JAVASCRIPT_LIBS_DIR}/fonts
  )

file(COPY
  ${CMAKE_CURRENT_LIST_DIR}/../Orthanc/OrthancLogo.png
  DESTINATION
  ${JAVASCRIPT_LIBS_DIR}/img
  )
