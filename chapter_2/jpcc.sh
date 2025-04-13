#!/bin/bash

# a script to invoke jpcc as a python module.

set -e

PYTHONPATH="jpcc-zipapp:$PYTHONPATH" python3 -m jpcc "$@"
