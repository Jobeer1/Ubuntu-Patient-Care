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


#include "StorageCommitmentScpCallback.h"

#include "PythonHeaderWrapper.h"

#include "../Resources/Orthanc/Plugins/OrthancPluginCppWrapper.h"
#include "ICallbackRegistration.h"
#include "PythonString.h"


static PyObject*   storageCommitmentScpCallback_ = NULL;
static PyObject*   storageCommitmentLookupCallback_ = NULL;


static OrthancPluginErrorCode StorageCommitmentSCPCallback(
  void**              handler /* out */,
  const char*         jobId,
  const char*         transactionUid,
  const char* const*  sopClassUids,
  const char* const*  sopInstanceUids,
  uint32_t            countInstances,
  const char*         remoteAet,
  const char*         calledAet)
{
  try
  {
    PythonLock lock;

    PythonObject args(lock, PyTuple_New(6));
    {
      PythonString str(lock, jobId);
      PyTuple_SetItem(args.GetPyObject(), 0, str.Release());
    }
    {
      PythonString str(lock, transactionUid);
      PyTuple_SetItem(args.GetPyObject(), 1, str.Release());
    }
    {
      PythonObject sopClassUidList(lock, PyList_New(countInstances));
      for (uint32_t i = 0; i < countInstances; i++)
      {
        PythonString str(lock, sopClassUids[i]);
        PyList_SetItem(sopClassUidList.GetPyObject(), i, str.Release());
      }
      PyTuple_SetItem(args.GetPyObject(), 2, sopClassUidList.Release());
      PythonObject sopInstanceUidList(lock, PyList_New(countInstances));
      for (uint32_t i = 0; i < countInstances; i++)
      {
        PythonString str(lock, sopInstanceUids[i]);
        PyList_SetItem(sopInstanceUidList.GetPyObject(), i, str.Release());
      }
      PyTuple_SetItem(args.GetPyObject(), 3, sopInstanceUidList.Release());
    }
    {
      PythonString str(lock, remoteAet);
      PyTuple_SetItem(args.GetPyObject(), 4, str.Release());
    }
    {
      PythonString str(lock, calledAet);
      PyTuple_SetItem(args.GetPyObject(), 5, str.Release());
    }

    PythonObject result(lock, PyObject_CallObject(storageCommitmentScpCallback_, args.GetPyObject()));
    *handler = result.Release();

    std::string traceback;
    if (lock.HasErrorOccurred(traceback))
    {
      ORTHANC_PLUGINS_LOG_ERROR("Error in the Python storage commitment SCP callback, traceback:\n" + traceback);
      return OrthancPluginErrorCode_Plugin;
    }
  }
  catch (OrthancPlugins::PluginException& e)
  {
    ORTHANC_PLUGINS_LOG_ERROR("Error in the Python storage commitment SCP callback: " +
                              std::string(e.What(OrthancPlugins::GetGlobalContext())));
  }
  return OrthancPluginErrorCode_Success;
}

static OrthancPluginErrorCode StorageCommitmentLookupCallback(
  OrthancPluginStorageCommitmentFailureReason* target /* out */,
  void*                                        handler,
  const char*                                  sopClassUid,
  const char*                                  sopInstanceUid)
{
  try
  {
    PythonLock lock;

    PythonObject args(lock, PyTuple_New(3));
    {
      PythonString str(lock, sopClassUid);
      PyTuple_SetItem(args.GetPyObject(), 0, str.Release());
    }
    {
      PythonString str(lock, sopInstanceUid);
      PyTuple_SetItem(args.GetPyObject(), 1, str.Release());
    }
    {
      PyObject* data = (PyObject*) handler;
      Py_INCREF(data);  // Keep a reference before it was stolen by PyTuple_SetItem.
      PyTuple_SetItem(args.GetPyObject(), 2, data);
    }

    PythonObject result(lock, PyObject_CallObject(storageCommitmentLookupCallback_, args.GetPyObject()));

    if (!PyLong_Check(result.GetPyObject()))
    {
      ORTHANC_PLUGINS_LOG_ERROR("The Python storage commitment Lookup callback has not returned an int as the return value");
      return OrthancPluginErrorCode_Plugin;
    }

    *target = static_cast<OrthancPluginStorageCommitmentFailureReason>(PyLong_AsLong(result.GetPyObject()));

    std::string traceback;
    if (lock.HasErrorOccurred(traceback))
    {
      ORTHANC_PLUGINS_LOG_ERROR("Error in the Python storage commitment Lookup callback, traceback:\n" + traceback);
      return OrthancPluginErrorCode_Plugin;
    }
  }
  catch (OrthancPlugins::PluginException& e)
  {
    ORTHANC_PLUGINS_LOG_ERROR("Error in the Python storage commitment Lookup callback: " +
                              std::string(e.What(OrthancPlugins::GetGlobalContext())));
  }
  return OrthancPluginErrorCode_Success;
}

static void StorageCommitmentDestructor(void *handler)
{
  PythonLock lock;
  Py_DECREF((PyObject*)handler);  // Release the reference
}

PyObject* RegisterStorageCommitmentScpCallback(PyObject* module, PyObject* args)
{
  // The GIL is locked at this point (no need to create "PythonLock")

  class Registration : public ICallbackRegistration
  {
  public:
    virtual void Register() ORTHANC_OVERRIDE
    {
      OrthancPluginRegisterStorageCommitmentScpCallback(
        OrthancPlugins::GetGlobalContext(),
        StorageCommitmentSCPCallback,
        StorageCommitmentDestructor,
        StorageCommitmentLookupCallback);
    }
  };

  {
    Registration registration;
    return ICallbackRegistration::Apply2(registration, args,
      storageCommitmentScpCallback_,
      storageCommitmentLookupCallback_,
      "Python storage commitment SCP & Lookup callback");
  }
}

void FinalizeStorageCommitmentScpCallback()
{
  ICallbackRegistration::Unregister(storageCommitmentScpCallback_);
  ICallbackRegistration::Unregister(storageCommitmentLookupCallback_);
}
