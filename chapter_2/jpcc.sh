#!/bin/bash

# run jpcc, building a python zipapp first if needed.

set -e

if test "$1" = "--module" ; then
    shift
    # run as a python module.
    PYTHONPATH="jpcc-zipapp:$PYTHONPATH" python3 -m jpcc "$@"
else
    # run as a python zipapp.
    ./build.sh && ./jpcc "$@"
fi
