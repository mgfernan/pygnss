#include <Python.h>
#include <datetime.h>

#include "hatanaka/include/crx2rnx.h"


static char* get_crx_line(void* _args, size_t n_max, char* dst) {

    FILE* input_fh = (FILE*)_args;
    return fgets(dst, n_max, input_fh);

}

static bool is_eof(void* _args) {

    FILE* input_fh = (FILE*)_args;
    return (fgetc(input_fh) == EOF);

}

static int on_measurement(const struct gnss_meas* gnss_meas, void* _args) {

    static const int N_FIELDS = 5;  // Number of fields for struct gnss_meas

    int ret = -1;
    PyObject* list = (PyObject*)_args;

    if (gnss_meas == NULL) {
        goto exit;
    }

    PyDateTime_IMPORT;

    // Create Python lists for each inner list
    PyObject* row = PyList_New(N_FIELDS);

    double timestamp = (double)gnss_meas->gps_time.tv_sec + (double)gnss_meas->gps_time.tv_nsec / 1e9;
    PyObject* time_tuple = Py_BuildValue("(d)", timestamp);
    PyObject* date_time = PyDateTime_FromTimestamp(time_tuple);

    PyList_SetItem(row, 0, date_time);
    PyList_SetItem(row, 1, PyUnicode_FromStringAndSize(gnss_meas->satid, 3));
    PyList_SetItem(row, 2, PyUnicode_FromStringAndSize(gnss_meas->rinex3_code, 3));
    PyList_SetItem(row, 3, PyFloat_FromDouble(gnss_meas->value));
    PyList_SetItem(row, 4, PyLong_FromUnsignedLong(gnss_meas->lli));

    // Add inner lists to the outer list
    PyList_Append(list, row);
    Py_DECREF(row);  // Decrement the reference count of 'row'

    ret = 0;
exit:
    return ret;
}

PyObject *_read_crx(PyObject* self, PyObject* args, PyObject* kwargs) {

    char *filename = NULL;
    struct crx2rnx* crx2rnx = NULL;
    int ret = -1;
    PyObject* list = PyList_New(0);

    struct crx2rnx_callbacks callbacks = {
        .on_measurement = on_measurement,
        .on_measurement_args = list
    };

    // Parse the filename argument
    if (!PyArg_ParseTuple(args, "s", &filename)) {
        PyErr_SetString(PyExc_TypeError, "Expected a string filename");
        goto end;
    }

    // Open the file
    FILE* fp = fopen(filename, "r");
    if (fp == NULL) {
        PyErr_SetString(PyExc_IOError, "Could not open file");
        goto end;
    }

    crx2rnx = crx2rnx__init(false, false, NULL, get_crx_line, (void*)fp, is_eof, (void*)fp, &callbacks);

    ret = crx2rnx__run(crx2rnx);

    if (ret < 0) {
        PyErr_SetString(PyExc_IOError, "There was an issue processing the Hatanaka file");
        PyList_SetSlice(list, 0, PY_SSIZE_T_MAX, NULL);  // clear the list
    }

    // Clean-up
    fclose(fp);
end:
    return list;

}
