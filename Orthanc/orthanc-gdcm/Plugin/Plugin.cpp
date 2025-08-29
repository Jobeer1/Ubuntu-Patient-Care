/**
 * Orthanc - A Lightweight, RESTful DICOM Store
 * Copyright (C) 2012-2016 Sebastien Jodogne, Medical Physics
 * Department, University Hospital of Liege, Belgium
 * Copyright (C) 2017-2023 Osimis S.A., Belgium
 * Copyright (C) 2024-2025 Orthanc Team SRL, Belgium
 * Copyright (C) 2021-2025 Sebastien Jodogne, ICTEAM UCLouvain, Belgium
 *
 * This program is free software: you can redistribute it and/or
 * modify it under the terms of the GNU General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 * 
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program. If not, see <http://www.gnu.org/licenses/>.
 **/


#include "GdcmDecoderCache.h"

#include <Compatibility.h>
#include <DicomFormat/DicomMap.h>
#include <Logging.h>
#include <MultiThreading/Semaphore.h>
#include <Toolbox.h>

#include <gdcmFileExplicitFilter.h>
#include <gdcmImageChangePhotometricInterpretation.h>
#include <gdcmImageChangeTransferSyntax.h>
#include <gdcmImageHelper.h>
#include <gdcmImageReader.h>
#include <gdcmImageWriter.h>
#include <gdcmTagKeywords.h>
#include <gdcmUIDGenerator.h>
#include <gdcmVersion.h>

#define PLUGIN_NAME "gdcm"

#define GDCM_VERSION_IS_ABOVE(major, minor, revision)           \
  (GDCM_MAJOR_VERSION > major ||                                \
   (GDCM_MAJOR_VERSION == major &&                              \
    (GDCM_MINOR_VERSION > minor ||                              \
     (GDCM_MINOR_VERSION == minor &&                            \
      GDCM_BUILD_VERSION >= revision))))


static OrthancPlugins::GdcmDecoderCache  cache_;
static bool restrictTransferSyntaxes_ = false;
static std::set<std::string> enabledTransferSyntaxes_;
static bool hasThrottling_ = false;
static std::unique_ptr<Orthanc::Semaphore> throttlingSemaphore_;

static bool ExtractTransferSyntax(std::string& transferSyntax,
                                  const void* dicom,
                                  const uint32_t size)
{
  Orthanc::DicomMap header;
  if (!Orthanc::DicomMap::ParseDicomMetaInformation(header, reinterpret_cast<const char*>(dicom), size))
  {
    return false;
  }

  const Orthanc::DicomValue* tag = header.TestAndGetValue(0x0002, 0x0010);
  if (tag == NULL ||
      tag->IsNull() ||
      tag->IsBinary())
  {
    return false;
  }
  else
  {
    // Stripping spaces should not be required, as this is a UI value
    // representation whose stripping is supported by the Orthanc
    // core, but let's be careful...
    transferSyntax = Orthanc::Toolbox::StripSpaces(tag->GetContent());
    return true;
  }
}


static bool IsTransferSyntaxEnabled(const void* dicom,
                                    const uint32_t size)
{
  std::string formattedSize;

  {
    char tmp[16];
    sprintf(tmp, "%0.1fMB", static_cast<float>(size) / (1024.0f * 1024.0f));
    formattedSize.assign(tmp);
  }

  if (!restrictTransferSyntaxes_)
  {
    LOG(INFO) << "Decoding one DICOM instance of " << formattedSize << " using GDCM";
    return true;
  }

  std::string transferSyntax;
  if (!ExtractTransferSyntax(transferSyntax, dicom, size))
  {
    LOG(INFO) << "Cannot extract the transfer syntax of this instance of "
              << formattedSize << ", will use GDCM to decode it";
    return true;
  }
  else if (enabledTransferSyntaxes_.find(transferSyntax) != enabledTransferSyntaxes_.end())
  {
    // Decoding for this transfer syntax is enabled
    LOG(INFO) << "Using GDCM to decode this instance of " << formattedSize
              << " with transfer syntax " << transferSyntax;
    return true;
  }
  else
  {
    LOG(INFO) << "Won't use GDCM to decode this instance of " << formattedSize
              << ", as its transfer syntax " << transferSyntax << " is disabled";
    return false;
  }
}

static bool IsTransferSyntaxEnabled(const std::string& transferSyntax)
{
  if (!restrictTransferSyntaxes_)
  {
    return true;
  }

  if (enabledTransferSyntaxes_.find(transferSyntax) != enabledTransferSyntaxes_.end())
  {
    return true;
  }

  return false;
}

static OrthancPluginErrorCode DecodeImageCallback(OrthancPluginImage** target,
                                                  const void* dicom,
                                                  const uint32_t size,
                                                  uint32_t frameIndex)
{
  try
  {
    std::unique_ptr<Orthanc::Semaphore::Locker> locker;
    
    if (hasThrottling_)
    {
      if (throttlingSemaphore_.get() == NULL)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
      }
      else
      {
        locker.reset(new Orthanc::Semaphore::Locker(*throttlingSemaphore_));
      }
    }

    if (!IsTransferSyntaxEnabled(dicom, size))
    {
      *target = NULL;
      return OrthancPluginErrorCode_Success;
    }

    std::unique_ptr<OrthancPlugins::OrthancImage> image;

#if 0
    // Do not use the cache
    OrthancPlugins::GdcmImageDecoder decoder(dicom, size);
    image.reset(new OrthancPlugins::OrthancImage(decoder.Decode(frameIndex)));
#else
    image.reset(cache_.Decode(dicom, size, frameIndex));
#endif

    *target = image->Release();

    return OrthancPluginErrorCode_Success;
  }
  catch (Orthanc::OrthancException& e)
  {
    *target = NULL;

    LOG(INFO) << "Cannot decode image using GDCM: " << e.What();
    return OrthancPluginErrorCode_Plugin;
  }
  catch (std::runtime_error& e)
  {
    *target = NULL;

    LOG(INFO) << "Cannot decode image using GDCM: " << e.what();
    return OrthancPluginErrorCode_Plugin;
  }
  catch (...)
  {
    *target = NULL;

    LOG(WARNING) << "Native exception while decoding image using GDCM";
    return OrthancPluginErrorCode_Plugin;
  }
}


#if ORTHANC_PLUGINS_VERSION_IS_ABOVE(1, 7, 0)

static bool IsYbrToRgbConversionNeeded(const gdcm::Image& image)
{
  return (image.GetPhotometricInterpretation().GetSamplesPerPixel() == 3 &&
          image.GetPhotometricInterpretation() == gdcm::PhotometricInterpretation::YBR_FULL &&
          // Only applicable to Little Endian uncompressed transfer syntaxes
          (image.GetTransferSyntax() == gdcm::TransferSyntax::ImplicitVRLittleEndian ||
           image.GetTransferSyntax() == gdcm::TransferSyntax::ExplicitVRLittleEndian));
}


static void AnswerTranscoded(OrthancPluginMemoryBuffer* transcoded /* out */,
                             const gdcm::Image&         image,
                             const gdcm::ImageReader&   reader)
{
  /**
   * In GDCM, if "ForceRescaleInterceptSlope" is "false" (the default
   * value), the SOP Class UID (0008,0016) might be changed from
   * 1.2.840.10008.5.1.4.1.1.4 (MR Image Storage) to
   * 1.2.840.10008.5.1.4.1.1.4.1 (Enhanced MR Image Storage), because
   * of function "ImageHelper::ComputeMediaStorageFromModality()" that
   * is called by "ImageWriter::ComputeTargetMediaStorage()". But,
   * changing the SOP Class UID is unexpected if doing transcoding.
   *
   * As another side-effect, the DICOM tags "ImagePositionPatient"
   * (0020,0032) and "ImageOrientationPatient" (0020,0037) are removed
   * from the root of the dataset, and moved into subsequence "Shared
   * Functional Groups Sequence" (5200,9229). This leads to issue
   * LSD-598.
   **/
  gdcm::ImageHelper::SetForceRescaleInterceptSlope(true);

  gdcm::ImageWriter writer;
  writer.SetImage(image);
  writer.SetFile(reader.GetFile());

  std::stringstream ss;
  writer.SetStream(ss);
  if (writer.Write())
  {
    std::string s = ss.str();
    OrthancPlugins::MemoryBuffer orthancBuffer(s.empty() ? NULL : s.c_str(), s.size());
    *transcoded = orthancBuffer.Release();
  }
  else
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError,
                                    "GDCM cannot serialize the image");
  }
}


static void ConvertYbrToRgb(OrthancPluginMemoryBuffer* transcoded /* out */,
                            const gdcm::Image&         image,
                            const gdcm::ImageReader&   reader)
{
  /**
   * Fix the photometric interpretation, typically needed for some
   * multiframe US images (as the one in BitBucket issue 164). Also
   * check out the "Plugins/Samples/GdcmDecoder/GdcmImageDecoder.cpp"
   * file in the source distribution of Orthanc, and Osimis issue
   * WVB-319 ("Some images are not loading in US_MF").
   **/

  assert(IsYbrToRgbConversionNeeded(image));

  gdcm::ImageChangePhotometricInterpretation change;
  change.SetPhotometricInterpretation(gdcm::PhotometricInterpretation::RGB);
  change.SetInput(image);

  if (change.Change())
  {
    AnswerTranscoded(transcoded, change.GetOutput(), reader);
  }
  else
  {
    throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented,
                                    "GDCM cannot change the photometric interpretation");
  }
}


OrthancPluginErrorCode TranscoderCallback(
  OrthancPluginMemoryBuffer* transcoded /* out */,
  const void*                buffer,
  uint64_t                   size,
  const char* const*         allowedSyntaxes,
  uint32_t                   countSyntaxes,
  uint8_t                    allowNewSopInstanceUid)
{
  try
  {
    std::string sourceTransferSyntax;
    ExtractTransferSyntax(sourceTransferSyntax, buffer, size);

    bool pluginShouldHandleTranscoding = false;
    for (uint32_t i = 0; i < countSyntaxes; i++)
    {
      if (IsTransferSyntaxEnabled(sourceTransferSyntax) || IsTransferSyntaxEnabled(allowedSyntaxes[i]))
      {
        pluginShouldHandleTranscoding = true;
      }
    }

    if (!pluginShouldHandleTranscoding)
    {
      return OrthancPluginErrorCode_Plugin; // not really an error but only way to tell Orthanc that the plugin did not handle transcoding
    }


    std::unique_ptr<Orthanc::Semaphore::Locker> locker;
    
    if (hasThrottling_)
    {
      if (throttlingSemaphore_.get() == NULL)
      {
        throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
      }
      else
      {
        locker.reset(new Orthanc::Semaphore::Locker(*throttlingSemaphore_));
      }
    }

    std::string dicom(reinterpret_cast<const char*>(buffer), size);
    std::stringstream stream(dicom);

    gdcm::ImageReader reader;
    reader.SetStream(stream);
    if (!reader.Read())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat,
                                      "GDCM cannot decode the image");
    }

    // First check that transcoding is mandatory
    for (uint32_t i = 0; i < countSyntaxes; i++)
    {
      gdcm::TransferSyntax syntax(gdcm::TransferSyntax::GetTSType(allowedSyntaxes[i]));
      if (syntax.IsValid() &&
          reader.GetImage().GetTransferSyntax() == syntax)
      {
        // Same transfer syntax as in the source, return a copy of the
        // source buffer
        if (IsYbrToRgbConversionNeeded(reader.GetImage()))
        {
          ConvertYbrToRgb(transcoded, reader.GetImage(), reader);
        }
        else
        {
          OrthancPlugins::MemoryBuffer orthancBuffer(buffer, size);
          *transcoded = orthancBuffer.Release();
        }
        
        return OrthancPluginErrorCode_Success;
      }
    }

    if (reader.GetImage().GetTransferSyntax().IsImplicit())
    {
      /**
       * New in release 1.1. This fixes the transcoding of DICOM files
       * encoded using an implicit transfer syntax. This is similar to
       * enabling the command-line option "-U" or "--use-dict" of the
       * gdcmconv tool (cf. GDCM-3.0.6/Applications/Cxx/gdcmconv.cxx).
       * If this conversion is not done, the value representations are
       * left to the "UN" VR, which prevents Orthanc from accessing
       * tags such as "Study|Series|SOP Instance UID" (because Orthanc
       * considers "UN" as a binary value).
       **/
      gdcm::FileExplicitFilter toExplicit;
      toExplicit.SetFile(reader.GetFile());
      toExplicit.Change();
    }

    for (uint32_t i = 0; i < countSyntaxes; i++)
    {
      gdcm::TransferSyntax syntax(gdcm::TransferSyntax::GetTSType(allowedSyntaxes[i]));
      if (syntax.IsValid())
      {
        if (reader.GetImage().GetPixelFormat().GetBitsAllocated() == 1u)
        {
          // Prevent transcoding of 1-bit images, as this might crash GDCM
          // https://groups.google.com/g/orthanc-users/c/xIwrkFRceuE/m/jwxy50djAQAJ
          throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented, "Cannot transcode 1bpp DICOM images");
        }

        gdcm::DataSet ds = reader.GetFile().GetDataSet();
        const gdcm::Tag sfgs(0x5200,0x9229); // SharedFunctionalGroupsSequence
        if (ds.FindDataElement(sfgs) && ds.GetDataElement(sfgs).IsEmpty())
        {
          throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented, "Cannot transcode DICOM images with empty 5200,9229 sequence");
        }
 
#if !GDCM_VERSION_IS_ABOVE(3, 0, 9)
        if (reader.GetImage().GetPixelFormat().GetBitsStored() == 16u &&
            syntax == gdcm::TransferSyntax::JPEGExtendedProcess2_4)
        {
          /**
           * This is a temporary workaround for issue #513 in GDCM
           * that was fixed in GDCM 3.0.9:
           * https://sourceforge.net/p/gdcm/bugs/513/
           * https://groups.google.com/g/orthanc-users/c/xt9hwpj6mlQ
           **/
          throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented,
                                          "Transcoding 16bpp images to 1.2.840.10008.1.2.4.51 might lead to a crash in GDCM");
        }
#endif
        
        gdcm::ImageChangeTransferSyntax change;
        change.SetTransferSyntax(syntax);
        change.SetInput(reader.GetImage());

        if (change.Change())
        {
          if (change.GetOutput().GetTransferSyntax() != syntax)
          {
            throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
          }
         
          if (syntax == gdcm::TransferSyntax::JPEGBaselineProcess1 ||
              syntax == gdcm::TransferSyntax::JPEGExtendedProcess2_4 ||
              syntax == gdcm::TransferSyntax::JPEGLSNearLossless ||
              syntax == gdcm::TransferSyntax::JPEG2000 ||
              syntax == gdcm::TransferSyntax::JPEG2000Part2)
          {
            // In the case of a lossy compression, generate new SOP instance UID
            gdcm::UIDGenerator generator;
            std::string uid = generator.Generate();
            if (uid.size() == 0)
            {
              throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError,
                                              "GDCM cannot generate a UID");
            }

            gdcm::Keywords::SOPInstanceUID sopInstanceUid;
            sopInstanceUid.SetValue(uid);
            reader.GetFile().GetDataSet().Replace(sopInstanceUid.GetAsDataElement());
          }
      
          // GDCM was able to change the transfer syntax, serialize it
          // to the output buffer
          if (IsYbrToRgbConversionNeeded(change.GetOutput()))
          {
            ConvertYbrToRgb(transcoded, change.GetOutput(), reader);
          }
          else
          {
            AnswerTranscoded(transcoded, change.GetOutput(), reader);
          }

          return OrthancPluginErrorCode_Success;
        }
      }
    }
    
    throw Orthanc::OrthancException(Orthanc::ErrorCode_NotImplemented);
  }
  catch (Orthanc::OrthancException& e)
  {
    LOG(INFO) << "Cannot transcode image using GDCM: " << e.What();
    return OrthancPluginErrorCode_Plugin;
  }
  catch (std::runtime_error& e)
  {
    LOG(INFO) << "Cannot transcode image using GDCM: " << e.what();
    return OrthancPluginErrorCode_Plugin;
  }
  catch (...)
  {
    LOG(INFO) << "Native exception while decoding image using GDCM";
    return OrthancPluginErrorCode_Plugin;
  }
}
#endif


/**
 * We force the redefinition of the "ORTHANC_PLUGINS_API" macro, that
 * was left empty with gcc until Orthanc SDK 1.5.7 (no "default"
 * visibility). This causes the version script, if run from "Holy
 * Build Box", to make private the 4 global functions of the plugin.
 **/

#undef ORTHANC_PLUGINS_API

#ifdef WIN32
#  define ORTHANC_PLUGINS_API __declspec(dllexport)
#elif __GNUC__ >= 4
#  define ORTHANC_PLUGINS_API __attribute__ ((visibility ("default")))
#else
#  define ORTHANC_PLUGINS_API
#endif


extern "C"
{
  ORTHANC_PLUGINS_API int32_t OrthancPluginInitialize(OrthancPluginContext* context)
  {
    static const char* const KEY_GDCM = "Gdcm";
    static const char* const KEY_ENABLE_GDCM = "Enable";
    static const char* const KEY_THROTTLING = "Throttling";
    static const char* const KEY_RESTRICT_TRANSFER_SYNTAXES = "RestrictTransferSyntaxes";

    try
    {
      OrthancPlugins::SetGlobalContext(context);

#if defined(ORTHANC_FRAMEWORK_VERSION_IS_ABOVE)
#  if ORTHANC_FRAMEWORK_VERSION_IS_ABOVE(1, 12, 4)
      Orthanc::Logging::InitializePluginContext(context, PLUGIN_NAME);
#  elif ORTHANC_FRAMEWORK_VERSION_IS_ABOVE(1, 7, 2)
      Orthanc::Logging::InitializePluginContext(context);
#  else
      Orthanc::Logging::Initialize(context);
#  endif
#else
      Orthanc::Logging::Initialize(context);
#endif
      
      LOG(INFO) << "Initializing the decoder/transcoder of medical images using GDCM";

      /* Check the version of the Orthanc core */
      if (!OrthancPlugins::CheckMinimalOrthancVersion(0, 9, 5))
      {
        LOG(ERROR) << "Your version of Orthanc (" << std::string(context->orthancVersion)
                   << ") must be above 0.9.5 to run this plugin";
        return -1;
      }

      OrthancPlugins::SetDescription(PLUGIN_NAME, "Decoder/transcoder of medical images using GDCM.");

      OrthancPlugins::OrthancConfiguration global;

      bool enabled = true;
      hasThrottling_ = false;
    
      if (global.IsSection(KEY_GDCM))
      {
        OrthancPlugins::OrthancConfiguration config;
        global.GetSection(config, KEY_GDCM);

        enabled = config.GetBooleanValue(KEY_ENABLE_GDCM, true);

        if (enabled)
        {
          if (config.LookupSetOfStrings(enabledTransferSyntaxes_, KEY_RESTRICT_TRANSFER_SYNTAXES, false))
          {
            if (enabledTransferSyntaxes_.size() == 0)
            {
              restrictTransferSyntaxes_ = false;
              LOG(WARNING) << KEY_GDCM << "." << KEY_RESTRICT_TRANSFER_SYNTAXES << " configuration is set but empty, Orthanc will use GDCM to transcode ALL transfer syntaxes.";
            }
            else
            {
              LOG(WARNING) << KEY_GDCM << "." << KEY_RESTRICT_TRANSFER_SYNTAXES << " configuration is set and not empty, Orthanc will use GDCM to transcode SOME transfer syntaxes:";
            }
          }
          else
          {
            LOG(WARNING) << KEY_GDCM << "." << KEY_RESTRICT_TRANSFER_SYNTAXES << " configuration is not set, using default configuration. Orthanc will use GDCM to transcode only J2K transfer syntaxes:";
            enabledTransferSyntaxes_.insert("1.2.840.10008.1.2.4.90"); // JPEG 2000 Image Compression (Lossless Only)
            enabledTransferSyntaxes_.insert("1.2.840.10008.1.2.4.91"); // JPEG 2000 Image Compression
            enabledTransferSyntaxes_.insert("1.2.840.10008.1.2.4.92"); // JPEG 2000 Part 2 Multicomponent Image Compression (Lossless Only)
            enabledTransferSyntaxes_.insert("1.2.840.10008.1.2.4.93"); // JPEG 2000 Part 2 Multicomponent Image Compression
          }

          if (enabledTransferSyntaxes_.size() > 0)
          {
            restrictTransferSyntaxes_ = true;
            for (std::set<std::string>::const_iterator it = enabledTransferSyntaxes_.begin();
                it != enabledTransferSyntaxes_.end(); ++it)
            {
              LOG(WARNING) << "Orthanc will use GDCM to decode transfer syntax: " << *it;
            }
          }
        }


        unsigned int throttling;
        if (enabled &&
            config.LookupUnsignedIntegerValue(throttling, KEY_THROTTLING))
        {
          if (throttling == 0)
          {
            LOG(ERROR) << "Bad value for option \"" << KEY_THROTTLING
                       << "\": Must be a strictly positive integer";
            return -1;
          }
          else
          {
            LOG(WARNING) << "Throttling GDCM to " << throttling << " concurrent thread(s)";
            hasThrottling_ = true;
            throttlingSemaphore_.reset(new Orthanc::Semaphore(throttling));
          }
        }
      }

      if (enabled)
      {
        LOG(WARNING) << "Version of GDCM: " << gdcm::Version::GetVersion();
        
        if (!hasThrottling_)
        {
          LOG(WARNING) << "GDCM throttling is disabled";
        }

        OrthancPluginRegisterDecodeImageCallback(context, DecodeImageCallback);

#if ORTHANC_PLUGINS_VERSION_IS_ABOVE(1, 7, 0)
        if (OrthancPlugins::CheckMinimalOrthancVersion(1, 7, 0))
        {
          OrthancPluginRegisterTranscoderCallback(context, TranscoderCallback);
        }
        else
        {
          LOG(WARNING) << "Your version of Orthanc (" << std::string(context->orthancVersion)
                       << ") must be above 1.7.0 to benefit from transcoding";
        }
#else
        LOG(WARNING) << "The GDCM plugin was compiled against Orthanc SDK "
                     << ORTHANC_PLUGINS_MINIMAL_MAJOR_NUMBER << "."
                     << ORTHANC_PLUGINS_MINIMAL_MINOR_NUMBER << "."
                     << ORTHANC_PLUGINS_MINIMAL_REVISION_NUMBER
                     << ": Support for DICOM transcoding is disabled (1.7.0 is required)";
#endif
      }
      else
      {
        LOG(WARNING) << "The decoder/transcoder of medical images using GDCM is disabled";
      }
    
      return 0;
    }
    catch (Orthanc::OrthancException& e)
    {
      LOG(ERROR) << "Exception while initializing the GDCM plugin: " << e.What();
      return -1;
    }
  }


  ORTHANC_PLUGINS_API void OrthancPluginFinalize()
  {
    LOG(INFO) << "Finalizing the decoder/transcoder of medical images using GDCM";
  }


  ORTHANC_PLUGINS_API const char* OrthancPluginGetName()
  {
    return PLUGIN_NAME;
  }


  ORTHANC_PLUGINS_API const char* OrthancPluginGetVersion()
  {
    return PLUGIN_VERSION;
  }
}
