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


#include "DicomScpCallbacks.h"

#include "PythonHeaderWrapper.h"

#include "../Resources/Orthanc/Plugins/OrthancPluginCppWrapper.h"
#include "ICallbackRegistration.h"
#include "PythonString.h"

#include <sdk.h>


static PyObject* findScpCallback_ = NULL;
static PyObject* moveScpCallback_ = NULL;
static PyObject* worklistScpCallback_ = NULL;

// version 2 of Move callbacks
static PyObject* createMoveScpDriverCallback_ = NULL;
static PyObject* getMoveSizeCallback_ = NULL;
static PyObject* applyMoveCallback_ = NULL;
static PyObject* freeMoveCallback_ = NULL;


static PyObject *GetFindQueryTag(sdk_OrthancPluginFindQuery_Object* self,
                                 PyObject *args,
                                 bool isGroup)
{
  unsigned long index;
  uint16_t group, element;
  
  if (self->object_ == NULL)
  {
    PyErr_SetString(PyExc_ValueError, "Invalid object");
    return NULL;
  }
  else if (!PyArg_ParseTuple(args, "k", &index))
  {
    PyErr_SetString(PyExc_TypeError, "Index is missing");
    return NULL;
  }
  else if (OrthancPluginGetFindQueryTag(OrthancPlugins::GetGlobalContext(), &group, &element, self->object_, index) !=
           OrthancPluginErrorCode_Success)
  {
    PyErr_SetString(PyExc_ValueError, "Index is out of range");
    return NULL;
  }
  else if (isGroup)
  {
    return PyLong_FromUnsignedLong(group);
  }
  else
  {
    return PyLong_FromUnsignedLong(element);
  }
}



// Check out "CUSTOM_METHODS" in "../CodeAnalysis/ParseOrthancSDK.py"
PyObject *GetFindQueryTagGroup(sdk_OrthancPluginFindQuery_Object* self, PyObject *args)
{
  return GetFindQueryTag(self, args, true);
}

PyObject *GetFindQueryTagElement(sdk_OrthancPluginFindQuery_Object* self, PyObject *args)
{
  return GetFindQueryTag(self, args, false);
}
// End of "CUSTOM_METHODS"



static OrthancPluginErrorCode FindCallback(OrthancPluginFindAnswers *answers,
                                           const OrthancPluginFindQuery *query,
                                           const char *issuerAet,
                                           const char *calledAet)
{
  try
  {
    PythonLock lock;

    PyObject *pAnswers, *pQuery;
    
    {
      PythonObject args(lock, PyTuple_New(2));
      PyTuple_SetItem(args.GetPyObject(), 0, PyLong_FromSsize_t((intptr_t) answers));
      PyTuple_SetItem(args.GetPyObject(), 1, PyBool_FromLong(true /* borrowed, don't destruct */));
      pAnswers = PyObject_CallObject((PyObject *) GetOrthancPluginFindAnswersType(), args.GetPyObject());
    }
    
    {
      PythonObject args(lock, PyTuple_New(2));
      PyTuple_SetItem(args.GetPyObject(), 0, PyLong_FromSsize_t((intptr_t) query));
      PyTuple_SetItem(args.GetPyObject(), 1, PyBool_FromLong(true /* borrowed, don't destruct */));
      pQuery = PyObject_CallObject((PyObject *) GetOrthancPluginFindQueryType(), args.GetPyObject());
    }
    
    PythonString pIssuerAet(lock, issuerAet);
    PythonString pCalledAet(lock, calledAet);

    {
      PythonObject args(lock, PyTuple_New(4));
      PyTuple_SetItem(args.GetPyObject(), 0, pAnswers);
      PyTuple_SetItem(args.GetPyObject(), 1, pQuery);
      PyTuple_SetItem(args.GetPyObject(), 2, pIssuerAet.Release());
      PyTuple_SetItem(args.GetPyObject(), 3, pCalledAet.Release());

      assert(findScpCallback_ != NULL);
      PythonObject result(lock, PyObject_CallObject(findScpCallback_, args.GetPyObject()));
    }

    return lock.CheckCallbackSuccess("Python C-FIND SCP callback");
  }
  catch (OrthancPlugins::PluginException& e)
  {
    return e.GetErrorCode();
  }
}



class IMoveDriver : public boost::noncopyable
{
public:
  virtual ~IMoveDriver()
  {
  }

  virtual void Apply() = 0;
};

   
static void* CreateMoveCallback(OrthancPluginResourceType resourceType,
                                const char *patientId,
                                const char *accessionNumber,
                                const char *studyInstanceUid,
                                const char *seriesInstanceUid,
                                const char *sopInstanceUid,
                                const char *originatorAet,
                                const char *sourceAet,
                                const char *targetAet,
                                uint16_t originatorId)
{
  class Driver : public IMoveDriver
  {
  private:
    OrthancPluginResourceType  resourceType_;
    std::string                patientId_;
    std::string                accessionNumber_;
    std::string                studyInstanceUid_;
    std::string                seriesInstanceUid_;
    std::string                sopInstanceUid_;
    std::string                originatorAet_;
    std::string                sourceAet_;
    std::string                targetAet_;
    uint16_t                   originatorId_;
    
  public:
    Driver(OrthancPluginResourceType resourceType,
           const char *patientId,
           const char *accessionNumber,
           const char *studyInstanceUid,
           const char *seriesInstanceUid,
           const char *sopInstanceUid,
           const char *originatorAet,
           const char *sourceAet,
           const char *targetAet,
           uint16_t originatorId) :
      resourceType_(resourceType),
      originatorId_(originatorId)
    {
      if (patientId != NULL)
      {
        patientId_.assign(patientId);
      }

      if (accessionNumber != NULL)
      {
        accessionNumber_.assign(accessionNumber);
      }
      
      if (studyInstanceUid != NULL)
      {
        studyInstanceUid_.assign(studyInstanceUid);
      }

      if (seriesInstanceUid != NULL)
      {
        seriesInstanceUid_.assign(seriesInstanceUid);
      }

      if (sopInstanceUid != NULL)
      {
        sopInstanceUid_.assign(sopInstanceUid);
      }

      if (originatorAet != NULL)
      {
        originatorAet_.assign(originatorAet);
      }

      if (sourceAet != NULL)
      {
        sourceAet_.assign(sourceAet);
      }

      if (targetAet != NULL)
      {
        targetAet_.assign(targetAet);
      }
    }

    
    virtual void Apply() ORTHANC_OVERRIDE
    {
      PythonLock lock;

      PythonObject kw(lock, PyDict_New());

      std::string level;
      switch (resourceType_)
      {
        case OrthancPluginResourceType_Patient:
          level = "PATIENT";
          break;
          
        case OrthancPluginResourceType_Study:
          level = "STUDY";
          break;
          
        case OrthancPluginResourceType_Series:
          level = "SERIES";
          break;
          
        case OrthancPluginResourceType_Instance:
          level = "INSTANCE";
          break;

        default:
          throw OrthancPlugins::PluginException(OrthancPluginErrorCode_ParameterOutOfRange);
      }

      {
        PythonString tmp(lock, level);
        PyDict_SetItemString(kw.GetPyObject(), "Level", tmp.GetPyObject());
      }

      {
        PythonString tmp(lock, patientId_);
        PyDict_SetItemString(kw.GetPyObject(), "PatientID", tmp.GetPyObject());
      }

      {
        PythonString tmp(lock, accessionNumber_);
        PyDict_SetItemString(kw.GetPyObject(), "AccessionNumber", tmp.GetPyObject());
      }

      {
        PythonString tmp(lock, studyInstanceUid_);
        PyDict_SetItemString(kw.GetPyObject(), "StudyInstanceUID", tmp.GetPyObject());
      }

      {
        PythonString tmp(lock, seriesInstanceUid_);
        PyDict_SetItemString(kw.GetPyObject(), "SeriesInstanceUID", tmp.GetPyObject());
      }

      {
        PythonString tmp(lock, sopInstanceUid_);
        PyDict_SetItemString(kw.GetPyObject(), "SOPInstanceUID", tmp.GetPyObject());
      }

      {
        PythonString tmp(lock, originatorAet_);
        PyDict_SetItemString(kw.GetPyObject(), "OriginatorAET", tmp.GetPyObject());
      }

      {
        PythonString tmp(lock, sourceAet_);
        PyDict_SetItemString(kw.GetPyObject(), "SourceAET", tmp.GetPyObject());
      }

      {
        PythonString tmp(lock, targetAet_);
        PyDict_SetItemString(kw.GetPyObject(), "TargetAET", tmp.GetPyObject());
      }

      {
        PythonObject tmp(lock, PyLong_FromUnsignedLong(originatorId_));
        PyDict_SetItemString(kw.GetPyObject(), "OriginatorID", tmp.GetPyObject());
      }

      PythonObject args(lock, PyTuple_New(0));

      assert(moveScpCallback_ != NULL);
      PythonObject result(lock, PyObject_Call(moveScpCallback_, args.GetPyObject(), kw.GetPyObject()));

      OrthancPluginErrorCode code = lock.CheckCallbackSuccess("Python C-MOVE SCP callback");
      if (code != OrthancPluginErrorCode_Success)
      {
        throw OrthancPlugins::PluginException(code);
      }
    }
  };
  
  try
  {
    return new Driver(resourceType, patientId, accessionNumber, studyInstanceUid,
                      seriesInstanceUid, sopInstanceUid, originatorAet, sourceAet,
                      targetAet, originatorId);
  }
  catch (OrthancPlugins::PluginException& e)
  {
    return NULL;
  }
}


static uint32_t GetMoveSize(void *moveDriver)
{
  assert(moveDriver != NULL);
  return 1;
}


OrthancPluginErrorCode ApplyMove(void *moveDriver)
{
  assert(moveDriver != NULL);
  
  try
  {
    reinterpret_cast<IMoveDriver*>(moveDriver)->Apply();
    return OrthancPluginErrorCode_Success;
  }
  catch (OrthancPlugins::PluginException& e)
  {
    return e.GetErrorCode();
  }
}

   
void FreeMove(void *moveDriver)
{
  assert(moveDriver != NULL);
  delete reinterpret_cast<IMoveDriver*>(moveDriver);
}


static void* CreateMoveCallback2(OrthancPluginResourceType resourceType,
                                 const char *patientId,
                                 const char *accessionNumber,
                                 const char *studyInstanceUid,
                                 const char *seriesInstanceUid,
                                 const char *sopInstanceUid,
                                 const char *originatorAet,
                                 const char *sourceAet,
                                 const char *targetAet,
                                 uint16_t originatorId)
{
  assert(createMoveScpDriverCallback_ != NULL);

  try
  {
    std::string _patientId, _accessionNumber, _studyInstanceUid, _seriesInstanceUid, _sopInstanceUid, _originatorAet, _sourceAet, _targetAet;
    if (patientId != NULL)
    {
      _patientId.assign(patientId);
    }

    if (accessionNumber != NULL)
    {
      _accessionNumber.assign(accessionNumber);
    }
    
    if (studyInstanceUid != NULL)
    {
      _studyInstanceUid.assign(studyInstanceUid);
    }

    if (seriesInstanceUid != NULL)
    {
      _seriesInstanceUid.assign(seriesInstanceUid);
    }

    if (sopInstanceUid != NULL)
    {
      _sopInstanceUid.assign(sopInstanceUid);
    }

    if (originatorAet != NULL)
    {
      _originatorAet.assign(originatorAet);
    }

    if (sourceAet != NULL)
    {
      _sourceAet.assign(sourceAet);
    }

    if (targetAet != NULL)
    {
      _targetAet.assign(targetAet);
    }

    PythonLock lock;

    PythonObject kw(lock, PyDict_New());

    std::string level;
    switch (resourceType)
    {
      case OrthancPluginResourceType_Patient:
        level = "PATIENT";
        break;
        
      case OrthancPluginResourceType_Study:
        level = "STUDY";
        break;
        
      case OrthancPluginResourceType_Series:
        level = "SERIES";
        break;
        
      case OrthancPluginResourceType_Instance:
        level = "INSTANCE";
        break;

      default:
        throw OrthancPlugins::PluginException(OrthancPluginErrorCode_ParameterOutOfRange);
    }

    {
      PythonString tmp(lock, level);
      PyDict_SetItemString(kw.GetPyObject(), "Level", tmp.GetPyObject());
    }

    {
      PythonString tmp(lock, _patientId);
      PyDict_SetItemString(kw.GetPyObject(), "PatientID", tmp.GetPyObject());
    }

    {
      PythonString tmp(lock, _accessionNumber);
      PyDict_SetItemString(kw.GetPyObject(), "AccessionNumber", tmp.GetPyObject());
    }

    {
      PythonString tmp(lock, _studyInstanceUid);
      PyDict_SetItemString(kw.GetPyObject(), "StudyInstanceUID", tmp.GetPyObject());
    }

    {
      PythonString tmp(lock, _seriesInstanceUid);
      PyDict_SetItemString(kw.GetPyObject(), "SeriesInstanceUID", tmp.GetPyObject());
    }

    {
      PythonString tmp(lock, _sopInstanceUid);
      PyDict_SetItemString(kw.GetPyObject(), "SOPInstanceUID", tmp.GetPyObject());
    }

    {
      PythonString tmp(lock, _originatorAet);
      PyDict_SetItemString(kw.GetPyObject(), "OriginatorAET", tmp.GetPyObject());
    }

    {
      PythonString tmp(lock, _sourceAet);
      PyDict_SetItemString(kw.GetPyObject(), "SourceAET", tmp.GetPyObject());
    }

    {
      PythonString tmp(lock, _targetAet);
      PyDict_SetItemString(kw.GetPyObject(), "TargetAET", tmp.GetPyObject());
    }

    {
      PythonObject tmp(lock, PyLong_FromUnsignedLong(originatorId));
      PyDict_SetItemString(kw.GetPyObject(), "OriginatorID", tmp.GetPyObject());
    }

    PythonObject args(lock, PyTuple_New(0));

    // Note: the result is not attached to the PythonLock because we want it to survive after this call since 
    // the result is the python move driver that will be passed as first argument to GetMoveSize, Apply and Free.
    // After the PyObject_Call, result's ref count is 1 -> no need to add a reference but we need to decref explicitely
    // to delete the object at the end of the move.
    PyObject* result = PyObject_Call(createMoveScpDriverCallback_, args.GetPyObject(), kw.GetPyObject());

    OrthancPluginErrorCode code = lock.CheckCallbackSuccess("Python C-MOVE SCP callback (Create)");
    if (code != OrthancPluginErrorCode_Success)
    {
      throw OrthancPlugins::PluginException(code);
    }

    return result;
  }
  catch (OrthancPlugins::PluginException& e)
  {
    return NULL;
  }
}


static uint32_t GetMoveSize2(void *moveDriver)
{
  assert(moveDriver != NULL);
  assert(getMoveSizeCallback_ != NULL);

  PythonLock lock;

  PythonObject args(lock, PyTuple_New(1));
  PyTuple_SetItem(args.GetPyObject(), 0, reinterpret_cast<PyObject*>(moveDriver));
  Py_INCREF(moveDriver);  // because PyTuple_SetItem steals a reference and we need to keep the object alive

  PythonObject result(lock, PyObject_CallObject(getMoveSizeCallback_, args.GetPyObject()));

  OrthancPluginErrorCode code = lock.CheckCallbackSuccess("Python C-MOVE SCP callback (GetMoveSize)");
  if (code != OrthancPluginErrorCode_Success)
  {
    throw OrthancPlugins::PluginException(code);
  }

  if (!PyLong_Check(result.GetPyObject()))
  {
    throw OrthancPlugins::PluginException(OrthancPluginErrorCode_BadParameterType);
  }

  return static_cast<uint32_t>(PyLong_AsLong(result.GetPyObject()));
}


OrthancPluginErrorCode ApplyMove2(void *moveDriver)
{
  assert(moveDriver != NULL);
  assert(applyMoveCallback_ != NULL);

  PythonLock lock;

  PythonObject args(lock, PyTuple_New(1));
  PyTuple_SetItem(args.GetPyObject(), 0, reinterpret_cast<PyObject*>(moveDriver));
  Py_INCREF(moveDriver);  // because PyTuple_SetItem steals a reference and we need to keep the object alive

  PythonObject result(lock, PyObject_CallObject(applyMoveCallback_, args.GetPyObject()));

  OrthancPluginErrorCode code = lock.CheckCallbackSuccess("Python C-MOVE SCP callback (Apply)");
  return code;
}

   
void FreeMove2(void *moveDriver)
{
  assert(moveDriver != NULL);

  PythonLock lock;

  PythonObject args(lock, PyTuple_New(1));
  PyTuple_SetItem(args.GetPyObject(), 0, reinterpret_cast<PyObject*>(moveDriver));
  Py_INCREF(moveDriver);  // because PyTuple_SetItem steals a reference and we need to keep the object alive

  assert(freeMoveCallback_ != NULL);
  PythonObject result(lock, PyObject_CallObject(freeMoveCallback_, args.GetPyObject()));

  lock.CheckCallbackSuccess("Python C-MOVE SCP callback (Free)");

  Py_DECREF(moveDriver); // remove the initial reference -> this will delete the Python Object when we exit this function
}


OrthancPluginErrorCode WorklistCallback(OrthancPluginWorklistAnswers *answers,
                                        const OrthancPluginWorklistQuery *query,
                                        const char *issuerAet,
                                        const char *calledAet)
{
  try
  {
    PythonLock lock;

    PyObject *pAnswers, *pQuery;
    
    {
      PythonObject args(lock, PyTuple_New(2));
      PyTuple_SetItem(args.GetPyObject(), 0, PyLong_FromSsize_t((intptr_t) answers));
      PyTuple_SetItem(args.GetPyObject(), 1, PyBool_FromLong(true /* borrowed, don't destruct */));
      pAnswers = PyObject_CallObject((PyObject *) GetOrthancPluginWorklistAnswersType(), args.GetPyObject());
    }
    
    {
      PythonObject args(lock, PyTuple_New(2));
      PyTuple_SetItem(args.GetPyObject(), 0, PyLong_FromSsize_t((intptr_t) query));
      PyTuple_SetItem(args.GetPyObject(), 1, PyBool_FromLong(true /* borrowed, don't destruct */));
      pQuery = PyObject_CallObject((PyObject *) GetOrthancPluginWorklistQueryType(), args.GetPyObject());
    }
    
    PythonString pIssuerAet(lock, issuerAet);
    PythonString pCalledAet(lock, calledAet);

    {
      PythonObject args(lock, PyTuple_New(4));
      PyTuple_SetItem(args.GetPyObject(), 0, pAnswers);
      PyTuple_SetItem(args.GetPyObject(), 1, pQuery);
      PyTuple_SetItem(args.GetPyObject(), 2, pIssuerAet.Release());
      PyTuple_SetItem(args.GetPyObject(), 3, pCalledAet.Release());

      assert(worklistScpCallback_ != NULL);
      PythonObject result(lock, PyObject_CallObject(worklistScpCallback_, args.GetPyObject()));
    }

    return lock.CheckCallbackSuccess("Python C-FIND SCP for worklist callback");
  }
  catch (OrthancPlugins::PluginException& e)
  {
    return e.GetErrorCode();
  }
}

   
PyObject* RegisterFindCallback(PyObject* module, PyObject* args)
{
  // The GIL is locked at this point (no need to create "PythonLock")

  class Registration : public ICallbackRegistration
  {
  public:
    virtual void Register() ORTHANC_OVERRIDE
    {
      OrthancPluginRegisterFindCallback(OrthancPlugins::GetGlobalContext(), FindCallback);
    }
  };

  Registration registration;
  return ICallbackRegistration::Apply(
    registration, args, findScpCallback_, "Python C-FIND SCP callback");
}


PyObject* RegisterMoveCallback(PyObject* module, PyObject* args)
{
  // The GIL is locked at this point (no need to create "PythonLock")

  class Registration : public ICallbackRegistration
  {
  public:
    virtual void Register() ORTHANC_OVERRIDE
    {
      OrthancPluginRegisterMoveCallback(
        OrthancPlugins::GetGlobalContext(), CreateMoveCallback, GetMoveSize, ApplyMove, FreeMove);
    }
  };

  Registration registration;
  return ICallbackRegistration::Apply(
    registration, args, moveScpCallback_, "Python C-MOVE SCP callback");
}


PyObject* RegisterMoveCallback2(PyObject* module, PyObject* args)
{
  // The GIL is locked at this point (no need to create "PythonLock")

  class Registration : public ICallbackRegistration
  {
  public:
    virtual void Register() ORTHANC_OVERRIDE
    {
      OrthancPluginRegisterMoveCallback(
        OrthancPlugins::GetGlobalContext(), CreateMoveCallback2, GetMoveSize2, ApplyMove2, FreeMove2);
    }
  };

  Registration registration;
  return ICallbackRegistration::Apply4(
    registration, args, createMoveScpDriverCallback_, getMoveSizeCallback_, applyMoveCallback_, freeMoveCallback_, "Python C-MOVE SCP callback (2)");
}

PyObject* RegisterWorklistCallback(PyObject* module, PyObject* args)
{
  // The GIL is locked at this point (no need to create "PythonLock")

  class Registration : public ICallbackRegistration
  {
  public:
    virtual void Register() ORTHANC_OVERRIDE
    {
      OrthancPluginRegisterWorklistCallback(OrthancPlugins::GetGlobalContext(), WorklistCallback);
    }
  };

  Registration registration;
  return ICallbackRegistration::Apply(
    registration, args, worklistScpCallback_, "Python C-FIND SCP for worklist callback");
}


void FinalizeDicomScpCallbacks()
{
  ICallbackRegistration::Unregister(findScpCallback_);
  ICallbackRegistration::Unregister(moveScpCallback_);
  ICallbackRegistration::Unregister(worklistScpCallback_);

  ICallbackRegistration::Unregister(createMoveScpDriverCallback_);
  ICallbackRegistration::Unregister(getMoveSizeCallback_);
  ICallbackRegistration::Unregister(applyMoveCallback_);
  ICallbackRegistration::Unregister(freeMoveCallback_);
}
