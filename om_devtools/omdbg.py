
import os
import sys
import pdb
import bdb
import inspect
from bdb import effective, Breakpoint, checkfuncname, BdbQuit

from om_devtools.breakpoints import BreakpointLocator, BreakManager
import openmdao.utils.hooks as hooks
from openmdao.utils.file_utils import _load_and_exec, _to_filename


class _DBGInput(object):
    def __init__(self, debugger):
        self.brkmanager = debugger.brkmanager
        self.debugger = debugger

    def readline(self, *args, **kwargs):
        if self.brkmanager.has_commands():
            return self.brkmanager.next_command()
        else:
            inp = input('Enter a command: ')
            if not inp:
                return 'p ""'
            return inp


class OMdbg(pdb.Pdb):
    file = None
    use_rawinput = False  # we're using our own stdin

    def __init__(self, problem, *args, **kwargs):
        self.brkmanager = BreakManager(problem)
        kwargs['stdin'] = _DBGInput(self)
        super(OMdbg, self).__init__(*args, **kwargs)
        self.prompt = ''
        self.command_prompt = ''

    def om_setup(self):
        self.brkmanager.setup()

    # # ----- basic commands -----
    def do_bfunc(self, arg):
        'Stop in a specific instance or class method'
        self.brkmanager.bfunc(arg)
        return True

    def do_fdump(self, arg):
        'Dump known functions'
        self.brkmanager.fdump(arg)
        return True

    def do_idump(self, arg):
        'Dump known instances'
        self.brkmanager.idump(arg)
        return True

    def do_quit(self, arg):
        print("QUIT!!!")
        return False

    def message(self, msg):
        print(msg, file=self.stdout)


# ---------------- command line tool setup -------------------

def _omdbg_setup_parser(parser):
    """
    Set up the openmdao subparser for the 'openmdao dump_idxs' command.

    Parameters
    ----------
    parser : argparse subparser
        The parser we're adding options to.
    """
    parser.add_argument('file', nargs=1, help='Python file containing the OpenMDAO model.')
    parser.add_argument('-o', default=None, action='store', dest='outfile',
                        help='Name of output file.  By default, output goes to stdout.')


_debugger = None


def _omdbg_exec(options, user_args):
    """
    Return the post_setup hook function for 'openmdao debug'.

    Parameters
    ----------
    options : argparse Namespace
        Command line options.
    user_args : list of str
        Args to be passed to the user script.
    """

    def _start_user_interaction(system):
        global _debugger
        hooks._unregister_hook('_configure', class_name='System', inst_id=None, post=None)
        _debugger.om_setup()
        _debugger.set_trace()

    def _set_dbg_hooks(prob):
        global _debugger
        _debugger = OMdbg(prob)
        # We want to activate debugging as soon as we can, but we need to know instance pathnames
        # before we do it, so wait until after _setup_procs.  First call after _setup_procs in
        # _setup is _configure.
        hooks._register_hook('_configure', class_name='System', inst_id=None,
                             pre=_start_user_interaction)
        hooks._setup_hooks(prob.model)

    # register the hooks
    hooks._register_hook('setup', 'Problem', pre=_set_dbg_hooks)

    _load_and_exec(options.file[0], user_args)


def _omdbg_setup():
    """
    A command to debug an OpenMDAO script.
    """
    return (
        _omdbg_setup_parser,
        _omdbg_exec,
        "Debug an OpenMDAO script."
        )
