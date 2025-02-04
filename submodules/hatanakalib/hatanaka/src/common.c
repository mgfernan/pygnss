#include <stdbool.h>
#include <string.h>

#include "../include/common.h"

bool is_header_line_of_type(const char* line, const char* header_line_type) {

    bool res = false;

    if ((line != NULL) && (header_line_type != NULL)) {
        res = (strncmp(&line[60], header_line_type, strlen(header_line_type)) == 0);
    }

    return res;

}
