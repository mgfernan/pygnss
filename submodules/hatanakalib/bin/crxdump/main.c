/* crxdump

    Program that takes in uncompressed stream of data from standard input
    and generates a dump

    This executable can be used as an example on how to use the hatanaka library
*/
#include <stdbool.h>
#include <stdio.h>

#include "hatanaka/include/common.h"
#include "hatanaka/include/crx2rnx.h"


static char* get_crx_line(void* _args, size_t n_max, char* dst) {

    FILE* input_fh = (FILE*)_args;
    return fgets(dst, n_max, input_fh);

}

static bool is_eof(void* _args) {

    FILE* input_fh = (FILE*)_args;
    return (fgetc(input_fh) == EOF);

}


static int on_line(const char* header_line, void* _user) {

    FILE* fp = (FILE*)_user;

    fprintf(fp, header_line);

    return 0;
}

static int on_measurement(const struct gnss_meas* gnss_meas, void* args) {

    static bool printed_header = false;
    int ret = -1;

    if (gnss_meas == NULL) {
        goto exit;
    }

    if (printed_header == false) {
        fprintf(stdout, "unix_seconds[s],time_fraction[ns],satellite,obs_type,value\n");

        printed_header = true;
    }

    fprintf(stdout, "%ld,%ld,%s,%s,%lf\n", gnss_meas->gps_time.tv_sec, gnss_meas->gps_time.tv_nsec, gnss_meas->satid, gnss_meas->rinex3_code, gnss_meas->value);

    ret = 0;
exit:
    return ret;
}

int main(int argc, char* argv[]) {

    bool input_file = false;
    struct crx2rnx* crx2rnx;
    int ret = -1;

    // Use stdin by default, unless a file is specified
    FILE* fh = stdin;
    if (argc > 1) {
        input_file = true;
        fh = fopen(argv[1], "r");
    }

    int return_code = 1;

    struct crx2rnx_callbacks callbacks = {
        .on_log_message = on_line,
        .on_log_message_args = stderr,

        .on_measurement = on_measurement,
        .on_measurement_args = stderr
    };

    crx2rnx = crx2rnx__init(false, false, NULL, get_crx_line, (void*)fh, is_eof, (void*)fh, &callbacks);

    ret = crx2rnx__run(crx2rnx);

    return_code = (ret < 0 ? 1 : 0);

    if ((input_file == true) && (fh != NULL)) {
        fclose(fh);
    }

    return return_code;

}