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


#include "DicomInstanceParameters.h"

#include "../Scene2D/ColorTextureSceneLayer.h"
#include "../Scene2D/FloatTextureSceneLayer.h"
#include "GeometryToolbox.h"
#include "ImageToolbox.h"
#include "OrthancDatasets/DicomDatasetReader.h"
#include "OrthancDatasets/DicomWebDataset.h"
#include "OrthancDatasets/OrthancNativeDataset.h"

#include <Images/Image.h>
#include <Images/ImageProcessing.h>
#include <Logging.h>
#include <OrthancException.h>
#include <SerializationToolbox.h>
#include <Toolbox.h>


namespace OrthancStone
{
  static void ExtractFrameOffsets(Vector& target,
                                  const Orthanc::DicomMap& dicom,
                                  unsigned int numberOfFrames)
  {
    // http://dicom.nema.org/medical/Dicom/2016a/output/chtml/part03/sect_C.8.8.3.2.html

    std::string increment;

    if (dicom.LookupStringValue(increment, Orthanc::DICOM_TAG_FRAME_INCREMENT_POINTER, false))
    {
      Orthanc::Toolbox::ToUpperCase(increment);

      // We only support volumes where the FrameIncrementPointer (0028,0009) (required) contains 
      // the "Grid Frame Offset Vector" tag (DICOM_TAG_GRID_FRAME_OFFSET_VECTOR)
      if (increment != "3004,000C")
      {
        LOG(WARNING) << "Bad value for the FrameIncrementPointer tags in a multiframe image";
        target.resize(0);
        return;
      }
    }

    if (!LinearAlgebra::ParseVector(target, dicom, Orthanc::DICOM_TAG_GRID_FRAME_OFFSET_VECTOR) ||
        target.size() != numberOfFrames)
    {
      LOG(ERROR) << "The frame offset information (GridFrameOffsetVector (3004,000C)) is missing in a multiframe image";

      // DO NOT use ".clear()" here, as the "Vector" class doesn't behave like std::vector!
      target.resize(0);
    }
  }


  DicomInstanceParameters::Data::Data(const Orthanc::DicomMap& dicom)
  {
    if (!dicom.LookupStringValue(studyInstanceUid_, Orthanc::DICOM_TAG_STUDY_INSTANCE_UID, false) ||
        !dicom.LookupStringValue(seriesInstanceUid_, Orthanc::DICOM_TAG_SERIES_INSTANCE_UID, false) ||
        !dicom.LookupStringValue(sopInstanceUid_, Orthanc::DICOM_TAG_SOP_INSTANCE_UID, false))
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
    }
        
    std::string s;
    if (dicom.LookupStringValue(s, Orthanc::DICOM_TAG_SOP_CLASS_UID, false))
    {
      sopClassUid_ = StringToSopClassUid(s);
    }
    else
    {
      sopClassUid_ = SopClassUid_Other;
    }

    uint32_t n;
    if (dicom.ParseUnsignedInteger32(n, Orthanc::DICOM_TAG_NUMBER_OF_FRAMES))
    {
      hasNumberOfFrames_ = true;
      numberOfFrames_ = n;
    }
    else
    {
      hasNumberOfFrames_ = false;
      numberOfFrames_ = 1;
    }

    if (!dicom.HasTag(Orthanc::DICOM_TAG_COLUMNS) ||
        !dicom.GetValue(Orthanc::DICOM_TAG_COLUMNS).ParseFirstUnsignedInteger(width_))
    {
      width_ = 0;
    }    

    if (!dicom.HasTag(Orthanc::DICOM_TAG_ROWS) ||
        !dicom.GetValue(Orthanc::DICOM_TAG_ROWS).ParseFirstUnsignedInteger(height_))
    {
      height_ = 0;
    }


    if (dicom.ParseDouble(sliceThickness_, Orthanc::DICOM_TAG_SLICE_THICKNESS))
    {
      hasSliceThickness_ = true;
    }
    else
    {
      hasSliceThickness_ = false;

      if (numberOfFrames_ > 1)
      {
        LOG(INFO) << "The (non-madatory) slice thickness information is missing in a multiframe image";
      }
    }

    hasPixelSpacing_ = GeometryToolbox::GetPixelSpacing(pixelSpacingX_, pixelSpacingY_, dicom);

    std::string position, orientation;
    if (dicom.LookupStringValue(position, Orthanc::DICOM_TAG_IMAGE_POSITION_PATIENT, false) &&
        dicom.LookupStringValue(orientation, Orthanc::DICOM_TAG_IMAGE_ORIENTATION_PATIENT, false))
    {
      geometry_ = CoordinateSystem3D(position, orientation);
    }

    // Must be AFTER setting "numberOfFrames_"
    if (numberOfFrames_ > 1)
    {
      ExtractFrameOffsets(frameOffsets_, dicom, numberOfFrames_);
    }

    if (sopClassUid_ == SopClassUid_RTDose)
    {
      static const Orthanc::DicomTag DICOM_TAG_DOSE_UNITS(0x3004, 0x0002);

      if (!dicom.LookupStringValue(doseUnits_, DICOM_TAG_DOSE_UNITS, false))
      {
        LOG(ERROR) << "Tag DoseUnits (0x3004, 0x0002) is missing in " << sopInstanceUid_;
        doseUnits_.clear();
      }
    }

    if (dicom.ParseDouble(rescaleIntercept_, Orthanc::DICOM_TAG_RESCALE_INTERCEPT) &&
        dicom.ParseDouble(rescaleSlope_, Orthanc::DICOM_TAG_RESCALE_SLOPE))
    {
      if (sopClassUid_ == SopClassUid_RTDose)
      {
        LOG(INFO) << "DOSE HAS Rescale*: rescaleIntercept_ = " << rescaleIntercept_ << " rescaleSlope_ = " << rescaleSlope_;
        // WE SHOULD NOT TAKE THE RESCALE VALUE INTO ACCOUNT IN THE CASE OF DOSES
        hasRescale_ = false;
      }
      else
      {
        hasRescale_ = true;
      }
      
    }
    else
    {
      hasRescale_ = false;
    }

    if (dicom.ParseDouble(doseGridScaling_, Orthanc::DICOM_TAG_DOSE_GRID_SCALING))
    {
      if (sopClassUid_ == SopClassUid_RTDose)
      {
        LOG(INFO) << "DOSE HAS DoseGridScaling: doseGridScaling_ = " << doseGridScaling_;
      }
    }
    else
    {
      doseGridScaling_ = 1.0;
      if (sopClassUid_ == SopClassUid_RTDose)
      {
        LOG(ERROR) << "Tag DoseGridScaling (0x3004, 0x000e) is missing in " << sopInstanceUid_ << " doseGridScaling_ will be set to 1.0";
      }
    }


    windowingPresets_.clear();

    Vector centers, widths;
    
    if (LinearAlgebra::ParseVector(centers, dicom, Orthanc::DICOM_TAG_WINDOW_CENTER) &&
        LinearAlgebra::ParseVector(widths, dicom, Orthanc::DICOM_TAG_WINDOW_WIDTH))
    {
      if (centers.size() == widths.size())
      {
        windowingPresets_.resize(centers.size());

        for (size_t i = 0; i < centers.size(); i++)
        {
          windowingPresets_[i] = Windowing(centers[i], widths[i]);
        }
      }
      else
      {
        LOG(ERROR) << "Mismatch in the number of preset windowing widths/centers, ignoring this";
      }
    }

    // This computes the "IndexInSeries" metadata from Orthanc (check
    // out "Orthanc::ServerIndex::Store()")
    hasIndexInSeries_ = (
      dicom.ParseUnsignedInteger32(indexInSeries_, Orthanc::DICOM_TAG_INSTANCE_NUMBER) ||
      dicom.ParseUnsignedInteger32(indexInSeries_, Orthanc::DICOM_TAG_IMAGE_INDEX));

    if (!dicom.LookupStringValue(
          frameOfReferenceUid_, Orthanc::DICOM_TAG_FRAME_OF_REFERENCE_UID, false))
    {
      frameOfReferenceUid_.clear();
    }

    if (!dicom.HasTag(Orthanc::DICOM_TAG_INSTANCE_NUMBER) ||
        !dicom.GetValue(Orthanc::DICOM_TAG_INSTANCE_NUMBER).ParseInteger32(instanceNumber_))
    {
      instanceNumber_ = 0;
    }
  }


  void DicomInstanceParameters::InjectSequenceTags(const IDicomDataset& dataset)
  {
    /**
     * Use DICOM tag "SequenceOfUltrasoundRegions" (0018,6011) in
     * order to derive the pixel spacing on ultrasound (US) images
     **/

    static const Orthanc::DicomTag DICOM_TAG_SEQUENCE_OF_ULTRASOUND_REGIONS(0x0018, 0x6011);
    static const Orthanc::DicomTag DICOM_TAG_PHYSICAL_UNITS_X_DIRECTION(0x0018, 0x6024);
    static const Orthanc::DicomTag DICOM_TAG_PHYSICAL_UNITS_Y_DIRECTION(0x0018, 0x6026);
    static const Orthanc::DicomTag DICOM_TAG_PHYSICAL_DELTA_X(0x0018, 0x602c);
    static const Orthanc::DicomTag DICOM_TAG_PHYSICAL_DELTA_Y(0x0018, 0x602e);

    DicomDatasetReader reader(dataset);

    size_t size;

    if (!data_.hasPixelSpacing_ &&
        dataset.GetSequenceSize(size, Orthanc::DicomPath(DICOM_TAG_SEQUENCE_OF_ULTRASOUND_REGIONS)) &&
        size >= 1)
    {
      int directionX, directionY;
      double deltaX, deltaY;

      if (reader.GetIntegerValue(directionX, Orthanc::DicomPath(DICOM_TAG_SEQUENCE_OF_ULTRASOUND_REGIONS,
                                                                0, DICOM_TAG_PHYSICAL_UNITS_X_DIRECTION)) &&
          reader.GetIntegerValue(directionY, Orthanc::DicomPath(DICOM_TAG_SEQUENCE_OF_ULTRASOUND_REGIONS,
                                                                0, DICOM_TAG_PHYSICAL_UNITS_Y_DIRECTION)) &&
          reader.GetDoubleValue(deltaX, Orthanc::DicomPath(DICOM_TAG_SEQUENCE_OF_ULTRASOUND_REGIONS,
                                                           0, DICOM_TAG_PHYSICAL_DELTA_X)) &&
          reader.GetDoubleValue(deltaY, Orthanc::DicomPath(DICOM_TAG_SEQUENCE_OF_ULTRASOUND_REGIONS,
                                                           0, DICOM_TAG_PHYSICAL_DELTA_Y)) &&
          directionX == 0x0003 &&  // Centimeters
          directionY == 0x0003)    // Centimeters
      {
        // Scene coordinates are expressed in millimeters => multiplication by 10
        SetPixelSpacing(10.0 * deltaX, 10.0 * deltaY);
      }
    }


    /**
     * New in Stone Web viewer 2.2: Deal with Philips multiframe
     * (cf. mail from Tomas Kenda on 2021-08-17). This cannot be done
     * in LoadSeriesDetailsFromInstance, as the "Per Frame Functional
     * Groups Sequence" is not available at that point.
     **/

    static const Orthanc::DicomTag DICOM_TAG_PER_FRAME_FUNCTIONAL_GROUPS_SEQUENCE(0x5200, 0x9230);
    static const Orthanc::DicomTag DICOM_TAG_FRAME_VOI_LUT_SEQUENCE_ATTRIBUTE(0x0028, 0x9132);

    if (dataset.GetSequenceSize(size, Orthanc::DicomPath(DICOM_TAG_PER_FRAME_FUNCTIONAL_GROUPS_SEQUENCE)))
    {
      data_.perFrameWindowing_.reserve(data_.numberOfFrames_);

      // This corresponds to "ParsedDicomFile::GetDefaultWindowing()"
      for (size_t i = 0; i < size; i++)
      {
        size_t tmp;
        double center, width;

        if (dataset.GetSequenceSize(tmp, Orthanc::DicomPath(DICOM_TAG_PER_FRAME_FUNCTIONAL_GROUPS_SEQUENCE, i,
                                                            DICOM_TAG_FRAME_VOI_LUT_SEQUENCE_ATTRIBUTE)) &&
            tmp == 1 &&
            reader.GetDoubleValue(center, Orthanc::DicomPath(DICOM_TAG_PER_FRAME_FUNCTIONAL_GROUPS_SEQUENCE, i,
                                                             DICOM_TAG_FRAME_VOI_LUT_SEQUENCE_ATTRIBUTE, 0,
                                                             Orthanc::DICOM_TAG_WINDOW_CENTER)) &&
            reader.GetDoubleValue(width, Orthanc::DicomPath(DICOM_TAG_PER_FRAME_FUNCTIONAL_GROUPS_SEQUENCE, i,
                                                            DICOM_TAG_FRAME_VOI_LUT_SEQUENCE_ATTRIBUTE, 0,
                                                            Orthanc::DICOM_TAG_WINDOW_WIDTH)))
        {
          data_.perFrameWindowing_.push_back(Windowing(center, width));
        }
      }
    }
  }


  DicomInstanceParameters::DicomInstanceParameters(const DicomInstanceParameters& other) :
    data_(other.data_),
    tags_(other.tags_->Clone())
  {
  }


  DicomInstanceParameters::DicomInstanceParameters(const Orthanc::DicomMap& dicom) :
    data_(dicom),
    tags_(dicom.Clone())
  {
    OrthancNativeDataset dataset(dicom);
    InjectSequenceTags(dataset);
  }


  double DicomInstanceParameters::GetSliceThickness() const
  {
    if (data_.hasSliceThickness_)
    {
      return data_.sliceThickness_;
    }
    else
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
    }
  }


  const Orthanc::DicomImageInformation& DicomInstanceParameters::GetImageInformation() const
  {
    assert(tags_.get() != NULL);
    
    if (imageInformation_.get() == NULL)
    {
      const_cast<DicomInstanceParameters&>(*this).imageInformation_.
        reset(new Orthanc::DicomImageInformation(GetTags()));

      assert(imageInformation_->GetWidth() == GetWidth());
      assert(imageInformation_->GetHeight() == GetHeight());
      assert(imageInformation_->GetNumberOfFrames() == GetNumberOfFrames());
    }

    assert(imageInformation_.get() != NULL);
    return *imageInformation_;
  }
  

  CoordinateSystem3D  DicomInstanceParameters::GetFrameGeometry(unsigned int frame) const
  {
    if (frame >= data_.numberOfFrames_)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
    else if (data_.frameOffsets_.empty())
    {
      return data_.geometry_;
    }
    else
    {
      assert(data_.frameOffsets_.size() == data_.numberOfFrames_);

      return CoordinateSystem3D(
        data_.geometry_.GetOrigin() + data_.frameOffsets_[frame] * data_.geometry_.GetNormal(),
        data_.geometry_.GetAxisX(),
        data_.geometry_.GetAxisY());
    }
  }


  bool DicomInstanceParameters::IsPlaneWithinSlice(unsigned int frame,
                                                   const CoordinateSystem3D& plane) const
  {
    if (frame >= data_.numberOfFrames_)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }

    CoordinateSystem3D tmp = data_.geometry_;

    if (frame != 0)
    {
      tmp = GetFrameGeometry(frame);
    }

    double distance;

    return (CoordinateSystem3D::ComputeDistance(distance, tmp, plane) &&
            distance <= data_.sliceThickness_ / 2.0);
  }


  bool DicomInstanceParameters::IsColor() const
  {
    Orthanc::PhotometricInterpretation photometric =
      GetImageInformation().GetPhotometricInterpretation();
    
    return (photometric != Orthanc::PhotometricInterpretation_Monochrome1 &&
            photometric != Orthanc::PhotometricInterpretation_Monochrome2);
  }


  void DicomInstanceParameters::ApplyRescaleAndDoseScaling(Orthanc::ImageAccessor& image,
                                                           bool useDouble) const
  {
    if (image.GetFormat() != Orthanc::PixelFormat_Float32)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_IncompatibleImageFormat);
    }

    double scaling = data_.doseGridScaling_;
    double offset = 0.0;

    if (data_.hasRescale_)
    {
      scaling *= data_.rescaleSlope_;
      offset = data_.rescaleIntercept_;
    }

    Orthanc::ImageProcessing::ShiftScale2(image, offset, scaling, false);
  }
  

  double DicomInstanceParameters::GetRescaleIntercept() const
  {
    if (data_.hasRescale_)
    {
      return data_.rescaleIntercept_;
    }
    else
    {
      LOG(ERROR) << "DicomInstanceParameters::GetRescaleIntercept(): !data_.hasRescale_";
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
    }
  }


  double DicomInstanceParameters::GetRescaleSlope() const
  {
    if (data_.hasRescale_)
    {
      return data_.rescaleSlope_;
    }
    else
    {
      LOG(ERROR) << "DicomInstanceParameters::GetRescaleSlope(): !data_.hasRescale_";
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
    }
  }


  Orthanc::PixelFormat DicomInstanceParameters::GetExpectedPixelFormat() const
  {
    if (GetSopClassUid() == SopClassUid_RTDose)
    {
      switch (GetImageInformation().GetBitsStored())
      {
        case 16:
          return Orthanc::PixelFormat_Grayscale16;

        case 32:
          return Orthanc::PixelFormat_Grayscale32;

        default:
          return Orthanc::PixelFormat_Grayscale16;  // Rough guess
      } 
    }
    else if (IsColor())
    {
      return Orthanc::PixelFormat_RGB24;
    }
    else if (GetImageInformation().IsSigned())
    {
      return Orthanc::PixelFormat_SignedGrayscale16;
    }
    else
    {
      return Orthanc::PixelFormat_Grayscale16;  // Rough guess
    }
  }


  Windowing DicomInstanceParameters::GetFallbackWindowing() const
  {
    double a, b;
    if (tags_->ParseDouble(a, Orthanc::DICOM_TAG_SMALLEST_IMAGE_PIXEL_VALUE) &&
        tags_->ParseDouble(b, Orthanc::DICOM_TAG_LARGEST_IMAGE_PIXEL_VALUE))
    {
      const double center = (a + b) / 2.0f;
      const double width = (b - a);
      return Windowing(center, width);
    }

    // Added in Stone Web viewer > 2.5
    uint32_t bitsStored, pixelRepresentation;
    if (tags_->ParseUnsignedInteger32(bitsStored, Orthanc::DICOM_TAG_BITS_STORED) &&
        tags_->ParseUnsignedInteger32(pixelRepresentation, Orthanc::DICOM_TAG_PIXEL_REPRESENTATION))
    {
      const bool isSigned = (pixelRepresentation != 0);
      const float maximum = powf(2.0, bitsStored);
      return Windowing(isSigned ? 0.0f : maximum / 2.0f, maximum);
    }
    else
    {
      // Cannot infer a suitable windowing from the available tags
      return Windowing();
    }
  }


  size_t DicomInstanceParameters::GetWindowingPresetsCount() const
  {
    return data_.windowingPresets_.size();
  }
  

  Windowing DicomInstanceParameters::GetWindowingPreset(size_t i) const
  {
    if (i < GetWindowingPresetsCount())
    {
      return data_.windowingPresets_[i];
    }
    else
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }
  }

  
  Windowing DicomInstanceParameters::GetWindowingPresetsUnion() const
  {
    assert(tags_.get() != NULL);
    size_t s = GetWindowingPresetsCount();

    if (s > 0)
    {
      // Use the largest windowing given all the preset windowings
      // that are available in the DICOM tags
      double low, high;
      GetWindowingPreset(0).GetBounds(low, high);

      for (size_t i = 1; i < s; i++)
      {
        double a, b;
        GetWindowingPreset(i).GetBounds(a, b);
        low = std::min(low, a);
        high = std::max(high, b);
      }

      assert(low <= high);

      if (!LinearAlgebra::IsNear(low, high))
      {
        const double center = (low + high) / 2.0f;
        const double width = (high - low);
        return Windowing(center, width);
      }
    }

    // No preset, or presets with an empty range
    return GetFallbackWindowing();
  }


  Orthanc::ImageAccessor* DicomInstanceParameters::ConvertToFloat(const Orthanc::ImageAccessor& pixelData) const
  {
    std::unique_ptr<Orthanc::Image> converted(new Orthanc::Image(Orthanc::PixelFormat_Float32, 
                                                                 pixelData.GetWidth(), 
                                                                 pixelData.GetHeight(),
                                                                 false));
    Orthanc::ImageProcessing::Convert(*converted, pixelData);

                                                   
    // Correct rescale slope/intercept if need be
    //ApplyRescaleAndDoseScaling(*converted, (pixelData.GetFormat() == Orthanc::PixelFormat_Grayscale32));
    ApplyRescaleAndDoseScaling(*converted, false);

    return converted.release();
  }


  TextureBaseSceneLayer* DicomInstanceParameters::CreateTexture(
    const Orthanc::ImageAccessor& pixelData) const
  {
    // {
    //   const Orthanc::ImageAccessor& source = pixelData;
    //   const void* sourceBuffer = source.GetConstBuffer();
    //   intptr_t sourceBufferInt = reinterpret_cast<intptr_t>(sourceBuffer);
    //   int sourceWidth = source.GetWidth();
    //   int sourceHeight = source.GetHeight();
    //   int sourcePitch = source.GetPitch();

    //   // TODO: turn error into trace below
    //   LOG(ERROR) << "ConvertGrayscaleToFloat | source:"
    //     << " W = " << sourceWidth << " H = " << sourceHeight
    //     << " P = " << sourcePitch << " B = " << sourceBufferInt
    //     << " B % 4 == " << sourceBufferInt % 4;
    // }

    assert(sizeof(float) == 4);

    Orthanc::PixelFormat sourceFormat = pixelData.GetFormat();

    if (sourceFormat != GetExpectedPixelFormat())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_IncompatibleImageFormat);
    }

    std::unique_ptr<TextureBaseSceneLayer> texture;

    if (sourceFormat == Orthanc::PixelFormat_RGB24)
    {
      // This is the case of a color image. No conversion has to be done.
      texture.reset(new ColorTextureSceneLayer(pixelData));
    }
    else
    {
      // This is the case of a grayscale frame. Convert it to Float32.
      if (pixelData.GetFormat() == Orthanc::PixelFormat_Float32)
      {
        texture.reset(new FloatTextureSceneLayer(pixelData));
      }
      else
      {
        std::unique_ptr<Orthanc::ImageAccessor> converted(ConvertToFloat(pixelData));
        texture.reset(new FloatTextureSceneLayer(*converted));
      }

      FloatTextureSceneLayer& floatTexture = dynamic_cast<FloatTextureSceneLayer&>(*texture);

      if (GetWindowingPresetsCount() > 0)
      {
        Windowing preset = GetWindowingPreset(0);
        floatTexture.SetCustomWindowing(preset.GetCenter(), preset.GetWidth());
      }
      
      switch (GetImageInformation().GetPhotometricInterpretation())
      {
        case Orthanc::PhotometricInterpretation_Monochrome1:
          floatTexture.SetInverted(true);
          break;
          
        case Orthanc::PhotometricInterpretation_Monochrome2:
          floatTexture.SetInverted(false);
          break;

        default:
          break;
      }
    }

    if (HasPixelSpacing())
    {
      texture->SetPixelSpacing(GetPixelSpacingX(), GetPixelSpacingY());
    }
    
    return texture.release();
  }


  LookupTableTextureSceneLayer* DicomInstanceParameters::CreateLookupTableTexture(
    const Orthanc::ImageAccessor& pixelData) const
  {
    std::unique_ptr<LookupTableTextureSceneLayer> texture;
    
    if (pixelData.GetFormat() == Orthanc::PixelFormat_Float32)
    {
      texture.reset(new LookupTableTextureSceneLayer(pixelData));
    }
    else
    {
      std::unique_ptr<Orthanc::ImageAccessor> converted(ConvertToFloat(pixelData));
      texture.reset(new LookupTableTextureSceneLayer(*converted));
    }

    if (HasPixelSpacing())
    {
      texture->SetPixelSpacing(GetPixelSpacingX(), GetPixelSpacingY());
    }

    return texture.release();
  }

  
  LookupTableTextureSceneLayer* DicomInstanceParameters::CreateOverlayTexture(
    int originX,
    int originY,
    const Orthanc::ImageAccessor& overlay) const
  {
    if (overlay.GetFormat() != Orthanc::PixelFormat_Grayscale8)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_IncompatibleImageFormat);
    }

    std::unique_ptr<LookupTableTextureSceneLayer> texture(CreateLookupTableTexture(overlay));

    texture->SetOrigin(static_cast<double>(originX - 1) * texture->GetPixelSpacingX(),
                       static_cast<double>(originY - 1) * texture->GetPixelSpacingY());

    std::vector<uint8_t> lut(4 * 256);
    for (size_t i = 0; i < 256; i++)
    {
      if (i < 127)
      {
        // Black pixels are converted to transparent pixels
        lut[4 * i] = 0;
        lut[4 * i + 1] = 0;
        lut[4 * i + 2] = 0;
        lut[4 * i + 3] = 0;  // alpha
      }
      else
      {
        // White pixels are converted to opaque white
        lut[4 * i] = 255;
        lut[4 * i + 1] = 255;
        lut[4 * i + 2] = 255;
        lut[4 * i + 3] = 255;  // alpha
      }
    }

    texture->SetLookupTable(lut);
    
    return texture.release();
  }


  unsigned int DicomInstanceParameters::GetIndexInSeries() const
  {
    if (data_.hasIndexInSeries_)
    {
      return data_.indexInSeries_;
    }
    else
    {
      LOG(ERROR) << "DicomInstanceParameters::GetIndexInSeries(): !data_.hasIndexInSeries_";
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadSequenceOfCalls);
    }
  }


  double DicomInstanceParameters::ApplyRescale(double value) const
  {
    double scaling = data_.doseGridScaling_;
    double offset = 0.0;

    if (data_.hasRescale_)
    {
      scaling *= data_.rescaleSlope_;
      offset = data_.rescaleIntercept_;
    }

    return (value * scaling + offset);
  }


  bool DicomInstanceParameters::ComputeFrameOffsetsSpacing(double& spacing) const
  {
    if (data_.frameOffsets_.size() == 0)  // Not a RT-DOSE
    {
      return false;
    }
    else if (data_.frameOffsets_.size() == 1)
    {
      spacing = 1;   // Edge case: RT-DOSE with one single frame
      return true;
    }
    else
    {
      static double THRESHOLD = 0.001;
      
      if (data_.frameOffsets_.size() != GetNumberOfFrames())
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
      }

      double a = data_.frameOffsets_[1] - data_.frameOffsets_[0];

      for (size_t i = 1; i + 1 < data_.frameOffsets_.size(); i++)
      {
        double b = data_.frameOffsets_[i + 1] - data_.frameOffsets_[i];
        if (!LinearAlgebra::IsNear(a, b, THRESHOLD))
        {
          LOG(ERROR) << "Unable to extract slice thickness from GridFrameOffsetVector (3004,000C) (reason: varying spacing)";
          return false;
        }
      }

      spacing = std::abs(a);

      if (HasSliceThickness() &&
          !LinearAlgebra::IsNear(spacing, GetSliceThickness(), THRESHOLD))
      {
        LOG(WARNING) << "SliceThickness and GridFrameOffsetVector (3004,000C) do not match";
      }
      
      return true;
    }
  }

  
  void DicomInstanceParameters::SetPixelSpacing(double pixelSpacingX,
                                                double pixelSpacingY)
  {
    data_.hasPixelSpacing_ = true;
    data_.pixelSpacingX_ = pixelSpacingX;
    data_.pixelSpacingY_ = pixelSpacingY;
  }


  void DicomInstanceParameters::EnrichUsingDicomWeb(const Json::Value& dicomweb)
  {
    DicomWebDataset dataset(dicomweb);
    InjectSequenceTags(dataset);
  }


  CoordinateSystem3D DicomInstanceParameters::GetMultiFrameGeometry() const
  {
    if (data_.frameOffsets_.empty())
    {
      return data_.geometry_;
    }
    else
    {
      assert(data_.frameOffsets_.size() == data_.numberOfFrames_);

      double lowest = data_.frameOffsets_[0];
      for (size_t i = 1; i < data_.frameOffsets_.size(); i++)
      {
        lowest = std::min(lowest, data_.frameOffsets_[i]);
      }

      return CoordinateSystem3D(
        data_.geometry_.GetOrigin() + lowest * data_.geometry_.GetNormal(),
        data_.geometry_.GetAxisX(),
        data_.geometry_.GetAxisY());
    }
  }


  bool DicomInstanceParameters::IsReversedFrameOffsets() const
  {
    if (data_.frameOffsets_.size() < 2)
    {
      return false;
    }
    else
    {
      return (data_.frameOffsets_[0] > data_.frameOffsets_[1]);
    }
  }


  bool DicomInstanceParameters::LookupPerFrameWindowing(Windowing& windowing,
                                                        unsigned int frame) const
  {
    if (frame < data_.perFrameWindowing_.size())
    {
      windowing = data_.perFrameWindowing_[frame];
      return true;
    }
    else
    {
      return false;
    }
  }
}
