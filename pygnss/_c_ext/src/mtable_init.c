#include <Python.h>

#include "hatanaka.h"

static PyMethodDef module_methods[] = {
    { "_read_crx",         (PyCFunction)_read_crx, METH_VARARGS | METH_KEYWORDS,
      "Read a Hatanaka (gzip uncompressed) file and generate a numpy array\n\n"
      ":param filename: Name of the Hatanaka file to process\n"
      ":return: Numpy array\n\n"},
      {NULL, NULL, 0, NULL},  /* Sentinel */
};

/*----------------------------------------------------------------------------*/

static struct PyModuleDef module = {
    PyModuleDef_HEAD_INIT,
    "_c_ext", /* name of the module*/
    "C extension methods",
    -1,  // size of per-interpreter state of the module,
         // or -1 if the module keeps state in global variables.
    module_methods
};


PyMODINIT_FUNC PyInit__c_ext(void) {

    PyObject* m = NULL;

//     // Classes
//     if (PyType_Ready(HatanakaReaderType) < 0) {
//         goto end;
//     }

    m = PyModule_Create(&module);
    if (m == NULL) {
        goto end;
    }

//     Py_INCREF(HatanakaReaderType);
//     PyModule_AddObject(m, "HatanakaReader", (PyObject*)HatanakaReaderType);

end:
    return m;
}
