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


set(BASE_URL "https://orthanc.uclouvain.be/downloads/third-party-downloads")

DownloadPackage(
  "f9746611d1d77072f5ce5a1d9e915c42"
  "${BASE_URL}/fontawesome-free-5.14.0-web.zip"
  "${CMAKE_CURRENT_BINARY_DIR}/fontawesome-free-5.14.0-web")

DownloadPackage(
  "b40f2ec8769ebee23a395fa2b907e4b4"
  "${BASE_URL}/bootstrap-3.4.1-dist.zip"
  "${CMAKE_CURRENT_BINARY_DIR}/bootstrap-3.4.1-dist")

DownloadPackage(
  "ca84d906dcaecd4c66553bf49b547f65"
  "${BASE_URL}/dicom-web/vue-2.6.14.tar.gz"
  "${CMAKE_CURRENT_BINARY_DIR}/vue-2.6.14")

DownloadPackage(
  "93082a766ebf2748aba038aeb32d8a06"
  "${BASE_URL}/dicom-web/axios-1.7.5.tar.gz"
  "${CMAKE_CURRENT_BINARY_DIR}/axios-1.7.5")

DownloadFile(
  "2c872dbe60f4ba70fb85356113d8b35e"
  "${BASE_URL}/jquery-3.7.1.min.js")

if (NOT EXISTS ${CMAKE_CURRENT_BINARY_DIR}/pdfjs)
  DownloadPackage(
    "f2e0f7eacd8946bd3111a2d10dceaa72"
    "${BASE_URL}/web-viewer/pdfjs-2.5.207-dist.zip"
    "${CMAKE_CURRENT_BINARY_DIR}/build")

  # Reorganize the PDF.js package
  file(REMOVE ${CMAKE_CURRENT_BINARY_DIR}/LICENSE)
  file(REMOVE_RECURSE ${CMAKE_CURRENT_BINARY_DIR}/web)
  file(RENAME ${CMAKE_CURRENT_BINARY_DIR}/build ${CMAKE_CURRENT_BINARY_DIR}/pdfjs)
endif()


install(
  FILES
  ${CMAKE_CURRENT_BINARY_DIR}/fontawesome-free-5.14.0-web/css/all.css
  ${CMAKE_CURRENT_BINARY_DIR}/bootstrap-3.4.1-dist/css/bootstrap.css
  ${CMAKE_CURRENT_BINARY_DIR}/bootstrap-3.4.1-dist/css/bootstrap.css.map
  DESTINATION ${ORTHANC_STONE_INSTALL_PREFIX}/css
  )

install(
  FILES
  ${CMAKE_CURRENT_BINARY_DIR}/bootstrap-3.4.1-dist/js/bootstrap.min.js
  ${CMAKE_SOURCE_DIR}/ThirdPartyDownloads/jquery-3.7.1.min.js
  ${CMAKE_CURRENT_BINARY_DIR}/vue-2.6.14/dist/vue.min.js
  ${CMAKE_CURRENT_BINARY_DIR}/axios-1.7.5/dist/axios.min.js
  ${CMAKE_CURRENT_BINARY_DIR}/axios-1.7.5/dist/axios.min.js.map
  ${CMAKE_CURRENT_BINARY_DIR}/pdfjs/pdf.js
  ${CMAKE_CURRENT_BINARY_DIR}/pdfjs/pdf.js.map
  ${CMAKE_CURRENT_BINARY_DIR}/pdfjs/pdf.worker.js
  ${CMAKE_CURRENT_BINARY_DIR}/pdfjs/pdf.worker.js.map
  DESTINATION ${ORTHANC_STONE_INSTALL_PREFIX}/js
  )

install(
  FILES
  ${CMAKE_CURRENT_BINARY_DIR}/fontawesome-free-5.14.0-web/webfonts/fa-brands-400.eot
  ${CMAKE_CURRENT_BINARY_DIR}/fontawesome-free-5.14.0-web/webfonts/fa-brands-400.svg
  ${CMAKE_CURRENT_BINARY_DIR}/fontawesome-free-5.14.0-web/webfonts/fa-brands-400.ttf
  ${CMAKE_CURRENT_BINARY_DIR}/fontawesome-free-5.14.0-web/webfonts/fa-brands-400.woff
  ${CMAKE_CURRENT_BINARY_DIR}/fontawesome-free-5.14.0-web/webfonts/fa-brands-400.woff2
  ${CMAKE_CURRENT_BINARY_DIR}/fontawesome-free-5.14.0-web/webfonts/fa-regular-400.eot
  ${CMAKE_CURRENT_BINARY_DIR}/fontawesome-free-5.14.0-web/webfonts/fa-regular-400.svg
  ${CMAKE_CURRENT_BINARY_DIR}/fontawesome-free-5.14.0-web/webfonts/fa-regular-400.ttf
  ${CMAKE_CURRENT_BINARY_DIR}/fontawesome-free-5.14.0-web/webfonts/fa-regular-400.woff
  ${CMAKE_CURRENT_BINARY_DIR}/fontawesome-free-5.14.0-web/webfonts/fa-regular-400.woff2
  ${CMAKE_CURRENT_BINARY_DIR}/fontawesome-free-5.14.0-web/webfonts/fa-solid-900.eot
  ${CMAKE_CURRENT_BINARY_DIR}/fontawesome-free-5.14.0-web/webfonts/fa-solid-900.svg
  ${CMAKE_CURRENT_BINARY_DIR}/fontawesome-free-5.14.0-web/webfonts/fa-solid-900.ttf
  ${CMAKE_CURRENT_BINARY_DIR}/fontawesome-free-5.14.0-web/webfonts/fa-solid-900.woff
  ${CMAKE_CURRENT_BINARY_DIR}/fontawesome-free-5.14.0-web/webfonts/fa-solid-900.woff2
  ${CMAKE_SOURCE_DIR}/../Resources/OpenSans/2017-11-13-OpenSans-Regular.ttf
  ${CMAKE_SOURCE_DIR}/../Resources/OpenSans/2017-11-13-OpenSans-Regular.woff2
  DESTINATION ${ORTHANC_STONE_INSTALL_PREFIX}/webfonts
  )
