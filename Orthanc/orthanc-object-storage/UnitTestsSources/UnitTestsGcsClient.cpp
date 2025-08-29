/**
 * Cloud storage plugins for Orthanc
 * Copyright (C) 2020-2023 Osimis S.A., Belgium
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


#include "gtest/gtest.h"
#include <threads.h>
#include <thread>
#include "google/cloud/storage/client.h"

namespace gcs = google::cloud::storage;
std::string credentialsPath = "/home/am/builds/orthanc/google-api-key.json"; // TODO: change to your file
std::string googleBucketName = "test-orthanc-storage-plugin";

// Note: this test actually crashes when run from gdb.  Same happens in the Orthanc plugins (only with GDB again !).
// Since this does not happen when run from command line (same for Orthanc plugins), we never investigated any further.
TEST(DISABLED_GcsClient, PruneDeadConnections)
{
  static google::cloud::StatusOr<gcs::Client> mainClient; // the client that is created at startup.  Each thread should copy it when it needs it. (from the doc: Instances of this class created via copy-construction or copy-assignment share the underlying pool of connections. Access to these copies via multiple threads is guaranteed to work. Two threads operating on the same instance of this class is not guaranteed to work.)

  // Use service account credentials from a JSON keyfile:
  auto creds = gcs::oauth2::CreateServiceAccountCredentialsFromJsonFilePath(credentialsPath);
  ASSERT_TRUE(creds);

  mainClient = gcs::Client(gcs::ClientOptions(*creds));

  ASSERT_TRUE(mainClient);

  std::string content = "MY TEST FILE CONTENT";
  std::string filePath = "0000_test_file.txt";

  {
    gcs::Client client(mainClient.value());

    auto writer = client.WriteObject(googleBucketName, filePath);
    writer.write(content.data(), content.size());
    writer.Close();

    ASSERT_TRUE(writer.metadata());
  }

  std::cout << "file written (1)" << std::endl;
  system("date && netstat -p | grep UnitTests");

  // on my system, I need 4 minutes before the connections go into "CLOSE_WAIT" state
  std::cout << "waiting 250s" << std::endl;
  std::this_thread::sleep_for(std::chrono::seconds(250));
  system("date && netstat -p | grep UnitTests");

  // and an extra 1 minute before the previous connection disappears
  std::cout << "waiting 60s" << std::endl;
  std::this_thread::sleep_for(std::chrono::seconds(60));
  system("date && netstat -p | grep UnitTests");

  {
    gcs::Client client(mainClient.value());

    auto writer = client.WriteObject(googleBucketName, filePath);
    writer.write(content.data(), content.size());
    writer.Close();

    ASSERT_TRUE(writer.metadata());
  }
}
