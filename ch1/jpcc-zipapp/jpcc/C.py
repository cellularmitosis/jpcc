# A parser for the subset of C described in chapter 1 of
# "Writing a C Compiler" by Nora Sandler.

# This file translates a pycparser C AST into a chapter 1 C AST.

import sys
from dataclasses import dataclass

try:
    import pycparser
except:
    sys.stderr.write("Error: missing Python module 'pycparser'.\n")
    sys.stderr.write("Please pip3 install pycparser.\n")
    sys.exit(1)


# ASDL for the subset of C from chapter 1:
#     program = Program(funcdef)
#     funcdef = Function(identifier name, statement body)
#   statement = Return(expr)
#        expr = Constant(int)

# EBNF for the subset of C from chapter 1:
#      <program> ::= <function>
#     <function> ::= "int" <identifier> "(" "void" ")" "{" <statement> "}"
#    <statement> ::= "return" <expr> ";"
#         <expr> ::= <int>
#   <identifier> ::= ? An identifier token ?
#          <int> ::= ? A constant token ?

class C_AST: pass


@dataclass
class Constant(C_AST):
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


# return_2.c:
#   int main(void) {
#       return 2;
#   }

# pycparser AST for return_2.c:
#   FileAST(
#   .   ext[0] = FuncDef(  // line 1
#   .   .   decl = Decl(
#   .   .   .   name = main
#   .   .   .   type = FuncDecl(
#   .   .   .   .   args = ParamList(  // line 0
#   .   .   .   .   .   params[0] = Typename(
#   .   .   .   .   .   .   type = TypeDecl(
#   .   .   .   .   .   .   .   type = IdentifierType(  // line 1
#   .   .   .   .   .   .   .   .   names = ['void']
#   .   .   .   .   )   )   )   )   
#   .   .   .   .   type = TypeDecl(
#   .   .   .   .   .   declname = main
#   .   .   .   .   .   type = IdentifierType(
#   .   .   .   .   .   .   names = ['int']
#   .   .   )   )   )   )   
#   .   .   body = Compound(
#   .   .   .   block_items[0] = Return(  // line 2
#   .   .   .   .   expr = Constant(
#   .   .   .   .   .   type = int
#   .   .   .   .   .   value = 2
#   )   )   )   )   )   

# ch1 AST for return_2.c:
#   Program(
#       Function(
#           name="main",
#           body=Return(
#               Constant(2)
#           )
#       )
#   )


def parse_pycp_ast(fname: str) -> C_AST:
    "Use pycparser to parse a C file, returning the AST"
    c_ast = pycparser.parse_file(fname, use_cpp=False)
    return c_ast


def pycp_ast_to_ch1_ast(c_ast: pycparser.c_ast.Node) -> C_AST:
    "Translate a pycparser AST into a chapter 1 AST"
    assert isinstance(c_ast, pycparser.c_ast.FileAST)
    funcdef = c_ast.ext[0]
    assert isinstance(funcdef, pycparser.c_ast.FuncDef)
    assert funcdef.decl.name == 'main'
    body = funcdef.body
    assert isinstance(body, pycparser.c_ast.Compound)
    assert len(body.block_items) == 1
    ret = body.block_items[0]
    assert isinstance(ret, pycparser.c_ast.Return)
    constant = ret.expr
    assert isinstance(constant, pycparser.c_ast.Constant)

    ch1_ast = Program(
        Function(
            name = funcdef.decl.name,
            body = Return(
                Constant(constant.value)
            )
        )
    )

    return ch1_ast


def parse(fname: str) -> C_AST:
    "Parse a C file and return the chapter 1 AST"
    pycp_ast = parse_pycp_ast(fname)
    ch1_ast = pycp_ast_to_ch1_ast(pycp_ast)
    return ch1_ast
