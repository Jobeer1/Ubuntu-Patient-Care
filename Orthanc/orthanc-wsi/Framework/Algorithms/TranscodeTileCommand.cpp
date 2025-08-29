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


#include "../PrecompiledHeadersWSI.h"
#include "TranscodeTileCommand.h"

#include <OrthancException.h>
#include <Logging.h>

#include <cassert>

namespace OrthancWSI
{
  TranscodeTileCommand::TranscodeTileCommand(IPyramidWriter& target,
                                             ITiledPyramid& source,
                                             unsigned int level,
                                             unsigned int x,
                                             unsigned int y,
                                             unsigned int countTilesX,
                                             unsigned int countTilesY,
                                             const DicomizerParameters& parameters) :
  target_(target),
    source_(source, level, target.GetTileWidth(), target.GetTileHeight(), parameters),
    level_(level),
    x_(x),
    y_(y),
    countTilesX_(countTilesX),
    countTilesY_(countTilesY)
  {
    assert(x_ + countTilesX_ <= target_.GetCountTilesX(level_) &&
           y_ + countTilesY_ <= target_.GetCountTilesY(level_));

    if (target.GetPixelFormat() != source.GetPixelFormat())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_IncompatibleImageFormat);
    }
  }


  bool TranscodeTileCommand::Execute()
  {
    for (unsigned int x = x_; x < x_ + countTilesX_; x++)
    {
      for (unsigned int y = y_; y < y_ + countTilesY_; y++)
      {
        LOG(INFO) << "Adding tile (" << x << "," << y << ") at level " << level_;

        ImageCompression compression;
        const std::string* rawTile = source_.GetRawTile(compression, x, y);

        if (rawTile != NULL)
        {
          // Simple transcoding
          target_.WriteRawTile(*rawTile, compression, level_, x, y);
        }
        else
        {
          bool isEmpty;
          Orthanc::ImageAccessor tile;
          source_.GetDecodedTile(tile, isEmpty, x, y);

          if (!isEmpty)
          {
            // Re-encoding the file
            target_.EncodeTile(tile, level_, x, y);
          }
          else
          {
            printf("ICI\n");
          }
        }
      }
    }

    return true;
  }


  void TranscodeTileCommand::PrepareBagOfTasks(BagOfTasks& tasks,
                                               IPyramidWriter& target,
                                               ITiledPyramid& source,
                                               const DicomizerParameters& parameters)
  {
    for (unsigned int level = 0; level < source.GetLevelCount(); level++)
    {
      const unsigned int targetCountTilesX = target.GetCountTilesX(level);
      const unsigned int targetCountTilesY = target.GetCountTilesY(level);

      const unsigned int stepX = source.GetTileWidth(level) / target.GetTileWidth();
      const unsigned int stepY = source.GetTileHeight(level) / target.GetTileHeight();
      assert(stepX >= 1 && stepY >= 1);

      for (unsigned int y = 0; y < targetCountTilesY; y += stepY)
      {
        unsigned int cy = stepY;
        if (y + cy > targetCountTilesY)
        {
          cy = targetCountTilesY - y;
        }

        for (unsigned int x = 0; x < targetCountTilesX; x += stepX)
        {
          unsigned int cx = stepX;
          if (x + cx > targetCountTilesX)
          {
            cx = targetCountTilesX - x;
          }

          tasks.Push(new TranscodeTileCommand
                     (target, source, level, x, y, cx, cy, parameters));
        }
      }
    }
  }
}
