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

#include "ResourceHierarchyCache.h"

#include <Logging.h>
#include <OrthancException.h>

#include <boost/lexical_cast.hpp>
#include <Toolbox.h>

namespace OrthancPlugins
{
  std::string ResourceHierarchyCache::ComputeKey(Orthanc::ResourceType level,
                                                 const std::string& identifier) const
  {
    return boost::lexical_cast<std::string>(level) + "|" + identifier;
  }
    

  void ResourceHierarchyCache::LinkParent(const OrthancResource& child,
                                          const OrthancResource& parent)
  {
    LOG(INFO) << "Linking " << Orthanc::EnumerationToString(child.GetLevel())
              << " \"" << child.GetIdentifier() << "\" to its parent "
              << Orthanc::EnumerationToString(parent.GetLevel())
              << " \"" << parent.GetIdentifier() << "\"";
        
    cache_->Store(ComputeKey(child), parent.GetIdentifier(), 0 /* no expiration */);
  }

  void ResourceHierarchyCache::GetLabels(std::set<std::string>& labels,
                                         const OrthancResource& resource)
  {
    labels.clear();
    
    std::string key = ComputeKey(resource);
    
    std::string serializedLabels;
    if (!labels_->Retrieve(serializedLabels, key))
    {
      // The labels were not already stored in the cache or they have expired
      OrthancResource parent;
      UpdateResourceFromOrthanc(parent, labels, resource);
    }
    else
    {
      Orthanc::Toolbox::SplitString(labels, serializedLabels, ',');
    }
  }


  void ResourceHierarchyCache::UpdateResourceFromOrthanc(OrthancResource& parent,
                                                         std::set<std::string>& labels,
                                                         const OrthancResource& resource)
  {
    std::string key = ComputeKey(resource);

    // Not in the cache, reading the resource from the Orthanc store
    std::string dicomUid;
    std::list<OrthancResource> children;

    if (!resource.GetHierarchy(dicomUid, parent, children, labels))
    {
      // The resource is non-existing (*)
      return;
    }

    orthancToDicom_->Store(key, dicomUid, 0 /* no expiration */);
    dicomToOrthanc_->Store(ComputeKey(resource.GetLevel(), dicomUid),
                           resource.GetIdentifier(), 0 /* no expiration */);
    std::string serializedLabels;
    Orthanc::Toolbox::JoinStrings(serializedLabels, labels, ",");
    labels_->Store(key, serializedLabels, 60);

    for (std::list<OrthancResource>::const_iterator
           it = children.begin(); it != children.end(); ++it)
    {
      // Cache the relation of the resource with its children
      LinkParent(*it, resource);
    }

    if (parent.IsValid())
    {
      LinkParent(resource, parent);
    }
  }


  bool ResourceHierarchyCache::LookupParent(std::string& target,
                                            const OrthancResource& resource)
  {
    std::string key = ComputeKey(resource);
      
    if (cache_->Retrieve(target, key))
    {
      // The parent was already stored in the cache
      return true;
    }

    OrthancResource parent;
    std::set<std::string> labels;
    UpdateResourceFromOrthanc(parent, labels, resource);

    if (parent.IsValid())
    {
      target = parent.GetIdentifier();
      return true;
    }
    else
    {
      // We reached the patient level, or the resource was removed
      // from Orthanc since (*)
      return false;
    }
  }


  ResourceHierarchyCache::ResourceHierarchyCache(ICacheFactory& factory) :
    cache_(factory.Create()),
    orthancToDicom_(factory.Create()),
    dicomToOrthanc_(factory.Create()),
    labels_(factory.Create())
  {
    if (cache_.get() == NULL)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
    }
  }

  
  void ResourceHierarchyCache::Invalidate(Orthanc::ResourceType level,
                                          const std::string& identifier)
  {
    LOG(INFO) << "Invalidating " << Orthanc::EnumerationToString(level)
              << " resource with ID: " << identifier;

    std::string key = ComputeKey(level, identifier);
    cache_->Invalidate(key);
    orthancToDicom_->Invalidate(key);
    labels_->Invalidate(key);
  }


  bool ResourceHierarchyCache::LookupSeries(std::string& patient,
                                            std::string& study,
                                            const std::string& series)
  {
    if (LookupParent(study, Orthanc::ResourceType_Series, series))
    {
      return LookupStudy(patient, study);
    }
    else
    {
      return false;
    }
  }

  
  bool ResourceHierarchyCache::LookupInstance(std::string& patient,
                                              std::string& study,
                                              std::string& series,
                                              const std::string& instance)
  {
    if (LookupParent(series, Orthanc::ResourceType_Instance, instance))
    {
      return LookupSeries(patient, study, series);
    }
    else
    {
      return false;
    }
  }


  bool ResourceHierarchyCache::LookupDicomUid(std::string& target,
                                              Orthanc::ResourceType level,
                                              const std::string& orthancId)
  {
    std::string key = ComputeKey(level, orthancId);

    if (orthancToDicom_->Retrieve(target, key))
    {
      return true;
    }

    OrthancResource resource(level, orthancId);

    if (resource.GetDicomUid(target))
    {
      orthancToDicom_->Store(key, target, 0 /* no expiration */);
      return true;
    }
    else
    {
      return false;
    }
  }

  
  bool ResourceHierarchyCache::LookupOrthancId(std::string& target,
                                               Orthanc::ResourceType level,
                                               const std::string& dicomUid)
  {
    std::string key = ComputeKey(level, dicomUid);

    if (dicomToOrthanc_->Retrieve(target, key))
    {
      return true;
    }

    if (OrthancResource::LookupOrthancId(target, level, dicomUid))
    {
      dicomToOrthanc_->Store(key, target, 0 /* no expiration */);
      return true;
    }
    else
    {
      return false;
    }
  }

#if BUILD_UNIT_TESTS == 1
  void ResourceHierarchyCache::AddOrthancDicomMapping(Orthanc::ResourceType level,
                                                      const std::string& orthancId,
                                                      const std::string& dicomUid)
  {
    dicomToOrthanc_->Store(ComputeKey(level, dicomUid), orthancId, 0 /* no expiration */);
    orthancToDicom_->Store(ComputeKey(level, orthancId), dicomUid, 0 /* no expiration */);
  }

  void ResourceHierarchyCache::AddParentLink(Orthanc::ResourceType childLevel,
                                             const std::string& childOrthancId,
                                             const std::string& parentOrthancId)
  {
    cache_->Store(ComputeKey(childLevel, childOrthancId), parentOrthancId, 0 /* no expiration */);
  }

  void ResourceHierarchyCache::AddLabels(Orthanc::ResourceType level,
                                         const std::string& orthancId,
                                         const std::string& serializedLabels)
  {
    labels_->Store(ComputeKey(level, orthancId), serializedLabels, 0 /* no expiration */);
  }

#endif

}
