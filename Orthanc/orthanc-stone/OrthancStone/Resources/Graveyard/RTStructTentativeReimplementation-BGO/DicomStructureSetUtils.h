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

#include <vector>
#include <utility>

#include "../Scene2D/ScenePoint2D.h"
#include "../Toolbox/LinearAlgebra.h"

namespace OrthancStone
{
  /** Internal */
  struct RtStructRectangleInSlab
  {
    double xmin, xmax, ymin, ymax;
  };
  typedef std::vector<RtStructRectangleInSlab> RtStructRectanglesInSlab;

  enum RectangleBoundaryKind
  {
    RectangleBoundaryKind_Start,
    RectangleBoundaryKind_End
  };

#if 0
  /** Internal */
  void PartitionRectangleList(std::vector< std::vector<size_t> > & sets, const std::vector<RtStructRectanglesInSlab>);
#endif

  /** Internal */
  void ConvertListOfSlabsToSegments(std::vector< std::pair<ScenePoint2D, ScenePoint2D> >& segments,
                                    const std::vector<RtStructRectanglesInSlab>& slabCuts,
                                    const size_t totalRectCount);

  /** Internal */
  void AddSlabBoundaries(std::vector<std::pair<double, RectangleBoundaryKind> >& boundaries,
                         const std::vector<RtStructRectanglesInSlab>& slabCuts,
                         size_t iSlab);

  /** Internal */
  void ProcessBoundaryList(std::vector< std::pair<ScenePoint2D, ScenePoint2D> >& segments,
                           const std::vector<std::pair<double, RectangleBoundaryKind> >& boundaries,
                           double y);

}
