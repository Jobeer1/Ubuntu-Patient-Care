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


#include <gtest/gtest.h>
#include <boost/lexical_cast.hpp>
#include <boost/algorithm/string/predicate.hpp>

#include "../Plugin/Configuration.h"
#include "../Plugin/DicomWebServers.h"

using namespace OrthancPlugins;

OrthancPluginContext* context_ = NULL;


TEST(DicomWebServers, Serialization)
{
  std::list<std::string> servers;
  DicomWebServers::GetInstance().ListServers(servers);
  ASSERT_TRUE(servers.empty());

  {
    std::string json;
    DicomWebServers::GetInstance().SerializeGlobalProperty(json);
    DicomWebServers::GetInstance().UnserializeGlobalProperty(json);
    ASSERT_TRUE(servers.empty());
  }

  Orthanc::WebServiceParameters p;
  p.SetUrl("http://hello/");
  p.SetCredentials("user", "world");
  DicomWebServers::GetInstance().SetServer("test", p);

  std::string json;
  DicomWebServers::GetInstance().SerializeGlobalProperty(json);

  p.SetUrl("http://nope/");
  p.ClearCredentials();
  DicomWebServers::GetInstance().SetServer("nope", p);

  DicomWebServers::GetInstance().ListServers(servers);
  ASSERT_EQ(2u, servers.size());
  
  DicomWebServers::GetInstance().UnserializeGlobalProperty(json);

  DicomWebServers::GetInstance().ListServers(servers);
  ASSERT_EQ(1u, servers.size());

  ASSERT_THROW(DicomWebServers::GetInstance().GetServer("nope"), Orthanc::OrthancException);
  p = DicomWebServers::GetInstance().GetServer("test");
  ASSERT_EQ("http://hello/", p.GetUrl());
  ASSERT_EQ("user", p.GetUsername());

  DicomWebServers::GetInstance().Clear();
  DicomWebServers::GetInstance().ListServers(servers);
  ASSERT_TRUE(servers.empty());
}


int main(int argc, char **argv)
{
  ::testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}
