/**
 * Orthanc - A Lightweight, RESTful DICOM Store
 * Copyright (C) 2012-2016 Sebastien Jodogne, Medical Physics
 * Department, University Hospital of Liege, Belgium
 * Copyright (C) 2017-2023 Osimis S.A., Belgium
 * Copyright (C) 2024-2025 Orthanc Team SRL, Belgium
 * Copyright (C) 2021-2025 Sebastien Jodogne, ICTEAM UCLouvain, Belgium
 *
 * This program is free software: you can redistribute it and/or
 * modify it under the terms of the GNU Affero General Public License
 * as published by the Free Software Foundation, either version 3 of
 * the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Affero General Public License for more details.
 * 
 * You should have received a copy of the GNU Affero General Public License
 * along with this program. If not, see <http://www.gnu.org/licenses/>.
 **/


#pragma once

namespace OrthancWSI
{
  class ImagedVolumeParameters
  {
  private:
    bool   hasWidth_;
    bool   hasHeight_;
    float  width_;
    float  height_;
    float  depth_;
    float  offsetX_;
    float  offsetY_;

  public:
    ImagedVolumeParameters();

    bool HasWidth() const
    {
      return hasWidth_;
    }

    bool HasHeight() const
    {
      return hasHeight_;
    }
    
    float GetWidth() const;

    float GetHeight() const;
    
    float GetDepth() const
    {
      return depth_;
    }

    float GetOffsetX() const
    {
      return offsetX_;
    }

    float GetOffsetY() const
    {
      return offsetY_;
    }

    void SetWidth(float width);
    
    void SetHeight(float height);
    
    void SetDepth(float depth);
    
    void SetOffsetX(float offset)
    {
      offsetX_ = offset;
    }
    
    void SetOffsetY(float offset)
    {
      offsetY_ = offset;
    }

    void GetLocation(float& physicalX,
                     float& physicalY,
                     unsigned int imageX,
                     unsigned int imageY,
                     unsigned int totalWidth,
                     unsigned int totalHeight) const;
  };
}
