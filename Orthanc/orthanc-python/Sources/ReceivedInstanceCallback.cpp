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


#include "ReceivedInstanceCallback.h"

#include "PythonHeaderWrapper.h"

#include "../Resources/Orthanc/Plugins/OrthancPluginCppWrapper.h"
#include "ICallbackRegistration.h"
#include "PythonString.h"


#if ORTHANC_PLUGINS_VERSION_IS_ABOVE(1, 10, 0)

#include <Compatibility.h>  // For std::unique_ptr<>

static PyObject*   receivedInstanceCallback_ = NULL;


static OrthancPluginReceivedInstanceAction ReceivedInstanceCallback(
  OrthancPluginMemoryBuffer64* modifiedDicomBuffer /* out */,
  const void* receivedDicomBuffer,
  uint64_t receivedDicomBufferSize,
  OrthancPluginInstanceOrigin origin)
{
  try
  {
    PythonLock lock;

    PythonObject args(lock, PyTuple_New(2));
    
    PyTuple_SetItem(args.GetPyObject(), 0, PyBytes_FromStringAndSize(reinterpret_cast<const char*>(receivedDicomBuffer), receivedDicomBufferSize));
    PyTuple_SetItem(args.GetPyObject(), 1, PyLong_FromLong(origin));

    PythonObject result(lock, PyObject_CallObject(receivedInstanceCallback_, args.GetPyObject()));

    std::string traceback;
    if (lock.HasErrorOccurred(traceback))
    {
      ORTHANC_PLUGINS_LOG_ERROR("Error in the Python received instance callback, traceback:\n" + traceback);
      return OrthancPluginReceivedInstanceAction_KeepAsIs;
    }
    else if (!PyTuple_Check(result.GetPyObject()) || PyTuple_Size(result.GetPyObject()) != 2)
    {
      ORTHANC_PLUGINS_LOG_ERROR("The Python received instance callback has not returned a tuple as expected");
      return OrthancPluginReceivedInstanceAction_KeepAsIs;
    }
    else
    {
      PyObject* returnCode = PyTuple_GET_ITEM(result.GetPyObject(), 0);
      PyObject* modifiedDicom = PyTuple_GET_ITEM(result.GetPyObject(), 1);

      if (!PyLong_Check(returnCode))
      {
        ORTHANC_PLUGINS_LOG_ERROR("The Python received instance callback has not returned an int as the first element of the return tuple");
        return OrthancPluginReceivedInstanceAction_KeepAsIs;
      }

      OrthancPluginReceivedInstanceAction resultCode = static_cast<OrthancPluginReceivedInstanceAction>(PyLong_AsLong(returnCode));

      if (resultCode == OrthancPluginReceivedInstanceAction_KeepAsIs ||
          resultCode == OrthancPluginReceivedInstanceAction_Discard)
      {
        return resultCode;
      }
      else
      {
        char* pythonBuffer = NULL;
        Py_ssize_t pythonSize = 0;
        if (PyBytes_AsStringAndSize(modifiedDicom, &pythonBuffer, &pythonSize) == 1)
        {
          ORTHANC_PLUGINS_LOG_ERROR("Cannot access the byte buffer returned by the Python received instance callback");
          return OrthancPluginReceivedInstanceAction_KeepAsIs;
        }
        else
        {
          OrthancPluginCreateMemoryBuffer64(OrthancPlugins::GetGlobalContext(), modifiedDicomBuffer, pythonSize);
        
          if (pythonSize != 0)
          {
            if (modifiedDicomBuffer->data == NULL)
            {
              ORTHANC_PLUGINS_LOG_ERROR("Cannot allocate memory in the Python received instance callback");
              return OrthancPluginReceivedInstanceAction_KeepAsIs;
            }
            else
            {
              memcpy(modifiedDicomBuffer->data, pythonBuffer, pythonSize);
            }
          }

          return OrthancPluginReceivedInstanceAction_Modify;
        }
      }
    }
  }
  catch (OrthancPlugins::PluginException& e)
  {
    ORTHANC_PLUGINS_LOG_ERROR("Error in the Python received instance callback: " +
                              std::string(e.What(OrthancPlugins::GetGlobalContext())));
  }

  return OrthancPluginReceivedInstanceAction_KeepAsIs;
}

   
PyObject* RegisterReceivedInstanceCallback(PyObject* module, PyObject* args)
{
  // The GIL is locked at this point (no need to create "PythonLock")

  class Registration : public ICallbackRegistration
  {
  public:
    virtual void Register() ORTHANC_OVERRIDE
    {
      OrthancPluginRegisterReceivedInstanceCallback(
        OrthancPlugins::GetGlobalContext(), ReceivedInstanceCallback);
    }
  };

  Registration registration;
  return ICallbackRegistration::Apply(
    registration, args, receivedInstanceCallback_, "Python received instance callback");
}


void FinalizeReceivedInstanceCallback()
{
  ICallbackRegistration::Unregister(receivedInstanceCallback_);
}

#else

#warning OrthancPluginRegisterReceivedInstanceCallback() is not supported

PyObject* RegisterReceivedInstanceCallback(PyObject* module, PyObject* args)
{
  PyErr_SetString(PyExc_RuntimeError, "The version of your Orthanc SDK doesn't provide OrthancPluginRegisterReceivedInstanceCallback()");
  return NULL;
}

void FinalizeReceivedInstanceCallback()
{
}

#endif
