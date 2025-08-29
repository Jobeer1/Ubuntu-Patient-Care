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

#include "RotateSceneTracker.h"

#include "../Scene2DViewport/ViewportController.h"
#include "../Viewport/ViewportLocker.h"

namespace OrthancStone
{
  RotateSceneTracker::RotateSceneTracker(boost::weak_ptr<IViewport> viewport,
                                         const PointerEvent& event) :
    viewport_(viewport),
    click_(event.GetMainPosition()),
    referenceAngle_(0),
    isFirst_(true)
  {
    ViewportLocker locker(viewport_);
    
    if (locker.IsValid())
    {
      aligner_.reset(new Internals::FixedPointAligner(locker.GetController(), click_));
      originalSceneToCanvas_ = locker.GetController().GetSceneToCanvasTransform();
    }
  }

  
  void RotateSceneTracker::PointerMove(const PointerEvent& event,
                                       const Scene2D& scene)
  {
    if (aligner_.get() != NULL)
    {
      ScenePoint2D p = event.GetMainPosition();
      double dx = p.GetX() - click_.GetX();
      double dy = p.GetY() - click_.GetY();

      if (std::abs(dx) > 5.0 ||
          std::abs(dy) > 5.0)
      {
        double a = atan2(dy, dx);

        if (isFirst_)
        {
          referenceAngle_ = a;
          isFirst_ = false;
        }

        ViewportLocker locker(viewport_);
    
        if (locker.IsValid())
        {
          locker.GetController().SetSceneToCanvasTransform(
            AffineTransform2D::Combine(
              AffineTransform2D::CreateRotation(a - referenceAngle_),
              originalSceneToCanvas_));
          aligner_->Apply(locker.GetController());
          locker.Invalidate();
        }
      }
    }
  }

  
  void RotateSceneTracker::Cancel(const Scene2D& scene)
  {
    ViewportLocker locker(viewport_);
    
    if (locker.IsValid())
    {
      locker.GetController().SetSceneToCanvasTransform(originalSceneToCanvas_);
      locker.Invalidate();
    }
  }
}
