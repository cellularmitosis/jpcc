#!/bin/bash

# run nora sandler's tests
# see https://github.com/nlsandler/writing-a-c-compiler-tests

# optionally takes a chapter number:
#   $ ./test-nlsandler.sh 2
# and also a stage:
#   $ ./test-nlsandler.sh 2 codegen

set -e -o pipefail

testpath="$HOME/github/nlsandler/writing-a-c-compiler-tests"
if ! test -e "$testpath" ; then
    echo "Downloading nlsandler/writing-a-c-compiler-tests" >&2
    mkdir -p ~/github/nlsandler
    cd ~/github/nlsandler
    git clone git@github.com:nlsandler/writing-a-c-compiler-tests
    cd -
fi
export PATH="$PATH:$testpath"

./build.sh

flags="--verbose --verbose --verbose --failfast"

ch=$1
if test -z "$ch" ; then
    ch=1
fi

if test -n "$2" ; then
    # note: --stage is one of lex,parse,validate,tacky,codegen,run
    set -x
    test_compiler $flags jpcc --chapter $ch --stage $2
else
    set -x
    test_compiler $flags jpcc --chapter $ch
fi
