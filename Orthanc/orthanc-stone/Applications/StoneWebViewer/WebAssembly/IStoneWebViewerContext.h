/**
 * Stone of Orthanc
 * Copyright (C) 2012-2016 Sebastien Jodogne, Medical Physics
 * Department, University Hospital of Liege, Belgium
 * Copyright (C) 2017-2023 Osimis S.A., Belgium
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

#include "../../../OrthancStone/Sources/Scene2D/ISceneLayer.h"
#include "../../../OrthancStone/Sources/Toolbox/DicomInstanceParameters.h"

#include <Images/ImageAccessor.h>


static const int LAYER_TEXTURE = 0;
static const int LAYER_OVERLAY = 1;
static const int LAYER_ORIENTATION_MARKERS = 2;
static const int LAYER_REFERENCE_LINES = 3;
static const int LAYER_ANNOTATIONS_STONE = 5;
static const int LAYER_ANNOTATIONS_OSIRIX = 4;
static const int LAYER_STRUCTURED_REPORT = 6;


#define DISPATCH_JAVASCRIPT_EVENT(name)                         \
  EM_ASM(                                                       \
    const customEvent = document.createEvent("CustomEvent");    \
    customEvent.initCustomEvent(name, false, false, undefined); \
    window.dispatchEvent(customEvent);                          \
    );

#define EXTERN_CATCH_EXCEPTIONS                         \
  catch (Orthanc::OrthancException& e)                  \
  {                                                     \
    LOG(ERROR) << "OrthancException: " << e.What();     \
    DISPATCH_JAVASCRIPT_EVENT("StoneException");        \
  }                                                     \
  catch (OrthancStone::StoneException& e)               \
  {                                                     \
    LOG(ERROR) << "StoneException: " << e.What();       \
    DISPATCH_JAVASCRIPT_EVENT("StoneException");        \
  }                                                     \
  catch (std::exception& e)                             \
  {                                                     \
    LOG(ERROR) << "Runtime error: " << e.what();        \
    DISPATCH_JAVASCRIPT_EVENT("StoneException");        \
  }                                                     \
  catch (...)                                           \
  {                                                     \
    LOG(ERROR) << "Native exception";                   \
    DISPATCH_JAVASCRIPT_EVENT("StoneException");        \
  }


// WARNING: This class can be shared by multiple viewports
class ILayerSource : public boost::noncopyable
{
public:
  virtual ~ILayerSource()
  {
  }

  virtual int GetDepth() const = 0;

  virtual OrthancStone::ISceneLayer* Create(const Orthanc::ImageAccessor& frame,
                                            const OrthancStone::DicomInstanceParameters& instance,
                                            unsigned int frameNumber,
                                            double pixelSpacingX,
                                            double pixelSpacingY,
                                            const OrthancStone::CoordinateSystem3D& plane) = 0;
};


class IStoneWebViewerContext : public boost::noncopyable
{
public:
  virtual ~IStoneWebViewerContext()
  {
  }

  virtual void RedrawAllViewports() = 0;

  // WARNING: The ImageAccessor will become invalid once leaving the
  // JavaScript callback, do not keep a reference!
  virtual bool GetSelectedFrame(Orthanc::ImageAccessor& target /* out */,
                                std::string& sopInstanceUid /* out */,
                                unsigned int& frameNumber /* out */,
                                const std::string& canvas /* in */) = 0;
};


class IStoneWebViewerPlugin : public boost::noncopyable
{
public:
  virtual ~IStoneWebViewerPlugin()
  {
  }

  virtual ILayerSource& GetLayerSource() = 0;
};
