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


#include "PythonString.h"

#include "../Resources/Orthanc/Plugins/OrthancPluginCppWrapper.h"


void PythonString::SanityCheck()
{
  if (!string_->IsValid())
  {
    ORTHANC_PLUGINS_LOG_ERROR("Cannot create a Python string, check that the string is properly encoded using UTF-8");
    ORTHANC_PLUGINS_THROW_EXCEPTION(InternalError);
  }
}


PythonString::PythonString(PythonLock& lock,
                           const std::string& utf8)
{
  string_.reset(new PythonObject(lock, PyUnicode_FromString(utf8.c_str())));
  SanityCheck();
}


PythonString::PythonString(PythonLock& lock,
                           const char* utf8)
{
  if (utf8 == NULL)
  {
    ORTHANC_PLUGINS_THROW_EXCEPTION(NullPointer);
  }
  else
  {
    string_.reset(new PythonObject(lock, PyUnicode_FromString(utf8)));
    SanityCheck();
  }
}
