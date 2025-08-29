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

#include "../Scene2DViewport/IFlexiblePointerTracker.h"
#include "../Viewport/IViewport.h"
#include "PointerEvent.h"


namespace OrthancStone
{
  class PinchZoomTracker : public IFlexiblePointerTracker
  {
  private:
    enum State
    {
      State_OneFinger,
      State_TwoFingers,
      State_Upgraded,
      State_Dead
    };

    boost::weak_ptr<IViewport> viewport_;
    State                      state_;
    AffineTransform2D          originalSceneToCanvas_;
    AffineTransform2D          originalCanvasToScene_;
    ScenePoint2D               pivot_;
    double                     originalDistance_;

  public:
    PinchZoomTracker(boost::weak_ptr<IViewport> viewport,
                     const PointerEvent& event);

    virtual void PointerMove(const PointerEvent &event,
                             const Scene2D &scene) ORTHANC_OVERRIDE;

    virtual void PointerUp(const PointerEvent &event,
                           const Scene2D &scene) ORTHANC_OVERRIDE
    {
      state_ = State_Dead;
    }

    virtual void PointerDown(const PointerEvent &event,
                             const Scene2D &scene) ORTHANC_OVERRIDE
    {
    }

    virtual bool IsAlive() const ORTHANC_OVERRIDE
    {
      return state_ != State_Dead;
    }

    virtual void Cancel(const Scene2D &scene) ORTHANC_OVERRIDE
    {
      state_ = State_Dead;
    }
  };
}
