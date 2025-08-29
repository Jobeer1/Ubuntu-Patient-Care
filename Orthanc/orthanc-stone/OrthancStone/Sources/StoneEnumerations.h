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

#include "OrthancFramework.h"

#include <string>


namespace OrthancStone
{
  enum SliceOffsetMode
  {
    SliceOffsetMode_Absolute,
    SliceOffsetMode_Relative,
    SliceOffsetMode_Loop
  };

  enum ImageWindowing
  {
    ImageWindowing_Bone,
    ImageWindowing_Lung,
    ImageWindowing_Custom
  };

  enum MouseButton
  {
    MouseButton_Left,
    MouseButton_Right,
    MouseButton_Middle,
    MouseButton_None   // For instance, because of touch event
  };

  enum MouseWheelDirection
  {
    MouseWheelDirection_Up,
    MouseWheelDirection_Down
  };

  enum VolumeProjection
  {
    VolumeProjection_Axial,
    VolumeProjection_Coronal,
    VolumeProjection_Sagittal
  };

  enum ImageInterpolation
  {
    ImageInterpolation_Nearest,
    ImageInterpolation_Bilinear,
    ImageInterpolation_Trilinear
  };

  enum KeyboardModifiers
  {
    KeyboardModifiers_None = 0,
    KeyboardModifiers_Shift = (1 << 0),
    KeyboardModifiers_Control = (1 << 1),
    KeyboardModifiers_Alt = (1 << 2)
  };

  enum KeyboardKeys
  {
    KeyboardKeys_Generic = 0,

    // let's use the same ids as in javascript to avoid some conversion in WASM: https://css-tricks.com/snippets/javascript/javascript-keycodes/
    KeyboardKeys_Backspace = 8,
    KeyboardKeys_Left = 37,
    KeyboardKeys_Up = 38,
    KeyboardKeys_Right = 39,
    KeyboardKeys_Down = 40,
    KeyboardKeys_Delete = 46,

    KeyboardKeys_F1 = 112,
    KeyboardKeys_F2 = 113,
    KeyboardKeys_F3 = 114,
    KeyboardKeys_F4 = 115,
    KeyboardKeys_F5 = 116,
    KeyboardKeys_F6 = 117,
    KeyboardKeys_F7 = 118,
    KeyboardKeys_F8 = 119,
    KeyboardKeys_F9 = 120,
    KeyboardKeys_F10 = 121,
    KeyboardKeys_F11 = 122,
    KeyboardKeys_F12 = 123,
  };


  // https://dicom.nema.org/medical/dicom/current/output/chtml/part04/sect_b.5.html
  enum SopClassUid
  {
    SopClassUid_Other,
    SopClassUid_RTDose,
    SopClassUid_RTStruct,
    SopClassUid_RTPlan,
    SopClassUid_EncapsulatedPdf,
    SopClassUid_VideoEndoscopicImageStorage,
    SopClassUid_VideoMicroscopicImageStorage,
    SopClassUid_VideoPhotographicImageStorage,
    SopClassUid_DicomSeg,

    // All the possible DICOM-SR
    SopClassUid_BasicTextSR,
    SopClassUid_EnhancedSR,
    SopClassUid_ComprehensiveSR,
    SopClassUid_Comprehensive3DSR,
    SopClassUid_ExtensibleSR,
    SopClassUid_MammographyCADSR,
    SopClassUid_ChestCADSR,
    SopClassUid_XRayRadiationDoseSR,
    SopClassUid_RadiopharmaceuticalRadiationDoseSR,
    SopClassUid_ColonCADSR,
    SopClassUid_ImplantationPlanSR,
    SopClassUid_AcquisitionContextSR,
    SopClassUid_SimplifiedAdultEchoSR,
    SopClassUid_PatientRadiationDoseSR,
    SopClassUid_PlannedImagingAgentAdministrationSR,
    SopClassUid_PerformedImagingAgentAdministrationSR,
    SopClassUid_EnhancedXRayRadiationDoseSR,
    SopClassUid_WaveformAnnotationSR
  };

  enum SeriesThumbnailType
  {
    SeriesThumbnailType_NotLoaded = 1,  // "SeriesThumbnailsLoader" has not information about this series yet
    SeriesThumbnailType_Unsupported = 2,  // The remote server cannot decode this image
    SeriesThumbnailType_Pdf = 3,
    SeriesThumbnailType_Video = 4,
    SeriesThumbnailType_Image = 5,
    SeriesThumbnailType_StructuredReport = 6
  };

  enum BitmapAnchor
  {
    BitmapAnchor_BottomLeft,
    BitmapAnchor_BottomCenter,
    BitmapAnchor_BottomRight,
    BitmapAnchor_CenterLeft,
    BitmapAnchor_Center,
    BitmapAnchor_CenterRight,
    BitmapAnchor_TopLeft,
    BitmapAnchor_TopCenter,
    BitmapAnchor_TopRight
  };

  enum SliceAction
  {
    SliceAction_FastPlus,
    SliceAction_Plus,
    SliceAction_None,
    SliceAction_Minus,
    SliceAction_FastMinus
  };

  enum MouseAction
  {
    MouseAction_Pan,
    MouseAction_Zoom,
    MouseAction_Rotate,
    MouseAction_GrayscaleWindowing,
    MouseAction_MagnifyingGlass,
    MouseAction_None
  };

  enum Units
  {
    Units_Millimeters,
    Units_Pixels
  };
    
  SopClassUid StringToSopClassUid(const std::string& source);

  void ComputeWindowing(float& targetCenter,
                        float& targetWidth,
                        ImageWindowing windowing,
                        float customCenter,
                        float customWidth);

  void ComputeAnchorTranslation(double& deltaX /* out */,
                                double& deltaY /* out */,
                                BitmapAnchor anchor,
                                unsigned int bitmapWidth,
                                unsigned int bitmapHeight,
                                unsigned int border = 0);

  SeriesThumbnailType GetSeriesThumbnailType(SopClassUid sopClassUid);

  bool IsStructuredReport(SopClassUid sopClassUid);
}
