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


#include "AnnotationsSceneLayer.h"

#include "MacroSceneLayer.h"
#include "PolylineSceneLayer.h"
#include "TextSceneLayer.h"
#include "TextureBaseSceneLayer.h"

#include <Images/ImageTraits.h>
#include <OrthancException.h>

#include <boost/math/constants/constants.hpp>
#include <list>

static const double PI = boost::math::constants::pi<double>();

static const double HANDLE_SIZE = 10.0;
static const double ARROW_LENGTH = 1.5 * HANDLE_SIZE;
static const double ARROW_ANGLE = 20.0 * PI / 180.0;

static const char* const KEY_ANNOTATIONS = "annotations";
static const char* const KEY_TYPE = "type";
static const char* const KEY_X = "x";
static const char* const KEY_Y = "y";
static const char* const KEY_X1 = "x1";
static const char* const KEY_Y1 = "y1";
static const char* const KEY_X2 = "x2";
static const char* const KEY_Y2 = "y2";
static const char* const KEY_X3 = "x3";
static const char* const KEY_Y3 = "y3";
static const char* const KEY_UNITS = "units";
static const char* const KEY_LABEL = "label";

static const char* const VALUE_ANGLE = "angle";
static const char* const VALUE_CIRCLE = "circle";
static const char* const VALUE_LENGTH = "length";
static const char* const VALUE_MILLIMETERS = "millimeters";
static const char* const VALUE_PIXELS = "pixels";
static const char* const VALUE_PIXEL_PROBE = "pixel-probe";
static const char* const VALUE_RECTANGLE_PROBE = "rectangle-probe";
static const char* const VALUE_ELLIPSE_PROBE = "ellipse-probe";
static const char* const VALUE_TEXT_ANNOTATION = "text";

#if 0
// Color codes that were used in Stone Web viewer <= 2.6
static OrthancStone::Color COLOR_PRIMITIVES(0x40, 0x82, 0xad);
static OrthancStone::Color COLOR_HOVER(0x40, 0xad, 0x79);
static OrthancStone::Color COLOR_TEXT(0x4e, 0xde, 0x99);   // This was replaced by COLOR_HOVER in 2.7
#endif


namespace OrthancStone
{
  class AnnotationsSceneLayer::Annotation : public boost::noncopyable
  {
  private:
    typedef std::list<GeometricPrimitive*>  GeometricPrimitives;

    AnnotationsSceneLayer&  that_;
    GeometricPrimitives     primitives_;
    Color                   color_;
    Color                   hoverColor_;

  public:
    explicit Annotation(AnnotationsSceneLayer& that) :
      that_(that),
      color_(that.GetColor()),
      hoverColor_(that.GetHoverColor())
    {
      that.AddAnnotation(this);
    }

    virtual ~Annotation()
    {
      for (GeometricPrimitives::iterator it = primitives_.begin(); it != primitives_.end(); ++it)
      {
        that_.DeletePrimitive(*it);
      }
    }

    AnnotationsSceneLayer& GetParentLayer() const
    {
      return that_;
    }

    GeometricPrimitive* AddPrimitive(GeometricPrimitive* primitive)
    {
      if (primitive == NULL)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_NullPointer);
      }
      else
      {
        assert(that_.primitives_.find(primitive) == that_.primitives_.end());
        primitives_.push_back(primitive);  // For automated deallocation
        that_.primitives_.insert(primitive);
        return primitive;
      }
    }

    const Color& GetColor() const
    {
      return color_;
    }

    const Color& GetHoverColor() const
    {
      return hoverColor_;
    }

    template <typename T>
    T& AddTypedPrimitive(T* primitive)
    {
      AddPrimitive(primitive);
      return *primitive;
    }

    virtual unsigned int GetHandlesCount() const = 0;

    virtual Handle& GetHandle(unsigned int index) const = 0;

    virtual void SignalMove(GeometricPrimitive& primitive,
                            const Scene2D& scene) = 0;

    virtual void UpdateProbe(const Scene2D& scene) = 0;

    virtual void Serialize(Json::Value& target) = 0;
  };


  class AnnotationsSceneLayer::GeometricPrimitive : public boost::noncopyable
  {
  private:
    bool         modified_;
    Annotation&  parentAnnotation_;
    Color        color_;
    Color        hoverColor_;
    bool         isHover_;
    int          depth_;

  public:
    GeometricPrimitive(Annotation& parentAnnotation,
                       int depth) :
      modified_(true),
      parentAnnotation_(parentAnnotation),
      color_(parentAnnotation.GetColor()),
      hoverColor_(parentAnnotation.GetHoverColor()),
      isHover_(false),
      depth_(depth)
    {
    }
      
    virtual ~GeometricPrimitive()
    {
    }

    Annotation& GetParentAnnotation() const
    {
      return parentAnnotation_;
    }
      
    int GetDepth() const
    {
      return depth_;
    }

    void SetHover(bool hover)
    {
      if (hover != isHover_)
      {
        isHover_ = hover;
        modified_ = true;
      }
    }

    bool IsHover() const
    {
      return isHover_;
    }
      
    void SetModified(bool modified)
    {
      modified_ = modified;
    }
      
    bool IsModified() const
    {
      return modified_;
    }

    void SetColor(const Color& color)
    {
      SetModified(true);
      color_ = color;
    }

    void SetHoverColor(const Color& color)
    {
      SetModified(true);
      hoverColor_ = color;
    }

    const Color& GetColor() const
    {
      return color_;
    }

    const Color& GetHoverColor() const
    {
      return hoverColor_;
    }
    
    Color GetActiveColor() const
    {
      return (IsHover() ? GetHoverColor() : GetColor());
    }

    virtual bool IsHit(const ScenePoint2D& p,
                       const Scene2D& scene) const = 0;

    // Always called, even if not modified
    virtual void RenderPolylineLayer(PolylineSceneLayer& polyline,
                                     const Scene2D& scene) = 0;

    // Only called if modified
    virtual void RenderOtherLayers(MacroSceneLayer& macro,
                                   const Scene2D& scene) = 0;

    virtual void MovePreview(const ScenePoint2D& delta,
                             const Scene2D& scene) = 0;

    virtual void MoveDone(const ScenePoint2D& delta,
                          const Scene2D& scene) = 0;
  };
    

  class AnnotationsSceneLayer::Handle : public GeometricPrimitive
  {
  public:
    enum Shape {
      Shape_Square,
      Shape_CrossedSquare,
      Shape_Circle,
      Shape_CrossedCircle,
      Shape_Invisible  /* to use in conjunction with arrows */
    };
    
  private:
    Shape         shape_;
    ScenePoint2D  center_;
    ScenePoint2D  delta_;

    void AddCross(PolylineSceneLayer& polyline,
                  double x1,
                  double y1,
                  double x2,
                  double y2)
    {
      const double halfX = (x1 + x2) / 2.0;
      const double halfY = (y1 + y2) / 2.0;
      polyline.AddSegment(x1, halfY, x2, halfY, GetActiveColor());
      polyline.AddSegment(halfX, y1, halfX, y2, GetActiveColor());
    }

  public:
    explicit Handle(Annotation& parentAnnotation,
                    Shape shape,
                    const ScenePoint2D& center) :
      GeometricPrimitive(parentAnnotation, 0),  // Highest priority
      shape_(shape),
      center_(center),
      delta_(0, 0)
    {
    }

    void SetSize(unsigned int size)
    {
      SetModified(true);
    }

    void SetCenter(const ScenePoint2D& center)
    {
      SetModified(true);
      center_ = center;
      delta_ = ScenePoint2D(0, 0);
    }

    void SetCenter(double x,
                   double y)
    {
      SetCenter(ScenePoint2D(x, y));
    }

    ScenePoint2D GetCenter() const
    {
      return center_ + delta_;
    }

    virtual bool IsHit(const ScenePoint2D& p,
                       const Scene2D& scene) const ORTHANC_OVERRIDE
    {
      const double zoom = scene.GetSceneToCanvasTransform().ComputeZoom();

      double dx = (center_.GetX() + delta_.GetX() - p.GetX()) * zoom;
      double dy = (center_.GetY() + delta_.GetY() - p.GetY()) * zoom;

      return (std::abs(dx) <= HANDLE_SIZE / 2.0 &&
              std::abs(dy) <= HANDLE_SIZE / 2.0);
    }

    virtual void RenderPolylineLayer(PolylineSceneLayer& polyline,
                                     const Scene2D& scene) ORTHANC_OVERRIDE
    {
      static unsigned int NUM_SEGMENTS = 16;

      const double zoom = scene.GetSceneToCanvasTransform().ComputeZoom();

      // TODO: take DPI into account
      const double unzoomedHandleSize = (HANDLE_SIZE / 2.0) / zoom;
      const double x = center_.GetX() + delta_.GetX();
      const double y = center_.GetY() + delta_.GetY();
      const double x1 = x - unzoomedHandleSize;
      const double y1 = y - unzoomedHandleSize;
      const double x2 = x + unzoomedHandleSize;
      const double y2 = y + unzoomedHandleSize;

      switch (shape_)
      {
        case Shape_Square:
          polyline.AddRectangle(x1, y1, x2, y2, GetActiveColor());
          break;
          
        case Shape_CrossedSquare:
          polyline.AddRectangle(x1, y1, x2, y2, GetActiveColor());
          AddCross(polyline, x1, y1, x2, y2);
          break;

        case Shape_Circle:
          polyline.AddCircle(x, y, unzoomedHandleSize, GetActiveColor(), NUM_SEGMENTS);
          break;
          
        case Shape_CrossedCircle:
          polyline.AddCircle(x, y, unzoomedHandleSize, GetActiveColor(), NUM_SEGMENTS);
          AddCross(polyline, x1, y1, x2, y2);
          break;

        case Shape_Invisible:
          break;
          
        default:
          throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
      }
    }
      
    virtual void RenderOtherLayers(MacroSceneLayer& macro,
                                   const Scene2D& scene) ORTHANC_OVERRIDE
    {
    }

    virtual void MovePreview(const ScenePoint2D& delta,
                             const Scene2D& scene) ORTHANC_OVERRIDE
    {
      SetModified(true);
      delta_ = delta;
      GetParentAnnotation().SignalMove(*this, scene);
    }

    virtual void MoveDone(const ScenePoint2D& delta,
                          const Scene2D& scene) ORTHANC_OVERRIDE
    {
      SetModified(true);
      center_ = center_ + delta;
      delta_ = ScenePoint2D(0, 0);
      GetParentAnnotation().SignalMove(*this, scene);
    }
  };

    
  class AnnotationsSceneLayer::Segment : public GeometricPrimitive
  {
  private:
    ScenePoint2D  p1_;
    ScenePoint2D  p2_;
    ScenePoint2D  delta_;
    bool          hasStartArrow_;
    bool          hasEndArrow_;
      
  public:
    Segment(Annotation& parentAnnotation,
            const ScenePoint2D& p1,
            const ScenePoint2D& p2) :
      GeometricPrimitive(parentAnnotation, 1),  // Can only be selected if no handle matches
      p1_(p1),
      p2_(p2),
      delta_(0, 0),
      hasStartArrow_(false),
      hasEndArrow_(false)
    {
    }

    Segment(Annotation& parentAnnotation,
            double x1,
            double y1,
            double x2,
            double y2) :
      GeometricPrimitive(parentAnnotation, 1),  // Can only be selected if no handle matches
      p1_(x1, y1),
      p2_(x2, y2),
      delta_(0, 0),
      hasStartArrow_(false),
      hasEndArrow_(false)
    {
    }

    void SetPosition(const ScenePoint2D& p1,
                     const ScenePoint2D& p2)
    {
      SetModified(true);
      p1_ = p1;
      p2_ = p2;
      delta_ = ScenePoint2D(0, 0);
    }

    void SetPosition(double x1,
                     double y1,
                     double x2,
                     double y2)
    {
      SetModified(true);
      p1_ = ScenePoint2D(x1, y1);
      p2_ = ScenePoint2D(x2, y2);
      delta_ = ScenePoint2D(0, 0);
    }

    ScenePoint2D GetPosition1() const
    {
      return p1_ + delta_;
    }

    ScenePoint2D GetPosition2() const
    {
      return p2_ + delta_;
    }

    void SetStartArrow(bool enabled)
    {
      SetModified(true);
      hasStartArrow_ = enabled;
    }

    bool HasStartArrow() const
    {
      return hasStartArrow_;
    }

    void SetEndArrow(bool enabled)
    {
      SetModified(true);
      hasEndArrow_ = enabled;
    }

    bool HasEndArrow() const
    {
      return hasEndArrow_;
    }

    virtual bool IsHit(const ScenePoint2D& p,
                       const Scene2D& scene) const ORTHANC_OVERRIDE
    {
      const double zoom = scene.GetSceneToCanvasTransform().ComputeZoom();
      return (ScenePoint2D::SquaredDistancePtSegment(p1_ + delta_, p2_ + delta_, p) * zoom * zoom <=
              (HANDLE_SIZE / 2.0) * (HANDLE_SIZE / 2.0));
    }

    virtual void RenderPolylineLayer(PolylineSceneLayer& polyline,
                                     const Scene2D& scene) ORTHANC_OVERRIDE
    {
      const Color color = GetActiveColor();
      const ScenePoint2D a(p1_ + delta_);
      const ScenePoint2D b(p2_ + delta_);
      
      polyline.AddSegment(a, b, color);
      
      if (hasStartArrow_ ||
          hasEndArrow_)
      {
        const double length = ARROW_LENGTH / scene.GetSceneToCanvasTransform().ComputeZoom();
        const double angle = atan2(b.GetY() - a.GetY(), b.GetX() - a.GetX());

        if (hasStartArrow_)
        {
          polyline.AddSegment(a, a + ScenePoint2D(
                                length * cos(angle + ARROW_ANGLE),
                              length * sin(angle + ARROW_ANGLE)), color);
          polyline.AddSegment(a, a + ScenePoint2D(
                                length * cos(angle - ARROW_ANGLE),
                                length * sin(angle - ARROW_ANGLE)), color);
        }

        if (hasEndArrow_)
        {
          polyline.AddSegment(b, b + ScenePoint2D(
                                length * cos(angle + ARROW_ANGLE + PI),
                                length * sin(angle + ARROW_ANGLE + PI)), color);
          polyline.AddSegment(b, b + ScenePoint2D(
                                length * cos(angle - ARROW_ANGLE + PI),
                                length * sin(angle - ARROW_ANGLE + PI)), color);
        }
      }
    }
      
    virtual void RenderOtherLayers(MacroSceneLayer& macro,
                                   const Scene2D& scene) ORTHANC_OVERRIDE
    {
    }

    virtual void MovePreview(const ScenePoint2D& delta,
                             const Scene2D& scene) ORTHANC_OVERRIDE
    {
      SetModified(true);
      delta_ = delta;
      GetParentAnnotation().SignalMove(*this, scene);
    }

    virtual void MoveDone(const ScenePoint2D& delta,
                          const Scene2D& scene) ORTHANC_OVERRIDE
    {
      SetModified(true);
      p1_ = p1_ + delta;
      p2_ = p2_ + delta;
      delta_ = ScenePoint2D(0, 0);
      GetParentAnnotation().SignalMove(*this, scene);
    }
  };

    
  class AnnotationsSceneLayer::Circle : public GeometricPrimitive
  {
  private:
    ScenePoint2D  p1_;
    ScenePoint2D  p2_;
    ScenePoint2D  delta_;
      
  public:
    Circle(Annotation& parentAnnotation,
           const ScenePoint2D& p1,
           const ScenePoint2D& p2) :
      GeometricPrimitive(parentAnnotation, 2),
      p1_(p1),
      p2_(p2),
      delta_(0, 0)
    {
    }

    void SetPosition(const ScenePoint2D& p1,
                     const ScenePoint2D& p2)
    {
      SetModified(true);
      p1_ = p1;
      p2_ = p2;
      delta_ = ScenePoint2D(0, 0);
    }

    ScenePoint2D GetPosition1() const
    {
      return p1_ + delta_;
    }

    ScenePoint2D GetPosition2() const
    {
      return p2_ + delta_;
    }

    virtual bool IsHit(const ScenePoint2D& p,
                       const Scene2D& scene) const ORTHANC_OVERRIDE
    {
      const double zoom = scene.GetSceneToCanvasTransform().ComputeZoom();

      ScenePoint2D middle((p1_.GetX() + p2_.GetX()) / 2.0,
                          (p1_.GetY() + p2_.GetY()) / 2.0);
        
      const double radius = ScenePoint2D::DistancePtPt(middle, p1_);
      const double distance = ScenePoint2D::DistancePtPt(middle, p - delta_);

      return std::abs(radius - distance) * zoom <= HANDLE_SIZE / 2.0;
    }

    virtual void RenderPolylineLayer(PolylineSceneLayer& polyline,
                                     const Scene2D& scene) ORTHANC_OVERRIDE
    {
      static unsigned int NUM_SEGMENTS = 128;

      ScenePoint2D center((p1_.GetX() + p2_.GetX()) / 2.0,
                          (p1_.GetY() + p2_.GetY()) / 2.0);
        
      const double radius = ScenePoint2D::DistancePtPt(center, p1_);

      polyline.AddCircle(center.GetX() + delta_.GetX(), center.GetY() + delta_.GetY(),
                         radius, GetActiveColor(), NUM_SEGMENTS);
    }
      
    virtual void RenderOtherLayers(MacroSceneLayer& macro,
                                   const Scene2D& scene) ORTHANC_OVERRIDE
    {
    }

    virtual void MovePreview(const ScenePoint2D& delta,
                             const Scene2D& scene) ORTHANC_OVERRIDE
    {
      SetModified(true);
      delta_ = delta;
      GetParentAnnotation().SignalMove(*this, scene);
    }

    virtual void MoveDone(const ScenePoint2D& delta,
                          const Scene2D& scene) ORTHANC_OVERRIDE
    {
      SetModified(true);
      p1_ = p1_ + delta;
      p2_ = p2_ + delta;
      delta_ = ScenePoint2D(0, 0);
      GetParentAnnotation().SignalMove(*this, scene);
    }
  };

    
  class AnnotationsSceneLayer::Arc : public GeometricPrimitive
  {
  private:
    ScenePoint2D  start_;
    ScenePoint2D  middle_;
    ScenePoint2D  end_;
    double        radius_;  // in pixels

    void ComputeAngles(double& fullAngle,
                       double& startAngle,
                       double& endAngle) const
    {
      const double x1 = start_.GetX();
      const double y1 = start_.GetY();
      const double xc = middle_.GetX();
      const double yc = middle_.GetY();
      const double x2 = end_.GetX();
      const double y2 = end_.GetY();

      double referenceAngle = atan2(y1 - yc, x1 - xc);
      double secondAngle = atan2(y2 - yc, x2 - xc);

      secondAngle -= referenceAngle;

      while (secondAngle >= PI)
      {
        secondAngle -= 2.0 * PI;
      }

      while (secondAngle <= -PI)
      {
        secondAngle += 2.0 * PI;
      }

      if (secondAngle < 0)
      {
        startAngle = referenceAngle + secondAngle;
        endAngle = referenceAngle;
      }
      else
      {
        startAngle = referenceAngle;
        endAngle = referenceAngle + secondAngle;
      }
      
      fullAngle = endAngle - startAngle;
    }
      
  public:
    Arc(Annotation& parentAnnotation,
        const ScenePoint2D& start,
        const ScenePoint2D& middle,
        const ScenePoint2D& end) :
      GeometricPrimitive(parentAnnotation, 2),
      start_(start),
      middle_(middle),
      end_(end),
      radius_(20)
    {
    }

    double GetAngle() const
    {
      double fullAngle, startAngle, endAngle;
      ComputeAngles(fullAngle, startAngle, endAngle);
      return fullAngle;
    }

    void SetStart(const ScenePoint2D& p)
    {
      SetModified(true);
      start_ = p;
    }

    void SetMiddle(const ScenePoint2D& p)
    {
      SetModified(true);
      middle_ = p;
    }

    void SetEnd(const ScenePoint2D& p)
    {
      SetModified(true);
      end_ = p;
    }

    virtual bool IsHit(const ScenePoint2D& p,
                       const Scene2D& scene) const ORTHANC_OVERRIDE
    {
      return false;
    }

    virtual void RenderPolylineLayer(PolylineSceneLayer& polyline,
                                     const Scene2D& scene) ORTHANC_OVERRIDE
    {
      static unsigned int NUM_SEGMENTS = 64;

      const double radius = radius_ / scene.GetSceneToCanvasTransform().ComputeZoom();

      double fullAngle, startAngle, endAngle;
      ComputeAngles(fullAngle, startAngle, endAngle);

      polyline.AddArc(middle_, radius, radius, startAngle, endAngle, GetActiveColor(), NUM_SEGMENTS);
    }
      
    virtual void RenderOtherLayers(MacroSceneLayer& macro,
                                   const Scene2D& scene) ORTHANC_OVERRIDE
    {
    }

    virtual void MovePreview(const ScenePoint2D& delta,
                             const Scene2D& scene) ORTHANC_OVERRIDE
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);  // No hit is possible
    }

    virtual void MoveDone(const ScenePoint2D& delta,
                          const Scene2D& scene) ORTHANC_OVERRIDE
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);  // No hit is possible
    }
  };

    
  class AnnotationsSceneLayer::Text : public GeometricPrimitive
  {
  private:
    AnnotationsSceneLayer&           that_;
    bool                             first_;
    size_t                           subLayer_;
    std::unique_ptr<TextSceneLayer>  content_;

  public:
    Text(AnnotationsSceneLayer& that,
         Annotation& parentAnnotation) :
      GeometricPrimitive(parentAnnotation, 2),
      that_(that),
      first_(true),
      subLayer_(0)  // dummy initialization
    {
    }

    virtual ~Text()
    {
      if (!first_)
      {
        that_.TagSubLayerToRemove(subLayer_);
      }
    }
      
    void SetContent(const TextSceneLayer& content)
    {
      SetModified(true);
      content_.reset(dynamic_cast<TextSceneLayer*>(content.Clone()));
    }

    void SetText(const std::string& text)
    {
      if (content_.get() == NULL)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
      }
      else
      {
        SetModified(true);
        content_->SetText(text);
      }
    }

    std::string GetText() const
    {
      return content_->GetText();
    }

    void SetPosition(double x,
                     double y)
    {
      if (content_.get() == NULL)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
      }
      else
      {
        SetModified(true);
        content_->SetPosition(x, y);
      }
    }

    virtual bool IsHit(const ScenePoint2D& p,
                       const Scene2D& scene) const ORTHANC_OVERRIDE
    {
      return false;
    }

    virtual void RenderPolylineLayer(PolylineSceneLayer& polyline,
                                     const Scene2D& scene) ORTHANC_OVERRIDE
    {
    }
      
    virtual void RenderOtherLayers(MacroSceneLayer& macro,
                                   const Scene2D& scene) ORTHANC_OVERRIDE
    {
      if (content_.get() != NULL)
      {
        std::unique_ptr<TextSceneLayer> layer(reinterpret_cast<TextSceneLayer*>(content_->Clone()));

        layer->SetColor(GetActiveColor());
          
        if (first_)
        {
          subLayer_ = macro.AddLayer(layer.release());
          first_ = false;
        }
        else
        {
          macro.UpdateLayer(subLayer_, layer.release());
        }
      }
    }

    virtual void MovePreview(const ScenePoint2D& delta,
                             const Scene2D& scene) ORTHANC_OVERRIDE
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);  // No hit is possible
    }

    virtual void MoveDone(const ScenePoint2D& delta,
                          const Scene2D& scene) ORTHANC_OVERRIDE
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);  // No hit is possible
    }
  };


  class AnnotationsSceneLayer::Ellipse : public GeometricPrimitive
  {
  private:
    ScenePoint2D  p1_;
    ScenePoint2D  p2_;
    ScenePoint2D  delta_;

    double GetCenterX() const
    {
      return (p1_.GetX() + p2_.GetX()) / 2.0 + delta_.GetX();
    }

    double GetCenterY() const
    {
      return (p1_.GetY() + p2_.GetY()) / 2.0 + delta_.GetY();
    }

    double GetRadiusX() const
    {
      return std::abs(p1_.GetX() - p2_.GetX()) / 2.0;
    }

    double GetRadiusY() const
    {
      return std::abs(p1_.GetY() - p2_.GetY()) / 2.0;
    }
    
  public:
    Ellipse(Annotation& parentAnnotation,
            const ScenePoint2D& p1,
            const ScenePoint2D& p2) :
      GeometricPrimitive(parentAnnotation, 2),
      p1_(p1),
      p2_(p2),
      delta_(0, 0)
    {
    }

    void SetPosition(const ScenePoint2D& p1,
                     const ScenePoint2D& p2)
    {
      SetModified(true);
      p1_ = p1;
      p2_ = p2;
      delta_ = ScenePoint2D(0, 0);
    }

    ScenePoint2D GetPosition1() const
    {
      return p1_ + delta_;
    }

    ScenePoint2D GetPosition2() const
    {
      return p2_ + delta_;
    }

    double GetArea() const
    {
      return PI * GetRadiusX() * GetRadiusY();
    }

    bool IsPointInside(const ScenePoint2D& p) const
    {
      const double radiusX = GetRadiusX();
      const double radiusY = GetRadiusY();

      double a, b, x, y;
      
      if (radiusX > radiusY)
      {
        // The ellipse is horizontal => we are in the case described
        // on Wikipedia:
        // https://en.wikipedia.org/wiki/Ellipse#Standard_equation

        a = radiusX;
        b = radiusY;
        x = p.GetX() - GetCenterX();
        y = p.GetY() - GetCenterY();
      }
      else
      {
        a = radiusY;
        b = radiusX;
        x = p.GetY() - GetCenterY();
        y = p.GetX() - GetCenterX();
      }
      
      const double c = sqrt(a * a - b * b);

      return (sqrt((x - c) * (x - c) + y * y) +
              sqrt((x + c) * (x + c) + y * y)) <= 2.0 * a;
    }
    
    virtual bool IsHit(const ScenePoint2D& p,
                       const Scene2D& scene) const ORTHANC_OVERRIDE
    {
      const double zoom = scene.GetSceneToCanvasTransform().ComputeZoom();

      const double radiusX = GetRadiusX();
      const double radiusY = GetRadiusY();

      // Warning: This is only an approximation of the
      // point-to-ellipse distance, as explained here:
      // https://blog.chatfield.io/simple-method-for-distance-to-ellipse/
      
      const double x = (p.GetX() - GetCenterX()) / radiusX;
      const double y = (p.GetY() - GetCenterY()) / radiusY;
      const double t = atan2(y, x);
      const double xx = cos(t) - x;
      const double yy = sin(t) - y;

      const double approximateDistance = sqrt(xx * xx + yy * yy) * (radiusX + radiusY) / 2.0;
      return std::abs(approximateDistance) * zoom <= HANDLE_SIZE / 2.0;
    }

    virtual void RenderPolylineLayer(PolylineSceneLayer& polyline,
                                     const Scene2D& scene) ORTHANC_OVERRIDE
    {
      static unsigned int NUM_SEGMENTS = 128;
      polyline.AddArc(GetCenterX(), GetCenterY(), GetRadiusX(), GetRadiusY(), 0, 2.0 * PI, GetActiveColor(), NUM_SEGMENTS);
    }
      
    virtual void RenderOtherLayers(MacroSceneLayer& macro,
                                   const Scene2D& scene) ORTHANC_OVERRIDE
    {
    }

    virtual void MovePreview(const ScenePoint2D& delta,
                             const Scene2D& scene) ORTHANC_OVERRIDE
    {
      SetModified(true);
      delta_ = delta;
      GetParentAnnotation().SignalMove(*this, scene);
    }

    virtual void MoveDone(const ScenePoint2D& delta,
                          const Scene2D& scene) ORTHANC_OVERRIDE
    {
      SetModified(true);
      p1_ = p1_ + delta;
      p2_ = p2_ + delta;
      delta_ = ScenePoint2D(0, 0);
      GetParentAnnotation().SignalMove(*this, scene);
    }
  };

    
  class AnnotationsSceneLayer::EditPrimitiveTracker : public IFlexiblePointerTracker
  {
  private:
    AnnotationsSceneLayer&  that_;
    GeometricPrimitive&     primitive_;
    ScenePoint2D            sceneClick_;
    AffineTransform2D       canvasToScene_;
    bool                    alive_;
      
  public:
    EditPrimitiveTracker(AnnotationsSceneLayer& that,
                         GeometricPrimitive& primitive,
                         const ScenePoint2D& sceneClick,
                         const AffineTransform2D& canvasToScene) :
      that_(that),
      primitive_(primitive),
      sceneClick_(sceneClick),
      canvasToScene_(canvasToScene),
      alive_(true)
    {
    }

    virtual void PointerMove(const PointerEvent& event,
                             const Scene2D& scene) ORTHANC_OVERRIDE
    {
      primitive_.MovePreview(event.GetMainPosition().Apply(canvasToScene_) - sceneClick_, scene);
      that_.BroadcastMessage(AnnotationChangedMessage(that_));
    }
      
    virtual void PointerUp(const PointerEvent& event,
                           const Scene2D& scene) ORTHANC_OVERRIDE
    {
      primitive_.MoveDone(event.GetMainPosition().Apply(canvasToScene_) - sceneClick_, scene);
      alive_ = false;
      that_.BroadcastMessage(AnnotationChangedMessage(that_));
    }

    virtual void PointerDown(const PointerEvent& event,
                             const Scene2D& scene) ORTHANC_OVERRIDE
    {
    }

    virtual bool IsAlive() const ORTHANC_OVERRIDE
    {
      return alive_;
    }

    virtual void Cancel(const Scene2D& scene) ORTHANC_OVERRIDE
    {
      //primitive_.MoveDone(ScenePoint2D(0, 0), scene);
      primitive_.MoveDone(sceneClick_, scene);   // TODO Check this
    }
  };


  class AnnotationsSceneLayer::SegmentAnnotation : public Annotation
  {
  private:
    Handle&   handle1_;
    Handle&   handle2_;
    Segment&  segment_;
    Text&     label_;

  protected:
    void SetLabelContent(const TextSceneLayer& content)
    {
      label_.SetContent(content);
    }

    std::string GetCurrentLabel() const
    {
      return label_.GetText();
    } 

    const Handle& GetHandle1() const
    {
      return handle1_;
    }

    const Handle& GetHandle2() const
    {
      return handle2_;
    }

    void SetStartArrow(bool enabled)
    {
      segment_.SetStartArrow(enabled);
    }

    void SetEndArrow(bool enabled)
    {
      segment_.SetEndArrow(enabled);
    }

  public:
    SegmentAnnotation(AnnotationsSceneLayer& that,
                      Handle::Shape shape1,
                      const ScenePoint2D& p1,
                      Handle::Shape shape2,
                      const ScenePoint2D& p2) :
      Annotation(that),
      handle1_(AddTypedPrimitive<Handle>(new Handle(*this, shape1, p1))),
      handle2_(AddTypedPrimitive<Handle>(new Handle(*this, shape2, p2))),
      segment_(AddTypedPrimitive<Segment>(new Segment(*this, p1, p2))),
      label_(AddTypedPrimitive<Text>(new Text(that, *this)))
    {
      label_.SetColor(that.GetHoverColor());
    }

    virtual unsigned int GetHandlesCount() const ORTHANC_OVERRIDE
    {
      return 2;
    }

    virtual Handle& GetHandle(unsigned int index) const ORTHANC_OVERRIDE
    {
      switch (index)
      {
        case 0:
          return handle1_;

        case 1:
          return handle2_;

        default:
          throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
      }
    }

    virtual void SignalMove(GeometricPrimitive& primitive,
                            const Scene2D& scene) ORTHANC_OVERRIDE
    {
      if (&primitive == &handle1_ ||
          &primitive == &handle2_)
      {
        segment_.SetPosition(handle1_.GetCenter(), handle2_.GetCenter());
      }
      else if (&primitive == &segment_)
      {
        handle1_.SetCenter(segment_.GetPosition1());
        handle2_.SetCenter(segment_.GetPosition2());
      }
      else
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
      }
    }

    virtual void UpdateProbe(const Scene2D& scene) ORTHANC_OVERRIDE
    {
    }
  };


  class AnnotationsSceneLayer::LengthAnnotation : public SegmentAnnotation
  {
  private:
    Units  units_;
    bool   showLabel_;

    void UpdateLabel()
    {
      if (showLabel_)
      {
        TextSceneLayer content;

        double x1 = GetHandle1().GetCenter().GetX();
        double y1 = GetHandle1().GetCenter().GetY();
        double x2 = GetHandle2().GetCenter().GetX();
        double y2 = GetHandle2().GetCenter().GetY();
        
        // Put the label to the right of the right-most handle
        if (x1 < x2)
        {
          content.SetPosition(x2, y2);
        }
        else
        {
          content.SetPosition(x1, y1);
        }

        content.SetAnchor(BitmapAnchor_CenterLeft);
        content.SetBorder(10);

        double dx = x1 - x2;
        double dy = y1 - y2;
        char buf[32];

        switch (units_)
        {
          case Units_Millimeters:
            sprintf(buf, "%0.2f cm", sqrt(dx * dx + dy * dy) / 10.0);
            break;

          case Units_Pixels:
            sprintf(buf, "%0.1f px", sqrt(dx * dx + dy * dy));
            break;

          default:
            throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
        }
            
        content.SetText(buf);

        SetLabelContent(content);
      }
    }

  public:
    LengthAnnotation(AnnotationsSceneLayer& that,
                     Units units,
                     bool showLabel,
                     const ScenePoint2D& p1,
                     const ScenePoint2D& p2) :
      SegmentAnnotation(that, Handle::Shape_Square, p1, Handle::Shape_Square, p2),
      units_(units),
      showLabel_(showLabel)
    {
      UpdateLabel();
    }

    virtual void SignalMove(GeometricPrimitive& primitive,
                            const Scene2D& scene) ORTHANC_OVERRIDE
    {
      SegmentAnnotation::SignalMove(primitive, scene);
      UpdateLabel();
    }

    virtual void Serialize(Json::Value& target) ORTHANC_OVERRIDE
    {
      target = Json::objectValue;
      target[KEY_TYPE] = VALUE_LENGTH;
      target[KEY_X1] = GetHandle1().GetCenter().GetX();
      target[KEY_Y1] = GetHandle1().GetCenter().GetY();
      target[KEY_X2] = GetHandle2().GetCenter().GetX();
      target[KEY_Y2] = GetHandle2().GetCenter().GetY();
    }

    static void Unserialize(AnnotationsSceneLayer& target,
                            Units units,
                            const Json::Value& source)
    {
      if (source.isMember(KEY_X1) &&
          source.isMember(KEY_Y1) &&
          source.isMember(KEY_X2) &&
          source.isMember(KEY_Y2) &&
          source[KEY_X1].isNumeric() &&
          source[KEY_Y1].isNumeric() &&
          source[KEY_X2].isNumeric() &&
          source[KEY_Y2].isNumeric())
      {
        new LengthAnnotation(target, units, true,
                             ScenePoint2D(source[KEY_X1].asDouble(), source[KEY_Y1].asDouble()),
                             ScenePoint2D(source[KEY_X2].asDouble(), source[KEY_Y2].asDouble()));
      }
      else
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat, "Cannot unserialize a length annotation");
      }
    }
  };


  class AnnotationsSceneLayer::TextAnnotation : public SegmentAnnotation
  {
  public:
    TextAnnotation(AnnotationsSceneLayer& that,
                   const std::string& label,
                   const ScenePoint2D& pointedPosition,
                   const ScenePoint2D& labelPosition) :
      SegmentAnnotation(that, Handle::Shape_Invisible, pointedPosition /* p1 */,
                        Handle::Shape_Square, labelPosition /* p2 */)
    {
      SetStartArrow(true);
      UpdateLabel(label);
    }

    ScenePoint2D GetPointedPosition() const
    {
      return GetHandle1().GetCenter();
    }

    ScenePoint2D GetLabelPosition() const
    {
      return GetHandle2().GetCenter();
    }

    void UpdateLabel(const std::string& label)
    {
      TextSceneLayer content;

      double x1 = GetHandle1().GetCenter().GetX();
      double x2 = GetHandle2().GetCenter().GetX();
      double y2 = GetHandle2().GetCenter().GetY();
        
      if (x1 < x2)
      {
        content.SetAnchor(BitmapAnchor_CenterLeft);
      }
      else
      {
        content.SetAnchor(BitmapAnchor_CenterRight);
      }

      content.SetPosition(x2, y2);
      content.SetBorder(10);
      content.SetText(label);

      SetLabelContent(content);
    }

    void UpdateLabel()
    {
      UpdateLabel(GetCurrentLabel());
    }
    
    virtual void SignalMove(GeometricPrimitive& primitive,
                            const Scene2D& scene) ORTHANC_OVERRIDE
    {
      SegmentAnnotation::SignalMove(primitive, scene);
      UpdateLabel();
    }

    virtual void Serialize(Json::Value& target) ORTHANC_OVERRIDE
    {
      target = Json::objectValue;
      target[KEY_TYPE] = VALUE_TEXT_ANNOTATION;
      target[KEY_X1] = GetHandle1().GetCenter().GetX();
      target[KEY_Y1] = GetHandle1().GetCenter().GetY();
      target[KEY_X2] = GetHandle2().GetCenter().GetX();
      target[KEY_Y2] = GetHandle2().GetCenter().GetY();
      target[KEY_LABEL] = GetCurrentLabel();
    }

    static void Unserialize(AnnotationsSceneLayer& target,
                            const Json::Value& source)
    {
      if (source.isMember(KEY_X1) &&
          source.isMember(KEY_Y1) &&
          source.isMember(KEY_X2) &&
          source.isMember(KEY_Y2) &&
          source.isMember(KEY_LABEL) &&
          source[KEY_X1].isNumeric() &&
          source[KEY_Y1].isNumeric() &&
          source[KEY_X2].isNumeric() &&
          source[KEY_Y2].isNumeric() &&
          source[KEY_LABEL].isString())
      {
        new TextAnnotation(target, source[KEY_LABEL].asString(),
                           ScenePoint2D(source[KEY_X1].asDouble(), source[KEY_Y1].asDouble()),
                           ScenePoint2D(source[KEY_X2].asDouble(), source[KEY_Y2].asDouble()));
      }
      else
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat, "Cannot unserialize a text annotation");
      }
    }
  };


  // Use this class to avoid unnecessary probing if neither the scene,
  // nor the probe, has changed
  class AnnotationsSceneLayer::ProbingAnnotation : public Annotation
  {
  private:
    int       probedLayer_;
    bool      probeChanged_;
    uint64_t  lastLayerRevision_;

  protected:
    virtual void UpdateProbeForLayer(const ISceneLayer& layer) = 0;

    void TagProbeAsChanged()
    {
      probeChanged_ = true;
    }

  public:
    explicit ProbingAnnotation(AnnotationsSceneLayer& that) :
      Annotation(that),
      probedLayer_(that.GetProbedLayer()),
      probeChanged_(true),
      lastLayerRevision_(0)
    {
    }

    virtual void UpdateProbe(const Scene2D& scene) ORTHANC_OVERRIDE
    {
      if (scene.HasLayer(probedLayer_))
      {
        const ISceneLayer& layer = scene.GetLayer(probedLayer_);
        if (probeChanged_ ||
            layer.GetRevision() != lastLayerRevision_)
        {
          UpdateProbeForLayer(layer);
          probeChanged_ = false;
          lastLayerRevision_ = layer.GetRevision();
        }
      }
    }
  };

    
  class AnnotationsSceneLayer::PixelProbeAnnotation : public ProbingAnnotation
  {
  private:
    Handle&   handle_;
    Text&     label_;

  protected:
    virtual void UpdateProbeForLayer(const ISceneLayer& layer) ORTHANC_OVERRIDE
    {
      if (layer.GetType() == ISceneLayer::Type_FloatTexture ||
          layer.GetType() == ISceneLayer::Type_ColorTexture)
      {
        const TextureBaseSceneLayer& texture = dynamic_cast<const TextureBaseSceneLayer&>(layer);
        const AffineTransform2D sceneToTexture = AffineTransform2D::Invert(texture.GetTransform());

        double sceneX = handle_.GetCenter().GetX();
        double sceneY = handle_.GetCenter().GetY();
        sceneToTexture.Apply(sceneX, sceneY);
          
        int x = static_cast<int>(std::floor(sceneX));
        int y = static_cast<int>(std::floor(sceneY));

        const Orthanc::ImageAccessor& image = texture.GetTexture();
        
        if (x >= 0 &&
            y >= 0 &&
            x < static_cast<int>(image.GetWidth()) &&
            y < static_cast<int>(image.GetHeight()))
        {
          char buf[64];

          switch (image.GetFormat())
          {
            case Orthanc::PixelFormat_Float32:
              sprintf(buf, "(%d,%d): %.01f", x, y, Orthanc::ImageTraits<Orthanc::PixelFormat_Float32>::GetFloatPixel(
                        image, static_cast<unsigned int>(x), static_cast<unsigned int>(y)));
              break;

            case Orthanc::PixelFormat_RGB24:
            {
              Orthanc::PixelTraits<Orthanc::PixelFormat_RGB24>::PixelType pixel;
              Orthanc::ImageTraits<Orthanc::PixelFormat_RGB24>::GetPixel(
                pixel, image, static_cast<unsigned int>(x), static_cast<unsigned int>(y));
              sprintf(buf, "(%d,%d): (%d,%d,%d)", x, y, pixel.red_, pixel.green_, pixel.blue_);
              break;
            }

            default:
              break;
          }
          
          label_.SetText(buf);
        }
        else
        {
          label_.SetText("?");
        }
      }
    }

  public:
    PixelProbeAnnotation(AnnotationsSceneLayer& that,
                         const ScenePoint2D& p) :
      ProbingAnnotation(that),
      handle_(AddTypedPrimitive<Handle>(new Handle(*this, Handle::Shape_CrossedSquare, p))),
      label_(AddTypedPrimitive<Text>(new Text(that, *this)))
    {
      TextSceneLayer content;
      content.SetPosition(handle_.GetCenter().GetX(), handle_.GetCenter().GetY());
      content.SetAnchor(BitmapAnchor_CenterLeft);
      content.SetBorder(10);
      content.SetText("?");

      label_.SetContent(content);      
      label_.SetColor(that.GetHoverColor());
    }

    virtual unsigned int GetHandlesCount() const ORTHANC_OVERRIDE
    {
      return 1;
    }

    virtual Handle& GetHandle(unsigned int index) const ORTHANC_OVERRIDE
    {
      if (index == 0)
      {
        return handle_;
      }
      else
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
      }
    }

    virtual void SignalMove(GeometricPrimitive& primitive,
                            const Scene2D& scene) ORTHANC_OVERRIDE
    {
      label_.SetPosition(handle_.GetCenter().GetX(), handle_.GetCenter().GetY());
      TagProbeAsChanged();
    }

    virtual void Serialize(Json::Value& target) ORTHANC_OVERRIDE
    {
      target = Json::objectValue;
      target[KEY_TYPE] = VALUE_PIXEL_PROBE;
      target[KEY_X] = handle_.GetCenter().GetX();
      target[KEY_Y] = handle_.GetCenter().GetY();
    }

    static void Unserialize(AnnotationsSceneLayer& target,
                            const Json::Value& source)
    {
      if (source.isMember(KEY_X) &&
          source.isMember(KEY_Y) &&
          source[KEY_X].isNumeric() &&
          source[KEY_Y].isNumeric())
      {
        new PixelProbeAnnotation(target, ScenePoint2D(source[KEY_X].asDouble(), source[KEY_Y].asDouble()));
      }
      else
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat, "Cannot unserialize a pixel probe");
      }
    }
  };

    
  class AnnotationsSceneLayer::AngleAnnotation : public Annotation
  {
  private:
    Handle&   startHandle_;
    Handle&   middleHandle_;
    Handle&   endHandle_;
    Segment&  segment1_;
    Segment&  segment2_;
    Arc&      arc_;
    Text&     label_;

    void UpdateLabel()
    {
      TextSceneLayer content;

      const double x1 = startHandle_.GetCenter().GetX();
      const double x2 = middleHandle_.GetCenter().GetX();
      const double y2 = middleHandle_.GetCenter().GetY();
      const double x3 = endHandle_.GetCenter().GetX();
        
      if (x2 < x1 &&
          x2 < x3)
      {
        content.SetAnchor(BitmapAnchor_CenterRight);
      }
      else
      {
        content.SetAnchor(BitmapAnchor_CenterLeft);
      }

      content.SetPosition(x2, y2);
      content.SetBorder(10);

      char buf[32];
      sprintf(buf, "%.01f%c%c", std::abs(arc_.GetAngle()) / PI * 180.0,
              0xc2, 0xb0 /* two bytes corresponding to degree symbol in UTF-8 */);
      content.SetText(buf);

      label_.SetContent(content);
    }

  public:
    AngleAnnotation(AnnotationsSceneLayer& that,
                    const ScenePoint2D& start,
                    const ScenePoint2D& middle,
                    const ScenePoint2D& end) :
      Annotation(that),
      startHandle_(AddTypedPrimitive<Handle>(new Handle(*this, Handle::Shape_Square, start))),
      middleHandle_(AddTypedPrimitive<Handle>(new Handle(*this, Handle::Shape_Square, middle))),
      endHandle_(AddTypedPrimitive<Handle>(new Handle(*this, Handle::Shape_Square, end))),
      segment1_(AddTypedPrimitive<Segment>(new Segment(*this, start, middle))),
      segment2_(AddTypedPrimitive<Segment>(new Segment(*this, middle, end))),
      arc_(AddTypedPrimitive<Arc>(new Arc(*this, start, middle, end))),
      label_(AddTypedPrimitive<Text>(new Text(that, *this)))
    {
      label_.SetColor(that.GetHoverColor());
      UpdateLabel();
    }

    virtual unsigned int GetHandlesCount() const ORTHANC_OVERRIDE
    {
      return 3;
    }

    virtual Handle& GetHandle(unsigned int index) const ORTHANC_OVERRIDE
    {
      switch (index)
      {
        case 0:
          return startHandle_;

        case 1:
          return middleHandle_;

        case 2:
          return endHandle_;

        default:
          throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
      }
    }

    virtual void SignalMove(GeometricPrimitive& primitive,
                            const Scene2D& scene) ORTHANC_OVERRIDE
    {
      if (&primitive == &startHandle_)
      {
        segment1_.SetPosition(startHandle_.GetCenter(), middleHandle_.GetCenter());
        arc_.SetStart(startHandle_.GetCenter());
      }
      else if (&primitive == &middleHandle_)
      {
        segment1_.SetPosition(startHandle_.GetCenter(), middleHandle_.GetCenter());
        segment2_.SetPosition(middleHandle_.GetCenter(), endHandle_.GetCenter());
        arc_.SetMiddle(middleHandle_.GetCenter());
      }
      else if (&primitive == &endHandle_)
      {
        segment2_.SetPosition(middleHandle_.GetCenter(), endHandle_.GetCenter());
        arc_.SetEnd(endHandle_.GetCenter());
      }
      else if (&primitive == &segment1_)
      {
        startHandle_.SetCenter(segment1_.GetPosition1());
        middleHandle_.SetCenter(segment1_.GetPosition2());
        segment2_.SetPosition(segment1_.GetPosition2(), segment2_.GetPosition2());
        arc_.SetStart(segment1_.GetPosition1());
        arc_.SetMiddle(segment1_.GetPosition2());
      }
      else if (&primitive == &segment2_)
      {
        middleHandle_.SetCenter(segment2_.GetPosition1());
        endHandle_.SetCenter(segment2_.GetPosition2());
        segment1_.SetPosition(segment1_.GetPosition1(), segment2_.GetPosition1());
        arc_.SetMiddle(segment2_.GetPosition1());
        arc_.SetEnd(segment2_.GetPosition2());
      }
      else
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
      }

      UpdateLabel();
    }

    virtual void UpdateProbe(const Scene2D& scene) ORTHANC_OVERRIDE
    {
    }
    
    virtual void Serialize(Json::Value& target) ORTHANC_OVERRIDE
    {
      target = Json::objectValue;
      target[KEY_TYPE] = VALUE_ANGLE;
      target[KEY_X1] = startHandle_.GetCenter().GetX();
      target[KEY_Y1] = startHandle_.GetCenter().GetY();
      target[KEY_X2] = middleHandle_.GetCenter().GetX();
      target[KEY_Y2] = middleHandle_.GetCenter().GetY();
      target[KEY_X3] = endHandle_.GetCenter().GetX();
      target[KEY_Y3] = endHandle_.GetCenter().GetY();
    }

    static void Unserialize(AnnotationsSceneLayer& target,
                            const Json::Value& source)
    {
      if (source.isMember(KEY_X1) &&
          source.isMember(KEY_Y1) &&
          source.isMember(KEY_X2) &&
          source.isMember(KEY_Y2) &&
          source.isMember(KEY_X3) &&
          source.isMember(KEY_Y3) &&
          source[KEY_X1].isNumeric() &&
          source[KEY_Y1].isNumeric() &&
          source[KEY_X2].isNumeric() &&
          source[KEY_Y2].isNumeric() &&
          source[KEY_X3].isNumeric() &&
          source[KEY_Y3].isNumeric())
      {
        new AngleAnnotation(target,
                            ScenePoint2D(source[KEY_X1].asDouble(), source[KEY_Y1].asDouble()),
                            ScenePoint2D(source[KEY_X2].asDouble(), source[KEY_Y2].asDouble()),
                            ScenePoint2D(source[KEY_X3].asDouble(), source[KEY_Y3].asDouble()));
      }
      else
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat, "Cannot unserialize an angle annotation");
      }
    }
  };

    
  class AnnotationsSceneLayer::CircleAnnotation : public Annotation
  {
  private:
    Units     units_;
    Handle&   handle1_;
    Handle&   handle2_;
    Segment&  segment_;
    Circle&   circle_;
    Text&     label_;

    void UpdateLabel()
    {
      TextSceneLayer content;

      double x1 = handle1_.GetCenter().GetX();
      double y1 = handle1_.GetCenter().GetY();
      double x2 = handle2_.GetCenter().GetX();
      double y2 = handle2_.GetCenter().GetY();
        
      // Put the label to the right of the right-most handle
      if (x1 < x2)
      {
        content.SetPosition(x2, y2);
      }
      else
      {
        content.SetPosition(x1, y1);
      }

      content.SetAnchor(BitmapAnchor_CenterLeft);
      content.SetBorder(10);

      double dx = x1 - x2;
      double dy = y1 - y2;
      double diameter = sqrt(dx * dx + dy * dy);  // in millimeters

      double area = PI * diameter * diameter / 4.0;
        
      char buf[32];

      switch (units_)
      {
        case Units_Millimeters:
          sprintf(buf, "%0.2f cm\n%0.2f cm%c%c",
                  diameter / 10.0,
                  area / 100.0,
                  0xc2, 0xb2 /* two bytes corresponding to two power in UTF-8 */);
          break;

        case Units_Pixels:
          // Don't report area (pixel-times-pixel is a strange unit)
          sprintf(buf, "%0.1f px", diameter);
          break;
          
        default:
          throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
      }

      content.SetText(buf);

      label_.SetContent(content);
    }

  public:
    CircleAnnotation(AnnotationsSceneLayer& that,
                     Units units,
                     const ScenePoint2D& p1,
                     const ScenePoint2D& p2) :
      Annotation(that),
      units_(units),
      handle1_(AddTypedPrimitive<Handle>(new Handle(*this, Handle::Shape_Square, p1))),
      handle2_(AddTypedPrimitive<Handle>(new Handle(*this, Handle::Shape_Square, p2))),
      segment_(AddTypedPrimitive<Segment>(new Segment(*this, p1, p2))),
      circle_(AddTypedPrimitive<Circle>(new Circle(*this, p1, p2))),
      label_(AddTypedPrimitive<Text>(new Text(that, *this)))
    {
      label_.SetColor(that.GetHoverColor());
      UpdateLabel();
    }

    virtual unsigned int GetHandlesCount() const ORTHANC_OVERRIDE
    {
      return 2;
    }

    virtual Handle& GetHandle(unsigned int index) const ORTHANC_OVERRIDE
    {
      switch (index)
      {
        case 0:
          return handle1_;

        case 1:
          return handle2_;

        default:
          throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
      }
    }

    virtual void SignalMove(GeometricPrimitive& primitive,
                            const Scene2D& scene) ORTHANC_OVERRIDE
    {
      if (&primitive == &handle1_ ||
          &primitive == &handle2_)
      {
        segment_.SetPosition(handle1_.GetCenter(), handle2_.GetCenter());
        circle_.SetPosition(handle1_.GetCenter(), handle2_.GetCenter());          
      }
      else if (&primitive == &segment_)
      {
        handle1_.SetCenter(segment_.GetPosition1());
        handle2_.SetCenter(segment_.GetPosition2());
        circle_.SetPosition(segment_.GetPosition1(), segment_.GetPosition2());
      }
      else if (&primitive == &circle_)
      {
        handle1_.SetCenter(circle_.GetPosition1());
        handle2_.SetCenter(circle_.GetPosition2());
        segment_.SetPosition(circle_.GetPosition1(), circle_.GetPosition2());
      }
      else
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
      }
        
      UpdateLabel();
    }

    virtual void UpdateProbe(const Scene2D& scene) ORTHANC_OVERRIDE
    {
    }

    virtual void Serialize(Json::Value& target) ORTHANC_OVERRIDE
    {
      target = Json::objectValue;
      target[KEY_TYPE] = VALUE_CIRCLE;
      target[KEY_X1] = handle1_.GetCenter().GetX();
      target[KEY_Y1] = handle1_.GetCenter().GetY();
      target[KEY_X2] = handle2_.GetCenter().GetX();
      target[KEY_Y2] = handle2_.GetCenter().GetY();
    }

    static void Unserialize(AnnotationsSceneLayer& target,
                            Units units,
                            const Json::Value& source)
    {
      if (source.isMember(KEY_X1) &&
          source.isMember(KEY_Y1) &&
          source.isMember(KEY_X2) &&
          source.isMember(KEY_Y2) &&
          source[KEY_X1].isNumeric() &&
          source[KEY_Y1].isNumeric() &&
          source[KEY_X2].isNumeric() &&
          source[KEY_Y2].isNumeric())
      {
        new CircleAnnotation(target, units,
                             ScenePoint2D(source[KEY_X1].asDouble(), source[KEY_Y1].asDouble()),
                             ScenePoint2D(source[KEY_X2].asDouble(), source[KEY_Y2].asDouble()));
      }
      else
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat, "Cannot unserialize an circle annotation");
      }
    }
  };

    
  class AnnotationsSceneLayer::RectangleProbeAnnotation : public ProbingAnnotation
  {
  private:
    Units     units_;
    Handle&   handle1_;
    Handle&   handle2_;
    Segment&  segment1_;
    Segment&  segment2_;
    Segment&  segment3_;
    Segment&  segment4_;
    Text&     label_;

  protected:
    virtual void UpdateProbeForLayer(const ISceneLayer& layer) ORTHANC_OVERRIDE
    {
      double x1 = handle1_.GetCenter().GetX();
      double y1 = handle1_.GetCenter().GetY();
      double x2 = handle2_.GetCenter().GetX();
      double y2 = handle2_.GetCenter().GetY();

      {
        // Put the label to the right of the right-most handle
        //const double y = std::min(y1, y2);
        const double y = (y1 + y2) / 2.0;
        if (x1 < x2)
        {
          label_.SetPosition(x2, y);
        }
        else
        {
          label_.SetPosition(x1, y);
        }
      }

      std::string text;
      
      char buf[32];

      if (units_ == Units_Millimeters)
      {
        const double area = std::abs(x1 - x2) * std::abs(y1 - y2);

        sprintf(buf, "Area: %0.2f cm%c%c",
                area / 100.0,
                0xc2, 0xb2 /* two bytes corresponding to two power in UTF-8 */);
        text = buf;
      }

      if (layer.GetType() == ISceneLayer::Type_FloatTexture)
      {
        const TextureBaseSceneLayer& texture = dynamic_cast<const TextureBaseSceneLayer&>(layer);
        const AffineTransform2D sceneToTexture = AffineTransform2D::Invert(texture.GetTransform());

        const Orthanc::ImageAccessor& image = texture.GetTexture();
        assert(image.GetFormat() == Orthanc::PixelFormat_Float32);

        sceneToTexture.Apply(x1, y1);
        sceneToTexture.Apply(x2, y2);
        int ix1 = static_cast<int>(std::floor(x1));
        int iy1 = static_cast<int>(std::floor(y1));
        int ix2 = static_cast<int>(std::floor(x2));
        int iy2 = static_cast<int>(std::floor(y2));

        if (ix1 > ix2)
        {
          std::swap(ix1, ix2);
        }

        if (iy1 > iy2)
        {
          std::swap(iy1, iy2);
        }

        LinearAlgebra::OnlineVarianceEstimator estimator;

        for (int y = std::max(0, iy1); y <= std::min(static_cast<int>(image.GetHeight()) - 1, iy2); y++)
        {
          int x = std::max(0, ix1);
          
          const float* p = reinterpret_cast<const float*>(image.GetConstRow(y)) + x;

          for (; x <= std::min(static_cast<int>(image.GetWidth()) - 1, ix2); x++, p++)
          {
            estimator.AddSample(*p);
          }
        }

        if (estimator.GetCount() > 0)
        {
          if (!text.empty())
          {
            text += "\n";
          }
          sprintf(buf, "Mean: %0.1f\nStdDev: %0.1f", estimator.GetMean(), estimator.GetStandardDeviation());
          text += buf;
        }
      }
      
      label_.SetText(text);
    }
    
  public:
    RectangleProbeAnnotation(AnnotationsSceneLayer& that,
                             Units units,
                             const ScenePoint2D& p1,
                             const ScenePoint2D& p2) :
      ProbingAnnotation(that),
      units_(units),
      handle1_(AddTypedPrimitive<Handle>(new Handle(*this, Handle::Shape_Square, p1))),
      handle2_(AddTypedPrimitive<Handle>(new Handle(*this, Handle::Shape_Square, p2))),
      segment1_(AddTypedPrimitive<Segment>(new Segment(*this, p1.GetX(), p1.GetY(), p2.GetX(), p1.GetY()))),
      segment2_(AddTypedPrimitive<Segment>(new Segment(*this, p2.GetX(), p1.GetY(), p2.GetX(), p2.GetY()))),
      segment3_(AddTypedPrimitive<Segment>(new Segment(*this, p1.GetX(), p2.GetY(), p2.GetX(), p2.GetY()))),
      segment4_(AddTypedPrimitive<Segment>(new Segment(*this, p1.GetX(), p1.GetY(), p1.GetX(), p2.GetY()))),
      label_(AddTypedPrimitive<Text>(new Text(that, *this)))
    {
      TextSceneLayer content;
      content.SetAnchor(BitmapAnchor_CenterLeft);
      content.SetBorder(10);
      content.SetText("?");

      label_.SetContent(content);
      label_.SetColor(that.GetHoverColor());
    }

    virtual unsigned int GetHandlesCount() const ORTHANC_OVERRIDE
    {
      return 2;
    }

    virtual Handle& GetHandle(unsigned int index) const ORTHANC_OVERRIDE
    {
      switch (index)
      {
        case 0:
          return handle1_;

        case 1:
          return handle2_;

        default:
          throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
      }
    }

    virtual void SignalMove(GeometricPrimitive& primitive,
                            const Scene2D& scene) ORTHANC_OVERRIDE
    {
      if (&primitive == &handle1_ ||
          &primitive == &handle2_)
      {
        double x1 = handle1_.GetCenter().GetX();
        double y1 = handle1_.GetCenter().GetY();
        double x2 = handle2_.GetCenter().GetX();
        double y2 = handle2_.GetCenter().GetY();
        
        segment1_.SetPosition(x1, y1, x2, y1);
        segment2_.SetPosition(x2, y1, x2, y2);
        segment3_.SetPosition(x1, y2, x2, y2);
        segment4_.SetPosition(x1, y1, x1, y2);
      }
      else if (&primitive == &segment1_ ||
               &primitive == &segment2_ ||
               &primitive == &segment3_ ||
               &primitive == &segment4_)
      {
        const Segment& segment = dynamic_cast<const Segment&>(primitive);
        double x1 = segment.GetPosition1().GetX();
        double y1 = segment.GetPosition1().GetY();
        double x2 = segment.GetPosition2().GetX();
        double y2 = segment.GetPosition2().GetY();

        if (&primitive == &segment1_)
        {        
          y2 = y1 + handle2_.GetCenter().GetY() - handle1_.GetCenter().GetY();
        }
        else if (&primitive == &segment2_)
        {
          x1 = x2 + handle1_.GetCenter().GetX() - handle2_.GetCenter().GetX();
        }
        else if (&primitive == &segment3_)
        {
          y1 = y2 + handle1_.GetCenter().GetY() - handle2_.GetCenter().GetY();
        }
        else if (&primitive == &segment4_)
        {
          x2 = x1 + handle2_.GetCenter().GetX() - handle1_.GetCenter().GetX();
        }
        else
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
        }

        handle1_.SetCenter(x1, y1);
        handle2_.SetCenter(x2, y2);

        if (&primitive != &segment1_)
        {
          segment1_.SetPosition(x1, y1, x2, y1);
        }
        
        if (&primitive != &segment2_)
        {
          segment2_.SetPosition(x2, y1, x2, y2);
        }

        if (&primitive != &segment3_)
        {
          segment3_.SetPosition(x1, y2, x2, y2);
        }

        if (&primitive != &segment4_)
        {
          segment4_.SetPosition(x1, y1, x1, y2);
        }
      }
      else
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
      }
      
      TagProbeAsChanged();
    }

    virtual void Serialize(Json::Value& target) ORTHANC_OVERRIDE
    {
      target = Json::objectValue;
      target[KEY_TYPE] = VALUE_RECTANGLE_PROBE;
      target[KEY_X1] = handle1_.GetCenter().GetX();
      target[KEY_Y1] = handle1_.GetCenter().GetY();
      target[KEY_X2] = handle2_.GetCenter().GetX();
      target[KEY_Y2] = handle2_.GetCenter().GetY();
    }

    static void Unserialize(AnnotationsSceneLayer& target,
                            Units units,
                            const Json::Value& source)
    {
      if (source.isMember(KEY_X1) &&
          source.isMember(KEY_Y1) &&
          source.isMember(KEY_X2) &&
          source.isMember(KEY_Y2) &&
          source[KEY_X1].isNumeric() &&
          source[KEY_Y1].isNumeric() &&
          source[KEY_X2].isNumeric() &&
          source[KEY_Y2].isNumeric())
      {
        new RectangleProbeAnnotation(target, units,
                                     ScenePoint2D(source[KEY_X1].asDouble(), source[KEY_Y1].asDouble()),
                                     ScenePoint2D(source[KEY_X2].asDouble(), source[KEY_Y2].asDouble()));
      }
      else
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat, "Cannot unserialize a rectangle probe annotation");
      }
    }
  };

  
  class AnnotationsSceneLayer::EllipseProbeAnnotation : public ProbingAnnotation
  {
  private:
    Units     units_;
    Handle&   handle1_;
    Handle&   handle2_;
    Ellipse&  ellipse_;
    Text&     label_;

  protected:
    virtual void UpdateProbeForLayer(const ISceneLayer& layer) ORTHANC_OVERRIDE
    {
      double x1 = handle1_.GetCenter().GetX();
      double y1 = handle1_.GetCenter().GetY();
      double x2 = handle2_.GetCenter().GetX();
      double y2 = handle2_.GetCenter().GetY();

      {
        // Put the label to the right of the right-most handle
        //const double y = std::min(y1, y2);
        const double y = (y1 + y2) / 2.0;
        if (x1 < x2)
        {
          label_.SetPosition(x2, y);
        }
        else
        {
          label_.SetPosition(x1, y);
        }
      }

      std::string text;
      
      char buf[32];

      if (units_ == Units_Millimeters)
      {
        sprintf(buf, "Area: %0.2f cm%c%c",
                ellipse_.GetArea() / 100.0,
                0xc2, 0xb2 /* two bytes corresponding to two power in UTF-8 */);
        text = buf;
      }

      if (layer.GetType() == ISceneLayer::Type_FloatTexture)
      {
        const TextureBaseSceneLayer& texture = dynamic_cast<const TextureBaseSceneLayer&>(layer);
        const AffineTransform2D& textureToScene = texture.GetTransform();
        const AffineTransform2D sceneToTexture = AffineTransform2D::Invert(textureToScene);

        const Orthanc::ImageAccessor& image = texture.GetTexture();
        assert(image.GetFormat() == Orthanc::PixelFormat_Float32);

        sceneToTexture.Apply(x1, y1);
        sceneToTexture.Apply(x2, y2);
        int ix1 = static_cast<int>(std::floor(x1));
        int iy1 = static_cast<int>(std::floor(y1));
        int ix2 = static_cast<int>(std::floor(x2));
        int iy2 = static_cast<int>(std::floor(y2));

        if (ix1 > ix2)
        {
          std::swap(ix1, ix2);
        }

        if (iy1 > iy2)
        {
          std::swap(iy1, iy2);
        }

        LinearAlgebra::OnlineVarianceEstimator estimator;

        for (int y = std::max(0, iy1); y <= std::min(static_cast<int>(image.GetHeight()) - 1, iy2); y++)
        {
          int x = std::max(0, ix1);
          const float* p = reinterpret_cast<const float*>(image.GetConstRow(y)) + x;

          for (; x <= std::min(static_cast<int>(image.GetWidth()) - 1, ix2); x++, p++)
          {
            double yy = static_cast<double>(y) + 0.5;
            double xx = static_cast<double>(x) + 0.5;
            textureToScene.Apply(xx, yy);
            if (ellipse_.IsPointInside(ScenePoint2D(xx, yy)))
            {
              estimator.AddSample(*p);
            }
          }
        }

        if (estimator.GetCount() > 0)
        {
          if (!text.empty())
          {
            text += "\n";
          }
          sprintf(buf, "Mean: %0.1f\nStdDev: %0.1f", estimator.GetMean(), estimator.GetStandardDeviation());
          text += buf;
        }
      }
      
      label_.SetText(text);
    }
    
  public:
    EllipseProbeAnnotation(AnnotationsSceneLayer& that,
                           Units units,
                           const ScenePoint2D& p1,
                           const ScenePoint2D& p2) :
      ProbingAnnotation(that),
      units_(units),
      handle1_(AddTypedPrimitive<Handle>(new Handle(*this, Handle::Shape_Square, p1))),
      handle2_(AddTypedPrimitive<Handle>(new Handle(*this, Handle::Shape_Square, p2))),
      ellipse_(AddTypedPrimitive<Ellipse>(new Ellipse(*this, p1, p2))),
      label_(AddTypedPrimitive<Text>(new Text(that, *this)))
    {
      TextSceneLayer content;
      content.SetAnchor(BitmapAnchor_CenterLeft);
      content.SetBorder(10);
      content.SetText("?");

      label_.SetContent(content);
      label_.SetColor(that.GetHoverColor());
    }

    virtual unsigned int GetHandlesCount() const ORTHANC_OVERRIDE
    {
      return 2;
    }

    virtual Handle& GetHandle(unsigned int index) const ORTHANC_OVERRIDE
    {
      switch (index)
      {
        case 0:
          return handle1_;

        case 1:
          return handle2_;

        default:
          throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
      }
    }

    virtual void SignalMove(GeometricPrimitive& primitive,
                            const Scene2D& scene) ORTHANC_OVERRIDE
    {
      if (&primitive == &handle1_ ||
          &primitive == &handle2_)
      {
        ellipse_.SetPosition(handle1_.GetCenter(), handle2_.GetCenter());
      }
      else if (&primitive == &ellipse_)
      {
        handle1_.SetCenter(ellipse_.GetPosition1());
        handle2_.SetCenter(ellipse_.GetPosition2());
      }
      else
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
      }
      
      TagProbeAsChanged();
    }

    virtual void Serialize(Json::Value& target) ORTHANC_OVERRIDE
    {
      target = Json::objectValue;
      target[KEY_TYPE] = VALUE_ELLIPSE_PROBE;
      target[KEY_X1] = handle1_.GetCenter().GetX();
      target[KEY_Y1] = handle1_.GetCenter().GetY();
      target[KEY_X2] = handle2_.GetCenter().GetX();
      target[KEY_Y2] = handle2_.GetCenter().GetY();
    }

    static void Unserialize(AnnotationsSceneLayer& target,
                            Units units,
                            const Json::Value& source)
    {
      if (source.isMember(KEY_X1) &&
          source.isMember(KEY_Y1) &&
          source.isMember(KEY_X2) &&
          source.isMember(KEY_Y2) &&
          source[KEY_X1].isNumeric() &&
          source[KEY_Y1].isNumeric() &&
          source[KEY_X2].isNumeric() &&
          source[KEY_Y2].isNumeric())
      {
        new EllipseProbeAnnotation(target, units,
                                     ScenePoint2D(source[KEY_X1].asDouble(), source[KEY_Y1].asDouble()),
                                     ScenePoint2D(source[KEY_X2].asDouble(), source[KEY_Y2].asDouble()));
      }
      else
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat, "Cannot unserialize an ellipse probe annotation");
      }
    }
  };

  
  class AnnotationsSceneLayer::CreateTwoHandlesTracker : public IFlexiblePointerTracker
  {
  private:
    AnnotationsSceneLayer&  layer_;
    Annotation*             annotation_;
    AffineTransform2D       canvasToScene_;

  protected:
    AnnotationsSceneLayer& GetLayer() const
    {
      return layer_;
    }
    
    const Annotation& GetAnnotation() const
    {
      if (IsAlive())
      {
        assert(annotation_ != NULL);
        return *annotation_;
      }
      else
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
      }
    }
      
  public:
    CreateTwoHandlesTracker(Annotation& annotation,
                            const AffineTransform2D& canvasToScene) :
      layer_(annotation.GetParentLayer()),
      annotation_(&annotation),
      canvasToScene_(canvasToScene)
    {
      assert(annotation_ != NULL &&
             annotation_->GetHandlesCount() >= 2);
    }

    virtual void PointerMove(const PointerEvent& event,
                             const Scene2D& scene) ORTHANC_OVERRIDE
    {
      if (annotation_ != NULL)
      {
        annotation_->GetHandle(1).SetCenter(event.GetMainPosition().Apply(canvasToScene_));
        annotation_->SignalMove(annotation_->GetHandle(1), scene);

        layer_.BroadcastMessage(AnnotationChangedMessage(layer_));
      }
    }
      
    virtual void PointerUp(const PointerEvent& event,
                           const Scene2D& scene) ORTHANC_OVERRIDE
    {
      annotation_ = NULL;  // IsAlive() becomes false

      layer_.BroadcastMessage(AnnotationAddedMessage(layer_));
    }

    virtual void PointerDown(const PointerEvent& event,
                             const Scene2D& scene) ORTHANC_OVERRIDE
    {
    }

    virtual bool IsAlive() const ORTHANC_OVERRIDE
    {
      return (annotation_ != NULL);
    }

    virtual void Cancel(const Scene2D& scene) ORTHANC_OVERRIDE
    {
      if (annotation_ != NULL)
      {
        layer_.DeleteAnnotation(annotation_);
        annotation_ = NULL;
      }
    }
  };


  class AnnotationsSceneLayer::CreateAngleTracker : public IFlexiblePointerTracker
  {
  private:
    AnnotationsSceneLayer&  that_;
    LengthAnnotation*       length_;
    AngleAnnotation*        angle_;
    AffineTransform2D       canvasToScene_;
      
  public:
    CreateAngleTracker(AnnotationsSceneLayer& that,
                       const ScenePoint2D& sceneClick,
                       const AffineTransform2D& canvasToScene) :
      that_(that),
      length_(NULL),
      angle_(NULL),
      canvasToScene_(canvasToScene)
    {
      length_ = new LengthAnnotation(that, that.GetUnits(), false /* no length label */, sceneClick, sceneClick);
    }

    virtual void PointerMove(const PointerEvent& event,
                             const Scene2D& scene) ORTHANC_OVERRIDE
    {
      if (length_ != NULL)
      {
        length_->GetHandle(1).SetCenter(event.GetMainPosition().Apply(canvasToScene_));
        length_->SignalMove(length_->GetHandle(1), scene);
        that_.BroadcastMessage(AnnotationChangedMessage(that_));
      }

      if (angle_ != NULL)
      {
        angle_->GetHandle(2).SetCenter(event.GetMainPosition().Apply(canvasToScene_));
        angle_->SignalMove(angle_->GetHandle(2), scene);
        that_.BroadcastMessage(AnnotationChangedMessage(that_));
      }
    }
      
    virtual void PointerUp(const PointerEvent& event,
                           const Scene2D& scene) ORTHANC_OVERRIDE
    {
      if (length_ != NULL)
      {
        // End of first step: The first segment is available, now create the angle

        angle_ = new AngleAnnotation(that_, length_->GetHandle(0).GetCenter(),
                                     length_->GetHandle(1).GetCenter(),
                                     length_->GetHandle(1).GetCenter());
          
        that_.DeleteAnnotation(length_);
        length_ = NULL;

        that_.BroadcastMessage(AnnotationChangedMessage(that_));
      }
      else
      {
        angle_ = NULL;  // IsAlive() becomes false

        that_.BroadcastMessage(AnnotationAddedMessage(that_));
      }
    }

    virtual void PointerDown(const PointerEvent& event,
                             const Scene2D& scene) ORTHANC_OVERRIDE
    {
    }

    virtual bool IsAlive() const ORTHANC_OVERRIDE
    {
      return (length_ != NULL ||
              angle_ != NULL);
    }

    virtual void Cancel(const Scene2D& scene) ORTHANC_OVERRIDE
    {
      if (length_ != NULL)
      {
        that_.DeleteAnnotation(length_);
        length_ = NULL;
      }

      if (angle_ != NULL)
      {
        that_.DeleteAnnotation(angle_);
        angle_ = NULL;
      }
    }
  };


  class AnnotationsSceneLayer::CreatePixelProbeTracker : public IFlexiblePointerTracker
  {
  public:
    CreatePixelProbeTracker(AnnotationsSceneLayer& that,
                            const ScenePoint2D& sceneClick,
                            const Scene2D& scene)
    {
      PixelProbeAnnotation* annotation = new PixelProbeAnnotation(that, sceneClick);
      annotation->UpdateProbe(scene);
      that.BroadcastMessage(AnnotationAddedMessage(that));
    }

    virtual void PointerMove(const PointerEvent& event,
                             const Scene2D& scene) ORTHANC_OVERRIDE
    {
    }
      
    virtual void PointerUp(const PointerEvent& event,
                           const Scene2D& scene) ORTHANC_OVERRIDE
    {
    }

    virtual void PointerDown(const PointerEvent& event,
                             const Scene2D& scene) ORTHANC_OVERRIDE
    {
    }

    virtual bool IsAlive() const ORTHANC_OVERRIDE
    {
      return false;
    }

    virtual void Cancel(const Scene2D& scene) ORTHANC_OVERRIDE
    {
    }
  };


  class AnnotationsSceneLayer::CreateTextAnnotationTracker : public CreateTwoHandlesTracker
  {
  public:
    CreateTextAnnotationTracker(AnnotationsSceneLayer& that,
                                const std::string& label,
                                const ScenePoint2D& position,
                                const AffineTransform2D& canvasToScene) :
      CreateTwoHandlesTracker(*new TextAnnotation(that, label, position, position), canvasToScene)
    {
    }

    virtual void PointerUp(const PointerEvent& event,
                           const Scene2D& scene) ORTHANC_OVERRIDE
    {
      std::unique_ptr<TextAnnotationRequiredMessage> request;
      
      {
        const TextAnnotation& annotation = dynamic_cast<const TextAnnotation&>(GetAnnotation());
        request.reset(new TextAnnotationRequiredMessage(GetLayer(), annotation.GetPointedPosition(), annotation.GetLabelPosition()));
      }
      
      Cancel(scene);  // Warning: "annotation_" is now invalid!
      
      GetLayer().BroadcastMessage(AnnotationChangedMessage(GetLayer()));
      GetLayer().BroadcastMessage(*request);
    }
  };


  // Dummy tracker that is only used for deletion, in order to warn
  // the caller that the mouse action was taken into consideration
  class AnnotationsSceneLayer::RemoveTracker : public IFlexiblePointerTracker
  {
  public:
    RemoveTracker()
    {
    }

    virtual void PointerMove(const PointerEvent& event,
                             const Scene2D& scene) ORTHANC_OVERRIDE
    {
    }
      
    virtual void PointerUp(const PointerEvent& event,
                           const Scene2D& scene) ORTHANC_OVERRIDE
    {
    }

    virtual void PointerDown(const PointerEvent& event,
                             const Scene2D& scene) ORTHANC_OVERRIDE
    {
    }

    virtual bool IsAlive() const ORTHANC_OVERRIDE
    {
      return false;
    }

    virtual void Cancel(const Scene2D& scene) ORTHANC_OVERRIDE
    {
    }
  };


  void AnnotationsSceneLayer::AddAnnotation(Annotation* annotation)
  {
    assert(annotation != NULL);
    assert(annotations_.find(annotation) == annotations_.end());
    annotations_.insert(annotation);
  }
  

  void AnnotationsSceneLayer::DeleteAnnotation(Annotation* annotation)
  {
    if (annotation != NULL)
    {
      assert(annotations_.find(annotation) != annotations_.end());
      annotations_.erase(annotation);
      delete annotation;
    }
  }

  
  void AnnotationsSceneLayer::DeletePrimitive(GeometricPrimitive* primitive)
  {
    if (primitive != NULL)
    {
      assert(primitives_.find(primitive) != primitives_.end());
      primitives_.erase(primitive);
      delete primitive;
    }
  }

  
  void AnnotationsSceneLayer::TagSubLayerToRemove(size_t subLayerIndex)
  {
    assert(subLayersToRemove_.find(subLayerIndex) == subLayersToRemove_.end());
    subLayersToRemove_.insert(subLayerIndex);
  }
    

  AnnotationsSceneLayer::AnnotationsSceneLayer(size_t macroLayerIndex) :
    activeTool_(Tool_Edit),
    macroLayerIndex_(macroLayerIndex),
    polylineSubLayer_(0),  // dummy initialization
    units_(Units_Pixels),
    probedLayer_(0),
    color_(0, 255, 0),
    hoverColor_(255, 0, 0)
  {
  }
    

  void AnnotationsSceneLayer::Clear()
  {
    for (Annotations::iterator it = annotations_.begin(); it != annotations_.end(); ++it)
    {
      assert(*it != NULL);
      delete *it;
    }

    annotations_.clear();

    ClearHover();
  }

  
  void AnnotationsSceneLayer::SetUnits(Units units)
  {
    if (units_ != units)
    {
      Clear();
      units_ = units;
    }
  }


  void AnnotationsSceneLayer::AddLengthAnnotation(const ScenePoint2D& p1,
                                                  const ScenePoint2D& p2)
  {
    annotations_.insert(new LengthAnnotation(*this, units_, true /* show label */, p1, p2));
    BroadcastMessage(AnnotationChangedMessage(*this));
  }
  

  void AnnotationsSceneLayer::AddCircleAnnotation(const ScenePoint2D& p1,
                                                  const ScenePoint2D& p2)
  {
    annotations_.insert(new CircleAnnotation(*this, units_, p1, p2));
    BroadcastMessage(AnnotationChangedMessage(*this));
  }
  

  void AnnotationsSceneLayer::AddAngleAnnotation(const ScenePoint2D& p1,
                                                 const ScenePoint2D& p2,
                                                 const ScenePoint2D& p3)
  {
    annotations_.insert(new AngleAnnotation(*this, p1, p2, p3));
    BroadcastMessage(AnnotationChangedMessage(*this));
  }
  

  void AnnotationsSceneLayer::Render(Scene2D& scene)
  {
    // First, update the probes
    for (Annotations::const_iterator it = annotations_.begin(); it != annotations_.end(); ++it)
    {
      assert(*it != NULL);
      (*it)->UpdateProbe(scene);
    }

    MacroSceneLayer* macro = NULL;

    if (scene.HasLayer(macroLayerIndex_))
    {
      macro = &dynamic_cast<MacroSceneLayer&>(scene.GetLayer(macroLayerIndex_));
    }
    else
    {
      macro = &dynamic_cast<MacroSceneLayer&>(scene.SetLayer(macroLayerIndex_, new MacroSceneLayer));
      polylineSubLayer_ = macro->AddLayer(new PolylineSceneLayer);
    }

    for (SubLayers::const_iterator it = subLayersToRemove_.begin(); it != subLayersToRemove_.end(); ++it)
    {
      assert(macro->HasLayer(*it));
      macro->DeleteLayer(*it);
    }

    subLayersToRemove_.clear();

    std::unique_ptr<PolylineSceneLayer> polyline(new PolylineSceneLayer);

    for (GeometricPrimitives::iterator it = primitives_.begin(); it != primitives_.end(); ++it)
    {
      assert(*it != NULL);
      GeometricPrimitive& primitive = **it;        
        
      primitive.RenderPolylineLayer(*polyline, scene);

      if (primitive.IsModified())
      {
        primitive.RenderOtherLayers(*macro, scene);
        primitive.SetModified(false);
      }
    }

    macro->UpdateLayer(polylineSubLayer_, polyline.release());
  }

  
  bool AnnotationsSceneLayer::ClearHover()
  {
    bool needsRefresh = false;
      
    for (GeometricPrimitives::iterator it = primitives_.begin(); it != primitives_.end(); ++it)
    {
      assert(*it != NULL);
      if ((*it)->IsHover())
      {
        (*it)->SetHover(false);
        needsRefresh = true;
      }
    }

    return needsRefresh;
  }
  

  bool AnnotationsSceneLayer::SetMouseHover(const ScenePoint2D& p,
                                            const Scene2D& scene)
  {
    if (activeTool_ == Tool_None)
    {
      return ClearHover();
    }
    else
    {
      bool needsRefresh = false;
      
      const ScenePoint2D s = p.Apply(scene.GetCanvasToSceneTransform());
      
      for (GeometricPrimitives::iterator it = primitives_.begin(); it != primitives_.end(); ++it)
      {
        assert(*it != NULL);
        bool hover = (*it)->IsHit(s, scene);

        if ((*it)->IsHover() != hover)
        {
          needsRefresh = true;
        }
        
        (*it)->SetHover(hover);
      }

      return needsRefresh;
    }
  }


  IFlexiblePointerTracker* AnnotationsSceneLayer::CreateTracker(const ScenePoint2D& p,
                                                                const Scene2D& scene)
  {
    /**
     * WARNING: The created trackers must NOT keep a reference to "scene"!
     **/

    if (activeTool_ == Tool_None)
    {
      return NULL;
    }
    else
    {
      const ScenePoint2D s = p.Apply(scene.GetCanvasToSceneTransform());

      GeometricPrimitive* bestHit = NULL;
      
      for (GeometricPrimitives::iterator it = primitives_.begin(); it != primitives_.end(); ++it)
      {
        assert(*it != NULL);
        if ((*it)->IsHit(s, scene))
        {
          if (bestHit == NULL ||
              bestHit->GetDepth() > (*it)->GetDepth())
          {
            bestHit = *it;
          }
        }
      }

      if (bestHit != NULL)
      {
        if (activeTool_ == Tool_Remove)
        {
          DeleteAnnotation(&bestHit->GetParentAnnotation());
          BroadcastMessage(AnnotationRemovedMessage(*this));
          return new RemoveTracker;
        }
        else
        {
          return new EditPrimitiveTracker(*this, *bestHit, s, scene.GetCanvasToSceneTransform());
        }
      }
      else
      {
        switch (activeTool_)
        {
          case Tool_Length:
          {
            Annotation* annotation = new LengthAnnotation(*this, units_, true /* show label */, s, s);
            return new CreateTwoHandlesTracker(*annotation, scene.GetCanvasToSceneTransform());
          }

          case Tool_Circle:
          {
            Annotation* annotation = new CircleAnnotation(*this, units_, s, s);
            return new CreateTwoHandlesTracker(*annotation, scene.GetCanvasToSceneTransform());
          }

          case Tool_Angle:
            return new CreateAngleTracker(*this, s, scene.GetCanvasToSceneTransform());

          case Tool_PixelProbe:
            return new CreatePixelProbeTracker(*this, s, scene);

          case Tool_RectangleProbe:
          {
            Annotation* annotation = new RectangleProbeAnnotation(*this, units_, s, s);
            return new CreateTwoHandlesTracker(*annotation, scene.GetCanvasToSceneTransform());
          }

          case Tool_EllipseProbe:
          {
            Annotation* annotation = new EllipseProbeAnnotation(*this, units_, s, s);
            return new CreateTwoHandlesTracker(*annotation, scene.GetCanvasToSceneTransform());
          }

          case Tool_TextAnnotation:
            return new CreateTextAnnotationTracker(*this, "" /* empty label */, s, scene.GetCanvasToSceneTransform());

          default:
            return NULL;
        }
      }
    }
  }


  void AnnotationsSceneLayer::Serialize(Json::Value& target) const
  {
    Json::Value annotations = Json::arrayValue;
      
    for (Annotations::const_iterator it = annotations_.begin(); it != annotations_.end(); ++it)
    {
      assert(*it != NULL);

      Json::Value item;
      (*it)->Serialize(item);
      annotations.append(item);
    }

    target = Json::objectValue;
    target[KEY_ANNOTATIONS] = annotations;

    switch (units_)
    {
      case Units_Millimeters:
        target[KEY_UNITS] = VALUE_MILLIMETERS;
        break;

      case Units_Pixels:
        target[KEY_UNITS] = VALUE_PIXELS;
        break;

      default:
        throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
  }


  void AnnotationsSceneLayer::Unserialize(const Json::Value& serialized)
  {
    Clear();
      
    if (serialized.type() != Json::objectValue ||
        !serialized.isMember(KEY_ANNOTATIONS) ||
        !serialized.isMember(KEY_UNITS) ||
        serialized[KEY_ANNOTATIONS].type() != Json::arrayValue ||
        serialized[KEY_UNITS].type() != Json::stringValue)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat, "Cannot unserialize a set of annotations");
    }

    const std::string& u = serialized[KEY_UNITS].asString();

    if (u == VALUE_MILLIMETERS)
    {
      units_ = Units_Millimeters;
    }
    else if (u == VALUE_PIXELS)
    {
      units_ = Units_Pixels;
    }
    else
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat, "Unknown units: " + u);
    }

    const Json::Value& annotations = serialized[KEY_ANNOTATIONS];

    for (Json::Value::ArrayIndex i = 0; i < annotations.size(); i++)
    {
      if (annotations[i].type() != Json::objectValue ||
          !annotations[i].isMember(KEY_TYPE) ||
          annotations[i][KEY_TYPE].type() != Json::stringValue)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
      }

      const std::string& type = annotations[i][KEY_TYPE].asString();

      if (type == VALUE_ANGLE)
      {
        AngleAnnotation::Unserialize(*this, annotations[i]);
      }
      else if (type == VALUE_CIRCLE)
      {
        CircleAnnotation::Unserialize(*this, units_, annotations[i]);
      }
      else if (type == VALUE_LENGTH)
      {
        LengthAnnotation::Unserialize(*this, units_, annotations[i]);
      }
      else if (type == VALUE_PIXEL_PROBE)
      {
        PixelProbeAnnotation::Unserialize(*this, annotations[i]);
      }
      else if (type == VALUE_RECTANGLE_PROBE)
      {
        RectangleProbeAnnotation::Unserialize(*this, units_, annotations[i]);
      }
      else if (type == VALUE_ELLIPSE_PROBE)
      {
        EllipseProbeAnnotation::Unserialize(*this, units_, annotations[i]);
      }
      else if (type == VALUE_TEXT_ANNOTATION)
      {
        TextAnnotation::Unserialize(*this, annotations[i]);
      }
      else
      {
        LOG(ERROR) << "Cannot unserialize unknown type of annotation: " << type;
      }
    }
  }


  void AnnotationsSceneLayer::AddTextAnnotation(const std::string& label,
                                                const ScenePoint2D& pointedPosition,
                                                const ScenePoint2D& labelPosition)
  {
    annotations_.insert(new TextAnnotation(*this, label, pointedPosition, labelPosition));
    BroadcastMessage(AnnotationChangedMessage(*this));
  }
}
