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

#include "../Framework/MultiThreading/BagOfTasks.h"

#include <WebServiceParameters.h>

#include <string>
#include <stdint.h>
#include <boost/program_options.hpp>

namespace OrthancWSI
{
  namespace ApplicationToolbox
  {
    void GlobalInitialize();

    void GlobalFinalize();

    void Execute(BagOfTasks& tasks,
                 unsigned int threadsCount);

    void ParseColor(uint8_t& red,
                    uint8_t& green,
                    uint8_t& blue,
                    const std::string& color);

    void PrintVersion(const char* path);

    void ShowVersionInLog(const char* path);

    void AddRestApiOptions(boost::program_options::options_description& section);

    void SetupRestApi(Orthanc::WebServiceParameters& parameters,
                      const boost::program_options::variables_map& options);
  }
}
