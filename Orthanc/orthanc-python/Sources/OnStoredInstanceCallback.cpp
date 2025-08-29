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


#include "OnStoredInstanceCallback.h"

#include "PythonHeaderWrapper.h"

#include "../Resources/Orthanc/Plugins/OrthancPluginCppWrapper.h"
#include "ICallbackRegistration.h"
#include "PythonString.h"

#include <sdk.h>


static PyObject*   storedInstanceCallback_ = NULL;


static OrthancPluginErrorCode OnStoredInstanceCallback(const OrthancPluginDicomInstance *instance,
                                                       const char *instanceId)
{
  try
  {
    PythonLock lock;

    /**
     * Construct an instance object of the "orthanc.DicomInstance"
     * class. This is done by calling the constructor function
     * "sdk_OrthancPluginDicomInstance_Type".
     **/
    PythonObject args(lock, PyTuple_New(2));
    PyTuple_SetItem(args.GetPyObject(), 0, PyLong_FromSsize_t((intptr_t) instance));
    PyTuple_SetItem(args.GetPyObject(), 1, PyBool_FromLong(true /* borrowed, don't destruct */));
    PyObject *pInst = PyObject_CallObject((PyObject*) GetOrthancPluginDicomInstanceType(), args.GetPyObject());
    
    /**
     * Construct the arguments tuple (instance, instanceId)
     **/
    PythonString str(lock, instanceId);
    
    PythonObject args2(lock, PyTuple_New(2));
    PyTuple_SetItem(args2.GetPyObject(), 0, pInst);
    PyTuple_SetItem(args2.GetPyObject(), 1, str.Release());

    PythonObject result(lock, PyObject_CallObject(storedInstanceCallback_, args2.GetPyObject()));

    std::string traceback;
    if (lock.HasErrorOccurred(traceback))
    {
      ORTHANC_PLUGINS_LOG_ERROR("Error in the Python on-stored-instance callback, traceback:\n" + traceback);
      return OrthancPluginErrorCode_Plugin;
    }
    else
    {
      return OrthancPluginErrorCode_Success;
    }
  }
  catch (OrthancPlugins::PluginException& e)
  {
    return e.GetErrorCode();
  }
}

   
PyObject* RegisterOnStoredInstanceCallback(PyObject* module, PyObject* args)
{
  // The GIL is locked at this point (no need to create "PythonLock")

  class Registration : public ICallbackRegistration
  {
  public:
    virtual void Register() ORTHANC_OVERRIDE
    {
      OrthancPluginRegisterOnStoredInstanceCallback(
        OrthancPlugins::GetGlobalContext(), OnStoredInstanceCallback);
    }
  };

  Registration registration;
  return ICallbackRegistration::Apply(
    registration, args, storedInstanceCallback_, "Python on-stored-instance callback");
}


void FinalizeOnStoredInstanceCallback()
{
  ICallbackRegistration::Unregister(storedInstanceCallback_);
}
