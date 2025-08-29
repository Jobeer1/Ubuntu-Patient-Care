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


#include "../Framework/DownloadArea.h"

#include <Compression/GzipCompressor.h>
#include <Logging.h>
#include <OrthancException.h>
#include <gtest/gtest.h>


TEST(Toolbox, Enumerations)
{
  using namespace OrthancPlugins;
  ASSERT_EQ(BucketCompression_None, StringToBucketCompression(EnumerationToString(BucketCompression_None)));
  ASSERT_EQ(BucketCompression_Gzip, StringToBucketCompression(EnumerationToString(BucketCompression_Gzip)));
  ASSERT_THROW(StringToBucketCompression("None"), Orthanc::OrthancException);
}


TEST(Toolbox, Conversions)
{
  ASSERT_EQ(2u, OrthancPlugins::ConvertToKilobytes(2048));
  ASSERT_EQ(1u, OrthancPlugins::ConvertToKilobytes(1000));
  ASSERT_EQ(0u, OrthancPlugins::ConvertToKilobytes(500));

  ASSERT_EQ(2u, OrthancPlugins::ConvertToMegabytes(2048 * 1024));
  ASSERT_EQ(1u, OrthancPlugins::ConvertToMegabytes(1000 * 1024));
  ASSERT_EQ(0u, OrthancPlugins::ConvertToMegabytes(500 * 1024));
}


TEST(TransferBucket, Basic)
{  
  using namespace OrthancPlugins;

  DicomInstanceInfo d1("d1", 10, "");
  DicomInstanceInfo d2("d2", 20, "");
  DicomInstanceInfo d3("d3", 30, "");
  DicomInstanceInfo d4("d4", 40, "");

  {
    TransferBucket b;
    ASSERT_EQ(0u, b.GetTotalSize());
    ASSERT_EQ(0u, b.GetChunksCount());

    b.AddChunk(d1, 0, 10);
    b.AddChunk(d2, 0, 20);
    ASSERT_THROW(b.AddChunk(d3, 0, 31), Orthanc::OrthancException);
    ASSERT_THROW(b.AddChunk(d3, 1, 30), Orthanc::OrthancException);
    b.AddChunk(d3, 0, 30);
    
    ASSERT_EQ(60u, b.GetTotalSize());
    ASSERT_EQ(3u, b.GetChunksCount());

    ASSERT_EQ("d1", b.GetChunkInstanceId(0));
    ASSERT_EQ(0u, b.GetChunkOffset(0));
    ASSERT_EQ(10u, b.GetChunkSize(0));
    ASSERT_EQ("d2", b.GetChunkInstanceId(1));
    ASSERT_EQ(0u, b.GetChunkOffset(1));
    ASSERT_EQ(20u, b.GetChunkSize(1));
    ASSERT_EQ("d3", b.GetChunkInstanceId(2));
    ASSERT_EQ(0u, b.GetChunkOffset(2));
    ASSERT_EQ(30u, b.GetChunkSize(2));

    std::string uri;
    b.ComputePullUri(uri, BucketCompression_None);
    ASSERT_EQ("/transfers/chunks/d1.d2.d3?offset=0&size=60&compression=none", uri);
    b.ComputePullUri(uri, BucketCompression_Gzip);
    ASSERT_EQ("/transfers/chunks/d1.d2.d3?offset=0&size=60&compression=gzip", uri);
      
    b.Clear();
    ASSERT_EQ(0u, b.GetTotalSize());
    ASSERT_EQ(0u, b.GetChunksCount());

    ASSERT_THROW(b.ComputePullUri(uri, BucketCompression_None), Orthanc::OrthancException);  // Empty
  }

  {
    TransferBucket b;
    b.AddChunk(d1, 5, 5);
    ASSERT_THROW(b.AddChunk(d2, 1, 7), Orthanc::OrthancException);  // Can only skip bytes in 1st chunk
    b.AddChunk(d2, 0, 20);
    b.AddChunk(d3, 0, 7);
    ASSERT_THROW(b.AddChunk(d4, 0, 10), Orthanc::OrthancException); // d2 was not complete

    ASSERT_EQ(32u, b.GetTotalSize());
    ASSERT_EQ(3u, b.GetChunksCount());

    ASSERT_EQ("d1", b.GetChunkInstanceId(0));
    ASSERT_EQ(5u, b.GetChunkOffset(0));
    ASSERT_EQ(5u, b.GetChunkSize(0));
    ASSERT_EQ("d2", b.GetChunkInstanceId(1));
    ASSERT_EQ(0u, b.GetChunkOffset(1));
    ASSERT_EQ(20u, b.GetChunkSize(1));
    ASSERT_EQ("d3", b.GetChunkInstanceId(2));
    ASSERT_EQ(0u, b.GetChunkOffset(2));
    ASSERT_EQ(7u, b.GetChunkSize(2));
    
    std::string uri;
    b.ComputePullUri(uri, BucketCompression_None);
    ASSERT_EQ("/transfers/chunks/d1.d2.d3?offset=5&size=32&compression=none", uri);
    b.ComputePullUri(uri, BucketCompression_Gzip);
    ASSERT_EQ("/transfers/chunks/d1.d2.d3?offset=5&size=32&compression=gzip", uri);

    b.Clear();
    ASSERT_EQ(0u, b.GetTotalSize());
    ASSERT_EQ(0u, b.GetChunksCount());

    b.AddChunk(d2, 1, 7);
    ASSERT_EQ(7u, b.GetTotalSize());
    ASSERT_EQ(1u, b.GetChunksCount());
  }
}


TEST(TransferBucket, Serialization)
{  
  using namespace OrthancPlugins;

  Json::Value s;
  
  {
    DicomInstanceInfo d1("d1", 10, "");
    DicomInstanceInfo d2("d2", 20, "");
    DicomInstanceInfo d3("d3", 30, "");

    TransferBucket b;
    b.AddChunk(d1, 5, 5);
    b.AddChunk(d2, 0, 20);
    b.AddChunk(d3, 0, 7);
    b.Serialize(s);
  }

  {
    TransferBucket b(s);

    std::string uri;
    b.ComputePullUri(uri, BucketCompression_None);
    ASSERT_EQ("/transfers/chunks/d1.d2.d3?offset=5&size=32&compression=none", uri);
  }
}


TEST(TransferScheduler, Empty)
{  
  using namespace OrthancPlugins;

  TransferScheduler s;
  ASSERT_EQ(0u, s.GetInstancesCount());
  ASSERT_EQ(0u, s.GetTotalSize());

  std::vector<DicomInstanceInfo> i;
  s.ListInstances(i);
  ASSERT_TRUE(i.empty());

  std::vector<TransferBucket> b;
  s.ComputePullBuckets(b, 10, 1000, "http://localhost/", BucketCompression_None);
  ASSERT_TRUE(b.empty());

  Json::Value v;
  s.FormatPushTransaction(v, b, 10, 1000, BucketCompression_None);
  ASSERT_TRUE(b.empty());
  ASSERT_EQ(Json::objectValue, v.type());
  ASSERT_TRUE(v.isMember("Buckets"));
  ASSERT_TRUE(v.isMember("Compression"));
  ASSERT_TRUE(v.isMember("Instances"));
  ASSERT_EQ(Json::arrayValue, v["Buckets"].type());
  ASSERT_EQ(Json::stringValue, v["Compression"].type());
  ASSERT_EQ(Json::arrayValue, v["Instances"].type());
  ASSERT_EQ(0u, v["Buckets"].size());
  ASSERT_EQ("none", v["Compression"].asString());
  ASSERT_EQ(0u, v["Instances"].size());
}


TEST(TransferScheduler, Basic)
{  
  using namespace OrthancPlugins;

  DicomInstanceInfo d1("d1", 10, "md1");
  DicomInstanceInfo d2("d2", 10, "md2");
  DicomInstanceInfo d3("d3", 10, "md3");

  TransferScheduler s;
  s.AddInstance(d1);
  s.AddInstance(d2);
  s.AddInstance(d3);

  std::vector<DicomInstanceInfo> i;
  s.ListInstances(i);
  ASSERT_EQ(3u, i.size());

  std::vector<TransferBucket> b;
  s.ComputePullBuckets(b, 10, 1000, "http://localhost/", BucketCompression_None);
  ASSERT_EQ(3u, b.size());
  ASSERT_EQ(1u, b[0].GetChunksCount());
  ASSERT_EQ("d1", b[0].GetChunkInstanceId(0));
  ASSERT_EQ(0u, b[0].GetChunkOffset(0));
  ASSERT_EQ(10u, b[0].GetChunkSize(0));
  ASSERT_EQ(1u, b[1].GetChunksCount());
  ASSERT_EQ("d2", b[1].GetChunkInstanceId(0));
  ASSERT_EQ(0u, b[1].GetChunkOffset(0));
  ASSERT_EQ(10u, b[1].GetChunkSize(0));
  ASSERT_EQ(1u, b[2].GetChunksCount());
  ASSERT_EQ("d3", b[2].GetChunkInstanceId(0));
  ASSERT_EQ(0u, b[2].GetChunkOffset(0));
  ASSERT_EQ(10u, b[2].GetChunkSize(0));

  Json::Value v;
  s.FormatPushTransaction(v, b, 10, 1000, BucketCompression_Gzip);
  ASSERT_EQ(3u, b.size());
  ASSERT_EQ(3u, v["Buckets"].size());
  ASSERT_EQ("gzip", v["Compression"].asString());
  ASSERT_EQ(3u, v["Instances"].size());

  for (Json::Value::ArrayIndex j = 0; j < 3; j++)
  {
    TransferBucket t(v["Buckets"][j]);
    ASSERT_EQ(1u, t.GetChunksCount());
    if (j == 0)
      ASSERT_EQ("d1", t.GetChunkInstanceId(0));
    else if (j == 1)
      ASSERT_EQ("d2", t.GetChunkInstanceId(0));
    else
      ASSERT_EQ("d3", t.GetChunkInstanceId(0));
        
    ASSERT_EQ(0u, t.GetChunkOffset(0));
    ASSERT_EQ(10u, t.GetChunkSize(0));
  }
    
  for (Json::Value::ArrayIndex j = 0; j < 3; j++)
  {
    DicomInstanceInfo d(v["Instances"][j]);
    if (j == 0)
    {
      ASSERT_EQ("d1", d.GetId());
      ASSERT_EQ("md1", d.GetMD5());
    }
    else if (j == 1)
    {
      ASSERT_EQ("d2", d.GetId());
      ASSERT_EQ("md2", d.GetMD5());
    }
    else
    {
      ASSERT_EQ("d3", d.GetId());
      ASSERT_EQ("md3", d.GetMD5());
    }
        
    ASSERT_EQ(10u, d.GetSize());
  }
}



TEST(TransferScheduler, Grouping)
{  
  using namespace OrthancPlugins;

  DicomInstanceInfo d1("d1", 10, "md1");
  DicomInstanceInfo d2("d2", 10, "md2");
  DicomInstanceInfo d3("d3", 10, "md3");

  TransferScheduler s;
  s.AddInstance(d1);
  s.AddInstance(d2);
  s.AddInstance(d3);

  {
    std::vector<TransferBucket> b;
    s.ComputePullBuckets(b, 20, 1000, "http://localhost/", BucketCompression_None);
    ASSERT_EQ(2u, b.size());
    ASSERT_EQ(2u, b[0].GetChunksCount());
    ASSERT_EQ("d1", b[0].GetChunkInstanceId(0));
    ASSERT_EQ("d2", b[0].GetChunkInstanceId(1));
    ASSERT_EQ(1u, b[1].GetChunksCount());    
    ASSERT_EQ("d3", b[1].GetChunkInstanceId(0));
  }

  {
    std::vector<TransferBucket> b;
    s.ComputePullBuckets(b, 21, 1000, "http://localhost/", BucketCompression_None);
    ASSERT_EQ(1u, b.size());
    ASSERT_EQ(3u, b[0].GetChunksCount());
    ASSERT_EQ("d1", b[0].GetChunkInstanceId(0));
    ASSERT_EQ("d2", b[0].GetChunkInstanceId(1));
    ASSERT_EQ("d3", b[0].GetChunkInstanceId(2));
  }

  {
    std::string longBase(2048, '_');
    std::vector<TransferBucket> b;
    s.ComputePullBuckets(b, 21, 1000, longBase, BucketCompression_None);
    ASSERT_EQ(3u, b.size());
    ASSERT_EQ(1u, b[0].GetChunksCount());
    ASSERT_EQ("d1", b[0].GetChunkInstanceId(0));
    ASSERT_EQ(1u, b[1].GetChunksCount());
    ASSERT_EQ("d2", b[1].GetChunkInstanceId(0));
    ASSERT_EQ(1u, b[2].GetChunksCount());
    ASSERT_EQ("d3", b[2].GetChunkInstanceId(0));
  }
}


TEST(TransferScheduler, Splitting)
{  
  using namespace OrthancPlugins;

  for (size_t i = 1; i < 20; i++)
  {
    DicomInstanceInfo dicom("dicom", i, "");

    TransferScheduler s;
    s.AddInstance(dicom);

    {
      std::vector<TransferBucket> b;
      s.ComputePullBuckets(b, 1, 1000, "http://localhost/", BucketCompression_None);
      ASSERT_EQ(1u, b.size());
      ASSERT_EQ(1u, b[0].GetChunksCount());
      ASSERT_EQ("dicom", b[0].GetChunkInstanceId(0));
      ASSERT_EQ(0u, b[0].GetChunkOffset(0));
      ASSERT_EQ(i, b[0].GetChunkSize(0));
    }

    for (size_t split = 1; split < 20; split++)
    {
      size_t count;
      if (dicom.GetSize() % split != 0)
        count = dicom.GetSize() / split + 1;
      else
        count = dicom.GetSize() / split;
    
      std::vector<TransferBucket> b;
      s.ComputePullBuckets(b, 1, split, "http://localhost/", BucketCompression_None);
      ASSERT_EQ(count, b.size());

      size_t size = dicom.GetSize() / count;
      size_t offset = 0;
      for (size_t j = 0; j < count; j++)
      {
        ASSERT_EQ(1u, b[j].GetChunksCount());
        ASSERT_EQ("dicom", b[j].GetChunkInstanceId(0));
        ASSERT_EQ(offset, b[j].GetChunkOffset(0));
        if (j + 1 != count)
          ASSERT_EQ(size, b[j].GetChunkSize(0));
        else
          ASSERT_EQ(dicom.GetSize() - (count - 1) * size, b[j].GetChunkSize(0));
        offset += b[j].GetChunkSize(0);
      }
    }
  }
}


TEST(DownloadArea, Basic)
{
  using namespace OrthancPlugins;
  
  std::string s1 = "Hello";
  std::string s2 = "Hello, World!";

  std::string md1, md2;
  Orthanc::Toolbox::ComputeMD5(md1, s1);
  Orthanc::Toolbox::ComputeMD5(md2, s2);
  
  std::vector<DicomInstanceInfo> instances;
  instances.push_back(DicomInstanceInfo("d1", s1.size(), md1));
  instances.push_back(DicomInstanceInfo("d2", s2.size(), md2));

  {
    DownloadArea area(instances);
    ASSERT_EQ(s1.size() + s2.size(), area.GetTotalSize());
    ASSERT_THROW(area.CheckMD5(), Orthanc::OrthancException);

    area.WriteInstance("d1", s1.c_str(), s1.size());
    area.WriteInstance("d2", s2.c_str(), s2.size());
  
    area.CheckMD5();
  }

  {
    DownloadArea area(instances);
    ASSERT_THROW(area.CheckMD5(), Orthanc::OrthancException);

    {
      TransferBucket b;
      b.AddChunk(instances[0] /*d1*/, 0, 2);
      area.WriteBucket(b, s1.c_str(), 2, BucketCompression_None);
    }

    {
      TransferBucket b;
      b.AddChunk(instances[0] /*d1*/, 2, 3);
      b.AddChunk(instances[1] /*d2*/, 0, 4);
      std::string s = s1.substr(2, 3) + s2.substr(0, 4);
      area.WriteBucket(b, s.c_str(), s.size(), BucketCompression_None);
    }

    {
      TransferBucket b;
      b.AddChunk(instances[1] /*d2*/, 4, 9);
      std::string s = s2.substr(4);
      std::string t;
      Orthanc::GzipCompressor compressor;
      compressor.Compress(t, s.c_str(), s.size());
      area.WriteBucket(b, t.c_str(), t.size(), BucketCompression_Gzip);
    }

    area.CheckMD5();
  }
}



int main(int argc, char **argv)
{
  ::testing::InitGoogleTest(&argc, argv);
  Orthanc::Logging::Initialize();
  Orthanc::Logging::EnableInfoLevel(true);
  Orthanc::Logging::EnableTraceLevel(true);

  int result = RUN_ALL_TESTS();

  Orthanc::Logging::Finalize();

  return result;
}
