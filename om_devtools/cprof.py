
"""
Setup functions for the 'openmdao cprof' command plugin.

This command runs the c profiler on the given file or test function.
"""
import os
import sys
from openmdao.utils.file_utils import _load_and_exec
from openmdao.devtools.debug import profiling


def _cprof_setup_parser(parser):
    """
    Set up the openmdao subparser for the 'openmdao cprof' command.

    Parameters
    ----------
    parser : argparse subparser
        The parser we're adding options to.
    """
    parser.add_argument('file', nargs=1, help='Python script or test to profile.')
    parser.add_argument('-o', default='prof.out', action='store', dest='outfile',
                        help='Name of output file.  By default, output goes to prof.out')


def _cprof_exec(options, user_args):
    """
    Gather profiling info.

    Parameters
    ----------
    options : argparse Namespace
        Command line options.
    user_args : list of str
        Args to be passed to the user script.
    """
    with profiling(options.outfile):
        _load_and_exec(options.file[0], user_args)


def _cprof_setup():
    """
    A command to display source lines that allocate the most memory.
    """
    return (
        _cprof_setup_parser,
        _cprof_exec,
        "Run the c profiler on the given python script or test."
    )
