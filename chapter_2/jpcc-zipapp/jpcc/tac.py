# This file translates chapter 2 C AST into a chapter 2 TAC AST.
# See "Writing a C Compiler" by Nora Sandler.

from dataclasses import dataclass


# Nora Sandler's ASDL for TAC from chapter 2:
#       program = Program(funcdef)
#       funcdef = Function(identifier name, instruction* body)
#   instruction = Return(val) | Unary(unaryop, val src, val dst)
#           val = Constant(int) | Var(identifier)
#       unaryop = Complement | Negate

# I use a slightly modified grammar and syntax:
#         TAC_AST > Program | Function | Instruction | Operand | UnaryOperator
#         Program : Program(funcdef: Function)
#        Function : Function(name: str, body: list[Instruction])
#     Instruction > Unary | Return
#         Operand > Constant | Var
#        Constant : Constant(value: int)
#             Var : Var(name: str)
#           Unary : Unary(op: UnaryOperator, src: Operand, dst: Operand)
#          Return : Return(val: Operand)
#   UnaryOperator > Complement | Negate


class TAC_AST: pass


class Operand(TAC_AST):  pass


@dataclass
class Constant(Operand):
    value: int


@dataclass
class Var(Operand):
    name: str


class Instruction(TAC_AST): pass


class UnaryOperator(TAC_AST): pass
class Complement(UnaryOperator): pass
class Negate(UnaryOperator): pass


@dataclass
class Unary(Instruction):
    op: UnaryOperator
    src: Operand
    dst: Operand


@dataclass
class Return(Instruction):
    val: Operand


@dataclass
class Function(TAC_AST):
    name: str
    body: list[Instruction]


@dataclass
class Program(TAC_AST):
    funcdef: Function
