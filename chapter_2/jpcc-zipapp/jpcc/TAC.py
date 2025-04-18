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


from jpcc import C


@dataclass
class State:
    nextTmp: int = 0

g_state = State()

def _next_tmp(state=g_state) -> str:
    "Claim the next tmp number and return a tmp Var."
    varname = f"tmp{state.nextTmp}"
    state.nextTmp += 1
    return Var(varname)


def c_to_tac(c_ast: C.Program) -> Program:
    "Translate from a C AST to a TAC AST."
    return _translate_Program(c_ast)


def _translate_Program(c_ast: C.Program) -> Program:
    assert isinstance(c_ast, C.Program)
    funcdef = _translate_Function(c_ast.funcdef)
    return Program(funcdef)


def _translate_Function(c_ast: C.Function) -> Function:
    assert isinstance(c_ast, C.Function)
    name = c_ast.name
    body = _translate_Statement(c_ast.body)
    return Function(name, body)


def _translate_Statement(c_ast: C.Statement) -> list[Instruction]:
    assert isinstance(c_ast, C.Statement)
    assert isinstance(c_ast, C.Return)
    instructions = []
    match c_ast:
        case C.Return(C.Constant() as con):
            instructions += [Return(Constant(con.value))]
        case C.Return(C.Unary() as un):
            (expr_instructions, last_tmp) = _translate_Expression(un)
            instructions += [*expr_instructions, Return(last_tmp)]
        case _:
            raise Exception("Unreachable")
    return instructions


def _translate_UnaryOperator(c_ast: C.UnaryOperator) -> UnaryOperator:
    assert isinstance(c_ast, C.UnaryOperator)
    match c_ast:
        case C.Complement(): return Complement()
        case C.Negate(): return Negate()
        case _: raise Exception("Unreachable")


def _translate_Constant(c_ast: C.Constant) -> UnaryOperator:
    assert isinstance(c_ast, C.Constant)
    return Constant(c_ast.value)


def _translate_Expression(c_ast: C.Expression) -> tuple[list[Instruction],str]:
    "Translate a C.Expression, returning a list of expressions and the name of the last temporary."
    match c_ast:
        case C.Unary(op, C.Constant() as con):
            dst = _next_tmp()
            instructions = [Unary(
                op = _translate_UnaryOperator(op),
                src = _translate_Constant(con),
                dst = dst,
            )]
            return (instructions, dst)
        case C.Unary(op, C.Unary() as inner_un):
            (instructions, inner_tmp) = _translate_Expression(inner_un)
            dst = _next_tmp()
            instructions += [Unary(
                op = _translate_UnaryOperator(op),
                src = inner_tmp,
                dst = dst,
            )]
            return (instructions, dst)
        case _:
            raise Exception(f"Unreachable")
