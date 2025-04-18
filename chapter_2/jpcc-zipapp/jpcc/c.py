# This file translates a pycparser C AST into a chapter 2 C AST.
# See "Writing a C Compiler" by Nora Sandler.

import sys
from dataclasses import dataclass

try:
    import pycparser.c_ast
except:
    sys.stderr.write("Error: missing Python module 'pycparser'.\n")
    sys.stderr.write("Please pip3 install pycparser.\n")
    sys.exit(1)


# Nora Sandler's ASDL for the subset of C from chapter 2:
#     program = Program(funcdef)
#     funcdef = Function(identifier name, statement body)
#   statement = Return(expr)
#        expr = Constant(int) | Unary(unaryop, expr)
#     unaryop = Complement | Negate

# I use a slightly modified grammar and syntax:
#           C_AST > Program | Function | Statement | Expression | UnaryOperator
#         Program : Program(funcdef: Function)
#        Function : Function(name: str, body: Statement)
#       Statement > Return
#          Return : Return(expr: Expression)
#      Expression > Constant | Unary
#        Constant = Constant(value: int)
#           Unary : Unary(op: UnaryOperator, expr: Expression)
#   UnaryOperator > Complement | Negate


class C_AST: pass


class Expression(C_AST): pass


class UnaryOperator(C_AST): pass
class Complement(UnaryOperator): pass
class Negate(UnaryOperator): pass


@dataclass
class Unary(Expression):
    op: UnaryOperator
    expr: Expression


@dataclass
class Constant(Expression):
    value: int


class Statement(C_AST): pass


@dataclass
class Return(Statement):
    expr: Constant


@dataclass
class Function(C_AST):
    name: str
    body: Return


@dataclass
class Program(C_AST):
    funcdef: Function
