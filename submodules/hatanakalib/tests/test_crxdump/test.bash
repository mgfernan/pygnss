#!/bin/bash

PROGRAM="${BIN_PATH}/crxdump"

ANSWER="${TESTS_SOURCE_FOLDER}/test_crxdump/answer.txt"

zcat ${TESTS_SOURCE_FOLDER}/data/ACSO00XXX_R_20241310000_05S_01S_MO.crx.gz  | ${PROGRAM} | diff - ${ANSWER}
