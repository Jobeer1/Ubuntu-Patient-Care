namespace OrthancStone
{
  static RtStructRectangleInSlab CreateRectangle(float x1, float y1,
                                                 float x2, float y2)
  {
    RtStructRectangleInSlab rect;
    rect.xmin = std::min(x1, x2);
    rect.xmax = std::max(x1, x2);
    rect.ymin = std::min(y1, y2);
    rect.ymax = std::max(y1, y2);
    return rect;
  }

  bool CompareRectanglesForProjection(const std::pair<RtStructRectangleInSlab,double>& r1,
                                      const std::pair<RtStructRectangleInSlab, double>& r2)
  {
    return r1.second < r2.second;
  }

  bool CompareSlabsY(const RtStructRectanglesInSlab& r1,
                     const RtStructRectanglesInSlab& r2)
  {
    if ((r1.size() == 0) || (r2.size() == 0))
      return false;

    return r1[0].ymax < r2[0].ymax;
  }
}


  bool DicomStructureSet::ProjectStructure(std::vector< std::vector<ScenePoint2D> >& chains,
                                           const Structure& structure,
                                           const CoordinateSystem3D& sourceSlice) const
  {

    // FOR SAGITTAL AND CORONAL


          // this will contain the intersection of the polygon slab with
      // the cutting plane, projected on the cutting plane coord system 
      // (that yields a rectangle) + the Z coordinate of the polygon 
      // (this is required to group polygons with the same Z later)
      std::vector<std::pair<RtStructRectangleInSlab, double> > projected;

      for (Polygons::const_iterator polygon = structure.polygons_.begin();
           polygon != structure.polygons_.end(); ++polygon)
      {
        double x1, y1, x2, y2;

        if (polygon->Project(x1, y1, x2, y2, slice, GetEstimatedNormal(), GetEstimatedSliceThickness()))
        {
          double curZ = polygon->GetGeometryOrigin()[2];

          // x1,y1 and x2,y2 are in "slice" coordinates (the cutting plane 
          // geometry)
          projected.push_back(std::make_pair(CreateRectangle(
                                               static_cast<float>(x1), 
                                               static_cast<float>(y1), 
                                               static_cast<float>(x2), 
                                               static_cast<float>(y2)),curZ));
        }
      }

      // projected contains a set of rectangles specified by two opposite
      // corners (x1,y1,x2,y2)
      // we need to merge them 
      // each slab yields ONE polygon!

      // we need to sorted all the rectangles that originate from the same Z
      // into lanes. To make sure they are grouped together in the array, we
      // sort it.
      std::sort(projected.begin(), projected.end(), CompareRectanglesForProjection);

      std::vector<RtStructRectanglesInSlab> rectanglesForEachSlab;
      rectanglesForEachSlab.reserve(projected.size());

      double curZ = 0;
      for (size_t i = 0; i < projected.size(); ++i)
      {
#if 0
        rectanglesForEachSlab.push_back(RtStructRectanglesInSlab());
#else
        if (i == 0)
        {
          curZ = projected[i].second;
          rectanglesForEachSlab.push_back(RtStructRectanglesInSlab());
        }
        else
        {
          // this check is needed to prevent creating a new slab if 
          // the new polygon is at the same Z coord than last one
          if (!LinearAlgebra::IsNear(curZ, projected[i].second))
          {
            rectanglesForEachSlab.push_back(RtStructRectanglesInSlab());
            curZ = projected[i].second;
          }
        }
#endif

        rectanglesForEachSlab.back().push_back(projected[i].first);

        // as long as they have the same y, we should put them into the same lane
        // BUT in Sebastien's code, there is only one polygon per lane.

        //std::cout << "rect: xmin = " << rect.xmin << " xmax = " << rect.xmax << " ymin = " << rect.ymin << " ymax = " << rect.ymax << std::endl;
      }
      
      // now we need to sort the slabs in increasing Y order (see ConvertListOfSlabsToSegments)
      std::sort(rectanglesForEachSlab.begin(), rectanglesForEachSlab.end(), CompareSlabsY);

      std::vector< std::pair<ScenePoint2D, ScenePoint2D> > segments;
      ConvertListOfSlabsToSegments(segments, rectanglesForEachSlab, projected.size());

      chains.resize(segments.size());
      for (size_t i = 0; i < segments.size(); i++)
      {
        chains[i].resize(2);
        chains[i][0] = segments[i].first;
        chains[i][1] = segments[i].second;
      }
#endif
      
      return true;
  }
