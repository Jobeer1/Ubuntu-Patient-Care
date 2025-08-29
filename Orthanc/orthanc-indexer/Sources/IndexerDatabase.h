/**
 * Indexer plugin for Orthanc
 * Copyright (C) 2021-2025 Sebastien Jodogne, ICTEAM UCLouvain, Belgium
 *
 * This program is free software: you can redistribute it and/or
 * modify it under the terms of the GNU General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program. If not, see <http://www.gnu.org/licenses/>.
 **/


#pragma once

#include <OrthancFramework.h>  // To have ORTHANC_ENABLE_SQLITE defined
#include <SQLite/Connection.h>

#include <boost/noncopyable.hpp>
#include <boost/thread/mutex.hpp>


class IndexerDatabase : public boost::noncopyable
{
public:
  enum FileStatus
  {
    FileStatus_New,
    FileStatus_Modified,
    FileStatus_AlreadyStored,
    FileStatus_NotDicom
  };

  class IFileVisitor : public boost::noncopyable
  {
  public:
    virtual ~IFileVisitor()
    {
    }

    virtual void VisitInstance(const std::string& path,
                               bool isDicom,
                               const std::string& instanceId) = 0;
  };  


private:
  boost::mutex                 mutex_;
  Orthanc::SQLite::Connection  db_;
  
  void Initialize();

  void AddFileInternal(const std::string& path,
                       const std::time_t time,
                       const uintmax_t size,
                       bool isDicom,
                       const std::string& instanceId);

public:
  void Open(const std::string& path);

  void OpenInMemory();  // For unit tests

  FileStatus LookupFile(std::string& oldInstanceId,
                        const std::string& path,
                        const std::time_t time,
                        const uintmax_t size);

  // Returns "true" iff. this file was the last copy of some DICOM instance
  bool RemoveFile(const std::string& path);

  void AddDicomInstance(const std::string& path,
                        const std::time_t time,
                        const uintmax_t size,
                        const std::string& instanceId);
  
  void AddNonDicomFile(const std::string& path,
                       const std::time_t time,
                       const uintmax_t size);

  // Warning: The visitor is invoked in mutual exclusion, so it
  // shouldn't do lengthy operations
  void Apply(IFileVisitor& visitor);

  // Returns "false" iff. this instance has not been previously
  // registerded using "AddDicomInstance()", which indicates the
  // import of an external DICOM file
  bool AddAttachment(const std::string& uuid,
                     const std::string& instanceId);

  bool LookupAttachment(std::string& path,
                        const std::string& uuid);

  void RemoveAttachment(const std::string& uuid);

  unsigned int GetFilesCount();  // For unit testing

  unsigned int GetAttachmentsCount();  // For unit testing
};
