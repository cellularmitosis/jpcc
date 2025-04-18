# This file translates a chapter 2 TAC AST into a ASM AST and emits GAS-syntax assembly.

from __future__ import annotations
from dataclasses import dataclass


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

# Note that my amd64 AST diverges from the book:
# - removed the 'Function' AST node
# - added 'Directive', 'LabelDef' and 'Comment' AST nodes
# - split up the Instruction class hierarchy by arity (Instruction0, Instruction1, ...)
# - added a few organization superclasses (Statement, Instruction)

# Note: 'GAS' (GNU as) syntax is:
#   instruction source, destination
# e.g. this copies %rsp into %rbp:
#   movl %rsp, %rbp

from jpcc import targets

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


def format_label(label: str) -> str:
    match targets.current_target.os:
        case "darwin":
            return f"_{label}"
        case _:
            return label


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


@dataclass
class LabelDef(Statement):
    def __init__(self, name: str, comment: str = None):
        self.name = name
        self.comment = comment

    def gas(self) -> str:
        line = f"{format_label(self.name)}:"
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
