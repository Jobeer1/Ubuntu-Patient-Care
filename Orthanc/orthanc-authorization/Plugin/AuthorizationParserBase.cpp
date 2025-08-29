/**
 * Advanced authorization plugin for Orthanc
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

#include "AuthorizationParserBase.h"

#include <OrthancException.h>

namespace OrthancPlugins
{
  void AuthorizationParserBase::AddResourceInternal(AccessedResources& target,
                                                    Orthanc::ResourceType level,
                                                    const std::string& orthancId,
                                                    const std::set<std::string>& labels)
  {
    std::string dicomUid;

    if (resourceHierarchy_->LookupDicomUid(dicomUid, level, orthancId))
    {
      target.push_back(AccessedResource(level, orthancId, dicomUid, labels));
    }
  }
    

  Orthanc::ResourceType AuthorizationParserBase::AddOrthancUnknownResource(AccessedResources& target,
                                                                           const std::string& orthancId)
  {
    std::string dicomId;
    if (resourceHierarchy_->LookupDicomUid(dicomId, Orthanc::ResourceType_Study, orthancId))
    {
      AddOrthancStudy(target, orthancId);
      return Orthanc::ResourceType_Study;
    }

    if (resourceHierarchy_->LookupDicomUid(dicomId, Orthanc::ResourceType_Patient, orthancId))
    {
      AddOrthancPatient(target, orthancId);
      return Orthanc::ResourceType_Patient;
    }

    if (resourceHierarchy_->LookupDicomUid(dicomId, Orthanc::ResourceType_Series, orthancId))
    {
      AddOrthancSeries(target, orthancId);
      return Orthanc::ResourceType_Series;
    }

    if (resourceHierarchy_->LookupDicomUid(dicomId, Orthanc::ResourceType_Instance, orthancId))
    {
      AddOrthancInstance(target, orthancId);
      return Orthanc::ResourceType_Instance;
    }

    throw Orthanc::OrthancException(Orthanc::ErrorCode_UnknownResource);
  }


  void AuthorizationParserBase::AddOrthancInstance(AccessedResources& target,
                                                   const std::string& orthancId)
  {
    std::string patient, study, series;
    if (!resourceHierarchy_->LookupInstance(patient, study, series, orthancId))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_UnknownResource);
    }

    std::set<std::string> labels;

    resourceHierarchy_->GetLabels(labels, OrthancResource(Orthanc::ResourceType_Patient, patient));
    AddResourceInternal(target, Orthanc::ResourceType_Patient, patient, labels);

    resourceHierarchy_->GetLabels(labels, OrthancResource(Orthanc::ResourceType_Study, study));
    AddResourceInternal(target, Orthanc::ResourceType_Study, study, labels);

    resourceHierarchy_->GetLabels(labels, OrthancResource(Orthanc::ResourceType_Series, series));
    AddResourceInternal(target, Orthanc::ResourceType_Series, series, labels);

    resourceHierarchy_->GetLabels(labels, OrthancResource(Orthanc::ResourceType_Instance, orthancId));
    AddResourceInternal(target, Orthanc::ResourceType_Instance, orthancId, labels);
  }

  
  void AuthorizationParserBase::AddOrthancSeries(AccessedResources& target,
                                                 const std::string& orthancId)
  {
    std::string patient, study;
    if (!resourceHierarchy_->LookupSeries(patient, study, orthancId))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_UnknownResource);
    }

    std::set<std::string> labels;

    resourceHierarchy_->GetLabels(labels, OrthancResource(Orthanc::ResourceType_Patient, patient));
    AddResourceInternal(target, Orthanc::ResourceType_Patient, patient, labels);

    resourceHierarchy_->GetLabels(labels, OrthancResource(Orthanc::ResourceType_Study, study));
    AddResourceInternal(target, Orthanc::ResourceType_Study, study, labels);

    resourceHierarchy_->GetLabels(labels, OrthancResource(Orthanc::ResourceType_Series, orthancId));
    AddResourceInternal(target, Orthanc::ResourceType_Series, orthancId, labels);
  }

  
  void AuthorizationParserBase::AddOrthancStudy(AccessedResources& target,
                                                const std::string& orthancId)
  {
    std::string patient;
    if (!resourceHierarchy_->LookupStudy(patient, orthancId))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_UnknownResource);
    }

    std::set<std::string> labels;

    resourceHierarchy_->GetLabels(labels, OrthancResource(Orthanc::ResourceType_Patient, patient));
    AddResourceInternal(target, Orthanc::ResourceType_Patient, patient, labels);

    resourceHierarchy_->GetLabels(labels, OrthancResource(Orthanc::ResourceType_Study, orthancId));
    AddResourceInternal(target, Orthanc::ResourceType_Study, orthancId, labels);
  }

  
  void AuthorizationParserBase::AddOrthancPatient(AccessedResources& target,
                                                  const std::string& orthancId)
  {
    std::set<std::string> labels;

    resourceHierarchy_->GetLabels(labels, OrthancResource(Orthanc::ResourceType_Patient, orthancId));
    AddResourceInternal(target, Orthanc::ResourceType_Patient, orthancId, labels);
  }

  
  void AuthorizationParserBase::AddDicomStudy(AccessedResources& target,
                                              const std::string& studyDicomUid)
  {
    std::string patient, study;

    if (!resourceHierarchy_->LookupOrthancId(study, Orthanc::ResourceType_Study, studyDicomUid) ||
        !resourceHierarchy_->LookupStudy(patient, study))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_UnknownResource);
    }

    std::set<std::string> labels;

    resourceHierarchy_->GetLabels(labels, OrthancResource(Orthanc::ResourceType_Patient, patient));
    AddResourceInternal(target, Orthanc::ResourceType_Patient, patient, labels);

    resourceHierarchy_->GetLabels(labels, OrthancResource(Orthanc::ResourceType_Study, study));
    target.push_back(AccessedResource(Orthanc::ResourceType_Study, study, studyDicomUid, labels));
  }

  void AuthorizationParserBase::AddDicomPatient(AccessedResources& target,
                                                const std::string& patientId)
  {
    std::string patient;

    if (!resourceHierarchy_->LookupOrthancId(patient, Orthanc::ResourceType_Patient, patientId))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_UnknownResource);
    }

    std::set<std::string> labels;

    resourceHierarchy_->GetLabels(labels, OrthancResource(Orthanc::ResourceType_Patient, patient));
    AddResourceInternal(target, Orthanc::ResourceType_Patient, patient, labels);
  }
  
  void AuthorizationParserBase::AddDicomSeries(AccessedResources& target,
                                               const std::string& studyDicomUid,
                                               const std::string& seriesDicomUid)
  {
    std::string series;

    if (!resourceHierarchy_->LookupOrthancId(series, Orthanc::ResourceType_Series, seriesDicomUid))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_UnknownResource);
    }

    std::set<std::string> labels;

    AddDicomStudy(target, studyDicomUid);

    resourceHierarchy_->GetLabels(labels, OrthancResource(Orthanc::ResourceType_Series, series));
    target.push_back(AccessedResource(Orthanc::ResourceType_Series, series, seriesDicomUid, labels));
  }

  
  void AuthorizationParserBase::AddDicomInstance(AccessedResources& target,
                                                 const std::string& studyDicomUid,
                                                 const std::string& seriesDicomUid,
                                                 const std::string& instanceDicomUid)
  {
    std::string instance;

    if (!resourceHierarchy_->LookupOrthancId
        (instance, Orthanc::ResourceType_Instance, instanceDicomUid))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_UnknownResource);
    }

    std::set<std::string> labels;

    AddDicomSeries(target, studyDicomUid, seriesDicomUid);

    resourceHierarchy_->GetLabels(labels, OrthancResource(Orthanc::ResourceType_Instance, instance));
    target.push_back(AccessedResource(Orthanc::ResourceType_Instance, instance, instanceDicomUid, labels));
  }

  
  AuthorizationParserBase::AuthorizationParserBase(ICacheFactory& factory)
  {
    resourceHierarchy_.reset(new ResourceHierarchyCache(factory));

    if (resourceHierarchy_.get() == NULL)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
    }
  }
}
    
