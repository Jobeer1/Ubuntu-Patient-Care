/**
 * Stone of Orthanc
 * Copyright (C) 2012-2016 Sebastien Jodogne, Medical Physics
 * Department, University Hospital of Liege, Belgium
 * Copyright (C) 2017-2023 Osimis S.A., Belgium
 * Copyright (C) 2021-2025 Sebastien Jodogne, ICTEAM UCLouvain, Belgium
 *
 * This program is free software: you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public License
 * as published by the Free Software Foundation, either version 3 of
 * the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this program. If not, see
 * <http://www.gnu.org/licenses/>.
 **/


#include <gtest/gtest.h>

#include "../Sources/Toolbox/DicomInstanceParameters.h"
#include "../Sources/Loaders/DicomSource.h"

#include <OrthancException.h>


static void SetupUids(Orthanc::DicomMap& m)
{
  m.SetValue(Orthanc::DICOM_TAG_STUDY_INSTANCE_UID, "my_study", false);
  m.SetValue(Orthanc::DICOM_TAG_SERIES_INSTANCE_UID, "my_series", false);
  m.SetValue(Orthanc::DICOM_TAG_SOP_INSTANCE_UID, "my_sop", false);
}


TEST(DicomInstanceParameters, Basic)
{
  Orthanc::DicomMap m;
  SetupUids(m);

  std::unique_ptr<OrthancStone::DicomInstanceParameters> p;
  p.reset(OrthancStone::DicomInstanceParameters(m).Clone());

  ASSERT_TRUE(p->GetOrthancInstanceIdentifier().empty());
  ASSERT_EQ(3u, p->GetTags().GetSize());
  ASSERT_EQ("my_study", p->GetStudyInstanceUid());
  ASSERT_EQ("my_series", p->GetSeriesInstanceUid());
  ASSERT_EQ("my_sop", p->GetSopInstanceUid());
  ASSERT_EQ(OrthancStone::SopClassUid_Other, p->GetSopClassUid());
  ASSERT_EQ(1u, p->GetNumberOfFrames());
  ASSERT_EQ(0u, p->GetWidth());
  ASSERT_EQ(0u, p->GetHeight());
  ASSERT_FALSE(p->HasSliceThickness());
  ASSERT_THROW(p->GetSliceThickness(), Orthanc::OrthancException);
  ASSERT_FLOAT_EQ(1, p->GetPixelSpacingX());
  ASSERT_FLOAT_EQ(1, p->GetPixelSpacingY());
  ASSERT_FALSE(p->GetGeometry().IsValid());
  ASSERT_THROW(p->GetImageInformation(), Orthanc::OrthancException);
  ASSERT_FALSE(p->GetFrameGeometry(0).IsValid());
  ASSERT_THROW(p->IsColor(), Orthanc::OrthancException);  // Accesses DicomImageInformation
  ASSERT_FALSE(p->HasRescale());
  ASSERT_THROW(p->GetRescaleIntercept(), Orthanc::OrthancException);
  ASSERT_THROW(p->GetRescaleSlope(), Orthanc::OrthancException);
  ASSERT_EQ(0u, p->GetWindowingPresetsCount());
  ASSERT_THROW(p->GetWindowingPreset(0), Orthanc::OrthancException);

  OrthancStone::Windowing w = p->GetWindowingPresetsUnion();
  ASSERT_FLOAT_EQ(128.0f, w.GetCenter());
  ASSERT_FLOAT_EQ(256.0f, w.GetWidth());

  ASSERT_THROW(p->GetExpectedPixelFormat(), Orthanc::OrthancException);
  ASSERT_FALSE(p->HasIndexInSeries());
  ASSERT_THROW(p->GetIndexInSeries(), Orthanc::OrthancException);
  ASSERT_TRUE(p->GetDoseUnits().empty());
  ASSERT_DOUBLE_EQ(1.0, p->GetDoseGridScaling());
  ASSERT_DOUBLE_EQ(1.0, p->ApplyRescale(1.0));

  double s;
  ASSERT_FALSE(p->ComputeFrameOffsetsSpacing(s));
  ASSERT_TRUE(p->GetFrameOfReferenceUid().empty());
}


TEST(DicomInstanceParameters, Windowing)
{
  Orthanc::DicomMap m;
  SetupUids(m);
  m.SetValue(Orthanc::DICOM_TAG_WINDOW_CENTER, "10\\100\\1000", false);
  m.SetValue(Orthanc::DICOM_TAG_WINDOW_WIDTH, "50\\60\\70", false);

  OrthancStone::DicomInstanceParameters p(m);
  ASSERT_EQ(3u, p.GetWindowingPresetsCount());
  ASSERT_FLOAT_EQ(10, p.GetWindowingPreset(0).GetCenter());
  ASSERT_FLOAT_EQ(100, p.GetWindowingPreset(1).GetCenter());
  ASSERT_FLOAT_EQ(1000, p.GetWindowingPreset(2).GetCenter());
  ASSERT_FLOAT_EQ(50, p.GetWindowingPreset(0).GetWidth());
  ASSERT_FLOAT_EQ(60, p.GetWindowingPreset(1).GetWidth());
  ASSERT_FLOAT_EQ(70, p.GetWindowingPreset(2).GetWidth());

  const float a = 10.0f - 50.0f / 2.0f;
  const float b = 1000.0f + 70.0f / 2.0f;
  
  OrthancStone::Windowing w = p.GetWindowingPresetsUnion();
  ASSERT_FLOAT_EQ((a + b) / 2.0f, w.GetCenter());
  ASSERT_FLOAT_EQ(b - a, w.GetWidth());
}


TEST(DicomSource, Equality)
{
  {
    OrthancStone::DicomSource s1;

    {
      OrthancStone::DicomSource s2;
      ASSERT_TRUE(s1.IsSameSource(s2));

      s2.SetDicomDirSource();
      ASSERT_FALSE(s1.IsSameSource(s2));

      s2.SetDicomWebSource("toto");
      ASSERT_FALSE(s1.IsSameSource(s2));

      s2.SetDicomWebThroughOrthancSource("toto");
      ASSERT_FALSE(s1.IsSameSource(s2));

      s2.SetOrthancSource();
      ASSERT_TRUE(s1.IsSameSource(s2));
    }
  }

  {
    OrthancStone::DicomSource s1;

    {
      Orthanc::WebServiceParameters p;
      p.SetUrl("http://localhost:8042/");

      OrthancStone::DicomSource s2;
      s2.SetOrthancSource(p);
      ASSERT_TRUE(s1.IsSameSource(s2));

      p.SetCredentials("toto", "tutu");
      s2.SetOrthancSource(p);
      ASSERT_FALSE(s1.IsSameSource(s2));
      
      p.ClearCredentials();
      s2.SetOrthancSource(p);
      ASSERT_TRUE(s1.IsSameSource(s2));

      p.SetUrl("http://localhost:8043/");
      s2.SetOrthancSource(p);
      ASSERT_FALSE(s1.IsSameSource(s2));
    }
  }

  {
    OrthancStone::DicomSource s1;
    s1.SetDicomDirSource();

    {
      OrthancStone::DicomSource s2;
      ASSERT_FALSE(s1.IsSameSource(s2));

      s2.SetDicomDirSource();
      ASSERT_TRUE(s1.IsSameSource(s2));

      s2.SetDicomWebSource("toto");
      ASSERT_FALSE(s1.IsSameSource(s2));

      s2.SetDicomWebThroughOrthancSource("toto");
      ASSERT_FALSE(s1.IsSameSource(s2));
    }
  }

  {
    OrthancStone::DicomSource s1;
    s1.SetDicomWebSource("http");

    {
      OrthancStone::DicomSource s2;
      ASSERT_FALSE(s1.IsSameSource(s2));

      s2.SetDicomDirSource();
      ASSERT_FALSE(s1.IsSameSource(s2));

      s2.SetDicomWebSource("http");
      ASSERT_TRUE(s1.IsSameSource(s2));

      s2.SetDicomWebSource("http2");
      ASSERT_FALSE(s1.IsSameSource(s2));

      s2.SetDicomWebThroughOrthancSource("toto");
      ASSERT_FALSE(s1.IsSameSource(s2));
    }
  }

  {
    OrthancStone::DicomSource s1;
    s1.SetDicomWebThroughOrthancSource("server");

    {
      OrthancStone::DicomSource s2;
      ASSERT_FALSE(s1.IsSameSource(s2));

      s2.SetDicomDirSource();
      ASSERT_FALSE(s1.IsSameSource(s2));

      s2.SetDicomWebSource("http");
      ASSERT_FALSE(s1.IsSameSource(s2));

      s2.SetDicomWebThroughOrthancSource("server");
      ASSERT_TRUE(s1.IsSameSource(s2));

      s2.SetDicomWebThroughOrthancSource("server2");
      ASSERT_FALSE(s1.IsSameSource(s2));
    }
  }
}


TEST(DicomInstanceParameters, ReverseFrameOffsetsGrid)
{
  Orthanc::DicomMap m;
  SetupUids(m);

  m.SetValue(Orthanc::DICOM_TAG_IMAGE_POSITION_PATIENT, "-276.611\\-274.463\\100", false);
  m.SetValue(Orthanc::DICOM_TAG_IMAGE_ORIENTATION_PATIENT, "1\\0\\0\\0\\1\\0", false);
  m.SetValue(Orthanc::DICOM_TAG_NUMBER_OF_FRAMES, "126", false);
  m.SetValue(Orthanc::DICOM_TAG_GRID_FRAME_OFFSET_VECTOR, "0\\-2\\-4\\-6\\-8\\-10\\-12\\-14\\-16\\-18\\-20\\-22\\-24\\-26\\-28\\-30\\-32\\-34\\-36\\-38\\-40\\-42\\-44\\-46\\-48\\-50\\-52\\-54\\-56\\-58\\-60\\-62\\-64\\-66\\-68\\-70\\-72\\-74\\-76\\-78\\-80\\-82\\-84\\-86\\-88\\-90\\-92\\-94\\-96\\-98\\-100\\-102\\-104\\-106\\-108\\-110\\-112\\-114\\-116\\-118\\-120\\-122\\-124\\-126\\-128\\-130\\-132\\-134\\-136\\-138\\-140\\-142\\-144\\-146\\-148\\-150\\-152\\-154\\-156\\-158\\-160\\-162\\-164\\-166\\-168\\-170\\-172\\-174\\-176\\-178\\-180\\-182\\-184\\-186\\-188\\-190\\-192\\-194\\-196\\-198\\-200\\-202\\-204\\-206\\-208\\-210\\-212\\-214\\-216\\-218\\-220\\-222\\-224\\-226\\-228\\-230\\-232\\-234\\-236\\-238\\-240\\-242\\-244\\-246\\-248\\-250", false);

  std::unique_ptr<OrthancStone::DicomInstanceParameters> p;
  p.reset(OrthancStone::DicomInstanceParameters(m).Clone());

  ASSERT_FALSE(p->HasSliceThickness());
  ASSERT_THROW(p->GetSliceThickness(), Orthanc::OrthancException);

  double s;
  ASSERT_TRUE(p->ComputeFrameOffsetsSpacing(s));
  ASSERT_DOUBLE_EQ(s, 2.0);
  ASSERT_TRUE(p->IsReversedFrameOffsets());

  ASSERT_DOUBLE_EQ(1, p->GetMultiFrameGeometry().GetAxisX() [0]);
  ASSERT_DOUBLE_EQ(0, p->GetMultiFrameGeometry().GetAxisX() [1]);
  ASSERT_DOUBLE_EQ(0, p->GetMultiFrameGeometry().GetAxisX() [2]);

  ASSERT_DOUBLE_EQ(0, p->GetMultiFrameGeometry().GetAxisY() [0]);
  ASSERT_DOUBLE_EQ(1, p->GetMultiFrameGeometry().GetAxisY() [1]);
  ASSERT_DOUBLE_EQ(0, p->GetMultiFrameGeometry().GetAxisY() [2]);

  ASSERT_DOUBLE_EQ(0, p->GetMultiFrameGeometry().GetNormal() [0]);
  ASSERT_DOUBLE_EQ(0, p->GetMultiFrameGeometry().GetNormal() [1]);
  ASSERT_DOUBLE_EQ(1, p->GetMultiFrameGeometry().GetNormal() [2]);

  ASSERT_DOUBLE_EQ(-276.611, p->GetMultiFrameGeometry().GetOrigin() [0]);
  ASSERT_DOUBLE_EQ(-274.463, p->GetMultiFrameGeometry().GetOrigin() [1]);
  ASSERT_DOUBLE_EQ(100.0 - 250.0, p->GetMultiFrameGeometry().GetOrigin() [2]);
}


TEST(DicomInstanceParameters, StandardFrameOffsetsGrid)
{
  Orthanc::DicomMap m;
  SetupUids(m);

  m.SetValue(Orthanc::DICOM_TAG_SLICE_THICKNESS, "2", false);
  m.SetValue(Orthanc::DICOM_TAG_IMAGE_POSITION_PATIENT, "-205.2157\\-388.4679\\-120", false);
  m.SetValue(Orthanc::DICOM_TAG_IMAGE_ORIENTATION_PATIENT, "1\\0\\0\\0\\1\\0", false);
  m.SetValue(Orthanc::DICOM_TAG_NUMBER_OF_FRAMES, "155", false);
  m.SetValue(Orthanc::DICOM_TAG_GRID_FRAME_OFFSET_VECTOR, "0\\2\\4\\6\\8\\10\\12\\14\\16\\18\\20\\22\\24\\26\\28\\30\\32\\34\\36\\38\\40\\42\\44\\46\\48\\50\\52\\54\\56\\58\\60\\62\\64\\66\\68\\70\\72\\74\\76\\78\\80\\82\\84\\86\\88\\90\\92\\94\\96\\98\\100\\102\\104\\106\\108\\110\\112\\114\\116\\118\\120\\122\\124\\126\\128\\130\\132\\134\\136\\138\\140\\142\\144\\146\\148\\150\\152\\154\\156\\158\\160\\162\\164\\166\\168\\170\\172\\174\\176\\178\\180\\182\\184\\186\\188\\190\\192\\194\\196\\198\\200\\202\\204\\206\\208\\210\\212\\214\\216\\218\\220\\222\\224\\226\\228\\230\\232\\234\\236\\238\\240\\242\\244\\246\\248\\250\\252\\254\\256\\258\\260\\262\\264\\266\\268\\270\\272\\274\\276\\278\\280\\282\\284\\286\\288\\290\\292\\294\\296\\298\\300\\302\\304\\306\\308", false);

  std::unique_ptr<OrthancStone::DicomInstanceParameters> p;
  p.reset(OrthancStone::DicomInstanceParameters(m).Clone());

  ASSERT_TRUE(p->HasSliceThickness());
  ASSERT_DOUBLE_EQ(2.0, p->GetSliceThickness());

  double s;
  ASSERT_TRUE(p->ComputeFrameOffsetsSpacing(s));
  ASSERT_DOUBLE_EQ(s, 2.0);
  ASSERT_FALSE(p->IsReversedFrameOffsets());

  ASSERT_DOUBLE_EQ(1, p->GetMultiFrameGeometry().GetAxisX() [0]);
  ASSERT_DOUBLE_EQ(0, p->GetMultiFrameGeometry().GetAxisX() [1]);
  ASSERT_DOUBLE_EQ(0, p->GetMultiFrameGeometry().GetAxisX() [2]);

  ASSERT_DOUBLE_EQ(0, p->GetMultiFrameGeometry().GetAxisY() [0]);
  ASSERT_DOUBLE_EQ(1, p->GetMultiFrameGeometry().GetAxisY() [1]);
  ASSERT_DOUBLE_EQ(0, p->GetMultiFrameGeometry().GetAxisY() [2]);

  ASSERT_DOUBLE_EQ(0, p->GetMultiFrameGeometry().GetNormal() [0]);
  ASSERT_DOUBLE_EQ(0, p->GetMultiFrameGeometry().GetNormal() [1]);
  ASSERT_DOUBLE_EQ(1, p->GetMultiFrameGeometry().GetNormal() [2]);

  ASSERT_DOUBLE_EQ(-205.2157, p->GetMultiFrameGeometry().GetOrigin() [0]);
  ASSERT_DOUBLE_EQ(-388.4679, p->GetMultiFrameGeometry().GetOrigin() [1]);
  ASSERT_DOUBLE_EQ(-120.0, p->GetMultiFrameGeometry().GetOrigin() [2]);
}
