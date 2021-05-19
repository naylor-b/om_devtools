
import sys
import ast
import inspect
import weakref
from fnmatch import fnmatchcase
from collections import defaultdict, deque, namedtuple

from openmdao.core.problem import Problem
from openmdao.core.system import System


class BreakInfo(object):
    __slots__ = ['id', 'active', 'fpath', 'line', 'conditions']

    def __init__(self, ident, fpath, line, conditions):
        self.id = ident
        self.active = True
        self.fpath = fpath
        self.line = line
        self.conditions = conditions[:]

    def __iter__(self):
        yield self.id
        yield self.active
        yield self.fpath
        yield self.line
        yield self.conditions


class BreakManager(object):
    def __init__(self, problem):
        self._problem = weakref.ref(problem)
        self.bplocator = bplocator = BreakpointLocator()
        bplocator.process_class(problem.__class__)
        self._breaks = []
        self._cmds = deque([])

    def setup(self):
        seen = set([object])
        for s in self._problem().model.system_iter(recurse=True, include_self=True):
            for c in inspect.getmro(s.__class__):
                if c not in seen:
                    self.bplocator.process_class(c)
                    seen.add(c)
            self.bplocator.add_instance(s.pathname, s.__class__)

    def add_command(self, cmd):
        self._cmds.append(cmd)

    def has_commands(self):
        return len(self._cmds) > 0

    def next_command(self):
        return self._cmds.popleft()

    def find_break(self, arg):
        # TODO: add parsing for , condition
        instance = None
        if '.' in arg:
            parent, func = arg.rsplit('.', 1)
        else:
            func = arg
            parent = None

        # first map instance name to class
        try:
            klass = self.bplocator.inst2class[parent]
            instance = parent
        except KeyError:
            # didn't find instance, could be a class
            if parent in self.bplocator.classes:
                klass = self.bplocator.classes[parent]
            else:
                print(f"Can't find function '{arg}.")
                return None, None, None
        # get start line of method from bplocator
        for class_ in inspect.getmro(klass):
            try:
                info = self.bplocator.func_info['.'.join((class_.__name__, func))]
                break
            except KeyError:
                continue
        else:
            print(f"Can't find function '{'.'.join((class_.__name__, func))}.")
            return None, None, None

        if instance is None:
            # Add a break for all instances of the class
            if klass is class_:
                conds = ()
            else:
                # Add a condition for the specific class since the actual
                # method is coming from a base class.
                conds = (f"({klass.__name__} in self.__class__.__mro__)",)
        else:
            # Add conditional break where pathname matches the given instance
            conds = (f"(self.pathname=='{instance}')",)

        return info.filepath, info.start, conds

    def bfunc(self, arg):  # break in func
        fpath, start, conds = self.find_break(arg)
        if fpath is None:
            return

        self._breaks.append(BreakInfo(len(self._breaks) + 1, fpath, start, conds))
        if conds:
            self.add_command(f"break {fpath}: {start}, {' or '.join(conds)}")
        else:
            self.add_command(f"break {fpath}: {start}")

    def fdump(self, arg):
        """
        Dump known functions, with optional glob pattern filtering.
        """
        if arg:
            for f in self.bplocator.func_info:
                if fnmatchcase(f, arg):
                    print(f)
        else:
            for f in self.bplocator.func_info:
                print(f)

    def idump(self, arg):
        """
        Dump known instance paths, with optional glob pattern filtering.
        """
        if arg:
            for i in self.bplocator.inst2class:
                if fnmatchcase(i, arg):
                    print(i)
        else:
            for i in self.bplocator.inst2class:
                print(i)


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
        self.inst2class = {}
        self.cname2inst = defaultdict(list)
        self.classes = {}
        self.filepath = None

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
                    continue
                start = finfo.start = bnode.lineno
            self.visit(bnode)
        finfo.end = bnode.lineno

        self.stack.pop()
        self.fstack.pop()

    def visit_Return(self, node):
        self.fstack[-1].returns.append(node.lineno)

    def visit_Raise(self, node):
        self.fstack[-1].raises.append(node.lineno)

    def add_instance(self, pathname, klass):
        self.inst2class[pathname] = klass
        self.cname2inst[klass.__name__].append(pathname)

    def process_class(self, klass):
        try:
            mod = sys.modules[klass.__module__]
        except:
            print(f"skipping class {klass.__name__}. Can't find module.")

        self.classes[klass.__name__] = klass

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
