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


// http://edcjones.tripod.com/refcount.html
// https://docs.python.org/3/extending/extending.html

// https://www.codevate.com/blog/7-concurrency-with-embedded-python-in-a-multi-threaded-c-application
// https://fr.slideshare.net/YiLungTsai/embed-python


#include "DicomScpCallbacks.h"
#include "IncomingHttpRequestFilter.h"
#include "OnChangeCallback.h"
#include "OnStoredInstanceCallback.h"
#include "IncomingInstanceFilter.h"
#include "ReceivedInstanceCallback.h"
#include "StorageArea.h"
#include "StorageCommitmentScpCallback.h"

#include "PythonModule.h"
#include "PythonThreadsAllower.h"
#include "RestCallbacks.h"

#include "../Resources/Orthanc/Plugins/OrthancPluginCppWrapper.h"

#include <sdk.h>

#include <boost/algorithm/string/predicate.hpp>
#include <boost/filesystem.hpp>
#include <boost/thread.hpp>

// The "dl_iterate_phdr()" function (to walk through shared libraries)
// is not available on Microsoft Windows and Apple OS X
#if defined(_WIN32)
#  define HAS_DL_ITERATE  0
#elif defined(__APPLE__) && defined(__MACH__)
#  define HAS_DL_ITERATE  0
#else
#  define HAS_DL_ITERATE  1
#endif


#include "PythonString.h"

PyObject* LookupDictionary(PyObject* module, PyObject* args)
{
  const char* name = NULL;
  
  if (!PyArg_ParseTuple(args, "s", &name))
  {
    PyErr_SetString(PyExc_TypeError, "Please provide a string containing the name of the DICOM tag of interest");
    return NULL;
  }
  else
  {
    OrthancPluginDictionaryEntry entry;
    OrthancPluginErrorCode code;

    {
      PythonThreadsAllower allower;
      code = OrthancPluginLookupDictionary(OrthancPlugins::GetGlobalContext(), &entry, name);
    }
    
    if (code == OrthancPluginErrorCode_Success)
    {
      /**
       * "PyGILState_Ensure()" can be invoked several times from the
       * same thread, so no problem in creating a PythonLock even if
       * the GIL is already locked.
       **/
      PythonLock lock;
      
      PythonObject dict(lock, PyDict_New());

      {
        PythonObject tmp(lock, PyLong_FromUnsignedLong(entry.group));
        PyDict_SetItemString(dict.GetPyObject(), "Group", tmp.GetPyObject());
      }

      {
        PythonObject tmp(lock, PyLong_FromUnsignedLong(entry.element));
        PyDict_SetItemString(dict.GetPyObject(), "Element", tmp.GetPyObject());
      }

      {
        PythonObject tmp(lock, PyLong_FromUnsignedLong(entry.vr));
        PyDict_SetItemString(dict.GetPyObject(), "ValueRepresentation", tmp.GetPyObject());
      }

      {
        PythonObject tmp(lock, PyLong_FromUnsignedLong(entry.minMultiplicity));
        PyDict_SetItemString(dict.GetPyObject(), "MinMultiplicity", tmp.GetPyObject());
      }

      {
        PythonObject tmp(lock, PyLong_FromUnsignedLong(entry.maxMultiplicity));
        PyDict_SetItemString(dict.GetPyObject(), "MaxMultiplicity", tmp.GetPyObject());
      }
      
      return dict.Release();
    }
    else
    {
      std::string message = "Unknown DICOM tag: " + std::string(name);
      PyErr_SetString(PyExc_TypeError, message.c_str());
      return NULL;
    }
  }
}


PyObject* GetInstanceData(sdk_OrthancPluginDicomInstance_Object* self, PyObject *args)
{
  // The GIL is locked at this point (no need to create "PythonLock")

  if (self->object_ == NULL)
  {
    PyErr_SetString(PyExc_ValueError, "Invalid object");
    return NULL;
  }
  else
  {
    OrthancPluginDicomInstance* instance = self->object_;

    const void* data;
    size_t size;

    {
      PythonThreadsAllower allower;
      data = OrthancPluginGetInstanceData(OrthancPlugins::GetGlobalContext(), instance);
      size = OrthancPluginGetInstanceSize(OrthancPlugins::GetGlobalContext(), instance);
    }

    if (data == NULL &&
        size != 0)
    {
      PyErr_SetString(PyExc_ValueError, "Accessing an invalid orthanc.DicomInstance object");
      return NULL;  
    }
    else
    {
      return PyBytes_FromStringAndSize(reinterpret_cast<const char*>(data), size);
    }
  }
}


/**
 * Contrarily to "OrthancPluginGetImageBuffer()" that provides a
 * read-write pointer, the method "orthanc.Image.GetImageBuffer()"
 * returns a copy of the image buffer. Use "CreateImageFromBuffer()"
 * to create an image from a Python buffer.
 **/
PyObject* GetImageBuffer(sdk_OrthancPluginImage_Object* self, PyObject *args)
{
  // The GIL is locked at this point (no need to create "PythonLock")
  
  if (self->object_ == NULL)
  {
    PyErr_SetString(PyExc_ValueError, "Invalid object");
    return NULL;
  }
  else
  {
    OrthancPluginImage* image = self->object_;

    const void* buffer;
    size_t size;

    {
      PythonThreadsAllower allower;
      buffer = OrthancPluginGetImageBuffer(OrthancPlugins::GetGlobalContext(), image);
      size = (OrthancPluginGetImagePitch(OrthancPlugins::GetGlobalContext(), image) *
              OrthancPluginGetImageHeight(OrthancPlugins::GetGlobalContext(), image));
    }

    if (buffer == NULL &&
        size != 0)
    {
      PyErr_SetString(PyExc_ValueError, "Accessing an invalid orthanc.Image object");
      return NULL;  
    }
    else
    {
      return PyBytes_FromStringAndSize(reinterpret_cast<const char*>(buffer), size);
    }
  }
}


/**
 * This function is the Python alternative for function
 * "OrthancPluginCreateImageAccessor()". Indeed, it is not possible to
 * share a memory buffer between Orthanc and Python, so we have to
 * create a copy of the image.
 **/
PyObject* CreateImageFromBuffer(PyObject* module, PyObject* args)
{
  // The GIL is locked at this point (no need to create "PythonLock")

  unsigned long format, width, height, sourcePitch;
  Py_buffer buffer;

  if (!PyArg_ParseTuple(args, "kkkks*", &format, &width, &height, &sourcePitch, &buffer))
  {
    PyErr_SetString(PyExc_TypeError, "5 arguments are needed: image.PixelFormat, width, height, pitch and memory buffer");
    return NULL;
  }
  else if (static_cast<Py_ssize_t>(sourcePitch * height) != buffer.len)
  {
    PyBuffer_Release(&buffer);

    PyErr_SetString(PyExc_TypeError, "The size of the memory buffer must match the product of height by pitch");
    return NULL;
  }
  else
  {
    OrthancPluginImage* image;
    unsigned long targetPitch = 0;

    {
      PythonThreadsAllower allower;
      image = OrthancPluginCreateImage(
        OrthancPlugins::GetGlobalContext(), static_cast<OrthancPluginPixelFormat>(format), width, height);

      if (image != NULL)
      {
        targetPitch = OrthancPluginGetImagePitch(OrthancPlugins::GetGlobalContext(), image);
      }
    }

    if (image == NULL)
    {
      PyBuffer_Release(&buffer);

      PyErr_SetString(PyExc_ValueError, "Cannot create the image");
      return NULL;  
    }
    else
    {
      // Copy the image line by line
      const uint8_t* sourcePixels = reinterpret_cast<const uint8_t*>(buffer.buf);
      uint8_t* targetPixels = reinterpret_cast<uint8_t*>(OrthancPluginGetImageBuffer(OrthancPlugins::GetGlobalContext(), image));

      unsigned long rowSize = std::min(sourcePitch, targetPitch);
      
      for (unsigned int y = 0; y < height; y++)
      {
        memcpy(targetPixels, sourcePixels, rowSize);
        targetPixels += targetPitch;
        sourcePixels += sourcePitch;
      }
             
      PyBuffer_Release(&buffer);

      {
        PyObject *argList = Py_BuildValue("Lb", image, false /* not borrowed */);
        PyObject *python = PyObject_CallObject((PyObject *) GetOrthancPluginImageType(), argList);
        Py_DECREF(argList);
        return python;
      }
    }
  }
}


#if ORTHANC_PLUGINS_VERSION_IS_ABOVE(1, 12, 8)
PyObject* GetKeyValue(PyObject* module, PyObject* args)
{
  // The GIL is locked at this point (no need to create "PythonLock")

  const char* storeId = NULL;
  const char* key = NULL;

  if (!PyArg_ParseTuple(args, "ss", &storeId, &key))
  {
    PyErr_SetString(PyExc_TypeError, "Bad arguments");
    return NULL;
  }
  else
  {
    uint8_t found = 0;
    OrthancPlugins::MemoryBuffer buffer;
    OrthancPluginErrorCode code;

    {
      PythonThreadsAllower allower;
      code = OrthancPluginGetKeyValue(OrthancPlugins::GetGlobalContext(), &found, *buffer, storeId, key);
    }

    if (code == OrthancPluginErrorCode_Success)
    {
      if (found)
      {
        return PyBytes_FromStringAndSize(reinterpret_cast<const char*>(buffer.GetData()), buffer.GetSize());
      }
      else
      {
        return Py_None;
      }
    }
    else
    {
      PyErr_SetString(PyExc_TypeError, OrthancPluginGetErrorDescription(OrthancPlugins::GetGlobalContext(), code));
      return NULL;
    }
  }
}
#endif


#if ORTHANC_PLUGINS_VERSION_IS_ABOVE(1, 12, 8)
PyObject* DequeueValue(PyObject* module, PyObject* args)
{
  // The GIL is locked at this point (no need to create "PythonLock")

  const char* queueId = NULL;
  unsigned long origin = 0;

  if (!PyArg_ParseTuple(args, "sl", &queueId, &origin))
  {
    PyErr_SetString(PyExc_TypeError, "Bad arguments");
    return NULL;
  }
  else
  {
    uint8_t found = 0;
    OrthancPlugins::MemoryBuffer buffer;
    OrthancPluginErrorCode code;

    {
      PythonThreadsAllower allower;
      code = OrthancPluginDequeueValue(OrthancPlugins::GetGlobalContext(), &found, *buffer, queueId,
                                       static_cast<OrthancPluginQueueOrigin>(origin));
    }

    if (code == OrthancPluginErrorCode_Success)
    {
      if (found)
      {
        return PyBytes_FromStringAndSize(reinterpret_cast<const char*>(buffer.GetData()), buffer.GetSize());
      }
      else
      {
        return Py_None;
      }
    }
    else
    {
      PyErr_SetString(PyExc_TypeError, OrthancPluginGetErrorDescription(OrthancPlugins::GetGlobalContext(), code));
      return NULL;
    }
  }
}
#endif


#if ORTHANC_PLUGINS_VERSION_IS_ABOVE(1, 12, 8)
PyObject* GetQueueSize(PyObject* module, PyObject* args)
{
  // The GIL is locked at this point (no need to create "PythonLock")

  const char* queueId = NULL;

  if (!PyArg_ParseTuple(args, "s", &queueId))
  {
    PyErr_SetString(PyExc_TypeError, "Bad arguments");
    return NULL;
  }
  else
  {
    uint64_t size = 0;
    OrthancPluginErrorCode code;

    {
      PythonThreadsAllower allower;
      code = OrthancPluginGetQueueSize(OrthancPlugins::GetGlobalContext(), queueId, &size);
    }

    if (code == OrthancPluginErrorCode_Success)
    {
      return PyLong_FromLong(size);
    }
    else
    {
      PyErr_SetString(PyExc_TypeError, OrthancPluginGetErrorDescription(OrthancPlugins::GetGlobalContext(), code));
      return NULL;
    }
  }
}
#endif


#if ORTHANC_PLUGINS_VERSION_IS_ABOVE(1, 12, 8)
PyObject* KeysValuesIteratorNext(sdk_OrthancPluginKeysValuesIterator_Object* self, PyObject *args)
{
  // The GIL is locked at this point (no need to create "PythonLock")

  if (self->object_ == NULL)
  {
    PyErr_SetString(PyExc_ValueError, "Invalid object");
    return NULL;
  }
  else
  {
    uint8_t done;
    OrthancPluginErrorCode code;

    {
      PythonThreadsAllower allower;
      code = OrthancPluginKeysValuesIteratorNext(OrthancPlugins::GetGlobalContext(), &done, self->object_);
    }

    if (code == OrthancPluginErrorCode_Success)
    {
      return PyBool_FromLong(done ? 1 : 0);
    }
    else
    {
      PyErr_SetString(PyExc_TypeError, OrthancPluginGetErrorDescription(OrthancPlugins::GetGlobalContext(), code));
      return NULL;
    }
  }
}
#endif


#if ORTHANC_PLUGINS_VERSION_IS_ABOVE(1, 12, 9)
PyObject* SetStableStatus(PyObject* module, PyObject* args)
{
  const char* resourceId = NULL;
  long int stableStatus = 0;

  if (!PyArg_ParseTuple(args, "sl", &resourceId, &stableStatus))
  {
    PyErr_SetString(PyExc_TypeError, "Please provide a string containing the resourceId and a integer with 0 for stable and 1 for unstable");
    return NULL;
  }
  else
  {
    OrthancPluginErrorCode code;
    uint8_t statusHasChanged;

    {
      PythonThreadsAllower allower;
      code = OrthancPluginSetStableStatus(OrthancPlugins::GetGlobalContext(), &statusHasChanged, resourceId, static_cast<OrthancPluginStableStatus>(stableStatus));
    }
    
    if (code == OrthancPluginErrorCode_Success)
    {
      /**
       * "PyGILState_Ensure()" can be invoked several times from the
       * same thread, so no problem in creating a PythonLock even if
       * the GIL is already locked.
       **/
      PythonLock lock;

      PythonObject tuple(lock, PyTuple_New(2));
      PyTuple_SetItem(tuple.GetPyObject(), 0, PyLong_FromUnsignedLong(static_cast<unsigned long>(code)));
      PyTuple_SetItem(tuple.GetPyObject(), 1, PyLong_FromLong(static_cast<long>(statusHasChanged)));
      
      return tuple.Release();
    }
    else
    {
      std::string message = "Failed to change stable status of resource: " + std::string(resourceId);
      PyErr_SetString(PyExc_TypeError, message.c_str());
      return NULL;
    }
  }
}
#endif


static bool pythonEnabled_ = false;
static std::string userScriptName_;
static boost::thread displayMemoryUsageThread_;
static bool displayMemoryUsageStopping_ = false;


#if HAS_DL_ITERATE == 1

#include <dlfcn.h>
#include <link.h>  // For dl_phdr_info

static int ForceImportCallback(struct dl_phdr_info *info, size_t size, void *data)
{ 
  /**
   * The following line solves the error: "ImportError:
   * /usr/lib/python2.7/dist-packages/PIL/_imaging.x86_64-linux-gnu.so:
   * undefined symbol: PyExc_SystemError"
   * https://stackoverflow.com/a/48517485/881731
   * 
   * dlopen("/usr/lib/x86_64-linux-gnu/libpython2.7.so", RTLD_NOW | RTLD_LAZY | RTLD_GLOBAL);
   * 
   * Another fix consists in using LD_PRELOAD as follows:
   * LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libpython2.7.so ~/Subversion/orthanc/i/Orthanc tutu.json
   **/
    
  std::string module(info->dlpi_name);

  if (module.find("python") != std::string::npos)
  {
    ORTHANC_PLUGINS_LOG_WARNING("Force global loading of Python shared library: " + module);
    dlopen(module.c_str(), RTLD_NOW | RTLD_LAZY | RTLD_GLOBAL);
  }
  
  return 0;
}

#endif


static void DisplayMemoryUsageThread()
{
  {
    PythonLock lock;
    lock.ExecuteCommand("import tracemalloc");
    lock.ExecuteCommand("tracemalloc.start()");
  }

  while (!displayMemoryUsageStopping_)
  {
    {
      PythonLock lock;
      lock.ExecuteCommand("print('Python memory usage: %0.03fMB' % "
                          "(tracemalloc.get_traced_memory() [0] / (1024.0 * 1024.0)))");
    }

    boost::this_thread::sleep(boost::posix_time::seconds(1));
  }
}


extern "C"
{
  ORTHANC_PLUGINS_API int32_t OrthancPluginInitialize(OrthancPluginContext* c)
  {
    OrthancPlugins::SetGlobalContext(c, PLUGIN_NAME);
    ORTHANC_PLUGINS_LOG_WARNING("Python plugin is initializing");
    

    /* Check the version of the Orthanc core */
    if (OrthancPluginCheckVersion(c) == 0)
    {
      char info[1024];
      sprintf(info, "Your version of Orthanc (%s) must be above %d.%d.%d to run this plugin",
              c->orthancVersion,
              ORTHANC_PLUGINS_MINIMAL_MAJOR_NUMBER,
              ORTHANC_PLUGINS_MINIMAL_MINOR_NUMBER,
              ORTHANC_PLUGINS_MINIMAL_REVISION_NUMBER);
      OrthancPluginLogError(c, info);
      return -1;
    }
    
    OrthancPlugins::SetDescription(PLUGIN_NAME, "Run Python scripts as Orthanc plugins");
    
    ORTHANC_PLUGINS_LOG_WARNING("Version of the Orthanc SDK in use by the Python plugin: " +
                                boost::lexical_cast<std::string>(ORTHANC_PLUGINS_MINIMAL_MAJOR_NUMBER) + "." +
                                boost::lexical_cast<std::string>(ORTHANC_PLUGINS_MINIMAL_MINOR_NUMBER) + "." +
                                boost::lexical_cast<std::string>(ORTHANC_PLUGINS_MINIMAL_REVISION_NUMBER));

    try
    {
      /**
       * Detection of the user script
       **/

      OrthancPlugins::OrthancConfiguration globalConfig;

      OrthancPlugins::OrthancConfiguration pythonConfig;
      globalConfig.GetSection(pythonConfig, "Python");

      std::string script;
      if (!globalConfig.LookupStringValue(script, "PythonScript") &&
          !pythonConfig.LookupStringValue(script, "Path"))
      {
        pythonEnabled_ = false;
      
        ORTHANC_PLUGINS_LOG_WARNING("Options \"PythonScript\" and \"Python.Path\" are not provided: "
                                    "Python scripting is disabled");
      }
      else
      {
        pythonEnabled_ = true;
      
        /**
         * Installation of the user script
         **/

        const boost::filesystem::path path(script);
        if (!boost::iequals(path.extension().string(), ".py"))
        {
          ORTHANC_PLUGINS_LOG_ERROR("Python script must have the \".py\" file extension: " +
                                    path.string());
          return -1;
        }

        if (!boost::filesystem::is_regular_file(path))
        {
          ORTHANC_PLUGINS_LOG_ERROR("Inexistent directory for the Python script: " +
                                    path.string());
          return -1;
        }

        boost::filesystem::path userScriptDirectory = boost::filesystem::absolute(path).parent_path();

        {
          boost::filesystem::path module = path.filename().replace_extension("");
          userScriptName_ = module.string();
        }

        ORTHANC_PLUGINS_LOG_WARNING("Using Python script \"" + userScriptName_ +
                                    ".py\" from directory: " + userScriptDirectory.string());
    
    
        /**
         * Initialization of Python
         **/

        PythonThreadsAllower::SetAllowThreads(pythonConfig.GetBooleanValue("AllowThreads", false));

        const bool isVerbose = (globalConfig.GetBooleanValue("PythonVerbose", false) ||
                                pythonConfig.GetBooleanValue("Verbose", false));

#if HAS_DL_ITERATE == 1
        dl_iterate_phdr(ForceImportCallback, NULL);
#endif

        PythonLock::GlobalInitialize("orthanc", "OrthancException", GetOrthancSdkFunctions, RegisterOrthancSdk, isVerbose);
        PythonLock::AddSysPath(userScriptDirectory.string());

        if (pythonConfig.GetBooleanValue("DisplayMemoryUsage", false))
        {
          displayMemoryUsageThread_ = boost::thread(DisplayMemoryUsageThread);
        }

      
        /**
         * Force loading the declarations in the user script
         **/

        PythonLock lock;

        {
          PythonModule module(lock, userScriptName_);
        }
      
        std::string traceback;
        if (lock.HasErrorOccurred(traceback))
        {
          ORTHANC_PLUGINS_LOG_ERROR("Error during the installation of the Python script, "
                                    "traceback:\n" + traceback);
          return -1;
        }
      }
    }
    catch (ORTHANC_PLUGINS_EXCEPTION_CLASS& e)
    {
      ORTHANC_PLUGINS_LOG_ERROR("Exception while starting the Python plugin: " +
                                std::string(e.What(c)));
      return -1;
    }
    
    return 0;
  }


  ORTHANC_PLUGINS_API void OrthancPluginFinalize()
  {
    ORTHANC_PLUGINS_LOG_WARNING("Python plugin is finalizing");

    if (pythonEnabled_)
    {
      FinalizeOnChangeCallback();
      FinalizeRestCallbacks();
      FinalizeOnStoredInstanceCallback();
      FinalizeIncomingHttpRequestFilter();
      FinalizeDicomScpCallbacks();

      displayMemoryUsageStopping_ = true;

      if (displayMemoryUsageThread_.joinable())
      {
        displayMemoryUsageThread_.join();
      }
      
      PythonLock::GlobalFinalize();
    }

    OrthancPlugins::ResetGlobalContext();
  }


  ORTHANC_PLUGINS_API const char* OrthancPluginGetName()
  {
    return PLUGIN_NAME;
  }


  ORTHANC_PLUGINS_API const char* OrthancPluginGetVersion()
  {
    return PLUGIN_VERSION;
  }
}
