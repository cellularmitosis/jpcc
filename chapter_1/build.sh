#!/bin/bash

# build a single-file distributable zipapp version of the jpcc.

set -e

python3 -m zipapp -p "/usr/bin/env python3" jpcc-zipapp -o jpcc
