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


#include "../Sources/Toolbox/DicomStructureSet.h"

#include <EmbeddedResources.h>

#include <gtest/gtest.h>


TEST(StructureSet, ReadFromJson)
{
  OrthancStone::FullOrthancDataset dicom(
    Orthanc::EmbeddedResources::GetFileResourceBuffer(Orthanc::EmbeddedResources::RT_STRUCT_00),
    Orthanc::EmbeddedResources::GetFileResourceSize(Orthanc::EmbeddedResources::RT_STRUCT_00));

  OrthancStone::DicomStructureSet rtstruct(dicom);

  ASSERT_DOUBLE_EQ(0.0, rtstruct.GetEstimatedNormal() [0]);
  ASSERT_DOUBLE_EQ(0.0, rtstruct.GetEstimatedNormal() [1]);
  ASSERT_DOUBLE_EQ(1.0, rtstruct.GetEstimatedNormal() [2]);
  ASSERT_DOUBLE_EQ(3.0, rtstruct.GetEstimatedSliceThickness());

  // (0x3006, 0x0080) seq. size
  ASSERT_EQ(7u, rtstruct.GetStructuresCount());

  // (0x3006, 0x0080)[i]/(0x3006, 0x00a4)
  for (size_t i = 0; i < 5; ++i)
  {
    ASSERT_EQ("ORGAN", rtstruct.GetStructureInterpretation(i));
  }
  
  ASSERT_EQ("EXTERNAL", rtstruct.GetStructureInterpretation(5));
  ASSERT_EQ("PTV", rtstruct.GetStructureInterpretation(6));

  // (0x3006, 0x0020)[i]/(0x3006, 0x0026)
  ASSERT_EQ("LN300", rtstruct.GetStructureName(0));
  ASSERT_EQ("Cortical Bone", rtstruct.GetStructureName(1));
  ASSERT_EQ("Adipose", rtstruct.GetStructureName(2));
  ASSERT_EQ("CB2-50%", rtstruct.GetStructureName(3));
  ASSERT_EQ("Water", rtstruct.GetStructureName(4));
  ASSERT_EQ("External", rtstruct.GetStructureName(5));
  ASSERT_EQ("PTV", rtstruct.GetStructureName(6));

  // (0x3006, 0x0039)[i]/(0x3006, 0x002a)
  ASSERT_EQ(255, rtstruct.GetStructureColor(0).GetRed());
  ASSERT_EQ(0, rtstruct.GetStructureColor(0).GetGreen());
  ASSERT_EQ(0, rtstruct.GetStructureColor(0).GetBlue());

  ASSERT_EQ(0, rtstruct.GetStructureColor(1).GetRed());
  ASSERT_EQ(255, rtstruct.GetStructureColor(1).GetGreen());
  ASSERT_EQ(255, rtstruct.GetStructureColor(1).GetBlue());

  ASSERT_EQ(255, rtstruct.GetStructureColor(2).GetRed());
  ASSERT_EQ(0, rtstruct.GetStructureColor(2).GetGreen());
  ASSERT_EQ(255, rtstruct.GetStructureColor(2).GetBlue());

  ASSERT_EQ(0, rtstruct.GetStructureColor(3).GetRed());
  ASSERT_EQ(0, rtstruct.GetStructureColor(3).GetGreen());
  ASSERT_EQ(255, rtstruct.GetStructureColor(3).GetBlue());

  ASSERT_EQ(0, rtstruct.GetStructureColor(4).GetRed());
  ASSERT_EQ(128, rtstruct.GetStructureColor(4).GetGreen());
  ASSERT_EQ(255, rtstruct.GetStructureColor(4).GetBlue());

  ASSERT_EQ(0, rtstruct.GetStructureColor(5).GetRed());
  ASSERT_EQ(128, rtstruct.GetStructureColor(5).GetGreen());
  ASSERT_EQ(0, rtstruct.GetStructureColor(5).GetBlue());

  ASSERT_EQ(255, rtstruct.GetStructureColor(6).GetRed());
  ASSERT_EQ(0, rtstruct.GetStructureColor(6).GetGreen());
  ASSERT_EQ(255, rtstruct.GetStructureColor(6).GetBlue());
}
