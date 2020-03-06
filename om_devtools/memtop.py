
"""
Setup functions for the 'openmdao memtop' command plugin.

This command displays the top memory allocating source lines.
"""
from __future__ import print_function

import os
import sys
import linecache
import tracemalloc
from openmdao.utils.file_utils import _load_and_exec


# the following function is taken from the python tracemalloc docs.

def display_top(snapshot, key_type='lineno', limit=10, file=sys.stdout):
    snapshot = snapshot.filter_traces((
        tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
        tracemalloc.Filter(False, "<unknown>"),
    ))
    top_stats = snapshot.statistics(key_type)

    pstr = "%s Source Lines Using the Most Memory" % limit
    if file is sys.stdout:
        print('\n\n')
    print(pstr, file=file)
    print('-' * len(pstr), file=file)
    for index, stat in enumerate(top_stats[:limit], 1):
        frame = stat.traceback[0]
        # replace "/path/to/module/file.py" with "module/file.py"
        filename = os.sep.join(frame.filename.split(os.sep)[-2:])
        print("#%s: %s:%s: %.1f KiB"
              % (index, filename, frame.lineno, stat.size / 1024), file=file)
        line = linecache.getline(frame.filename, frame.lineno).strip()
        if line:
            print('    %s' % line, file=file)

    other = top_stats[limit:]
    if other:
        size = sum(stat.size for stat in other)
        print("%s other: %.1f KiB" % (len(other), size / 1024), file=file)
    total = sum(stat.size for stat in top_stats)
    print("Total allocated size: %.1f KiB" % (total / 1024), file=file)


def _memtop_setup_parser(parser):
    """
    Set up the openmdao subparser for the 'openmdao memtop' command.

    Parameters
    ----------
    parser : argparse subparser
        The parser we're adding options to.
    """
    parser.add_argument('file', nargs=1, help='Python script to check for memory usage.')
    parser.add_argument('-o', default=None, action='store', dest='outfile',
                        help='Name of output file.  By default, output goes to stdout.')
    parser.add_argument('-l', '--limit', action='store', type=int, default=20, dest='limit',
                        help='Limit the number of lines in the output.')


def _memtop_exec(options, user_args):
    """
    Display the top memory usage.

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

    tracemalloc.start()

    _load_and_exec(options.file[0], user_args)

    snapshot = tracemalloc.take_snapshot()
    display_top(snapshot, limit=options.limit, file=out)


def _memtop_setup():
    """
    A command to display source lines that allocate the most memory.
    """
    return (
        _memtop_setup_parser,
        _memtop_exec,
        "Display source lines that allocate the most memory."
        )

