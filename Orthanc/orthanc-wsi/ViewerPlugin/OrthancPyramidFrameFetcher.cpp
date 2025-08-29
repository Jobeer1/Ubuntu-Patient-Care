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


#include "../Framework/PrecompiledHeadersWSI.h"
#include "OrthancPyramidFrameFetcher.h"

#include "../Framework/Inputs/OnTheFlyPyramid.h"

#include <DicomFormat/DicomImageInformation.h>
#include <DicomFormat/DicomMap.h>
#include <Images/Image.h>
#include <Images/ImageProcessing.h>

#include "../Resources/Orthanc/Plugins/OrthancPluginCppWrapper.h"


namespace OrthancWSI
{
  OrthancPyramidFrameFetcher::OrthancPyramidFrameFetcher(OrthancStone::IOrthancConnection* orthanc,
                                                         bool smooth) :
    orthanc_(orthanc),
    smooth_(smooth),
    tileWidth_(512),
    tileHeight_(512),
    paddingX_(0),
    paddingY_(0),
    defaultBackgroundRed_(0),
    defaultBackgroundGreen_(0),
    defaultBackgroundBlue_(0)
  {
    if (orthanc == NULL)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_NullPointer);
    }
  }


  void OrthancPyramidFrameFetcher::SetTileWidth(unsigned int tileWidth)
  {
    if (tileWidth <= 2)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
    else
    {
      tileWidth_ = tileWidth;
    }
  }


  void OrthancPyramidFrameFetcher::SetTileHeight(unsigned int tileHeight)
  {
    if (tileHeight <= 2)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
    else
    {
      tileHeight_ = tileHeight;
    }
  }


  void OrthancPyramidFrameFetcher::SetDefaultBackgroundColor(uint8_t red,
                                                             uint8_t green,
                                                             uint8_t blue)
  {
    defaultBackgroundRed_ = red;
    defaultBackgroundGreen_ = green;
    defaultBackgroundBlue_ = blue;
  }


  DecodedTiledPyramid* OrthancPyramidFrameFetcher::Fetch(const std::string &instanceId,
                                                         unsigned frameNumber)
  {
    OrthancPlugins::MemoryBuffer buffer;
    buffer.GetDicomInstance(instanceId.c_str());

    OrthancPlugins::DicomInstance dicom(buffer.GetData(), buffer.GetSize());

    Json::Value tags;
    dicom.GetJson(tags);

    Orthanc::DicomMap m;
    m.FromDicomAsJson(tags);

    Orthanc::DicomImageInformation info(m);

    uint8_t backgroundRed, backgroundGreen, backgroundBlue;

    if (info.GetPhotometricInterpretation() == Orthanc::PhotometricInterpretation_Monochrome1 ||
        info.GetPhotometricInterpretation() == Orthanc::PhotometricInterpretation_Monochrome2)
    {
      backgroundRed = 0;
      backgroundGreen = 0;
      backgroundBlue = 0;
    }
    else
    {
      backgroundRed = defaultBackgroundRed_;
      backgroundGreen = defaultBackgroundGreen_;
      backgroundBlue = defaultBackgroundBlue_;
    }

    std::unique_ptr<OrthancPlugins::OrthancImage> frame(dicom.GetDecodedFrame(frameNumber));

    unsigned int paddedWidth, paddedHeight;

    if (paddingX_ >= 2)
    {
      paddedWidth = OrthancWSI::CeilingDivision(frame->GetWidth(), paddingX_) * paddingX_;
    }
    else
    {
      paddedWidth = frame->GetWidth();
    }

    if (paddingY_ >= 2)
    {
      paddedHeight = OrthancWSI::CeilingDivision(frame->GetHeight(), paddingY_) * paddingY_;
    }
    else
    {
      paddedHeight = frame->GetHeight();
    }


    Orthanc::PixelFormat sourceFormat, targetFormat;
    switch (frame->GetPixelFormat())
    {
      case OrthancPluginPixelFormat_RGB24:
        sourceFormat = Orthanc::PixelFormat_RGB24;
        targetFormat = Orthanc::PixelFormat_RGB24;
        break;

      case OrthancPluginPixelFormat_Grayscale8:
        sourceFormat = Orthanc::PixelFormat_Grayscale8;
        targetFormat = Orthanc::PixelFormat_Grayscale8;
        break;

      case OrthancPluginPixelFormat_Grayscale16:
        sourceFormat = Orthanc::PixelFormat_Grayscale16;
        targetFormat = Orthanc::PixelFormat_Grayscale8;
        break;

      case OrthancPluginPixelFormat_SignedGrayscale16:
        sourceFormat = Orthanc::PixelFormat_SignedGrayscale16;
        targetFormat = Orthanc::PixelFormat_Grayscale8;
        break;

      default:
        throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
    }


    std::unique_ptr<Orthanc::ImageAccessor> rendered(new Orthanc::Image(targetFormat, paddedWidth, paddedHeight, false));

    if (paddedWidth != frame->GetWidth() ||
        paddedHeight != frame->GetHeight())
    {
      Orthanc::ImageProcessing::Set(*rendered, backgroundRed, backgroundGreen, backgroundBlue, 255 /* alpha */);
    }


    {
      Orthanc::ImageAccessor target;
      rendered->GetRegion(target, 0, 0, frame->GetWidth(), frame->GetHeight());

      Orthanc::ImageAccessor source;
      source.AssignReadOnly(sourceFormat, frame->GetWidth(), frame->GetHeight(), frame->GetPitch(), frame->GetBuffer());

      Orthanc::ImageProcessing::RenderDefaultWindow(target, info, source);
    }


    std::unique_ptr<DecodedTiledPyramid> result(new OnTheFlyPyramid(rendered.release(), tileWidth_, tileHeight_, smooth_));
    result->SetBackgroundColor(backgroundRed, backgroundGreen, backgroundBlue);

    return result.release();
  }
}
