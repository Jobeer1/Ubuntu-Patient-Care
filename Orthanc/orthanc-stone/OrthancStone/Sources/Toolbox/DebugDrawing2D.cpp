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


#include "DebugDrawing2D.h"

#include <stdio.h>


namespace OrthancStone
{
  class DebugDrawing2D::Segment
  {
  private:
    double       x1_;
    double       y1_;
    double       x2_;
    double       y2_;
    std::string  color_;
    bool         arrow_;

  public:
    Segment(double x1,
            double y1,
            double x2,
            double y2,
            const std::string& color,
            bool arrow) :
      x1_(x1),
      y1_(y1),
      x2_(x2),
      y2_(y2),
      color_(color),
      arrow_(arrow)
    {
    }

    double GetX1() const
    {
      return x1_;
    }

    double GetY1() const
    {
      return y1_;
    }

    double GetX2() const
    {
      return x2_;
    }

    double GetY2() const
    {
      return y2_;
    }

    const std::string& GetColor() const
    {
      return color_;
    }

    bool IsArrow() const
    {
      return arrow_;
    }
  };


  void DebugDrawing2D::AddSegment(double x1,
                                  double y1,
                                  double x2,
                                  double y2,
                                  const std::string& color,
                                  bool arrow,
                                  bool addToExtent)
  {
    if (addToExtent)
    {
      extent_.AddPoint(x1, y1);
      extent_.AddPoint(x2, y2);
    }

    segments_.push_back(Segment(x1, y1, x2, y2, color, arrow));
  }


  void DebugDrawing2D::SaveSvg(const std::string& path)
  {
    // Size in pixels
    float ww, hh;
    if (extent_.IsEmpty())
    {
      ww = 2048.0f;
      hh = 2048.0f;
    }
    else if (extent_.GetWidth() > extent_.GetHeight())
    {
      ww = 2048.0f;
      hh = ww * extent_.GetHeight() / extent_.GetWidth();
    }
    else
    {
      hh = 2048.0f;
      ww = hh * extent_.GetWidth() / extent_.GetHeight();
    }

    FILE* fp = fopen(path.c_str(), "w");
    fprintf(fp, "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\"?>\n");
    fprintf(fp, "<!DOCTYPE svg PUBLIC \"-//W3C//DTD SVG 1.1//EN\" \"http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd\">\n");
    fprintf(fp, "<svg width=\"%f\" height=\"%f\" viewBox=\"0 0 %f %f\" xmlns=\"http://www.w3.org/2000/svg\" xmlns:xlink=\"http://www.w3.org/1999/xlink\">\n", ww, hh, extent_.GetWidth(), extent_.GetHeight());

    // http://thenewcode.com/1068/Making-Arrows-in-SVG
    fprintf(fp, "<defs>\n");
    fprintf(fp, "<marker id=\"arrowhead\" markerWidth=\"2\" markerHeight=\"3\" \n");
    fprintf(fp, "refX=\"2\" refY=\"1.5\" orient=\"auto\">\n");
    fprintf(fp, "<polygon points=\"0 0, 2 1.5, 0 3\" />\n");
    fprintf(fp, "</marker>\n");
    fprintf(fp, "</defs>\n");

    fprintf(fp, "<rect fill=\"#fff\" stroke=\"#000\" x=\"0\" y=\"0\" width=\"%f\" height=\"%f\"/>\n", extent_.GetWidth(), extent_.GetHeight());

    for (std::list<Segment>::const_iterator it = segments_.begin(); it != segments_.end(); ++it)
    {
      float strokeWidth = 0.1;

      std::string s;
      if (it->IsArrow())
      {
        s = "marker-end=\"url(#arrowhead)\"";
      }

      fprintf(fp, "<line x1=\"%f\" y1=\"%f\" x2=\"%f\" y2=\"%f\" stroke=\"%s\" stroke-width=\"%f\" %s/>\n",
              it->GetX1() - extent_.GetX1(), it->GetY1() - extent_.GetY1(),
              it->GetX2() - extent_.GetX1(), it->GetY2() - extent_.GetY1(),
              it->GetColor().c_str(), strokeWidth, s.c_str());
    }

    fprintf(fp, "</svg>\n");

    fclose(fp);
  }
}
