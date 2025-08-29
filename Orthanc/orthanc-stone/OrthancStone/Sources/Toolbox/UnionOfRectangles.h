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

#include "Extent2D.h"
#include "../Scene2D/ScenePoint2D.h"

#include <list>


namespace OrthancStone
{
  /**
   * This implementation closely follows "Finding the Contour of a
   * Union of Iso-Oriented Rectangles" by Lipski and Preparata (1980),
   * as well as Section 8.5 (pages 340-348) of "Computational Geometry
   * - An Introduction" by Preparata and Ian Shamos (1985).
   **/
  class UnionOfRectangles : public boost::noncopyable
  {
  private:
    enum Operation
    {
      Operation_Insert,
      Operation_Delete
    };

    enum Status
    {
      Status_Full,
      Status_Partial,
      Status_Empty
    };

    class Payload;
    class Factory;
    class Visitor;

    class VerticalSide;
    class HorizontalJunction;
    
    UnionOfRectangles();  // Pure static class

  public:
    static void Apply(std::list< std::vector<ScenePoint2D> >& contours,
                      const std::list<Extent2D>& rectangles);
  };
}
