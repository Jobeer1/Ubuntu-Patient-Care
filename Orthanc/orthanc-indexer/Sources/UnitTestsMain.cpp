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


#include <gtest/gtest.h>

#include "IndexerDatabase.h"
#include "StorageArea.h"

#include <Logging.h>
#include <OrthancException.h>
#include <SystemToolbox.h>
#include <Toolbox.h>


TEST(StorageArea, Basic)
{
  const std::string uuid = Orthanc::Toolbox::GenerateUuid();
  ASSERT_TRUE(Orthanc::Toolbox::IsUuid(uuid));

  StorageArea area("StorageAreaTests");
  
  area.Create(uuid, "Hello", 5);
  ASSERT_TRUE(Orthanc::SystemToolbox::IsRegularFile(area.GetPath(uuid)));

  std::string s;
  area.ReadWhole(s, uuid);
  ASSERT_EQ(5u, s.size());
  ASSERT_EQ("Hello", s);

  char data[10];
  OrthancPluginMemoryBuffer64 buffer;
  buffer.data = data;

  buffer.size = 1;
  area.ReadRange(&buffer, uuid, 0);  ASSERT_EQ('H', data[0]);
  area.ReadRange(&buffer, uuid, 4);  ASSERT_EQ('o', data[0]);
  ASSERT_THROW(area.ReadRange(&buffer, uuid, 5), Orthanc::OrthancException);
  
  buffer.size = 2;
  area.ReadRange(&buffer, uuid, 0);  ASSERT_EQ('H', data[0]);  ASSERT_EQ('e', data[1]);
  area.ReadRange(&buffer, uuid, 1);  ASSERT_EQ('e', data[0]);  ASSERT_EQ('l', data[1]);
  area.ReadRange(&buffer, uuid, 2);  ASSERT_EQ('l', data[0]);  ASSERT_EQ('l', data[1]);
  area.ReadRange(&buffer, uuid, 3);  ASSERT_EQ('l', data[0]);  ASSERT_EQ('o', data[1]);
  ASSERT_THROW(area.ReadRange(&buffer, uuid, 4), Orthanc::OrthancException);
  
  buffer.size = 3;
  area.ReadRange(&buffer, uuid, 0);  ASSERT_EQ('H', data[0]);  ASSERT_EQ('e', data[1]);  ASSERT_EQ('l', data[2]);
  area.ReadRange(&buffer, uuid, 1);  ASSERT_EQ('e', data[0]);  ASSERT_EQ('l', data[1]);  ASSERT_EQ('l', data[2]);
  area.ReadRange(&buffer, uuid, 2);  ASSERT_EQ('l', data[0]);  ASSERT_EQ('l', data[1]);  ASSERT_EQ('o', data[2]);
  ASSERT_THROW(area.ReadRange(&buffer, uuid, 3), Orthanc::OrthancException);
  
  buffer.size = 5;
  area.ReadRange(&buffer, uuid, 0);
  ASSERT_EQ('H', data[0]);
  ASSERT_EQ('e', data[1]);
  ASSERT_EQ('l', data[2]);
  ASSERT_EQ('l', data[3]);
  ASSERT_EQ('o', data[4]);
  ASSERT_THROW(area.ReadRange(&buffer, uuid, 1), Orthanc::OrthancException);
  
  area.RemoveAttachment(uuid);
  ASSERT_FALSE(Orthanc::SystemToolbox::IsRegularFile(area.GetPath(uuid)));

  ASSERT_THROW(area.ReadWhole(&buffer, uuid), Orthanc::OrthancException);
  ASSERT_THROW(area.ReadRange(&buffer, uuid, 0), Orthanc::OrthancException);
}



class Visitor : public IndexerDatabase::IFileVisitor
{
private:
  std::vector<std::string>  path_;
  std::vector<bool>         isDicom_;
  std::vector<std::string>  instanceId_;

public:
  virtual void VisitInstance(const std::string& path,
                             bool isDicom,
                             const std::string& instanceId) ORTHANC_OVERRIDE
  {
    path_.push_back(path);
    isDicom_.push_back(isDicom);
    instanceId_.push_back(instanceId);
  }

  void Clear()
  {
    path_.clear();
    isDicom_.clear();
    instanceId_.clear();
  }

  size_t GetSize() const
  {
    assert(path_.size() == isDicom_.size() &&
           path_.size() == instanceId_.size());
    return path_.size();
  }

  const std::string& GetPath(size_t i) const
  {
    assert(i < path_.size());
    return path_[i];
  }

  bool IsDicom(size_t i) const
  {
    assert(i < isDicom_.size());
    return isDicom_[i];
  }

  const std::string& GetInstanceId(size_t i) const
  {
    assert(i < instanceId_.size());
    return instanceId_[i];
  }

  void GetDicomPath(std::set<std::string>& target) const
  {
    target.clear();
    for (size_t i = 0; i < GetSize(); i++)
    {
      target.insert(GetPath(i));
    }
  }

  void GetInstanceId(std::set<std::string>& target) const
  {
    target.clear();
    for (size_t i = 0; i < GetSize(); i++)
    {
      target.insert(GetInstanceId(i));
    }
  }
};


TEST(IndexerDatabase, Files)
{
  Visitor v;
  
  IndexerDatabase db;
  ASSERT_THROW(db.Apply(v), Orthanc::OrthancException);  // DB is not opened

  db.OpenInMemory();
  db.Apply(v);
  ASSERT_EQ(0u, v.GetSize());

  ASSERT_EQ(0u, db.GetFilesCount());
  ASSERT_EQ(0u, db.GetAttachmentsCount());

  std::string s;
  ASSERT_EQ(IndexerDatabase::FileStatus_New, db.LookupFile(s, "some/path/to/dicom", 42 /* time */, 5 /* size */));

  db.AddDicomInstance("some/path/to/dicom", 42 /* time */, 5 /* size */, "instance1");
  db.Apply(v);
  ASSERT_EQ(1u, v.GetSize());
  ASSERT_EQ("some/path/to/dicom", v.GetPath(0));
  ASSERT_TRUE(v.IsDicom(0));
  ASSERT_EQ("instance1", v.GetInstanceId(0));

  ASSERT_EQ(IndexerDatabase::FileStatus_AlreadyStored, db.LookupFile(s, "some/path/to/dicom", 42 /* time */, 5 /* size */));
  ASSERT_EQ(IndexerDatabase::FileStatus_Modified, db.LookupFile(s, "some/path/to/dicom", 43 /* time */, 5 /* size */));
  ASSERT_EQ(IndexerDatabase::FileStatus_Modified, db.LookupFile(s, "some/path/to/dicom", 42 /* time */, 6 /* size */));
  
  ASSERT_EQ(1u, db.GetFilesCount());
  ASSERT_EQ(0u, db.GetAttachmentsCount());

  ASSERT_THROW(db.RemoveFile("nope"), Orthanc::OrthancException);
  ASSERT_TRUE(db.RemoveFile("some/path/to/dicom"));
  ASSERT_THROW(db.RemoveFile("some/path/to/dicom"), Orthanc::OrthancException);

  ASSERT_EQ(0u, db.GetFilesCount());
  ASSERT_EQ(0u, db.GetAttachmentsCount());

  v.Clear();
  db.Apply(v);
  ASSERT_EQ(0u, v.GetSize());

  ASSERT_EQ(IndexerDatabase::FileStatus_New, db.LookupFile(s, "some/path/to/text", 42 /* time */, 5 /* size */));

  db.AddNonDicomFile("some/path/to/text", 42 /* time */, 5 /* size */);
  db.Apply(v);
  ASSERT_EQ(1u, v.GetSize());
  ASSERT_EQ("some/path/to/text", v.GetPath(0));
  ASSERT_FALSE(v.IsDicom(0));
  ASSERT_TRUE(v.GetInstanceId(0).empty());

  ASSERT_EQ(1u, db.GetFilesCount());
  ASSERT_EQ(0u, db.GetAttachmentsCount());

  ASSERT_EQ(IndexerDatabase::FileStatus_NotDicom, db.LookupFile(s, "some/path/to/text", 42 /* time */, 5 /* size */));
  ASSERT_EQ(IndexerDatabase::FileStatus_Modified, db.LookupFile(s, "some/path/to/text", 43 /* time */, 5 /* size */));
  ASSERT_EQ(IndexerDatabase::FileStatus_Modified, db.LookupFile(s, "some/path/to/text", 42 /* time */, 6 /* size */));
  
  ASSERT_TRUE(db.RemoveFile("some/path/to/text"));
  ASSERT_THROW(db.RemoveFile("some/path/to/text"), Orthanc::OrthancException);

  v.Clear();
  db.Apply(v);
  ASSERT_EQ(0u, v.GetSize());

  ASSERT_EQ(0u, db.GetFilesCount());
  ASSERT_EQ(0u, db.GetAttachmentsCount());
}


TEST(IndexerDatabase, RemoveUsingRestApi)
{
  Visitor v;

  IndexerDatabase db;
  db.OpenInMemory();

  // Firstly, the plugin detects the new instances on the filesystem
  // and uploads them into Orthanc in the "ProcessFile()" function
  db.AddDicomInstance("sample.dcm", 42 /* time */, 5 /* size */, "instance1");

  db.Apply(v);
  ASSERT_EQ(1u, v.GetSize());
  ASSERT_EQ("sample.dcm", v.GetPath(0));
  ASSERT_TRUE(v.IsDicom(0));
  ASSERT_EQ("instance1", v.GetInstanceId(0));

  std::string path;
  ASSERT_FALSE(db.LookupAttachment(path, "uuid1"));
  ASSERT_FALSE(db.LookupAttachment(path, "uuid2"));

  ASSERT_EQ(1u, db.GetFilesCount());
  ASSERT_EQ(0u, db.GetAttachmentsCount());
  
  // Secondly, the storage area plugin parses DICOM attachments in
  // order to extract their Orthanc ID, and indexes them in the DB
  ASSERT_TRUE(db.AddAttachment("uuid1", "instance1"));
  ASSERT_FALSE(db.AddAttachment("uuid2", "instance2"));

  ASSERT_TRUE(db.LookupAttachment(path, "uuid1"));
  ASSERT_EQ("sample.dcm", path);
  ASSERT_FALSE(db.LookupAttachment(path, "uuid2"));

  db.RemoveAttachment("uuid2");

  ASSERT_EQ(1u, db.GetFilesCount());
  ASSERT_EQ(1u, db.GetAttachmentsCount());

  // Thirdly, the user deletes the DICOM instance using the REST API,
  // which causes the storage area to remove the attachment
  db.RemoveAttachment("uuid1");
  db.RemoveAttachment("uuid1");

  v.Clear();
  db.Apply(v);
  ASSERT_EQ(1u, v.GetSize());
  ASSERT_EQ("sample.dcm", v.GetPath(0));
  ASSERT_TRUE(v.IsDicom(0));
  ASSERT_EQ("instance1", v.GetInstanceId(0));

  ASSERT_EQ(1u, db.GetFilesCount());
  ASSERT_EQ(0u, db.GetAttachmentsCount());

  db.RemoveFile("sample.dcm");
  ASSERT_THROW(db.RemoveFile("sample.dcm"), Orthanc::OrthancException);
  ASSERT_EQ(0u, db.GetFilesCount());
  ASSERT_EQ(0u, db.GetAttachmentsCount());
}


TEST(IndexerDatabase, RemoveFromFilesystem)
{
  Visitor v;

  IndexerDatabase db;
  db.OpenInMemory();

  // Firstly, the plugin finds two copies of the same DICOM instance
  db.AddDicomInstance("copy1.dcm", 42 /* time */, 5 /* size */, "instance1");
  db.AddDicomInstance("copy2.dcm", 43 /* time */, 6 /* size */, "instance1");

  std::set<std::string> s;
  db.Apply(v);
  v.GetDicomPath(s);
  ASSERT_EQ(2u, s.size());
  ASSERT_TRUE(s.find("copy1.dcm") != s.end());
  ASSERT_TRUE(s.find("copy2.dcm") != s.end());
  v.GetInstanceId(s);
  ASSERT_EQ(1u, s.size());
  ASSERT_TRUE(s.find("instance1") != s.end());

  std::string path;
  ASSERT_FALSE(db.LookupAttachment(path, "uuid1"));
  
  ASSERT_EQ(2u, db.GetFilesCount());
  ASSERT_EQ(0u, db.GetAttachmentsCount());

  // Secondly, the storage area plugin parses DICOM attachments in
  // order to extract their Orthanc ID, and indexes them in the DB
  ASSERT_TRUE(db.AddAttachment("uuid1", "instance1"));
  ASSERT_THROW(db.AddAttachment("uuid1", "instance1"), Orthanc::OrthancException);  // Constraint violation

  ASSERT_TRUE(db.LookupAttachment(path, "uuid1"));
  ASSERT_TRUE(path == "copy1.dcm" || path == "copy2.dcm");
  ASSERT_FALSE(db.LookupAttachment(path, "uuid2"));

  ASSERT_EQ(2u, db.GetFilesCount());
  ASSERT_EQ(1u, db.GetAttachmentsCount());

  // Thirdly, one of the two copies is removed from the filesystem
  ASSERT_FALSE(db.RemoveFile("copy1.dcm"));  // "false" means that there is still one copy
  ASSERT_TRUE(db.LookupAttachment(path, "uuid1"));
  ASSERT_EQ("copy2.dcm", path);

  ASSERT_EQ(1u, db.GetFilesCount());
  ASSERT_EQ(1u, db.GetAttachmentsCount());

  v.Clear();
  db.Apply(v);
  ASSERT_EQ(1u, v.GetSize());
  ASSERT_EQ("copy2.dcm", v.GetPath(0));
  ASSERT_TRUE(v.IsDicom(0));
  ASSERT_EQ("instance1", v.GetInstanceId(0));

  // Fourthly, the second copy is also removed, which causes a call to
  // "OrthancPluginRestApiDelete()"
  ASSERT_TRUE(db.RemoveFile("copy2.dcm"));  // "true" means this was the last copy
  ASSERT_FALSE(db.LookupAttachment(path, "uuid1"));

  v.Clear();
  db.Apply(v);
  ASSERT_EQ(0u, v.GetSize());

  ASSERT_EQ(0u, db.GetFilesCount());
  ASSERT_EQ(1u, db.GetAttachmentsCount());

  // Finally, because of the call to "OrthancPluginRestApiDelete()",
  // Orthanc removes the attachment from the file storage
  db.RemoveAttachment("uuid1");
  ASSERT_EQ(0u, db.GetFilesCount());
  ASSERT_EQ(0u, db.GetAttachmentsCount());
}


int main(int argc, char **argv)
{
  Orthanc::Logging::Initialize();
  Orthanc::Logging::EnableInfoLevel(true);

  ::testing::InitGoogleTest(&argc, argv);
  int result = RUN_ALL_TESTS();

  Orthanc::Logging::Finalize();

  return result;
}
