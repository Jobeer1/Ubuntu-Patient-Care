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


#include "ApplicationToolbox.h"

#include "../Framework/Inputs/OpenSlideLibrary.h"
#include "../Framework/MultiThreading/BagOfTasksProcessor.h"

#include <Compatibility.h>  // For std::unique_ptr
#include <DicomParsing/FromDcmtkBridge.h>
#include <HttpClient.h>
#include <Logging.h>
#include <OrthancException.h>
#include <SystemToolbox.h>
#include <Toolbox.h>

#include <boost/filesystem.hpp>
#include <boost/lexical_cast.hpp>
#include <boost/regex.hpp>
#include <boost/date_time/posix_time/posix_time.hpp>
#include <cassert>


static const char* OPTION_CA_CERTIFICATES = "ca-certificates";
static const char* OPTION_PASSWORD = "password";
static const char* OPTION_PROXY = "proxy";
static const char* OPTION_TIMEOUT = "timeout";
static const char* OPTION_URL = "orthanc";
static const char* OPTION_USERNAME = "username";
static const char* OPTION_VERIFY_PEERS = "verify-peers";
      


static bool DisplayPerformanceWarning()
{
  (void) DisplayPerformanceWarning;   // Disable warning about unused function
  LOG(WARNING) << "Performance warning in whole-slide imaging: "
               << "Non-release build, runtime debug assertions are turned on";
  return true;
}


namespace OrthancWSI
{
  namespace ApplicationToolbox
  {
    void GlobalInitialize()
    {
      Orthanc::Logging::Initialize();
      Orthanc::Toolbox::InitializeOpenSsl();
      Orthanc::HttpClient::GlobalInitialize();
      Orthanc::FromDcmtkBridge::InitializeDictionary(false /* don't load private dictionary */);
      assert(DisplayPerformanceWarning());

#if ORTHANC_ENABLE_DCMTK_TRANSCODING == 1
      Orthanc::FromDcmtkBridge::InitializeCodecs();
#endif
    }


    void GlobalFinalize()
    {
#if ORTHANC_ENABLE_DCMTK_TRANSCODING == 1
      Orthanc::FromDcmtkBridge::FinalizeCodecs();
#endif

      OrthancWSI::OpenSlideLibrary::Finalize();
      Orthanc::HttpClient::GlobalFinalize();
      Orthanc::Toolbox::FinalizeOpenSsl();
    }


    static void PrintProgress(BagOfTasksProcessor::Handle* handle,
                              bool* done)
    {
      unsigned int previous = 0;

      while (!*done)
      {
        unsigned int progress = static_cast<unsigned int>(100.0f * handle->GetProgress());
        if (previous != progress)
        {
          LOG(WARNING) << "Progress: " << progress << "%";
          previous = progress;
        }

        boost::this_thread::sleep(boost::posix_time::milliseconds(100));
      }
    }


    void Execute(BagOfTasks& tasks,
                 unsigned int threadsCount)
    {
      if (threadsCount > 1)
      {
        // Submit the tasks to a newly-created processor
        LOG(WARNING) << "Running " << tasks.GetSize() << " tasks";
        LOG(WARNING) << "Using " << threadsCount << " threads for the computation";
        BagOfTasksProcessor processor(threadsCount);
        std::unique_ptr<BagOfTasksProcessor::Handle> handle(processor.Submit(tasks));

        // Start a thread to display the progress
        bool done = false;
        boost::thread progress(PrintProgress, handle.get(), &done);

        // Wait for the completion of the tasks
        bool success = handle->Join();

        // Stop the progress-printing thread
        done = true;
        
        if (progress.joinable())
        {
          progress.join();
        }

        if (success)
        {
          LOG(WARNING) << "All tasks have finished";
        }
        else
        {
          LOG(ERROR) << "Error has occurred, aborting";
          throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
        }
      }
      else
      {
        LOG(WARNING) << "Running " << tasks.GetSize() << " tasks without multithreading";

        unsigned int previous = 0;
        unsigned int size = tasks.GetSize();

        // No multithreading
        while (!tasks.IsEmpty())
        {
          std::unique_ptr<ICommand> task(tasks.Pop());
          if (task->Execute())
          {
            unsigned int progress = static_cast<unsigned int>(100.0f * 
                                                              static_cast<float>((size - tasks.GetSize())) / 
                                                              static_cast<float>(size));
            if (progress != previous)
            {
              LOG(WARNING) << "Progress: " << progress << "%";
              previous = progress;
            }
          }
          else
          {
            LOG(ERROR) << "Error has occurred, aborting";
            throw Orthanc::OrthancException(Orthanc::ErrorCode_InternalError);
          }
        }
      }
    }


    void ParseColor(uint8_t& red,
                    uint8_t& green,
                    uint8_t& blue,
                    const std::string& color)
    {
      boost::regex pattern("([0-9]*),([0-9]*),([0-9]*)");
    
      bool ok = false;
      boost::cmatch what;

      // Set white as the default color to avoid compiler warnings
      red = 255;
      green = 255;
      blue = 255;

      try
      {
        if (regex_match(color.c_str(), what, pattern))
        {
          int r = boost::lexical_cast<int>(what[1]);
          int g = boost::lexical_cast<int>(what[2]);
          int b = boost::lexical_cast<int>(what[3]);

          if (r >= 0 && r <= 255 &&
              g >= 0 && g <= 255 &&
              b >= 0 && b <= 255)
          {
            red = static_cast<uint8_t>(r);
            green = static_cast<uint8_t>(g);
            blue = static_cast<uint8_t>(b);
            ok = true;
          }
        }
      }
      catch (boost::bad_lexical_cast&)
      {
      }
    
      if (!ok)
      {
        LOG(ERROR) << "Bad color specification: " << color;
        throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
      }
    }


    void PrintVersion(const char* path)
    {
      std::cout
        << path << " " << ORTHANC_WSI_VERSION << std::endl
        << "Copyright (C) 2012-2016 Sebastien Jodogne, "
        << "Medical Physics Department, University Hospital of Liege (Belgium)" << std::endl
        << "Copyright (C) 2017-2023 Osimis S.A. (Belgium)" << std::endl
        << "Copyright (C) 2024-2025 Orthanc Team SRL (Belgium)" << std::endl
        << "Copyright (C) 2021-2025 Sebastien Jodogne, ICTEAM UCLouvain (Belgium)" << std::endl
        << "Licensing AGPL: GNU AGPL version 3 or later <http://gnu.org/licenses/agpl.html>." << std::endl
        << "This is free software: you are free to change and redistribute it." << std::endl
        << "There is NO WARRANTY, to the extent permitted by law." << std::endl
        << std::endl
        << "Written by Sebastien Jodogne <s.jodogne@orthanc-labs.com>" << std::endl;
    }


    void ShowVersionInLog(const char* path)
    {
      std::string version(ORTHANC_WSI_VERSION);

      if (version == "mainline")
      {
        try
        {
          boost::filesystem::path exe(Orthanc::SystemToolbox::GetPathToExecutable());
          std::time_t creation = boost::filesystem::last_write_time(exe);
          boost::posix_time::ptime converted(boost::posix_time::from_time_t(creation));
          version += " (" + boost::posix_time::to_iso_string(converted) + ")";
        }
        catch (...)
        {
        }
      }

      LOG(WARNING) << "Orthanc WSI version: " << version;
    }


  
    void AddRestApiOptions(boost::program_options::options_description& section)
    {
      section.add_options()
        (OPTION_USERNAME, boost::program_options::value<std::string>(),
         "Username for the target Orthanc server")
        (OPTION_PASSWORD, boost::program_options::value<std::string>(),
         "Password for the target Orthanc server")
        (OPTION_PROXY, boost::program_options::value<std::string>(),
         "HTTP proxy to be used")
        (OPTION_TIMEOUT, boost::program_options::value<int>()->default_value(0),
         "HTTP timeout (in seconds, 0 means no timeout)")
        (OPTION_VERIFY_PEERS, boost::program_options::value<bool>()->default_value(true),
         "Enable the verification of the peers during HTTPS requests")
        (OPTION_CA_CERTIFICATES, boost::program_options::value<std::string>()->default_value(""),
         "Path to the CA (certification authority) certificates to validate peers in HTTPS requests")
        ;
    }


    void SetupRestApi(Orthanc::WebServiceParameters& parameters,
                      const boost::program_options::variables_map& options)
    {
      if (options.count(OPTION_URL))
      {
        parameters.SetUrl(options[OPTION_URL].as<std::string>());
      }

      if (options.count(OPTION_USERNAME) &&
          options.count(OPTION_PASSWORD))
      {
        parameters.SetCredentials(options[OPTION_USERNAME].as<std::string>(),
                                  options[OPTION_PASSWORD].as<std::string>());
      }

      if (options.count(OPTION_TIMEOUT))
      {
        int timeout = options[OPTION_TIMEOUT].as<int>();
        if (timeout < 0)
        {
          LOG(ERROR) << "Timeouts cannot be negative: " << timeout;
          throw Orthanc::OrthancException(Orthanc::ErrorCode_ParameterOutOfRange);
        }
        else
        {
          Orthanc::HttpClient::SetDefaultTimeout(timeout);
        }

        if (options.count(OPTION_PROXY))
        {
          Orthanc::HttpClient::SetDefaultProxy(options[OPTION_PROXY].as<std::string>());
        }
      }

#if ORTHANC_ENABLE_SSL == 1
      if (options.count(OPTION_VERIFY_PEERS) ||
          options.count(OPTION_CA_CERTIFICATES))
      {
        Orthanc::HttpClient::ConfigureSsl(options[OPTION_VERIFY_PEERS].as<bool>(),
                                          options[OPTION_CA_CERTIFICATES].as<std::string>());
      }
#endif
    }
  }
}
