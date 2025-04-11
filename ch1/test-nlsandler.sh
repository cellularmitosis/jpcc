#!/bin/bash

# run nora sandler's tests
# see https://github.com/nlsandler/writing-a-c-compiler-tests

# optionally takes a chapter number:
#   $ ./test-nlsandler.sh 2
# and also a stage:
#   $ ./test-nlsandler.sh 2 codegen

set -e -o pipefail

./build.sh

export PATH="$PATH:$HOME/github/nlsandler/writing-a-c-compiler-tests"

flags="--verbose --verbose --verbose --failfast"

if test -n "$2" ; then
    # note: --stage is one of lex,parse,validate,tacky,codegen,run
    set -x
    test_compiler $flags jpcc --chapter $1 --stage $2
else
    set -x
    test_compiler $flags jpcc --chapter $1
fi
