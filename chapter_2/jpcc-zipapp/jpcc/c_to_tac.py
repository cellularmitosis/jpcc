# This file translates chapter 2 C AST into a chapter 2 TAC AST.
# See "Writing a C Compiler" by Nora Sandler.

from dataclasses import dataclass

# So for return-comp-neg-2.c:
#
#   int main(void) {
#       return ~(-2);
#   }
#
# we will translate this line:
#
#   return ~(-2)
#
# into these instruction:
#
#   tac0 = Negate(2);
#   tac1 = Complement(tac0);
#   return tmp1;
#
# Overall, we will perform this AST transform:
#
# C_AST:                   | TAC_AST:
# ------                   | --------
# (Program                 | (Program
#   funcdef (Function      |   funcdef (Function
#     name "main"          |     name "main"
#     body (Return         |     body (list
#       expr (Unary        |       (Unary
#         op (Complement)  |         op Negate
#         expr (Unary      |         src (Constant 2)
#           op (Negate)    |         dst (Var "tmp0")
#           expr (Constant |       )
#             value 2      |       (Unary
#           )              |         op Complement
#         )                |         src (Var "tmp0")
#       )                  |         dst (Var "tmp1")
#     )                    |       )
#   )                      |       (Return
# )                        |         (Var "tmp1")
#                          |       )
#                          |     )
#                          |   )
#                          | )

# A few examples focusing on just the Return statement:

# This C:
#   return 2;
# becomes this TAC-like C:
#   return 2;
# Alternatively, this C AST:
#   Return(2)
# becomes this TAC AST:
#   Return(2)

# C:
#   return ~(2);
# TAC-C:
#   int tmp0 = ~(2);
#   return tmp0;
# C AST:
#   Return(Unary(Complement, Constant(2)))
# TAC:
#   Unary(Complement, Constant(2), Var("tmp0"))
#   Return("tmp0")

# C:
#   return -(~(2));
# TAC-C:
#   int tmp0 = ~(2);
#   int tmp1 = -(tmp0);
#   return tmp1;
# C AST:
#   Return(Unary(Negate, Unary(Complement, Constant(2))))
# TAC:
#   Unary(Complement, Constant(2), Var("tmp0"))
#   Unary(Negate, Var("tmp0"), Var("tmp1"))
#   Return("tmp1")

# C:
#   return ~(-(~(2)));
# TAC-C:
#   int tmp0 = ~(2);
#   int tmp1 = -(tmp0);
#   int tmp2 = ~(tmp1);
#   return tmp2;
# C AST:
#   Return(Unary(Complement, Unary(Negate, Unary(Complement, Constant(2)))))
# TAC:
#   Unary(Complement, Constant(2), Var("tmp0"))
#   Unary(Negate, Var("tmp0"), Var("tmp1"))
#   Unary(Complement, Var("tmp1"), Var("tmp2"))
#   Return("tmp2")


from jpcc import tac
from jpcc import c


@dataclass
class State:
    nextTmp: int = 0

g_state = State()

def _next_tmp(state=g_state) -> tac.Var:
    "Claim the next tmp number and return a tmp Var."
    varname = f"tmp{state.nextTmp}"
    state.nextTmp += 1
    return tac.Var(varname)


def c_to_tac(c_ast: c.Program) -> tac.Program:
    "Translate from a C AST to a TAC AST."
    return _translate_Program(c_ast)


def _translate_Program(c_ast: c.Program) -> tac.Program:
    assert isinstance(c_ast, c.Program)
    funcdef = _translate_Function(c_ast.funcdef)
    return tac.Program(funcdef)


def _translate_Function(c_ast: c.Function) -> tac.Function:
    assert isinstance(c_ast, c.Function)
    name = c_ast.name
    body = _translate_Statement(c_ast.body)
    return tac.Function(name, body)


def _translate_Statement(c_ast: c.Statement) -> list[tac.Instruction]:
    assert isinstance(c_ast, c.Statement)
    assert isinstance(c_ast, c.Return)
    instructions = []
    match c_ast:
        case c.Return(c.Constant() as con):
            instructions += [tac.Return(tac.Constant(con.value))]
        case c.Return(c.Unary() as un):
            (expr_instructions, last_tmp) = _translate_Expression(un)
            instructions += [*expr_instructions, tac.Return(last_tmp)]
        case _:
            raise Exception("Unreachable")
    return instructions


def _translate_UnaryOperator(c_ast: c.UnaryOperator) -> tac.UnaryOperator:
    assert isinstance(c_ast, c.UnaryOperator)
    match c_ast:
        case c.Complement(): return tac.Complement()
        case c.Negate(): return tac.Negate()
        case _: raise Exception("Unreachable")


def _translate_Constant(c_ast: c.Constant) -> tac.UnaryOperator:
    assert isinstance(c_ast, c.Constant)
    return tac.Constant(c_ast.value)


def _translate_Expression(c_ast: c.Expression) -> tuple[list[tac.Instruction],str]:
    "Translate a c.Expression, returning a list of expressions and the name of the last temporary."
    match c_ast:
        case c.Unary(op, c.Constant() as con):
            dst = _next_tmp()
            instructions = [tac.Unary(
                op = _translate_UnaryOperator(op),
                src = _translate_Constant(con),
                dst = dst,
            )]
            return (instructions, dst)
        case c.Unary(op, c.Unary() as inner_un):
            (instructions, inner_tmp) = _translate_Expression(inner_un)
            dst = _next_tmp()
            instructions += [tac.Unary(
                op = _translate_UnaryOperator(op),
                src = inner_tmp,
                dst = dst,
            )]
            return (instructions, dst)
        case _:
            raise Exception(f"Unreachable")
