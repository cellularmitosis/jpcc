# This file is the main entry point into jpcc.

import sys
import os

from jpcc import C
from jpcc import x86_64
from jpcc import Targets
from jpcc import Serialization


def parse_command_line() -> tuple[set, dict, list]:
    """Parse the command line, returning flags, options, and args.
    Flags don't expect an argument, e.g. '--verbose'.
    Options expect an argument, e.g. '--output file.txt'.
    Args are everything left over after parsing flags and options.
    """
    # flags don't expect an argument:
    flag_names = set([
        # flags for compatibility with test_compiler from github.com/nlsandler/writing-a-c-compiler-tests:
        '--lex', '--parse', '--codgen', '--validate', '--tacky', '--codegen', '--run',
        # standard compiler flags:
        '-S', '-c',
        # serialization flags
        '--c-ast', '--asm-ast',
    ])
    # options expect a argument:
    option_names = set(['-o', '--target'])
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

    # determine the input filename.
    if len(g_args) == 0:
        sys.stderr.write("Error: no input filename given.\n")
        sys.exit(1)
    if len(g_args) > 1:
        sys.stderr.write("Error: only one input filename is currently supported, multiple given: %s\n" % g_args)
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

    # build the AST.
    c_ast = C.parse(i_fname)
    if '--c-ast' in g_flags:
        # dump the C AST and exit.
        print(Serialization.to_exprs_str(c_ast))
        sys.exit(0)
    if '--lex' in g_flags or '--parse' in g_flags:
        # stop after lexing (or parsing).
        sys.exit(0)

    # generate assembly.
    asm_ast = x86_64.gen_Program(c_ast)
    if '--asm-ast' in g_flags:
        # dump the ASM AST and exit.
        print(Serialization.to_exprs_str(asm_ast))
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
    if '-c' in g_flags:
        if '-o' in g_options:
            o_fname = g_options['-o']
        else:
            o_fname = drop_ext(c_fname) + '.o'
        cmdline = f"{cc} -c -o {o_fname} {s_fname}"
    else:
        if '-o' in g_options:
            exe_fname = g_options['-o']
        else:
            exe_fname = drop_ext(c_fname)
        cmdline = f"{cc} -o {exe_fname} {s_fname}"
    sys.stderr.write(cmdline + '\n')
    status = shell(cmdline)
    sys.exit(status)
