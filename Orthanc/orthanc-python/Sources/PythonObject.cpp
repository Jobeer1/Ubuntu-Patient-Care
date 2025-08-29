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


#include "PythonObject.h"

#include "../Resources/Orthanc/Plugins/OrthancPluginCppWrapper.h"
#include "PythonLock.h"


PythonObject::PythonObject(PythonLock& lock,
                           PyObject *object,
                           bool borrowed) :
  lock_(lock),
  object_(object),
  borrowed_(borrowed)
{
}


PythonObject::~PythonObject()
{
  if (!borrowed_ &&
      object_ != NULL)
  {
    Py_DECREF(object_);
  }
}


PyObject* PythonObject::GetPyObject() const
{
  if (object_ == NULL)
  {
    // "IsValid()" should have been called
    ORTHANC_PLUGINS_THROW_EXCEPTION(BadSequenceOfCalls);
  }
  else
  {
    return object_;
  }
}


PythonObject* PythonObject::GetAttribute(const std::string& name)
{
  return new PythonObject(lock_, PyObject_GetAttrString(GetPyObject(), name.c_str()));
}


bool PythonObject::ToUtf8String(std::string& target,
                                PyObject* value)
{
  if (value == NULL)
  {
    ORTHANC_PLUGINS_THROW_EXCEPTION(NullPointer);
  }
  else if (PyUnicode_Check(value))
  {
    PythonObject encoded(lock_, PyUnicode_AsEncodedString(value, "utf-8", "replace"));
    if (encoded.IsValid())
    {
      target = PyBytes_AS_STRING(encoded.GetPyObject());
      return true;
    }
    else
    {
      target.clear();
      return false;
    }
  }
#if PY_MAJOR_VERSION == 2
  else if (PyString_Check(value))
  {
    target = PyString_AS_STRING(value);
    return true;
  }
#endif
  else
  {
    target.clear();
    return false;
  }
}


void PythonObject::Format(std::ostream& os)
{
  std::string s;
  if (object_ == NULL)
  {
    os << "Can't format a NULL Python object" << std::endl;
  }
  else if (ToUtf8String(s))
  {
    os << s;
  }
  else
  {
    os << "Can't format this Python object" << std::endl;
  }
}


PyObject* PythonObject::Release()
{
  if (!borrowed_ &&
      object_ != NULL)
  {
    PyObject* value = object_;
    object_ = NULL;
    return value;
  }
  else
  {
    ORTHANC_PLUGINS_LOG_ERROR("Cannot release a NULL or borrowed reference");
    ORTHANC_PLUGINS_THROW_EXCEPTION(InternalError);
  }
}


void PythonObject::ConvertToJson(Json::Value& target,
                                 PyObject* source)
{
  // WARNING: The order *is* important!
  if (source == Py_None)
  {
    target = Json::nullValue;
  }
  else if (PyBool_Check(source))
  {
    target = (PyObject_IsTrue(source) ? true : false);
  }
  else if (PyLong_Check(source))
  {
    target = static_cast<int32_t>(PyLong_AsLong(source));
  }
  else if (PyFloat_Check(source))
  {
    target = PyFloat_AsDouble(source);
  }
  else if (PyNumber_Check(source))
  {
    PythonObject asLong(lock_, PyNumber_Long(source));
    if (PyLong_Check(asLong.GetPyObject()))
    {
      target = static_cast<int32_t>(PyLong_AsLong(asLong.GetPyObject()));
    }
    else
    {
      ORTHANC_PLUGINS_THROW_EXCEPTION(InternalError);
    }
  }
  else if (PyUnicode_Check(source))
  {
    std::string s;
    if (ToUtf8String(s, source))
    {
      target = s;
    }
    else
    {
      ORTHANC_PLUGINS_THROW_EXCEPTION(NotImplemented);
    }
  }
#if PY_MAJOR_VERSION == 2
  else if (PyString_Check(source))
  {
    target = PyString_AS_STRING(source);
  }
#endif
  else if (PySequence_Check(source))  // tuples or lists
  {
    Py_ssize_t size = PySequence_Size(source);

    if (size < 0)
    {
      ORTHANC_PLUGINS_THROW_EXCEPTION(InternalError);      
    }

    target = Json::arrayValue;
    for (Py_ssize_t i = 0; i < size; i++)
    {
      Json::Value item;
      ConvertToJson(item, PySequence_GetItem(source, i));
      target.append(item);
    }
  }
  else if (PyMapping_Check(source))  // dictionaries
  {
    PythonObject items(lock_, PyMapping_Items(source));

    Py_ssize_t size = PySequence_Size(items.GetPyObject());

    if (size < 0)
    {
      ORTHANC_PLUGINS_THROW_EXCEPTION(InternalError);      
    }

    for (Py_ssize_t i = 0; i < size; i++)
    {
      PyObject* pair = PySequence_GetItem(items.GetPyObject(), i);

      std::string key;
      Json::Value value;
      if (pair != NULL &&
          ToUtf8String(key, PySequence_GetItem(pair, 0)))
      {
        ConvertToJson(value, PySequence_GetItem(pair, 1));
        target[key] = value;
      }
      else
      {
        ORTHANC_PLUGINS_THROW_EXCEPTION(InternalError);      
      }
    }
  }
  else
  {
    ORTHANC_PLUGINS_THROW_EXCEPTION(NotImplemented);
  }
}
