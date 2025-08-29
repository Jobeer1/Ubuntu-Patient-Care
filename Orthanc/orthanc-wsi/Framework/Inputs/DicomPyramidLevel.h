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

#include "DicomPyramidInstance.h"

#include <list>

namespace OrthancWSI
{
  class DicomPyramidLevel : public boost::noncopyable
  {
  private:
    struct TileContent
    {
      DicomPyramidInstance*  instance_;
      unsigned int           frame_;

      TileContent() : 
        instance_(NULL),
        frame_(0)
      {
      }
    };

    unsigned int             totalWidth_;
    unsigned int             totalHeight_;
    unsigned int             tileWidth_;
    unsigned int             tileHeight_;
    unsigned int             countTilesX_;
    unsigned int             countTilesY_;
    std::vector<TileContent> tiles_;

    TileContent& GetTileContent(unsigned int tileX,
                                unsigned int tileY);

    void RegisterFrame(DicomPyramidInstance& instance,
                       unsigned int frame);

    bool LookupTile(TileContent& tile,
                    unsigned int tileX,
                    unsigned int tileY) const;

  public:
    explicit DicomPyramidLevel(DicomPyramidInstance& instance);

    void AddInstance(DicomPyramidInstance& instance);

    unsigned int GetTotalWidth() const
    {
      return totalWidth_;
    }

    unsigned int GetTotalHeight() const
    {
      return totalHeight_;
    }

    unsigned int GetTileWidth() const
    {
      return tileWidth_;
    }

    unsigned int GetTileHeight() const
    {
      return tileHeight_;
    }

    bool DownloadRawTile(std::string& raw /* out */,
                         Orthanc::PixelFormat& format /* out */,
                         ImageCompression& compression /* out */,
                         OrthancStone::IOrthancConnection& orthanc,
                         unsigned int tileX,
                         unsigned int tileY) const;
  };
}
