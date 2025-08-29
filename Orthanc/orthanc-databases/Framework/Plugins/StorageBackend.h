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

#include "../Common/DatabaseManager.h"

#include <orthanc/OrthancCDatabasePlugin.h>

#include <boost/thread/mutex.hpp>


namespace OrthancDatabases
{
  class StorageBackend : public boost::noncopyable
  {
  public:
    class IFileContentVisitor : public boost::noncopyable
    {
    public:
      virtual ~IFileContentVisitor()
      {
      }

      virtual void Assign(const std::string& content) = 0;

      virtual bool IsSuccess() const = 0;
    };

    class IAccessor : public boost::noncopyable
    {
    public:
      virtual ~IAccessor()
      {
      }

      virtual void Create(const std::string& uuid,
                          const void* content,
                          size_t size,
                          OrthancPluginContentType type) = 0;

      virtual void ReadWhole(IFileContentVisitor& visitor,
                             const std::string& uuid,
                             OrthancPluginContentType type) = 0;

      virtual void ReadRange(IFileContentVisitor& visitor,
                             const std::string& uuid,
                             OrthancPluginContentType type,
                             uint64_t start,
                             size_t length) = 0;
      
      virtual void Remove(const std::string& uuid,
                          OrthancPluginContentType type) = 0;
    };
    
    /**
     * This class is similar to
     * "Orthanc::StatelessDatabaseOperations": It handles retries of
     * transactions in the case of collision between multiple
     * readers/writers.
     **/
    class IDatabaseOperation : public boost::noncopyable
    {
    public:
      virtual ~IDatabaseOperation()
      {
      }

      virtual void Execute(IAccessor& accessor) = 0;
    };

    class ReadWholeOperation;

  private:
    class StringVisitor;
    
    boost::mutex      mutex_;
    DatabaseManager   manager_;
    unsigned int      maxRetries_;

  protected:
    class AccessorBase : public IAccessor
    {
    private:
      boost::mutex::scoped_lock  lock_;
      DatabaseManager&           manager_;

    public:
      explicit AccessorBase(StorageBackend& backend) :
        lock_(backend.mutex_),
        manager_(backend.manager_)
      {
      }

      DatabaseManager& GetManager() const
      {
        return manager_;
      }

      virtual void Create(const std::string& uuid,
                          const void* content,
                          size_t size,
                          OrthancPluginContentType type) ORTHANC_OVERRIDE;

      virtual void ReadWhole(IFileContentVisitor& visitor,
                             const std::string& uuid,
                             OrthancPluginContentType type) ORTHANC_OVERRIDE;

      virtual void ReadRange(IFileContentVisitor& visitor,
                             const std::string& uuid,
                             OrthancPluginContentType type,
                             uint64_t start,
                             size_t length) ORTHANC_OVERRIDE;
      
      virtual void Remove(const std::string& uuid,
                          OrthancPluginContentType type) ORTHANC_OVERRIDE;
    };
    
    virtual bool HasReadRange() const = 0;

  public:
    StorageBackend(IDatabaseFactory* factory /* takes ownership */,
                   unsigned int maxRetries);

    virtual ~StorageBackend()
    {
    }

    virtual IAccessor* CreateAccessor()
    {
      return new AccessorBase(*this);
    }

    static void Register(OrthancPluginContext* context,
                         StorageBackend* backend);   // Takes ownership

    static void Finalize();

    // For unit tests
    static void ReadWholeToString(std::string& target,
                                  IAccessor& accessor,
                                  const std::string& uuid,
                                  OrthancPluginContentType type);

    // For unit tests
    static void ReadRangeToString(std::string& target,
                                  IAccessor& accessor,
                                  const std::string& uuid,
                                  OrthancPluginContentType type,
                                  uint64_t start,
                                  size_t length);

    unsigned int GetMaxRetries() const
    {
      return maxRetries_;
    }

    void Execute(IDatabaseOperation& operation);
  };
}
