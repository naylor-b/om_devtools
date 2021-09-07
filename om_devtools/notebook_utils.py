import json
import os
import sys
import argparse
import subprocess

from openmdao.utils.file_utils import files_iter


def nb2dict(fname):
    with open(fname) as f:
        return json.load(f)


def notebook_filter(fname, filters):
    """
    Return True if the given notebook satisfies the given filter function.

    Parameters
    ----------
    fname : str
        Name of the notebook file.
    filters : list of functions
        The filter functions.  They take a dictionary as an arg and return True/False.

    Returns
    -------
    bool
        True if the filter returns True.
    """
    dct = nb2dict(fname)

    for f in filters:
        if f(dct):
            return True

    return False


def is_parallel(dct):
    """
    Return True if the notebook containing the dict uses ipyparallel.
    """
    for cell in dct['cells']:
        if cell['cell_type'] == 'code':
            for line in cell['source']:
                if 'ipyparallel' in line:
                    return True
    return False


def section_filter(dct, section):
    """
    Return True if the notebook containing the dict contains the given section string.
    """
    for cell in dct['cells']:
        if cell['cell_type'] == 'markdown':
            for line in cell['source']:
                if section in line and line.startswith('#'):
                    return True
    return False


def string_filter(dct, s):
    """
    Return True if the notebook containing the dict contains the given string.
    """
    for cell in dct['cells']:
        if cell['cell_type'] in ('markdown', 'code'):
            for line in cell['source']:
                if s in line:
                    return True
    return False


def find_notebooks_iter(section=None, string=None):
    filters = []
    if section:
        filters.append(lambda dct: section_filter(dct, section))
    if string:
        filters.append(lambda dct: string_filter(dct, string))

    dexcludes = ['.ipynb_checkpoints', '_*']
    for f in files_iter(file_includes=['*.ipynb'], dir_excludes=dexcludes):
        if not filters or notebook_filter(f, filters):
            yield f


def pick_one(files):
    print("Multiple matches found.")
    while True:
        for i, f in enumerate(files):
            print(f"{i}) {f}")
        try:
            response = int(input("\nSelect the index of the file to view: "))
        except ValueError:
            print("\nBAD index.  Try again.\n")
            continue
        if response < 0 or response > (len(files) + 1):
            print(f"\nIndex {response} is out of range.  Try again.\n")
            continue
        return files[response]


def show_notebook_cmd():
    """
    Display a notebook given a keyword.
    """
    parser = argparse.ArgumentParser(description='Empty output cells, reset execution_count, and '
                                     'remove empty cells of jupyter notebook(s).')
    parser.add_argument('file', nargs='?', help='Look for notebook having the given base filename')
    parser.add_argument('--section', action='store', dest='section',
                        help='Look for notebook(s) having the given section string.')
    parser.add_argument('-s', '--string', action='store', dest='string',
                        help='Look for notebook(s) having the given string in a code or markdown '
                        'cell.')
    args = parser.parse_args()

    if args.file is None:
        fname = None
    elif args.file.endswith('.ipynb'):
        fname = args.file
    else:
        fname = args.file + '.ipynb'

    if fname is not None:
        files = [f for f in find_notebooks_iter() if os.path.basename(f) == fname]
        if not files:
            print(f"Can't find file {fname}.")
            sys.exit(-1)
    else:
        files = list(find_notebooks_iter(section=args.section, string=args.string))
        if not files:
            print(f"No matching notebook files found.")
            sys.exit(-1)

    if len(files) == 1:
        show_notebook(files[0], nb2dict(files[0]))
    else:
        f = pick_one(files)
        show_notebook(f, nb2dict(f))


def show_notebook(f, dct):
    if is_parallel(dct):
        pidfile = os.path.join(os.path.expanduser('~'), '.ipython/profile_mpi/pid/ipcluster.pid')
        if not os.path.isfile(pidfile):
            print("cluster isn't running...")
            sys.exit(-1)
    os.system(f"jupyter notebook {f}")


def notebook_src_cell_iter(fname):
    """
    Iterate over source cells of the given notebook.

    Parameters
    ----------
    fname : str
        Name of the notebook file.

    Yields
    ------
    list of str
        Lines of the source cell.
    list of str
        Lines of the corresponding output.
    int
        Execution count.
    """
    with open(fname) as f:
        dct = json.load(f)

    for cell in dct['cells']:
        if cell['cell_type'] == 'code':
            if cell['source']:  # cell is not empty
                yield cell['source'], cell['outputs'], cell['execution_count']


def get_full_notebook_src(fname):
    """
    Return the full contents of source cells in the given notebook.

    Parameters
    ----------
    fname : str
        Name of the notebook file.

    Returns
    -------
    str
        Source of the given notebook.
    """
    lines = []
    for srclines, _, _ in notebook_src_cell_iter(fname):
        for s in srclines:
            ls = s.lstrip()
            if ls.startswith('!') or ls.startswith('%'):
                lines.append(' ' * (len(s) - len(ls)) + 'pass # ' + ls.rstrip())
            elif ls:
                lines.append(s.rstrip())
    return '\n'.join(lines)


def grep_notebooks(includes=('*.ipynb',), dir_excludes=('_build', '_srcdocs', '.ipynb_checkpoints'),
                   greps=()):
    """
    Yield the file pathname and the full contents of source cells from matching notebooks.

    Parameters
    ----------
    includes : list of str
        List of local file names or glob patterns to match.
    dir_excludes : list of str
        List of local directory names to skip.
    greps : list of str
        If not empty, only return names and source from notebooks whose source contains at least
        one of the strings provided.

    Yields
    ------
    str
        Full file pathname of a matching notebook.
    str
        Full contents of source cells from the given notebook.
    """
    for fpath in files_iter(file_includes=includes, dir_excludes=dir_excludes):
        full = get_full_notebook_src(fpath)
        if not greps:
            yield fpath, full
        else:
            for g in greps:
                if g in full:
                    yield fpath, full
                    break


def run_notebook_src(fname, src, nprocs=1, show_src=True, timeout=None, outstream=sys.stdout,
                     errstream=sys.stderr):
    """
    Execute python source code from notebook(s).

    Parameters
    ----------
    fname : str
        Filename of the notebook.
    src : str
        Full python source contained in the notebook.
    nprocs : int
        Number of processes to use for cells using MPI.
    show_src : bool
        If True, display the full python source to outstream.
    timeout : float
        If set, terminate the running code after 'timeout' seconds.
    outstream : file
        File where output is written.
    errstream : file
        File where errors and warnings are written.
    """
    # only run on nprocs if we find %px in the source
    if '%px' not in src:
        nprocs = 1

    print('&' * 20, ' running', fname, ' ' + '&' * 20, file=outstream, flush=True)
    if show_src:
        print(src, file=outstream)
    print('-=' * 40, file=outstream)
    with open('_junk_.py', 'w') as tmp:
        tmp.write(src)
    if nprocs == 1:
        proc = subprocess.run(['python', '_junk_.py'], text=True, capture_output=True,
                              timeout=timeout)
    else:
        proc = subprocess.run(['mpirun', '-n', str(nprocs), 'python', '_junk_.py'],
                                text=True, capture_output=True, timeout=timeout)
    try:
        os.remove('_junk.py')
    except OSError:
        pass

    if proc.returncode != 0:
        print(f"{fname} return code = {proc.returncode}.", file=errstream)
    print(proc.stdout, file=outstream)
    print(proc.stderr, file=errstream)
    print('-=' * 40, file=outstream)


def _run_notebook_exec(options, user_args):
    if options.recurse:
        if options.file:
            print("When using the --recurse option, don't specify filenames. Use --include "
                  "instead.")
            sys.exit(-1)

        if not options.includes:
            options.includes = ['*.ipynb']

        outs = open('run_notebooks.out', 'w')
        errs = open('run_notebooks.err', 'w')

        for fpath, src in grep_notebooks(includes=options.includes,
                                         greps=options.greps):
            if options.dryrun:
                print(fpath)
            else:
                run_notebook_src(fpath, src, nprocs=options.nprocs, timeout=options.timeout,
                                 outstream=outs, errstream=errs)
    else:

        if options.includes:
            print("The --include option only works when also using --recurse.")
            sys.exit(-1)

        for f in sorted(options.file):
            if os.path.isdir(f):
                continue
            if not f.endswith('.ipynb'):
                print(f"'{f}' is not a notebook.")
                continue
            if not os.path.isfile(f):
                print(f"Can't find file '{f}'.")
                sys.exit(-1)

            src = get_full_notebook_src(f)
            run_notebook_src(f, src, nprocs=options.nprocs, timeout=options.timeout)


def _run_notebook_setup_parser(parser):
    parser.add_argument('file', nargs='*', help='Jupyter notebook file(s).')
    parser.add_argument('-r', '--recurse', action='store_true', dest='recurse',
                        help='Search through all directories at or below the current one for the '
                        'specified file(s).  If no files are specified, execute all jupyter '
                        'notebook files found.')
    parser.add_argument('-i', '--include', action='append', dest='includes',
                        default=[], help='If the --recurse option is active, this specifies a '
                        'local filename or glob pattern to match. This argument may be supplied '
                        'multiple times.')
    parser.add_argument('-g', '--grep', action='append', dest='greps',
                        default=[], help='Run only notebooks that contain this string.  This '
                        'argument can be supplied multiple times.')
    parser.add_argument('-n', '--nprocs', action='store', dest='nprocs',
                        default=4, type=int,
                        help='The number of processes to use for MPI cases.')
    parser.add_argument('-d', '--dryrun', action='store_true', dest='dryrun',
                        help="Report which notebooks would be run but don't actually run them.")
    parser.add_argument('--timeout', action='store', dest='timeout', type=float,
                        help='Timeout in seconds. Run will be terminated if it takes longer than '
                             'timeout.')


def _run_notebook_setup():
    """
    A command to run the source cells from given notebook(s).
    """
    return (
        _run_notebook_setup_parser,
        _run_notebook_exec,
        "Run a given ipython notebook or collection of notebooks and store their output."
    )
