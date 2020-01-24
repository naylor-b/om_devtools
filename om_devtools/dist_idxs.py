
"""
Setup functions for the 'openmdao dist_idxs' command plugin.

This command dumps the distributed indices of specified OpenMDAO vectors.
"""

import sys
from six.moves import zip_longest

from openmdao.utils.hooks import _register_hook
from openmdao.utils.file_utils import _load_and_exec
from openmdao.utils.mpi import MPI


def dump_dist_idxs(problem, vec_name='nonlinear', full=False, stream=sys.stdout):
    """
    Print out the distributed idxs for each variable in input and output vecs.

    Output looks like this:

    C3.y     24
    C2.y     21
    sub.C3.y 18
    C1.y     17     18 C3.x
    P.x      14     15 C2.x
    C3.y     12     12 sub.C3.x
    C3.y     11     11 C1.x
    C2.y      8      8 C3.x
    sub.C2.y  5      5 C2.x
    C1.y      3      2 sub.C2.x
    P.x       0      0 C1.x

    Parameters
    ----------
    problem : <Problem>
        The problem object that contains the model.
    vec_name : str
        Name of vector to dump (when there are multiple vectors due to parallel derivs)
    full : bool
        If True, include data for all indices instead of just offsets.
    stream : File-like
        Where dump output will go.
    """
    def _get_data(g, type_):

        sizes = g._var_sizes[vec_name]
        vnames = g._var_allprocs_abs_names

        data = []
        nwid = 0
        iwid = 0
        total = 0
        for rank in range(g.comm.size):
            for ivar, vname in enumerate(vnames[type_]):
                sz = sizes[type_][rank, ivar]
                if sz > 0:
                    if full:
                        data.extend((vname, str(total + i)) for i in range(sz))
                    else:
                        data.append((vname, str(total)))
                nwid = max(nwid, len(vname))
                iwid = max(iwid, len(data[-1][1]))
                total += sz

        return data, nwid, iwid

    def _dump(g, stream):

        pdata, pnwid, piwid = _get_data(g, 'input')
        udata, unwid, uiwid = _get_data(g, 'output')

        data = []
        for u, p in zip_longest(udata, pdata, fillvalue=('', '')):
            data.append((u[0], u[1], p[1], p[0]))

        template = "{0:<{wid0}} {1:>{wid1}}     {2:>{wid2}} {3:<{wid3}}\n"
        for d in data[::-1]:
            stream.write(template.format(d[0], d[1], d[2], d[3],
                                         wid0=unwid, wid1=uiwid,
                                         wid2=piwid, wid3=pnwid))
        stream.write("\n\n")

    if not MPI or MPI.COMM_WORLD.rank == 0:
        _dump(problem.model, stream)


def _dist_idxs_setup_parser(parser):
    """
    Set up the openmdao subparser for the 'openmdao dump_idxs' command.

    Parameters
    ----------
    parser : argparse subparser
        The parser we're adding options to.
    """
    parser.add_argument(
        'file', nargs=1, help='Python file containing the model.')
    parser.add_argument('-o', default=None, action='store', dest='outfile',
                        help='Name of output file.  By default, output goes to stdout.')
    parser.add_argument('-v', '--vecname', action='store', default='nonlinear', dest='vecname',
                        help='Name of vectors to show indices for.  Default is "nonlinear".')
    parser.add_argument('-f', '--full', action='store_true', dest='full',
                        help="Show all indices instead of just offsets.")


def _dist_idxs_exec(options, user_args):
    """
    Return the post_setup hook function for 'openmdao dump_idxs'.

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

    def _dumpdist(prob):
        dump_dist_idxs(prob, vec_name=options.vecname, full=options.full, stream=out)
        exit()

    _register_hook('final_setup', 'Problem', post=_dumpdist)

    _load_and_exec(options.file[0], user_args)


def _dist_idxs_setup():
    """
    A command to list the global indices of specified OpenMDAO vectors.
    """
    return (
        _dist_idxs_setup_parser,
        _dist_idxs_exec,
        "Dump the distributed indices of variables in OpenMDAO vectors."
        )

