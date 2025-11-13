#include <ctype.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>

#include "../include/hatanaka/crx2rnx.h"
#include "../include/hatanaka/common.h"

// DEFINES

struct crx2rnx {
    int clk_order;
    int clk_arc_order;
    clock_format clk0;
    clock_format clk1;

    int ntype_gnss[UCHAR_MAX];

    /** \brief Rinex 3 codes for each constellation */
    char types_gnss[UCHAR_MAX][MAXTYPE][4];

    int rinex_version;
    int crinex_version;

    const struct rinex_params* rinex_params;

    int nsat;
    int ntype;  // number of types
    int ntype_record[MAXSAT];
    char current_obstypes_constellation;

    data_format dy1[MAXSAT][MAXTYPE];
    data_format dy0[MAXSAT][MAXTYPE];
    char obscode[UCHAR_MAX][MAXTYPE][4];  // Rinex codes for each constellation
    char flag[MAXSAT][MAXTYPE*2+1];
    char flag1[MAXSAT][MAXTYPE*2+1];

    long nl_count;

    bool skip_strange_options;

    /** \brief Temporary buffer to store a single line */
    char line[MAXCLM];

    struct gnss_meas gnss_meas;

    char msg[2 * MAXCLM];

    char out_buff[MAX_BUFF_SIZE];
    char* p_buff;  /** \todo Move to a RINEX writer class */

    /* method to handle error exits*/
    void (*error_exit)(int, char*, long);

    /** \brief Method used by the class to feed the processor with raw lines
     *
     * Typically, this method can be a wrapper around the `fgets` method
     *
     * \param _input_args Input arguments (e.g. custom `struct`, input file pointer, ...)
     * \param n_max_chars Maximum number of characters to be read
     * \param dst Pointer to where the incoming line will be copied
     *
     * \return Returns `dst` on success or NULL otherwise
     */
    char* (*getline)(void* _input_args, size_t n_max_chars, char* dst);
    void* getline_args;

    /** \brief Method to check if the end of input has been reached
     *
     * This is used to check unexpected end of files and it can be left
     * optional
     *
     * \param _input_args Input arguments (e.g. custom `struct`, input file pointer, ...)
     *
     * \return Returns true if end of input has been reached or false otherwise
     */
    bool (*is_end_of_input)(void* _input_args);
    void* is_end_of_input_args;

    /** \brief Callback methods to send information to external handlers */
    struct crx2rnx_callbacks callbacks;

    /* debug options */
    bool output_overflow;

};

struct crx2rnx _crx2rnx;

// PRIVATE

/** \brief read, repair the line */
static void repair(char *s, char *ds){
    for(; *s != '\0' && *ds != '\0' ; ds++,s++){
        if(*ds == ' ')continue;
        if(*ds == '&')
            *s = ' ';
        else
            *s = *ds;
    }
    if(*ds != '\0') {
        sprintf(s,"%s",ds);
        for(; *s != '\0' ;s++) {
            if(*s == '&') *s = ' ';
        }
    }
}

static int crx2rnx__read_chk_line(struct crx2rnx* self, char *line){
    char *p;

    self->nl_count++;
    if( self->getline(self->getline_args, MAXCLM, line) == NULL ) {
        self->error_exit(8,line, self->nl_count);
    }

    if( (p = strchr(line,'\n')) == NULL) {
        if( (self->is_end_of_input != NULL) &&
            (self->is_end_of_input(self->is_end_of_input_args) == true) ) {     /** check if EOF is there **/
            if (self->error_exit) {
                self->error_exit(8, line, self->nl_count);
            }
        }else{
            if( ! self->skip_strange_options ) self->error_exit(13, line, self->nl_count);
            return 1;
        }
    }
    if( *(p-1) == '\n' )p--;
    if( *(p-1) == '\r' )p--;   /*** check DOS CR/LF ***/
    *p = '\0';
    return 0;
}

int parse_rinex_obs_epoch(const char* epoch_str, const uint8_t version, struct timespec* ts) {

    // Parse the string using sscanf
    int year, month, day, hour, minute, second;
    long fraction;
    int ret = -1;
    const char* str_start = (version == 2 ? epoch_str : &epoch_str[2]);
    int nread = sscanf(str_start, "%d %d %d %d %d %d.%ld",
               &year, &month, &day, &hour, &minute, &second, &fraction);

    if (nread != 7) {
        goto exit;
    }

    // Create a struct tm
    struct tm tm = {
        .tm_sec = second,
        .tm_min = minute,
        .tm_hour = hour,
        .tm_mday = day,
        .tm_mon = month - 1, // Month is 0-indexed in struct tm
        .tm_year = year - (version == 2 ? 0 : 1900),  // Rinex 2 is two digit, 3 is four digit
        .tm_isdst = -1 // Unknown DST information
    };

    // Convert struct tm to time_t
    time_t epoch_time = mktime(&tm);
    if (epoch_time == (time_t)-1) {
        goto exit;
    }

    // Populate the timespec struct
    ts->tv_sec = epoch_time;
    ts->tv_nsec = fraction * 1000000000;

    ret = 0;
exit:
    return ret;
};

/*---------------------------------------------------------------------*/
static int crx2rnx__header(struct crx2rnx* self){

    int ret = -1;

    char line[MAXCLM],*p;

    if( crx2rnx__read_chk_line(self, line) == 1 ) {
        if (self->error_exit) {
            self->error_exit(5,"1.0-2.0", self->nl_count);
        }
    }

    self->crinex_version = atoi(line);

    if( (strncmp(&line[0],"1.0",C3) != 0 && strncmp(&line[0],"3.0",C3) != 0) ||
         is_header_line_of_type(line, CRINEX_VERS) == false ) {
        if (self->error_exit) {
            self->error_exit(5,"1.0-2.0", self->nl_count);
        }
    }

    if( crx2rnx__read_chk_line(self, line) == 1 ) {
        if (self->error_exit) {
            self->error_exit(8,line, self->nl_count);
        }
    }

    if( crx2rnx__read_chk_line(self, line) == 1 ) {
        if (self->error_exit) {
            self->error_exit(8,line, self->nl_count);
        }
    }

    CHOP_BLANK(line,p);

    self->rinex_version=atoi(line);
    if (self->rinex_version == 2){
        ret = CRX2RNX_ERROR_UNSUPPORTED_FORMAT;
        goto exit;
    }

    self->rinex_params = &RINEX_PARAMS[1];

    if (self->callbacks.on_raw_line != NULL) {
        sprintf(self->msg, "%s\n",line);
        self->callbacks.on_raw_line(self->msg, self->callbacks.on_raw_line_args);
    }

    if(is_header_line_of_type(line, RINEX_VERSION) == false ||
       (line[5]!='2' && line[5]!='3' && line[5]!='4' ) ) {

        if (self->error_exit) {
            self->error_exit(15,"2.x, 3.x  or 4.x", self->nl_count);
        }
    }

    do {
        crx2rnx__read_chk_line(self, line);
        CHOP_BLANK(line,p);

        if (self->callbacks.on_raw_line != NULL) {
            sprintf(self->msg, "%s\n",line);
            self->callbacks.on_raw_line(self->msg, self->callbacks.on_raw_line_args);
        }

        if (is_header_line_of_type(line,TYPES_OF_OBSERV) == true && line[5] != ' '){
            self->ntype = atoi(line);                                        /** for RINEX2 **/

        } else if(is_header_line_of_type(line, SYS_OBS_TYPES) == true){
            if (line[0] != ' ') {
                char constellation = line[0];
                int n_obs = atoi(&line[3]);
                if (n_obs > MAXTYPE) {
                    ret = CRX2RNX_ERROR_TOO_MANY_OBS_TYPES;
                    goto exit;
                }

                self->current_obstypes_constellation = constellation;
                self->ntype_gnss[(unsigned int)constellation] = n_obs;
            }

            // Parse the observable types and append it to the array
            // of observable types for the current constellation
            char* p_observables = &self->types_gnss[(unsigned int)self->current_obstypes_constellation][0][0];

            /* look for the last stored type */
            char* p_append_pos = p_observables;
            for (int i = 0; i < self->ntype_gnss[(unsigned int)self->current_obstypes_constellation]; i ++) {
                if (*p_append_pos == '\0') {
                    break;
                }

                p_append_pos += 4;
            }

            for (int i = 0; i < 13; i ++) {
                char obscode[4] = "";

                if (line[7 + i * 4] == ' ') {
                    break;
                }

                obscode[0] = line[7 + i * 4];
                obscode[1] = line[7 + i * 4 + 1];
                obscode[2] = line[7 + i * 4 + 2];
                memcpy(p_append_pos, obscode, 4);
                p_append_pos += 4;  // go to next empty slot
            }
        }
    }while(is_header_line_of_type(line, END_OF_HEADER) == false);

    ret = 0;
exit:
    return ret;
}


static int crx2rnx__put_event_data(struct crx2rnx* self, char *dline, char *p_event){
/***********************************************************************/
/*  - Put event data for one event.                                    */
/*  - This function is called when the event flag > 1.                 */
/***********************************************************************/
    int i,n;
    char *p;
    do {
        dline[0] = self->rinex_params->ep_top_to;
        CHOP_BLANK(dline,p);

        if (self->callbacks.on_raw_line != NULL) {
            sprintf(self->msg, "%s\n", dline);
            self->callbacks.on_raw_line(self->msg, self->callbacks.on_raw_line_args);
        }

        if( strlen(dline) > 29 ){
            n = atoi((p_event+1));
            for(i=0;i<n;i++){
                crx2rnx__read_chk_line(self, dline);
                CHOP_BLANK(dline,p);

                if (self->callbacks.on_raw_line != NULL) {
                    sprintf(self->msg, "%s\n", dline);
                    self->callbacks.on_raw_line(self->msg, self->callbacks.on_raw_line_args);
                }

                if (strncmp(&dline[60],"# / TYPES OF OBSERV",C1*19) == 0 && dline[5] != ' ' ){
                     self->ntype = atoi(dline);                                        /** for RINEX2 **/
                } else if(strncmp(&dline[60],"SYS / # / OBS TYPES",C1*19) == 0){ /** for RINEX3 **/
                     if (dline[0] != ' ') {
                        self->ntype_gnss[(unsigned int)dline[0]] = atoi(&dline[3]);
                     }
                     if (self->ntype_gnss[(unsigned int)dline[0]] > MAXTYPE) {
                        if (self->error_exit) {
                            self->error_exit(16, dline, 0);
                        }
                     }
                }
            }
        }

        do {
            self->nl_count++;
            if(self->getline(self->getline_args, MAXCLM, dline) == NULL) {
                exit(EXIT_SUCCESS);  /*** eof: exit program successfully ***/
            }
        } while (self->crinex_version >= 3 && dline[0] == '&');
        CHOP_LF(dline,p);

        if(dline[0] != self->rinex_params->ep_top_from || strlen(dline)<29   || (isdigit(*p_event) == false)) {
            if (self->skip_strange_options == false) {
                if (self->error_exit) {
                    self->error_exit(9, dline, 0);
                }
            }

            if (self->callbacks.on_log_message != NULL) {
                sprintf(self->msg,"WARNING :  The epoch should be initialized, but not.\n");
                self->callbacks.on_log_message(self->msg, self->callbacks.on_log_message_args);
            }

            return 1;
        }
    }while(*p_event != '0' && *p_event != '1');
    return 0;
}

static void crx2rnx__skip_to_next(struct crx2rnx* self, char *dline){
    char *p;

    if (self->callbacks.on_log_message != NULL) {
        sprintf(self->msg,"    line %ld : skip until an initialized epoch is found.", self->nl_count);
        self->callbacks.on_log_message(self->msg, self->callbacks.on_log_message_args);
    }

    if(self->rinex_version == 2) {
        p = dline+3;    /** pointer to the space between year and month **/
    }else{
        p = dline+6;
    }

    do {
        self->nl_count++;
        if(self->getline(self->getline_args, MAXCLM, dline) == NULL) {

            if (self->callbacks.on_log_message != NULL) {
                sprintf(self->msg,"  .....next epoch not found before EOF.\n");
                self->callbacks.on_log_message(self->msg, self->callbacks.on_log_message_args);
            }

            if (self->callbacks.on_raw_line != NULL) {

                if(self->rinex_version == 2) {
                    sprintf(self->msg, "%29d%3d\n%-60sCOMMENT\n",4,1,"  *** Some epochs are skipped by CRX2RNX ***");
                }else{
                    sprintf(self->msg, ">%31d%3d\n%-60sCOMMENT\n",4,1,"  *** Some epochs are skipped by CRX2RNX ***");
                }

                self->callbacks.on_raw_line(self->msg, self->callbacks.on_raw_line_args);
            }

            exit(EXIT_WARNING);
        }
    }while(dline[0] != self->rinex_params->ep_top_from || strlen(dline) < 29   || *p != ' '
              || *(p+3)  != ' ' || *(p+6)  != ' ' || *(p+9)  != ' '
              || *(p+12) != ' ' || *(p+23) != ' ' || *(p+24) != ' '
              || ! isdigit(*(p+25)) );

    CHOP_LF(dline,p);

    if (self->callbacks.on_log_message != NULL) {
        sprintf(self->msg,"  .....next epoch found at line %ld.\n", self->nl_count);
        self->callbacks.on_log_message(self->msg, self->callbacks.on_log_message_args);
    }

    if (self->callbacks.on_raw_line != NULL) {

        if(self->rinex_version == 2) {
            sprintf(self->msg, "%29d%3d\n%-60sCOMMENT\n",4,1,"  *** Some epochs are skipped by CRX2RNX ***");
        }else{
            sprintf(self->msg, ">%31d%3d\n%-60sCOMMENT\n",4,1,"  *** Some epochs are skipped by CRX2RNX ***");
        }

        self->callbacks.on_raw_line(self->msg, self->callbacks.on_raw_line_args);
    }

}

static void crx2rnx__set_sat_table(struct crx2rnx* self, char *p_new, char *p_old, int nsat1, int *sattbl){
/***********************************************************************/
/*  - Read number of satellites (nsat)                                 */
/*  - Compare the satellite list at the epoch (*p_new) and that at the */
/*    previous epoch(*p_old), and make index (*sattbl) for the         */
/*    corresponding order of the satellites.                           */
/*    *sattbl is set to -1 for new satellites.                         */
/***********************************************************************/
    int i,j;
    char *ps;

    /*** set # of data types for each satellite ***/
    if(self->rinex_version == 2 ) {             /** for RINEX2 **/
        for (i = 0; i < self->nsat; i++) {
            self->ntype_record[i] = self->ntype;
        }
    }else{                                /** for RINEX3 **/
        for (i = 0, ps = p_new; i < self->nsat; i++, ps+=3){
            self->ntype_record[i] = self->ntype_gnss[(unsigned int)*ps];  /*** # of data type for the GNSS system ***/
            if(self->ntype_record[i]<0) {
                if (self->error_exit) {
                    self->error_exit(20, p_new, self->nl_count);
                }
            }
        }
    }
    for (i=0; i<self->nsat ; i++,p_new+=3){
        *sattbl = -1;
        for(j=0,ps=p_old ; j<nsat1 ; j++,ps+=3){
            if(strncmp(p_new,ps,C3) == 0){
                *sattbl = j;
                break;
            }
        }
        sattbl++;
    }
}

static int crx2rnx__getdiff(struct crx2rnx* self, data_format *y, data_format *dy0, int i0, char *dflag){
    int j,length;
    char *s,*s1,*s2,line[MAXCLM];

    /******************************************/
    /****  separate the fields with '\0'   ****/
    /******************************************/
    if(crx2rnx__read_chk_line(self, line)!=0) return 1;
    for(j=0,s=line; j<self->ntype; s++){
        if(*s == '\0') {
            j++;
            *(s+1) = '\0';
        }else if(*s == ' '){
            j++;
            *s = '\0';
        }
    }
    strcpy(dflag,s);

    /************************************/
    /*     read the differenced data    */
    /************************************/
    s1 = line;
    for(j=0;j<self->ntype;j++,y++,dy0++){
        if(*s1 == '\0'){
            y->arc_order = -1;      /**** arc_order < 0 means that the field is blank ****/
            y->order = -1;
            s1++;
        }else{
            if(*(s1+1) == '&'){     /**** arc initialization ****/
                y->order = -1;
                y->arc_order = atoi(s1);
                s1 += 2;
                if(y->arc_order > MAX_DIFF_ORDER) {
                    if (self->error_exit) {
                        self->error_exit(7, line, 0);
                    }
                }
            }else if(i0 < 0){
                if( self->skip_strange_options == false) {
                    if (self->error_exit) {
                        self->error_exit(11, line, 0);
                    }
                }

                if (self->callbacks.on_log_message != NULL) {
                    sprintf(self->msg,"WARNING : New satellite, but data arc is not initialized.\n");
                    self->callbacks.on_log_message(self->msg, self->callbacks.on_log_message_args);
                }

                return 1;
            }else if(dy0->arc_order < 0){
                if( self->skip_strange_options == false) {
                    if (self->error_exit) {
                        self->error_exit(12,line, 0);
                    }
                }

                if (self->callbacks.on_log_message != NULL) {
                    sprintf(self->msg,"WARNING : New data sequence but without initialization.\n");
                    self->callbacks.on_log_message(self->msg, self->callbacks.on_log_message_args);
                }

                return 1;
            }else{
                y->order = dy0->order;
                y->arc_order = dy0->arc_order;
            }
            length = (s2=strchr(s1,'\0'))-s1;
            if(*s1 == '-') length--;
            if(length < 6){
                y->u[0] = 0;
                y->l[0] = atol(s1);
            }else{
                s = s2-5;
                y->l[0] = atol(s); *s = '\0';
                y->u[0] = atol(s1);
                if(y->u[0] < 0) y->l[0] = -y->l[0];
            }
            s1 = s2+1;
        }
    }
    return 0;
}

static void crx2rnx__putfield(struct crx2rnx* self, data_format *y, char *flag){
    int  i;

    i = y->order;

    if(y->u[i]<0 && y->l[i]>0){
        y->u[i]++ ; y->l[i] -= 100000 ;
    }else if(y->u[i]>0 && y->l[i]<0){
        y->u[i]-- ; y->l[i] += 100000 ;
    }
    /* The signs of y->u and y->l are the same (or zero) at this stage */

    if(y->u[i]!=0){                                    /* ex) 123.456  -123.456 */
       self->p_buff += sprintf(self->p_buff,"%8ld %5.5ld%c%c",y->u[i],labs(y->l[i]),*flag,*(flag+1));
       self->p_buff[-8] = self->p_buff[-7];
       self->p_buff[-7] = self->p_buff[-6];
       if( y->u[i] > 99999999 || y->u[i] < -9999999 ){
          if( self->output_overflow == true ) {
              if (self->callbacks.on_log_message != NULL) {
                  sprintf(self->msg,"Warning: line %ld. : Data record becomes out of range allowed in the RINEX format. The output is corrupted.\n", self->nl_count);
                  self->callbacks.on_log_message(self->msg, self->callbacks.on_log_message_args);
              }
             exit(EXIT_WARNING);
          }else{
            if (self->error_exit) {
                self->error_exit(17, "Data record", 0);
            }
          }
       }
    }else{
       self->p_buff += sprintf(self->p_buff,"         %5.5ld%c%c",labs(y->l[i]),*flag,*(flag+1));
       if (self->p_buff[-7] != '0' ){                        /* ex)  12.345    -2.345 */
           self->p_buff[-8] = self->p_buff[-7];
           self->p_buff[-7] = self->p_buff[-6];
           if(y->l[i] <0) self->p_buff[-9]='-';
       }else if (self->p_buff[-6] != '0' ){                  /* ex)   1.234    -1.234 */
           self->p_buff[-7] = self->p_buff[-6];
           self->p_buff[-8] = (y->l[i] <0)? '-':' ';
       }else{                                          /* ex)    .123     -.123 */
           self->p_buff[-7] = (y->l[i] <0)? '-':' ';
       }
    }
    self->p_buff[-6] = '.';
}


/*---------------------------------------------------------------------*/
static void crx2rnx__print_clock(struct crx2rnx* self, long yu, long yl, int shift_clk){
    char tmp[8],*p_tmp,*p;
    int n,sgn;

    if(yu<0 && yl>0){
        yu++ ; yl -= 100000000;
    }else if(yu>0 && yl<0){
        yu-- ; yl += 100000000;
    }
    /* The signs of yu and yl are the same (or zero) at this stage */

    /** add ond more digit to handle '-0'(RINEX2) or '-0000'(RINEX3) **/
    sgn = (yl<0) ? -1:1;
    n = sprintf(tmp,"%.*ld",shift_clk+1,yu*10+sgn); /** AT LEAST fractional parts are filled with 0 **/
    n--;                           /** n: number of digits excluding the additional digit **/
    p_tmp = &tmp[n];
    *p_tmp = '\0';
    p_tmp -= shift_clk;       /** pointer to the top of last "shift_clk" digits **/
    self->p_buff += sprintf(self->p_buff,"  .%s",p_tmp);  /** print last "shift_clk" digits.  **/
    if( n > shift_clk ){
        p_tmp--;
        p = self->p_buff-shift_clk-2;
        *p = *p_tmp;

        if( n > shift_clk+1 ){
             *(p-1) =* (p_tmp-1);
             if( n > shift_clk+2 ){
                 if( self->output_overflow == true  ) {
                     if (self->callbacks.on_log_message != NULL) {
                         sprintf(self->msg,"Warning: line %ld. : Clock offset becomes out of range allowed in the RINEX format. The output is corrupted.\n",self->nl_count);
                         self->callbacks.on_log_message(self->msg, self->callbacks.on_log_message_args);
                     }
                    exit(EXIT_WARNING);
                 }else{
                    if (self->error_exit) {
                        self->error_exit(17,"Clock offset", self->nl_count);
                    }
                 }
             }
        }
    }

    self->p_buff += sprintf(self->p_buff,"%8.8ld\n",labs(yl));
}


static void crx2rnx__data(struct crx2rnx* self, char *p_sat_lst, int *sattbl, char dflag[][MAXTYPE*2]){
/********************************************************************/
/*  Functions                                                       */
/*      (1) compose the original data from 3rd order difference     */
/*      (2) repair the flags                                        */
/*  sattbl : previous column on which the satellites are set        */
/*           new satellites are set to -1                           */
/*       u : upper X digits of the data                             */
/*       l : lower 5 digits of the data                             */
/*            ( y = u*100 + l/1000)                                 */
/*   date of previous epoch are set to dy0                           */
/********************************************************************/
    data_format *py1,*py0;
    int  i,j,k,k1,*i0;
    char *p;

    for(i=0,i0=sattbl,p=p_sat_lst ; i< self->nsat ; i++,i0++,p+=3){
        /**** set # of data types for the GNSS type    ****/
        /**** and write satellite ID in case of RINEX3 ****/
        /**** ---------------------------------------- ****/
        if(self->rinex_version >= 3 ){
            self->ntype = self->ntype_record[i];
            strncpy(self->p_buff,p,C3);
            self->p_buff += 3;
        }
        /**** repair the data flags ****/
        /**** ----------------------****/
        if(*i0 < 0){       /* new satellite */
            if(self->rinex_version >= 3 ){
                *self->flag[i] = '\0';
            }else{
                sprintf(self->flag[i],"%-*s",self->ntype*2,dflag[i]);
            }
        }else{
            strncpy(self->flag[i],self->flag1[*i0],self->ntype*C2);
        }
        repair(self->flag[i], dflag[i]);

        /**** recover the date, and output ****/
        /**** ---------------------------- ****/
        for(j=0,py1=self->dy1[i] ; j<self->ntype ; j++,py1++){
            if(py1->arc_order >= 0){
                char* flag;
                py0 = &(self->dy0[*i0][j]);
                if(py1->order < py1->arc_order){
                    (py1->order)++;
                    for(k=0,k1=1; k<py1->order; k++,k1++){
                        py1->u[k1] = py1->u[k] + py0->u[k];
                        py1->l[k1] = py1->l[k] + py0->l[k];
                        py1->u[k1] += py1->l[k1]/100000;  /*** to avoid overflow of dy1.l ***/
                        py1->l[k1] %= 100000;
                    }
                }else{
                    for(k=0,k1=1; k<py1->order; k++,k1++){
                        py1->u[k1] = py1->u[k] + py0->u[k1];
                        py1->l[k1] = py1->l[k] + py0->l[k1];
                        py1->u[k1] += py1->l[k1]/100000;
                        py1->l[k1] %= 100000;
                    }
                }
                /* Signs of py1->u and py1->l can be different at this stage */
                /*   and will be adjusted before outputting                 */
                flag = &self->flag[i][j*2];
                crx2rnx__putfield(self, py1, flag);

                if (self->callbacks.on_measurement != NULL) {
                    char lli = flag[0];
                    strncpy(self->gnss_meas.satid, p, 3);
                    strncpy(self->gnss_meas.rinex3_code, "X0X\0", 4);
                    self->gnss_meas.value = atof(&self->p_buff[-15]);
                    self->gnss_meas.lli = (lli == ' ' ? 0 : (uint8_t)(lli - '0'));
                    strncpy(self->gnss_meas.rinex3_code, self->types_gnss[(uint8_t)self->gnss_meas.satid[0]][j], 3);
                    self->callbacks.on_measurement(&self->gnss_meas, self->callbacks.on_measurement_args);
                }

            }else{
                if (self->crinex_version == 1 ) {                       /*** CRINEX 1 assumes that flags are always ***/
                    self->p_buff += sprintf(self->p_buff,"                "); /*** blank if data field is blank           ***/
                    self->flag[i][j*2] = self->flag[i][j*2+1] = ' ';
                }else{                                            /*** CRINEX 3 evaluate flags independently **/
                    self->p_buff += sprintf(self->p_buff,"              %c%c",self->flag[i][j*2],self->flag[i][j*2+1]);
                }
            }
            if((j+1) == self->ntype || (self->rinex_version==2 && (j+1)%5 == 0 ) ){
                while(*--self->p_buff == ' '){}; self->p_buff++;  /*** cut spaces ***/
                *self->p_buff++ = '\n';
            }
        }
    }
}

static void crx2rnx__process_clock(struct crx2rnx* self){
    int i,j;
    /****************************************/
    /**** recover the clock offset value ****/
    /****************************************/
    if(self->clk_order < self->clk_arc_order){
        self->clk_order++;
        for(i=0,j=1 ; i<self->clk_order ; i++,j++){
            self->clk1.u[j] = self->clk1.u[i] + self->clk0.u[i];
            self->clk1.l[j] = self->clk1.l[i] + self->clk0.l[i];
            self->clk1.u[j] += self->clk1.l[j] / 100000000;  /*** to avoid overflow of dy1.l ***/
            self->clk1.l[j] %= 100000000;
        }
    }else{
        for(i=0,j=1 ; i<self->clk_order ; i++,j++){
            self->clk1.u[j] = self->clk1.u[i] + self->clk0.u[j];
            self->clk1.l[j] = self->clk1.l[i] + self->clk0.l[j];
            self->clk1.u[j] += self->clk1.l[j] / 100000000;
            self->clk1.l[j] %= 100000000;
        }
    }
    /* Signs of py1->u and py1->l can be different at this stage */
    /*   and will be adjustied before outputting */
}

static void crx2rnx__read_clock(struct crx2rnx* self, char *dline, long *yu, long *yl){
    char *p,*s,*p1;

    p = dline;

    if(*p == '\0'){
        self->clk_order = -1;
    }else{
        if(*(p+1) == '&') {        /**** for the case of arc initialization ****/
            sscanf(p,"%d&",&(self->clk_arc_order));
            if(self->clk_arc_order > MAX_DIFF_ORDER) {
                if (self->error_exit) {
                    self->error_exit(7,dline, self->nl_count);
                }
            }
            self->clk_order = -1;
            p += 2;
        }
        p1 = p; if(*p == '-') p1++;
        s = strchr(p1,'\0');
        if((s-p1) < 9 ){                /** s-p1 == strlen(p1) ***/
            *yu = 0;
            *yl = atol(p);
        }else{
            s -= 8;
            *yl = atol(s);
            *s = '\0';
            *yu = atol(p);
            if(*yu < 0) *yl = -*yl;
        }
    }
}

// PUBLIC

struct crx2rnx* crx2rnx__init(bool skip_strange_options, bool output_overflow, void (*error_exit)(int, char*, long), char* (*getline)(void*, size_t, char* ), void* _getline_args, bool (*is_end_of_input)(void*), void* is_end_of_input_args, struct crx2rnx_callbacks* callbacks) {

    memset(&_crx2rnx, 0, sizeof(struct crx2rnx));

    _crx2rnx.skip_strange_options = skip_strange_options;
    _crx2rnx.output_overflow = output_overflow;

    for(int i = 0; i < UCHAR_MAX; i++) {
        _crx2rnx.ntype_gnss[i] = -1;  /** -1 unless GNSS type is defined **/
    }

    _crx2rnx.error_exit = error_exit;

    _crx2rnx.getline = getline;
    _crx2rnx.getline_args = _getline_args;

    _crx2rnx.is_end_of_input = is_end_of_input;
    _crx2rnx.is_end_of_input_args = is_end_of_input_args;

    if (callbacks != NULL) {
        _crx2rnx.callbacks = *callbacks;
    }

    return &_crx2rnx;
}

int crx2rnx__run(struct crx2rnx* self) {

    int ret;

    char dline[MAXCLM] = "";

    static char sat_lst_old[MAXSAT*3];
    static int nsat1 = 0, n;

    char *p;
    int sattbl[MAXSAT],i,j,*i0;
    char dflag[MAXSAT][MAXTYPE*2];
       /* sattbl[i]: order (at the previous epoch) of i-th satellite */
       /* (at the current epoch). -1 is set for the new satellites   */

    ret = crx2rnx__header(self);
    if (ret < 0) {
        goto exit;
    }

    while(true){

        if (self->getline(self->getline_args, MAXCLM, dline) == NULL) {
            break;  /*** exit program successfully ***/
        }

        self->nl_count++;
        CHOP_LF(dline,p);
        SKIP:
        if(self->crinex_version == 3) { /*** skip escape lines of CRINEX version 3 ***/

            bool reached_eof = false;

            while(dline[0] == '&'){
                self->nl_count++;
                if(self->getline(self->getline_args, MAXCLM, dline) == NULL) {
                    reached_eof = true;
                    break;
                }
                CHOP_LF(dline,p);
            }

            if (reached_eof) {
                break;
            }
        }
        if(dline[0] == self->rinex_params->ep_top_from){
            dline[0] = self->rinex_params->ep_top_to;
            char* p_event = &dline[self->rinex_params->event_pos];
            if(*p_event!='0' && *p_event!='1' ){
                if(crx2rnx__put_event_data(self, dline, p_event)!=0) {
                    crx2rnx__skip_to_next(self, dline);
                }
                goto SKIP;
            }
            self->line[0] = '\0';          /**** initialize arc for epoch data ***/
            nsat1 = 0;               /**** initialize the all satellite arcs ****/
        }else if( dline[0] == '\032' ){
            break;   /** DOS EOF **/
        }
        repair(self->line,dline);
        p = &self->line[self->rinex_params->offset];  /** pointer to the space between year and month **/
        if(self->line[0] != self->rinex_params->ep_top_to || strlen(self->line)<(size_t)(26+self->rinex_params->offset) || *(p+23) != ' '
                             || *(p+24) != ' ' || ! isdigit(*(p+25)) ) {
            crx2rnx__skip_to_next(self, dline);
            goto SKIP;
        }
        CHOP_BLANK(self->line,p);

        char* p_nsat = &self->line[self->rinex_params->nsat_pos];
        char* p_satlst = &self->line[self->rinex_params->satlst_pos];

        self->nsat = atoi(p_nsat);
        if(self->nsat > MAXSAT) {
            self->error_exit(6, p_nsat, self->nl_count);
        }


        crx2rnx__set_sat_table(self, p_satlst,sat_lst_old,nsat1,sattbl); /****  set satellite table  ****/
        if(crx2rnx__read_chk_line(self, dline) != 0) {
            crx2rnx__skip_to_next(self, dline);
            goto SKIP;
        }

        crx2rnx__read_clock(self, dline, self->clk1.u, self->clk1.l);
        for(i=0,i0=sattbl ; i<self->nsat ; i++,i0++){
            self->ntype = self->ntype_record[i];
            if( crx2rnx__getdiff(self, self->dy1[i], self->dy0[*i0],*i0,dflag[i]) != 0 ) {
                crx2rnx__skip_to_next(self, dline);
                goto SKIP;
            }
        }

        /*************************************/
        /**** print the recovered line(s) ****/
        /*************************************/
        if(dline[0] != '\0') crx2rnx__process_clock(self);
        self->p_buff = self->out_buff;

        uint8_t shift_clk = self->rinex_params->shift_clk;
        if(self->rinex_version == 2){
            if(self->clk_order >= 0){
                self->p_buff += sprintf(self->p_buff,"%-68.68s",self->line);
                crx2rnx__print_clock(self, self->clk1.u[self->clk_order],self->clk1.l[self->clk_order],shift_clk);
            }else{
                self->p_buff += sprintf(self->p_buff,"%.68s\n",self->line);
            }
            for(p = &self->line[68],n=self->nsat-12; n>0; n-=12,p+=36) self->p_buff += sprintf(self->p_buff,"%32.s%.36s\n"," ",p);

            parse_rinex_obs_epoch(self->line, 2, &self->gnss_meas.gps_time);
        }else{
            if(self->clk_order >= 0){
                self->p_buff += sprintf(self->p_buff,"%.41s",self->line);
                crx2rnx__print_clock(self, self->clk1.u[self->clk_order],self->clk1.l[self->clk_order],shift_clk);
            }else{
                sprintf(self->p_buff,"%.41s",self->line);
                CHOP_BLANK(self->p_buff,p);*p++ = '\n';self->p_buff=p;
            }

            /* set epoch of current measurement*/
            parse_rinex_obs_epoch(self->line, 3, &self->gnss_meas.gps_time);
        }

        crx2rnx__data(self, p_satlst,sattbl,dflag);

        *self->p_buff = '\0';

        /* send RINEX block to external handler*/
        if (self->callbacks.on_raw_line != NULL) {
            self->callbacks.on_raw_line(self->out_buff, self->callbacks.on_raw_line_args);
        }

        /****************************/
        /**** save current epoch ****/
        /****************************/
        nsat1 = self->nsat;
        self->clk0 = self->clk1;
        strncpy(sat_lst_old, p_satlst, self->nsat * C3);
        for(i=0;i<self->nsat;i++) {
            strncpy(self->flag1[i],self->flag[i],self->ntype_record[i]*C2);
            for(j=0;j<self->ntype_record[i];j++) {
                self->dy0[i][j] = self->dy1[i][j];
            }
        }
    }

    ret = 0;
exit:
    return ret;
}
