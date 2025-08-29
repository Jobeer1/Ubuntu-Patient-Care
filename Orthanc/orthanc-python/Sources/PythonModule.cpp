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


#include "PythonModule.h"

#include "../Resources/Orthanc/Plugins/OrthancPluginCppWrapper.h"
#include "PythonString.h"

#include <boost/thread/mutex.hpp>
#include <set>


#if PY_VERSION_HEX < 0x03070000 /* 3.7.0 */
static PythonObject* GetModule(PythonLock& lock,
                               const std::string& utf8Name)
{
  static boost::mutex           mutex_;
  static std::set<std::string>  loadedModules_;

  boost::mutex::scoped_lock l(mutex_);

  if (loadedModules_.find(utf8Name) == loadedModules_.end())
  {
    PythonString tmp(lock, utf8Name);

    // The module is not imported yet
    loadedModules_.insert(utf8Name);
    return new PythonObject(lock, PyImport_Import(tmp.GetPyObject()), false);
  }
  else
  {
    // PyImport_AddModule returns a borrowed reference
    return new PythonObject(lock, PyImport_AddModule(utf8Name.c_str()), true);
  }
}

#else
// The "PyImport_GetModule()" function was introduced in Python
// 3.7.0
static PythonObject* GetModule(PythonLock& lock,
                               const std::string& utf8Name)
{
  PythonString tmp(lock, utf8Name);

  PyObject* module = PyImport_GetModule(tmp.GetPyObject());
  if (module != NULL)
  {
    // The module was already imported by a previous call: Reuse it
    return new PythonObject(lock, module);
  }
  else
  {
    // This is the first time this module is used: Import it
    return new PythonObject(lock, PyImport_Import(tmp.GetPyObject()));
  }
}
#endif
  

PythonModule::PythonModule(PythonLock& lock,
                           const std::string& utf8Name) :
  lock_(lock),
  name_(utf8Name)
{
  module_.reset(GetModule(lock, utf8Name));
}


bool PythonModule::IsValid() const
{
  return (module_.get() != NULL &&
          module_->IsValid());
}


PythonObject& PythonModule::GetObject() const
{
  if (!IsValid())
  {
    ORTHANC_PLUGINS_THROW_EXCEPTION(BadSequenceOfCalls);
  }
  else
  {
    return *module_;
  }
}


PyObject* PythonModule::GetPyObject() const
{
  if (!IsValid())
  {
    ORTHANC_PLUGINS_THROW_EXCEPTION(BadSequenceOfCalls);
  }
  else
  {
    return module_->GetPyObject();
  }
}
