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


#include "StorageArea.h"

#include "PythonHeaderWrapper.h"

#include "../Resources/Orthanc/Plugins/OrthancPluginCppWrapper.h"
#include "PythonString.h"


static PyObject*  createCallback_ = NULL;
static PyObject*  readCallback_ = NULL;
static PyObject*  removeCallback_ = NULL;


static OrthancPluginErrorCode RunCallback(PythonLock& lock,
                                          PyObject* callback,
                                          const PythonObject& args,
                                          const std::string& name)
{
  PythonObject result(lock, PyObject_CallObject(callback, args.GetPyObject()));

  std::string traceback;
  if (lock.HasErrorOccurred(traceback))
  {
    ORTHANC_PLUGINS_LOG_ERROR("Error in the Python " + name + " callback, traceback:\n" + traceback);
    return OrthancPluginErrorCode_Plugin;
  }
  else
  {
    return OrthancPluginErrorCode_Success;
  }
}


static OrthancPluginErrorCode StorageCreate(const char *uuid,
                                            const void *content,
                                            int64_t size,
                                            OrthancPluginContentType type)
{
  try
  {
    if (createCallback_ == NULL)
    {
      throw OrthancPlugins::PluginException(OrthancPluginErrorCode_InternalError);
    }
    
    PythonLock lock;

    PythonObject args(lock, PyTuple_New(3));

    PythonString str(lock, uuid);
    PyTuple_SetItem(args.GetPyObject(), 0, str.Release());
    PyTuple_SetItem(args.GetPyObject(), 1, PyLong_FromLong(type));
    PyTuple_SetItem(args.GetPyObject(), 2, PyBytes_FromStringAndSize(reinterpret_cast<const char*>(content), size));

    return RunCallback(lock, createCallback_, args, "StorageCreate");
  }
  catch (OrthancPlugins::PluginException& e)
  {
    return e.GetErrorCode();
  }
}


static OrthancPluginErrorCode StorageRead(void **content,
                                          int64_t *size,
                                          const char *uuid,
                                          OrthancPluginContentType type)
{
  try
  {
    if (readCallback_ == NULL)
    {
      throw OrthancPlugins::PluginException(OrthancPluginErrorCode_InternalError);
    }
    
    PythonLock lock;

    PythonObject args(lock, PyTuple_New(2));

    PythonString str(lock, uuid);
    PyTuple_SetItem(args.GetPyObject(), 0, str.Release());
    PyTuple_SetItem(args.GetPyObject(), 1, PyLong_FromLong(type));
    
    PythonObject result(lock, PyObject_CallObject(readCallback_, args.GetPyObject()));
    
    std::string traceback;
    if (lock.HasErrorOccurred(traceback))
    {
      ORTHANC_PLUGINS_LOG_ERROR("Error in the Python StorageRead callback, traceback:\n" + traceback);
      return OrthancPluginErrorCode_Plugin;
    }
    else if (!PyBytes_Check(result.GetPyObject()))
    {
      ORTHANC_PLUGINS_LOG_ERROR("The Python StorageRead callback has not returned a byte array as expected");
      return OrthancPluginErrorCode_Plugin;
    }
    else
    {
      char* pythonBuffer = NULL;
      Py_ssize_t pythonSize = 0;
      if (PyBytes_AsStringAndSize(result.GetPyObject(), &pythonBuffer, &pythonSize) == 1)
      {
        ORTHANC_PLUGINS_LOG_ERROR("Cannot access the byte buffer returned by the Python StorageRead callback");
        return OrthancPluginErrorCode_Plugin;
      }
      else
      {
        if (pythonSize == 0)
        {
          *content = NULL;
          *size = 0;
        }
        else
        {
          *content = malloc(pythonSize);
          *size = pythonSize;
          if (*content == NULL)
          {
            return OrthancPluginErrorCode_NotEnoughMemory;
          }

          memcpy(*content, pythonBuffer, pythonSize);
        }
        
        return OrthancPluginErrorCode_Success;
      }
    }
  }
  catch (OrthancPlugins::PluginException& e)
  {
    return e.GetErrorCode();
  }
}


static OrthancPluginErrorCode StorageRemove(const char *uuid,
                                            OrthancPluginContentType type)
{
  try
  {
    if (removeCallback_ == NULL)
    {
      throw OrthancPlugins::PluginException(OrthancPluginErrorCode_InternalError);
    }
    
    PythonLock lock;

    PythonObject args(lock, PyTuple_New(2));

    PythonString str(lock, uuid);
    PyTuple_SetItem(args.GetPyObject(), 0, str.Release());
    PyTuple_SetItem(args.GetPyObject(), 1, PyLong_FromLong(type));

    return RunCallback(lock, removeCallback_, args, "StorageRemove");
  }
  catch (OrthancPlugins::PluginException& e)
  {
    return e.GetErrorCode();
  }
}


PyObject* RegisterStorageArea(PyObject* module, PyObject* args)
{
  // The GIL is locked at this point (no need to create "PythonLock")

  PyObject* a = NULL;
  PyObject* b = NULL;
  PyObject* c = NULL;

  if (!PyArg_ParseTuple(args, "OOO", &a, &b, &c) ||
      a == NULL ||
      b == NULL ||
      c == NULL)
  {
    PyErr_SetString(PyExc_ValueError, "Expected three callback functions to register a custom storage area");
    return NULL;
  }
  else if (createCallback_ != NULL ||
           readCallback_ != NULL ||
           removeCallback_ != NULL)
  {
    PyErr_SetString(PyExc_RuntimeError, "Cannot register twice a custom storage area");
    return NULL;
  }
  else
  {
    ORTHANC_PLUGINS_LOG_INFO("Registering a custom storage area in Python");

    OrthancPluginRegisterStorageArea(OrthancPlugins::GetGlobalContext(),
                                     StorageCreate, StorageRead, StorageRemove);
    
    createCallback_ = a;
    Py_XINCREF(createCallback_);
    
    readCallback_ = b;
    Py_XINCREF(readCallback_);
    
    removeCallback_ = c;
    Py_XINCREF(removeCallback_);
    
    Py_INCREF(Py_None);
    return Py_None;
  }
}


void FinalizeStorageArea()
{
  PythonLock lock;
  
  if (createCallback_ != NULL)
  {
    Py_XDECREF(createCallback_);
  }
  
  if (readCallback_ != NULL)
  {
    Py_XDECREF(readCallback_);
  }
  
  if (removeCallback_ != NULL)
  {
    Py_XDECREF(removeCallback_);
  }
}
