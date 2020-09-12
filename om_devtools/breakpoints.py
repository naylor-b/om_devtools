
import sys
import ast


class FuncInfo(object):
    def __init__(self, filepath, funcpath, lineno):
        self.filepath = filepath
        self.funcpath = funcpath
        self.lineno = lineno
        self.start = None
        self.end = None
        self.returns = []
        self.raises = []

    def __str__(self):
        return f"{self.filepath}:{self.lineno} - {self.funcpath}:{self.start}:{self.end}"


class BreakpointLocator(ast.NodeVisitor):
    """
    An ast.NodeVisitor that records location info for potential breakpoints.
    """

    def __init__(self):
        super(BreakpointLocator, self).__init__()
        self.func_info = {}
        self.stack = []
        self.fstack = []
        self.seen = set()
        self.filepath = None

    # def generic_visit(self, node):
    #     if self.fstack:
    #         if hasattr(node, 'lineno'):
    #             # update the last line of every funct on the stack
    #             for f in self.fstack:
    #                 f[1] = node.lineno

    #     super(BreakpointLocator, self).generic_visit(node)

    def visit_ClassDef(self, node):
        self.stack.append(node.name)
        for bnode in node.body:
            self.visit(bnode)
        self.stack.pop()

    def visit_FunctionDef(self, node):
        self.stack.append(node.name)
        fpath = '.'.join(self.stack)

        self.func_info[fpath] = finfo = FuncInfo(self.filepath, fpath, node.lineno)
        self.fstack.append(finfo)

        start = None
        for i, bnode in enumerate(node.body):
            if start is None:
                # skip docstring
                if isinstance(bnode, ast.Expr) and isinstance(bnode.value, ast.Str):
                    #print("Expr: ", bnode.value.n, bnode.value.s)
                    continue
                start = finfo.start = bnode.lineno
                # print(fpath, "start: ", bnode.lineno, type(bnode).__name__)
            self.visit(bnode)
        finfo.end = bnode.lineno

        self.stack.pop()
        self.fstack.pop()

    def visit_Return(self, node):
        self.fstack[-1].returns.append(node.lineno)

    def visit_Raise(self, node):
        self.fstack[-1].raises.append(node.lineno)

    def process_class(self, klass):
        try:
            mod = sys.modules[klass.__module__]
        except:
            print(f"skipping class {klass.__name__}")

        self.process_file(mod.__file__)

    def process_file(self, fname):
        if fname in self.seen:
            return

        self.seen.add(fname)
        self.filepath = fname

        with open(fname, 'r') as f:
            self.stack = []
            self.fstack = []
            node = ast.parse(f.read(), filename=fname, mode='exec')
            self.visit(node)

        self.filepath = None

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
