/**
 * SPDX-FileCopyrightText: 2020-2023 Osimis S.A., 2024-2025 Orthanc Team SRL, 2021-2025 Sebastien Jodogne, ICTEAM UCLouvain
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

/**
 * Python plugin for Orthanc
 * Copyright (C) 2020-2023 Osimis S.A., Belgium
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

#include <orthanc/OrthancCPlugin.h>

#include "PythonHeaderWrapper.h"

#include <boost/noncopyable.hpp>
#include <string>

class PythonLock : public boost::noncopyable
{
private:
  PyGILState_STATE gstate_;
  
public:
  typedef void (*ModuleClassesInstaller) (PyObject* module);
  
  typedef PyMethodDef* (*ModuleFunctionsInstaller) ();
  
  PythonLock();
  
  ~PythonLock();

  void ExecuteCommand(const std::string& s);

  void ExecuteFile(const std::string& path);

  bool HasErrorOccurred(std::string& traceback);

  OrthancPluginErrorCode CheckCallbackSuccess(const std::string& callbackDetails);

  static void GlobalInitialize(const std::string& moduleName,
                               const std::string& exceptionName,
                               ModuleFunctionsInstaller moduleFunctions,
                               ModuleClassesInstaller moduleClasses,
                               bool verbose);

  static void GlobalFinalize();

  static void AddSysPath(const std::string& path);

  static void RaiseException(OrthancPluginErrorCode code);

  static void LogCall(const std::string& message);
};
