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

# I use a slightly modified syntax and grammar:
#        ASM_AST > Program | Function | Instruction | Operand | Identifier
#        Program : Program(funcdef: Function)
#       Function : Function(name: Identifier, instructions: list[Instruction])
#    Instruction : Instruction(comment: str)
#    Instruction > Instruction0 | Instruction1 | Instruction2 | AllocateStack
#   Instruction0 > Ret
#   Instruction1 : Instruction1(srcdst: Operand)
#   Instruction1 > Neg | Not
#   Instruction2 : Instruction2(src: Operand, dst: Operand)
#   Instruction2 > Movl
#  AllocateStack : AllocateStack(bytes: int)
#        Operand > Imm | Register | Pseudo | Stack
#            Imm : Imm(value: int)
#       Register > RAX | RBX | ...
#         Pseudo : Pseudo(name: Identifier)
#          Stack : Stack(offset: int)
#     Identifier : Identifier(value: str)


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
#       AllocateStack
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
    "An instruction of artiy 0."
    def gas(self) -> str:
        op = self.__class__.__name__.lower()
        line = f"\t{op}"
        line = add_comment(line, self.get_comment())
        return line


class Instruction1(Instruction):
    "An instruction of artiy 1."
    def __init__(self, *, srcdst: Operand, comment: str = None):
        self.srcdst = srcdst
        self.comment = comment

    def gas(self) -> str:
        op = self.__class__.__name__.lower()
        srcdst_str = self.srcdst.gas()
        line = f"\t{op} {srcdst_str}"
        line = add_comment(line, self.get_comment())
        return line


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
        line = add_comment(line, self.get_comment())
        return line


class Ret(Instruction0):
    def get_comment(self) -> str:
        default = f"Jump to the return address."
        return coalesce(super().get_comment(), default)


class Neg(Instruction1):
    def get_comment(self) -> str:
        default = f"Negate the value."
        return coalesce(super().get_comment(), default)


class Not(Instruction1):
    def get_comment(self) -> str:
        default = f"Flip all of the bits."
        return coalesce(super().get_comment(), default)


class Movl(Instruction2):
    def get_comment(self) -> str:
        default = f"Copy {self.src.gas()} to {self.dst.gas()}."
        return coalesce(super().get_comment(), default)


class AllocateStack(Instruction):
    "Increase the stack pointer by the given number of bytes."
    def __init__(self, *, bytes: int):
        self.bytes = bytes

    def gas(self) -> str:
        op = self.__class__.__name__.lower()
        srcdst_str = self.srcdst.gas()
        line = f"\t{op} {srcdst_str}"
        line = add_comment(line, self.get_comment())
        return line


    def get_comment(self) -> str:
        default = f"Copy {self.src.gas()} to {self.dst.gas()}."
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


from jpcc import TAC

def gen_Program(tac_ast: TAC.Program) -> Program:
    "Generate assembly for a TAC.Program"

    def gen_Function(tac_fn_ast: TAC.Function) -> Function:
        "Generate assembly for a TAC.Function"
        asm_instructions = [AllocateStack()]
        assert(isinstance(tac_fn_ast, TAC.Function))
        assert(isinstance(tac_fn_ast.body, list))
        for tac_inst in tac_fn_ast.body:
            match tac_inst:
                case TAC.Unary():
                case TAC.Return():
                case _:
                    raise Exception(f"Unreachable")
        tac_ret_ast = tac_fn_ast.body
        tac_expr_ast = tac_ret_ast.expr
        assert(isinstance(tac_expr_ast, TAC.Constant))
        asm_ast = Function(
            name = tac_fn_ast.name,
            instructions = [
                Movl(
                    src = Imm(tac_expr_ast.value),
                    dst = EAX(),
                    comment = f"Return value = {tac_expr_ast.value}."
                ),
                Ret(),
            ]
        )
        return asm_ast

    assert(isinstance(tac_ast, TAC.Program))
    asm_ast = Program(
        funcdef = gen_Function(tac_ast.funcdef)
    )
    return asm_ast
