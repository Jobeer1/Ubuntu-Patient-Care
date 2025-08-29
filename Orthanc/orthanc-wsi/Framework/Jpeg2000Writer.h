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

#include <Compatibility.h>
#include <Images/IImageWriter.h>

namespace OrthancWSI
{
  class Jpeg2000Writer : public Orthanc::IImageWriter
  {
  protected:
    virtual void WriteToMemoryInternal(std::string& compressed,
                                       unsigned int width,
                                       unsigned int height,
                                       unsigned int pitch,
                                       Orthanc::PixelFormat format,
                                       const void* buffer) ORTHANC_OVERRIDE;

  private:
    bool  isLossless_;

  public:
    Jpeg2000Writer() : isLossless_(true)
    {
    }

    void SetLossless(bool isLossless)
    {
      isLossless_ = isLossless;
    }

    bool IsLossless() const
    {
      return isLossless_;
    }
  };
}
