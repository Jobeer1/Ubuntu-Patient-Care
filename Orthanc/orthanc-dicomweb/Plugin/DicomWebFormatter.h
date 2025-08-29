/**
 * Orthanc - A Lightweight, RESTful DICOM Store
 * Copyright (C) 2012-2016 Sebastien Jodogne, Medical Physics
 * Department, University Hospital of Liege, Belgium
 * Copyright (C) 2017-2023 Osimis S.A., Belgium
 * Copyright (C) 2024-2025 Orthanc Team SRL, Belgium
 * Copyright (C) 2021-2025 Sebastien Jodogne, ICTEAM UCLouvain, Belgium
 *
 * This program is free software: you can redistribute it and/or
 * modify it under the terms of the GNU Affero General Public License
 * as published by the Free Software Foundation, either version 3 of
 * the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Affero General Public License for more details.
 * 
 * You should have received a copy of the GNU Affero General Public License
 * along with this program. If not, see <http://www.gnu.org/licenses/>.
 **/


#pragma once

#include <ChunkedBuffer.h>
#include <DicomFormat/DicomMap.h>

#include "../Resources/Orthanc/Plugins/OrthancPluginCppWrapper.h"

#include <json/value.h>

#include <boost/noncopyable.hpp>


namespace OrthancPlugins
{
  class DicomWebFormatter : public boost::noncopyable
  {
  private:
    OrthancPluginDicomWebBinaryMode  mode_;
    std::string                      bulkRoot_;

    static void Callback(OrthancPluginDicomWebNode *node,
                         OrthancPluginDicomWebSetBinaryNode setter,
                         uint32_t levelDepth,
                         const uint16_t *levelTagGroup,
                         const uint16_t *levelTagElement,
                         const uint32_t *levelIndex,
                         uint16_t tagGroup,
                         uint16_t tagElement,
                         OrthancPluginValueRepresentation vr,
                         void* payload);

    DicomWebFormatter(OrthancPluginDicomWebBinaryMode mode,
                      const std::string& bulkRoot) :
      mode_(mode),
      bulkRoot_(bulkRoot)
    {
    }
    
  public:
    static void Apply(std::string& target,
                      OrthancPluginContext* context,
                      const void* data,
                      size_t size,
                      bool xml,
                      OrthancPluginDicomWebBinaryMode mode,
                      const std::string& bulkRoot);

    static void Apply(std::string& target,
                      OrthancPluginContext* context,
                      const Json::Value& value,
                      bool xml,
                      OrthancPluginDicomWebBinaryMode mode,
                      const std::string& bulkRoot);

    static void Apply(std::string& target,
                      OrthancPluginContext* context,
                      const DicomInstance& instance,
                      bool xml,
                      OrthancPluginDicomWebBinaryMode mode,
                      const std::string& bulkRoot);

    class HttpWriter : public boost::noncopyable
    {
    private:
      OrthancPluginContext*     context_;
      OrthancPluginRestOutput*  output_;
      bool                      isXml_;
      bool                      first_;
      Orthanc::ChunkedBuffer    jsonBuffer_;

      void AddInternal(const void* dicom,
                       size_t size,
                       OrthancPluginDicomWebBinaryMode mode,
                       const std::string& bulkRoot);

    public:
      HttpWriter(OrthancPluginRestOutput* output,
                 bool isXml);

      bool IsXml() const
      {
        return isXml_;
      }

      void AddDicom(const void* dicom,
                    size_t size,
                    const std::string& bulkRoot)
      {
        AddInternal(dicom, size, OrthancPluginDicomWebBinaryMode_BulkDataUri, bulkRoot);
      }

      void AddOrthancMap(const Orthanc::DicomMap& value);

      void AddOrthancJson(const Json::Value& value);

      void AddDicomWebInstanceSerializedJson(const void* data,
                                             size_t size);

      void AddDicomWebSeriesSerializedJson(const void* data,
                                           size_t size);

      void Send();

      void CloseAndGetJsonOutput(std::string& target);

      void AddInstance(const DicomInstance& instance,
                       const std::string& bulkRoot);
    };
  };
}
