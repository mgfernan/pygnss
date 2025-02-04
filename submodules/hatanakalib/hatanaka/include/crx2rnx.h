#ifndef HATANAKA_INCLUDE_CRX2RNX_H_
#define HATANAKA_INCLUDE_CRX2RNX_H_
#include <limits.h>
#include <stdint.h>
#include <stdbool.h>
#include <time.h>

#include "common.h"

#define MAX_DIFF_ORDER 5      /* Maximum order of difference to be dealt with */

#define CHOP_LF(q,p) p = strchr(q,'\n'); if(p != NULL){if( *(p-1) == '\r' && p>q )p--;*p = '\0';}
#define CHOP_BLANK(q,p) p = strchr(q,'\0');while(*--p == ' ' && p>q);*++p = '\0'

#define CRX2RNX_ERROR_UNSUPPORTED_FORMAT -2
#define CRX2RNX_ERROR_TOO_MANY_OBS_TYPES -3

/* define data structure for fields of clock offset and observation records */
typedef struct clock_format{
    long u[MAX_DIFF_ORDER+1];      /* upper X digits for each difference order */
    long l[MAX_DIFF_ORDER+1];      /* lower 8 digits */
} clock_format;

typedef struct data_format{
    long u[MAX_DIFF_ORDER+1];      /* upper X digits for each difference order */
    long l[MAX_DIFF_ORDER+1];      /* lower 5 digits */
    int  order;
    int  arc_order;
} data_format;

struct gnss_meas {
    char satid[4];

    struct timespec gps_time;

    char rinex3_code[4];
    double value;
};

struct crx2rnx_callbacks {

    /** \brief Sends a long message to an external handler */
    int (*on_log_message)(const char* log_message, void* args);
    void* on_log_message_args;

    /** \brief Sends a RINEX raw line to an external handler
     *
     * These are typically header and event block lines
     */
    int (*on_raw_line)(const char* log_message, void* args);
    void* on_raw_line_args;

    /** \brief Callback method to handle decompressed messages */
    int (*on_measurement)(const struct gnss_meas* gnss_meas, void* args);
    void* on_measurement_args;

};

struct crx2rnx;  // forward declaration

/** \brief Initialize an instance of a crx2rnx object
 *
 * \return A valid pointer to an crx2rnx instance or NULL if an error took place
 */
struct crx2rnx* crx2rnx__init(bool skip_strange_options, bool output_overflow, void (*error_exit)(int, char*, long), char* (*getline)(void*, size_t, char* ), void* _getline_args, bool (*is_end_of_input)(void*), void* is_end_of_input_args, struct crx2rnx_callbacks* callbacks);

int crx2rnx__run(struct crx2rnx* self);

#endif  // HATANAKA_INCLUDE_CRX2RNX_H_