# This file translates a chapter 2 TAC AST into a ASM AST and emits GAS-syntax assembly.

from __future__ import annotations
from dataclasses import dataclass

from jpcc import Targets


# Nora Sandler's ASDL for the subset of ASM from chapter 2:
#       program = Program(funcdef)
#       funcdef = Function(identifier name, instruction* instructions)
#   instruction = Mov(operand src, operand dst)
#               | Unary(unaryop, operand)
#               | AllocateStack(int)
#               | Ret
#       unaryop = Neg | Not
#       operand = Imm(int) | Reg(reg) | Pseudo(identifier) | Stack(int)
#      reg = AX | R10

# I use a modified syntax and grammar:
#        ASM_AST > Program | Statement | Operand | Fixup
#        Program : Program(statements: list[Statement])
#      Statement > Directive | LabelDef | Instruction | Comment
#      Directive : Directive(name: str, content: str)
#       LabelDef : LabelDef(name: str)
#    Instruction : Instruction(comment: str)
#    Instruction > Instruction0 | Instruction1 | Instruction2
#   Instruction0 > Ret
#   Instruction1 : Instruction1(arg: Operand)
#   Instruction1 > Pushq | Popq | Negl | Notl
#   Instruction2 : Instruction2(src: Operand, dst: Operand)
#   Instruction2 > Movl | Movq | Subq
#        Operand > Imm | Register | Stack
#            Imm : Imm(value: int)
#       Register > RAX | RBX | ...
#          Stack : Stack(offset: int)
#        Comment : Comment(comment: str)


# So for return-comp-neg-2.c:
#
#   int main(void) {
#       return ~(-2);
#   }
#
# we want to make the following translation:
#
#   TAC AST:           ->  ASM AST:
#   ------                 --------
#   Program(           ->  Program(
#     Function(        ->    Function(
#       name="main",   ->      name=Identifier("main"),
#       body=Return(   ->      instructions=[
#         Constant(2)  ->        Mov(Imm(2), RAX),
#       )              ->        Ret()
#     )                ->      ]
#   )                  ->    )
#                      ->  )

# And then emit:
#     .globl main
# main:

# prolog
#     pushq %rbp
#     movq %rsp, %rbp

# allocate stack
#     subq $8, %rsp

# neg
#     movl $2, -4(%rbp)
#     negl -4(%rbp)

# not
#     movl -4(%rbp), %r10d
#     movl %r10d, -8(%rbp)
#     notl -8(%rbp)

# return value
#     movl -8(%rbp), %eax

# epilog
#     movq %rbp, %rsp
#     popq %rbp
#     ret


#   TAC AST:
#   --------
#   (Program
#     funcdef (Function
#       name "main"
#       body (list
#         (Unary
#           op (Negate)
#           src (Constant
#             value 2
#           )
#           dst (Var
#             name "tmp0"
#           )
#         )
#         (Unary
#           op (Complement)
#           src (Var
#             name "tmp0"
#           )
#           dst (Var
#             name "tmp1"
#           )
#         )
#         (Return
#           val (Var
#             name (Var
#               name "tmp1"
#             )
#           )
#         )
#       )
#     )
#   )

# ASM AST (FIXME)
# -------
# (Program
#   funcdef (Function
#     name (Identifier
#       name "main"
#     )
#     instructions (list
#       Subq
#       Neg
#       Not
#       Ret
#     )
#   )
# )


# And then emit:
#     .globl main
# main:
#     pushq %rbp
#     movq %rsp, %rbp
#     subq $8, %rsp
#     movl $2, -4(%rbp)
#     negl -4(%rbp)
#     movl -4(%rbp), %r10d
#     movl %r10d, -8(%rbp)
#     notl -8(%rbp)
#     movl -8(%rbp), %eax
#     movq %rbp, %rsp
#     popq %rbp
#     ret

# Note: 'GAS' (GNU as) syntax is:
#   instruction source, destination
# e.g. this copies %rsp into %rbp:
#   movl %rsp, %rbp


tab_width = 8  # the visible width of a rendered tab character
comment_col = 32  # the column at which comments should start.


def _coalesce(x, default_value):
    "Return the default value if x is None."
    return x if x is not None else default_value


def _vlen(s: str) -> int:
    "Return the visible length of a string, assuming tabs are 8 wide."
    return len(s) + (s.count('\t') * (tab_width - 1))


def _add_comment(stmt: str, comment: str, c_style: bool = False) -> str:
    "Add a comment to an ASM statement."
    if stmt is None:
        stmt = ""
    if comment is None:
        return stmt
    pad = (comment_col - _vlen(stmt)) * " "
    if c_style:
        # Note: '#' is the standard comment character for x86_64, but it appears
        # that it does not work after a directive, e.g. '.globl main # comment'.
        # However, '.globl main /* comment */' appears to work.
        line = f"{stmt}{pad}/* {comment} */"
    else:
        line = f"{stmt}{pad}# {comment}"
    return line


class ASM_AST: pass


class Fixup(ASM_AST): pass


class Operand(ASM_AST): pass


class Register(Operand):
    def gas(self) -> str:
        regname = self.__class__.__name__.lower()
        return f"%{regname}"


# x86_64 64-bit registers:
# See https://en.wikipedia.org/wiki/X86-64#Architectural_features

# General registers:
class RAX(Register): pass  # Accumulator register
class RBX(Register): pass  # Base register
class RCX(Register): pass  # Counter register
class RDX(Register): pass  # Data register

# Pointer registers:
class RSP(Register): pass  # Stack pointer
class RBP(Register): pass  # Base pointer

# Index registers:
class RDI(Register): pass  # Destination index
class RSI(Register): pass  # Source index

# Other:
class RIP(Register): pass  # Instruction pointer

class R8(Register): pass
class R9(Register): pass
class R10(Register): pass
class R11(Register): pass
class R12(Register): pass
class R13(Register): pass
class R14(Register): pass
class R15(Register): pass

# 32-bit registers:
class EAX(Register): pass
class EBX(Register): pass
class ECX(Register): pass
class EDX(Register): pass
class ESP(Register): pass
class EBP(Register): pass
class EDI(Register): pass
class ESI(Register): pass
class EIP(Register): pass
class R8D(Register): pass
class R9D(Register): pass
class R10D(Register): pass
class R11D(Register): pass
class R12D(Register): pass
class R13D(Register): pass
class R14D(Register): pass
class R15D(Register): pass


@dataclass
class Imm(Operand):
    value: int
    def gas(self) -> str:
        return f"${self.value}"


@dataclass
class Stack(Operand):
    offset: int
    def gas(self) -> str:
        return f"{self.offset}(%rbp)"


@dataclass
class Statement(ASM_AST):
    comment: str = None
    def get_comment(self) -> str:
        "This getter allows statements to provide a default comment."
        return self.comment


class Comment(Statement):
    "A bare comment."
    def gas(self) -> str:
        line = _add_comment(None, self.comment)
        return line


class Instruction(Statement): pass


class Instruction0(Instruction):
    "An instruction of artiy 0."
    def gas(self) -> str:
        op = self.__class__.__name__.lower()
        line = f"\t{op}"
        line = _add_comment(line, self.get_comment())
        return line


class Ret(Instruction0):
    def get_comment(self) -> str:
        default = f"Jump to the return address."
        return _coalesce(super().get_comment(), default)


class Instruction1(Instruction):
    "An instruction of artiy 1."
    def __init__(self, arg: Operand, comment: str = None):
        self.arg = arg
        self.comment = comment

    def gas(self) -> str:
        op = self.__class__.__name__.lower()
        line = f"\t{op} {self.arg.gas()}"
        line = _add_comment(line, self.get_comment())
        return line


class Pushq(Instruction1):
    def get_comment(self) -> str:
        default = f"Copy {self.arg.gas()} on the stack and decrement %rsp."
        return _coalesce(super().get_comment(), default)


class Popq(Instruction1):
    def get_comment(self) -> str:
        default = f"Copy the top of the stack into {self.arg.gas()} and increment %rsp."
        return _coalesce(super().get_comment(), default)


class Negl(Instruction1):
    def get_comment(self) -> str:
        default = f"Negate {self.arg.gas()}."
        return _coalesce(super().get_comment(), default)


class Notl(Instruction1):
    def get_comment(self) -> str:
        default = f"Flip all of the bits of {self.arg.gas()}."
        return _coalesce(super().get_comment(), default)


class Instruction2(Instruction):
    "An instruction of artiy 2."
    def __init__(self, *, src: Operand, dst: Operand, comment: str = None):
        self.src = src
        self.dst = dst
        self.comment = comment

    def gas(self) -> str:
        op = self.__class__.__name__.lower()
        src_str = self.src.gas()
        dst_str = self.dst.gas()
        line = f"\t{op} {src_str}, {dst_str}"
        line = _add_comment(line, self.get_comment())
        return line


class Movl(Instruction2):
    def get_comment(self) -> str:
        default = f"Copy (32-bit) {self.src.gas()} to {self.dst.gas()}."
        return _coalesce(super().get_comment(), default)


class Movq(Instruction2):
    def get_comment(self) -> str:
        default = f"Copy {self.src.gas()} to {self.dst.gas()}."
        return _coalesce(super().get_comment(), default)


class Subq(Instruction2):
    def get_comment(self) -> str:
        default = f"Subtract {self.src.gas()} from {self.dst.gas()} into {self.dst.gas()}"
        return _coalesce(super().get_comment(), default)


def _format_label(label: str) -> str:
    match Targets.current_target.os:
        case "darwin":
            return f"_{label}"
        case _:
            return label


@dataclass
class LabelDef(Statement):
    def __init__(self, name: str, comment: str = None):
        self.name = name
        self.comment = comment

    def gas(self) -> str:
        line = f"{_format_label(self.name)}:"
        line = _add_comment(line, self.get_comment())
        return line


@dataclass
class Directive(Statement):
    def __init__(self, name: str, content: str = None, comment: str = None):
        self.name = name
        self.content = content
        self.comment = comment

    def gas(self) -> str:
        if self.content is None:
            line = f"\t{self.name}"
        else:
            line = f"\t{self.name} {self.content}"
        line = _add_comment(line, self.get_comment(), c_style=True)
        return line


@dataclass
class Program(ASM_AST):
    statements: list[Statement]
    def gas(self) -> str:
        return "\n".join([s.gas() for s in self.statements]) + "\n"


from jpcc import TAC

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
        symbol_table[symbol] = Stack(lowest - 8)
    return symbol_table[symbol]


def gen_Program(tac_ast: TAC.Program) -> Program:
    "Generate assembly for a TAC.Program."
    assert(isinstance(tac_ast, TAC.Program))
    asm_ast = Program(
        statements = _gen_Function(tac_ast.funcdef)
    )
    return asm_ast


def _gen_Function(tac_fn_ast: TAC.Function) -> list[Statement]:
    "Generate assembly for a TAC.Function."
    assert(isinstance(tac_fn_ast, TAC.Function))
    statements = []
    funcname = tac_fn_ast.name

    # declare the function.
    funclabel = _format_label(funcname)
    statements += [
        Directive(".globl", funclabel, f"Make {funclabel} externally visible."),
        LabelDef(funcname, f"Begin function {funcname}.")
    ]

    # function prologue.
    statements += [
        Pushq(RBP(), "Save the caller's base pointer."),
        Movq(src=RSP(), dst=RBP(), comment="Start a new stack frame."),
    ]
    allocate_stack = Subq(src=Fixup(), dst=RSP(), comment=Fixup())
    statements.append(allocate_stack)

    # function body.
    assert(isinstance(tac_fn_ast.body, list))
    symbol_table = {}
    for tac_inst in tac_fn_ast.body:
        statements += _gen_Instruction(tac_inst, symbol_table)

    # fixup the stack allocation.
    lowest = _lowest_offset(symbol_table)
    allocate_stack.src = Stack(lowest)
    allocate_stack.comment = f"Allocate {lowest * -1} bytes on the stack for locals."

    statements += [Comment(f"End function {funcname}.")]
    return statements



def _gen_Instruction(tac_ast: TAC.Instruction, symbol_table: dict) -> list[Statement]:
    "Generate assembly for a TAC.Instruction."
    assert isinstance(tac_ast, TAC.Instruction)
    statements = []
    match tac_ast:
        case TAC.Unary():
            return _gen_Unary(tac_ast, symbol_table)
        case TAC.Return():
            return _gen_Return(tac_ast, symbol_table)
        case _:
            raise Exception(f"Unreachable")
    return statements


def _gen_Unary(tac_ast: TAC.Unary, symbol_table: dict) -> list[Statement]:
    "Generate assembly for a TAC.Unary."
    assert isinstance(tac_ast, TAC.Unary)
    statements = []
    match tac_ast:
        case TAC.Unary(op, tac_src, tac_dst):
            match tac_src:
                case TAC.Constant() as con:
                    src = Imm(con.value)
                case TAC.Var() as var:
                    src = _get_symbol(var.name, symbol_table)
                case _:
                    raise Exception(f"Unreachable")
            dst = _get_symbol(tac_dst.name, symbol_table)
            # pretend this is a load-store architecture.
            # load the src into a register.
            statements += [Movl(src=src, dst=R11D(), comment="Load.")]
            # perform the unary operation on the register.
            match op:
                case TAC.Complement():
                    statements += [Notl(R11D())]
                case TAC.Negate():
                    statements += [Negl(R11D())]
                case _:
                    raise Exception(f"Unreachable")
            # store the register into dst.
            statements += [Movl(src=R11D(), dst=dst, comment="Store.")]
        case _:
            raise Exception(f"Unreachable")
    return statements


def _gen_Return(tac_ast: TAC.Return, symbol_table: dict) -> list[Statement]:
    "Generate assembly for a TAC.Return."
    assert isinstance(tac_ast, TAC.Return)
    arg = tac_ast.val
    assert isinstance(arg, TAC.Operand)
    match arg:
        case TAC.Constant() as con:
            src = Imm(con.value)
        case TAC.Var() as var:
            src = _get_symbol(var.name, symbol_table)
        case _:
            raise Exception(f"Unreachable")
    statements = [
        Movl(src=src, dst=EAX(), comment=f"Use {src.gas()} as the return value."),
        Movq(src=RBP(), dst=RSP(), comment="Tear down the stack frame."),
        Popq(RBP(), "Restore the caller's base pointer."),
        Ret(comment="Jump to the return address."),
    ]
    return statements
