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

#include "../../Scene2DViewport/ViewportController.h"

namespace OrthancStone
{
  namespace Internals
  {
    // During a mouse event that modifies the view of a scene, keeps
    // one point (the pivot) at a fixed position on the canvas
    class FixedPointAligner : public boost::noncopyable
    {
    private:
      ScenePoint2D  pivot_;
      ScenePoint2D  canvas_;

    public:
      FixedPointAligner(const ViewportController& controller,
                        const ScenePoint2D& p);

      void Apply(ViewportController& controller);
    };
  }
}
