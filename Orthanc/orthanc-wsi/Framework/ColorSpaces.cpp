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


#include "ColorSpaces.h"

#include <SerializationToolbox.h>
#include <Toolbox.h>

#include <boost/math/special_functions/round.hpp>


namespace OrthancWSI
{
  RGBColor::RGBColor(const sRGBColor& srgb)
  {
    if (srgb.GetR() < 0)
    {
      r_ = 0;
    }
    else if (srgb.GetR() >= 1)
    {
      r_ = 255;
    }
    else
    {
      r_ = boost::math::iround(srgb.GetR() * 255.0f);
    }

    if (srgb.GetG() < 0)
    {
      g_ = 0;
    }
    else if (srgb.GetG() >= 1)
    {
      g_ = 255;
    }
    else
    {
      g_ = boost::math::iround(srgb.GetG() * 255.0f);
    }

    if (srgb.GetB() < 0)
    {
      b_ = 0;
    }
    else if (srgb.GetB() >= 1)
    {
      b_ = 255;
    }
    else
    {
      b_ = boost::math::iround(srgb.GetB() * 255.0f);
    }
  }


  sRGBColor::sRGBColor(const RGBColor& rgb)
  {
    r_ = static_cast<float>(rgb.GetR()) / 255.0f;
    g_ = static_cast<float>(rgb.GetG()) / 255.0f;
    b_ = static_cast<float>(rgb.GetB()) / 255.0f;
  }


  static float ApplyGammaXYZ(float value)
  {
    // https://www.image-engineering.de/library/technotes/958-how-to-convert-between-srgb-and-ciexyz
    if (value <= 0.0031308f)
    {
      return value * 12.92f;
    }
    else
    {
      return 1.055f * powf(value, 1.0f / 2.4f) - 0.055f;
    }
  }


  sRGBColor::sRGBColor(const XYZColor& xyz)
  {
    // https://en.wikipedia.org/wiki/SRGB#From_CIE_XYZ_to_sRGB
    // https://www.image-engineering.de/library/technotes/958-how-to-convert-between-srgb-and-ciexyz
    const float sr =  3.2404542f * xyz.GetX() - 1.5371385f * xyz.GetY() - 0.4985314f * xyz.GetZ();
    const float sg = -0.9692660f * xyz.GetX() + 1.8760108f * xyz.GetY() + 0.0415560f * xyz.GetZ();
    const float sb =  0.0556434f * xyz.GetX() - 0.2040259f * xyz.GetY() + 1.0572252f * xyz.GetZ();

    r_ = ApplyGammaXYZ(sr);
    g_ = ApplyGammaXYZ(sg);
    b_ = ApplyGammaXYZ(sb);
  }


  static float LinearizeXYZ(float value)
  {
    // https://www.image-engineering.de/library/technotes/958-how-to-convert-between-srgb-and-ciexyz
    if (value <= 0.04045f)
    {
      return value / 12.92f;
    }
    else
    {
      return powf((value + 0.055f) / 1.055f, 2.4f);
    }
  }


  XYZColor::XYZColor(const sRGBColor& srgb)
  {
    // https://en.wikipedia.org/wiki/SRGB#From_sRGB_to_CIE_XYZ
    // https://www.image-engineering.de/library/technotes/958-how-to-convert-between-srgb-and-ciexyz
    const float linearizedR = LinearizeXYZ(srgb.GetR());
    const float linearizedG = LinearizeXYZ(srgb.GetG());
    const float linearizedB = LinearizeXYZ(srgb.GetB());

    x_ = 0.4124564f * linearizedR + 0.3575761f * linearizedG + 0.1804375f * linearizedB;
    y_ = 0.2126729f * linearizedR + 0.7151522f * linearizedG + 0.0721750f * linearizedB;
    z_ = 0.0193339f * linearizedR + 0.1191920f * linearizedG + 0.9503041f * linearizedB;
  }


  static const float LAB_DELTA = 6.0f / 29.0f;

  static float LABf_inv(float t)
  {
    if (t > LAB_DELTA)
    {
      return powf(t, 3.0f);
    }
    else
    {
      return 3.0f * LAB_DELTA * LAB_DELTA * (t - 4.0f / 29.0f);
    }
  }


  // Those correspond to Standard Illuminant D65
  // https://en.wikipedia.org/wiki/CIELAB_color_space#From_CIEXYZ_to_CIELAB
  static const float X_N = 95.0489f;
  static const float Y_N = 100.0f;
  static const float Z_N = 108.8840f;

  XYZColor::XYZColor(const LABColor& lab)
  {
    // https://en.wikipedia.org/wiki/CIELAB_color_space#From_CIELAB_to_CIEXYZ
    const float shared = (lab.GetL() + 16.0f) / 116.0f;

    x_ = X_N * LABf_inv(shared + lab.GetA() / 500.0f) / 100.0f;
    y_ = Y_N * LABf_inv(shared) / 100.0f;
    z_ = Z_N * LABf_inv(shared - lab.GetB() / 200.0f) / 100.0f;
  }


  static float LABf(float t)
  {
    if (t > powf(LAB_DELTA, 3.0f))
    {
      return powf(t, 1.0f / 3.0f);
    }
    else
    {
      return t / 3.0f * powf(LAB_DELTA, -2.0f) + 4.0f / 29.0f;
    }
  }


  LABColor::LABColor(const XYZColor& xyz)
  {
    // https://en.wikipedia.org/wiki/CIELAB_color_space#From_CIEXYZ_to_CIELAB

    const float fx = LABf(xyz.GetX() * 100.0f / X_N);
    const float fy = LABf(xyz.GetY() * 100.0f / Y_N);
    const float fz = LABf(xyz.GetZ() * 100.0f / Z_N);

    l_ = 116.0f * fy - 16.0f;
    a_ = 500.0f * (fx - fy);
    b_ = 200.0f * (fy - fz);
  }


  static uint16_t EncodeUint16(float value,
                               float minValue,
                               float maxValue)
  {
    if (value <= minValue)
    {
      return 0;
    }
    else if (value >= maxValue)
    {
      return 0xffff;
    }
    else
    {
      float lambda = (value - minValue) / (maxValue - minValue);
      assert(lambda >= 0 && lambda <= 1);
      return static_cast<uint16_t>(boost::math::iround(lambda * static_cast<float>(0xffff)));
    }
  }


  void LABColor::EncodeDicomRecommendedAbsentPixelCIELab(uint16_t target[3]) const
  {
    /**
     * "An L value linearly scaled to 16 bits, such that 0x0000
     * corresponds to an L of 0.0, and 0xFFFF corresponds to an L of
     * 100.0."
     **/
    target[0] = EncodeUint16(GetL(), 0.0f, 100.0f);

    /**
     * "An a* then a b* value, each linearly scaled to 16 bits and
     * offset to an unsigned range, such that 0x0000 corresponds to an
     * a* or b* of -128.0, 0x8080 corresponds to an a* or b* of 0.0
     * and 0xFFFF corresponds to an a* or b* of 127.0"
     **/
    target[1] = EncodeUint16(GetA(), -128.0f, 127.0f);
    target[2] = EncodeUint16(GetB(), -128.0f, 127.0f);
  }


  LABColor LABColor::DecodeDicomRecommendedAbsentPixelCIELab(uint16_t l,
                                                             uint16_t a,
                                                             uint16_t b)
  {
    return LABColor(static_cast<float>(l) / static_cast<float>(0xffff) * 100.0f,
                    -128.0f + static_cast<float>(a) / static_cast<float>(0xffff) * 255.0f,
                    -128.0f + static_cast<float>(b) / static_cast<float>(0xffff) * 255.0f);
  }


  bool LABColor::DecodeDicomRecommendedAbsentPixelCIELab(LABColor& target,
                                                         const std::string& tag)
  {
    std::vector<std::string> channels;
    Orthanc::Toolbox::TokenizeString(channels, tag, '\\');

    unsigned int l, a, b;
    if (channels.size() == 3 &&
        Orthanc::SerializationToolbox::ParseUnsignedInteger32(l, channels[0]) &&
        Orthanc::SerializationToolbox::ParseUnsignedInteger32(a, channels[1]) &&
        Orthanc::SerializationToolbox::ParseUnsignedInteger32(b, channels[2]) &&
        l <= 0xffffu &&
        a <= 0xffffu &&
        b <= 0xffffu)
    {
      target = LABColor::DecodeDicomRecommendedAbsentPixelCIELab(l, a, b);
      return true;
    }
    else
    {
      return false;
    }
  }
}
