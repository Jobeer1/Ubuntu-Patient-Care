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


#include "../Framework/DicomToolbox.h"
#include "../Framework/ImageToolbox.h"
#include "../Framework/Inputs/DicomPyramid.h"
#include "../Framework/Inputs/TiledPyramidStatistics.h"
#include "../Framework/Outputs/HierarchicalTiffWriter.h"
#include "../Resources/Orthanc/Stone/OrthancHttpConnection.h"

#include <Compatibility.h>  // For std::unique_ptr
#include <Logging.h>
#include <OrthancException.h>

#include "ApplicationToolbox.h"


static const char* OPTION_COLOR = "color";
static const char* OPTION_HELP = "help";
static const char* OPTION_INPUT = "input";
static const char* OPTION_JPEG_QUALITY = "jpeg-quality";
static const char* OPTION_OUTPUT = "output";
static const char* OPTION_REENCODE = "reencode";
static const char* OPTION_VERBOSE = "verbose";
static const char* OPTION_VERSION = "version";

static bool ParseParameters(int& exitStatus,
                            boost::program_options::variables_map& options,
                            int argc, 
                            char* argv[])
{
  // Declare the supported parameters
  boost::program_options::options_description generic("Generic options");
  generic.add_options()
    (OPTION_HELP,    "Display this help and exit")
    (OPTION_VERSION, "Output version information and exit")
    (OPTION_VERBOSE, "Be verbose in logs")
    ;

  boost::program_options::options_description source("Options for the source DICOM image");
  source.add_options()
    ("orthanc", boost::program_options::value<std::string>()->default_value("http://localhost:8042/"),
     "URL to the REST API of the target Orthanc server")
    ;
  OrthancWSI::ApplicationToolbox::AddRestApiOptions(source);

  boost::program_options::options_description target("Options for the target TIFF image");
  target.add_options()
    (OPTION_COLOR, boost::program_options::value<std::string>(),
     "Color of the background for missing tiles (e.g. \"255,0,0\")")
    (OPTION_REENCODE, boost::program_options::value<bool>(), 
     "Whether to re-encode each tile in JPEG (no transcoding, much slower) (Boolean)")
    (OPTION_JPEG_QUALITY, boost::program_options::value<int>(),
     "Set quality level for JPEG (0..100)")
    ;

  boost::program_options::options_description hidden;
  hidden.add_options()
    (OPTION_INPUT, boost::program_options::value<std::string>(),
     "Orthanc identifier of the input series of interest")
    (OPTION_OUTPUT, boost::program_options::value<std::string>(),
     "Output TIFF file");

  boost::program_options::options_description allWithoutHidden;
  allWithoutHidden.add(generic).add(source).add(target);

  boost::program_options::options_description all = allWithoutHidden;
  all.add(hidden);

  boost::program_options::positional_options_description positional;
  positional.add(OPTION_INPUT, 1);
  positional.add(OPTION_OUTPUT, 1);

  bool error = false;

  try
  {
    boost::program_options::store(boost::program_options::command_line_parser(argc, argv).
                                  options(all).positional(positional).run(), options);
    boost::program_options::notify(options);    
  }
  catch (boost::program_options::error& e)
  {
    LOG(ERROR) << "Error while parsing the command-line arguments: " << e.what();
    error = true;
  }

  if (!error &&
      options.count(OPTION_HELP) == 0 &&
      options.count(OPTION_VERSION) == 0)
  {
    if (options.count(OPTION_INPUT) != 1)
    {
      LOG(ERROR) << "No input series was specified";
      error = true;
    }

    if (options.count(OPTION_OUTPUT) != 1)
    {
      LOG(ERROR) << "No output file was specified";
      error = true;
    }
  }

  if (error || options.count(OPTION_HELP)) 
  {
    std::cout << std::endl
              << "Usage: " << argv[0] << " [OPTION]... [INPUT] [OUTPUT]"
              << std::endl
              << "Orthanc, lightweight, RESTful DICOM server for healthcare and medical research."
              << std::endl << std::endl
              << "Convert a DICOM image for digital pathology stored in some Orthanc server as a" << std::endl
              << "standard hierarchical TIFF (whose tiles are all encoded using JPEG)."
              << std::endl;

    std::cout << allWithoutHidden << "\n";

    if (error)
    {
      exitStatus = -1;
    }

    return false;
  }

  if (options.count(OPTION_VERSION)) 
  { 
    OrthancWSI::ApplicationToolbox::PrintVersion(argv[0]);
    return false;
  }

  if (options.count(OPTION_VERBOSE))
  {
    Orthanc::Logging::EnableInfoLevel(true);
  }

  return true;
}



static Orthanc::ImageAccessor* CreateEmptyTile(const OrthancWSI::IPyramidWriter& writer,
                                               const boost::program_options::variables_map& options)
{
  std::unique_ptr<Orthanc::ImageAccessor> tile
    (OrthancWSI::ImageToolbox::Allocate(writer.GetPixelFormat(), 
                                        writer.GetTileWidth(), 
                                        writer.GetTileHeight()));

  uint8_t red = 255;
  uint8_t green = 255;
  uint8_t blue = 255;

  if (options.count(OPTION_COLOR))
  {
    OrthancWSI::ApplicationToolbox::ParseColor(red, green, blue, options[OPTION_COLOR].as<std::string>());
  }

  OrthancWSI::ImageToolbox::Set(*tile, red, green, blue);

  return tile.release();
}



static void Run(OrthancWSI::ITiledPyramid& source,
                const boost::program_options::variables_map& options)
{
  bool reencode = (options.count(OPTION_REENCODE) &&
                   options[OPTION_REENCODE].as<bool>());

  Orthanc::PhotometricInterpretation targetPhotometric;

  if (reencode)
  {
    // The DicomToTiff tool only creates TIFF images with JPEG tiles (*)
    targetPhotometric = Orthanc::PhotometricInterpretation_YBRFull422;
  }
  else
  {
    targetPhotometric = source.GetPhotometricInterpretation();
  }

  OrthancWSI::ImageToolbox::CheckConstantTileSize(source); // (**)
  OrthancWSI::HierarchicalTiffWriter target(options[OPTION_OUTPUT].as<std::string>(),
                                            source.GetPixelFormat(), 
                                            OrthancWSI::ImageCompression_Jpeg,  // (*)
                                            source.GetTileWidth(0),   // (**) 
                                            source.GetTileHeight(0),  // (**)
                                            targetPhotometric);

  if (options.count(OPTION_JPEG_QUALITY))
  {
    target.SetJpegQuality(options[OPTION_JPEG_QUALITY].as<int>());
  }

  LOG(WARNING) << "Source photometric interpretation: " << EnumerationToString(source.GetPhotometricInterpretation());
  LOG(WARNING) << "Target photometric interpretation: " << EnumerationToString(targetPhotometric);

  std::unique_ptr<Orthanc::ImageAccessor> empty(CreateEmptyTile(target, options));

  for (unsigned int level = 0; level < source.GetLevelCount(); level++)
  {
    LOG(WARNING) << "Creating level " << level << " of size " 
                 << source.GetLevelWidth(level) << "x" << source.GetLevelHeight(level);
    target.AddLevel(source.GetLevelWidth(level), source.GetLevelHeight(level));
  }

  for (unsigned int level = 0; level < source.GetLevelCount(); level++)
  {
    LOG(WARNING) << std::string(reencode ? "Re-encoding" : "Transcoding")
                 << " level " << level;

    unsigned int countX = OrthancWSI::CeilingDivision
      (source.GetLevelWidth(level), source.GetTileWidth(level));

    unsigned int countY = OrthancWSI::CeilingDivision
      (source.GetLevelHeight(level), source.GetTileHeight(level));

    for (unsigned int tileY = 0; tileY < countY; tileY++)
    {
      for (unsigned int tileX = 0; tileX < countX; tileX++)
      {
        LOG(INFO) << "Dealing with tile (" << tileX << "," << tileY << ") at level " << level;

        bool missing = false;
        bool success = true;

        std::string tile;
        OrthancWSI::ImageCompression compression;

        if (source.ReadRawTile(tile, compression, level, tileX, tileY))
        {
          if (compression == OrthancWSI::ImageCompression_Jpeg)
          {
            // Transcoding of JPEG tiles
            target.WriteRawTile(tile, compression, level, tileX, tileY);
          }
          else if (reencode)
          {
            std::unique_ptr<Orthanc::ImageAccessor> decoded;

            if (compression == OrthancWSI::ImageCompression_None)
            {
              decoded.reset(OrthancWSI::ImageToolbox::DecodeRawTile(
                              tile, source.GetPixelFormat(),
                              source.GetTileWidth(level), source.GetTileHeight(level)));
            }
            else
            {
              decoded.reset(OrthancWSI::ImageToolbox::DecodeTile(tile, compression));
            }
                
            target.EncodeTile(*decoded, level, tileX, tileY);
          }
          else
          {
            success = false;  // Re-encoding is mandatory
          }
        }
        else
        {
          // Unable to read the raw tile: The tile is missing (sparse tiling)
          missing = true;
        }

        if (!success)
        {
          LOG(WARNING) << "Cannot transcode a DICOM image that is not encoded using JPEG (it is " 
                       << OrthancWSI::EnumerationToString(compression) 
                       << "), please use the --" << OPTION_REENCODE << "=1 option";
          throw Orthanc::OrthancException(Orthanc::ErrorCode_BadFileFormat);
        }
        
        if (missing)
        {
          LOG(WARNING) << "Sparse tiling: Using an empty image for missing tile ("
                       << tileX << "," << tileY << ") at level " << level;
          target.EncodeTile(*empty, level, tileX, tileY);
        }
      }        
    }

    target.Flush();
  }
}



int main(int argc, char* argv[])
{
  OrthancWSI::ApplicationToolbox::GlobalInitialize();
  OrthancWSI::ApplicationToolbox::ShowVersionInLog(argv[0]);

  int exitStatus = 0;
  boost::program_options::variables_map options;

  try
  {
    if (ParseParameters(exitStatus, options, argc, argv))
    {
      Orthanc::WebServiceParameters params;

      OrthancWSI::ApplicationToolbox::SetupRestApi(params, options);

      OrthancStone::OrthancHttpConnection orthanc(params);
      OrthancWSI::DicomPyramid source(orthanc, options[OPTION_INPUT].as<std::string>(), 
                                      false /* don't use cached metadata */);

      OrthancWSI::TiledPyramidStatistics stats(source);
      Run(stats, options);
    }
  }
  catch (Orthanc::OrthancException& e)
  {
    LOG(ERROR) << "Terminating on exception: " << e.What() << ": " << e.GetDetails();;

    if (options.count(OPTION_REENCODE) == 0)
    {
      LOG(ERROR) << "Consider using option \"--" << OPTION_REENCODE << "\"";
    }
    
    exitStatus = -1;
  }

  OrthancWSI::ApplicationToolbox::GlobalFinalize();

  return exitStatus;
}
