#ifndef _C_EXT_INCLUDE_HELPERS_H
#define _C_EXT_INCLUDE_HELPERS_H

#include <stdlib.h>

#include <Python.h>

PyObject *convert_to_pylist(const double* array, size_t n);

#endif  // _C_EXT_INCLUDE_HELPERS_H
