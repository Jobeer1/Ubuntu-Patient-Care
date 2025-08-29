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


#include <gtest/gtest.h>
#include <boost/lexical_cast.hpp>
#include <boost/algorithm/string/predicate.hpp>

#include "../Plugin/DefaultAuthorizationParser.h"
#include "../Plugin/AssociativeArray.h"
#include "../Plugin/AccessedResource.h"
#include "../Plugin/IAuthorizationService.h"
#include "../Plugin/MemoryCache.h"
#include "../Plugin/PermissionParser.h"
#include "../Plugin/ResourceHierarchyCache.h"

extern void AdjustToolsFindQueryLabels(Json::Value& query, const OrthancPlugins::IAuthorizationService::UserProfile& profile);

using namespace OrthancPlugins;

std::string instanceOrthancId = "44444444-44444444-44444444-44444444-44444444";
std::string seriesOrthancId   = "33333333-33333333-33333333-33333333-33333333";
std::string studyOrthancId    = "22222222-22222222-22222222-22222222-22222222";
std::string patientOrthancId  = "11111111-11111111-11111111-11111111-11111111";

std::string instanceDicomUid = "4.4";
std::string seriesDicomUid   = "3.3";
std::string studyDicomUid    = "2.2";
std::string patientDicomUid  = "PATIENT.1";

bool IsAccessing(const IAuthorizationParser::AccessedResources& accesses, AccessLevel level, const std::string& orthancId)
{
  for (IAuthorizationParser::AccessedResources::const_iterator it = accesses.begin(); it != accesses.end(); ++it)
  {
    if (it->GetLevel() == level && it->GetOrthancId() == orthancId)
    {
      return true;
    }
  }
  return false;
}

namespace OrthancPlugins
{
  // The namespace is necessary for friend classes to work
  // http://code.google.com/p/googletest/wiki/AdvancedGuide#Private_Class_Members

TEST(DefaultAuthorizationParser, Parse)
{
  MemoryCache::Factory factory(10);
  DefaultAuthorizationParser parser(factory, "/dicom-web/");
  ResourceHierarchyCache* cache = parser.GetResourceHierarchy();

  cache->AddOrthancDicomMapping(Orthanc::ResourceType_Instance, instanceOrthancId, instanceDicomUid);
  cache->AddOrthancDicomMapping(Orthanc::ResourceType_Series, seriesOrthancId, seriesDicomUid);
  cache->AddOrthancDicomMapping(Orthanc::ResourceType_Study, studyOrthancId, studyDicomUid);
  cache->AddOrthancDicomMapping(Orthanc::ResourceType_Patient, patientOrthancId, patientDicomUid);

  cache->AddParentLink(Orthanc::ResourceType_Instance, instanceOrthancId, seriesOrthancId);
  cache->AddParentLink(Orthanc::ResourceType_Series, seriesOrthancId, studyOrthancId);
  cache->AddParentLink(Orthanc::ResourceType_Study, studyOrthancId, patientOrthancId);

  cache->AddLabels(Orthanc::ResourceType_Series, seriesOrthancId, "series-label");
  cache->AddLabels(Orthanc::ResourceType_Study, studyOrthancId, "study-label");
  cache->AddLabels(Orthanc::ResourceType_Instance, instanceOrthancId, "instance-label");
  cache->AddLabels(Orthanc::ResourceType_Patient, patientOrthancId, "patient-label");

  IAuthorizationParser::AccessedResources accesses;
  AssociativeArray noGetArguments(0, NULL, NULL, false);

  accesses.clear();
  parser.Parse(accesses, "/studies/22222222-22222222-22222222-22222222-22222222/", noGetArguments.GetMap());
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Study, studyOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Patient, patientOrthancId));

  accesses.clear();
  parser.Parse(accesses, "/studies/22222222-22222222-22222222-22222222-22222222/instances", noGetArguments.GetMap());
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Study, studyOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Patient, patientOrthancId));

  accesses.clear();
  parser.Parse(accesses, "/studies/22222222-22222222-22222222-22222222-22222222/archive", noGetArguments.GetMap());
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Study, studyOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Patient, patientOrthancId));

  accesses.clear();
  parser.Parse(accesses, "/studies/22222222-22222222-22222222-22222222-22222222/ohif-dicom.json", noGetArguments.GetMap());
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Study, studyOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Patient, patientOrthancId));

  accesses.clear();
  parser.Parse(accesses, "/osimis-viewer/studies/22222222-22222222-22222222-22222222-22222222/archive", noGetArguments.GetMap());
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Study, studyOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Patient, patientOrthancId));

  accesses.clear();
  parser.Parse(accesses, "/series/33333333-33333333-33333333-33333333-33333333/", noGetArguments.GetMap());
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Series, seriesOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Study, studyOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Patient, patientOrthancId));

  accesses.clear();
  parser.Parse(accesses, "/series/33333333-33333333-33333333-33333333-33333333/media", noGetArguments.GetMap());
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Series, seriesOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Study, studyOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Patient, patientOrthancId));

  accesses.clear();
  parser.Parse(accesses, "/series/33333333-33333333-33333333-33333333-33333333/modify", noGetArguments.GetMap());
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Series, seriesOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Study, studyOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Patient, patientOrthancId));

  accesses.clear();
  parser.Parse(accesses, "/web-viewer/series/33333333-33333333-33333333-33333333-33333333", noGetArguments.GetMap());
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Series, seriesOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Study, studyOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Patient, patientOrthancId));

  accesses.clear();
  parser.Parse(accesses, "/osimis-viewer/series/33333333-33333333-33333333-33333333-33333333", noGetArguments.GetMap());
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Series, seriesOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Study, studyOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Patient, patientOrthancId));

  accesses.clear();
  parser.Parse(accesses, "/instances/44444444-44444444-44444444-44444444-44444444/file", noGetArguments.GetMap());
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Instance, instanceOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Series, seriesOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Study, studyOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Patient, patientOrthancId));

  accesses.clear();
  parser.Parse(accesses, "/instances/44444444-44444444-44444444-44444444-44444444/preview", noGetArguments.GetMap());
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Instance, instanceOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Series, seriesOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Study, studyOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Patient, patientOrthancId));

  accesses.clear();
  parser.Parse(accesses, "/web-viewer/instances/jpeg95-44444444-44444444-44444444-44444444-44444444_0", noGetArguments.GetMap());
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Instance, instanceOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Series, seriesOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Study, studyOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Patient, patientOrthancId));

  accesses.clear();
  parser.Parse(accesses, "/osimis-viewer/images/44444444-44444444-44444444-44444444-44444444/0/high-quality", noGetArguments.GetMap());
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Instance, instanceOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Series, seriesOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Study, studyOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Patient, patientOrthancId));

  accesses.clear();
  parser.Parse(accesses, "/system", noGetArguments.GetMap());
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_System, "/system"));

  accesses.clear();
  parser.Parse(accesses, "/instances", noGetArguments.GetMap());
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_System, "/instances"));

  accesses.clear();
  parser.Parse(accesses, "/series", noGetArguments.GetMap());
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_System, "/series"));

  accesses.clear();
  parser.Parse(accesses, "/studies", noGetArguments.GetMap());
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_System, "/studies"));

  accesses.clear();
  parser.Parse(accesses, "/patients", noGetArguments.GetMap());
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_System, "/patients"));


  ///////////////////////// dicom-web
  accesses.clear();
  parser.Parse(accesses, "/dicom-web/studies/2.2", noGetArguments.GetMap());
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Study, studyOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Patient, patientOrthancId));

  accesses.clear();
  parser.Parse(accesses, "/dicom-web/studies/2.2/instances", noGetArguments.GetMap());
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Study, studyOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Patient, patientOrthancId));

  accesses.clear();
  parser.Parse(accesses, "/dicom-web/studies/2.2/series/3.3", noGetArguments.GetMap());
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Series, seriesOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Study, studyOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Patient, patientOrthancId));

  accesses.clear();
  parser.Parse(accesses, "/dicom-web/studies/2.2/series/3.3/instances", noGetArguments.GetMap());
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Series, seriesOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Study, studyOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Patient, patientOrthancId));

  accesses.clear();
  parser.Parse(accesses, "/dicom-web/studies/2.2/series/3.3/rendered", noGetArguments.GetMap());
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Series, seriesOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Study, studyOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Patient, patientOrthancId));

  accesses.clear();
  parser.Parse(accesses, "/dicom-web/studies/2.2/series/3.3/metadata", noGetArguments.GetMap());
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Series, seriesOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Study, studyOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Patient, patientOrthancId));

  accesses.clear();
  parser.Parse(accesses, "/dicom-web/studies/2.2/series/3.3/instances/4.4", noGetArguments.GetMap());
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Instance, instanceOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Series, seriesOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Study, studyOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Patient, patientOrthancId));

  accesses.clear();
  parser.Parse(accesses, "/dicom-web/studies/2.2/series/3.3/instances/4.4/metadata", noGetArguments.GetMap());
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Instance, instanceOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Series, seriesOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Study, studyOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Patient, patientOrthancId));

  accesses.clear();
  parser.Parse(accesses, "/dicom-web/studies/2.2/series/3.3/instances/4.4/frames/0", noGetArguments.GetMap());
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Instance, instanceOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Series, seriesOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Study, studyOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Patient, patientOrthancId));

  accesses.clear();
  parser.Parse(accesses, "/dicom-web/studies/2.2/series/3.3/instances/4.4/frames/0/rendered", noGetArguments.GetMap());
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Instance, instanceOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Series, seriesOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Study, studyOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Patient, patientOrthancId));

  accesses.clear();
  parser.Parse(accesses, "/dicom-web/studies/2.2/series/3.3/instances/4.4/bulk/7fe00010", noGetArguments.GetMap());
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Instance, instanceOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Series, seriesOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Study, studyOrthancId));
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Patient, patientOrthancId));

  {
    accesses.clear();
    const char* getKeys[] = {"0020000D"};
    const char* getValues[] = {"2.2"};
    AssociativeArray getArguments(1, getKeys, getValues, false);
    parser.Parse(accesses, "/dicom-web/studies", getArguments.GetMap());
    ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Study, studyOrthancId));
    ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Patient, patientOrthancId));
  }
  {
    accesses.clear();
    const char* getKeys[] = {"0020000D", "0020000E"};
    const char* getValues[] = {"2.2", "3.3"};
    AssociativeArray getArguments(2, getKeys, getValues, false);
    parser.Parse(accesses, "/dicom-web/series", getArguments.GetMap());
    ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Series, seriesOrthancId));
    ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Study, studyOrthancId));
    ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Patient, patientOrthancId));
  }
  {
    accesses.clear();
    const char* getKeys[] = {"0020000D", "00080018", "0020000E"};
    const char* getValues[] = {"2.2", "4.4", "3.3", };
    AssociativeArray getArguments(3, getKeys, getValues, false);
    parser.Parse(accesses, "/dicom-web/studies", getArguments.GetMap());
    ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Instance, instanceOrthancId));
    ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Series, seriesOrthancId));
    ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Study, studyOrthancId));
    ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Patient, patientOrthancId));
  }
  {
    accesses.clear();
    const char* getKeys[] = {"StudyInstanceUID", "SOPInstanceUID", "SeriesInstanceUID"};
    const char* getValues[] = {"2.2", "4.4", "3.3", };
    AssociativeArray getArguments(3, getKeys, getValues, false);
    parser.Parse(accesses, "/dicom-web/studies", getArguments.GetMap());
    ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Instance, instanceOrthancId));
    ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Series, seriesOrthancId));
    ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Study, studyOrthancId));
    ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Patient, patientOrthancId));
  }
  {
    accesses.clear();
    const char* getKeys[] = {"00100020"};
    const char* getValues[] = {"PATIENT.1"};
    AssociativeArray getArguments(1, getKeys, getValues, false);
    parser.Parse(accesses, "/dicom-web/studies", getArguments.GetMap());
    ASSERT_TRUE(IsAccessing(accesses, AccessLevel_Patient, patientOrthancId));
  }

  { // qido with no arguments = search all => system resource
    accesses.clear();
    parser.Parse(accesses, "/dicom-web/studies", noGetArguments.GetMap());
    ASSERT_TRUE(IsAccessing(accesses, AccessLevel_System, "/dicom-web/studies"));
  }

  accesses.clear();
  parser.Parse(accesses, "/dicom-web/servers", noGetArguments.GetMap());
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_System, "/dicom-web/servers"));

  accesses.clear();
  parser.Parse(accesses, "/dicom-web/info", noGetArguments.GetMap());
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_System, "/dicom-web/info"));

  accesses.clear();
  parser.Parse(accesses, "/dicom-web/servers/test/qido", noGetArguments.GetMap());
  ASSERT_TRUE(IsAccessing(accesses, AccessLevel_System, "/dicom-web/servers/test/qido"));

}

bool IsInJsonArray(const char* needle, const Json::Value& array)
{
  for (Json::ArrayIndex i = 0; i < array.size(); ++i)
  {
    if (array[i].asString() == needle)
    {
      return true;
    }
  }
  return false;
}

TEST(ToolsFindLabels, AdjustQueryForUserWithoutAuthorizedLabels)
{
  // user who has access no authorized labels
  OrthancPlugins::IAuthorizationService::UserProfile profile;

  { // any call to tools/find for such a user should fail since it does not have access to anything
    Json::Value query;
    query["Query"] = Json::objectValue;
    query["Query"]["PatientID"] = "*";

    ASSERT_THROW(AdjustToolsFindQueryLabels(query, profile), Orthanc::OrthancException);
  }

}



TEST(ToolsFindLabels, AdjustQueryForUserWithoutRestrictions)
{
  // user who has access to all labels
  OrthancPlugins::IAuthorizationService::UserProfile profile;
  profile.authorizedLabels.insert("*");

  { // no labels filtering before transformation -> no labels filtering after 
    Json::Value query;
    query["Query"] = Json::objectValue;
    query["Query"]["PatientID"] = "*";

    AdjustToolsFindQueryLabels(query, profile);

    ASSERT_FALSE(query.isMember("Labels"));
    ASSERT_FALSE(query.isMember("LabelsConstraint"));
  }

  { // missing LabelsConstraint -> throw
    Json::Value query;
    query["Query"] = Json::objectValue;
    query["Query"]["PatientID"] = "*";
    query["Labels"] = Json::arrayValue;
    query["Labels"].append("a");

    ASSERT_THROW(AdjustToolsFindQueryLabels(query, profile), Orthanc::OrthancException);
  }

  { // simple 'All' label constraint is not modified since user has access to all labels
    Json::Value query;
    query["Query"] = Json::objectValue;
    query["Query"]["PatientID"] = "*";
    query["Labels"] = Json::arrayValue;
    query["Labels"].append("a");
    query["Labels"].append("b");
    query["LabelsConstraint"] = "All";

    AdjustToolsFindQueryLabels(query, profile);

    ASSERT_EQ(2u, query["Labels"].size());
    ASSERT_TRUE(IsInJsonArray("a", query["Labels"]));
    ASSERT_TRUE(IsInJsonArray("b", query["Labels"]));
    ASSERT_EQ("All", query["LabelsConstraint"].asString());
  }

  { // simple 'Any' label constraint is not modified since user has access to all labels
    Json::Value query;
    query["Query"] = Json::objectValue;
    query["Query"]["PatientID"] = "*";
    query["Labels"] = Json::arrayValue;
    query["Labels"].append("a");
    query["Labels"].append("b");
    query["LabelsConstraint"] = "Any";

    AdjustToolsFindQueryLabels(query, profile);

    ASSERT_EQ(2u, query["Labels"].size());
    ASSERT_TRUE(IsInJsonArray("a", query["Labels"]));
    ASSERT_TRUE(IsInJsonArray("b", query["Labels"]));
    ASSERT_EQ("Any", query["LabelsConstraint"].asString());
  }

  { // simple 'None' label constraint is not modified since user has access to all labels
    Json::Value query;
    query["Query"] = Json::objectValue;
    query["Query"]["PatientID"] = "*";
    query["Labels"] = Json::arrayValue;
    query["Labels"].append("a");
    query["Labels"].append("b");
    query["LabelsConstraint"] = "None";

    AdjustToolsFindQueryLabels(query, profile);

    ASSERT_EQ(2u, query["Labels"].size());
    ASSERT_TRUE(IsInJsonArray("a", query["Labels"]));
    ASSERT_TRUE(IsInJsonArray("b", query["Labels"]));
    ASSERT_EQ("None", query["LabelsConstraint"].asString());
  }

}


TEST(ToolsFindLabels, AdjustQueryForUserWithAuthorizedLabelsRestrictions)
{
  // user who has access only to "b" and "c"
  OrthancPlugins::IAuthorizationService::UserProfile profile;
  profile.authorizedLabels.insert("b");
  profile.authorizedLabels.insert("c");

  { // no labels before transformation -> "b", "c" label after 
    Json::Value query;
    query["Query"] = Json::objectValue;
    query["Query"]["PatientID"] = "*";

    AdjustToolsFindQueryLabels(query, profile);

    ASSERT_EQ(2u, query["Labels"].size());
    ASSERT_TRUE(IsInJsonArray("b", query["Labels"]));
    ASSERT_TRUE(IsInJsonArray("c", query["Labels"]));
    ASSERT_EQ("Any", query["LabelsConstraint"].asString());
  }

  { // missing LabelsConstraint -> throw
    Json::Value query;
    query["Query"] = Json::objectValue;
    query["Query"]["PatientID"] = "*";
    query["Labels"] = Json::arrayValue;
    query["Labels"].append("a");

    ASSERT_THROW(AdjustToolsFindQueryLabels(query, profile), Orthanc::OrthancException);
  }

  { // 'All' label constraint is not modified if it contains the labels that are accessible to the user
    Json::Value query;
    query["Query"] = Json::objectValue;
    query["Query"]["PatientID"] = "*";
    query["Labels"] = Json::arrayValue;
    query["Labels"].append("b");
    query["Labels"].append("c");
    query["LabelsConstraint"] = "All";

    AdjustToolsFindQueryLabels(query, profile);

    ASSERT_EQ(2u, query["Labels"].size());
    ASSERT_TRUE(IsInJsonArray("b", query["Labels"]));
    ASSERT_TRUE(IsInJsonArray("c", query["Labels"]));
    ASSERT_EQ("All", query["LabelsConstraint"].asString());
  }

  { // 'All' label constraint is not modified if it contains a subset of the labels that are accessible to the user
    Json::Value query;
    query["Query"] = Json::objectValue;
    query["Query"]["PatientID"] = "*";
    query["Labels"] = Json::arrayValue;
    query["Labels"].append("b");
    query["LabelsConstraint"] = "All";

    AdjustToolsFindQueryLabels(query, profile);

    ASSERT_EQ(1u, query["Labels"].size());
    ASSERT_TRUE(IsInJsonArray("b", query["Labels"]));
    ASSERT_EQ("All", query["LabelsConstraint"].asString());
  }

  { // 'All' label constraint becomes invalid if it contains a label that is not accessible to the user
    Json::Value query;
    query["Query"] = Json::objectValue;
    query["Query"]["PatientID"] = "*";
    query["Labels"] = Json::arrayValue;
    query["Labels"].append("a");
    query["Labels"].append("b");
    query["LabelsConstraint"] = "All";

    ASSERT_THROW(AdjustToolsFindQueryLabels(query, profile), Orthanc::OrthancException);
  }

  { // 'Any' label constraint is not modified if it contains the labels that are accessible to the user
    Json::Value query;
    query["Query"] = Json::objectValue;
    query["Query"]["PatientID"] = "*";
    query["Labels"] = Json::arrayValue;
    query["Labels"].append("b");
    query["Labels"].append("c");
    query["LabelsConstraint"] = "Any";

    AdjustToolsFindQueryLabels(query, profile);

    ASSERT_EQ(2u, query["Labels"].size());
    ASSERT_TRUE(IsInJsonArray("b", query["Labels"]));
    ASSERT_TRUE(IsInJsonArray("c", query["Labels"]));
    ASSERT_EQ("Any", query["LabelsConstraint"].asString());
  }

  { // 'Any' label constraint is not modified if it contains a subset of the labels that are accessible to the user
    Json::Value query;
    query["Query"] = Json::objectValue;
    query["Query"]["PatientID"] = "*";
    query["Labels"] = Json::arrayValue;
    query["Labels"].append("b");
    query["LabelsConstraint"] = "Any";

    AdjustToolsFindQueryLabels(query, profile);

    ASSERT_EQ(1u, query["Labels"].size());
    ASSERT_TRUE(IsInJsonArray("b", query["Labels"]));
    ASSERT_EQ("Any", query["LabelsConstraint"].asString());
  }

  { // 'Any' label constraint only contains the intersection of the initial requested labels and the ones authorized to the user
    Json::Value query;
    query["Query"] = Json::objectValue;
    query["Query"]["PatientID"] = "*";
    query["Labels"] = Json::arrayValue;
    query["Labels"].append("a");
    query["Labels"].append("b");
    query["LabelsConstraint"] = "Any";

    AdjustToolsFindQueryLabels(query, profile);

    ASSERT_EQ(1u, query["Labels"].size());
    ASSERT_TRUE(IsInJsonArray("b", query["Labels"]));
    ASSERT_EQ("Any", query["LabelsConstraint"].asString());
  }

  { // 'Any' label constraint can not be modified if the initial requested labels have nothing in common with the authorized labels
    Json::Value query;
    query["Query"] = Json::objectValue;
    query["Query"]["PatientID"] = "*";
    query["Labels"] = Json::arrayValue;
    query["Labels"].append("d");
    query["Labels"].append("e");
    query["LabelsConstraint"] = "Any";

    ASSERT_THROW(AdjustToolsFindQueryLabels(query, profile), Orthanc::OrthancException);
  }

  { // 'None' label constraint can not be modified since the user has only 'authorized_labels' -> throw
    Json::Value query;
    query["Query"] = Json::objectValue;
    query["Query"]["PatientID"] = "*";
    query["Labels"] = Json::arrayValue;
    query["Labels"].append("b");
    query["Labels"].append("c");
    query["LabelsConstraint"] = "None";

    ASSERT_THROW(AdjustToolsFindQueryLabels(query, profile), Orthanc::OrthancException);
  }
}

// TEST(ToolsFindLabels, AdjustQueryForUserWithForbiddenLabelsRestrictions)
// {
//   // user who has forbidden access to "b" and "c"
//   OrthancPlugins::IAuthorizationService::UserProfile profile;
//   profile.forbiddenLabels.insert("b");
//   profile.forbiddenLabels.insert("c");

//   { // no labels before transformation -> "b", "c" label after (with a 'None' constraint)
//     Json::Value query;
//     query["Query"] = Json::objectValue;
//     query["Query"]["PatientID"] = "*";

//     AdjustToolsFindQueryLabels(query, profile);

//     ASSERT_EQ(2u, query["Labels"].size());
//     ASSERT_TRUE(IsInJsonArray("b", query["Labels"]));
//     ASSERT_TRUE(IsInJsonArray("c", query["Labels"]));
//     ASSERT_EQ("None", query["LabelsConstraint"].asString());
//   }

//   { // missing LabelsConstraint -> throw
//     Json::Value query;
//     query["Query"] = Json::objectValue;
//     query["Query"]["PatientID"] = "*";
//     query["Labels"] = Json::arrayValue;
//     query["Labels"].append("a");

//     ASSERT_THROW(AdjustToolsFindQueryLabels(query, profile), Orthanc::OrthancException);
//   }

//   { // 'All' label constraint can not be modified for user with forbidden labels
//     Json::Value query;
//     query["Query"] = Json::objectValue;
//     query["Query"]["PatientID"] = "*";
//     query["Labels"] = Json::arrayValue;
//     query["Labels"].append("b");
//     query["Labels"].append("c");
//     query["LabelsConstraint"] = "All";

//     ASSERT_THROW(AdjustToolsFindQueryLabels(query, profile), Orthanc::OrthancException);
//   }

//   { // 'Any' label constraint can not be modified for user with forbidden labels
//     Json::Value query;
//     query["Query"] = Json::objectValue;
//     query["Query"]["PatientID"] = "*";
//     query["Labels"] = Json::arrayValue;
//     query["Labels"].append("b");
//     query["Labels"].append("c");
//     query["LabelsConstraint"] = "Any";

//     ASSERT_THROW(AdjustToolsFindQueryLabels(query, profile), Orthanc::OrthancException);
//   }

//   { // 'Any' label constraint can not be modified for user with forbidden labels
//     Json::Value query;
//     query["Query"] = Json::objectValue;
//     query["Query"]["PatientID"] = "*";
//     query["Labels"] = Json::arrayValue;
//     query["Labels"].append("a");
//     query["LabelsConstraint"] = "Any";

//     ASSERT_THROW(AdjustToolsFindQueryLabels(query, profile), Orthanc::OrthancException);
//   }


//   { // 'None' label constraint are modified to always contain at least all forbidden_labels of the user
//     Json::Value query;
//     query["Query"] = Json::objectValue;
//     query["Query"]["PatientID"] = "*";
//     query["Labels"] = Json::arrayValue;
//     query["Labels"].append("b");
//     query["LabelsConstraint"] = "None";

//     AdjustToolsFindQueryLabels(query, profile);
//     ASSERT_EQ(2u, query["Labels"].size());
//     ASSERT_TRUE(IsInJsonArray("b", query["Labels"]));
//     ASSERT_TRUE(IsInJsonArray("c", query["Labels"]));
//     ASSERT_EQ("None", query["LabelsConstraint"].asString());
//   }

//   { // 'None' label constraint are modified to always contain at least all forbidden_labels of the user
//     Json::Value query;
//     query["Query"] = Json::objectValue;
//     query["Query"]["PatientID"] = "*";
//     query["Labels"] = Json::arrayValue;
//     query["Labels"].append("d");
//     query["LabelsConstraint"] = "None";

//     AdjustToolsFindQueryLabels(query, profile);
//     ASSERT_EQ(3u, query["Labels"].size());
//     ASSERT_TRUE(IsInJsonArray("b", query["Labels"]));
//     ASSERT_TRUE(IsInJsonArray("c", query["Labels"]));
//     ASSERT_TRUE(IsInJsonArray("d", query["Labels"]));
//     ASSERT_EQ("None", query["LabelsConstraint"].asString());
//   }
// }

}

int main(int argc, char **argv)
{
  ::testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}
