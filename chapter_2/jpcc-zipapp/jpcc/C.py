# This file translates a pycparser C AST into a chapter 2 C AST.
# See "Writing a C Compiler" by Nora Sandler.

import sys
from dataclasses import dataclass

import pycparser.c_ast

try:
    import pycparser
except:
    sys.stderr.write("Error: missing Python module 'pycparser'.\n")
    sys.stderr.write("Please pip3 install pycparser.\n")
    sys.exit(1)


# ASDL for the subset of C from chapter 2:
#     program = Program(funcdef)
#     funcdef = Function(identifier name, statement body)
#   statement = Return(expr)
#        expr = Constant(int) | Unary(unaryop, expr)
#     unaryop = Complement | Negate


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


# return-comp-neg-2.c 
#   int main(void) {
#       return ~(-2);
#   }

# pycparser AST for return-comp-neg-2.c:
# FileAST(
# .   ext[0] = FuncDef(  // line 1
# .   .   decl = Decl(
# .   .   .   name = main
# .   .   .   type = FuncDecl(
# .   .   .   .   args = ParamList(  // line 0
# .   .   .   .   .   params[0] = Typename(
# .   .   .   .   .   .   type = TypeDecl(
# .   .   .   .   .   .   .   type = IdentifierType(  // line 1
# .   .   .   .   .   .   .   .   names = ['void']
# .   .   .   .   )   )   )   )   
# .   .   .   .   type = TypeDecl(
# .   .   .   .   .   declname = main
# .   .   .   .   .   type = IdentifierType(
# .   .   .   .   .   .   names = ['int']
# .   .   )   )   )   )   
# .   .   body = Compound(
# .   .   .   block_items[0] = Return(  // line 2
# .   .   .   .   expr = UnaryOp(
# .   .   .   .   .   op = ~
# .   .   .   .   .   expr = UnaryOp(
# .   .   .   .   .   .   op = -
# .   .   .   .   .   .   expr = Constant(
# .   .   .   .   .   .   .   type = int
# .   .   .   .   .   .   .   value = 2
# )   )   )   )   )   )   )   

# DELETEME
# ASDL for the subset of C from chapter 2:
#     program = Program(funcdef)
#     funcdef = Function(identifier name, statement body)
#   statement = Return(expr)
#        expr = Constant(int) | Unary(unaryop, expr)
#     unaryop = Complement | Negate

# chapter 2 AST for return-comp-neg-2.c 
#FIXME



def _c_pycp_ast(fname: str) -> C_AST:
    "Use pycparser to parse a C file, returning the AST"
    c_ast = pycparser.parse_file(fname, use_cpp=False)
    return c_ast


def _pycp_ast_to_ch2_ast(c_ast: pycparser.c_ast.Node) -> C_AST:
    "Translate a pycparser AST into a chapter 2 AST"
    return _translate_FileAST(c_ast)


def _translate_FileAST(c_ast: pycparser.c_ast.FileAST) -> Program:
    assert isinstance(c_ast, pycparser.c_ast.FileAST)
    return Program(_translate_FuncDef(c_ast.ext[0]))


def _translate_FuncDef(c_ast: pycparser.c_ast.FuncDef) -> Function:
    assert isinstance(c_ast, pycparser.c_ast.FuncDef)
    assert isinstance(c_ast.body, pycparser.c_ast.Compound)
    assert len(c_ast.body.block_items) == 1
    ret = _translate_Return(c_ast.body.block_items[0])
    return Function(name=c_ast.decl.name, body=ret)


def _translate_expr(c_ast: pycparser.c_ast.Node) -> C_AST:
    match type(c_ast):
        case pycparser.c_ast.UnaryOp:
            return _translate_UnaryOp(c_ast)
        case pycparser.c_ast.Constant:
            return _translate_Constant(c_ast)
        case _:
            raise Exception(f"Unsupported expression {c_ast}")


def _translate_UnaryOp(c_ast: pycparser.c_ast.UnaryOp) -> Unary:
    assert isinstance(c_ast, pycparser.c_ast.UnaryOp)
    match c_ast.op:
        case "-":
            op = Negate()
        case "~":
            op = Complement()
        case _:
            raise Exception(f"Unsupported UnaryOp '{c_ast.op}'")
    return Unary(op, _translate_expr(c_ast.expr))


def _translate_Return(c_ast: pycparser.c_ast.Return) -> Return:
    assert isinstance(c_ast, pycparser.c_ast.Return)
    return Return(_translate_expr(c_ast.expr))


def _translate_Constant(c_ast: pycparser.c_ast.Constant) -> Constant:
    assert isinstance(c_ast, pycparser.c_ast.Constant)
    assert c_ast.type == "int"
    value = int(c_ast.value)
    return Constant(value)


def parse(fname: str) -> C_AST:
    "Parse a C file and return the chapter 2 AST"
    pycp_ast = _c_pycp_ast(fname)
    ch2_ast = _pycp_ast_to_ch2_ast(pycp_ast)
    return ch2_ast
