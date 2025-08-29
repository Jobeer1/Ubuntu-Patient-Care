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

#include "../OrthancStone.h"

#if !defined(ORTHANC_ENABLE_DCMTK)
#  error The macro ORTHANC_ENABLE_DCMTK must be defined
#endif

#include "CoordinateSystem3D.h"
#include "Extent2D.h"
#include "OrthancDatasets/FullOrthancDataset.h"
#include "../Scene2D/Color.h"
#include "../Scene2D/PolylineSceneLayer.h"
#include "../Scene2D/ScenePoint2D.h"

#if ORTHANC_ENABLE_DCMTK == 1
#  include <DicomParsing/ParsedDicomFile.h>
#endif


#include <list>

namespace OrthancStone
{
  class DicomStructureSet : public boost::noncopyable
  {
  private:
    struct ReferencedSlice
    {
      std::string          seriesInstanceUid_;
      CoordinateSystem3D   geometry_;
      double               thickness_;

      ReferencedSlice()
      {
      }
      
      ReferencedSlice(const std::string& seriesInstanceUid,
                      const CoordinateSystem3D& geometry,
                      double thickness) :
        seriesInstanceUid_(seriesInstanceUid),
        geometry_(geometry),
        thickness_(thickness)
      {
      }
    };

    typedef std::map<std::string, ReferencedSlice>  ReferencedSlices;
    
    typedef std::vector<Vector>  Points;

    class Polygon : public boost::noncopyable
    {
    private:
      std::string         sopInstanceUid_;
      bool                hasSlice_;
      CoordinateSystem3D  geometry_;
      double              projectionAlongNormal_;
      double              sliceThickness_;  // In millimeters
      Points              points_;

      CoordinateSystem3D                    cachedGeometry_;
      std::unique_ptr< std::vector<float> > cachedProjectedSegments_;

      bool IsPointOnSliceIfAny(const Vector& v) const;

    public:
      explicit Polygon(const std::string& sopInstanceUid) :
        sopInstanceUid_(sopInstanceUid),
        hasSlice_(false),
        projectionAlongNormal_(0),
        sliceThickness_(0)
      {
      }

      void Reserve(size_t n)
      {
        points_.reserve(n);
      }

      void AddPoint(const Vector& v);

      bool UpdateReferencedSlice(const ReferencedSlices& slices);

      bool IsOnSlice(const CoordinateSystem3D& cuttingPlane,
                     const Vector& estimatedNormal,
                     double estimatedSliceThickness) const;

      const Vector& GetGeometryOrigin() const
      {
        return geometry_.GetOrigin();
      }

      const std::string& GetSopInstanceUid() const
      {
        return sopInstanceUid_;
      }

      const Points& GetPoints() const
      {
        return points_;
      }

      double GetSliceThickness() const
      {
        return sliceThickness_;
      }

      void Project(std::list<Extent2D>& target,
                   const CoordinateSystem3D& cuttingPlane,
                   const Vector& estimatedNormal,
                   double estimatedSliceThickness);
    };

    typedef std::list<Polygon*>  Polygons;

    struct Structure : public boost::noncopyable
    {
      std::string   name_;
      std::string   interpretation_;
      Polygons      polygons_;
      uint8_t       red_;
      uint8_t       green_;
      uint8_t       blue_;

      ~Structure();
    };

    typedef std::map<std::string, size_t>  StructureNamesIndex;

    std::vector<Structure*>  structures_;
    ReferencedSlices         referencedSlices_;
    Vector                   estimatedNormal_;
    double                   estimatedSliceThickness_;
    StructureNamesIndex      structureNamesIndex_;

    void Setup(const IDicomDataset& dataset);
    
    const Structure& GetStructure(size_t index) const;

    Structure& GetStructure(size_t index);
  
    bool ProjectStructure(std::vector< std::vector<ScenePoint2D> >& chains,
                          const Structure& structure,
                          const CoordinateSystem3D& cuttingPlane) const;

    void EstimateGeometry();
    
  public:
    explicit DicomStructureSet(const FullOrthancDataset& instance)
    {
      Setup(instance);
    }

#if ORTHANC_ENABLE_DCMTK == 1
    explicit DicomStructureSet(Orthanc::ParsedDicomFile& instance);
#endif

    ~DicomStructureSet();

    size_t GetStructuresCount() const
    {
      return structures_.size();
    }

    const std::string& GetStructureName(size_t index) const;

    const std::string& GetStructureInterpretation(size_t index) const;

    Color GetStructureColor(size_t index) const;

    void GetReferencedInstances(std::set<std::string>& instances) const;

    void AddReferencedSlice(const std::string& sopInstanceUid,
                            const std::string& seriesInstanceUid,
                            const CoordinateSystem3D& geometry,
                            double thickness);

    void AddReferencedSlice(const Orthanc::DicomMap& dataset);

    void CheckReferencedSlices();

    Vector GetNormal() const;

    bool ProjectStructure(std::vector< std::vector<ScenePoint2D> >& chains,
                          size_t index,
                          const CoordinateSystem3D& cuttingPlane) const
    {
      return ProjectStructure(chains, GetStructure(index), cuttingPlane);
    }

    void ProjectOntoLayer(PolylineSceneLayer& layer,
                          const CoordinateSystem3D& cuttingPlane,
                          size_t structureIndex,
                          const Color& color) const;

    void ProjectOntoLayer(PolylineSceneLayer& layer,
                          const CoordinateSystem3D& cuttingPlane,
                          size_t structureIndex) const
    {
      ProjectOntoLayer(layer, cuttingPlane, structureIndex, GetStructureColor(structureIndex));
    }

    void GetStructurePoints(std::list< std::vector<Vector> >& target,
                            size_t structureIndex,
                            const std::string& sopInstanceUid) const;

    const Vector& GetEstimatedNormal() const
    {
      return estimatedNormal_;
    }

    const double GetEstimatedSliceThickness() const
    {
      return estimatedSliceThickness_;
    }

    bool LookupStructureName(size_t& structureIndex /* out */,
                             const std::string& name) const;
  };
}
