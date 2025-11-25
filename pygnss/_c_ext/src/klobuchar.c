#include <Python.h>
#include <math.h>
#include <string.h>

#include "constants.h"

#include "klobuchar.h"


/** \brief Structure to hold the 8-parameters for the Klobuchar model */
struct klobuchar {
    double alphas[4];
    double betas[4];
};


typedef struct {
    PyObject_HEAD
    struct klobuchar klobuchar;
} Klobuchar;


static double compute_klobuchar(const double tow,
                         const double longitude_rad, const double latitude_rad,
                         const double el_rad, const double az_rad,
                         const struct klobuchar* klobuchar) {

    double el_semicircles;
    double psi;
    double phi_I;
    double lambda_I;
    double phi_m;
    double t;
    double phi_m_n[4];
    double amplitude_I;
    double period_I;
    double phase_I;
    double slant_factor;
    double iono_delay_l1;

    // Convert elevation from radians to semicircles
    el_semicircles = el_rad / CONSTANT_PI;

    // Earth-centered angle (psi)
    psi = 0.0137 / (el_semicircles + 0.11) - 0.022;

    // Latitude of the ionosphere pierce point (semicircles)
    phi_I = (latitude_rad / CONSTANT_PI) + (psi * cos(az_rad));
    if (phi_I > 0.416) {
        phi_I = 0.416;
    } else if (phi_I < -0.416) {
        phi_I = -0.416;
    } else {
    }

    // Longitude of the ionosphere pierce point (semicircles)
    lambda_I = (longitude_rad / CONSTANT_PI) + (psi * sin(az_rad) / cos(phi_I * CONSTANT_PI));

    // Geomagnetic latitude_rad of the ionosphere pierce point
    phi_m = phi_I + (0.064 * cos((lambda_I - 1.617) * CONSTANT_PI));

    // Local time at the IPP
    t = fmod((43200.0 * lambda_I) + tow, 86400);
    if (t < 0.0) {
        t += 86400.0;
    } else if (t >= 86400.0) {
        t -= 86400.0;
    } else {
    }

    // Compute powers of phi_m for later usage
    for (int i = 0; i < 4; i++) {
        phi_m_n[i] = pow(phi_m, (double)i);
    }

    // Compute the *amplitude* of the ionospheric delay (seconds)
    // Alpha coefficients are being used for this amount
    //
    // amplitude_I = \sum_{n=0}^3 \alpha_n \cdot \phi_m^n
    //
    amplitude_I = 0.0;
    for (int i = 0; i < 4; i++) {
        amplitude_I += klobuchar->alphas[i] * phi_m_n[i];
    }
    if (amplitude_I < 0.0) {
        amplitude_I = 0.0;
    }

    // Compute the *period* of the ionospheric delay (seconds)
    //
    // period_I = \sum_{n=0}^3 \beta_n \cdot \phi_m^n
    //
    period_I = 0.0;
    for (int i = 0; i < 4; i++) {
        period_I += klobuchar->betas[i] * phi_m_n[i];
    }
    if (period_I < 72000.0) {
        period_I = 72000.0;
    }

    // Compute the phase of the ionospheric delay (radians)
    phase_I = CONSTANT_TAU * (t - 50400.0) / period_I;

    // Compute the slant factor (elevation in semicircles)
    slant_factor = 1.0 + (16.0 * pow(0.53 - el_semicircles, 3));

    // Compute the ionospheric time delay (L1)
    iono_delay_l1 = 5.0e-9;
    if (fabs(phase_I) <= CONSTANT_HALFPI) {
        iono_delay_l1 = iono_delay_l1
            + (amplitude_I * (1.0 - (pow(phase_I, 2) / 2.0) + (pow(phase_I, 4) / 24.0)));
    }
    iono_delay_l1 = iono_delay_l1 * slant_factor;

    return iono_delay_l1 * CONSTANT_LIGHTSPEED;
}

double compute_klobuchar_stec(const double tow,
    const double longitude_rad, const double latitude_rad,
    const double elevation_rad, const double azimuth_rad,
    const struct klobuchar* klobuchar) {

    static const double INV_ALPHA_1_TECU = 154.0 * 154.0 * 10.23e6 * 10.23e6 / 40.3 * 1.0e-16; /* f_1^2 / 40.3 (in TECU) */

    double delay = compute_klobuchar(tow, longitude_rad, latitude_rad, elevation_rad, azimuth_rad, klobuchar);
    double stec_tecu = delay * INV_ALPHA_1_TECU;

    return stec_tecu;

}


static PyObject* new(PyTypeObject *type, PyObject *args, PyObject *kwds) {

    Klobuchar *self;
    self = (Klobuchar *) type->tp_alloc(type, 0);
    if (self != NULL) {
        memset(&self->klobuchar, 0, sizeof(struct klobuchar));
    }
    return (PyObject *) self;
}

static void dealloc(Klobuchar *self) {

    Py_TYPE(self)->tp_free((PyObject *) self);
}

static int init(Klobuchar *self, PyObject *args, PyObject *kwds) {

    static char *kwlist[] = {"alpha0", "alpha1", "alpha2", "alpha3",
                             "beta0", "beta1", "beta2", "beta3", NULL};

    struct klobuchar* klob = &self->klobuchar;
    if (!PyArg_ParseTupleAndKeywords(args, kwds, "dddddddd", kwlist,
                                     &klob->alphas[0], &klob->alphas[1], &klob->alphas[2], &klob->alphas[3],
                                     &klob->betas[0], &klob->betas[1], &klob->betas[2], &klob->betas[3]))
        return -1;
    return 0;
}

static PyObject* Klobuchar_ionospheric_delay(Klobuchar *self, PyObject *args) {

    double tow, lat_deg, lon_deg, az_deg, el_deg;
    if (!PyArg_ParseTuple(args, "ddddd", &tow, &lat_deg, &lon_deg, &az_deg, &el_deg))
        return NULL;

    double lat_rad = lat_deg * CONSTANT_DEG2RAD;
    double lon_rad = lon_deg * CONSTANT_DEG2RAD;
    double az_rad = az_deg * CONSTANT_DEG2RAD;
    double el_rad = el_deg * CONSTANT_DEG2RAD;
    double delay = compute_klobuchar(tow, lon_rad, lat_rad, el_rad, az_rad, &self->klobuchar);

    return PyFloat_FromDouble(delay);
}

static PyObject* Klobuchar_compute_stec(Klobuchar *self, PyObject *args) {

    double tow, lat_deg, lon_deg, az_deg, el_deg;
    if (!PyArg_ParseTuple(args, "ddddd", &tow, &lat_deg, &lon_deg, &az_deg, &el_deg))
        return NULL;

    double lat_rad = lat_deg * CONSTANT_DEG2RAD;
    double lon_rad = lon_deg * CONSTANT_DEG2RAD;
    double az_rad = az_deg * CONSTANT_DEG2RAD;
    double el_rad = el_deg * CONSTANT_DEG2RAD;
    double stec_tecu = compute_klobuchar_stec(tow, lon_rad, lat_rad, el_rad, az_rad, &self->klobuchar);

    return PyFloat_FromDouble(stec_tecu);
}


static PyObject* Klobuchar_compute_map(Klobuchar *self, PyObject *args, PyObject* kwargs) {

    static char* arguments[] = {"" /*tow*/, "n_lats", "n_lons", NULL};

    double tow;
    int n_lats = 72;
    int n_lons = 72;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "d|ii", arguments, &tow, &n_lats, &n_lons))
        return NULL;

    double* map = calloc(n_lats * n_lons, sizeof(double));
    if (map == NULL)
        return NULL;

    /* compute the map */
    double dlat = 180.0 / n_lats;
    double dlon = 360.0 / n_lons;

    for (int i = 0; i < n_lats; i ++) {
        double lat_rad = (+90 - (i + 0.5) * dlat) * CONSTANT_DEG2RAD;
        for (int j = 0; j < n_lons; j++) {
            double lon_rad = (-180 + (j + 0.5) * dlon) * CONSTANT_DEG2RAD;

            map[i * n_lons + j] = compute_klobuchar_stec(tow, lon_rad, lat_rad, CONSTANT_HALFPI, 0, &self->klobuchar);
        }
    }

    /* store the result into a list of lists*/
    PyObject* matrix = PyList_New(n_lats);

    // Fill the Python list of lists with sublists
    for (int i = 0; i < n_lats; ++i) {
        PyObject* sublist = PyList_New(n_lons);
        for (int j = 0; j < n_lons; ++j) {
            double value = map[i * n_lons + j];
            PyObject* float_obj = PyFloat_FromDouble(value);
            PyList_SET_ITEM(sublist, j, float_obj);
        }
        PyList_SET_ITEM(matrix, i, sublist);
    }

    free(map);

    return matrix;
}


static PyMethodDef methods[] = {
{"compute_slant_delay", (PyCFunction) Klobuchar_ionospheric_delay, METH_VARARGS,
    "Compute ionospheric delay.\n\n"
    ":param tow: Time of the Week (in seconds)\n"
    ":param lat_deg: Latitude (in degrees)\n"
    ":param lon_deg: Longitude (in degrees)\n"
    ":param az_deg: Azimuth (in degrees)\n"
    ":param el_deg: Elevation (in degrees)\n\n"
    ":return: Delay in meters for the GPS L1 frequency\n\n"
    },
{"compute_stec", (PyCFunction) Klobuchar_compute_stec, METH_VARARGS,
    "Compute Slant Total Electron Content\n\n"
    ":param tow: Time of the Week (in seconds)\n"
    ":param lat_deg: Latitude (in degrees)\n"
    ":param lon_deg: Longitude (in degrees)\n"
    ":param az_deg: Azimuth (in degrees)\n"
    ":param el_deg: Elevation (in degrees)\n\n"
    ":return: Slant Total Electron Content (in TEC Units)\n\n"},
{"compute_vtec_map", (PyCFunction) Klobuchar_compute_map, METH_VARARGS | METH_KEYWORDS,
    "Compute a VTEC global ionospheric map\n\n"
    ":param tow: Time of the Week (in seconds)\n"
    ":param n_lats: Number of latitude bins (defaults to 72)\n"
    ":param n_lons: Number of longitude bins (defaults to 72)\n\n"
    ":return: Array of arrays containing VTEC values (n_lats rows * n_lons columns) (TECU)\n\n"},
{NULL} /* Sentinel */
};

static PyTypeObject Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "pyrcore.Klobuchar", /* tp_name */
    sizeof(Klobuchar), /* tp_basicsize */
    0, /* tp_itemsize */
    (destructor) dealloc, /* tp_dealloc */
    0, /* tp_print */
    0, /* tp_getattr */
    0, /* tp_setattr */
    0, /* tp_reserved */
    0, /* tp_repr */
    0, /* tp_as_number */
    0, /* tp_as_sequence */
    0, /* tp_as_mapping */
    0, /* tp_hash */
    0, /* tp_call */
    0, /* tp_str */
    0, /* tp_getattro */
    0, /* tp_setattro */
    0, /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT, /* tp_flags */
    "Klobuchar class\n\n"
    ">>> from pyrcore import Klobuchar\n"
    ">>> alphas = [.3820e-07, .1490e-07,  -.1790e-06, .0000e-00]\n"
    ">>> betas = [.1430e+06, .0000e+00,  -.3280e+06, .1130e+06]\n"
    ">>> klobuchar = Klobuchar(*alphas, *betas)\n"
    ">>> delay_L1 = klobuchar.delay(593100, 40, 260, 210, 20)", /* tp_doc */
    0, /* tp_traverse */
    0, /* tp_clear */
    0, /* tp_richcompare */
    0, /* tp_weaklistoffset */
    0, /* tp_iter */
    0, /* tp_iternext */
    methods, /* tp_methods */
    0, /* tp_members */
    0, /* tp_getset */
    0, /* tp_base */
    0, /* tp_dict */
    0, /* tp_descr_get */
    0, /* tp_descr_set */
    0, /* tp_dictoffset */
    (initproc)init,/* tp_init */
    0,                         /* tp_alloc */
    new,                 /* tp_new */
};

PyTypeObject* KlobucharType = &Type;
