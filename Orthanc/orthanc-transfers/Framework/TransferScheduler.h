/**
 * Transfers accelerator plugin for Orthanc
 * Copyright (C) 2018-2023 Osimis S.A., Belgium
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

#include "OrthancInstancesCache.h"


namespace OrthancPlugins
{
  class TransferScheduler : public boost::noncopyable
  {
  private:
    void AddResource(OrthancInstancesCache& cache, 
                     Orthanc::ResourceType level,
                     const std::string& id);

    void ComputeBucketsInternal(std::vector<TransferBucket>& target,
                                size_t groupThreshold,
                                size_t separateThreshold,
                                const std::string& baseUrl,  /* only needed in pull mode */
                                BucketCompression compression /* only needed in pull mode */) const;

    typedef std::map<std::string, DicomInstanceInfo>   Instances;

    Instances    instances_;


  public:
    void AddPatient(OrthancInstancesCache& cache, 
                    const std::string& patient)
    {
      AddResource(cache, Orthanc::ResourceType_Patient, patient);
    }

    void AddStudy(OrthancInstancesCache& cache, 
                  const std::string& study)
    {
      AddResource(cache, Orthanc::ResourceType_Study, study);
    }

    void AddSeries(OrthancInstancesCache& cache, 
                   const std::string& series)
    {
      AddResource(cache, Orthanc::ResourceType_Series, series);
    }

    void AddInstance(OrthancInstancesCache& cache, 
                     const std::string& instanceId);

    void AddInstance(const DicomInstanceInfo& info);

    void ParseListOfResources(OrthancInstancesCache& cache, 
                              const Json::Value& resources);

    void ListInstances(std::vector<DicomInstanceInfo>& target) const;

    size_t GetInstancesCount() const
    {
      return instances_.size();
    }

    size_t GetTotalSize() const;

    void ComputePullBuckets(std::vector<TransferBucket>& target,
                            size_t groupThreshold,
                            size_t separateThreshold,
                            const std::string& baseUrl,
                            BucketCompression compression) const;

    void FormatPushTransaction(Json::Value& target,
                               std::vector<TransferBucket>& buckets,
                               size_t groupThreshold,
                               size_t separateThreshold,
                               BucketCompression compression) const;
  };
}
