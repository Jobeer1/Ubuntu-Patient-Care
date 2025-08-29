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


#pragma once

#if !defined(ORTHANC_ENABLE_DCMTK)
#  error The macro ORTHANC_ENABLE_DCMTK must be defined
#endif

#if ORTHANC_ENABLE_DCMTK != 1
#  error Support for DCMTK must be enabled
#endif

#include "../Fonts/FontRenderer.h"
#include "../Scene2D/Color.h"
#include "../Scene2D/ScenePoint2D.h"

#include <DicomParsing/ParsedDicomFile.h>

#include <dcmtk/dcmdata/dcitem.h>
#include <deque>
#include <list>
#include <set>

namespace OrthancStone
{
  class DicomStructuredReport : public boost::noncopyable
  {
  public:
    enum StructureType
    {
      StructureType_Point,
      StructureType_Polyline
    };

    class Structure : public boost::noncopyable
    {
    private:
      std::string   sopInstanceUid_;
      bool          hasFrameNumber_;
      unsigned int  frameNumber_;
      bool          hasProbabilityOfCancer_;
      float         probabilityOfCancer_;

    protected:
      void Copy(const Structure& other);

    public:
      explicit Structure(const std::string& sopInstanceUid);

      virtual ~Structure()
      {
      }

      virtual Structure* Clone() const = 0;

      virtual StructureType GetType() const = 0;

      const std::string& GetSopInstanceUid() const
      {
        return sopInstanceUid_;
      }

      void SetFrameNumber(unsigned int frame);

      void SetProbabilityOfCancer(float probability);

      bool HasFrameNumber() const
      {
        return hasFrameNumber_;
      }

      bool HasProbabilityOfCancer() const
      {
        return hasProbabilityOfCancer_;
      }

      unsigned int GetFrameNumber() const;

      float GetProbabilityOfCancer() const;
    };


    class Point : public Structure
    {
    private:
      ScenePoint2D  point_;

    public:
      Point(const std::string& sopInstanceUid,
            double x,
            double y);

      virtual Structure* Clone() const ORTHANC_OVERRIDE;

      virtual StructureType GetType() const ORTHANC_OVERRIDE
      {
        return StructureType_Point;
      }

      const ScenePoint2D& GetPoint() const
      {
        return point_;
      }
    };


    class Polyline : public Structure
    {
    private:
      std::vector<ScenePoint2D>  points_;

    public:
      Polyline(const std::string& sopInstanceUid,
               const float* points,
               unsigned long pointsCount);

      Polyline(const std::string& sopInstanceUid,
               const std::vector<ScenePoint2D>& points);

      virtual Structure* Clone() const ORTHANC_OVERRIDE;

      virtual StructureType GetType() const ORTHANC_OVERRIDE
      {
        return StructureType_Polyline;
      }

      size_t GetSize() const
      {
        return points_.size();
      }

      const ScenePoint2D& GetPoint(size_t i) const;
    };


  private:
    class ReferencedInstance
    {
    private:
      std::string  studyInstanceUid_;
      std::string  seriesInstanceUid_;
      std::string  sopClassUid_;
      std::set<unsigned int>  frames_;

    public:
      ReferencedInstance(const std::string& studyInstanceUid,
                         const std::string& seriesInstanceUid,
                         const std::string& sopClassUid) :
        studyInstanceUid_(studyInstanceUid),
        seriesInstanceUid_(seriesInstanceUid),
        sopClassUid_(sopClassUid)
      {
      }

      const std::string& GetStudyInstanceUid() const
      {
        return studyInstanceUid_;
      }

      const std::string& GetSeriesInstanceUid() const
      {
        return seriesInstanceUid_;
      }

      const std::string& GetSopClassUid() const
      {
        return sopClassUid_;
      }

      void AddFrame(unsigned int frame)
      {
        frames_.insert(frame);
      }

      const std::set<unsigned int>& GetFrames() const
      {
        return frames_;
      }
    };


    void AddStructure(const std::string& sopInstanceUid,
                      DcmItem& group,
                      bool hasFrameNumber,
                      unsigned int frameNumber,
                      bool hasProbabilityOfCancer,
                      float probabilityOfCancer);

    void ReadTID1500(Orthanc::ParsedDicomFile& dicom);

    std::string                                 studyInstanceUid_;
    std::string                                 seriesInstanceUid_;
    std::string                                 sopInstanceUid_;
    std::string                                 title_;
    Orthanc::DicomMap                           mainDicomTags_;
    Json::Value                                 textualReport_;

    bool                                        isTID1500_;
    std::map<std::string, ReferencedInstance*>  instancesInformation_;
    std::vector<std::string>                    orderedInstances_;
    std::deque<Structure*>                      structures_;

  public:
    class ReferencedFrame
    {
    private:
      std::string  studyInstanceUid_;
      std::string  seriesInstanceUid_;
      std::string  sopInstanceUid_;
      std::string  sopClassUid_;
      unsigned int frameNumber_;

    public:
      ReferencedFrame(const std::string& studyInstanceUid,
                      const std::string& seriesInstanceUid,
                      const std::string& sopInstanceUid,
                      const std::string& sopClassUid,
                      unsigned int frameNumber) :
        studyInstanceUid_(studyInstanceUid),
        seriesInstanceUid_(seriesInstanceUid),
        sopInstanceUid_(sopInstanceUid),
        sopClassUid_(sopClassUid),
        frameNumber_(frameNumber)
      {
      }

      const std::string& GetStudyInstanceUid() const
      {
        return studyInstanceUid_;
      }

      const std::string& GetSeriesInstanceUid() const
      {
        return seriesInstanceUid_;
      }

      const std::string& GetSopInstanceUid() const
      {
        return sopInstanceUid_;
      }

      const std::string& GetSopClassUid() const
      {
        return sopClassUid_;
      }

      unsigned int GetFrameNumber() const
      {
        return frameNumber_;
      }
    };

    explicit DicomStructuredReport(Orthanc::ParsedDicomFile& dicom);

    explicit DicomStructuredReport(const DicomStructuredReport& other);  // Copy constructor

    ~DicomStructuredReport();

    const std::string& GetStudyInstanceUid() const
    {
      return studyInstanceUid_;
    }

    const std::string& GetSeriesInstanceUid() const
    {
      return seriesInstanceUid_;
    }
    
    const std::string& GetSopInstanceUid() const
    {
      return sopInstanceUid_;
    }

    const std::string& GetTitle() const
    {
      return title_;
    }

    const Orthanc::DicomMap& GetMainDicomTags() const
    {
      return mainDicomTags_;
    }

    const Json::Value& GetTextualReport() const
    {
      return textualReport_;
    }

    bool IsTID1500() const
    {
      return isTID1500_;
    }

    size_t GetReferencedInstancesCount() const
    {
      return orderedInstances_.size();
    }

    void GetReferencedInstance(std::string& studyInstanceUid,
                               std::string& seriesInstanceUid,
                               std::string& sopInstanceUid,
                               std::string& sopClassUid,
                               size_t i) const;

    void ExportReferencedFrames(std::list<ReferencedFrame>& frames) const;

    size_t GetStructuresCount() const
    {
      return structures_.size();
    }

    const Structure& GetStructure(size_t index) const;

    bool IsReferencedInstance(const std::string& studyInstanceUid,
                              const std::string& seriesInstanceUid,
                              const std::string& sopInstanceUid) const;

    void FlattenTextualReport(std::string& target) const;

    Orthanc::ImageAccessor* Render(FontRenderer& font,
                                   const Color& highlightColor,
                                   const Color& normalColor) const;
  };
}
