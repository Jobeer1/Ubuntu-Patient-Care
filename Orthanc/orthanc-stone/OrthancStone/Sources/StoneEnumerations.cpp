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


#include "StoneEnumerations.h"

#include <Logging.h>
#include <OrthancException.h>
#include <Toolbox.h>

namespace OrthancStone
{  
  SopClassUid StringToSopClassUid(const std::string& source)
  {
    std::string s = Orthanc::Toolbox::StripSpaces(source);

    if (s == "1.2.840.10008.5.1.4.1.1.481.2")
    {
      return SopClassUid_RTDose;
    }
    else if (s == "1.2.840.10008.5.1.4.1.1.481.5")
    {
      return SopClassUid_RTPlan;
    }
    else if (s == "1.2.840.10008.5.1.4.1.1.481.3")
    {
      return SopClassUid_RTStruct;
    }
    else if (s == "1.2.840.10008.5.1.4.1.1.104.1")
    {
      return SopClassUid_EncapsulatedPdf;
    }
    else if (s == "1.2.840.10008.5.1.4.1.1.77.1.1.1")
    {
      return SopClassUid_VideoEndoscopicImageStorage;
    }      
    else if (s == "1.2.840.10008.5.1.4.1.1.77.1.2.1")
    {
      return SopClassUid_VideoMicroscopicImageStorage;
    }      
    else if (s == "1.2.840.10008.5.1.4.1.1.77.1.4.1")
    {
      return SopClassUid_VideoPhotographicImageStorage;
    }
    else if (s == "1.2.840.10008.5.1.4.1.1.66.4")
    {
      return SopClassUid_DicomSeg;
    }
    else if (s == "1.2.840.10008.5.1.4.1.1.88.11")
    {
      return SopClassUid_BasicTextSR;
    }
    else if (s == "1.2.840.10008.5.1.4.1.1.88.22")
    {
      return SopClassUid_EnhancedSR;
    }
    else if (s == "1.2.840.10008.5.1.4.1.1.88.33")
    {
      return SopClassUid_ComprehensiveSR;
    }
    else if (s == "1.2.840.10008.5.1.4.1.1.88.34")
    {
      return SopClassUid_Comprehensive3DSR;
    }
    else if (s == "1.2.840.10008.5.1.4.1.1.88.35")
    {
      return SopClassUid_ExtensibleSR;
    }
    else if (s == "1.2.840.10008.5.1.4.1.1.88.50")
    {
      return SopClassUid_MammographyCADSR;
    }
    else if (s == "1.2.840.10008.5.1.4.1.1.88.65")
    {
      return SopClassUid_ChestCADSR;
    }
    else if (s == "1.2.840.10008.5.1.4.1.1.88.67")
    {
      return SopClassUid_XRayRadiationDoseSR;
    }
    else if (s == "1.2.840.10008.5.1.4.1.1.88.68")
    {
      return SopClassUid_RadiopharmaceuticalRadiationDoseSR;
    }
    else if (s == "1.2.840.10008.5.1.4.1.1.88.69")
    {
      return SopClassUid_ColonCADSR;
    }
    else if (s == "1.2.840.10008.5.1.4.1.1.88.70")
    {
      return SopClassUid_ImplantationPlanSR;
    }
    else if (s == "1.2.840.10008.5.​1.​4.​1.​1.​88.​71")
    {
      return SopClassUid_AcquisitionContextSR;
    }
    else if (s == "1.2.840.10008.5.​1.​4.​1.​1.​88.​72")
    {
      return SopClassUid_SimplifiedAdultEchoSR;
    }
    else if (s == "1.2.840.10008.5.​1.​4.​1.​1.​88.​73")
    {
      return SopClassUid_PatientRadiationDoseSR;
    }
    else if (s == "1.2.840.10008.5.​1.​4.​1.​1.​88.​74")
    {
      return SopClassUid_PlannedImagingAgentAdministrationSR;
    }
    else if (s == "1.2.840.10008.5.​1.​4.​1.​1.​88.​75")
    {
      return SopClassUid_PerformedImagingAgentAdministrationSR;
    }
    else if (s == "1.2.840.10008.5.​1.​4.​1.​1.​88.​76")
    {
      return SopClassUid_EnhancedXRayRadiationDoseSR;
    }
    else if (s == "1.2.840.10008.5.​1.​4.​1.​1.​88.​77")
    {
      return SopClassUid_WaveformAnnotationSR;
    }
    else
    {
      //LOG(INFO) << "Other SOP class UID: " << source;
      return SopClassUid_Other;
    }
  }  


  void ComputeWindowing(float& targetCenter,
                        float& targetWidth,
                        ImageWindowing windowing,
                        float customCenter,
                        float customWidth)
  {
    switch (windowing)
    {
      case ImageWindowing_Custom:
        targetCenter = customCenter;
        targetWidth = customWidth;
        break;

      case ImageWindowing_Bone:
        targetCenter = 300;
        targetWidth = 2000;
        break;

      case ImageWindowing_Lung:
        targetCenter = -600;
        targetWidth = 1600;
        break;

      default:
        throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
  }

  
  void ComputeAnchorTranslation(double& deltaX,
                                double& deltaY,
                                BitmapAnchor anchor,
                                unsigned int bitmapWidth,
                                unsigned int bitmapHeight,
                                unsigned int border)
  {
    double dw = static_cast<double>(bitmapWidth);
    double dh = static_cast<double>(bitmapHeight);

    switch (anchor)
    {
      case BitmapAnchor_TopLeft:
        deltaX = 0;
        deltaY = 0;
        break;
        
      case BitmapAnchor_TopCenter:
        deltaX = -dw / 2.0;
        deltaY = 0;
        break;
        
      case BitmapAnchor_TopRight:
        deltaX = -dw;
        deltaY = 0;
        break;
        
      case BitmapAnchor_CenterLeft:
        deltaX = 0;
        deltaY = -dh / 2.0;
        break;
        
      case BitmapAnchor_Center:
        deltaX = -dw / 2.0;
        deltaY = -dh / 2.0;
        break;
        
      case BitmapAnchor_CenterRight:
        deltaX = -dw;
        deltaY = -dh / 2.0;
        break;
        
      case BitmapAnchor_BottomLeft:
        deltaX = 0;
        deltaY = -dh;
        break;
        
      case BitmapAnchor_BottomCenter:
        deltaX = -dw / 2.0;
        deltaY = -dh;
        break;
        
      case BitmapAnchor_BottomRight:
        deltaX = -dw;
        deltaY = -dh;
        break;
        
      default:
        throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }    

    if (border != 0)
    {
      double b = static_cast<double>(border);

      switch (anchor)
      {
        case BitmapAnchor_TopLeft:
        case BitmapAnchor_TopCenter:
        case BitmapAnchor_TopRight:
          deltaY += b;
          break;
        
        case BitmapAnchor_BottomLeft:
        case BitmapAnchor_BottomCenter:
        case BitmapAnchor_BottomRight:
          deltaY -= b;
          break;
        
        default:
          break;
      }    

      switch (anchor)
      {
        case BitmapAnchor_TopLeft:
        case BitmapAnchor_CenterLeft:
        case BitmapAnchor_BottomLeft:
          deltaX += b;
          break;

        case BitmapAnchor_CenterRight:
        case BitmapAnchor_TopRight:
        case BitmapAnchor_BottomRight:
          deltaX -= b;
          break;
        
        default:
          break;
      }
    }
  }


  SeriesThumbnailType GetSeriesThumbnailType(SopClassUid sopClassUid)
  {
    switch (sopClassUid)
    {
      case SopClassUid_EncapsulatedPdf:
        return SeriesThumbnailType_Pdf;
        
      case SopClassUid_VideoEndoscopicImageStorage:
      case SopClassUid_VideoMicroscopicImageStorage:
      case SopClassUid_VideoPhotographicImageStorage:
        return SeriesThumbnailType_Video;

      default:
        break;
    }

    if (IsStructuredReport(sopClassUid))
    {
      return SeriesThumbnailType_StructuredReport;
    }
    else
    {
      return SeriesThumbnailType_Unsupported;
    }
  }


  bool IsStructuredReport(SopClassUid sopClassUid)
  {
    return (sopClassUid == SopClassUid_BasicTextSR ||
            sopClassUid == SopClassUid_EnhancedSR ||
            sopClassUid == SopClassUid_ComprehensiveSR ||
            sopClassUid == SopClassUid_Comprehensive3DSR ||
            sopClassUid == SopClassUid_ExtensibleSR ||
            sopClassUid == SopClassUid_MammographyCADSR ||
            sopClassUid == SopClassUid_ChestCADSR ||
            sopClassUid == SopClassUid_XRayRadiationDoseSR ||
            sopClassUid == SopClassUid_RadiopharmaceuticalRadiationDoseSR ||
            sopClassUid == SopClassUid_ColonCADSR ||
            sopClassUid == SopClassUid_ImplantationPlanSR ||
            sopClassUid == SopClassUid_AcquisitionContextSR ||
            sopClassUid == SopClassUid_SimplifiedAdultEchoSR ||
            sopClassUid == SopClassUid_PatientRadiationDoseSR ||
            sopClassUid == SopClassUid_PlannedImagingAgentAdministrationSR ||
            sopClassUid == SopClassUid_PerformedImagingAgentAdministrationSR ||
            sopClassUid == SopClassUid_EnhancedXRayRadiationDoseSR ||
            sopClassUid == SopClassUid_WaveformAnnotationSR);
  }
}
