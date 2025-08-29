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


#include "IncomingHttpRequestFilter.h"

#include "PythonHeaderWrapper.h"

#include "../Resources/Orthanc/Plugins/OrthancPluginCppWrapper.h"
#include "ICallbackRegistration.h"
#include "PythonString.h"

#include <sdk.h>

static PyObject*  incomingHttpRequestFilter_ = NULL;


static int32_t IncomingHttpRequestFilter(OrthancPluginHttpMethod method,
                                         const char *uri,
                                         const char *ip,
                                         uint32_t headersCount,
                                         const char *const *headersKeys,
                                         const char *const *headersValues,
                                         uint32_t getArgumentsCount,
                                         const char *const *getArgumentsKeys,
                                         const char *const *getArgumentsValues)
{
  try
  {
    PythonLock lock;

    PythonObject args(lock, PyTuple_New(1));

    {
      PythonString str(lock, uri);
      PyTuple_SetItem(args.GetPyObject(), 0, str.Release());
    }

    PythonObject kw(lock, PyDict_New());

    {
      PythonObject tmp(lock, PyLong_FromLong(method));
      PyDict_SetItemString(kw.GetPyObject(), "method", tmp.GetPyObject());
    }

    {
      PythonString str(lock, ip);
      PyDict_SetItemString(kw.GetPyObject(), "ip", str.GetPyObject());
    }

    {
      PythonObject headers(lock, PyDict_New());

      for (uint32_t i = 0; i < headersCount; i++)
      {
        PythonString str(lock, headersValues[i]);
        PyDict_SetItemString(headers.GetPyObject(), headersKeys[i], str.GetPyObject());
      }

      PyDict_SetItemString(kw.GetPyObject(), "headers", headers.GetPyObject());
    }

    if (method == OrthancPluginHttpMethod_Get)
    {
      PythonObject getArguments(lock, PyDict_New());

      for (uint32_t i = 0; i < getArgumentsCount; i++)
      {
        PythonString str(lock, getArgumentsValues[i]);
        PyDict_SetItemString(getArguments.GetPyObject(), getArgumentsKeys[i], str.GetPyObject());
      }

      PyDict_SetItemString(kw.GetPyObject(), "get", getArguments.GetPyObject());
    }
    
    PythonObject result(lock, PyObject_Call(incomingHttpRequestFilter_,
                                            args.GetPyObject(), kw.GetPyObject()));

    std::string traceback;
    if (lock.HasErrorOccurred(traceback))
    {
      ORTHANC_PLUGINS_LOG_ERROR("Error in the Python incoming-http-request filter, traceback:\n" + traceback);
      return -1;
    }
    else
    {
      if (PyBool_Check(result.GetPyObject()))
      {
        return (PyObject_IsTrue(result.GetPyObject()) ? 1 /* allowed */ : 0 /* forbidden */);
      }
      else
      {
        ORTHANC_PLUGINS_LOG_ERROR("The Python incoming-http-request filter has not returned a Boolean");
        return -1;
      }
    }
  }
  catch (OrthancPlugins::PluginException& e)
  {
    ORTHANC_PLUGINS_LOG_ERROR("Exception in the Python incoming-http-request filter: " +
                              std::string(e.What(OrthancPlugins::GetGlobalContext())));
    return e.GetErrorCode();
  }
}

   
PyObject* RegisterIncomingHttpRequestFilter(PyObject* module, PyObject* args)
{
  // The GIL is locked at this point (no need to create "PythonLock")

  class Registration : public ICallbackRegistration
  {
  public:
    virtual void Register() ORTHANC_OVERRIDE
    {
      OrthancPluginRegisterIncomingHttpRequestFilter2(
        OrthancPlugins::GetGlobalContext(), IncomingHttpRequestFilter);
    }
  };

  Registration registration;
  return ICallbackRegistration::Apply(
    registration, args, incomingHttpRequestFilter_, "Python incoming-http-request filter");
}


void FinalizeIncomingHttpRequestFilter()
{
  ICallbackRegistration::Unregister(incomingHttpRequestFilter_);
}
