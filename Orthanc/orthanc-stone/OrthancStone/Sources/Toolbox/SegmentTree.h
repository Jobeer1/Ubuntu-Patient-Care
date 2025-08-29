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

#include <Compatibility.h>
#include <IDynamicObject.h>

namespace OrthancStone
{
  /**
   * This implementation of segment trees closely follows Section
   * 1.2.3.1 (pages 13-15) of "Computational Geometry - An
   * Introduction" by Preparata and Ian Shamos (1985).
   **/

  class SegmentTree : public boost::noncopyable
  {
  public:
    class IPayloadFactory : public boost::noncopyable
    {
    public:
      virtual ~IPayloadFactory()
      {
      }

      virtual Orthanc::IDynamicObject* Create() = 0;
    };

    class IVisitor : public boost::noncopyable
    {
    public:
      virtual ~IVisitor()
      {
      }

      // "fullyInside" is true iff. the segment of "node" is fully
      // inside the user-provided segment
      virtual void Visit(const SegmentTree& node,
                         bool fullyInside) = 0;
    };

  private:
    size_t                                    lowBound_;
    size_t                                    highBound_;
    std::unique_ptr<SegmentTree>              left_;
    std::unique_ptr<SegmentTree>              right_;
    std::unique_ptr<Orthanc::IDynamicObject>  payload_;
    
  public:
    SegmentTree(size_t lowBound,
                size_t highBound,
                IPayloadFactory& factory);

    size_t GetLowBound() const
    {
      return lowBound_;
    }

    size_t GetHighBound() const
    {
      return highBound_;
    }

    bool IsLeaf() const
    {
      return left_.get() == NULL;
    }

    Orthanc::IDynamicObject& GetPayload() const;

    template <typename T>
    T& GetTypedPayload() const
    {
      return dynamic_cast<T&>(GetPayload());
    }

    SegmentTree& GetLeftChild() const;

    SegmentTree& GetRightChild() const;

    size_t CountNodes() const;

    /**
     * Apply the given visitor to all the segments that intersect the
     * [low,high] segment. This corresponds to both methods "INSERT()"
     * and "DELETE()" from the reference textbook.
     **/
    void VisitSegment(size_t low,
                      size_t high,
                      IVisitor& visitor) const;

    // For unit tests
    const SegmentTree* FindLeaf(size_t low) const;

    // For unit tests
    const SegmentTree* FindNode(size_t low,
                                size_t high) const;
  };
}
