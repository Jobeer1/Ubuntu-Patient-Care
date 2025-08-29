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


#include "OrientedIntegerLine2D.h"

#include <cassert>
#include <map>


namespace OrthancStone
{
  namespace Internals
  {
    OrientedIntegerLine2D::OrientedIntegerLine2D(size_t x1,
                                                 size_t y1,
                                                 size_t x2,
                                                 size_t y2) :
      x1_(x1),
      y1_(y1),
      x2_(x2),
      y2_(y2)
    {
    }

    void OrientedIntegerLine2D::ExtractChains(std::list<Chain>& chains,
                                              const std::vector<OrientedIntegerLine2D>& edges)
    {
      chains.clear();
      
      typedef std::map< std::pair<size_t, size_t>, std::list<size_t> > Index;
      Index index;

      for (size_t i = 0; i < edges.size(); i++)
      {
        index[std::make_pair(edges[i].GetX1(), edges[i].GetY1())].push_back(i);
      }

      std::vector<bool> visited(edges.size(), false);

      for (size_t i = 0; i < edges.size(); i++)
      {
        if (!visited[i])
        {
          Chain chain;
          
          size_t current = i;
          
          chain.push_back(std::make_pair(edges[current].GetX1(), edges[current].GetY1()));
          
          for (;;)
          {
            visited[current] = true;

            std::pair<size_t, size_t> start(edges[current].GetX1(), edges[current].GetY1());
            std::pair<size_t, size_t> end(edges[current].GetX2(), edges[current].GetY2());
            
            assert(index.find(start) != index.end());
            index[start].pop_back();
            
            chain.push_back(end);
            Index::iterator next = index.find(end);

            if (next == index.end() /* non-closed chain */ ||
                next->second.empty())
            {
              break;
            }
            else
            {
              current = next->second.back();
            }
          }
          
          chains.push_back(chain);
        }
      }
    }
  }
}
