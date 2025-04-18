# This file translates a chapter 2 TAC AST into a ASM AST and emits GAS-syntax assembly.

from __future__ import annotations
from dataclasses import dataclass

# So for return-comp-neg-2.c:
#
#   int main(void) {
#       return ~(-2);
#   }
#
# we want to translate this TAC AST:
#
#   (Program
#      funcdef (Function
#         name "main"
#         body (list
#            (Unary
#               op (Negate)
#               src (Constant
#                  value 2
#               )
#               dst (Var
#                  name "tmp0"
#               )
#            )
#            (Unary
#               op (Complement)
#               src (Var
#                  name "tmp0"
#               )
#               dst (Var
#                  name "tmp1"
#               )
#            )
#            (Return
#               val (Var
#                  name "tmp1"
#               )
#            )
#         )
#      )
#   )
#
# into this ASM AST:
#
#   (Program
#      statements (list
#         (Directive
#            name ".globl"
#            content "_main"
#            comment "Make _main externally visible."
#         )
#         (LabelDef
#            name "main"
#            comment "Begin function main."
#         )
#         (Pushq
#            arg (RBP)
#            comment "Save the caller's base pointer."
#         )
#         (Movq
#            src (RSP)
#            dst (RBP)
#            comment "Start a new stack frame."
#         )
#         (Subq
#            src (Stack
#               offset -16
#            )
#            dst (RSP)
#            comment "Allocate 16 bytes on the stack for locals."
#         )
#         (Movl
#            src (Imm
#               value 2
#            )
#            dst (R11D)
#            comment "Load."
#         )
#         (Negl
#            arg (R11D)
#         )
#         (Movl
#            src (R11D)
#            dst (Stack
#               offset -8
#            )
#            comment "Store."
#         )
#         (Movl
#            src (Stack
#               offset -8
#            )
#            dst (R11D)
#            comment "Load."
#         )
#         (Notl
#            arg (R11D)
#         )
#         (Movl
#            src (R11D)
#            dst (Stack
#               offset -16
#            )
#            comment "Store."
#         )
#         (Movl
#            src (Stack
#               offset -16
#            )
#            dst (EAX)
#            comment "Use -16(%rbp) as the return value."
#         )
#         (Movq
#            src (RBP)
#            dst (RSP)
#            comment "Tear down the stack frame."
#         )
#         (Popq
#            arg (RBP)
#            comment "Restore the caller's base pointer."
#         )
#         (Ret
#            comment "Jump to the return address."
#         )
#         (Comment
#            comment "End function main."
#         )
#      )
#   )
#
# and then emit this amd64 assembly:
#
#           .globl _main            /* Make _main externally visible. */
#   _main:                          # Begin function main.
#           pushq %rbp              # Save the caller's base pointer.
#           movq %rsp, %rbp         # Start a new stack frame.
#           subq -16(%rbp), %rsp    # Allocate 16 bytes on the stack for locals.
#           movl $2, %r11d          # Load.
#           negl %r11d              # Negate %r11d.
#           movl %r11d, -8(%rbp)    # Store.
#           movl -8(%rbp), %r11d    # Load.
#           notl %r11d              # Flip all of the bits of %r11d.
#           movl %r11d, -16(%rbp)   # Store.
#           movl -16(%rbp), %eax    # Use -16(%rbp) as the return value.
#           movq %rbp, %rsp         # Tear down the stack frame.
#           popq %rbp               # Restore the caller's base pointer.
#           ret                     # Jump to the return address.
#                                   # End function main.

# Note that my ASM generation approach diverges from the book:
# - I pretend that amd64 is a "load/store" architecture.

# Note: 'GAS' (GNU as) syntax is:
#   instruction source, destination
# e.g. this copies %rsp into %rbp:
#   movl %rsp, %rbp


from jpcc import tac
from jpcc import amd64

def _lowest_offset(symbol_table: dict) -> int:
    "Find the lowest offset in the symbol table."
    lowest = 0
    for k, v in symbol_table.items():
        if v.offset < lowest:
            lowest = v.offset
    return lowest


def _get_symbol(symbol: str, symbol_table: dict):
    "Return the Stack() location of the symbol, adding it to the table if needed."
    assert isinstance(symbol, str), symbol
    if symbol not in symbol_table:
        lowest = _lowest_offset(symbol_table)
        symbol_table[symbol] = amd64.Stack(lowest - 8)
    return symbol_table[symbol]


def gen_Program(tac_ast: tac.Program) -> amd64.Program:
    "Generate assembly for a tac.Program."
    assert(isinstance(tac_ast, tac.Program))
    asm_ast = amd64.Program(
        statements = _gen_Function(tac_ast.funcdef)
    )
    return asm_ast


def _gen_Function(tac_fn_ast: tac.Function) -> list[amd64.Statement]:
    "Generate assembly for a tac.Function."
    assert(isinstance(tac_fn_ast, tac.Function))
    statements = []
    funcname = tac_fn_ast.name

    # declare the function.
    funclabel = amd64.format_label(funcname)
    statements += [
        amd64.Directive(".globl", funclabel, f"Make {funclabel} externally visible."),
        amd64.LabelDef(funcname, f"Begin function {funcname}.")
    ]

    # function prologue.
    statements += [
        amd64.Pushq(amd64.RBP(), "Save the caller's base pointer."),
        amd64.Movq(src=amd64.RSP(), dst=amd64.RBP(), comment="Start a new stack frame."),
    ]
    allocate_stack = amd64.Subq(src=amd64.Fixup(), dst=amd64.RSP(), comment=amd64.Fixup())
    statements.append(allocate_stack)

    # function body.
    assert(isinstance(tac_fn_ast.body, list))
    symbol_table = {}
    for tac_inst in tac_fn_ast.body:
        statements += _gen_Instruction(tac_inst, symbol_table)

    # fixup the stack allocation.
    lowest = _lowest_offset(symbol_table)
    allocate_stack.src = amd64.Stack(lowest)
    allocate_stack.comment = f"Allocate {lowest * -1} bytes on the stack for locals."

    statements += [amd64.Comment(f"End function {funcname}.")]
    return statements


def _gen_Instruction(tac_ast: tac.Instruction, symbol_table: dict) -> list[amd64.Statement]:
    "Generate assembly for a tac.Instruction."
    assert isinstance(tac_ast, tac.Instruction)
    statements = []
    match tac_ast:
        case tac.Unary():
            return _gen_Unary(tac_ast, symbol_table)
        case tac.Return():
            return _gen_Return(tac_ast, symbol_table)
        case _:
            raise Exception(f"Unreachable")
    return statements


def _gen_Unary(tac_ast: tac.Unary, symbol_table: dict) -> list[amd64.Statement]:
    "Generate assembly for a tac.Unary."
    assert isinstance(tac_ast, tac.Unary)
    statements = []
    match tac_ast:
        case tac.Unary(op, tac_src, tac_dst):
            match tac_src:
                case tac.Constant() as con:
                    src = amd64.Imm(con.value)
                case tac.Var() as var:
                    src = _get_symbol(var.name, symbol_table)
                case _:
                    raise Exception(f"Unreachable")
            dst = _get_symbol(tac_dst.name, symbol_table)
            # pretend this is a load-store architecture.
            # load the src into a register.
            statements += [amd64.Movl(src=src, dst=amd64.R11D(), comment="Load.")]
            # perform the unary operation on the register.
            match op:
                case tac.Complement():
                    statements += [amd64.Notl(amd64.R11D())]
                case tac.Negate():
                    statements += [amd64.Negl(amd64.R11D())]
                case _:
                    raise Exception(f"Unreachable")
            # store the register into dst.
            statements += [amd64.Movl(src=amd64.R11D(), dst=dst, comment="Store.")]
        case _:
            raise Exception(f"Unreachable")
    return statements


def _gen_Return(tac_ast: tac.Return, symbol_table: dict) -> list[amd64.Statement]:
    "Generate assembly for a tac.Return."
    assert isinstance(tac_ast, tac.Return)
    arg = tac_ast.val
    assert isinstance(arg, tac.Operand)
    match arg:
        case tac.Constant() as con:
            src = amd64.Imm(con.value)
        case tac.Var() as var:
            src = _get_symbol(var.name, symbol_table)
        case _:
            raise Exception(f"Unreachable")
    statements = [
        amd64.Movl(src=src, dst=amd64.EAX(), comment=f"Use {src.gas()} as the return value."),
        amd64.Movq(src=amd64.RBP(), dst=amd64.RSP(), comment="Tear down the stack frame."),
        amd64.Popq(amd64.RBP(), "Restore the caller's base pointer."),
        amd64.Ret(comment="Jump to the return address."),
    ]
    return statements
