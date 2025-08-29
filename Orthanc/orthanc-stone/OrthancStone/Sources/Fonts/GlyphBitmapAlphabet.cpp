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


#include "GlyphBitmapAlphabet.h"

#include "TextBoundingBox.h"
#include "../Toolbox/DynamicBitmap.h"
#include "../Toolbox/ImageToolbox.h"

#include <Images/Image.h>
#include <Images/ImageProcessing.h>

namespace OrthancStone
{
  class GlyphBitmapAlphabet::RenderTextVisitor : public GlyphAlphabet::ITextVisitor
  {
  private:
    Orthanc::ImageAccessor&     target_;
    const GlyphBitmapAlphabet&  that_;
    int                         offsetX_;
    int                         offsetY_;
    bool                        useColors_;
    Color                       activeColor_;
    Color                       color1_;
    Color                       color2_;
    Color                       color3_;
    Color                       color4_;
      
  public:
    RenderTextVisitor(Orthanc::ImageAccessor&  target,
                      const GlyphBitmapAlphabet&  that,
                      int  offsetX,
                      int  offsetY) :
      target_(target),
      that_(that),
      offsetX_(offsetX),
      offsetY_(offsetY),
      useColors_(false)
    {
    }

    void SetColors(const Color& color1,
                   const Color& color2,
                   const Color& color3,
                   const Color& color4)
    {
      useColors_ = true;
      activeColor_ = color1;
      color1_ = color1;
      color2_ = color2;
      color3_ = color3;
      color4_ = color4;
    }

    virtual void Visit(uint32_t unicode,
                       int x,
                       int y,
                       unsigned int width,
                       unsigned int height,
                       const Orthanc::IDynamicObject* payload) ORTHANC_OVERRIDE
    {
      int left = x + offsetX_;
      int top = y + offsetY_;

      assert(payload != NULL);
      const DynamicBitmap& glyph = *dynamic_cast<const DynamicBitmap*>(payload);
        
      assert(left >= 0 &&
             top >= 0 &&
             static_cast<unsigned int>(left) + width <= target_.GetWidth() &&
             static_cast<unsigned int>(top) + height <= target_.GetHeight() &&
             width == glyph.GetBitmap().GetWidth() &&
             height == glyph.GetBitmap().GetHeight());

      if (useColors_)
      {
        if (unicode == 0x11)
        {
          activeColor_ = color1_;
        }
        else if (unicode == 0x12)
        {
          activeColor_ = color2_;
        }
        else if (unicode == 0x13)
        {
          activeColor_ = color3_;
        }
        else if (unicode == 0x14)
        {
          activeColor_ = color4_;
        }
        else
        {
          Orthanc::ImageAccessor region;
          target_.GetRegion(region, left, top, width, height);

          std::unique_ptr<Orthanc::ImageAccessor> colorized(ImageToolbox::Colorize(glyph.GetBitmap(), activeColor_));
          Orthanc::ImageProcessing::Copy(region, *colorized);
        }
      }
      else
      {
        Orthanc::ImageAccessor region;
        target_.GetRegion(region, left, top, width, height);
        Orthanc::ImageProcessing::Copy(region, glyph.GetBitmap());
      }
    }
  };
  
    
#if ORTHANC_ENABLE_LOCALE == 1
  void GlyphBitmapAlphabet::LoadCodepage(FontRenderer& renderer,
                                         Orthanc::Encoding codepage)
  {
    for (unsigned int i = 0; i < 256; i++)
    {
      uint32_t unicode;
      if (GlyphAlphabet::GetUnicodeFromCodepage(unicode, i, codepage))
      {
        AddUnicodeCharacter(renderer, unicode);
      }
    }
  }
#endif

    
  Orthanc::ImageAccessor* GlyphBitmapAlphabet::RenderText(const std::string& utf8) const
  {
    TextBoundingBox box(alphabet_, utf8);

    std::unique_ptr<Orthanc::ImageAccessor> bitmap(
      new Orthanc::Image(Orthanc::PixelFormat_Grayscale8,
                         box.GetWidth(), box.GetHeight(),
                         true /* force minimal pitch, to be used in OpenGL textures */));

    Orthanc::ImageProcessing::Set(*bitmap, 0);

    RenderTextVisitor visitor(*bitmap, *this, -box.GetLeft(), -box.GetTop());
    alphabet_.Apply(visitor, utf8);

    return bitmap.release();
  }


  Orthanc::ImageAccessor* GlyphBitmapAlphabet::RenderText(FontRenderer& font,
                                                          const std::string& utf8)
  {
    alphabet_.Register(font, utf8);
    return RenderText(utf8);
  }


  Orthanc::ImageAccessor* GlyphBitmapAlphabet::RenderColorText(FontRenderer& font,
                                                               const std::string& utf8,
                                                               const Color color1,
                                                               const Color color2,
                                                               const Color color3,
                                                               const Color color4)
  {
    alphabet_.Register(font, utf8);

    TextBoundingBox box(alphabet_, utf8);

    std::unique_ptr<Orthanc::ImageAccessor> bitmap(
      new Orthanc::Image(Orthanc::PixelFormat_RGB24,
                         box.GetWidth(), box.GetHeight(),
                         true /* force minimal pitch, to be used in OpenGL textures */));

    Orthanc::ImageProcessing::Set(*bitmap, 0);

    RenderTextVisitor visitor(*bitmap, *this, -box.GetLeft(), -box.GetTop());
    visitor.SetColors(color1, color2, color3, color4);

    alphabet_.Apply(visitor, utf8);

    return bitmap.release();
  }
}
