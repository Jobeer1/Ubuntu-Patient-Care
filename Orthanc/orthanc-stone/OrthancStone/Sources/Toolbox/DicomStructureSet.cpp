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


#define USE_BOOST_UNION_FOR_POLYGONS 0

#include "DicomStructureSet.h"

#include "BucketAccumulator2D.h"
#include "GenericToolbox.h"
#include "GeometryToolbox.h"
#include "OrthancDatasets/DicomDatasetReader.h"

#include <Logging.h>
#include <OrthancException.h>
#include <Toolbox.h>

#if defined(_MSC_VER)
#  pragma warning(push)
#  pragma warning(disable:4244)
#endif

#if STONE_TIME_BLOCKING_OPS
#  include <boost/date_time/posix_time/posix_time.hpp>
#endif

#if !defined(USE_BOOST_UNION_FOR_POLYGONS)
#  error Macro USE_BOOST_UNION_FOR_POLYGONS must be defined
#endif

#include <limits>
#include <stdio.h>
#include <boost/math/constants/constants.hpp>

#if USE_BOOST_UNION_FOR_POLYGONS == 1
#  include <boost/geometry.hpp>
#  include <boost/geometry/geometries/point_xy.hpp>
#  include <boost/geometry/geometries/polygon.hpp>
#  include <boost/geometry/multi/geometries/multi_polygon.hpp>
#else
#  include "UnionOfRectangles.h"
#endif

#if defined(_MSC_VER)
#  pragma warning(pop)
#endif

#if ORTHANC_ENABLE_DCMTK == 1
#  include "ParsedDicomDataset.h"
#endif


#if USE_BOOST_UNION_FOR_POLYGONS == 1

typedef boost::geometry::model::d2::point_xy<double> BoostPoint;
typedef boost::geometry::model::polygon<BoostPoint> BoostPolygon;
typedef boost::geometry::model::multi_polygon<BoostPolygon>  BoostMultiPolygon;

static void Union(BoostMultiPolygon& output,
                  std::vector<BoostPolygon>& input)
{
  for (size_t i = 0; i < input.size(); i++)
  {
    boost::geometry::correct(input[i]);
  }
  
  if (input.size() == 0)
  {
    output.clear();
  }
  else if (input.size() == 1)
  {
    output.resize(1);
    output[0] = input[0];
  }
  else
  {
    boost::geometry::union_(input[0], input[1], output);

    for (size_t i = 0; i < input.size(); i++)
    {
      BoostMultiPolygon tmp;
      boost::geometry::union_(output, input[i], tmp);
      output = tmp;
    }
  }
}

static BoostPolygon CreateRectangle(float x1, float y1,
                                    float x2, float y2)
{
  BoostPolygon r;
  boost::geometry::append(r, BoostPoint(x1, y1));
  boost::geometry::append(r, BoostPoint(x1, y2));
  boost::geometry::append(r, BoostPoint(x2, y2));
  boost::geometry::append(r, BoostPoint(x2, y1));
  return r;
}

#endif


namespace OrthancStone
{
  static const Orthanc::DicomTag DICOM_TAG_CONTOUR_DATA(0x3006, 0x0050);
  static const Orthanc::DicomTag DICOM_TAG_CONTOUR_GEOMETRIC_TYPE(0x3006, 0x0042);
  static const Orthanc::DicomTag DICOM_TAG_CONTOUR_IMAGE_SEQUENCE(0x3006, 0x0016);
  static const Orthanc::DicomTag DICOM_TAG_CONTOUR_SEQUENCE(0x3006, 0x0040);
  static const Orthanc::DicomTag DICOM_TAG_NUMBER_OF_CONTOUR_POINTS(0x3006, 0x0046);
  static const Orthanc::DicomTag DICOM_TAG_REFERENCED_ROI_NUMBER(0x3006, 0x0084);
  static const Orthanc::DicomTag DICOM_TAG_REFERENCED_SOP_INSTANCE_UID(0x0008, 0x1155);
  static const Orthanc::DicomTag DICOM_TAG_ROI_CONTOUR_SEQUENCE(0x3006, 0x0039);
  static const Orthanc::DicomTag DICOM_TAG_ROI_DISPLAY_COLOR(0x3006, 0x002a);
  static const Orthanc::DicomTag DICOM_TAG_ROI_NAME(0x3006, 0x0026);
  static const Orthanc::DicomTag DICOM_TAG_ROI_NUMBER(0x3006, 0x0022);
  static const Orthanc::DicomTag DICOM_TAG_RT_ROI_INTERPRETED_TYPE(0x3006, 0x00a4);
  static const Orthanc::DicomTag DICOM_TAG_RT_ROI_OBSERVATIONS_SEQUENCE(0x3006, 0x0080);
  static const Orthanc::DicomTag DICOM_TAG_STRUCTURE_SET_ROI_SEQUENCE(0x3006, 0x0020);


  static uint8_t ConvertColor(double v)
  {
    if (v < 0)
    {
      return 0;
    }
    else if (v >= 255)
    {
      return 255;
    }
    else
    {
      return static_cast<uint8_t>(v);
    }
  }


  static bool FastParseVector(Vector& target,
                              const IDicomDataset& dataset,
                              const Orthanc::DicomPath& tag)
  {
    std::string value;
    return (dataset.GetStringValue(value, tag) &&
            GenericToolbox::FastParseVector(target, value));
  }

  bool DicomStructureSet::Polygon::IsPointOnSliceIfAny(const Vector& v) const
  {
    if (hasSlice_)
    {
      double magnitude = 
        GeometryToolbox::ProjectAlongNormal(v, geometry_.GetNormal());
      bool onSlice = LinearAlgebra::IsNear(
        magnitude,
        projectionAlongNormal_,
        sliceThickness_ / 2.0 /* in mm */);
      if (!onSlice)
      {
        LOG(WARNING) << "This RT-STRUCT contains a point that is off the "
                     << "slice of its instance | "
                     << "magnitude = " << magnitude << " | "
                     << "projectionAlongNormal_ = " << projectionAlongNormal_ << " | "
                     << "tolerance (sliceThickness_ / 2.0) = " << (sliceThickness_ / 2.0);
      }
      return onSlice;
    }
    else
    {
      return true;
    }
  }

  void DicomStructureSet::Polygon::AddPoint(const Vector& v)
  {
#if 1
    // BGO 2019-09-03
    if (IsPointOnSliceIfAny(v))
    {
      points_.push_back(v);
    }
#else
    CheckPoint(v);
    points_.push_back(v);
#endif 
  }


  bool DicomStructureSet::Polygon::UpdateReferencedSlice(const ReferencedSlices& slices)
  {
    if (hasSlice_)
    {
      return true;
    }
    else
    {
      ReferencedSlices::const_iterator it = slices.find(sopInstanceUid_);
      
      if (it == slices.end())
      {
        return false;
      }
      else
      {
        const CoordinateSystem3D& geometry = it->second.geometry_;
        
        hasSlice_ = true;
        geometry_ = geometry;
        projectionAlongNormal_ = GeometryToolbox::ProjectAlongNormal(geometry.GetOrigin(), geometry.GetNormal());
        sliceThickness_ = it->second.thickness_;
        return true;
      }
    }
  }

  bool DicomStructureSet::Polygon::IsOnSlice(const CoordinateSystem3D& cuttingPlane,
                                             const Vector& estimatedNormal,
                                             double estimatedSliceThickness) const
  {
    bool isOpposite = false;

    if (points_.empty())
    {
      return false;
    }
    else if (hasSlice_)
    {
      // Use the actual geometry of this specific slice
      if (!GeometryToolbox::IsParallelOrOpposite(isOpposite, cuttingPlane.GetNormal(), geometry_.GetNormal()))
      {
        return false;
      }
      else
      {
        double d = GeometryToolbox::ProjectAlongNormal(cuttingPlane.GetOrigin(), geometry_.GetNormal());
        return (LinearAlgebra::IsNear(d, projectionAlongNormal_, sliceThickness_ / 2.0));
      }
    }
    else
    {
      // Use the estimated geometry for the global RT-STRUCT volume
      if (!GeometryToolbox::IsParallelOrOpposite(isOpposite, cuttingPlane.GetNormal(), estimatedNormal))
      {
        return false;
      }
      else
      {
        double d1 = GeometryToolbox::ProjectAlongNormal(cuttingPlane.GetOrigin(), estimatedNormal);
        double d2 = GeometryToolbox::ProjectAlongNormal(points_.front(), estimatedNormal);
        return (LinearAlgebra::IsNear(d1, d2, estimatedSliceThickness / 2.0));
      }
    }
  }


  void DicomStructureSet::Polygon::Project(std::list<Extent2D>& target,
                                           const CoordinateSystem3D& cuttingPlane,
                                           const Vector& estimatedNormal,
                                           double estimatedSliceThickness)
  {
    CoordinateSystem3D geometry;
    double thickness = estimatedSliceThickness;

    /**
     * 1. Estimate the 3D plane associated with this polygon.
     **/

    if (hasSlice_)
    {
      // The exact geometry is known for this slice
      geometry = geometry_;
      thickness = sliceThickness_;
    }
    else if (points_.size() < 2)
    {
      return;
    }
    else
    {
      // Estimate the geometry
      Vector origin = points_[0];

      Vector axisX;
      bool found = false;
      for (size_t i = 1; i < points_.size(); i++)
      {
        axisX = points_[i] - origin;

        bool isOpposite;  // Ignored
        if (boost::numeric::ublas::norm_2(axisX) > 10.0 * std::numeric_limits<double>::epsilon() &&
            !GeometryToolbox::IsParallelOrOpposite(isOpposite, axisX, estimatedNormal))
        {
          found = true;
          break;
        }
      }

      if (!found)
      {
        return;  // The polygon is too small to extract a reliable geometry out of it
      }

      LinearAlgebra::NormalizeVector(axisX);

      Vector axisY;
      LinearAlgebra::CrossProduct(axisY, axisX, estimatedNormal);
      geometry = CoordinateSystem3D(origin, axisX, axisY);
    }

    
    /**
     * 2. Project the 3D cutting plane as a 2D line onto the polygon plane.
     **/

    double cuttingX1, cuttingY1, cuttingX2, cuttingY2;
    geometry.ProjectPoint(cuttingX1, cuttingY1, cuttingPlane.GetOrigin());

    bool isOpposite;
    if (GeometryToolbox::IsParallelOrOpposite(isOpposite, geometry.GetNormal(), cuttingPlane.GetAxisX()))
    {
      geometry.ProjectPoint(cuttingX2, cuttingY2, cuttingPlane.GetOrigin() + cuttingPlane.GetAxisY());
    }
    else if (GeometryToolbox::IsParallelOrOpposite(isOpposite, geometry.GetNormal(), cuttingPlane.GetAxisY()))
    {
      geometry.ProjectPoint(cuttingX2, cuttingY2, cuttingPlane.GetOrigin() + cuttingPlane.GetAxisX());
    }
    else
    {
      return;
    }


    /**
     * 3. Compute the intersection of the 2D cutting line with the polygon.
     **/

    // Initialize the projection of a point onto a line:
    // https://stackoverflow.com/a/64330724
    const double abx = cuttingX2 - cuttingX1;
    const double aby = cuttingY2 - cuttingY1;
    const double denominator = abx * abx + aby * aby;
    if (LinearAlgebra::IsCloseToZero(denominator))
    {
      return;  // Should never happen
    }

    if (cachedProjectedSegments_.get() == NULL ||
        !cachedGeometry_.Equals(geometry))
    {
      cachedGeometry_ = geometry;

      cachedProjectedSegments_.reset(new std::vector<float>());
      cachedProjectedSegments_->resize(2 * points_.size());

      for (size_t i = 0; i < points_.size(); i++)
      {
        double x, y;
        geometry.ProjectPoint(x, y, points_[i]);
        (*cachedProjectedSegments_) [2 * i] = x;
        (*cachedProjectedSegments_) [2 * i + 1] = y;
      }
    }

    std::vector<double> intersections;
    intersections.reserve(points_.size());

    for (size_t i = 0; i < points_.size(); i++)
    {
      const size_t next = (i + 1) % points_.size();
      const double segmentX1 = (*cachedProjectedSegments_) [2 * i];
      const double segmentY1 = (*cachedProjectedSegments_) [2 * i + 1];
      const double segmentX2 = (*cachedProjectedSegments_) [2 * next];
      const double segmentY2 = (*cachedProjectedSegments_) [2 * next + 1];

      double x, y;
      if (GeometryToolbox::IntersectLineAndSegment(x, y, cuttingX1, cuttingY1, cuttingX2, cuttingY2,
                                                   segmentX1, segmentY1, segmentX2, segmentY2))
      {
        // For each polygon segment that intersect the cutting line,
        // register its offset over the cutting line
        const double acx = x - cuttingX1;
        const double acy = y - cuttingY1;
        intersections.push_back((abx * acx + aby * acy) / denominator);
      }
    }


    /**
     * 4. Sort the intersection offsets, then generates one 2D rectangle on the
     * cutting plane from each pair of successive intersections.
     **/

    std::sort(intersections.begin(), intersections.end());

    if (intersections.size() % 2 == 1)
    {
      return;  // Should never happen
    }

    for (size_t i = 0; i < intersections.size(); i += 2)
    {
      Vector p1, p2;

      {
        // Let's convert them to 3D world geometry to add the slice thickness
        const double x1 = cuttingX1 + intersections[i] * abx;
        const double y1 = cuttingY1 + intersections[i] * aby;
        const double x2 = cuttingX1 + intersections[i + 1] * abx;
        const double y2 = cuttingY1 + intersections[i + 1] * aby;

        p1 = (geometry.MapSliceToWorldCoordinates(x1, y1) + thickness / 2.0 * geometry.GetNormal());
        p2 = (geometry.MapSliceToWorldCoordinates(x2, y2) - thickness / 2.0 * geometry.GetNormal());
      }

      {
        // Then back to the cutting plane geometry
        double x1, y1, x2, y2;
        cuttingPlane.ProjectPoint2(x1, y1, p1);
        cuttingPlane.ProjectPoint2(x2, y2, p2);

        target.push_back(Extent2D(x1, y1, x2, y2));
      }
    }
  }

  
  DicomStructureSet::Structure::~Structure()
  {
    for (Polygons::iterator it = polygons_.begin(); it != polygons_.end(); ++it)
    {
      assert(*it != NULL);
      delete *it;
    }
  }


  const DicomStructureSet::Structure& DicomStructureSet::GetStructure(size_t index) const
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


  DicomStructureSet::Structure& DicomStructureSet::GetStructure(size_t index)
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

  void DicomStructureSet::Setup(const IDicomDataset& tags)
  {
#if STONE_TIME_BLOCKING_OPS
    boost::posix_time::ptime timerStart = boost::posix_time::microsec_clock::universal_time();
#endif

    std::map<int, size_t> roiNumbersIndex;

    DicomDatasetReader reader(tags);


    /**
     * 1. Read all the available ROIs.
     **/

    {
      size_t count;
      if (!tags.GetSequenceSize(count, Orthanc::DicomPath(DICOM_TAG_STRUCTURE_SET_ROI_SEQUENCE)))
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
      }

      structures_.resize(count);
      structureNamesIndex_.clear();

      for (size_t i = 0; i < count; i++)
      {
        int roiNumber;
        if (!reader.GetIntegerValue
            (roiNumber, Orthanc::DicomPath(DICOM_TAG_STRUCTURE_SET_ROI_SEQUENCE, i, DICOM_TAG_ROI_NUMBER)))
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
        }

        if (roiNumbersIndex.find(roiNumber) != roiNumbersIndex.end())
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat,
                                          "Twice the same ROI number: " + boost::lexical_cast<std::string>(roiNumber));
        }

        roiNumbersIndex[roiNumber] = i;

        structures_[i] = new Structure();
        structures_[i]->name_ = reader.GetStringValue
          (Orthanc::DicomPath(DICOM_TAG_STRUCTURE_SET_ROI_SEQUENCE, i, DICOM_TAG_ROI_NAME), "No name");
        structures_[i]->interpretation_ = "No interpretation";

        if (structureNamesIndex_.find(structures_[i]->name_) == structureNamesIndex_.end())
        {
          structureNamesIndex_[structures_[i]->name_] = i;
        }
        else
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat,
                                          "RT-STRUCT with twice the same name for a structure: " + structures_[i]->name_);
        }
      }
    }


    /**
     * 2. Read the interpretation of the ROIs (if available).
     **/

    {
      size_t count;
      if (!tags.GetSequenceSize(count, Orthanc::DicomPath(DICOM_TAG_RT_ROI_OBSERVATIONS_SEQUENCE)))
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
      }

      for (size_t i = 0; i < count; i++)
      {
        std::string interpretation;
        if (reader.GetDataset().GetStringValue(interpretation,
                                               Orthanc::DicomPath(DICOM_TAG_RT_ROI_OBSERVATIONS_SEQUENCE, i,
                                                                  DICOM_TAG_RT_ROI_INTERPRETED_TYPE)))
        {
          int roiNumber;
          if (!reader.GetIntegerValue(roiNumber,
                                      Orthanc::DicomPath(DICOM_TAG_RT_ROI_OBSERVATIONS_SEQUENCE, i,
                                                         DICOM_TAG_REFERENCED_ROI_NUMBER)))
          {
            throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
          }

          std::map<int, size_t>::const_iterator found = roiNumbersIndex.find(roiNumber);
          if (found == roiNumbersIndex.end())
          {
            throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
          }

          structures_[found->second]->interpretation_ = interpretation;
        }
      }
    }


    /**
     * 3. Read the contours.
     **/

    {
      size_t count;
      if (!tags.GetSequenceSize(count, Orthanc::DicomPath(DICOM_TAG_ROI_CONTOUR_SEQUENCE)))
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
      }

      for (size_t i = 0; i < count; i++)
      {
        int roiNumber;
        if (!reader.GetIntegerValue(roiNumber,
                                    Orthanc::DicomPath(DICOM_TAG_ROI_CONTOUR_SEQUENCE, i,
                                                       DICOM_TAG_REFERENCED_ROI_NUMBER)))
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
        }

        std::map<int, size_t>::const_iterator found = roiNumbersIndex.find(roiNumber);
        if (found == roiNumbersIndex.end())
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
        }

        Structure& target = *structures_[found->second];

        Vector color;
        if (FastParseVector(color, tags, Orthanc::DicomPath(DICOM_TAG_ROI_CONTOUR_SEQUENCE, i,
                                                            DICOM_TAG_ROI_DISPLAY_COLOR)) &&
            color.size() == 3)
        {
          target.red_ = ConvertColor(color[0]);
          target.green_ = ConvertColor(color[1]);
          target.blue_ = ConvertColor(color[2]);
        }
        else
        {
          target.red_ = 255;
          target.green_ = 0;
          target.blue_ = 0;
        }

        size_t countSlices;
        if (!tags.GetSequenceSize(countSlices, Orthanc::DicomPath(DICOM_TAG_ROI_CONTOUR_SEQUENCE, i,
                                                                  DICOM_TAG_CONTOUR_SEQUENCE)))
        {
          countSlices = 0;
        }

        LOG(INFO) << "New RT structure: \"" << target.name_
                  << "\" with interpretation \"" << target.interpretation_
                  << "\" containing " << countSlices << " slices (color: " 
                  << static_cast<int>(target.red_) << ","
                  << static_cast<int>(target.green_) << ","
                  << static_cast<int>(target.blue_) << ")";

        /**
         * These temporary variables avoid allocating many vectors in
         * the loop below (indeed, "Orthanc::DicomPath" handles a
         * "std::vector<PrefixItem>")
         **/
        Orthanc::DicomPath countPointsPath(DICOM_TAG_ROI_CONTOUR_SEQUENCE, i,
                                           DICOM_TAG_CONTOUR_SEQUENCE, 0,
                                           DICOM_TAG_NUMBER_OF_CONTOUR_POINTS);

        Orthanc::DicomPath geometricTypePath(DICOM_TAG_ROI_CONTOUR_SEQUENCE, i,
                                             DICOM_TAG_CONTOUR_SEQUENCE, 0,
                                             DICOM_TAG_CONTOUR_GEOMETRIC_TYPE);

        Orthanc::DicomPath imageSequencePath(DICOM_TAG_ROI_CONTOUR_SEQUENCE, i,
                                             DICOM_TAG_CONTOUR_SEQUENCE, 0,
                                             DICOM_TAG_CONTOUR_IMAGE_SEQUENCE);

        // (3006,0039)[i] / (0x3006, 0x0040)[0] / (0x3006, 0x0016)[0] / (0x0008, 0x1155)
        Orthanc::DicomPath referencedInstancePath(DICOM_TAG_ROI_CONTOUR_SEQUENCE, i,
                                                  DICOM_TAG_CONTOUR_SEQUENCE, 0,
                                                  DICOM_TAG_CONTOUR_IMAGE_SEQUENCE, 0,
                                                  DICOM_TAG_REFERENCED_SOP_INSTANCE_UID);

        Orthanc::DicomPath contourDataPath(DICOM_TAG_ROI_CONTOUR_SEQUENCE, i,
                                           DICOM_TAG_CONTOUR_SEQUENCE, 0,
                                           DICOM_TAG_CONTOUR_DATA);

        for (size_t j = 0; j < countSlices; j++)
        {
          unsigned int countPoints;

          countPointsPath.SetPrefixIndex(1, j);
          if (!reader.GetUnsignedIntegerValue(countPoints, countPointsPath))
          {
            throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
          }

          //LOG(INFO) << "Parsing slice containing " << countPoints << " vertices";

          geometricTypePath.SetPrefixIndex(1, j);
          std::string type = reader.GetMandatoryStringValue(geometricTypePath);
          if (type != "CLOSED_PLANAR")
          {
            LOG(WARNING) << "Ignoring contour with geometry type: " << type;
            continue;
          }

          size_t size;

          imageSequencePath.SetPrefixIndex(1, j);
          if (!tags.GetSequenceSize(size, imageSequencePath) || size != 1)
          {
            LOG(ERROR) << "The ContourImageSequence sequence (tag 3006,0016) must be present and contain one entry.";
            throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
          }

          referencedInstancePath.SetPrefixIndex(1, j);
          std::string sopInstanceUid = reader.GetMandatoryStringValue(referencedInstancePath);

          contourDataPath.SetPrefixIndex(1, j);
          std::string slicesData = reader.GetMandatoryStringValue(contourDataPath);

          Vector points;

          if (!GenericToolbox::FastParseVector(points, slicesData) ||
              points.size() != 3 * countPoints)
          {
            throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
          }

          // seen in real world
          if(Orthanc::Toolbox::StripSpaces(sopInstanceUid) == "")
          {
            LOG(ERROR) << "WARNING. The following Dicom tag (Referenced SOP Instance UID) contains an empty value : // (3006,0039)[" << i << "] / (0x3006, 0x0040)[0] / (0x3006, 0x0016)[0] / (0x0008, 0x1155)";
          }

          std::unique_ptr<Polygon> polygon(new Polygon(sopInstanceUid));
          polygon->Reserve(countPoints);

          for (size_t k = 0; k < countPoints; k++)
          {
            Vector v(3);
            v[0] = points[3 * k];
            v[1] = points[3 * k + 1];
            v[2] = points[3 * k + 2];
            polygon->AddPoint(v);
          }

          target.polygons_.push_back(polygon.release());
        }
      }
    }

    EstimateGeometry();
    
#if STONE_TIME_BLOCKING_OPS
    boost::posix_time::ptime timerEnd = boost::posix_time::microsec_clock::universal_time();
    boost::posix_time::time_duration duration = timerEnd - timerStart;
    int64_t durationMs = duration.total_milliseconds();
    LOG(WARNING) << "DicomStructureSet::Setup took " << durationMs << " ms";
#endif
  }


#if ORTHANC_ENABLE_DCMTK == 1
  DicomStructureSet::DicomStructureSet(Orthanc::ParsedDicomFile& instance)
  {
    ParsedDicomDataset dataset(instance);
    Setup(dataset);
  }
#endif
  

  DicomStructureSet::~DicomStructureSet()
  {
    for (size_t i = 0; i < structures_.size(); i++)
    {
      assert(structures_[i] != NULL);
      delete structures_[i];
    }
  }


  const std::string& DicomStructureSet::GetStructureName(size_t index) const
  {
    return GetStructure(index).name_;
  }


  const std::string& DicomStructureSet::GetStructureInterpretation(size_t index) const
  {
    return GetStructure(index).interpretation_;
  }


  Color DicomStructureSet::GetStructureColor(size_t index) const
  {
    const Structure& s = GetStructure(index);
    return Color(s.red_, s.green_, s.blue_);
  }
  
    
  void DicomStructureSet::GetReferencedInstances(std::set<std::string>& instances) const
  {
    for (size_t i = 0; i < structures_.size(); i++)
    {
      assert(structures_[i] != NULL);
      for (Polygons::const_iterator polygon = structures_[i]->polygons_.begin();
           polygon != structures_[i]->polygons_.end(); ++polygon)
      {
        assert(*polygon != NULL);
        instances.insert((*polygon)->GetSopInstanceUid());
      }
    }
  }


  void DicomStructureSet::AddReferencedSlice(const std::string& sopInstanceUid,
                                             const std::string& seriesInstanceUid,
                                             const CoordinateSystem3D& geometry,
                                             double thickness)
  {
    if (referencedSlices_.find(sopInstanceUid) != referencedSlices_.end())
    {
      // This geometry is already known
      LOG(ERROR) << "DicomStructureSet::AddReferencedSlice(): (referencedSlices_.find(sopInstanceUid) != referencedSlices_.end()). sopInstanceUid = " << sopInstanceUid;
     
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
    }
    else
    {
      if (thickness < 0)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
      }
        
      if (!referencedSlices_.empty())
      {
        const ReferencedSlice& reference = referencedSlices_.begin()->second;

        if (reference.seriesInstanceUid_ != seriesInstanceUid)
        {
          LOG(ERROR) << "This RT-STRUCT refers to several different series";
          throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
        }

        if (!GeometryToolbox::IsParallel(reference.geometry_.GetNormal(), geometry.GetNormal()))
        {
          LOG(ERROR) << "The slices in this RT-STRUCT are not parallel";
          throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
        }
      }
        
      referencedSlices_[sopInstanceUid] = ReferencedSlice(seriesInstanceUid, geometry, thickness);

      for (size_t i = 0; i < structures_.size(); i++)
      {
        assert(structures_[i] != NULL);

        for (Polygons::iterator polygon = structures_[i]->polygons_.begin();
             polygon != structures_[i]->polygons_.end(); ++polygon)
        {
          assert(*polygon != NULL);
          (*polygon)->UpdateReferencedSlice(referencedSlices_);
        }
      }
    }
  }


  void DicomStructureSet::AddReferencedSlice(const Orthanc::DicomMap& dataset)
  {
    CoordinateSystem3D slice(dataset);

    double thickness = 1;  // 1 mm by default

    std::string s;
    Vector v;
    if (dataset.LookupStringValue(s, Orthanc::DICOM_TAG_SLICE_THICKNESS, false) &&
        LinearAlgebra::ParseVector(v, s) &&
        v.size() > 0)
    {
      thickness = v[0];
    }

    std::string instance, series;
    if (dataset.LookupStringValue(instance, Orthanc::DICOM_TAG_SOP_INSTANCE_UID, false) &&
        dataset.LookupStringValue(series, Orthanc::DICOM_TAG_SERIES_INSTANCE_UID, false))
    {
      AddReferencedSlice(instance, series, slice, thickness);
    }
    else
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
    }
  }


  void DicomStructureSet::CheckReferencedSlices()
  {
    for (size_t i = 0; i < structures_.size(); i++)
    {
      assert(structures_[i] != NULL);
      for (Polygons::iterator polygon = structures_[i]->polygons_.begin();
           polygon != structures_[i]->polygons_.end(); ++polygon)
      {
        assert(*polygon != NULL);
        if (!(*polygon)->UpdateReferencedSlice(referencedSlices_))
        {
          std::string sopInstanceUid = (*polygon)->GetSopInstanceUid();
          if (Orthanc::Toolbox::StripSpaces(sopInstanceUid) == "")
          {
            LOG(ERROR) << "DicomStructureSet::CheckReferencedSlices(): "
                       << " missing information about referenced instance "
                       << "(sopInstanceUid is empty!)";
          }
          else
          {
            LOG(ERROR) << "DicomStructureSet::CheckReferencedSlices(): "
                       << " missing information about referenced instance "
                       << "(sopInstanceUid = " << sopInstanceUid << ")";
          }
          //throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
        }
      }
    }
  }


  Vector DicomStructureSet::GetNormal() const
  {
    if (referencedSlices_.empty())
    {
      Vector v;
      LinearAlgebra::AssignVector(v, 0, 0, 1);
      return v;
    }
    else
    {
      return referencedSlices_.begin()->second.geometry_.GetNormal();
    }
  }

  bool DicomStructureSet::ProjectStructure(std::vector< std::vector<ScenePoint2D> >& chains,
                                           const Structure& structure,
                                           const CoordinateSystem3D& cuttingPlane) const
  {
    const CoordinateSystem3D cutting = CoordinateSystem3D::NormalizeCuttingPlane(cuttingPlane);
    
    chains.clear();

    Vector normal = GetNormal();
    
    bool isOpposite;    
    if (GeometryToolbox::IsParallelOrOpposite(isOpposite, normal, cutting.GetNormal()))
    {
      // This is an axial projection

      chains.reserve(structure.polygons_.size());
      
      for (Polygons::const_iterator polygon = structure.polygons_.begin();
           polygon != structure.polygons_.end(); ++polygon)
      {
        assert(*polygon != NULL);
        const Points& points = (*polygon)->GetPoints();
        
        if ((*polygon)->IsOnSlice(cutting, GetEstimatedNormal(), GetEstimatedSliceThickness()) &&
            !points.empty())
        {
          chains.push_back(std::vector<ScenePoint2D>());
          chains.back().reserve(points.size() + 1);
          
          for (Points::const_iterator p = points.begin();
               p != points.end(); ++p)
          {
            double x, y;
            cutting.ProjectPoint2(x, y, *p);
            chains.back().push_back(ScenePoint2D(x, y));
          }

          double x0, y0;
          cutting.ProjectPoint2(x0, y0, points.front());
          chains.back().push_back(ScenePoint2D(x0, y0));
        }
      }

      return true;
    }
    else if (GeometryToolbox::IsParallelOrOpposite(isOpposite, normal, cutting.GetAxisX()) ||
             GeometryToolbox::IsParallelOrOpposite(isOpposite, normal, cutting.GetAxisY()))
    {
      // Sagittal or coronal projection

#if USE_BOOST_UNION_FOR_POLYGONS == 1
      std::vector<BoostPolygon> projected;

      for (Polygons::const_iterator polygon = structure.polygons_.begin();
           polygon != structure.polygons_.end(); ++polygon)
      {
        std::list<Extent2D> rectangles;
        polygon->Project(rectangles, cutting, GetEstimatedNormal(), GetEstimatedSliceThickness());

        for (std::list<Extent2D>::const_iterator it = rectangles.begin(); it != rectangles.end(); ++it)
        {
          projected.push_back(CreateRectangle(it->GetX1(), it->GetY1(), it->GetX2(), it->GetY2()));
        }
      }

      BoostMultiPolygon merged;
      Union(merged, projected);

      chains.resize(merged.size());
      for (size_t i = 0; i < merged.size(); i++)
      {
        const std::vector<BoostPoint>& outer = merged[i].outer();

        chains[i].resize(outer.size());
        for (size_t j = 0; j < outer.size(); j++)
        {
          chains[i][j] = ScenePoint2D(outer[j].x(), outer[j].y());
        }
      }  

#else

      std::list<Extent2D> rectangles;
      
      for (Polygons::const_iterator polygon = structure.polygons_.begin();
           polygon != structure.polygons_.end(); ++polygon)
      {
        assert(*polygon != NULL);
        (*polygon)->Project(rectangles, cutting, GetEstimatedNormal(), GetEstimatedSliceThickness());
      }

      typedef std::list< std::vector<ScenePoint2D> >  Contours;

      Contours contours;
      UnionOfRectangles::Apply(contours, rectangles);

      chains.reserve(contours.size());
      
      for (Contours::const_iterator it = contours.begin(); it != contours.end(); ++it)
      {
        chains.push_back(*it);
      }
      
#endif

      return true;
    }
    else
    {
      return false;
    }
  }


  void DicomStructureSet::ProjectOntoLayer(PolylineSceneLayer& layer,
                                           const CoordinateSystem3D& cuttingPlane,
                                           size_t structureIndex,
                                           const Color& color) const
  {
    std::vector< std::vector<ScenePoint2D> > chains;
    
    if (ProjectStructure(chains, structureIndex, cuttingPlane))
    {
      for (size_t j = 0; j < chains.size(); j++)
      {
        layer.AddChain(chains[j], false, color.GetRed(), color.GetGreen(), color.GetBlue());
      }
    }
  }


  void DicomStructureSet::GetStructurePoints(std::list< std::vector<Vector> >& target,
                                             size_t structureIndex,
                                             const std::string& sopInstanceUid) const
  {
    target.clear();
    
    const Structure& structure = GetStructure(structureIndex);

    // TODO - Could be optimized by adding a multimap on "Structure", mapping
    // from SOP Instance UID to polygons
    
    for (Polygons::const_iterator polygon = structure.polygons_.begin();
         polygon != structure.polygons_.end(); ++polygon)
    {
      assert(*polygon != NULL);
      if ((*polygon)->GetSopInstanceUid() == sopInstanceUid)
      {
        target.push_back((*polygon)->GetPoints());
      }
    }
  }


  void DicomStructureSet::EstimateGeometry()
  {
    static const double PI = boost::math::constants::pi<double>();

    BucketAccumulator2D accumulator(0, PI, 9,   /* for acos() */
                                    -PI, PI, 9, /* for atan() */
                                    true /* store values */);

    unsigned int countPolygons = 0;
    for (size_t i = 0; i < structures_.size(); i++)
    {
      assert(structures_[i] != NULL);
      const Polygons& polygons = structures_[i]->polygons_;

      for (Polygons::const_iterator polygon = polygons.begin(); polygon != polygons.end(); ++polygon)
      {
        assert(*polygon != NULL);

        countPolygons++;

        const Points& points = (*polygon)->GetPoints();
        
        if (points.size() >= 3)
        {
          // Compute the normal of the polygon using 3 successive points
          Vector normal;
          bool valid = false;

          for (size_t j = 0; j + 2 < points.size(); j++)
          {
            const Vector& a = points[j];
            const Vector& b = points[j + 1];
            const Vector& c = points[j + 2];
            LinearAlgebra::CrossProduct(normal, b - a, c - a);  // (*)
            LinearAlgebra::NormalizeVector(normal);

            if (LinearAlgebra::IsNear(boost::numeric::ublas::norm_2(normal), 1.0))  // (**)
            {
              valid = true;
              break;
            }
          }

          if (valid)
          {
            // Check that all the points of the polygon lie in the plane defined by the normal
            double d1 = GeometryToolbox::ProjectAlongNormal(points[0], normal);
          
            for (size_t j = 1; j < points.size(); j++)
            {
              double d2 = GeometryToolbox::ProjectAlongNormal(points[j], normal);
            
              if (!LinearAlgebra::IsNear(d1, d2))
              {
                valid = false;
                break;
              }
            }
          }

          if (valid)
          {
            if (normal[2] < 0)
            {
              normal = -normal;
            }

            // The normal is a non-zero unit vector because of (*) and (**), so "r == 1"
            // https://en.wikipedia.org/wiki/Vector_fields_in_cylindrical_and_spherical_coordinates#Vector_fields_2
            
            const double theta = acos(normal[2]);
            const double phi = atan(normal[1]);
            accumulator.AddValue(theta, phi);
          }
        }
      }
    }

    size_t bestX, bestY;
    accumulator.FindBestBucket(bestX, bestY);

    if (accumulator.GetBucketContentSize(bestX, bestY) > 0)
    {
      double normalTheta, normalPhi;
      accumulator.ComputeBestMedian(normalTheta, normalPhi);
      
      // Back to (x,y,z) normal, taking "r == 1"
      // https://en.wikipedia.org/wiki/Vector_fields_in_cylindrical_and_spherical_coordinates#Vector_fields_2
      double sinTheta = sin(normalTheta);
      estimatedNormal_ = LinearAlgebra::CreateVector(sinTheta * cos(normalPhi), sinTheta * sin(normalPhi), cos(normalTheta));
    }
      
    std::vector<double> polygonsProjection;
    polygonsProjection.reserve(countPolygons);
    
    for (size_t i = 0; i < structures_.size(); i++)
    {
      assert(structures_[i] != NULL);
      const Polygons& polygons = structures_[i]->polygons_;

      for (Polygons::const_iterator polygon = polygons.begin(); polygon != polygons.end(); ++polygon)
      {
        assert(*polygon != NULL);
        const Points& points = (*polygon)->GetPoints();
        polygonsProjection.push_back(GeometryToolbox::ProjectAlongNormal(points[0], estimatedNormal_));
      }
    }

    std::sort(polygonsProjection.begin(), polygonsProjection.end());

    std::vector<double> deltas;
    deltas.reserve(polygonsProjection.size());

    for (size_t i = 0; i + 1 < polygonsProjection.size(); i++)
    {
      if (!LinearAlgebra::IsNear(polygonsProjection[i], polygonsProjection[i + 1]))
      {
        assert(polygonsProjection[i + 1] > polygonsProjection[i]);
        deltas.push_back(polygonsProjection[i + 1] - polygonsProjection[i]);
      }
    }

    if (deltas.empty())
    {
      estimatedSliceThickness_ = 1;
    }
    else
    {
      estimatedSliceThickness_ = LinearAlgebra::ComputeMedian(deltas);
    }
  }


  bool DicomStructureSet::LookupStructureName(size_t& structureIndex /* out */,
                                              const std::string& name) const
  {
    StructureNamesIndex::const_iterator found = structureNamesIndex_.find(name);

    if (found == structureNamesIndex_.end())
    {
      return false;
    }
    else
    {
      structureIndex = found->second;
      return true;
    }
  }
}
