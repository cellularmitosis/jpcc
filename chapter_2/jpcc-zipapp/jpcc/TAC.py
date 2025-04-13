# This file translates chapter 2 C AST into a chapter 2 TAC AST.
# See "Writing a C Compiler" by Nora Sandler.


# ASDL for TAC from chapter 2:
#     program = Program(funcdef)
#     funcdef = Function(identifier name, instruction* body)
# instruction = Return(val) | Unary(unaryop, val src, val dst)
#         val = Constant(int) | Var(identifier)
#     unaryop = Complement | Negate
