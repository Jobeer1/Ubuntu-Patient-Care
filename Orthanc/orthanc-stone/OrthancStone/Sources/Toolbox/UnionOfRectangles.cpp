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


#include "UnionOfRectangles.h"

#include "Internals/OrientedIntegerLine2D.h"
#include "Internals/RectanglesIntegerProjection.h"
#include "SegmentTree.h"

#include <OrthancException.h>

#include <stack>


namespace OrthancStone
{
  class UnionOfRectangles::Payload : public Orthanc::IDynamicObject
  {    
  private:
    int     counter_;
    Status  status_;
  
  public:
    Payload() :
      counter_(0),
      status_(Status_Empty)
    {
    }

    int GetCounter() const
    {
      return counter_;
    }

    Status GetStatus() const
    {
      return status_;
    }

    void SetStatus(Status status)
    {
      status_ = status;
    }

    void Increment()
    {
      counter_ ++;
    }

    void Decrement()
    {
      if (counter_ == 0)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
      }
      else
      {
        counter_ --;
      }
    }
  };
  
  
  class UnionOfRectangles::Factory : public SegmentTree::IPayloadFactory
  {
  public:
    virtual Orthanc::IDynamicObject* Create() ORTHANC_OVERRIDE
    {
      return new Payload;
    }
  };


  class UnionOfRectangles::Visitor : public SegmentTree::IVisitor
  {
  private:
    Operation  operation_;
  
  public:
    explicit Visitor(Operation operation) :
      operation_(operation)
    {
    }
  
    virtual void Visit(const SegmentTree& node,
                       bool fullyInside) ORTHANC_OVERRIDE
    {
      Payload& payload = node.GetTypedPayload<Payload>();

      if (fullyInside)
      {
        switch (operation_)
        {
          case Operation_Insert:
            payload.Increment();
            break;
            
          case Operation_Delete:
            payload.Decrement();
            break;

          default:
            throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
        }
      }

      if (payload.GetCounter() > 0)
      {
        payload.SetStatus(Status_Full);
      }
      else if (node.IsLeaf())
      {
        payload.SetStatus(Status_Empty);
      }
      else if (node.GetLeftChild().GetTypedPayload<Payload>().GetStatus() == Status_Empty &&
               node.GetRightChild().GetTypedPayload<Payload>().GetStatus() == Status_Empty)
      {
        payload.SetStatus(Status_Empty);
      }
      else
      {
        payload.SetStatus(Status_Partial);
      }
    }


    // This is the "CONTR()" function from the textbook
    static void IntersectComplement(std::stack<size_t>& stack,
                                    size_t low,
                                    size_t high,
                                    const SegmentTree& node)
    {
      if (low >= high)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
      }
    
      Status status = node.GetTypedPayload<Payload>().GetStatus();
    
      if (status != Status_Full)
      {
        assert(status == Status_Partial ||
               status == Status_Empty);

        // Aliases to use the same variable names as in the textbook
        const size_t& b = low;
        const size_t& e = high;
        const size_t& bv = node.GetLowBound();
        const size_t& ev = node.GetHighBound();
      
        if (b <= bv &&
            ev <= e &&
            status == Status_Empty)
        {
          // [B[v], E[v]] is contributed
          if (!stack.empty() &&
              stack.top() == bv)
          {
            stack.pop();     // Merge continuous segments
          }
          else
          {
            stack.push(bv);  // Beginning of edge
          }

          stack.push(ev);    // Current termination of edge
        }
        else
        {
          size_t middle = (bv + ev) / 2;

          if (b < middle)
          {
            IntersectComplement(stack, b, e, node.GetLeftChild());
          }

          if (middle < e)
          {
            IntersectComplement(stack, b, e, node.GetRightChild());
          }
        }
      }
    }
  };


  static void AddVerticalEdges(std::list<Internals::OrientedIntegerLine2D>& edges,
                               std::stack<size_t>& stack,
                               size_t x,
                               bool isLeft)
  {
    if (stack.size() % 2 != 0)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
    }

    typedef std::pair<size_t, size_t>  Interval;

    std::list<Interval> intervals;

    while (!stack.empty())
    {
      size_t high = stack.top();
      stack.pop();
      size_t low = stack.top();
      stack.pop();

      if (!intervals.empty() &&
          intervals.back().second == low)
      {
        // Extend the previous interval
        intervals.back().second = high;
      }
      else
      {
        intervals.push_back(std::make_pair(low, high));
      }
    }
  
    for (std::list<Interval>::const_iterator
           it = intervals.begin(); it != intervals.end(); ++it)
    {
      if (it->first >= it->second)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
      }
    
      // By convention, the left sides go downward, and the right go upward
      if (isLeft)
      {
        if (!edges.empty() &&
            edges.back().GetX1() == x &&
            edges.back().GetX2() == x &&
            edges.back().GetY1() == it->second &&
            edges.back().GetY2() == it->first)
        {
          // The two successive vertical segments cancel each other
          edges.pop_back();
        }
        else
        {
          edges.push_back(Internals::OrientedIntegerLine2D(x, it->first, x, it->second));
        }
      }
      else
      {
        if (!edges.empty() &&
            edges.back().GetX1() == x &&
            edges.back().GetX2() == x &&
            edges.back().GetY1() == it->first &&
            edges.back().GetY2() == it->second)
        {
          // The two successive vertical segments cancel each other
          edges.pop_back();
        }
        else
        {
          edges.push_back(Internals::OrientedIntegerLine2D(x, it->second, x, it->first));
        }
      }
    }
  }
  

  class UnionOfRectangles::VerticalSide
  {
  private:
    size_t  x_;
    bool    isLeft_;
    size_t  y1_;
    size_t  y2_;

  public:
    VerticalSide(size_t x,
                 bool isLeft,
                 size_t y1,
                 size_t y2) :
      x_(x),
      isLeft_(isLeft),
      y1_(y1),
      y2_(y2)
    {
      assert(y1 < y2);
    }

    size_t GetX() const
    {
      return x_;
    }

    bool IsLeft() const
    {
      return isLeft_;
    }

    size_t GetY1() const
    {
      return y1_;
    }

    size_t GetY2() const
    {
      return y2_;
    }

    bool operator< (const VerticalSide& other) const
    {
      if (x_ < other.x_)
      {
        return true;
      }
      else if (x_ == other.x_)
      {
        return static_cast<int>(isLeft_) < static_cast<int>(other.isLeft_);
      }
      else
      {
        return false;
      }
    }

    bool Equals(const VerticalSide& other) const
    {
      return (x_ == other.x_ &&
              isLeft_ == other.isLeft_);
    }
  };


  class UnionOfRectangles::HorizontalJunction
  {
  private:
    size_t  x_;
    size_t  y_;
    size_t  ybis_;
    bool    downward_;

  public:
    HorizontalJunction(size_t x,
                       size_t y,
                       size_t ybis,
                       bool downward) :
      x_(x),
      y_(y),
      ybis_(ybis),
      downward_(downward)
    {
    }

    size_t GetX() const
    {
      return x_;
    }

    size_t GetY() const
    {
      return y_;
    }

    size_t GetYBis() const
    {
      return ybis_;
    }

    bool IsDownward() const
    {
      return downward_;
    }

    bool operator< (const HorizontalJunction& other) const
    {
      if (y_ > other.y_)
      {
        return true;
      }
      else if (y_ == other.y_)
      {
        return x_ < other.x_;
      }
      else
      {
        return false;
      }
    }
  };
  
  
  void UnionOfRectangles::Apply(std::list< std::vector<ScenePoint2D> >& contours,
                                const std::list<Extent2D>& rectangles)
  {
    contours.clear();

    /**
     * STEP 1
     **/
    Internals::RectanglesIntegerProjection horizontalProjection(rectangles, true);
    Internals::RectanglesIntegerProjection verticalProjection(rectangles, false);

    assert(horizontalProjection.GetProjectedRectanglesCount() == verticalProjection.GetProjectedRectanglesCount());

    /**
     * STEP 2
     **/
    if (verticalProjection.GetEndpointsCount() == 0)
    {
      return;
    }
    
    Factory factory;
    SegmentTree tree(0, verticalProjection.GetEndpointsCount() - 1, factory);

    
    /**
     * STEP 3
     **/
    std::vector<VerticalSide> verticalSides;

    const size_t countRectangles = horizontalProjection.GetProjectedRectanglesCount();
    
    verticalSides.reserve(2 * countRectangles);
    
    for (size_t i = 0; i < countRectangles; i++)
    {
      size_t horizontalLow = horizontalProjection.GetProjectedRectangleLow(i);
      size_t horizontalHigh = horizontalProjection.GetProjectedRectangleHigh(i);
      size_t verticalLow = verticalProjection.GetProjectedRectangleLow(i);
      size_t verticalHigh = verticalProjection.GetProjectedRectangleHigh(i);
      
      verticalSides.push_back(VerticalSide(horizontalLow, true, verticalLow, verticalHigh));
      verticalSides.push_back(VerticalSide(horizontalHigh, false, verticalLow, verticalHigh));
    }
    
    assert(verticalSides.size() == 2 * countRectangles);
    
    std::sort(verticalSides.begin(), verticalSides.end());

    
    /**
     * STEP 4
     **/
    std::list<Internals::OrientedIntegerLine2D> verticalEdges;
    std::stack<size_t> stack;
    
    for (size_t i = 0; i < verticalSides.size(); i++)
    {
      if (i > 0 &&
          !verticalSides[i].Equals(verticalSides[i - 1]))
      {
        // Output the stack
        AddVerticalEdges(verticalEdges, stack, verticalSides[i - 1].GetX(),
                         verticalSides[i - 1].IsLeft());
      }

      size_t y1 = verticalSides[i].GetY1();
      size_t y2 = verticalSides[i].GetY2();
      
      if (verticalSides[i].IsLeft())
      {
        Visitor::IntersectComplement(stack, y1, y2, tree);

        Visitor visitor(Operation_Insert);
        tree.VisitSegment(y1, y2, visitor);
      }
      else
      {
        Visitor visitor(Operation_Delete);
        tree.VisitSegment(y1, y2, visitor);

        Visitor::IntersectComplement(stack, y1, y2, tree);
      }
    }

    if (!verticalSides.empty() &&
        !stack.empty())
    {
      AddVerticalEdges(verticalEdges, stack, verticalSides.back().GetX(),
                       verticalSides.back().IsLeft());
    }


    /**
     * STEP 5: Horizontal edges
     **/
    std::vector<HorizontalJunction> horizontalJunctions;
    horizontalJunctions.reserve(2 * verticalEdges.size());

    for (std::list<Internals::OrientedIntegerLine2D>::const_iterator
           it = verticalEdges.begin(); it != verticalEdges.end(); ++it)
    {
      assert(it->GetX1() == it->GetX2());
      horizontalJunctions.push_back(HorizontalJunction(it->GetX1(), it->GetY1(), it->GetY2(), it->IsDownward()));
      horizontalJunctions.push_back(HorizontalJunction(it->GetX1(), it->GetY2(), it->GetY1(), it->IsDownward()));
    }  

    assert(horizontalJunctions.size() == 2 * verticalEdges.size());
    std::sort(horizontalJunctions.begin(), horizontalJunctions.end());

    std::list<Internals::OrientedIntegerLine2D> horizontalEdges;
    for (size_t i = 0; i < horizontalJunctions.size(); i += 2)
    {
      size_t x1 = horizontalJunctions[i].GetX();
      size_t x2 = horizontalJunctions[i + 1].GetX();
      size_t y = horizontalJunctions[i].GetY();

      if ((horizontalJunctions[i].IsDownward() && y > horizontalJunctions[i].GetYBis()) ||
          (!horizontalJunctions[i].IsDownward() && y < horizontalJunctions[i].GetYBis()))
      {
        horizontalEdges.push_back(Internals::OrientedIntegerLine2D(x1, y, x2, y));
      }
      else
      {
        horizontalEdges.push_back(Internals::OrientedIntegerLine2D(x2, y, x1, y));
      }
    }


    /**
     * POST-PROCESSING: Combine the separate sets of horizontal and
     * vertical edges, into a set of 2D chains
     **/
    std::vector<Internals::OrientedIntegerLine2D> allEdges;
    allEdges.reserve(horizontalEdges.size() + verticalEdges.size());
    
    for (std::list<Internals::OrientedIntegerLine2D>::const_iterator
           it = horizontalEdges.begin(); it != horizontalEdges.end(); ++it)
    {
      allEdges.push_back(*it);
    }
    
    for (std::list<Internals::OrientedIntegerLine2D>::const_iterator
           it = verticalEdges.begin(); it != verticalEdges.end(); ++it)
    {
      allEdges.push_back(*it);
    }
    
    assert(allEdges.size() == horizontalEdges.size() + verticalEdges.size());

    std::list<Internals::OrientedIntegerLine2D::Chain> chains;
    Internals::OrientedIntegerLine2D::ExtractChains(chains, allEdges);

    for (std::list<Internals::OrientedIntegerLine2D::Chain>::const_iterator
           it = chains.begin(); it != chains.end(); ++it)
    {
      assert(!it->empty());
      
      std::vector<ScenePoint2D> chain;
      chain.reserve(it->size());
      
      for (Internals::OrientedIntegerLine2D::Chain::const_iterator
             it2 = it->begin(); it2 != it->end(); ++it2)
      {
        chain.push_back(ScenePoint2D(horizontalProjection.GetEndpointCoordinate(it2->first),
                                     verticalProjection.GetEndpointCoordinate(it2->second)));
      }

      assert(!chain.empty());
      contours.push_back(chain);
    }
  }
}
