
from openmdao.utils.entry_points import compute_entry_points


def _compute_entry_points_setup_parser(parser):
    """
    Set up the openmdao subparser for the 'openmdao compute_entry_points' command.

    Parameters
    ----------
    parser : argparse subparser
        The parser we're adding options to.
    """
    parser.add_argument('package', nargs=1,
                        help='Compute entry points for this package.')
    parser.add_argument('-o', action='store',
                        dest='outfile', help='output file.')


def _compute_entry_points_exec(options, user_args):
    """
    Run the `openmdao compute_entry_points` command.

    Parameters
    ----------
    options : argparse Namespace
        Command line options.
    user_args : list of str  (ignored)
        Args to be passed to the user script.

    Returns
    -------
    function
        The hook function.
    """
    if options.outfile:
        with open(options.outfile, 'w') as f:
            compute_entry_points(options.package[0], outstream=f)
    else:
        compute_entry_points(options.package[0])


def _compute_entry_points_setup():
    """
    A command to compute the entry point declaration string for a given package.
    """
    return (
        _compute_entry_points_setup_parser,
        _compute_entry_points_exec,
        "Compute entry point declarations to add to the setup.py file."
    )
