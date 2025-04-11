#!/bin/bash

# use gcc to compile C to assembly on a remote host of a specific architecture.
# use flags to avoid directive noise, etc.

set -e

cfile=$1
host=$2

orighost=$(hostname -s)
origuser=$(whoami)
origdir=$(pwd)

if test "$host" = "ibookg3" ; then
    echo '#!/opt/tigersh-deps-0.1/bin/bash' > /tmp/script.sh
else
    echo '#!/bin/bash' > /tmp/script.sh
fi

# create a script which will run locally or on a remote host
cat >> /tmp/script.sh << EOF
set -e -o pipefail

cd /tmp

# announce if we are running on a remote host
if test -n "$host" ; then
    echo running on host: $host
fi

# determine the os-arch platform
os=\$(uname -s | tr 'A-Z' 'a-z')
if test "$host" = "ibookg3" ; then
    arch=\$(uname -p)
else
    arch=\$(uname -m)
fi
platform=\$os-\$arch
echo platform: \$platform

# determine which cc to use
cc=gcc
if test "\$platform" = "darwin-arm64" ; then
    cc=clang
fi
echo "using compiler: \$cc"

# does the c file contain a main function?
if grep -q 'int main(' /tmp/in.c ; then
    has_main=1
fi

# run once with -O and again with -O0
for opt in O O0 ; do
    # choose flags to reduce noise in the asm output
    ccopts="-fno-asynchronous-unwind-tables -fno-verbose-asm -fno-pie -g0"
    if ! gcc --version 2>&1 | grep -q ' 4\.' ; then
        # if this isn't old gcc, we can use more options.
        ccopts="\$ccopts -fcf-protection=none -fno-dwarf2-cfi-asm"
    fi

    # compile C to asm:
    \$cc -S -\$opt \$ccopts \
        /tmp/in.c -o /tmp/out.s

    # clean up the asm output further
    asm_ext=.\${platform}.\${opt}.s
    asm_fname=\$(basename $cfile .c)\$asm_ext
    mkdir -p s
    cat /tmp/out.s \
        | grep -v -e '\.file' -e '\.size' -e '\.ident' -e '@function' \
        -e '\.build_version' \
        -e '\.subsections_via_symbols' \
        > /tmp/\$asm_fname

    # add a space after each comma on darwin-powerpc
    if test "\$platform" = "darwin-powerpc" ; then
        sed -i '' -e s'|,|, |' /tmp/\$asm_fname
    fi

    # display the asm
    echo "---- \$asm_fname with -\$opt:"
    cat /tmp/\$asm_fname

    # verify the cleaned up asm still compiles
    set +e
    if test "\$has_main" = "1" ; then
        rm -f /tmp/a.out && gcc /tmp/\$asm_fname -o /tmp/a.out && /tmp/a.out ; echo return value: \$?
    else
        rm -f /tmp/a.o && gcc -c /tmp/\$asm_fname -o /tmp/a.o && objdump -t /tmp/a.o ; echo return value: \$?
    fi
    set -e

    # copy the .s files back to the original host / dir
    if test "$host" = "localhost" ; then
        cp /tmp/\$asm_fname $origdir/s/\$asm_fname
    else
        scp /tmp/\$asm_fname $origuser@$orighost:$origdir/s/\$asm_fname
    fi

    echo
done
EOF
chmod +x /tmp/script.sh

if test -z "$host" ; then
    echo "usage: $0 c/file.c hostname" >&2
    echo "hosts:" >&2
    echo "  uranium (darwin-arm64)" >&2
    echo "  flouride (darwin-x86_64)" >&2
    echo "  ibookg3 (darwin-powerpc)" >&2
    echo "  opti7050 (linux-x86_64)" >&2
    echo "  mini10v (linux-i686)" >&2
    echo "  pogo1 (linux-armv5tel)" >&2
    echo "  qmips (linux-mips)" >&2
    echo "  qppc (linux-ppc)" >&2
    echo "  riscv (linux-riscv)" >&2
    exit 1
fi

if test "$host" = "localhost" ; then
    # run locally
    cp $cfile /tmp/in.c
    /tmp/script.sh
else
    # scp the script and files and run remotely 
    scp -O $cfile $host:/tmp/in.c
    scp -O /tmp/script.sh $host:/tmp/script.sh
    ssh $host /tmp/script.sh
fi
