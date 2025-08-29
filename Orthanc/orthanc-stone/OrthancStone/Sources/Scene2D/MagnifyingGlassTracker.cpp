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


#include "MagnifyingGlassTracker.h"

#include "../Scene2DViewport/ViewportController.h"
#include "../Viewport/ViewportLocker.h"

namespace OrthancStone
{
  void MagnifyingGlassTracker::Update(const ViewportLocker& locker,
                                      const PointerEvent& event)
  {
    ScenePoint2D p = event.GetMainPosition().Apply(originalCanvasToScene_);

    locker.GetController().SetSceneToCanvasTransform(
      AffineTransform2D::Combine(
        originalSceneToCanvas_,
        AffineTransform2D::CreateOffset(p.GetX(), p.GetY()),
        AffineTransform2D::CreateScaling(5, 5),
        AffineTransform2D::CreateOffset(-pivot_.GetX(), -pivot_.GetY())));

    locker.Invalidate();
  }
    

  MagnifyingGlassTracker::MagnifyingGlassTracker(boost::weak_ptr<IViewport> viewport,
                                                 const PointerEvent& event) :
    viewport_(viewport)
  {
    ViewportLocker locker(viewport_);
    
    if (locker.IsValid())
    {
      originalSceneToCanvas_ = locker.GetController().GetSceneToCanvasTransform();
      originalCanvasToScene_ = locker.GetController().GetCanvasToSceneTransform();
      pivot_ = event.GetMainPosition().Apply(locker.GetController().GetCanvasToSceneTransform());

      Update(locker, event);
    }
  }
      

  void MagnifyingGlassTracker::PointerUp(const PointerEvent& event,
                                         const Scene2D& scene)
  {
    Cancel(scene);
    OneGesturePointerTracker::PointerUp(event, scene);
  }

  
  void MagnifyingGlassTracker::PointerMove(const PointerEvent& event,
                                           const Scene2D& scene)
  {
    ViewportLocker locker(viewport_);
    
    if (locker.IsValid())
    {
      Update(locker, event);
    }
  }
    

  void MagnifyingGlassTracker::Cancel(const Scene2D& scene)
  {
    ViewportLocker locker(viewport_);
    
    if (locker.IsValid())
    {
      locker.GetController().SetSceneToCanvasTransform(originalSceneToCanvas_);
      locker.Invalidate();
    }
  }
}
