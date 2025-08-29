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

#include <stdint.h>
#include <string>


namespace OrthancWSI
{
  class sRGBColor;
  class XYZColor;
  class LABColor;


  class RGBColor
  {
  private:
    uint8_t  r_;
    uint8_t  g_;
    uint8_t  b_;

  public:
    RGBColor(uint8_t r,
             uint8_t g,
             uint8_t b) :
      r_(r),
      g_(g),
      b_(b)
    {
    }

    explicit RGBColor(const sRGBColor& srgb);

    uint8_t GetR() const
    {
      return r_;
    }

    uint8_t GetG() const
    {
      return g_;
    }

    uint8_t GetB() const
    {
      return b_;
    }
  };


  // Those correspond to Standard Illuminant D65
  // https://en.wikipedia.org/wiki/SRGB#From_CIE_XYZ_to_sRGB
  class sRGBColor
  {
  private:
    float  r_;
    float  g_;
    float  b_;

  public:
    sRGBColor(float r,
              float g,
              float b) :
      r_(r),
      g_(g),
      b_(b)
    {
    }

    explicit sRGBColor(const RGBColor& rgb);

    explicit sRGBColor(const XYZColor& xyz);

    float GetR() const
    {
      return r_;
    }

    float GetG() const
    {
      return g_;
    }

    float GetB() const
    {
      return b_;
    }
  };


  class XYZColor
  {
  private:
    float  x_;
    float  y_;
    float  z_;

  public:
    explicit XYZColor(const sRGBColor& srgb);

    explicit XYZColor(const LABColor& lab);

    float GetX() const
    {
      return x_;
    }

    float GetY() const
    {
      return y_;
    }

    float GetZ() const
    {
      return z_;
    }
  };


  class LABColor
  {
  private:
    float  l_;
    float  a_;
    float  b_;

  public:
    LABColor() :
      l_(0),
      a_(0),
      b_(0)
    {
    }

    LABColor(float l,
             float a,
             float b) :
      l_(l),
      a_(a),
      b_(b)
    {
    }

    explicit LABColor(const XYZColor& xyz);

    float GetL() const
    {
      return l_;
    }

    float GetA() const
    {
      return a_;
    }

    float GetB() const
    {
      return b_;
    }

    void EncodeDicomRecommendedAbsentPixelCIELab(uint16_t target[3]) const;

    static LABColor DecodeDicomRecommendedAbsentPixelCIELab(uint16_t l,
                                                            uint16_t a,
                                                            uint16_t b);

    static bool DecodeDicomRecommendedAbsentPixelCIELab(LABColor& target,
                                                        const std::string& tag);
  };
}
