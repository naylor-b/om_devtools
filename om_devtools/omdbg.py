
import os
import sys
import pdb
import inspect
# import tornado.web
# import tornado.ioloop

import openmdao.core.group
from openmdao.core.problem import Problem
from openmdao.core.system import System
from om_devtools.breakpoints import BreakpointLocator

class _DBGInput(object):
    def __init__(self):
        self.bploc = bploc = BreakpointLocator()
        bploc.process_class(System)
        bploc.process_class(Problem)
        p = bploc.func_info['Problem.__init__']
        s = bploc.func_info['System.__init__']
        self._cmds = [
            f'b {p.filepath}: {p.start}',
            f'b {s.filepath}: {s.start}',
            'c'
        ]
        self._cmdcount = 0
        # pprint.pprint(bploc.funct_ranges)

    def readline(self, *args, **kwargs):
        if self._cmdcount < len(self._cmds):
            idx = self._cmdcount
            self._cmdcount += 1
            return self._cmds[idx]
        else:
            return input('Enter a command: ')


class OMdbg(pdb.Pdb):
    file = None
    use_rawinput = False  # we're using our own stdin

    def __init__(self, *args, **kwargs):
        kwargs['stdin'] = _DBGInput()
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

