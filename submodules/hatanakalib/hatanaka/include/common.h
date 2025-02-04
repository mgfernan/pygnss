#ifndef HATANAKA_INCLUDE_COMMON_H_
#define HATANAKA_INCLUDE_COMMON_H_

#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>

#define EXIT_WARNING 2


#define MAXTYPE   100         /* Maximum number of data types   */
#define MAXCLM   2048         /* Maximum columns in one line   (>MAXTYPE*19+3)  */
#define MAX_BUFF_SIZE 204800  /* Maximum size of output buffer (>MAXSAT*(MAXTYPE*19+4)+60 */
#define MAXSAT    100         /* Maximum number of satellites observed at one epoch */

static const size_t C1 = sizeof("");               /* size of one character */
static const size_t C2 = sizeof(" ");              /* size of 2-character string */
static const size_t C3 = sizeof("  ");             /* size of 3-character string */

#define CRINEX_VERS "CRINEX VERS   / TYPE"
#define RINEX_VERSION "RINEX VERSION / TYPE"
#define TYPES_OF_OBSERV "# / TYPES OF OBSERV"
#define SYS_OBS_TYPES "SYS / # / OBS TYPES"
#define END_OF_HEADER "END OF HEADER"


/** \brief Rinex format parameters */
static const struct rinex_params {
    char ep_top_from;
    char ep_top_to;
    uint8_t event_pos;  // dlone p_event
    uint8_t nsat_pos;  // line p_sat
    uint8_t satlst_pos;  // line p_satlst
    uint8_t shift_clk;
    uint8_t offset;
} RINEX_PARAMS[] = {
    { '&', ' ', 28, 29, 32, 1, 3 },
    { '>', '>', 31, 32, 41, 4, 6 }
};

bool is_header_line_of_type(const char* line, const char* header_line_type);

#endif  // HATANAKA_INCLUDE_COMMON_H_
