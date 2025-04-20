#!/bin/bash

# use gcc to compile C to assembly on a remote host of a specific architecture.
# use flags to avoid directive noise, etc.

set -e -o pipefail

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
platform=\${arch}_\${os}
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
    if ! \$cc --version 2>&1 | grep -q -e 'gcc' -e ' 4\.' ; then
        # if this isn't old gcc, we can use more options.
        ccopts="\$ccopts -fcf-protection=none -fno-dwarf2-cfi-asm"
    fi

    # compile C to asm:
    \$cc -S -\$opt \$ccopts /tmp/in.c -o /tmp/out.s

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
    echo "---- \$asm_fname:"
    cat /tmp/\$asm_fname

    # verify the cleaned up asm still compiles
    if test "\$has_main" = "1" ; then
        bin_fname=a.out
        rm -f /tmp/\$bin_fname
        \$cc -\$opt \$ccopts /tmp/\$asm_fname -o /tmp/\$bin_fname
    else
        bin_fname=a.o
        rm -f /tmp/\$bin_fname
        \$cc -c -\$opt \$ccopts /tmp/\$asm_fname -o /tmp/\$bin_fname
    fi

    # display the decompiled asm
    if which objdump >/dev/null 2>&1 ; then
        dis_ext=.\${platform}.\${opt}.objdump
        dis_fname=\$(basename $cfile .c)\$dis_ext
        echo "---- \$dis_fname:"
        objdump -d /tmp/\$bin_fname | tee /tmp/\$dis_fname
    elif which otool >/dev/null 2>&1 ; then
        dis_ext=.\${platform}.\${opt}.otool
        dis_fname=\$(basename $cfile .c)\$dis_ext
        echo "---- \$dis_fname:"
        otool -tV /tmp/\$bin_fname | tee /tmp/\$dis_fname
    fi

    # run the binary
    if test "\$has_main" = "1" ; then
        set +e
        /tmp/\$bin_fname ; echo "---- return value: \$?"
        set -e
    fi

    # copy the .s files back to the original host / dir
    if test "$host" = "localhost" ; then
        cp /tmp/\$asm_fname $origdir/s/\$asm_fname
        cp /tmp/\$dis_fname $origdir/s/\$dis_fname
    else
        scp /tmp/\$asm_fname $origuser@$orighost:$origdir/s/\$asm_fname
        scp /tmp/\$dis_fname $origuser@$orighost:$origdir/s/\$dis_fname
    fi

    echo
done
EOF
chmod +x /tmp/script.sh

if test -z "$host" ; then
    echo "usage: $0 c/file.c hostname" >&2
    echo "hosts:" >&2
    echo "  uranium (arm64_darwin)" >&2
    echo "  flouride (amd64_darwin)" >&2
    echo "  ibookg3 (ppc_darwin)" >&2
    echo "  opti7050 (amd64_linux)" >&2
    echo "  mini10v (i386_linux)" >&2
    echo "  pogo1 (arm_linux)" >&2
    echo "  qmips (mips_linux)" >&2
    echo "  qppc (ppc_linux)" >&2
    echo "  riscv (riscv_linux)" >&2
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
