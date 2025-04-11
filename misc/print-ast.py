#!/usr/bin/env python3

# Print out the AST of a C file.
# This is a demonstration of patching in an alternative Node.show() method.

import sys
#sys.path.insert(0, '/Users/cell/github/eliben/pycparser/')
#sys.path.insert(0, '/home/cell/github/eliben/pycparser/')
from pycparser import parse_file
from pycparser.c_ast import *

def show(self, buf=sys.stdout, indent=4, showcoord=True, _my_node_name=None, _lead='', _lastcoord=None, _depth=1):
    """ Pretty print the Node and all its attributes and
        children (recursively) to a buffer.

        buf:
            Open IO buffer into which the Node is printed.

        indent:
            The number of spaces to indent at each level.
        
        showcoord:
            Do you want the coordinates of each Node to be
            displayed.

        returns the number of parens which need to be closed by the parent.
    """
    # print the node type
    s = _lead
    if _my_node_name:
        s += "%s = " % _my_node_name
    s += "%s(" % (self.__class__.__name__)
    if showcoord and self.coord:
        # only print the line number if it has changed
        coord_did_change = _lastcoord is None \
            or self.coord.file != _lastcoord.file \
            or self.coord.line != _lastcoord.line
        if coord_did_change:
            s += '  // '
            if self.coord.file:
                s += '%s ' % self.coord.file
            s += 'line %s' % self.coord.line
            _lastcoord = self.coord
    buf.write(s + '\n')

    # use dots to give visual column cues
    lead2 = _lead + '.' + (' ' * (indent-1))

    # print the attributes
    if self.attr_names:
        for name, value in [(n, getattr(self,n)) for n in self.attr_names]:
            # suppress empty fields
            if value is None:
                continue
            if hasattr(value, '__len__') and len(value) == 0:
                continue
            buf.write(lead2 + "%s = %s\n" % (name, value))

    # print the children.
    unclosed_depth = 0
    for i, (child_name, child) in enumerate(self.children()):
        is_last = i+1 == len(self.children())
        unclosed_depth = child.show(
            buf,
            indent=indent,
            _my_node_name=child_name,
            _lead=lead2,
            _lastcoord=_lastcoord,
            _depth=_depth+1
        )
        if not is_last:
            dot_spaces = ('.' + ' '*(indent-1))
            spaces_cparen = ')' + ' ' * (indent-1)
            buf.write((dot_spaces * _depth) + (spaces_cparen * unclosed_depth) + '\n')
        else:
            # let the caller close out parens after the last child
            pass

    if _depth == 1:
        # this is the final paren closing
        unclosed_depth += 1
        spaces_cparen = ')' + ' ' * (indent-1)
        buf.write((spaces_cparen * unclosed_depth) + '\n')
    else:
        # let the caller close out parens after the last child
        return unclosed_depth + 1


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

    #ast.show(attrnames=True, showemptyattrs=False, nodenames=False, showcoord=False)

    # patch in our custom show
    Node.show = show
    ast.show()
