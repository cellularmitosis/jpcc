#!/usr/bin/env python3

# dump a pycparser AST as symbolic expressions.

import sys
#sys.path.insert(0, '/Users/cell/github/eliben/pycparser/')
#sys.path.insert(0, '/home/cell/github/eliben/pycparser/')
from pycparser import parse_file
from pycparser.c_ast import *


def make_exprs(self):
    "serialize the AST as symbolic expressions (lists)"
    items = [self.__class__.__name__]
    # add the attributes
    if self.attr_names:
        for name, value in [(n, getattr(self,n)) for n in self.attr_names]:
            # suppress empty fields
            if value is None:
                continue
            if hasattr(value, '__len__') and len(value) == 0:
                continue
            items.append(name)
            if isinstance(value, list):
                items.append(["list", *value])
            else:
                items.append(str(value))
            continue
    # add the children
    chdn = self.children()
    i = 0
    while i < len(chdn):
        (name, child) = chdn[i]
        if name.endswith("[0]"):
            # this is the start of a 'multiname', e.g. 'block_items[0]'
            multiname = name.split('[')[0]
            multiitems = []
            while i < len(chdn) and chdn[i][0].startswith("%s[" % multiname):
                multiitems.append(chdn[i][1].make_exprs())
                i += 1
            items.append(multiname)
            items.append(["list", *multiitems])
            continue
        else:
            items.append(name)
            items.append(child.make_exprs())
            i += 1
            continue
    return items


Node.make_exprs = make_exprs


def format_exprs(exprs):
    "format the symbolic expressions as a string"
    strs = []
    for subexpr in exprs:
        if isinstance(subexpr, str):
            strs.append(subexpr)
        else:
            strs.append(format_exprs(subexpr))
    text = "(%s)" % " ".join(strs)
    return text


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.stderr.write("Error: no filename given.\n")
        sys.exit(1)

    fname = sys.argv[1]
    if sys.platform == "darwin":
        cpp="/usr/bin/clang"
    else:
        cpp="/usr/bin/gcc"
    ast = parse_file(fname, use_cpp=True, cpp_path=cpp, cpp_args=['-E','-P'])

    text = format_exprs(ast.make_exprs())
    print(text)
