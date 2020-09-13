
import os
import sys
import pdb
import inspect
from bdb import effective, Breakpoint, checkfuncname

import openmdao.core.group
from openmdao.core.problem import Problem
from openmdao.core.system import System
from om_devtools.breakpoints import BreakpointLocator, BreakManager


class _DBGInput(object):
    def __init__(self, brkmanager):
        self.brkmanager = brkmanager
        self.bploc = bploc = BreakpointLocator()
        bploc.process_class(System)
        bploc.process_class(Problem)
        sinit = bploc.func_info['System.__init__']
        setup_procs = bploc.func_info['System._setup_procs']
        self._cmds = [
            'c',
            f'b {sinit.filepath}: {sinit.start}, @parse_src',
            f'b {setup_procs.filepath}: {setup_procs.start}, @get_pathname',
        ]

    def readline(self, *args, **kwargs):
        if self._cmds:
            return self._cmds.pop()
        else:
            return input('Enter a command: ')


class OMdbg(pdb.Pdb):
    file = None
    use_rawinput = False  # we're using our own stdin

    def __init__(self, *args, **kwargs):
        self.brkmanager = BreakManager()
        kwargs['stdin'] = _DBGInput(self.brkmanager)
        super(OMdbg, self).__init__(*args, **kwargs)

    # # ----- basic commands -----
    # def do_forward(self, arg)
    #     'Move the turtle forward by the specified distance:  FORWARD 10'
    #     forward(*parse(arg))
    # def do_bye(self, arg):
    #     'Close the openmdao window and exit:  BYE'
    #     print('Thank you for using OpenMDAO')
    #     self.close()
    #     bye()
    #     return True

    def break_here(self, frame):
        """Return True if there is an effective breakpoint for this line.

        Check for line or function breakpoint and if in effect.
        Delete temporary breakpoints if effective() says to.
        """
        filename = self.canonic(frame.f_code.co_filename)
        if filename not in self.breaks:
            return False
        lineno = frame.f_lineno
        if lineno not in self.breaks[filename]:
            # The line itself has no breakpoint, but maybe the line is the
            # first line of a function with breakpoint set by function name.
            lineno = frame.f_code.co_firstlineno
            if lineno not in self.breaks[filename]:
                return False

        # flag says ok to delete temp. bp
        (bp, flag) = self.my_effective(filename, lineno, frame)
        if bp:
            self.currentbp = bp.number
            if (flag and bp.temporary):
                self.do_clear(str(bp.number))
            return True
        else:
            return False

    # Determines if there is an effective (active) breakpoint at this
    # line of code.  Returns breakpoint number or 0 if none
    def my_effective(self, file, line, frame):
        """Determine which breakpoint for this file:line is to be acted upon.

        Called only if we know there is a breakpoint at this location.  Return
        the breakpoint that was triggered and a boolean that indicates if it is
        ok to delete a temporary breakpoint.  Return (None, None) if there is no
        matching breakpoint.
        """
        for b in Breakpoint.bplist[file, line]:
            if not b.enabled:
                continue
            if not checkfuncname(b, frame):
                continue
            # Count every hit when bp is enabled
            b.hits += 1
            if not b.cond:
                # If unconditional, and ignoring go on to next, else break
                if b.ignore > 0:
                    b.ignore -= 1
                    continue
                else:
                    # breakpoint and marker that it's ok to delete if temporary
                    return (b, True)
            else:
                # Conditional bp.
                # Ignore count applies only to those bpt hits where the
                # condition evaluates to true.
                try:
                    if b.cond.startswith('@'):
                        val = self.brkmanager.do_break_action(b.cond, inspect.getframeinfo(frame),
                                                              frame.f_globals, frame.f_locals)
                    else:
                        val = eval(b.cond, frame.f_globals, frame.f_locals)
                    if val:
                        if b.ignore > 0:
                            b.ignore -= 1
                            # continue
                        else:
                            return (b, True)
                    # else:
                    #   continue
                except:
                    # if eval fails, most conservative thing is to stop on
                    # breakpoint regardless of ignore count.  Don't delete
                    # temporary, as another hint to user.
                    return (b, False)
        return (None, None)


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
    if options.outfile is None:
        out = sys.stdout
    else:
        out = open(options.outfile, 'w')

    script_name = options.file[0]

    sys.path.insert(0, os.path.dirname(script_name))

    sys.argv[:] = [script_name] + user_args

    with open(script_name, 'rb') as fp:
        code = compile(fp.read(), script_name, 'exec')

    globals_dict = {
        '__file__': script_name,
        '__name__': '__main__',
        '__package__': None,
        '__cached__': None,
    }

    om = OMdbg()
    om.intro = '\nWelcome to the OpenMDAO debugger\n'
    om.prompt='<openmdao> '
    om.run(code, globals=globals_dict)


def _omdbg_setup():
    """
    A command to debug an OpenMDAO script.
    """
    return (
        _omdbg_setup_parser,
        _omdbg_exec,
        "Debug an OpenMDAO script."
        )

