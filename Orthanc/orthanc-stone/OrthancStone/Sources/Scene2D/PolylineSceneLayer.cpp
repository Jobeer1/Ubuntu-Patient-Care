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


#include "PolylineSceneLayer.h"

#include <OrthancException.h>

#include <boost/math/constants/constants.hpp>

static const double PI = boost::math::constants::pi<double>();

namespace OrthancStone
{
  void PolylineSceneLayer::Copy(const PolylineSceneLayer& other)
  {
    items_ = other.items_;
    thickness_ = other.thickness_;
    revision_ ++;
  }

  
  ISceneLayer* PolylineSceneLayer::Clone() const
  {
    std::unique_ptr<PolylineSceneLayer> cloned(new PolylineSceneLayer);
    cloned->Copy(*this);
    return cloned.release();
  }
    

  void PolylineSceneLayer::SetThickness(double thickness)
  {
    if (thickness <= 0)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
    else
    {
      thickness_ = thickness;
      revision_++;
    }
  }


  void PolylineSceneLayer::AddChain(const Chain& chain,
                                    bool isClosed,
                                    uint8_t red,
                                    uint8_t green,
                                    uint8_t blue)
  {
    if (!chain.empty())
    {
      items_.push_back(Item());
      items_.back().chain_ = chain;
      items_.back().closed_ = isClosed;
      items_.back().color_ = Color(red, green, blue);

      revision_++;
    }
  }


  void PolylineSceneLayer::ClearAllChains()
  {
    items_.clear();
    revision_++;
  }

  const PolylineSceneLayer::Item& PolylineSceneLayer::GetItem(size_t i) const
  {
    if (i < items_.size())
    {
      return items_[i];
    }
    else
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
  }

  
  void PolylineSceneLayer::GetBoundingBox(Extent2D& target) const
  {
    target.Clear();

    for (size_t i = 0; i < items_.size(); i++)
    {
      for (size_t j = 0; j < items_[i].chain_.size(); j++)
      {
        const ScenePoint2D& p = items_[i].chain_[j];
        target.AddPoint(p.GetX(), p.GetY());
      }
    }
  }


  void PolylineSceneLayer::AddArc(double centerX,
                                  double centerY,
                                  double radiusX,
                                  double radiusY,
                                  double startAngle,
                                  double endAngle,
                                  Color color,
                                  unsigned int countSegments)
  {
    assert(countSegments != 0);

    if (endAngle >= startAngle)
    {
      double increment = (endAngle - startAngle) / static_cast<double>(countSegments - 1);

      Chain chain;
      chain.resize(countSegments);
        
      double theta = startAngle;
      for (unsigned int i = 0; i < countSegments; i++)
      {
        chain[i] = ScenePoint2D(centerX + radiusX * cos(theta),
                                centerY + radiusY * sin(theta));
        theta += increment;
      }
        
      AddChain(chain, false, color);
    }
  }


  void PolylineSceneLayer::AddCircle(double centerX,
                                     double centerY,
                                     double radius,
                                     Color color,
                                     unsigned int countSegments)
  {
    AddArc(centerX, centerY, radius, radius, 0, 2.0 * PI, color, countSegments);
  }
  

  void PolylineSceneLayer::AddRectangle(double x1,
                                        double y1,
                                        double x2,
                                        double y2,
                                        Color color)
  {
    Chain chain;
    chain.resize(4);
    chain[0] = ScenePoint2D(x1, y1);
    chain[1] = ScenePoint2D(x2, y1);
    chain[2] = ScenePoint2D(x2, y2);
    chain[3] = ScenePoint2D(x1, y2);
    AddChain(chain, true, color);
  }


  void PolylineSceneLayer::AddSegment(double x1,
                                      double y1,
                                      double x2,
                                      double y2,
                                      Color color)
  {
    Chain chain;
    chain.resize(2);
    chain[0] = ScenePoint2D(x1, y1);
    chain[1] = ScenePoint2D(x2, y2);
    AddChain(chain, false, color);
  }
}
