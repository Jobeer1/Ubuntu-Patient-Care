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


// Necessary for "std::max()" to work on Visual Studio
#ifndef NOMINMAX
#define NOMINMAX
#endif

#include "DicomStructuredReport.h"

#include "../Scene2D/ScenePoint2D.h"
#include "../Fonts/GlyphBitmapAlphabet.h"
#include "BitmapLayout.h"
#include "StoneToolbox.h"

#include <ChunkedBuffer.h>
#include <OrthancException.h>
#include <SerializationToolbox.h>

#include <dcmtk/dcmdata/dcdeftag.h>
#include <dcmtk/dcmdata/dcsequen.h>
#include <dcmtk/dcmdata/dcfilefo.h>

#include <algorithm>  // For std::max()


static std::string FormatTag(const DcmTagKey& key)
{
  OFString s = key.toString();
  return std::string(s.c_str());
}


static std::string GetStringValue(DcmItem& dataset,
                                  const DcmTagKey& key)
{
  const char* value = NULL;
  if (dataset.findAndGetString(key, value).good() &&
      value != NULL)
  {
    return value;
  }
  else
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat,
                                    "Missing tag in DICOM-SR: " + FormatTag(key));
  }
}


static DcmSequenceOfItems& GetSequenceValue(DcmItem& dataset,
                                            const DcmTagKey& key)
{
  DcmSequenceOfItems* sequence = NULL;
  if (dataset.findAndGetSequence(key, sequence).good() &&
      sequence != NULL)
  {
    return *sequence;
  }
  else
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat,
                                    "Missing sequence in DICOM-SR: " + FormatTag(key));
  }
}


static void CheckStringValue(DcmItem& dataset,
                             const DcmTagKey& key,
                             const std::string& expected)
{
  if (GetStringValue(dataset, key) != expected)
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
  }
}


static bool IsDicomTemplate(DcmItem& dataset,
                            const std::string& tid)
{
  DcmSequenceOfItems& sequence = GetSequenceValue(dataset, DCM_ContentTemplateSequence);

  return (sequence.card() == 1 &&
          GetStringValue(*sequence.getItem(0), DCM_MappingResource) == "DCMR" &&
          GetStringValue(*sequence.getItem(0), DCM_TemplateIdentifier) == tid);
}


static bool IsValidConcept(DcmItem& dataset,
                           const DcmTagKey& key,
                           const std::string& scheme,
                           const std::string& concept)
{
  DcmSequenceOfItems& sequence = GetSequenceValue(dataset, key);

  return (sequence.card() == 1 &&
          GetStringValue(*sequence.getItem(0), DCM_CodingSchemeDesignator) == scheme &&
          GetStringValue(*sequence.getItem(0), DCM_CodeValue) == concept);
}


static bool IsDicomConcept(DcmItem& dataset,
                           const std::string& concept)
{
  return IsValidConcept(dataset, DCM_ConceptNameCodeSequence, "DCM", concept);
}


namespace OrthancStone
{
  void DicomStructuredReport::Structure::Copy(const Structure& other)
  {
    if (other.HasFrameNumber())
    {
      SetFrameNumber(other.GetFrameNumber());
    }

    if (other.HasProbabilityOfCancer())
    {
      SetProbabilityOfCancer(other.GetProbabilityOfCancer());
    }
  }


  DicomStructuredReport::Structure::Structure(const std::string& sopInstanceUid) :
    sopInstanceUid_(sopInstanceUid),
    hasFrameNumber_(false),
    frameNumber_(0),         // dummy initialization
    hasProbabilityOfCancer_(false),
    probabilityOfCancer_(0)  // dummy initialization
  {
  }


  void DicomStructuredReport::Structure::SetFrameNumber(unsigned int frame)
  {
    hasFrameNumber_ = true;
    frameNumber_ = frame;
  }


  void DicomStructuredReport::Structure::SetProbabilityOfCancer(float probability)
  {
    if (probability < 0 ||
        probability > 100)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
    else
    {
      hasProbabilityOfCancer_ = true;
      probabilityOfCancer_ = probability;
    }
  }


  unsigned int DicomStructuredReport::Structure::GetFrameNumber() const
  {
    if (hasFrameNumber_)
    {
      return frameNumber_;
    }
    else
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
    }
  }

  float DicomStructuredReport::Structure::GetProbabilityOfCancer() const
  {
    if (hasProbabilityOfCancer_)
    {
      return probabilityOfCancer_;
    }
    else
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
    }
  }


  DicomStructuredReport::Point::Point(const std::string& sopInstanceUid,
                                      double x,
                                      double y) :
    Structure(sopInstanceUid),
    point_(x, y)
  {
  }


  DicomStructuredReport::Structure* DicomStructuredReport::Point::Clone() const
  {
    std::unique_ptr<Point> cloned(new Point(GetSopInstanceUid(), point_.GetX(), point_.GetY()));
    cloned->Copy(*this);
    return cloned.release();
  }


  DicomStructuredReport::Polyline::Polyline(const std::string& sopInstanceUid,
                                            const float* points,
                                            unsigned long pointsCount) :
    Structure(sopInstanceUid)
  {
    if (pointsCount % 2 != 0)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
    }

    points_.reserve(pointsCount / 2);

    for (unsigned long i = 0; i < pointsCount; i += 2)
    {
      points_.push_back(ScenePoint2D(points[i], points[i + 1]));
    }
  }


  DicomStructuredReport::Polyline::Polyline(const std::string& sopInstanceUid,
                                            const std::vector<ScenePoint2D>& points) :
    Structure(sopInstanceUid),
    points_(points)
  {
  }


  DicomStructuredReport::Structure* DicomStructuredReport::Polyline::Clone() const
  {
    std::unique_ptr<Polyline> cloned(new Polyline(GetSopInstanceUid(), points_));
    cloned->Copy(*this);
    return cloned.release();
  }


  const ScenePoint2D& DicomStructuredReport::Polyline::GetPoint(size_t i) const
  {
    if (i >= points_.size())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
    else
    {
      return points_[i];
    }
  }


  void DicomStructuredReport::AddStructure(const std::string& sopInstanceUid,
                                           DcmItem& group,
                                           bool hasFrameNumber,
                                           unsigned int frameNumber,
                                           bool hasProbabilityOfCancer,
                                           float probabilityOfCancer)
  {
    const std::string graphicType = GetStringValue(group, DCM_GraphicType);

    const Float32* coords = NULL;
    unsigned long coordsCount = 0;
    if (!group.findAndGetFloat32Array(DCM_GraphicData, coords, &coordsCount).good() ||
        (coordsCount != 0 && coords == NULL))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat,
                                      "Cannot read coordinates for region in DICOM-SR");
    }

    std::unique_ptr<Structure> structure;

    if (graphicType == "POINT")
    {
      if (coordsCount != 2)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
      }
      else
      {
        structure.reset(new Point(sopInstanceUid, coords[0], coords[1]));
      }
    }
    else if (graphicType == "POLYLINE")
    {
      structure.reset(new Polyline(sopInstanceUid, coords, coordsCount));
    }
    else
    {
      return;  // Unsupported graphic type
    }

    assert(structure.get() != NULL);

    if (hasFrameNumber)
    {
      structure->SetFrameNumber(frameNumber);
    }

    if (hasProbabilityOfCancer)
    {
      structure->SetProbabilityOfCancer(probabilityOfCancer);
    }

    structures_.push_back(structure.release());
  }


  void DicomStructuredReport::ReadTID1500(Orthanc::ParsedDicomFile& dicom)
  {
    DcmDataset& dataset = *dicom.GetDcmtkObject().getDataset();

    CheckStringValue(dataset, DCM_SOPClassUID, "1.2.840.10008.5.1.4.1.1.88.33");  // Comprehensive SR IOD
    CheckStringValue(dataset, DCM_ValueType, "CONTAINER");

    DcmSequenceOfItems& sequence = GetSequenceValue(dataset, DCM_CurrentRequestedProcedureEvidenceSequence);

    std::list<std::string> tmp;

    for (unsigned long i = 0; i < sequence.card(); i++)
    {
      std::string studyInstanceUid = GetStringValue(*sequence.getItem(i), DCM_StudyInstanceUID);

      DcmSequenceOfItems* referencedSeries = NULL;
      if (!sequence.getItem(i)->findAndGetSequence(DCM_ReferencedSeriesSequence, referencedSeries).good() ||
          referencedSeries == NULL)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
      }

      for (unsigned long j = 0; j < referencedSeries->card(); j++)
      {
        std::string seriesInstanceUid = GetStringValue(*referencedSeries->getItem(j), DCM_SeriesInstanceUID);

        DcmSequenceOfItems* referencedInstances = NULL;
        if (!referencedSeries->getItem(j)->findAndGetSequence(DCM_ReferencedSOPSequence, referencedInstances).good() ||
            referencedInstances == NULL)
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
        }

        for (unsigned int k = 0; k < referencedInstances->card(); k++)
        {
          std::string sopClassUid = GetStringValue(*referencedInstances->getItem(k), DCM_ReferencedSOPClassUID);
          std::string sopInstanceUid = GetStringValue(*referencedInstances->getItem(k), DCM_ReferencedSOPInstanceUID);

          if (instancesInformation_.find(sopInstanceUid) == instancesInformation_.end())
          {
            instancesInformation_[sopInstanceUid] = new ReferencedInstance(studyInstanceUid, seriesInstanceUid, sopClassUid);
          }
          else
          {
            throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat,
                                            "Multiple occurrences of the same instance in DICOM-SR: " + sopInstanceUid);
          }

          tmp.push_back(sopInstanceUid);
        }
      }
    }

    orderedInstances_.reserve(tmp.size());

    for (std::list<std::string>::const_iterator it = tmp.begin(); it != tmp.end(); ++it)
    {
      orderedInstances_.push_back(*it);
    }

    sequence = GetSequenceValue(dataset, DCM_ContentSequence);

    for (unsigned long i = 0; i < sequence.card(); i++)
    {
      DcmItem& item = *sequence.getItem(i);

      if (GetStringValue(item, DCM_RelationshipType) == "CONTAINS" &&
          GetStringValue(item, DCM_ValueType) == "CONTAINER" &&
          IsDicomConcept(item, "126010" /* Imaging measurements */))
      {
        DcmSequenceOfItems& measurements = GetSequenceValue(item, DCM_ContentSequence);

        for (unsigned long j = 0; j < measurements.card(); j++)
        {
          DcmItem& measurement = *measurements.getItem(j);

          if (GetStringValue(measurement, DCM_RelationshipType) == "CONTAINS" &&
              GetStringValue(measurement, DCM_ValueType) == "CONTAINER" &&
              IsDicomConcept(measurement, "125007" /* Measurement group */) &&
              IsDicomTemplate(measurement, "1410"))
          {
            DcmSequenceOfItems& groups = GetSequenceValue(measurement, DCM_ContentSequence);

            bool hasProbabilityOfCancer = false;
            float probabilityOfCancer = 0;

            for (unsigned int k = 0; k < groups.card(); k++)
            {
              DcmItem& group = *groups.getItem(k);

              if (GetStringValue(group, DCM_RelationshipType) == "CONTAINS" &&
                  GetStringValue(group, DCM_ValueType) == "NUM" &&
                  IsDicomConcept(group, "111047" /* Probability of cancer */))
              {
                DcmSequenceOfItems& values = GetSequenceValue(group, DCM_MeasuredValueSequence);

                if (values.card() == 1 &&
                    IsValidConcept(*values.getItem(0), DCM_MeasurementUnitsCodeSequence, "UCUM", "%"))
                {
                  std::string value = GetStringValue(*values.getItem(0), DCM_NumericValue);
                  if (Orthanc::SerializationToolbox::ParseFloat(probabilityOfCancer, value))
                  {
                    hasProbabilityOfCancer = true;
                  }
                  else
                  {
                    throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat,
                                                    "Cannot parse float in DICOM-SR: " + value);
                  }
                }
              }
            }

            for (unsigned int k = 0; k < groups.card(); k++)
            {
              DcmItem& group = *groups.getItem(k);

              if (GetStringValue(group, DCM_RelationshipType) == "CONTAINS" &&
                  GetStringValue(group, DCM_ValueType) == "SCOORD" &&
                  IsDicomConcept(group, "111030" /* Image region */))
              {
                DcmSequenceOfItems& regions = GetSequenceValue(group, DCM_ContentSequence);

                for (unsigned int l = 0; l < regions.card(); l++)
                {
                  DcmItem& region = *regions.getItem(l);

                  if (GetStringValue(region, DCM_RelationshipType) == "SELECTED FROM" &&
                      GetStringValue(region, DCM_ValueType) == "IMAGE" &&
                      IsDicomConcept(region, "111040") /* Original source */)
                  {
                    DcmSequenceOfItems& instances = GetSequenceValue(region, DCM_ReferencedSOPSequence);
                    if (instances.card() != 1)
                    {
                      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat,
                                                      "Region cannot reference multiple instances in DICOM-SR");
                    }

                    std::string sopInstanceUid = GetStringValue(*instances.getItem(0), DCM_ReferencedSOPInstanceUID);
                    std::map<std::string, ReferencedInstance*>::iterator instanceInformation = instancesInformation_.find(sopInstanceUid);

                    if (instanceInformation == instancesInformation_.end())
                    {
                      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat,
                                                      "Referencing unknown instance in DICOM-SR: " + sopInstanceUid);
                    }

                    assert(instanceInformation->second != NULL);

                    if (instances.getItem(0)->tagExists(DCM_ReferencedFrameNumber))
                    {
                      std::string frames = GetStringValue(*instances.getItem(0), DCM_ReferencedFrameNumber);
                      std::vector<std::string> tokens;
                      Orthanc::Toolbox::SplitString(tokens, frames, '\\');

                      for (size_t m = 0; m < tokens.size(); m++)
                      {
                        uint32_t frame;
                        if (!Orthanc::SerializationToolbox::ParseUnsignedInteger32(frame, tokens[m]) ||
                            frame == 0)
                        {
                          throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
                        }
                        else
                        {
                          AddStructure(sopInstanceUid, group, true, frame - 1, hasProbabilityOfCancer, probabilityOfCancer);
                          instanceInformation->second->AddFrame(frame - 1);
                        }
                      }
                    }
                    else
                    {
                      AddStructure(sopInstanceUid, group, false, 0, hasProbabilityOfCancer, probabilityOfCancer);
                      instanceInformation->second->AddFrame(0);
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }


  static bool ReadTextualReport(Json::Value& target,
                                DcmItem& dataset)
  {
    target = Json::arrayValue;

    if (dataset.tagExists(DCM_ContentSequence))
    {
      DcmSequenceOfItems& content = GetSequenceValue(dataset, DCM_ContentSequence);
      for (unsigned long i = 0; i < content.card(); i++)
      {
        DcmItem* item = content.getItem(i);
        if (item != NULL &&
            item->tagExists(DCM_ValueType) &&
            item->tagExists(DCM_ConceptNameCodeSequence))
        {
          const std::string valueType = GetStringValue(*item, DCM_ValueType);

          DcmSequenceOfItems& concepts = GetSequenceValue(*item, DCM_ConceptNameCodeSequence);
          if (concepts.card() == 1 &&
              concepts.getItem(0) != NULL)
          {
            DcmItem& concept = *concepts.getItem(0);
            if (concept.tagExists(DCM_CodeMeaning))
            {
              const std::string codeMeaning = GetStringValue(concept, DCM_CodeMeaning);

              bool hasValue = false;
              std::string value;

              if (valueType == "TEXT" &&
                  item->tagExists(DCM_TextValue))
              {
                value = GetStringValue(*item, DCM_TextValue);
                hasValue = true;
              }
              else if (valueType == "UIDREF" &&
                       item->tagExists(DCM_UID))
              {
                value = GetStringValue(*item, DCM_UID);
                hasValue = true;
              }
              else if (valueType == "CODE" &&
                       item->tagExists(DCM_ConceptCodeSequence))
              {
                DcmSequenceOfItems& codes = GetSequenceValue(*item, DCM_ConceptCodeSequence);
                if (codes.card() == 1 &&
                    codes.getItem(0) != NULL)
                {
                  DcmItem& code = *codes.getItem(0);
                  if (code.tagExists(DCM_CodeMeaning))
                  {
                    value = GetStringValue(code, DCM_CodeMeaning);
                    hasValue = true;
                  }
                }
              }
              else if (valueType == "NUM" &&
                       item->tagExists(DCM_MeasuredValueSequence))
              {
                DcmSequenceOfItems& measurements = GetSequenceValue(*item, DCM_MeasuredValueSequence);
                if (measurements.card() == 1 &&
                    measurements.getItem(0) != NULL)
                {
                  DcmItem& measurement = *measurements.getItem(0);
                  if (measurement.tagExists(DCM_NumericValue))
                  {
                    value = GetStringValue(measurement, DCM_NumericValue);

                    if (measurement.tagExists(DCM_MeasurementUnitsCodeSequence))
                    {
                      DcmSequenceOfItems& units = GetSequenceValue(measurement, DCM_MeasurementUnitsCodeSequence);
                      if (units.card() == 1 &&
                          units.getItem(0) != NULL)
                      {
                        DcmItem& unit = *units.getItem(0);
                        if (unit.tagExists(DCM_CodeValue) &&
                            unit.tagExists(DCM_CodingSchemeDesignator))
                        {
                          const std::string& code = GetStringValue(unit, DCM_CodeValue);
                          const std::string& scheme = GetStringValue(unit, DCM_CodingSchemeDesignator);
                          if (scheme != "UCUM" ||
                              code != "1")
                          {
                            // In UCUM, the "1" code means "no unit"
                            value += " " + code;
                          }
                        }
                      }
                    }

                    hasValue = true;
                  }
                }
              }

              if (!hasValue &&
                  valueType != "CONTAINER")
              {
                value = "<" + valueType + ">";
                hasValue = true;
              }

              Json::Value line = Json::arrayValue;
              line.append(codeMeaning);

              if (hasValue)
              {
                line.append(value);
              }
              else
              {
                line.append(Json::nullValue);
              }

              Json::Value children;
              if (ReadTextualReport(children, *item))  // Recursive call
              {
                line.append(children);
              }

              target.append(line);
            }
          }
        }
      }

      return true;
    }
    else
    {
      return false;
    }
  }


  DicomStructuredReport::DicomStructuredReport(Orthanc::ParsedDicomFile& dicom) :
    isTID1500_(false)
  {
    StoneToolbox::ExtractMainDicomTags(mainDicomTags_, dicom);
    StoneToolbox::CopyDicomTag(mainDicomTags_, dicom, Orthanc::DicomTag(0x0040, 0xa491));  // "Completion Flag"
    StoneToolbox::CopyDicomTag(mainDicomTags_, dicom, Orthanc::DicomTag(0x0040, 0xa493));  // "Verification Flag"
    StoneToolbox::CopyDicomTag(mainDicomTags_, dicom, Orthanc::DICOM_TAG_SOP_CLASS_UID);

    DcmDataset& dataset = *dicom.GetDcmtkObject().getDataset();

    studyInstanceUid_ = GetStringValue(dataset, DCM_StudyInstanceUID);
    seriesInstanceUid_ = GetStringValue(dataset, DCM_SeriesInstanceUID);
    sopInstanceUid_ = GetStringValue(dataset, DCM_SOPInstanceUID);

    std::string sopClassUidString = GetStringValue(dataset, DCM_SOPClassUID);
    SopClassUid sopClassUid = StringToSopClassUid(sopClassUidString);
    if (!IsStructuredReport(sopClassUid))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
    }

    CheckStringValue(dataset, DCM_Modality, "SR");

    title_ = mainDicomTags_.GetStringValue(Orthanc::DICOM_TAG_SERIES_DESCRIPTION, "?", false);

    if (dataset.tagExists(DCM_ConceptNameCodeSequence))
    {
      DcmSequenceOfItems& concepts = GetSequenceValue(dataset, DCM_ConceptNameCodeSequence);
      if (concepts.card() == 1 &&
          concepts.getItem(0) != NULL &&
          concepts.getItem(0)->tagExists(DCM_CodeMeaning))
      {
        title_ = GetStringValue(*concepts.getItem(0), DCM_CodeMeaning);
      }
    }

    ReadTextualReport(textualReport_, dataset);

    if (sopClassUid == SopClassUid_ComprehensiveSR &&
        IsDicomConcept(dataset, "126000") /* Imaging measurement report */ &&
        IsDicomTemplate(dataset, "1500") &&
        dataset.tagExists(DCM_CurrentRequestedProcedureEvidenceSequence))
    {
      ReadTID1500(dicom);
      isTID1500_ = true;
    }
  }


  DicomStructuredReport::DicomStructuredReport(const DicomStructuredReport& other) :
    studyInstanceUid_(other.studyInstanceUid_),
    seriesInstanceUid_(other.seriesInstanceUid_),
    sopInstanceUid_(other.sopInstanceUid_),
    orderedInstances_(other.orderedInstances_)
  {
    for (std::map<std::string, ReferencedInstance*>::const_iterator
           it = other.instancesInformation_.begin(); it != other.instancesInformation_.end(); ++it)
    {
      assert(it->second != NULL);
      instancesInformation_[it->first] = new ReferencedInstance(*it->second);
    }

    for (std::deque<Structure*>::const_iterator it = other.structures_.begin(); it != other.structures_.end(); ++it)
    {
      assert(*it != NULL);
      structures_.push_back((*it)->Clone());
    }
  }


  DicomStructuredReport::~DicomStructuredReport()
  {
    for (std::deque<Structure*>::iterator it = structures_.begin(); it != structures_.end(); ++it)
    {
      assert(*it != NULL);
      delete *it;
    }

    for (std::map<std::string, ReferencedInstance*>::iterator
           it = instancesInformation_.begin(); it != instancesInformation_.end(); ++it)
    {
      assert(it->second != NULL);
      delete it->second;
    }
  }


  void DicomStructuredReport::GetReferencedInstance(std::string& studyInstanceUid,
                                                    std::string& seriesInstanceUid,
                                                    std::string& sopInstanceUid,
                                                    std::string& sopClassUid,
                                                    size_t i) const
  {
    if (i >= orderedInstances_.size())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }

    sopInstanceUid = orderedInstances_[i];

    std::map<std::string, ReferencedInstance*>::const_iterator found = instancesInformation_.find(sopInstanceUid);
    if (found == instancesInformation_.end())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
    }

    assert(found->second != NULL);
    studyInstanceUid = found->second->GetStudyInstanceUid();
    seriesInstanceUid = found->second->GetSeriesInstanceUid();
    sopClassUid = found->second->GetSopClassUid();
  }


  void DicomStructuredReport::ExportReferencedFrames(std::list<ReferencedFrame>& frames) const
  {
    frames.clear();

    for (size_t i = 0; i < orderedInstances_.size(); i++)
    {
      std::map<std::string, ReferencedInstance*>::const_iterator found = instancesInformation_.find(orderedInstances_[i]);
      if (found == instancesInformation_.end())
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
      }

      assert(found->second != NULL);

      for (std::set<unsigned int>::const_iterator frame = found->second->GetFrames().begin();
           frame != found->second->GetFrames().end(); ++frame)
      {
        frames.push_back(ReferencedFrame(found->second->GetStudyInstanceUid(),
                                         found->second->GetSeriesInstanceUid(),
                                         orderedInstances_[i],
                                         found->second->GetSopClassUid(), *frame));
      }
    }
  }


  const DicomStructuredReport::Structure& DicomStructuredReport::GetStructure(size_t index) const
  {
    if (index >= structures_.size())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
    else
    {
      assert(structures_[index] != NULL);
      return *structures_[index];
    }
  }


  bool DicomStructuredReport::IsReferencedInstance(const std::string& studyInstanceUid,
                                                   const std::string& seriesInstanceUid,
                                                   const std::string& sopInstanceUid) const
  {
    std::map<std::string, ReferencedInstance*>::const_iterator found = instancesInformation_.find(sopInstanceUid);

    if (found == instancesInformation_.end())
    {
      return false;
    }
    else
    {
      assert(found->second != NULL);
      return (found->second->GetStudyInstanceUid() == studyInstanceUid &&
              found->second->GetSeriesInstanceUid() == seriesInstanceUid);
    }
  }


  static void Flatten(Orthanc::ChunkedBuffer& buffer,
                      const Json::Value& node,
                      const std::string& indent)
  {
    assert(node.type() == Json::arrayValue);
    for (Json::ArrayIndex i = 0; i < node.size(); i++)
    {
      assert(node[i].type() == Json::arrayValue);
      assert(node[i].size() == 2 || node[i].size() == 3);
      assert(node[i][0].type() == Json::stringValue);
      assert(node[i][1].type() == Json::stringValue || node[i][1].type() == Json::nullValue);

      std::string line = indent + boost::lexical_cast<std::string>(i + 1) + ". " + node[i][0].asString();

      if (node[i][1].type() == Json::stringValue)
      {
        line += ": " + node[i][1].asString();
      }
      else
      {
        assert(node[i][1].type() == Json::nullValue);
      }

      buffer.AddChunk(line + "\n");

      if (node[i].size() == 3)
      {
        Flatten(buffer, node[i][2], indent + "     ");
      }
    }
  }


  void DicomStructuredReport::FlattenTextualReport(std::string& target) const
  {
    Orthanc::ChunkedBuffer buffer;
    Flatten(buffer, textualReport_, "");
    buffer.Flatten(target);
  }


  namespace
  {
    class TextWriter : public boost::noncopyable
    {
    private:
      BitmapLayout        layout_;
      Color               highlightColor_;
      Color               normalColor_;

      FontRenderer&       font_;
      GlyphBitmapAlphabet alphabet_;
      int                 x_;
      int                 y_;
      unsigned int        maxHeight_;

    public:
      TextWriter(FontRenderer& font,
                 const Color& highlightColor,
                 const Color& normalColor) :
        highlightColor_(highlightColor),
        normalColor_(normalColor),
        font_(font),
        x_(0),
        y_(0),
        maxHeight_(0)
      {
      }

      enum Move
      {
        Move_None,
        Move_SmallInterline,
        Move_LargeInterline
      };

      const Orthanc::ImageAccessor& Write(const std::string& s,
                                          Move mode)
      {
        std::unique_ptr<Orthanc::ImageAccessor> block(alphabet_.RenderColorText(font_, s, highlightColor_, normalColor_));
        const Orthanc::ImageAccessor& item = layout_.AddBlock(x_, y_, block.release());
        maxHeight_ = std::max(maxHeight_, item.GetHeight());

        switch (mode)
        {
          case Move_None:
            break;

          case Move_SmallInterline:
            y_ += maxHeight_ + maxHeight_ / 4;
            break;

          case Move_LargeInterline:
            y_ += maxHeight_ + maxHeight_;
            break;

          default:
            throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
        }

        return item;
      }

      void SetX(int x)
      {
        x_ = x;
      }

      unsigned int GetX() const
      {
        return x_;
      }

      Orthanc::ImageAccessor* Render(Orthanc::PixelFormat format) const
      {
        return layout_.Render(format);
      }
    };
  }


  static void Explore(TextWriter& writer,
                      const Json::Value& node,
                      unsigned int maxLineWidth)
  {
    assert(node.type() == Json::arrayValue);

    const unsigned int x = writer.GetX();

    for (Json::ArrayIndex i = 0; i < node.size(); i++)
    {
      assert(node[i].type() == Json::arrayValue);
      assert(node[i].size() == 2 || node[i].size() == 3);
      assert(node[i][0].type() == Json::stringValue);
      assert(node[i][1].type() == Json::stringValue || node[i][1].type() == Json::nullValue);
      assert(node[i].size() == 2 || node[i][2].type() == Json::arrayValue);

      std::string s = "\021" + boost::lexical_cast<std::string>(i + 1) + ".  ";
      const Orthanc::ImageAccessor& label = writer.Write(s, TextWriter::Move_None);

      std::string text = "\021" + node[i][0].asString();

      if (node[i][1].type() == Json::stringValue)
      {
        text += ":\022 " + node[i][1].asString();
      }

      std::string indented;
      GlyphAlphabet::IndentUtf8(indented, text, maxLineWidth, false);

      writer.SetX(x + label.GetWidth());
      writer.Write(text, TextWriter::Move_SmallInterline);

      if (node[i].size() == 3)
      {
        Explore(writer, node[i][2], std::max(60u, maxLineWidth - 10u));
      }

      writer.SetX(x);
    }
  }


  Orthanc::ImageAccessor* DicomStructuredReport::Render(FontRenderer& font,
                                                        const Color& highlightColor,
                                                        const Color& normalColor) const
  {
    TextWriter writer(font, highlightColor, normalColor);

    writer.Write(GetTitle(), TextWriter::Move_LargeInterline);

    std::string s = GetMainDicomTags().GetStringValue(Orthanc::DICOM_TAG_SERIES_TIME, "", false);
    size_t pos = s.find('.');
    if (pos != std::string::npos)
    {
      s = s.substr(0, pos);
    }

    s = "\021Series Date Time:\022 " + GetMainDicomTags().GetStringValue(Orthanc::DICOM_TAG_SERIES_DATE, "", false) + " at " + s;
    writer.Write(s, TextWriter::Move_LargeInterline);

    writer.Write("\021Patient's name:\022 " +
                 GetMainDicomTags().GetStringValue(Orthanc::DICOM_TAG_PATIENT_NAME, "", false),
                 TextWriter::Move_SmallInterline);
    writer.Write("\021Patient ID:\022 " +
                 GetMainDicomTags().GetStringValue(Orthanc::DICOM_TAG_PATIENT_ID, "", false),
                 TextWriter::Move_SmallInterline);
    writer.Write("\021Patient's Birth Date:\022 " +
                 GetMainDicomTags().GetStringValue(Orthanc::DICOM_TAG_PATIENT_BIRTH_DATE, "", false),
                 TextWriter::Move_SmallInterline);
    writer.Write("\021Patient's Sex:\022 " +
                 GetMainDicomTags().GetStringValue(Orthanc::DICOM_TAG_PATIENT_SEX, "", false),
                 TextWriter::Move_LargeInterline);

    writer.Write("\021Study Description:\022 " +
                 GetMainDicomTags().GetStringValue(Orthanc::DICOM_TAG_STUDY_DESCRIPTION, "", false),
                 TextWriter::Move_SmallInterline);
    writer.Write("\021Study ID:\022 " +
                 GetMainDicomTags().GetStringValue(Orthanc::DICOM_TAG_STUDY_ID, "", false),
                 TextWriter::Move_SmallInterline);
    writer.Write("\021Accession Number:\022 " +
                 GetMainDicomTags().GetStringValue(Orthanc::DICOM_TAG_ACCESSION_NUMBER, "", false),
                 TextWriter::Move_SmallInterline);
    writer.Write("\021Referring Physician's Name:\022 " +
                 GetMainDicomTags().GetStringValue(Orthanc::DICOM_TAG_REFERRING_PHYSICIAN_NAME, "", false),
                 TextWriter::Move_LargeInterline);

    writer.Write("\021Completion Flag:\022 " +
                 GetMainDicomTags().GetStringValue(Orthanc::DicomTag(0x0040, 0xa491), "", false),
                 TextWriter::Move_SmallInterline);
    writer.Write("\021Verification Flag:\022 " +
                 GetMainDicomTags().GetStringValue(Orthanc::DicomTag(0x0040, 0xa493), "", false),
                 TextWriter::Move_LargeInterline);

    Explore(writer, GetTextualReport(), 160);

    return writer.Render(Orthanc::PixelFormat_RGB24);
  }
}
