# This file is the main entry point into jpcc.

import sys
import os

from jpcc import C
from jpcc import x86_64
from jpcc import Targets
from jpcc import Serialization


def usage(fd):
    msg = """Usage: jpcc [options] <C files>
  --help: print this message.

Standard cc flags:
  -o foo: name the final executable 'foo'.
  -S: emit assembly to '/tmp/<file>.s'.
  -S -o foo.s: emit assembly to 'foo.s'.

Cross-compilation:
  --target amd64_darwin: compile for amd64_darwin.
  --list-targets: list the supported targets.

Observing AST's:
  --c-ast: print the C AST and exit.
  --asm-ast: print the ASM AST and exit.
  --indent 4: control the indentation of ASTs.

Flags for "Writing a C Compiler":
  --lex: stop after lexing.
  --parse: stop after parsing.
  --codgen: stop after codegen.

Environment variables:
  CC: specify the cc to use for preprocessing and machine code emission.
    Example: CC=gcc
    Example: CC=/usr/local/bin/gcc-14
  JPCC_<target>_SSH_HOST: hostname to use for remote cc invocation.
    Example: JPCC_amd64_darwin_SSH_HOST=flouride
    Example: JPCC_amd64_darwin_SSH_HOST=192.168.1.42
  JPCC_<target>_SSH_CC: specify the cc to use for remote invocation.
    Example: JPCC_amd64_darwin_SSH_CC=gcc
    Example: JPCC_amd64_darwin_SSH_CC=/opt/gcc-4.9.5/bin/gcc

Example invocations:
  $ jpcc foo.c
    Emit /tmp/foo.i, /tmp/foo.s and ./foo.

  $ jpcc -S foo.c
    Emit /tmp/foo.i and /tmp/foo.s.

  $ jpcc -S -o asm.s foo.c
    Emit /tmp/foo.i and ./asm.s.

  $ jpcc --c-ast foo.c
    Print the C AST for foo.c.

  $ jpcc --asm-ast foo.c
    Print the assembly AST for foo.c.

  $ JPCC_amd64_darwin_SSH_HOST=flouride jpcc foo.c
    Emit /tmp/foo.i and /tmp/foo.s, then ssh to host 'flouride' and use gcc to
    compile foo.s, then scp the binary back to localhost.
"""
    fd.write(msg)


def parse_command_line() -> tuple[set, dict, list]:
    """Parse the command line, returning flags, options, and args.
    Flags don't expect an argument, e.g. '--verbose'.
    Options expect an argument, e.g. '--output file.txt'.
    Args are everything left over after parsing flags and options.
    """
    # flags don't expect an argument:
    flag_names = set([
        '--help',
        # flags for compatibility with test_compiler from github.com/nlsandler/writing-a-c-compiler-tests:
        '--lex', '--parse', '--codgen',
        # standard compiler flags:
        '-S', '-c',
        # serialization flags
        '--c-ast', '--asm-ast',
        # cross-compilation flags
        '--list-targets',
    ])
    # options expect a argument:
    option_names = set(['-o', '--target', '--indent'])
    flags = set()
    options = {}
    args = []
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg in flag_names:
            flags.add(arg)
        elif arg in option_names:
            i += 1
            if i >= len(sys.argv):
                sys.stderr.write(f"Error: option '{arg}' expects an argument.\n")
                usage(sys.stderr)
                sys.exit(1)
            arg2 = sys.argv[i]
            options[arg] = arg2
        else:
            args.append(arg)
        i += 1
        continue
    return (flags, options, args)


def basename(fname: str) -> str:
    "/foo/bar.txt -> bar.txt"
    return os.path.split(fname)[1]


def drop_ext(fname: str) -> str:
    "foo.txt -> foo"
    return os.path.splitext(fname)[0]


def shell(cmdline):
    "Execute a shell command, returning the exit status."
    status = os.waitstatus_to_exitcode(os.system(cmdline))
    return status


if __name__ == "__main__":
    (g_flags, g_options, g_args) = parse_command_line()

    if '--help' in g_flags:
        usage(sys.stdout)
        sys.exit(0)

    # list the targets and exit if requested.
    if '--list-targets' in g_flags:
        print("Supported targets:")
        for target in Targets.supported_targets:
            print(target)
        sys.exit(0)

    # determine the input filename.
    if len(g_args) == 0:
        sys.stderr.write("Error: no input filename given.\n")
        usage(sys.stderr)
        sys.exit(1)
    if len(g_args) > 1:
        sys.stderr.write(
            "Error: only one input filename is currently supported, multiple given: %s\n" % g_args
        )
        usage(sys.stderr)
        sys.exit(1)
    c_fname = g_args[0]
    sys.stderr.write(f"Input: {c_fname}\n")

    # determine the target.
    if '--target' in g_options:
        target = Targets.Target.from_str(g_options['--target'])
        if target not in Targets.supported_targets:
            sys.stderr.write(f"Error: target '{target}' not supported.\n")
            sys.exit(1)
        Targets.current_target = target
    sys.stderr.write(f"Target: {Targets.current_target}\n")

    # find a compiler for preprocessing and final machine code output.
    if "CC" in os.environ:
        cc = os.environ["CC"]
    elif shell("which gcc >/dev/null 2>&1") == 0:
        cc = "gcc"
    elif shell("which clang >/dev/null 2>&1") == 0:
        cc = "clang"
    else:
        sys.stderr.write("Error: can't find a C compiler.\n")
        sys.exit(1)
    sys.stderr.write(f"cc: {cc}\n")

    # preprocess the input.
    i_fname = "/tmp/" + drop_ext(basename(c_fname)) + ".i"
    cmdline = f"{cc} -E -P {c_fname} -o {i_fname}"
    sys.stderr.write(cmdline + '\n')
    status = shell(cmdline)
    if status != 0:
        sys.exit(status)

    indent=4
    if '--indent' in g_options:
        indent = int(g_options['--indent'])

    # build the C AST.
    c_ast = C.parse(i_fname)
    if '--c-ast' in g_flags:
        # dump the C AST and exit.
        print(Serialization.to_exprs_str(c_ast, indent=indent))
        sys.exit(0)
    if '--lex' in g_flags or '--parse' in g_flags:
        # stop after lexing (or parsing).
        sys.exit(0)

    # generate assembly.
    asm_ast = x86_64.gen_Program(c_ast)
    if '--asm-ast' in g_flags:
        # dump the ASM AST and exit.
        print(Serialization.to_exprs_str(asm_ast, indent=indent))
        sys.exit(0)
    if '-S' in g_flags and '-o' in g_options:
        s_fname = g_options['-o']
    else:
        s_fname = "/tmp/" + drop_ext(basename(c_fname)) + '.s'
    asm_text = asm_ast.gas()
    if s_fname == '-':
        sys.stdout.write(asm_text)
    else:
        with open(s_fname, 'w') as fd:
            fd.write(asm_text)
            sys.stderr.write(f"Wrote: {s_fname}\n")
    if '--codegen' in g_flags or '-S' in g_flags:
        # stop after codegen.
        sys.exit(0)

    # use gcc to compile the assembly to machine code.
    # note: test_compiler expects the output binary to
    # be the basename of the .c file, in the same directory.
    # so 'cc /foo/bar.c' should produce '/foo/bar'.
    c_flag = '-c' if '-c' in g_flags else ''
    if '-o' in g_options:
        bin_fname = g_options['-o']
    else:
        bin_fname = drop_ext(c_fname)
        if '-c' in g_flags:
            bin_fname += '.o'
    cc_flags = f"{c_flag}"
    envarname = f"JPCC_{Targets.current_target}_SSH_HOST"
    if envarname in os.environ:
        # use SSH to run gcc on a remote host.
        # note: using persistent SSH connections can greatly improve
        # performance when running lots of tests.
        # here's my ~/.ssh/config:
        #   Host *
        #       ControlMaster auto
        #       ControlPath  ~/.ssh/%r@%h-%p.socket
        #       ControlPersist  600

        host = os.environ[envarname]
        sys.stderr.write(f"{envarname}: {host}\n")

        remote_cc = "gcc"
        envarname = f"JPCC_{Targets.current_target}_SSH_CC"
        if envarname in os.environ:
            remote_cc = os.environ[envarname]
            sys.stderr.write(f"{envarname}: {remote_cc}\n")

        remote_s_fname = f"/tmp/{basename(s_fname)}"
        remote_bin_fname = f"/tmp/{basename(bin_fname)}"

        # copy the assembly file to the remote host.
        cmdline = f"scp -q {s_fname} {host}:{remote_s_fname}"
        sys.stderr.write(cmdline + '\n')
        status = shell(cmdline)
        if status != 0: sys.exit(status)

        # invoke the compiler on the remote host.
        cmdline = f"ssh {host} 'cd /tmp && {remote_cc} {cc_flags} -o {remote_bin_fname} {remote_s_fname}'"
        sys.stderr.write(cmdline + '\n')
        status = shell(cmdline)
        if status != 0: sys.exit(status)

        # if this was a .o, copy it back to localhost.
        if bin_fname.endswith('.o'):
            cmdline = f"scp -q {host}:{remote_bin_fname} {bin_fname}"
            sys.stderr.write(cmdline + '\n')
            status = shell(cmdline)
            sys.exit(status)
        # if this was an executable, create a wrapper script to invoke it remotely.
        else:
            with open(bin_fname, "w") as fd:
                script = f"""#!/bin/bash
set -e
ssh {host} "{remote_bin_fname} \\"$@\\""
"""
                fd.write(script)
            assert shell(f"chmod +x {bin_fname}") == 0

    else:
        # assume localhost is the correct target and run gcc locally.
        cmdline = f"{cc} {c_flag} -o {bin_fname} {s_fname}"
        sys.stderr.write(cmdline + '\n')
        status = shell(cmdline)
        sys.exit(status)
