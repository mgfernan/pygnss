/****************************************************************************/
/*     program name : CRX2RNX                                               */
/*                                                                          */
/*     Program to recover the RINEX file from Compact RINEX file            */
/*     Created by Yuki HATANAKA / Geospatial Information Authority of Japan */
/*                                                                          */
/*     ver.                                                                 */
/*     4.0.0       2007-01-31 test version   Y. Hatanaka                    */
/*                  - CRINEX 1/3 for RINEX 2.x/3.x                          */
/*     4.0.1       2007-05-08                Y. Hatanaka                    */
/*                  - elimination of supports for VMS and SUN OS 4.1.x      */
/*                  - output not to the current directory but the same      */
/*                    directory as the input file.                          */
/*                  - the same code for DOS and UNIX                        */
/*     4.0.2       2007-06-07                Y. Hatanaka                    */
/*                  - fixing incompatibility of argument and format         */
/*                    string of printf.                                     */
/*     4.0.3       2007-06-21                Y. Hatanaka                    */
/*                  - fixing a bug on lack of carrying the number           */
/*                    between lower and upper digits                        */
/*     4.0.4       2009-06-31                Y. Hatanaka                    */
/*                  - check null pointer in macro CHOP_LF                   */
/*                  - increase MAXTYPE from 30 to 50                        */
/*                  - correct typos in error messages                       */
/*     4.0.5       2012-07-1x                Y. Hatanaka                    */
/*                  - Fixing a bug in displaying error message(#16)         */
/*                  - minor changes to suppress warning messages            */
/*                    at compilation.                                       */
/*                  - check length of input file name                       */
/*     4.0.6       2014-03-24                Y. Hatanaka                    */
/*                  - Fixing a bug in outputting epoch lines in case there  */
/*                    are skipped epochs when a corrupted Compact RINEX     */
/*                    ver. 3 files are processed with the option "-s".      */
/*                  - "include" statements are moved to the top.            */
/*                  - check and stop with an error if value of data         */
/*                    exceed the range allowed in RINEX format. An hidden   */
/*                    option to keep output in such a case is also added.   */
/*                  - Manipulation of file names in the new file naming     */
/*                    convention (*.rnx/crx) is added.                      */
/*     4.0.7       2016-04-14                Y. Hatanaka                    */
/*                  - increase the following constants                      */
/*                       MAXSAT        90     -> 100                        */
/*                       MAXTYPE       50     -> 100                        */
/*                       MAXCLM        1024   -> 2048                       */
/*                       MAX_BUFF_SIZE 131072 -> 204800                     */
/*     4.0.8       2019-07-12                Y. Hatanaka                    */
/*                  - New option "-d" is added to delete input file after   */
/*                    successful conversion.                                */
/*     4.1.0       2021-12-22                Y. Hatanaka                    */
/*                  - recover RINEX ver. 4 files as well as RINEX ver. 3    */
/*                    files from CRINEX ver.3 files.                        */
/*                 2022-01-06                Y. Hatanaka                    */
/*                  - VERSION is corrected to 4.1.0                         */
/*                                                                          */
/*     Copyright (c) 2007 Geospatial Information Authority of Japan         */
/*                                                                          */
/****************************************************************************/

#include <limits.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

#include "hatanaka/include/crx2rnx.h"
#include "hatanaka/include/common.h"

#define VERSION  "ver.4.1.0"

/**** Exit codes are defined here. ****/
#ifndef EXIT_SUCCESS
#define EXIT_SUCCESS 0
#endif

#ifndef EXIT_FAILURE
#define EXIT_FAILURE 1
#endif

/* define global constants */
#define PROGNAME "CRX2RNX"

int exit_status = EXIT_SUCCESS;
int delete_if_no_error = 0; /* default : not delete */
int n_infile = 0;           /* number of input file (must be 0 or 1) */
char infile[MAXCLM];        /**** name of input file ****/

struct config {
    bool skip_strange_options;
    bool output_overflow;

    FILE* input_fh;

};

static void error_exit(int error_no, char *string, long nl_count){
    if(error_no == 1 ){
        fprintf(stderr,"Usage: %s [file] [-] [-f] [-s] [-d] [-h]\n",string);
        fprintf(stderr,"    stdin and stdout are used if input file name is not given.\n");
        fprintf(stderr,"    -  : output to stdout\n");
        fprintf(stderr,"    -f : force overwrite of output file\n");
        fprintf(stderr,"    -s : skip strange epochs (default:stop with error)\n");
        fprintf(stderr,"           This option may be used for salvaging usable data when middle of\n");
        fprintf(stderr,"           the Compact RINEX file is missing. The data after the missing part,\n");
        fprintf(stderr,"           are, however, useless until the compression operation of all data\n");
        fprintf(stderr,"           are initialized at some epoch. Combination with use of -e option\n");
        fprintf(stderr,"           of RNX2CRX may be effective.\n");
        fprintf(stderr,"           Caution : It is assumed that no change in the list of data types\n");
        fprintf(stderr,"                     happens in the lost part of the data.\n");
        fprintf(stderr,"    -d      : delete the input file if conversion finishes without errors\n");
        fprintf(stderr,"              (i.e. exit code = %d or %d).\n",EXIT_SUCCESS,EXIT_WARNING);
        fprintf(stderr,"              This option does nothing if stdin is used for the input.\n");
        fprintf(stderr,"    -h : display help message\n\n");
        fprintf(stderr,"    exit code = %d (success)\n",EXIT_SUCCESS);
        fprintf(stderr,"              = %d (error)\n",  EXIT_FAILURE);
        fprintf(stderr,"              = %d (warning)\n",EXIT_WARNING);
        fprintf(stderr,"    [version : %s]\n",VERSION);
        exit(EXIT_FAILURE);
    }
    if(error_no == 3 ){
        fprintf(stderr,"ERROR : invalid file name  %s\n",string);
        fprintf(stderr,"The extension of the input file name should be [.??d] or [.crx].\n");
        fprintf(stderr,"To convert the files whose name is not fit to the above conventions,\n");
        fprintf(stderr,"use of this program as a filter is also possible. \n");
        fprintf(stderr,"    for example)  cat file.in | %s - > file.out\n",PROGNAME);
        exit(EXIT_FAILURE);
    }
    if(error_no == 4 ){
        fprintf(stderr,"ERROR : can't open %s\n",string);
        exit(EXIT_FAILURE);
    }
    if(error_no == 5 ){
        fprintf(stderr,"ERROR : The file format is not Compact RINEX or the version of\n");
        fprintf(stderr,"        the format is not valid. This software can deal with\n");
        fprintf(stderr,"        only Compact RINEX format ver.%s.\n",string);
        exit(EXIT_FAILURE);
    }
    if(error_no == 6 ){
        fprintf(stderr,"ERROR at line %ld : exceed maximum number of satellites(%d)\n",nl_count,MAXSAT);
        fprintf(stderr,"      start>%s<end\n",string);
        exit(EXIT_FAILURE);
    }
    if(error_no == 7 ){
        fprintf(stderr,"ERROR at line %ld : exceed maximum order of difference (%d)\n",nl_count,MAX_DIFF_ORDER);
        fprintf(stderr,"      start>%s<end\n",string);
        exit(EXIT_FAILURE);
    }
    if(error_no == 8 ){
        fprintf(stderr,"ERROR : The file seems to be truncated in the middle.\n");
        fprintf(stderr,"        The conversion is interrupted after reading the line %ld :\n",nl_count);
        fprintf(stderr,"      start>%s<end\n",string);
        exit(EXIT_FAILURE);
    }
    if(error_no == 9 ){
        fprintf(stderr,"ERROR at line %ld : The arc should be initialized, but not.\n",nl_count);
        fprintf(stderr,"      start>%s<end\n",string);
        exit(EXIT_FAILURE);
    }
    if(error_no == 11){
        fprintf(stderr,"ERROR at line %ld : New satellite, but data arc is not initialized.\n",nl_count);
        fprintf(stderr,"      start>%s<end\n",string);
        exit(EXIT_FAILURE);
    }
    if(error_no == 12){
        fprintf(stderr,"ERROR at line %ld : The data field in previous epoch is blank, but the arc is not initialized.\n",nl_count);
        fprintf(stderr,"      start>%s<end\n",string);
        exit(EXIT_FAILURE);
    }
    if(error_no == 13){
        fprintf(stderr,"ERROR at line %ld : null character is found in the line or the line is too long (>%d) at line.\n",nl_count,MAXCLM);
        fprintf(stderr,"      start>%s<end\n",string);
        exit(EXIT_FAILURE);
    }
    if(error_no == 14 ){
        fprintf(stderr,"ERROR at line %ld. : Length of file name exceed MAXCLM(%d).\n",nl_count,MAXCLM);
        fprintf(stderr,"     start>%s<end\n",string);
        exit(EXIT_FAILURE);
    }
    if(error_no == 15 ){
        fprintf(stderr,"ERROR : The format version of the original RINEX file is not valid.\n");
        fprintf(stderr,"         This software can deal with only (compressed) RINEX format ver.%s.\n",string);
        exit(EXIT_FAILURE);
    }
    if(error_no == 16 ){
        fprintf(stderr,"ERROR at line %ld. : Number of data types exceed MAXTYPE(%d).\n",nl_count,MAXTYPE);
        fprintf(stderr,"     start>%s<end\n",string);
        exit(EXIT_FAILURE);
    }
    if(error_no == 17 ){
        fprintf(stderr,"ERROR at line %ld. : %s becomes out of range allowed in the RINEX format.\n",nl_count,string);
        exit(EXIT_FAILURE);
    }
    if(error_no == 20 ){
        fprintf(stderr,"ERROR at line %ld. : A GNSS type not defined in the header is found.\n",nl_count);
        fprintf(stderr,"     start>%s<end\n",string);
        exit(EXIT_FAILURE);
    }

}

/* declaration of functions */
static void fileopen(int argc, char *argv[], struct config* config){
    char *p,outfile[MAXCLM],*progname;
    int force = 0, help = 0;
    int nfout = 0;  /*** =0 default output file name ***/
                    /*** =1 standard output          ***/
    FILE *ifp;

    memset(config, 0, sizeof(struct config));

    progname = argv[0];
    argc--;argv++;
    for(;argc>0;argc--,argv++){
        if((*argv)[0] != '-'){
            strncpy(infile,*argv,C1*MAXCLM);
            n_infile++;
        }else if(strcmp(*argv,"-")   == 0){
            nfout = 1;
        }else if(strcmp(*argv,"-f")  == 0){
            force = 1;
        }else if(strcmp(*argv,"-d")  == 0){
            delete_if_no_error = 1;    /* delete the original file if
                                          no error in the conversion */
        }else if(strcmp(*argv,"-s")  == 0){
            config->skip_strange_options  = true;
        }else if(strcmp(*argv,"--output_overflow")  == 0){
            /* output the data without stopping with an error even if  */
            /* digits of an output data exceed the limit of the format */
            /* (a hidden option for checking)                          */
            config->output_overflow = true;
        }else if(strcmp(*argv,"-h")  == 0){
            help = 1;
        }else{
            help = 1;
        }
    }

    if(strlen(infile) == MAXCLM) error_exit(14, infile, 0);
    if(help == 1 || n_infile > 1  || n_infile < 0) error_exit(1, progname, 0);
    if(n_infile == 0) return;  /*** stdin & stdout will be used if input file name is not given ***/

    /***********************/
    /*** open input file ***/
    /***********************/
    p = strrchr(infile,'.');
    if(p == NULL || *(p+4) != '\0'
                 || ( toupper(*(p+3)) != 'D'
                      && strcmp(p+1,"CRX") != 0
                      && strcmp(p+1,"crx") != 0 )
    ) error_exit(3, p, 0);

    if((ifp = fopen(infile,"r")) == NULL) error_exit(4, infile, 0);

    /************************/
    /*** open output file ***/
    /************************/
    if(nfout == 0) {
        strcpy(outfile,infile);
        p = strrchr(outfile,'.');
        if     (*(p+3) == 'd') { *(p+3) = 'o';}
        else if(*(p+3) == 'D') { *(p+3) = 'O';}
        else if( strcmp(p+1,"crx") == 0) { strcpy((p+1),"rnx");}
        else if( strcmp(p+1,"CRX") == 0) { strcpy((p+1),"RNX");}

        if((freopen(outfile,"r",stdout)) != NULL && force == 0){
            fprintf(stderr,"The file %s already exists. Overwrite?(n)",outfile);
            if(getchar() != 'y') exit(EXIT_SUCCESS);
        }
        freopen(outfile,"w",stdout);
    }
    fclose(ifp);
    freopen(infile,"r",stdin);
}

static char* get_crx_line(void* _args, size_t n_max, char* dst) {

    struct config* config = (struct config*)_args;
    return fgets(dst, n_max, config->input_fh);

}

static bool is_eof(void* _args) {

    struct config* config = (struct config*)_args;
    return (fgetc(config->input_fh) == EOF);

}

static int print_to_file(const char* logmessage, void* _args) {

    FILE* fh = (FILE*)_args;
    fprintf(fh, logmessage);
    return 0;
}

int main(int argc, char *argv[]){

    struct config config;
    struct crx2rnx* crx2rnx;
    struct crx2rnx_callbacks crx2rnx_callbacks = {
        .on_log_message = print_to_file,
        .on_log_message_args = stderr,

        .on_raw_line = print_to_file,
        .on_raw_line_args = stdout,
    };
    int ret;

    fileopen(argc,argv, &config);
    config.input_fh = stdin;

    crx2rnx = crx2rnx__init(config.skip_strange_options, config.output_overflow, error_exit, get_crx_line, (void*)&config, is_eof, (void*)&config, &crx2rnx_callbacks);

    ret = crx2rnx__run(crx2rnx);

    exit_status = (ret < 0 ? 2 : 0);

    if (delete_if_no_error && exit_status != 2 && n_infile == 1) {
        remove(infile);
    }

    return(exit_status);
}
/*---------------------------------------------------------------------*/
