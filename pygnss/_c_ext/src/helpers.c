#include <stdlib.h>
#include <Python.h>

#include "../include/helpers.h"

PyObject *convert_to_pylist(const double* array, size_t n) {

    Py_ssize_t len = n;
    PyObject* list = PyList_New(len);

    for (Py_ssize_t i = 0; i < len; i++) {
        PyObject* value = PyFloat_FromDouble(array[i]);
        PyList_SetItem(list, i, value);
    }

    return list;
}
