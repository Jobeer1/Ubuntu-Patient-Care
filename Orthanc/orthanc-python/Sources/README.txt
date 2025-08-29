
Note about the "memory leaks" in the Python allocators
======================================================

This concerns functions "PyTuple_SetItem()" and
"PyDict_SetItemString()", whose documentation is the following:

>>>>>
* int PyTuple_SetItem(PyObject *p, Py_ssize_t pos, PyObject *o)

  Insert a reference to object o at position pos of the tuple pointed
  to by p. Return 0 on success. If pos is out of bounds, return -1 and
  set an IndexError exception.

  Note: This function "steals" a reference to o and discards a
  reference to an item already in the tuple at the affected position.

* int PyDict_SetItemString(PyObject *p, const char *key, PyObject *val)

  Insert val into the dictionary p using key as a key. key should be a
  const char* UTF-8 encoded bytes string. The key object is created
  using PyUnicode_FromString(key). Return 0 on success or -1 on
  failure. This function does not steal a reference to val.
<<<<<


As can be seen:

* PyTuple_SetItem() steals the reference.

* PyDict_SetItemString() does *not* steal the reference.


Consequently, when passing an object created by the Orthanc Python
plugin:

* PyTuple_SetItem() must use "PythonObject::Release()".

* PyDict_SetItemString() must use "PythonObject::GetPyObject()".


In releases <= 4.0 of the Python plugin, PyDict_SetItemString() was
using "PythonObject::Release()" instead of
"PythonObject::GetPyObject()", which resulted in memory leaks.
