#!/bin/bash

# run nora sandler's tests
# see https://github.com/nlsandler/writing-a-c-compiler-tests

# optionally takes a chapter number:
#   $ ./test-nlsandler.sh 2
# and also a stage:
#   $ ./test-nlsandler.sh 2 codegen

set -e -o pipefail

#testrepo=nlsandler/writing-a-c-compiler-tests
testrepo=cellularmitosis/writing-a-c-compiler-tests
testpath="$HOME/github/$testrepo"
if ! test -e "$testpath" ; then
    echo "Downloading $testrepo" >&2
    mkdir -p ~/github/$testrepo
    cd ~/github/$testrepo
    git clone git@github.com:$testrepo .
    cd -
fi
export PATH="$PATH:$testpath"

./build.sh

flags="--verbose --verbose --verbose --failfast"

# note: pycparser doesn't fail on missing return type, so we ignore that test.
flags="$flags --ignore chapter_1/invalid_parse/missing_type.c"

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
