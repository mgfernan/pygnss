#!/bin/bash

CRX2RNX="${BIN_PATH}/crx2rnx"

ANSWER="${TESTS_SOURCE_FOLDER}/test_CRZ2RNX/answer.txt"

zcat ${TESTS_SOURCE_FOLDER}/data/ACSO00XXX_R_20241310000_01D_01S_MO.crx.Z  | ${CRX2RNX} | grep -f ${ANSWER} | diff - ${ANSWER}
