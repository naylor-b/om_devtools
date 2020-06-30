
import os
import sys
import pdb

class OMdbg(pdb.Pdb):
    intro = 'Welcome to the OpenMDAO debugger.   Type help or ? to list commands.\n'
    prompt = '(openmdao) '
    file = None

    # # ----- basic commands -----
    # def do_forward(self, arg):
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

