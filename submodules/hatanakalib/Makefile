AR := ar
CC := gcc
CFLAGS := -Wall -Werror -I.

BIN_DIR := build/bin
LIB_DIR := build/lib

export BIN_PATH := ${PWD}/$(BIN_DIR)
export SOURCE_FOLDER := ${PWD}
export TESTS_SOURCE_FOLDER := ${PWD}/tests
export TESTS_BIN_FOLDER := ${PWD}/build/tests

# make DEBUG=1
ifeq ($(DEBUG), 1)
  CFLAGS += -g
endif

# Default target
all: crx2rnx crxdump rnx2crx

crx2rnx crxdump rnx2crx: $(LIB_DIR)/hatanaka.a
crx2rnx crxdump rnx2crx $(LIB_DIR)/hatanaka.a: build

# Create the build directory if it doesn't exist
.PHONY: build
build:
	mkdir -p $(BIN_DIR) $(LIB_DIR)

$(LIB_DIR)/%.o: hatanaka/src/%.c
	$(CC) $(CFLAGS) -c $< -o $@

crx2rnx: bin/crx2rnx/main.c build $(LIB_DIR)/common.o $(LIB_DIR)/crx2rnx.o
	$(CC) $(CFLAGS) $< $(LIB_DIR)/common.o $(LIB_DIR)/crx2rnx.o -o $(BIN_DIR)/crx2rnx

crxdump: bin/crxdump/main.c build $(LIB_DIR)/common.o $(LIB_DIR)/crx2rnx.o
	$(CC) $(CFLAGS) $< $(LIB_DIR)/common.o $(LIB_DIR)/crx2rnx.o -o $(BIN_DIR)/crxdump

rnx2crx: bin/rnx2crx/main.c
	$(CC) $(CFLAGS) $< -o $(BIN_DIR)/rnx2crx

# Run tests (replace 'test.c' with your test file)
test: crx2rnx crxdump
	(mkdir -p ${TESTS_BIN_FOLDER}/test_CRZ2RNX; cd ${TESTS_BIN_FOLDER}/test_CRZ2RNX; ${SOURCE_FOLDER}/tests/test_CRZ2RNX/test.bash)
	(mkdir -p ${TESTS_BIN_FOLDER}/test_crxdump; cd ${TESTS_BIN_FOLDER}/test_crxdump; ${SOURCE_FOLDER}/tests/test_crxdump/test.bash)

.PHONY: clean
clean:
	rm -rf build
