# This file translates a chapter 1 C AST into a ASM AST and emits GAS-syntax assembly.

from __future__ import annotations
from dataclasses import dataclass

from jpcc import Targets


# Nora Sandler's ASDL for the subset of ASM from chapter 1:
#       program = Program(funcdef)
#       funcdef = Function(identifier name, instruction* instructions)
#   instruction = Mov(operand src, operand dst) | Ret
#       operand = Imm(int) | Register

# I use a slightly modified syntax and grammar:
#        ASM_AST > Program | Function | Instruction | Operand | Identifier
#        Program : Program(funcdef: Function)
#       Function : Function(name: Identifier, instructions: list[Instruction])
#    Instruction : Instruction(comment: str)
#    Instruction > Instruction0 | Instruction2
#   Instruction0 > Ret
#   Instruction2 : Instruction2(src: Operand, dst: Operand)
#   Instruction2 > Movl
#        Operand > Imm | Register
#            Imm : Imm(value: int)
#       Register > RAX | RBX | ...
#     Identifier : Identifier(value: str)


# So for 'return-2.c':
# 
#   int main(void) {
#       return 2;
#   }
#
# we want to make the following translation:
#   C AST:             |  ASM AST:
#   ------             |  --------
#   Program(           |  Program(
#     Function(        |    Function(
#       name="main",   |      name=Identifier("main"),
#       body=Return(   |      instructions=[
#         Constant(2)  |        Mov(Imm(2), RAX),
#       )              |        Ret()
#     )                |      ]
#   )                  |    )
#                      |  )

# And then emit:
#           .globl main
#   main:
#           movl $2, %eax
#           ret

# Note: 'GAS' (GNU as) syntax is:
#   instruction source, destination
# e.g. this copies %rsp into %rbp:
#   movl %rsp, %rbp


tab_width = 8  # the visible width of a rendered tab character
comment_col = 32  # the column at which comments should start.


def coalesce(x, default_value):
    "Return the default value if x is None"
    return x if x is not None else default_value


def vlen(s: str) -> int:
    "Return the visible length of a string, assuming tabs are 8 wide"
    return len(s) + (s.count('\t') * (tab_width - 1))


def add_comment(stmt: str, comment: str) -> str:
    "Add a comment to an ASM statement."
    if stmt is None:
        stmt = ""
    if comment is None:
        return stmt
    pad = (comment_col - vlen(stmt)) * " "
    # Note: '#' is the standard comment character for x86_64, but it appears
    # that it does not work after a directive, e.g. '.globl main # comment'.
    # However, '/* comment */' appears to work everywhere.
    line = f"{stmt}{pad}/* {comment} */"
    return line


class ASM_AST: pass


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


@dataclass
class Imm(Operand):
    value: int
    def gas(self) -> str:
        return f"${self.value}"


@dataclass
class Instruction(ASM_AST):
    comment: str = None
    def get_comment(self) -> str:
        "This getter allows instructions to provide a default comment."
        return self.comment


class Instruction0(Instruction):
    def gas(self) -> str:
        op = self.__class__.__name__.lower()
        line = f"\t{op}"
        line = add_comment(line, self.get_comment())
        return line


class Instruction2(Instruction):
    def __init__(self, *, src: Operand, dst: Operand, comment: str = None):
        self.src = src
        self.dst = dst
        self.comment = comment

    def gas(self) -> str:
        op = self.__class__.__name__.lower()
        src_str = self.src.gas()
        dst_str = self.dst.gas()
        line = f"\t{op} {src_str}, {dst_str}"
        line = add_comment(line, self.get_comment())
        return line


class Movl(Instruction2):
    def get_comment(self) -> str:
        default = f"Copy {self.src.gas()} to {self.dst.gas()}."
        return coalesce(super().get_comment(), default)


class Ret(Instruction0):
    def get_comment(self) -> str:
        default = f"Jump to the return address."
        return coalesce(super().get_comment(), default)


@dataclass
class Identifier(ASM_AST):
    value: str


@dataclass
class Function(ASM_AST):
    name: Identifier
    instructions: list[Instruction]

    def gas(self) -> str:
        def make_label(fn_name: str) -> str:
            match Targets.current_target.os:
                case "darwin":
                    return f"_{fn_name}"
                case _:
                    return fn_name
        lines = []
        label = make_label(self.name)
        globl_stmt = add_comment(
            f"\t.globl {label}",
            f"Make {label} globally visible."
        )
        lines.append(globl_stmt)
        label_stmt = add_comment(
            f"{label}:",
            f"Begin function {self.name}."
        )
        lines.append(label_stmt)
        for instruction in self.instructions:
            lines.append(instruction.gas())
        asm_text = '\n'.join(lines) + '\n'
        return asm_text


@dataclass
class Program(ASM_AST):
    funcdef: Function
    def gas(self):
        return self.funcdef.gas()


from jpcc import C

def gen_Program(c_ast: C.Program) -> Program:
    "Generate assembly for a C.Program"

    def gen_Function(c_fn_ast: C.Function) -> Function:
        "Generate assembly for a C.Function"
        assert(isinstance(c_fn_ast, C.Function))
        c_ret_ast = c_fn_ast.body
        assert(isinstance(c_ret_ast, C.Return))
        c_expr_ast = c_ret_ast.expr
        assert(isinstance(c_expr_ast, C.Constant))
        asm_ast = Function(
            name = c_fn_ast.name,
            instructions = [
                Movl(
                    src = Imm(c_expr_ast.value),
                    dst = EAX(),
                    comment = f"Return value = {c_expr_ast.value}."
                ),
                Ret(),
            ]
        )
        return asm_ast

    assert(isinstance(c_ast, C.Program))
    c_fn_ast = c_ast.funcdef
    asm_ast = Program(
        gen_Function(c_fn_ast)
    )
    return asm_ast
