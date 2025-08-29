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


#include "GlyphAlphabet.h"

#include "../Toolbox/DynamicBitmap.h"

#include <OrthancException.h>
#include <Toolbox.h>


namespace OrthancStone
{
  void GlyphAlphabet::Clear()
  {
    for (Content::const_iterator it = content_.begin(); it != content_.end(); ++it)
    {
      assert(it->second != NULL);
      delete it->second;
    }
    content_.clear();
    lineHeight_ = 0;
  }
    
    
  void GlyphAlphabet::Register(uint32_t unicode,
                               const Glyph& glyph,
                               Orthanc::IDynamicObject* payload)
  {
    std::unique_ptr<Orthanc::IDynamicObject> protection(payload);
      
    // Don't add twice the same character
    if (content_.find(unicode) == content_.end())
    {
      std::unique_ptr<Glyph> raii(new Glyph(glyph));
        
      if (payload != NULL)
      {
        raii->SetPayload(protection.release());
      }

      content_[unicode] = raii.release();

      lineHeight_ = std::max(lineHeight_, glyph.GetLineHeight());
    }
  }


  void GlyphAlphabet::Register(FontRenderer& renderer,
                               uint32_t unicode)
  {
    std::unique_ptr<Glyph>  glyph(renderer.Render(unicode));
      
    if (glyph.get() != NULL)
    {
      Register(unicode, *glyph, glyph->ReleasePayload());
    }
  }
    

  void GlyphAlphabet::Register(FontRenderer& renderer,
                               const std::string& utf8)
  {
    size_t pos = 0;
    while (pos < utf8.size())
    {
      uint32_t unicode;
      size_t size;
      Orthanc::Toolbox::Utf8ToUnicodeCharacter(unicode, size, utf8, pos);

      if (unicode != '\r' &&
          unicode != '\n')
      {
        Register(renderer, unicode);
      }

      pos += size;
    }
  }


#if ORTHANC_ENABLE_LOCALE == 1
  bool GlyphAlphabet::GetUnicodeFromCodepage(uint32_t& unicode,
                                             unsigned int index,
                                             Orthanc::Encoding encoding)
  {
    if (index > 255)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
      
    std::string character;
    character.resize(1);
    character[0] = static_cast<unsigned char>(index);
    
#if ORTHANC_FRAMEWORK_VERSION_IS_ABOVE(1, 12, 9)
    std::string utf8 = Orthanc::Toolbox::ConvertToUtf8(character, encoding, false /* no code extensions */,
                                                       false /* don't skip backslashes */);
#else
    std::string utf8 = Orthanc::Toolbox::ConvertToUtf8(character, encoding, false /* no code extensions */);
#endif
      
    if (utf8.empty())
    {
      // This character is not available in this codepage
      return false;
    }
    else
    {
      size_t length;
      Orthanc::Toolbox::Utf8ToUnicodeCharacter(unicode, length, utf8, 0);
      assert(length != 0);
      return true;
    }
  }
#endif


  void GlyphAlphabet::Apply(IGlyphVisitor& visitor) const
  {
    for (Content::const_iterator it = content_.begin(); it != content_.end(); ++it)
    {
      assert(it->second != NULL);
      visitor.Visit(it->first, *it->second);
    }
  }


  void GlyphAlphabet::Apply(ITextVisitor& visitor,
                            const std::string& utf8) const
  {
    DynamicBitmap empty(Orthanc::PixelFormat_Grayscale8, 0, 0, true);

    size_t pos = 0;
    int x = 0;
    int y = 0;

    while (pos < utf8.size())
    {
      if (utf8[pos] == '\r')
      {
        // Ignore carriage return
        pos++;
      }
      else if (utf8[pos] == '\n')
      {
        // This is a newline character
        x = 0;
        y += static_cast<int>(lineHeight_);

        pos++;
      }
      else
      {         
        uint32_t unicode;
        size_t length;
        Orthanc::Toolbox::Utf8ToUnicodeCharacter(unicode, length, utf8, pos);

        if (unicode == '\r' ||
            IsDeviceControlCharacter(unicode))
        {
          /**
           * This is a device control character, which is used to change the color of the text.
           * Make sure that such a character is invisible (i.e., zero width and height).
           **/
          visitor.Visit(unicode, x, y, 0, 0, &empty);
        }
        else
        {
          Content::const_iterator glyph = content_.find(unicode);

          if (glyph != content_.end())
          {
            assert(glyph->second != NULL);
            const Orthanc::IDynamicObject* payload =
              (glyph->second->HasPayload() ? &glyph->second->GetPayload() : NULL);
            
            visitor.Visit(unicode,
                          x + glyph->second->GetOffsetLeft(),
                          y + glyph->second->GetOffsetTop(),
                          glyph->second->GetWidth(),
                          glyph->second->GetHeight(),
                          payload);
            x += glyph->second->GetAdvanceX();
          }
        }
        
        assert(length != 0);
        pos += length;
      }
    }
  }


  bool GlyphAlphabet::IsDeviceControlCharacter(uint32_t unicode)
  {
    return (unicode == 0x11 ||
            unicode == 0x12 ||
            unicode == 0x13 ||
            unicode == 0x14);
  }


  static void Copy(std::string& target,
                   const std::string& source,
                   size_t start,
                   size_t end,
                   bool ignoreDeviceControl)
  {
    size_t i = start;
    while (i < end)
    {
      uint32_t unicode;
      size_t length;
      Orthanc::Toolbox::Utf8ToUnicodeCharacter(unicode, length, source, i);
      assert(length != 0);

      if (unicode != '\r' &&
          (!ignoreDeviceControl || !GlyphAlphabet::IsDeviceControlCharacter(unicode)))
      {
        for (size_t j = 0; j < length; j++)
        {
          target.push_back(source[i + j]);
        }
      }

      i += length;
    }

    if (i != end)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
    }
  }


  void GlyphAlphabet::IndentUtf8(std::string& target,
                                 const std::string& source,
                                 unsigned int maxLineWidth,
                                 bool ignoreDeviceControl /* whether DC1, DC2, DC3, and DC4 codes are used to change color */)
  {
    if (maxLineWidth == 0)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }

    target.clear();
    target.reserve(source.size());

    unsigned int currentLineWidth = 0;

    size_t pos = 0;
    while (pos < source.size())
    {
      if (source[pos] == ' ')
      {
        pos++;
      }
      else if (source[pos] == '\n')
      {
        target.push_back('\n');
        currentLineWidth = 0;
        pos++;
      }
      else
      {
        // We are at the beginning of a word
        size_t wordEnd = pos;
        unsigned int wordLength = 0;  // Will be smaller than "wordEnd - pos" because of UTF8
        while (wordEnd < source.size())
        {
          uint32_t unicode;
          size_t length;
          Orthanc::Toolbox::Utf8ToUnicodeCharacter(unicode, length, source, wordEnd);
          assert(length != 0);

          if (unicode == '\r' ||
              (ignoreDeviceControl && IsDeviceControlCharacter(unicode)))
          {
            // Ignore carriage returns (and possibly device control characters)
            wordEnd += length;
          }
          else if (unicode == '\n' ||
                   unicode == ' ')
          {
            break;  // We found the end of the word
          }
          else
          {
            wordEnd += length;
            wordLength ++;
          }
        }

        if (wordLength != 0)
        {
          if (currentLineWidth == 0)
          {
            Copy(target, source, pos, wordEnd, ignoreDeviceControl);
            currentLineWidth = wordLength;
          }
          else
          {
            if (currentLineWidth + wordLength + 1 <= maxLineWidth)
            {
              target.push_back(' ');
              Copy(target, source, pos, wordEnd, ignoreDeviceControl);
              currentLineWidth += wordLength + 1;
            }
            else
            {
              target.push_back('\n');
              Copy(target, source, pos, wordEnd, ignoreDeviceControl);
              currentLineWidth = wordLength;
            }
          }
        }

        pos = wordEnd;
      }
    }
  }
}
