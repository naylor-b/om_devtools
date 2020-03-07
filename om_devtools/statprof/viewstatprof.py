
"""Define a function to view statistical profile data."""
import os
import sys
import signal
import json
import time
import contextlib
from collections import defaultdict
import threading
import struct
import webbrowser
import pickle

from six import iteritems

import numpy as np

from openmdao.core.problem import Problem
from openmdao.utils.units import convert_units
from openmdao.utils.mpi import MPI
from openmdao.utils.webview import webview
from openmdao.utils.general_utils import printoptions
from openmdao.utils.functionlocator import FunctionLocator
from openmdao.core.system import System
from openmdao.core.problem import Problem
from openmdao.core.driver import Driver
from openmdao.solvers.solver import Solver
import tornado.web
import tornado.ioloop

try:
    import faulthandler
    faulthandler.enable()
except ImportError:
    pass


def launch_browser(port):
    time.sleep(1)
    for browser in ['chrome', 'firefox', 'chromium', 'safari']:
        try:
            webbrowser.get(browser).open('http://localhost:%s' % port)
        except:
            pass
        else:
            break


def startThread(fn):
    thread = threading.Thread(target=fn)
    thread.setDaemon(True)
    thread.start()
    return thread


_cmap = ["#ffffcc", "#fffecb", "#fffec9", "#fffdc8", "#fffdc6", "#fffcc5", "#fffcc4", "#fffbc2", "#fffac1", 
         "#fffac0", "#fff9be", "#fff9bd", "#fff8bb", "#fff8ba", "#fff7b9", "#fff6b7", "#fff6b6", "#fff5b5", 
         "#fff5b3", "#fff4b2", "#fff4b0", "#fff3af", "#fff2ae", "#fff2ac", "#fff1ab", "#fff1aa", "#fff0a8", 
         "#fff0a7", "#ffefa6", "#ffeea4", "#ffeea3", "#ffeda2", "#ffeda0", "#ffec9f", "#ffeb9d", "#ffeb9c", 
         "#ffea9b", "#ffea99", "#ffe998", "#ffe897", "#ffe895", "#ffe794", "#ffe693", "#ffe691", "#ffe590", 
         "#ffe48f", "#ffe48d", "#ffe38c", "#fee28b", "#fee289", "#fee188", "#fee087", "#fee085", "#fedf84", 
         "#fede83", "#fedd82", "#fedc80", "#fedc7f", "#fedb7e", "#feda7c", "#fed97b", "#fed87a", "#fed778", 
         "#fed777", "#fed676", "#fed574", "#fed473", "#fed372", "#fed270", "#fed16f", "#fed06e", "#fecf6c", 
         "#fece6b", "#fecd6a", "#fecb69", "#feca67", "#fec966", "#fec865", "#fec764", "#fec662", "#fec561", 
         "#fec460", "#fec25f", "#fec15e", "#fec05c", "#febf5b", "#febe5a", "#febd59", "#febb58", "#feba57", 
         "#feb956", "#feb855", "#feb754", "#feb553", "#feb452", "#feb351", "#feb250", "#feb14f", "#feb04e", 
         "#feae4d", "#fead4d", "#feac4c", "#feab4b", "#feaa4a", "#fea84a", "#fea749", "#fea648", "#fea547", 
         "#fea347", "#fea246", "#fea145", "#fda045", "#fd9e44", "#fd9d44", "#fd9c43", "#fd9b42", "#fd9942", 
         "#fd9841", "#fd9741", "#fd9540", "#fd9440", "#fd923f", "#fd913f", "#fd8f3e", "#fd8e3e", "#fd8d3d", 
         "#fd8b3c", "#fd893c", "#fd883b", "#fd863b", "#fd853a", "#fd833a", "#fd8139", "#fd8039", "#fd7e38", 
         "#fd7c38", "#fd7b37", "#fd7937", "#fd7736", "#fc7535", "#fc7335", "#fc7234", "#fc7034", "#fc6e33", 
         "#fc6c33", "#fc6a32", "#fc6832", "#fb6731", "#fb6531", "#fb6330", "#fb6130", "#fb5f2f", "#fa5d2e", 
         "#fa5c2e", "#fa5a2d", "#fa582d", "#f9562c", "#f9542c", "#f9522b", "#f8512b", "#f84f2a", "#f74d2a", 
         "#f74b29", "#f64929", "#f64828", "#f54628", "#f54427", "#f44227", "#f44127", "#f33f26", "#f23d26", 
         "#f23c25", "#f13a25", "#f03824", "#f03724", "#ef3524", "#ee3423", "#ed3223", "#ed3123", "#ec2f22", 
         "#eb2e22", "#ea2c22", "#e92b22", "#e92921", "#e82821", "#e72621", "#e62521", "#e52420", "#e42220", 
         "#e32120", "#e22020", "#e11f20", "#e01d20", "#df1c20", "#de1b20", "#dd1a20", "#dc1920", "#db1820", 
         "#da1720", "#d91620", "#d81520", "#d71420", "#d51320", "#d41221", "#d31121", "#d21021", "#d10f21", 
         "#cf0e21", "#ce0d21", "#cd0d22", "#cc0c22", "#ca0b22", "#c90a22", "#c80a22", "#c60923", "#c50823", 
         "#c40823", "#c20723", "#c10723", "#bf0624", "#be0624", "#bc0524", "#bb0524", "#b90424", "#b80424", 
         "#b60425", "#b50325", "#b30325", "#b10325", "#b00225", "#ae0225", "#ac0225", "#ab0225", "#a90125", 
         "#a70126", "#a50126", "#a40126", "#a20126", "#a00126", "#9e0126", "#9c0026", "#9a0026", "#990026", 
         "#970026", "#950026", "#930026", "#910026", "#8f0026", "#8d0026", "#8b0026", "#8a0026", "#880026", 
         "#860026", "#840026", "#820026", "#800026"]


def _get_color(val, maxval):
    global _cmap
    idx = int(val / maxval * len(_cmap))
    if idx >= len(_cmap):
        idx = len(_cmap) -1
    return _cmap[idx]


class Application(tornado.web.Application):
    def __init__(self, pyfile, raw_stat_file, statprof_data, nsamples):
        if pyfile is None:
            self.infile = raw_stat_file
        else:
            self.infile = pyfile
        self.raw_stat_file = raw_stat_file
        self.data = statprof_data
        self.funct_locator = FunctionLocator()
        self.nsamples = nsamples

        handlers = [
            (r"/", Index),
            ("^\/heatmap\/(.+)$", HeatMap),
            # ("^\/icicle\/(.+)$", Icicle),
        ]

        settings = dict(
             template_path=os.path.join(os.path.dirname(__file__), "templates"),
             static_path=os.path.join(os.path.dirname(__file__), "static"),
        )

        super(Application, self).__init__(handlers, **settings)


class Index(tornado.web.RequestHandler):
    def get(self):
        app = self.application
        self.render('index.html', 
                    statprof_data={'table': app.data['table'], 'srcfile': app.infile})


class HeatMap(tornado.web.RequestHandler):
    def get(self, ident):
        app = self.application
        srcfile, fstart = ident.split('&')
        fstart = int(fstart)
        app.funct_locator.process_file(srcfile)
        fpath, fstop = app.funct_locator.get_funct_last_line(fstart)
        if fstop is None:  # it's not a function, so just show a region around the line
            fstop = fstart + 25
            fstart -= 25
            if fstart < 0:
                fstart = 0
        srcdata = app.data['heatmap'][srcfile]
        table = []
        indent = None
        with open(srcfile, 'r') as f:
            for i, line in enumerate(f):
                if i + 1 < fstart:
                    continue
                if i + 1 > fstop:
                    break
                if indent is None:
                    indent = len(line) - len(line.lstrip())
                snum = i + 1
                short = line[indent:]
                if not short:
                    short = ' '  # prevent table from smushing empty lines
                if snum in srcdata:
                    row = {'lnum': snum, 'hits': str(srcdata[snum]), 'src': short, 
                           'color': _get_color(srcdata[snum], app.nsamples)}
                else:
                    row = {'lnum': snum, 'hits': '', 'src': short, 'color': 'lightgray'}
                table.append(row)

        self.render('src_heatmap.html', statprof_data={'table': table, 'srcfile': os.path.basename(srcfile)})


# class Index(tornado.web.RequestHandler):
#     def get(self):
#         app = self.application

#         self.render('icicle.html', call_tree=app.data['call_tree'])


def view_statprof(options, pyfile, raw_stat_file):
    """
    Generate a self-contained html file containing a detailed statistical profile viewer.

    Optionally pops up a web browser to view the file.

    Parameters
    ----------
    options : Options
        The command line options.
    pyfile : str or None
        Python script being profiled.
    raw_stat_file : str
        The name of the raw statistical profiling data file.
    """
    if MPI and MPI.COMM_WORLD.rank != 0:
        return

    # dct values are [hits, obj]
    dct = defaultdict(lambda: [0, '?'])
    heatmap_dict = defaultdict(lambda: defaultdict(int))
    calltree = {}
    with open(raw_stat_file + '.maps', 'rb') as f:
        maps = pickle.load(f)
    samples_taken = maps['samples_taken']
    call_tree = {}
    stack = [call_tree]
    data_stack = []
    for data_tup in _rawfile_iter(raw_stat_file, maps):
        if data_tup[0].startswith('<'):  # fname
            continue
        if data_tup[-1] == 1:  # is_root
            stack = [call_tree]
            for fname, line_number, func, fstart, obj, _ in data_stack[::-1]:  # reverse the order
                key = "{} {}".format(fname, line_number)
                if key not in stack[-1]:
                    stack[-1][key] = {}
                stack.append(stack[-1][key])

                heatmap_dict[fname][line_number] += 1
                if func == '<module>':
                    lst = dct[fname, line_number, func]
                else:
                    lst = dct[fname, fstart, func]
                lst[0] += 1
                lst[1] = obj
            data_stack = []
        else:
            data_stack.append(data_tup)

    # # populate call tree leaf nodes
    # stack = [(None, call_tree, iter(call_tree))]
    # while stack:
    #     key, d, it = stack[-1]
    #     if len(d) == 0:
    #         if key is None:
    #             break
    #         # replace leaf empty dict with number of hits
    #         fname, lnum = key.split()
    #         lnum = int(lnum)
    #         print('fname', fname, 'lnum', lnum, "HITS:",heatmap_dict[fname, lnum], flush=True)
    #         stack[-2][1][key] = heatmap_dict[fname][lnum]

    #     while True:
    #         try:
    #             # fname, lnum = next(it)
    #             keystr = next(it)
    #             if keystr.startswith('<'):  # skip builtin stuff
    #                 continue
    #             new_fname, new_lnum = keystr.split()
    #         except StopIteration:
    #             stack.pop()
    #             break
    #         else:
    #             newkey = "{} {}".format(new_fname, new_lnum)
    #             print("NEWKEY:", newkey)
    #             stack.append((newkey, d[newkey], iter(d[newkey])))

    # import pprint
    # pprint.pprint(call_tree)

    table = []
    idx = 1  # unique ID for use by Tabulator
    for key, (hits, obj) in sorted(dct.items(), key=lambda x: x[1]):
        fname, line_number, func = key
        table.append({'id': idx, 'fname': fname, 'line_number': line_number, 'hits': hits, 'func': func})
        idx += 1

    data = {
        'table': table,
        'heatmap': heatmap_dict,
        'call_tree': call_tree,
    }

    port = options.port

    app = Application(pyfile, raw_stat_file, data, samples_taken)
    app.listen(port)

    print("starting server on port %d" % port)

    serve_thread  = startThread(tornado.ioloop.IOLoop.current().start)
    launch_thread = startThread(lambda: launch_browser(port))

    while serve_thread.isAlive():
        serve_thread.join(timeout=1)


omtypes = (System, Solver, Problem, Driver)


def invert_dict(dct):
    return {v:k for k, v in dct.items()}


# based on code from plop (https://github.com/bdarnell/plop.git)
# only works on linux, MacOS
class StatisticalProfiler(object):
    MODES = {
        'prof': (signal.ITIMER_PROF, signal.SIGPROF),
        'virtual': (signal.ITIMER_VIRTUAL, signal.SIGVTALRM),
        'real': (signal.ITIMER_REAL, signal.SIGALRM),
    }

    def __init__(self, outfile='statprof.raw.0', interval=0.005, mode='virtual'):
        self.outfile = outfile
        self.stream = None
        self._stats = defaultdict(int)
        self.interval = interval
        self.mode = mode
        assert mode in StatisticalProfiler.MODES, 'valid modes are: ["prof", "virtual", "real"] but you chose {}'.format(mode)
        timer, sig = StatisticalProfiler.MODES[mode]
        signal.signal(sig, self._statprof_handler)
        signal.siginterrupt(sig, False)
        self.struct = struct.Struct('H H i H i H')

        self.stacks = []
        self.fnames = {'builtin': -1}
        self.functs = {'N/A': -1}
        self.objs = {'N/A': -1}

        self.samples_remaining = 0
        self.stopping = False
        self.stopped = False
        self._recording = False

        self.samples_taken = 0
        self.hits = 0

    def start(self, duration=600.0):
        if self.stream is None:
            self.stream = open(self.outfile, 'wb')
        self.stopping = False
        self.stopped = False
        self.samples_remaining = int(duration / self.interval)
        timer, sig = StatisticalProfiler.MODES[self.mode]
        signal.setitimer(timer, self.interval, self.interval)

    def stop(self):
        self.stopping = True
        while not self.stopped:
            pass  # need busy wait; ITIMER_PROF doesn't proceed while sleeping
        if self.stream is not None:
            self.stream.close()
            self.stream = None
            with open(self.outfile + '.maps', 'wb') as f:
                pickle.dump({
                                'fnames': invert_dict(self.fnames),
                                'functs': invert_dict(self.functs),
                                'objs': invert_dict(self.objs),
                                'samples_taken': self.samples_taken,
                            }, f)

    def record(self, frame, is_root):
        global omtypes
        self._recording = True
        try:
            fname = frame.f_code.co_filename
            if fname not in self.fnames:
                self.fnames[fname] = len(self.fnames)
            fname = self.fnames[fname]

            if 'self' in frame.f_locals and frame.f_locals['self'] is not self:
                self.hits += 1
                slf = frame.f_locals['self']
                if isinstance(slf, omtypes):
                    try:
                        obj = slf.msginfo
                    except Exception:
                        obj = type(slf).__name__
                else:
                    obj = type(slf).__name__
                if obj not in self.objs:
                    self.objs[obj] = len(self.objs)
                obj = self.objs[obj]

                func = frame.f_code.co_name
                if func not in self.functs:
                    self.functs[func] = len(self.functs)
                func = self.functs[func]

                data = self.struct.pack(fname, frame.f_lineno, func, frame.f_code.co_firstlineno, obj, is_root)
            else:
                data = self.struct.pack(fname, frame.f_lineno, -1, frame.f_code.co_firstlineno, -1, is_root)

            self.stream.write(data)
        finally:
            self._recording = False

    def _statprof_handler(self, sig, current_frame):
        self.samples_remaining -= 1
        if self._recording:
            return

        if self.samples_remaining <= 0 or self.stopping:
            signal.setitimer(StatisticalProfiler.MODES[self.mode][0], 0, 0)
            self.stopped = True
            return

        for tid, frame in iteritems(sys._current_frames()):
            while frame is not None:
                func = frame.f_code.co_name
                if func == '_statprof_py_file':
                    break
                if func != '_statprof_handler':
                    is_root = frame.f_back is not None and frame.f_back.f_code.co_name == '_statprof_py_file'
                    self.record(frame, int(is_root))
                frame = frame.f_back

        frame = None

        self.samples_taken += 1


def _statprof_setup_parser(parser):
    parser.add_argument('-i', '--interval', action='store', dest='interval', type=float,
                        default=.005, help='Sampling interval.')
    parser.add_argument('-d', '--duration', action='store', dest='duration', type=float,
                        default=30., help='Sampling duration in seconds. File will be executed multiple '
                        'times if duration has not been reached.')
    parser.add_argument('--sampling_mode', action='store', dest='sampling_mode',
                        default='virtual', help='Sampling mode. Must be one of ["prof", "virtual", "real"].')
    parser.add_argument('--groupby', action='store', dest='groupby', default='line', 
                        help='How to group stats. Must be one of ["instance", "line", "function", "instfunction"]')
    parser.add_argument('--no_browser', action='store_true', dest='noshow',
                        help="Don't pop up a browser to view the data.")
    parser.add_argument('-p', '--port', action='store', dest='port', type=int, default=8009, help='Web server port.')
    parser.add_argument('file', metavar='file', nargs='*',
                        help='Raw profile data file or a python file.')


def _statprof_exec(options, user_args):
    """
    Called from the command line (openmdao statprof command) to create a statistical profile.
    """

    if not options.file:
        print("No files to process.")
        sys.exit(0)

    if len(options.file) > 1:
        print("statprof can only process a single file.", file=sys.stderr)
        sys.exit(-1)

    if options.file[0].endswith('.py'):
        pyfile = options.file[0]
        outfile = 'statprof.raw'
        if MPI:
            outfile = outfile + '.' + str(MPI.COMM_WORLD.rank)

        samples_taken = _statprof_py_file(options, outfile, user_args)
    else:  # assume it's a raw statprof data file
        outfile = options.file[0]
        pyfile = None

    if options.noshow:
        _process_raw_statfile(outfile, options)
    else:
        view_statprof(options, pyfile, outfile)


def _statprof_setup():
    """
    A command to display source lines that allocate the most memory.
    """
    return (
        _statprof_setup_parser,
        _statprof_exec,
        "Run a statistical profiler on the given python script."
    )


def _get_statfile_name(options):
    return 'statprof_{}.out'.format(options.groupby)


def _rawfile_iter(fname, maps):
    fnames = maps['fnames']
    functs = maps['functs']
    objs = maps['objs']
    _struct = struct.Struct('H H i H i H')
    size = _struct.size
    with open(fname, 'rb') as f:
        while True:
            s = f.read(size)
            if len(s) == 0:
                break
            fname, lnum, func, funcstart, obj, frame_id = _struct.unpack(s)
            yield fnames[fname], lnum, functs[func], funcstart, objs[obj], frame_id


def _process_raw_statfile(fname, options):
    if options.groupby not in ('instance', 'line', 'instfunction'):
        raise RuntimeError("Illegal option for --groupby.  Must be 'instance', 'line', or 'function'.")

    total_hits = 0
    outstream = open(_get_statfile_name(options), 'w')
    dct = defaultdict(int)

    with open(fname + '.maps', 'rb') as f:
        maps = pickle.load(f)

    samples_taken = maps['samples_taken']

    if options.groupby == 'line':
        for fname, line_number, func, fstart, obj, frame_id in _rawfile_iter(fname, maps):
            dct[fname, line_number] += 1
        display_line_data(dct, samples_taken, outstream)
    elif options.groupby == 'instance':
        for fname, line_number, func, fstart, obj, frame_id in _rawfile_iter(fname, maps):
            dct[line_number, func, fstart, obj] += 1
        display_instance_data(dct, samples_taken, outstream)
    elif options.groupby == 'instfunction':
        for fname, line_number, func, fstart, obj, frame_id in _rawfile_iter(fname, maps):
            if func == '<module>':
                dct[fname, line_number] += 1
            else:
                dct[func, obj] += 1
        display_instance_func_data(dct, samples_taken, outstream)

    outstream.close()


def display_line_data(dct, total_hits, stream=sys.stdout):
    for key, hits in sorted(dct.items(), key=lambda x: x[1]):
        print("{}  {} hits  {:<5.2f}%".format(key, hits, hits/total_hits*100), 
              file=stream)

def display_instance_data(dct, total_hits, stream=sys.stdout):
    for key, hits in sorted(dct.items(), key=lambda x: x[1]):
        print("{}  {} hits  {:<5.2f}%".format(key, hits, hits/total_hits*100),
              file=stream)

def display_instance_func_data(dct, total_hits, stream=sys.stdout):
    for key, hits in sorted(dct.items(), key=lambda x: x[1]):
        print("{}  {} hits  {:<5.2f}%".format(key, hits, hits/total_hits*100),
              file=stream)


def _statprof_py_file(options, outfile, user_args):
    """
    Run statistical profiling on the given python script.

    Parameters
    ----------
    options : argparse Namespace
        Command line options.
    outfile : str
        Output filename.
    user_args : list of str
        Command line options after '--' (if any).  Passed to user script.

    Returns
    -------
    int
        Total number of samples taken.
    """
    progname = options.file[0]
    sys.path.insert(0, os.path.dirname(progname))

    # update sys.argv in case python script takes cmd line args
    sys.argv[:] = [progname] + user_args

    with open(progname, 'rb') as fp:
        code = compile(fp.read(), progname, 'exec')

    prof = StatisticalProfiler(outfile, interval=options.interval, 
                               mode=options.sampling_mode)
    prof.start(duration=options.duration)

    while not (prof.stopped or prof.stopping):
        globals_dict = {
            '__file__': progname,
            '__name__': '__main__',
            '__package__': None,
            '__cached__': None,
        }

        exec (code, globals_dict)

    prof.stop()

    return prof.samples_taken



# # generic stat profiler.  will work on Windows as well, but has lower resolution
# class StatisticalProfiler_old(object):
#     def __init__(self, sleep_interval=0.01):
#         self._sleep_interval = sleep_interval
#         self._stopped = True
#         self._prof_thread = None
#         self._stats = defaultdict(int)

#     def start(self):
#         print("starting")
#         self._stopped = False
#         self._prof_thread = self.start_thread(self.collecting)

#     def stop(self):
#         self._stopped = True
#         self._prof_thread.join()
#         self._prof_thread = None
#         import pprint
#         pprint.pprint(self._stats)
#         print("stop complete")

#     def save(self):
#         pass

#     def shutdown(self):
#         pass

#     def collecting(self):
#         while True:
#             if self._stopped:
#                 break
#             sleep(self._sleep_interval)
#             self.collect_frame_data()

#     def record(self, frame):
#         if 'self' in frame.f_locals and frame.f_locals['self'] is not self:
#             name = type(frame.f_locals['self']).__name__ + '.' + frame.f_code.co_name
#             self._stats[name] += 1
#             print(name, self._stats[name])

#     def collect_frame_data(self):
#         switch_interval = getswitchinterval()
#         try:
#             setswitchinterval(10000)
#             for frame in _current_frames().values():
#                 self.record(frame)
#         finally:
#             setswitchinterval(switch_interval)

#     def start_thread(self, fn):
#         """
#         Start a daemon thread running the given function.
#         """
#         thread = threading.Thread(target=fn)
#         thread.setDaemon(True)
#         thread.start()
#         return thread
