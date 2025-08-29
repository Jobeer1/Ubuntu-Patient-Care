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


#include "IncomingInstanceFilter.h"

#include "PythonHeaderWrapper.h"

#include "../Resources/Orthanc/Plugins/OrthancPluginCppWrapper.h"
#include "ICallbackRegistration.h"
#include "PythonString.h"

#include <sdk.h>


#if ORTHANC_PLUGINS_VERSION_IS_ABOVE(1, 10, 0)

static PyObject*   incomingCStoreInstanceFilter_ = NULL;


static int32_t IncomingCStoreInstanceFilter(uint16_t* dimseStatus,
                                            const OrthancPluginDicomInstance *instance)
{
  assert(dimseStatus != NULL &&
         instance != NULL);
  
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
     * Construct the arguments tuple (instance)
     **/
    PythonObject args2(lock, PyTuple_New(1));
    PyTuple_SetItem(args2.GetPyObject(), 0, pInst);

    PythonObject result(lock, PyObject_CallObject(incomingCStoreInstanceFilter_, args2.GetPyObject()));

    std::string traceback;
    if (lock.HasErrorOccurred(traceback))
    {
      ORTHANC_PLUGINS_LOG_ERROR("Error in the Python incoming-cstore-instance callback, traceback:\n" + traceback);
      return -1;
    }
    else
    {
      if (PyNumber_Check(result.GetPyObject()))
      {
        int32_t code = PyLong_AsLong(result.GetPyObject());

        if (code < 0)
        {
          ORTHANC_PLUGINS_LOG_ERROR("The Python incoming-cstore-instance filter has returned a negative value");
          return -1;
        }
        else if (code == 0)
        {
          return 1;  // The instance is to be stored
        }
        else if (code <= 0xffff)
        {
          // The instance is to be discarded with a custom DIMSE status
          *dimseStatus = static_cast<uint16_t>(code);
          return 0;  // Discard
        }
        else
        {
          ORTHANC_PLUGINS_LOG_ERROR("The Python incoming-cstore-instance filter has returned an out-of-range DIMSE status: " +
                                    boost::lexical_cast<std::string>(code));
          return -1;
        }
      }
      else
      {
        ORTHANC_PLUGINS_LOG_ERROR("The Python incoming-cstore-instance filter has not returned an integer");
        return -1;
      }
    }
  }
  catch (OrthancPlugins::PluginException& e)
  {
    return e.GetErrorCode();
  }
}

   
PyObject* RegisterIncomingCStoreInstanceFilter(PyObject* module, PyObject* args)
{
  // The GIL is locked at this point (no need to create "PythonLock")

  class Registration : public ICallbackRegistration
  {
  public:
    virtual void Register() ORTHANC_OVERRIDE
    {
      OrthancPluginRegisterIncomingCStoreInstanceFilter(
        OrthancPlugins::GetGlobalContext(), IncomingCStoreInstanceFilter);
    }
  };

  Registration registration;
  return ICallbackRegistration::Apply(
    registration, args, incomingCStoreInstanceFilter_, "Python incoming CStore instance filter");
}


void FinalizeIncomingCStoreInstanceFilter()
{
  ICallbackRegistration::Unregister(incomingCStoreInstanceFilter_);
}

#else

#warning OrthancPluginRegisterIncomingCStoreInstanceFilter() is not supported

PyObject* RegisterIncomingCStoreInstanceFilter(PyObject* module, PyObject* args)
{
  PyErr_SetString(PyExc_RuntimeError, "The version of your Orthanc SDK doesn't provide OrthancPluginRegisterIncomingCStoreInstanceFilter()");
  return NULL;
}

void FinalizeIncomingCStoreInstanceFilter()
{
}

#endif
