
import sys
import ast
import inspect
from collections import defaultdict, deque

from openmdao.core.problem import Problem
from openmdao.core.system import System


class BreakManager(object):
    def __init__(self, model):
        assert model.pathname == ''
        self.fdict = {
            '@parse_system_src': self.parse_system_src,
            '@get_pathname': self.get_pathname,
        }
        self.bplocator = bplocator = BreakpointLocator()
        bplocator.process_class(Problem)
        seen = set()
        for s in model.system_iter(recurse=True, include_self=True):
            if s.__class__ not in seen:
                bplocator.process_class(s.__class__)
                seen.add(s.__class__)
            bplocator.add_instance(s.pathname, s.__class__)

        # sinit = bplocator.func_info['System.__init__']
        # setup_procs = bplocator.func_info['System._setup_procs']
        self._cmds = deque([])
        #     f'b {sinit.filepath}: {sinit.start}, @parse_system_src',
        #     'commands',
        #     'silent',
        #     'end',
        #     f'b {setup_procs.filepath}: {setup_procs.start}, @get_pathname',
        #     'commands',
        #     'silent',
        #     'forward foo:bar:baz',
        #     'end',
        # ])
        self.add_command('stopin circuit.R1.compute')

    def add_command(self, cmd):
        self._cmds.append(cmd)

    def has_commands(self):
        return len(self._cmds) > 0

    def next_command(self):
        return self._cmds.popleft()

    def stop_in(self, arg):
        # TODO: add parsing for , condition
        if '.' in arg:
            opath, func = arg.rsplit('.', 1)
        # first map instance name to class
        klass = self.bplocator.inst2class[opath]
        # get start line of method from bplocator
        info = self.bplocator.func_info['.'.join((klass.__name__, func))]
        self.add_command(f"b {info.filepath}: {info.start}")

    def do_break_action(self, bp, frameinfo, frame_globals, frame_locals):
        return self.fdict[bp.cond](frameinfo, frame_globals, frame_locals)

    def parse_system_src(self, frameinfo, frame_globals, frame_locals):
        """
        After breaking in System.__init__, get file of class and parse the ast for breakpoint locs.
        """
        for klass in inspect.getmro(frame_locals['self'].__class__):
            self.bplocator.process_class(klass)
            if klass is System:
                break
        return True

    def get_pathname(self, frameinfo, frame_globals, frame_locals):
        """
        After breaking in System._setup_procs, get instance pathname.
        """
        self.bplocator.add_instance(frame_locals['pathname'], frame_locals['self'].__class__)
        return True


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
        self.class2inst = defaultdict(list)
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
        self.class2inst[klass].append(pathname)

    def process_class(self, klass):
        try:
            mod = sys.modules[klass.__module__]
        except:
            print(f"skipping class {klass.__name__}. Can't find module.")

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
