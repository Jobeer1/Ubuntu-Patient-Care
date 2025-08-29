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


#include "PinchZoomTracker.h"

#include "../Scene2DViewport/ViewportController.h"
#include "../Viewport/ViewportLocker.h"

namespace OrthancStone
{
  static ScenePoint2D GetCenter(const PointerEvent& event)
  {
    assert(event.GetPositionsCount() == 2);
    return ScenePoint2D((event.GetPosition(0).GetX() + event.GetPosition(1).GetX()) / 2.0,
                        (event.GetPosition(0).GetY() + event.GetPosition(1).GetY()) / 2.0);
  }


  PinchZoomTracker::PinchZoomTracker(boost::weak_ptr<IViewport> viewport,
                                     const PointerEvent& event) :
    viewport_(viewport),
    state_(State_Dead)
  {
    ViewportLocker locker(viewport_);

    if (locker.IsValid())
    {
      originalSceneToCanvas_ = locker.GetController().GetSceneToCanvasTransform();
      originalCanvasToScene_ = locker.GetController().GetCanvasToSceneTransform();

      if (event.GetPositionsCount() == 1)
      {
        state_ = State_OneFinger;
        pivot_ = event.GetPosition(0).Apply(originalCanvasToScene_);
        originalDistance_ = 0;
      }
      else if (event.GetPositionsCount() == 2)
      {
        state_ = State_TwoFingers;
        pivot_ = GetCenter(event).Apply(originalCanvasToScene_);
        originalDistance_ = ScenePoint2D::DistancePtPt(event.GetPosition(0), event.GetPosition(1));
      }
    }
  }


  void PinchZoomTracker::PointerMove(const PointerEvent &event,
                                     const Scene2D &scene)
  {
    if (state_ == State_OneFinger &&
        event.GetPositionsCount() == 2)
    {
      // Upgrade from 1 finger to 2 fingers, keeping the original pivot point
      state_ = State_Upgraded;
      originalDistance_ = ScenePoint2D::DistancePtPt(event.GetPosition(0), event.GetPosition(1));
    }

    ScenePoint2D p;
    double zoom;

    if (event.GetPositionsCount() == 1 &&
        state_ == State_OneFinger)
    {
      p = event.GetPosition(0).Apply(originalCanvasToScene_);
      zoom = 1;
    }
    else if (event.GetPositionsCount() == 2)
    {
      if (state_ == State_TwoFingers)
      {
        p = GetCenter(event).Apply(originalCanvasToScene_);
      }
      else if (state_ == State_Upgraded)
      {
        p = event.GetPosition(0).Apply(originalCanvasToScene_);
      }
      else
      {
        state_ = State_Dead;
        return;
      }

      double distance = ScenePoint2D::DistancePtPt(event.GetPosition(0), event.GetPosition(1));
      zoom = distance / originalDistance_;
    }
    else
    {
      state_ = State_Dead;
      return;
    }

    {
      ViewportLocker locker(viewport_);

      if (locker.IsValid())
      {
        locker.GetController().SetSceneToCanvasTransform(
          AffineTransform2D::Combine(
            originalSceneToCanvas_,
            AffineTransform2D::CreateOffset(p.GetX(), p.GetY()),
            AffineTransform2D::CreateScaling(zoom),
            AffineTransform2D::CreateOffset(-pivot_.GetX(), -pivot_.GetY())));
        locker.Invalidate();
      }
    }
  }
}
