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
#include "ReconstructPyramidCommand.h"

#include "../ImageToolbox.h"

#include <Compatibility.h>  // For std::unique_ptr
#include <Logging.h>
#include <OrthancException.h>
#include <Images/Image.h>
#include <Images/ImageProcessing.h>

#include <cassert>

namespace OrthancWSI
{
  Orthanc::ImageAccessor* ReconstructPyramidCommand::Explore(bool& isEmpty,
                                                             unsigned int level,
                                                             unsigned int offsetX,
                                                             unsigned int offsetY)
  {
    unsigned int zoom = 1 << level;
    assert(x_ % zoom == 0 && y_ % zoom == 0);
    unsigned int x = x_ / zoom + offsetX;
    unsigned int y = y_ / zoom + offsetY;

    if (x >= target_.GetCountTilesX(level + shiftTargetLevel_) ||
        y >= target_.GetCountTilesY(level + shiftTargetLevel_))
    {
      return NULL;
    }

    std::unique_ptr<Orthanc::ImageAccessor> result;

    if (level == 0)
    {
      result.reset(new Orthanc::ImageAccessor);
      source_.GetDecodedTile(*result, isEmpty, x, y);

      if ((x == 0 && y == 0) ||  // Make sure to have at least 1 tile at each level
          !isEmpty ||
          level == upToLevel_)
      {
        ImageCompression compression;
        const std::string* rawTile = source_.GetRawTile(compression, x, y);

        if (rawTile != NULL)
        {
          // Simple transcoding
          target_.WriteRawTile(*rawTile, compression, level + shiftTargetLevel_, x, y);
        }
        else
        {
          // Re-encoding the file
          target_.EncodeTile(*result, level + shiftTargetLevel_, x, y);
        }
      }
    }
    else
    {
      std::unique_ptr<Orthanc::ImageAccessor> mosaic(ImageToolbox::Allocate(source_.GetPixelFormat(), 
                                                                          2 * target_.GetTileWidth(), 
                                                                          2 * target_.GetTileHeight()));
      ImageToolbox::Set(*mosaic, 
                        source_.GetParameters().GetBackgroundColorRed(),
                        source_.GetParameters().GetBackgroundColorGreen(),
                        source_.GetParameters().GetBackgroundColorBlue());

      isEmpty = true;

      {
        bool tmpIsEmpty;
        std::unique_ptr<Orthanc::ImageAccessor> subTile(Explore(tmpIsEmpty, level - 1, 2 * offsetX, 2 * offsetY));
        if (subTile.get() != NULL)
        {
          ImageToolbox::Embed(*mosaic, *subTile, 0, 0);
          if (!tmpIsEmpty)
          {
            isEmpty = false;
          }
        }
      }

      {
        bool tmpIsEmpty;
        std::unique_ptr<Orthanc::ImageAccessor> subTile(Explore(tmpIsEmpty, level - 1, 2 * offsetX + 1, 2 * offsetY));
        if (subTile.get() != NULL)
        {
          ImageToolbox::Embed(*mosaic, *subTile, target_.GetTileWidth(), 0);
          if (!tmpIsEmpty)
          {
            isEmpty = false;
          }
        }
      }

      {
        bool tmpIsEmpty;
        std::unique_ptr<Orthanc::ImageAccessor> subTile(Explore(tmpIsEmpty, level - 1, 2 * offsetX, 2 * offsetY + 1));
        if (subTile.get() != NULL)
        {
          ImageToolbox::Embed(*mosaic, *subTile, 0, target_.GetTileHeight());
          if (!tmpIsEmpty)
          {
            isEmpty = false;
          }
        }
      }

      {
        bool tmpIsEmpty;
        std::unique_ptr<Orthanc::ImageAccessor> subTile(Explore(tmpIsEmpty, level - 1, 2 * offsetX + 1, 2 * offsetY + 1));
        if (subTile.get() != NULL)
        {
          ImageToolbox::Embed(*mosaic, *subTile, target_.GetTileWidth(), target_.GetTileHeight());
          if (!tmpIsEmpty)
          {
            isEmpty = false;
          }
        }
      }

      if (source_.GetParameters().IsSmoothEnabled())
      {
        Orthanc::ImageProcessing::SmoothGaussian5x5(*mosaic, false /* don't use accurate rounding */);
      }

      result.reset(Orthanc::ImageProcessing::Halve(*mosaic, false /* don't force minimal pitch */));

      if ((x == 0 && y == 0) ||  // Make sure to have at least 1 tile at each level
          !isEmpty ||
          level == upToLevel_)
      {
        target_.EncodeTile(*result, level + shiftTargetLevel_, x, y);
      }
    }

    return result.release();
  }

  
  ReconstructPyramidCommand::ReconstructPyramidCommand(IPyramidWriter& target,
                                                       ITiledPyramid& source,
                                                       unsigned int upToLevel,
                                                       unsigned int x,
                                                       unsigned int y,
                                                       const DicomizerParameters& parameters) :
    target_(target),
    source_(source, 0, target.GetTileWidth(), target.GetTileHeight(), parameters),
    upToLevel_(upToLevel),
    x_(x),
    y_(y),
    shiftTargetLevel_(0)
  {
    unsigned int zoom = 1 << upToLevel;
    if (x % zoom != 0 ||
        y % zoom != 0)
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
    }

    if (target.GetPixelFormat() != source.GetPixelFormat())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_IncompatibleImageFormat);
    }
  }


  bool ReconstructPyramidCommand::Execute()
  {
    bool isEmpty;  // Unused
    std::unique_ptr<Orthanc::ImageAccessor> root(Explore(isEmpty, upToLevel_, 0, 0));
    return true;
  }


  void ReconstructPyramidCommand::PrepareBagOfTasks(BagOfTasks& tasks,
                                                    IPyramidWriter& target,
                                                    ITiledPyramid& source,
                                                    unsigned int countLevels,
                                                    unsigned int shiftTargetLevel,    
                                                    const DicomizerParameters& parameters)
  {
    if (countLevels == 0)
    {
      return;
    }

    if (shiftTargetLevel + countLevels > target.GetLevelCount())
    {
      throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
    }

    const unsigned int targetCountTilesX = target.GetCountTilesX(shiftTargetLevel);
    const unsigned int targetCountTilesY = target.GetCountTilesY(shiftTargetLevel);
    const unsigned int step = 1 << (countLevels - 1);

    for (unsigned int y = 0; y < targetCountTilesY; y += step)
    {
      for (unsigned int x = 0; x < targetCountTilesX; x += step)
      {
        std::unique_ptr<ReconstructPyramidCommand> command;
        command.reset(new ReconstructPyramidCommand
                      (target, source, countLevels - 1, x, y, parameters));
        command->SetShiftTargetLevel(shiftTargetLevel);
        tasks.Push(command.release());
      }
    }
  }
}
