#include <limits.h>
#include <stdint.h>
#include <stdlib.h>

const double CONSTANT_PI  = 3.14159265358979323846;
const double CONSTANT_TAU = 6.283185307179586476925;
const double CONSTANT_HALFPI = 3.14159265358979323846 / 2.0;
const double CONSTANT_LIGHTSPEED = 299792458.0;  // [m/s]

const double CONSTANT_DEG2RAD = 3.14159265358979323846 / 180.0;

// const double ROK_CT_TWOPI = 3.14159265358979323846 * 2.0;
// const double ROK_CT_QUARTERPI = 3.14159265358979323846 / 4.0;
// const double ROK_CT_RAD2DEG = 180.0 / 3.14159265358979323846;
// const double ROK_CT_RAD2SEMI = 1.0 / 3.14159265358979323846;
// const double ROK_CT_SEMI2RAD = 3.14159265358979323846;
// const double ROK_CT_EARTHGM = 3.986004418e14;  // [m^3/s^2]
// const double ROK_CT_EARTHGM_GPS = 3.986005e+14;  // [m^3/s^2]
// const double ROK_CT_EARTHGM_GLO = 3.9860044e+14;  // [m^3/s^2]
// const double ROK_CT_EARTHROTATION = 7.2921151467e-5;  // [rad/s]
// const double ROK_CT_EARTHROTATION_GLO = 7.2921150e-5;  // [rad/s]
// const double ROK_CT_EARTH_F = -4.442807633e-10;     // [s/sqrt(m)],  GPS ICD-GPS-200H, page 96
// const double ROK_CT_WGS84_A = 6378137.0;  // [m]
// const double ROK_CT_WGS84_E = 8.1819190842622e-2;
// const double ROK_CT_WGS84_F = 1.0 / 298.257223563;
// const double ROK_CT_EARTH_J2 = 1.0826257e-3;
// const double ROK_CT_NS2M = 1.0e-9 * 299792458.0;
// const double ROK_CT_M2NS = 1.0 / 299792458.0 / 1.0e-9;
// const double ROK_CT_WEEK2SECONDS = 604800.0;
// const double ROK_CT_DAY2SECONDS = 86400.0;
// const double ROK_CT_GRAVITY = 9.80665;  // m/s^2
// const uint16_t ROK_CT_WEEK_GALT_GPST = 1024;
// const uint16_t ROK_CT_WEEK_BDST_GPST = 1356;
// const size_t ROK_CT_SIZE_3D = 3 * sizeof(double);
// const double  ROK_CT_KNOTS_TO_MPS = 0.514444444444444444;
// const char* ROK_CT_DEF_RXNAME = "UNKN";
