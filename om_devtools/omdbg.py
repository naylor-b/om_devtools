
import os
import sys
import pdb
import bdb
import inspect
from bdb import effective, Breakpoint, checkfuncname

from om_devtools.breakpoints import BreakpointLocator, BreakManager
import openmdao.utils.hooks as hooks
from openmdao.utils.file_utils import _load_and_exec, _to_filename


class _DBGInput(object):
    def __init__(self, brkmanager):
        self.brkmanager = brkmanager

    def readline(self, *args, **kwargs):
        if self.brkmanager.has_commands():
            return self.brkmanager.next_command()
        else:
            return 'c'  # input('Enter a command: ')


class OMdbg(pdb.Pdb):
    file = None
    use_rawinput = False  # we're using our own stdin

    def __init__(self, problem, *args, **kwargs):
        self.brkmanager = BreakManager(problem)
        kwargs['stdin'] = _DBGInput(self.brkmanager)
        super(OMdbg, self).__init__(*args, **kwargs)
        self.prompt = ''
        self.command_prompt = ''

    # # ----- basic commands -----
    def do_stopin(self, arg):
        'Stop in a specific instance method'
        self.brkmanager.stop_in(arg)

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
                        self.prompt=''
                        val = self.brkmanager.do_break_action(b, inspect.getframeinfo(frame),
                                                              frame.f_globals, frame.f_locals)
                    else:
                        self.prompt='<omdbg> '
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

    def do_commands(self, arg):
        """commands [bpnumber]
        (com) ...
        (com) end
        (Pdb)

        Specify a list of commands for breakpoint number bpnumber.
        The commands themselves are entered on the following lines.
        Type a line containing just 'end' to terminate the commands.
        The commands are executed when the breakpoint is hit.

        To remove all commands from a breakpoint, type commands and
        follow it immediately with end; that is, give no commands.

        With no bpnumber argument, commands refers to the last
        breakpoint set.

        You can use breakpoint commands to start your program up
        again.  Simply use the continue command, or step, or any other
        command that resumes execution.

        Specifying any command resuming execution (currently continue,
        step, next, return, jump, quit and their abbreviations)
        terminates the command list (as if that command was
        immediately followed by end).  This is because any time you
        resume execution (even with a simple next or step), you may
        encounter another breakpoint -- which could have its own
        command list, leading to ambiguities about which list to
        execute.

        If you use the 'silent' command in the command list, the usual
        message about stopping at a breakpoint is not printed.  This
        may be desirable for breakpoints that are to print a specific
        message and then continue.  If none of the other commands
        print anything, you will see no sign that the breakpoint was
        reached.
        """
        if not arg:
            bnum = len(bdb.Breakpoint.bpbynumber) - 1
        else:
            try:
                bnum = int(arg)
            except:
                self.error("Usage: commands [bnum]\n        ...\n        end")
                return
        self.commands_bnum = bnum
        # Save old definitions for the case of a keyboard interrupt.
        if bnum in self.commands:
            old_command_defs = (self.commands[bnum],
                                self.commands_doprompt[bnum],
                                self.commands_silent[bnum])
        else:
            old_command_defs = None
        self.commands[bnum] = []
        self.commands_doprompt[bnum] = True
        self.commands_silent[bnum] = False

        prompt_back = self.prompt
        self.prompt = self.command_prompt
        self.commands_defining = True
        try:
            self.cmdloop()
        except KeyboardInterrupt:
            # Restore old definitions.
            if old_command_defs:
                self.commands[bnum] = old_command_defs[0]
                self.commands_doprompt[bnum] = old_command_defs[1]
                self.commands_silent[bnum] = old_command_defs[2]
            else:
                del self.commands[bnum]
                del self.commands_doprompt[bnum]
                del self.commands_silent[bnum]
            self.error('command definition aborted, old commands restored')
        finally:
            self.commands_defining = False
            self.prompt = prompt_back


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
    # if options.outfile is None:
    #     out = sys.stdout
    # else:
    #     out = open(options.outfile, 'w')

    # script_name = options.file[0]

    # sys.path.insert(0, os.path.dirname(script_name))

    # sys.argv[:] = [script_name] + user_args

    # with open(script_name, 'rb') as fp:
    #     code = compile(fp.read(), script_name, 'exec')

    # globals_dict = {
    #     '__file__': script_name,
    #     '__name__': '__main__',
    #     '__package__': None,
    #     '__cached__': None,
    # }

    # om = OMdbg()
    # om.run(code, globals=globals_dict)

    def _setup_dbg_info(prob):
        om = OMdbg(prob)
        om.set_trace()

    def _set_dbg_hook(prob):
        # We want to activate debugging as soon as we can, but we need to know instance pathnames
        # before we do it, so wait until after _setup_procs.  First call after _setup_procs in
        # _setup is _configure.
        hooks._register_hook('_configure', class_name='System', inst_id=None,
                             pre=_setup_dbg_info)
        hooks._setup_hooks(prob.model)

    # register the hooks
    hooks._register_hook('setup', 'Problem', pre=_set_dbg_hook)

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

