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

#include "Inputs/ITiledPyramid.h"
#include "Outputs/IPyramidWriter.h"
#include "Targets/IFileTarget.h"
#include "DicomToolbox.h"
#include <WebServiceParameters.h>

#include <stdint.h>

namespace OrthancWSI
{
  class DicomizerParameters
  {
  private:
    bool              safetyCheck_;
    bool              repaintBackground_;
    uint8_t           backgroundColor_[3];
    ImageCompression  targetCompression_;
    bool              hasTargetTileSize_;
    unsigned int      targetTileWidth_;
    unsigned int      targetTileHeight_;
    unsigned int      threadsCount_;
    unsigned int      maxDicomFileSize_;
    bool              reconstructPyramid_;
    unsigned int      pyramidLevelsCount_;  // "0" means use default choice
    unsigned int      pyramidLowerLevelsCount_;  // "0" means use default choice
    bool              smooth_;
    std::string       inputFile_;
    uint8_t           jpegQuality_;
    bool              forceReencode_;
    std::string       folder_;
    std::string       folderPattern_;
    std::string       dataset_;
    OpticalPath       opticalPath_;
    std::string       iccProfile_;

    Orthanc::WebServiceParameters  orthanc_;

    // New in release 1.1
    bool                           isCytomineSource_;
    Orthanc::WebServiceParameters  cytomineServer_;
    int                            cytomineImageInstanceId_;
    std::string                    cytominePublicKey_;
    std::string                    cytominePrivateKey_;
    ImageCompression               cytomineCompression_;

    // New in release 2.1
    bool          forceOpenSlide_;
    unsigned int  padding_;

  public:
    DicomizerParameters();

    void SetSafetyCheck(bool safety)
    {
      safetyCheck_ = safety;
    }

    bool IsSafetyCheck() const
    {
      return safetyCheck_;
    }

    bool IsRepaintBackground() const
    {
      return repaintBackground_;
    }

    void SetRepaintBackground(bool repaint)
    {
      repaintBackground_ = repaint;
    }

    void SetBackgroundColor(uint8_t red,
                            uint8_t green,
                            uint8_t blue);

    uint8_t GetBackgroundColorRed() const
    {
      return backgroundColor_[0];
    }

    uint8_t GetBackgroundColorGreen() const
    {
      return backgroundColor_[1];
    }

    uint8_t GetBackgroundColorBlue() const
    {
      return backgroundColor_[2];
    }

    void SetTargetCompression(ImageCompression compression)
    {
      targetCompression_ = compression;
    }

    ImageCompression GetTargetCompression() const
    {
      return targetCompression_;
    }

    void SetTargetTileSize(unsigned int width,
                           unsigned int height);

    unsigned int GetTargetTileWidth(unsigned int defaultWidth) const;

    unsigned int GetTargetTileWidth(const ITiledPyramid& source) const;

    unsigned int GetTargetTileHeight(unsigned int defaultHeight) const;

    unsigned int GetTargetTileHeight(const ITiledPyramid& source) const;

    void SetThreadsCount(unsigned int threads);

    unsigned int GetThreadsCount() const
    {
      return threadsCount_;
    }

    void SetDicomMaxFileSize(unsigned int size);

    unsigned int GetDicomMaxFileSize() const
    {
      return maxDicomFileSize_;
    }

    bool IsReconstructPyramid() const
    {
      return reconstructPyramid_;
    }

    void SetReconstructPyramid(bool reconstruct)
    {
      reconstructPyramid_ = reconstruct;
    }
    
    void SetPyramidLevelsCount(unsigned int count);

    unsigned int GetPyramidLevelsCount(const IPyramidWriter& target,
                                       const ITiledPyramid& source) const;

    void SetPyramidLowerLevelsCount(unsigned int count);

    unsigned int GetPyramidLowerLevelsCount(const IPyramidWriter& target,
                                            const ITiledPyramid& source) const;

    void SetSmoothEnabled(bool smooth)
    {
      smooth_ = smooth;
    }

    bool IsSmoothEnabled() const
    {
      return smooth_;
    }

    void SetInputFile(const std::string& path)
    {
      inputFile_ = path;
    }

    const std::string& GetInputFile() const
    {
      return inputFile_;
    }

    void SetJpegQuality(int quality);

    uint8_t GetJpegQuality() const
    {
      return jpegQuality_;
    }

    void SetForceReencode(bool force)
    {
      forceReencode_ = force;
    }

    bool IsForceReencode() const
    {
      return forceReencode_;
    }

    void SetTargetFolder(const std::string& folder)
    {
      folder_ = folder;
    }

    const std::string& GetTargetFolderPattern() const
    {
      return folderPattern_;
    }

    void SetTargetFolderPattern(const std::string& pattern)
    {
      folderPattern_ = pattern;
    }

    Orthanc::WebServiceParameters& GetOrthancParameters()
    {
      return orthanc_;
    }

    const Orthanc::WebServiceParameters& GetOrthancParameters() const
    {
      return orthanc_;
    }

    IFileTarget* CreateTarget() const;

    void SetDatasetPath(const std::string& path)
    {
      dataset_ = path;
    }

    const std::string& GetDatasetPath() const
    {
      return dataset_;
    }

    void SetOpticalPath(OpticalPath opticalPath)
    {
      opticalPath_ = opticalPath;
    }

    OpticalPath GetOpticalPath() const
    {
      return opticalPath_;
    }

    void SetIccProfilePath(const std::string& path)
    {
      iccProfile_ = path;
    }

    const std::string& GetIccProfilePath() const
    {
      return iccProfile_;
    }

    void SetCytomineSource(const std::string& url,
                           const std::string& publicKey,
                           const std::string& privateKey,
                           int imageInstanceId,
                           ImageCompression compression);

    bool IsCytomineSource() const
    {
      return isCytomineSource_;
    }

    const Orthanc::WebServiceParameters& GetCytomineServer() const;

    const std::string& GetCytominePublicKey() const;

    const std::string& GetCytominePrivateKey() const;

    int GetCytomineImageInstanceId() const;

    ImageCompression GetCytomineCompression() const;

    void SetPadding(unsigned int padding);

    unsigned int GetPadding() const
    {
      return padding_;
    }

    void SetForceOpenSlide(bool force)
    {
      forceOpenSlide_ = force;
    }

    bool IsForceOpenSlide() const
    {
      return forceOpenSlide_;
    }
  };
}
