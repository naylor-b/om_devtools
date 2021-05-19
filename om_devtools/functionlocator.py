
import sys
import ast


class FunctionLocator(ast.NodeVisitor):
    """
    An ast.NodeVisitor that records starting and ending lines of functions.
    """

    def __init__(self):
        super(FunctionLocator, self).__init__()
        self.funct_ranges = {}
        self.stack = []
        self.fstack = []
        self.seen = set()

    def generic_visit(self, node):
        if self.fstack:
            if hasattr(node, 'lineno'):
                # update the last line of every funct on the stack
                for f in self.fstack:
                    f[1] = node.lineno

        super(FunctionLocator, self).generic_visit(node)

    def visit_ClassDef(self, node):
        self.stack.append(node.name)
        for bnode in node.body:
            self.visit(bnode)
        self.stack.pop()

    def visit_FunctionDef(self, node):
        if self.stack:
            parent = '.'.join(self.stack) + '.'
        else:
            parent = ''
        fpath = parent + node.name

        finfo = [fpath, node.lineno]
        self.funct_ranges[node.lineno] = finfo

        self.stack.append(node.name)
        self.fstack.append(finfo)
        for bnode in node.body:
            self.visit(bnode)
        self.stack.pop()
        self.fstack.pop()

    def process_file(self, fname):
        if fname in self.seen:
            return

        self.seen.add(fname)

        with open(fname, 'r') as f:
            self.stack = []
            self.fstack = []
            node = ast.parse(f.read(), filename=fname, mode='exec')
            self.visit(node)

    def get_funct_last_line(self, lineno):
        """
        Given a starting line number, return the function name and ending line number.
        """
        try:
            return self.funct_ranges[lineno]
        except KeyError:
            return (None, None)


if __name__ == '__main__':
    import pprint
    floc = FunctionLocator()
    floc.process_file(sys.argv[1])
    pprint.pprint(floc.funct_ranges)
