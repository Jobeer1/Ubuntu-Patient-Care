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


#include "IndexerDatabase.h"

#include <EmbeddedResources.h>
#include <SQLite/Transaction.h>


void IndexerDatabase::AddFileInternal(const std::string& path,
                                      const std::time_t time,
                                      const uintmax_t size,
                                      bool isDicom,
                                      const std::string& instanceId)
{
  Orthanc::SQLite::Transaction transaction(db_);
  transaction.Begin();

  Orthanc::SQLite::Statement statement(db_, SQLITE_FROM_HERE,
                                       "INSERT INTO Files VALUES(?, ?, ?, ?, ?)");
  statement.BindString(0, path);
  statement.BindInt64(1, time);
  statement.BindInt64(2, size);
  statement.BindInt64(3, isDicom);
  statement.BindString(4, instanceId);
  statement.Run();

  transaction.Commit();
}


void IndexerDatabase::Initialize()
{
  {
    Orthanc::SQLite::Transaction transaction(db_);
    transaction.Begin();

    if (!db_.DoesTableExist("Attachments"))
    {
      std::string sql;
      Orthanc::EmbeddedResources::GetFileResource(sql, Orthanc::EmbeddedResources::PREPARE_DATABASE);
      db_.Execute(sql);
    }

    transaction.Commit();
  }
    
  // Performance tuning of SQLite with PRAGMAs
  // http://www.sqlite.org/pragma.html
  db_.Execute("PRAGMA SYNCHRONOUS=NORMAL;");
  db_.Execute("PRAGMA JOURNAL_MODE=WAL;");
  db_.Execute("PRAGMA LOCKING_MODE=EXCLUSIVE;");
  db_.Execute("PRAGMA WAL_AUTOCHECKPOINT=1000;");
}


void IndexerDatabase::Open(const std::string& path)
{
  boost::mutex::scoped_lock lock(mutex_);
  db_.Open(path);
  Initialize();
}
  

void IndexerDatabase::OpenInMemory()
{
  boost::mutex::scoped_lock lock(mutex_);
  db_.OpenInMemory();
  Initialize();
}
  

IndexerDatabase::FileStatus IndexerDatabase::LookupFile(std::string& oldInstanceId,
                                                        const std::string& path,
                                                        const std::time_t time,
                                                        const uintmax_t size)
{
  boost::mutex::scoped_lock lock(mutex_);
    
  FileStatus result;
  
  Orthanc::SQLite::Transaction transaction(db_);
  transaction.Begin();

  {
    Orthanc::SQLite::Statement statement(db_, SQLITE_FROM_HERE,
                                         "SELECT time, size, isDicom, instanceId FROM Files WHERE path=?");
    statement.BindString(0, path);

    if (statement.Step())
    {
      if (time == static_cast<std::time_t>(statement.ColumnInt64(0)) &&
          size == static_cast<uintmax_t>(statement.ColumnInt64(1)))
      {
        if (statement.ColumnBool(2))
        {
          result = FileStatus_AlreadyStored;
        }
        else
        {
          result = FileStatus_NotDicom;
        }
      }
      else
      {
        result = FileStatus_Modified;
        oldInstanceId = statement.ColumnString(3);
      }
    }
    else
    {
      result = FileStatus_New;
    }
  }

  transaction.Commit();

  return result;
}
  

bool IndexerDatabase::RemoveFile(const std::string& path)
{
  boost::mutex::scoped_lock lock(mutex_);
    
  Orthanc::SQLite::Transaction transaction(db_);
  transaction.Begin();

  std::string instanceId;

  {
    Orthanc::SQLite::Statement statement(db_, SQLITE_FROM_HERE,
                                         "SELECT instanceId FROM Files WHERE path=?");
    statement.BindString(0, path);
      
    if (statement.Step())
    {
      instanceId = statement.ColumnString(0);
    }
    else
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_InexistentItem);
    }
  }

  bool isLastInstance;
    
  {
    Orthanc::SQLite::Statement statement(db_, SQLITE_FROM_HERE,
                                         "SELECT COUNT(*) FROM Files WHERE instanceId=?");
    statement.BindString(0, instanceId);
      
    if (statement.Step())
    {
      int64_t count = statement.ColumnInt64(0);
      if (count == 0)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
      }
      else
      {
        isLastInstance = (count == 1);
      }
    }
    else
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
    }
  }
    
  {
    Orthanc::SQLite::Statement statement(db_, SQLITE_FROM_HERE,
                                         "DELETE FROM Files WHERE path=?");
    statement.BindString(0, path);
    statement.Run();
  }
    
  transaction.Commit();
  return isLastInstance;
}


void IndexerDatabase::AddDicomInstance(const std::string& path,
                                       const std::time_t time,
                                       const uintmax_t size,
                                       const std::string& instanceId)
{
  boost::mutex::scoped_lock lock(mutex_);
  AddFileInternal(path, time, size, true, instanceId);
}               


void IndexerDatabase::AddNonDicomFile(const std::string& path,
                                      const std::time_t time,
                                      const uintmax_t size)
{
  boost::mutex::scoped_lock lock(mutex_);
  AddFileInternal(path, time, size, false, "");
}


void IndexerDatabase::Apply(IFileVisitor& visitor)
{
  boost::mutex::scoped_lock lock(mutex_);
    
  Orthanc::SQLite::Transaction transaction(db_);
  transaction.Begin();

  Orthanc::SQLite::Statement statement(db_, SQLITE_FROM_HERE,
                                       "SELECT path, isDicom, instanceId FROM Files");

  while (statement.Step())
  {
    visitor.VisitInstance(statement.ColumnString(0), statement.ColumnBool(1), statement.ColumnString(2));
  }
        
  transaction.Commit();
}


bool IndexerDatabase::AddAttachment(const std::string& uuid,
                                    const std::string& instanceId)
{
  boost::mutex::scoped_lock lock(mutex_);
    
  Orthanc::SQLite::Transaction transaction(db_);
  transaction.Begin();

  {
    Orthanc::SQLite::Statement statement(db_, SQLITE_FROM_HERE,
                                         "SELECT COUNT(*) FROM Files WHERE instanceId=?");
    statement.BindString(0, instanceId);
      
    if (!statement.Step() ||
        statement.ColumnInt64(0) == 0)
    {
      return false;
    }
  }

  {
    Orthanc::SQLite::Statement statement(db_, SQLITE_FROM_HERE,
                                         "INSERT INTO Attachments VALUES(?, ?)");
    statement.BindString(0, uuid);
    statement.BindString(1, instanceId);
    statement.Run();
  }
  
  transaction.Commit();
  return true;
}


bool IndexerDatabase::LookupAttachment(std::string& path,
                                       const std::string& uuid)
{
  boost::mutex::scoped_lock lock(mutex_);
    
  Orthanc::SQLite::Transaction transaction(db_);
  transaction.Begin();

  bool found = true;
  std::string instanceId;
    
  {
    Orthanc::SQLite::Statement statement(db_, SQLITE_FROM_HERE,
                                         "SELECT instanceId FROM Attachments WHERE uuid=?");
    statement.BindString(0, uuid);
      
    if (statement.Step())
    {
      instanceId = statement.ColumnString(0);
    }
    else
    {
      found = false;
    }
  }

  if (found)
  {
    Orthanc::SQLite::Statement statement(db_, SQLITE_FROM_HERE,
                                         "SELECT path FROM Files WHERE instanceId=?");
    statement.BindString(0, instanceId);

    if (statement.Step())
    {
      path = statement.ColumnString(0);
    }
    else
    {
      found = false;
    }
  }

  transaction.Commit();
  return found;
}


void IndexerDatabase::RemoveAttachment(const std::string& uuid)
{
  boost::mutex::scoped_lock lock(mutex_);
    
  Orthanc::SQLite::Transaction transaction(db_);
  transaction.Begin();

  {
    Orthanc::SQLite::Statement statement(db_, SQLITE_FROM_HERE,
                                         "DELETE FROM Attachments WHERE uuid=?");
    statement.BindString(0, uuid);
    statement.Run();
  }
    
  transaction.Commit();
}


unsigned int IndexerDatabase::GetFilesCount()
{
  Orthanc::SQLite::Statement statement(db_, SQLITE_FROM_HERE,
                                       "SELECT COUNT(*) FROM Files");
  statement.Step();
  return static_cast<unsigned int>(statement.ColumnInt64(0));
}


unsigned int IndexerDatabase::GetAttachmentsCount()
{
  Orthanc::SQLite::Statement statement(db_, SQLITE_FROM_HERE,
                                       "SELECT COUNT(*) FROM Attachments");
  statement.Step();
  return static_cast<unsigned int>(statement.ColumnInt64(0));
}
