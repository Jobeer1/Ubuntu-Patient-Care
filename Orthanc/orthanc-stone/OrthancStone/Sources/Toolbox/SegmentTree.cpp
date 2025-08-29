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


#include "SegmentTree.h"

#include <OrthancException.h>

#include <cassert>


namespace OrthancStone
{
  SegmentTree::SegmentTree(size_t lowBound,
                           size_t highBound,
                           IPayloadFactory& factory) :
    lowBound_(lowBound),
    highBound_(highBound),
    payload_(factory.Create())
  {
    if (payload_.get() == NULL)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_NullPointer);
    }
    
    if (lowBound >= highBound)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
    
    if (highBound - lowBound > 1)
    {
      size_t middle = (lowBound + highBound) / 2;
      left_.reset(new SegmentTree(lowBound, middle, factory));
      right_.reset(new SegmentTree(middle, highBound, factory));
    }
  }


  Orthanc::IDynamicObject& SegmentTree::GetPayload() const
  {
    assert(payload_.get() != NULL);
    return *payload_;
  }


  SegmentTree& SegmentTree::GetLeftChild() const
  {
    if (IsLeaf())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
    }
    else
    {
      assert(left_.get() != NULL);
      return *left_;
    }
  }


  SegmentTree& SegmentTree::GetRightChild() const
  {
    if (IsLeaf())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
    }
    else
    {
      assert(right_.get() != NULL);
      return *right_;
    }
  }


  size_t SegmentTree::CountNodes() const
  {
    if (IsLeaf())
    {
      return 1;
    }
    else
    {
      return 1 + GetLeftChild().CountNodes() + GetRightChild().CountNodes();
    }
  }


  void SegmentTree::VisitSegment(size_t low,
                                 size_t high,
                                 IVisitor& visitor) const
  {
    if (low >= high)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
    
    assert(payload_.get() != NULL);
    
    // Aliases to use the same variable names as in the textbook
    const size_t& b = low;
    const size_t& e = high;
    const size_t& bv = GetLowBound();
    const size_t& ev = GetHighBound();
    
    if (b <= bv &&
        ev <= e)
    {
      // The segment of this node is fully inside the user-provided segment
      visitor.Visit(*this, true);
    }
    else if (!IsLeaf())
    {
      // The child nodes are first updated
      size_t middle = (bv + ev) / 2;

      if (b < middle)
      {
        GetLeftChild().VisitSegment(b, e, visitor);
      }

      if (middle < e)
      {
        GetRightChild().VisitSegment(b, e, visitor);
      }
      
      // The segment of this node only partially intersects the user-provided segment
      visitor.Visit(*this, false);
    }
  }


  const SegmentTree* SegmentTree::FindLeaf(size_t low) const
  {
    if (IsLeaf())
    {
      if (low == lowBound_)
      {
        return this;
      }
      else
      {
        return NULL;
      }
    }
    else
    {
      size_t middle = (lowBound_ + highBound_) / 2;
      if (low < middle)
      {
        return GetLeftChild().FindLeaf(low);
      }
      else
      {
        return GetRightChild().FindLeaf(low);
      }
    }
  }


  const SegmentTree* SegmentTree::FindNode(size_t low,
                                           size_t high) const
  {
    if (low == lowBound_ &&
        high == highBound_)
    {
      return this;
    }
    else if (IsLeaf())
    {
      return NULL;
    }
    else
    {
      size_t middle = (lowBound_ + highBound_) / 2;
      if (low < middle)
      {
        return GetLeftChild().FindNode(low, high);
      }
      else
      {
        return GetRightChild().FindNode(low, high);
      }
    }
  }
}
