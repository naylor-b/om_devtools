
import atexit
from functools import wraps, partial
from inspect import signature
from collections import Counter, defaultdict


_total_arg_type_counts = defaultdict(dict)
_do_atc_atexit = True


def _dump_typ_counts():
    """
    Take any collected arg type counts and print them out.
    """
    global _total_arg_type_counts
    if _total_arg_type_counts:
        for funcname, counters in _total_arg_type_counts.items():
            keep = False
            for counter in counters.values():
                if counter:
                    keep = True
                    break
            if keep:
                print("Function", funcname)
                for argname, counter in counters.items():
                    if counter:
                        print(f"{argname}:", counter.most_common())


def _save_typ_counts_atexit(funcname, type_counts):
    global _total_arg_type_counts
    counts = _total_arg_type_counts[funcname]
    if not counts:
        for n, c in type_counts:
            counts[n] = c
    else:
        cdict = counts
        for n, cnt in type_counts:
            if n not in cdict:
                cdict[n] = cnt
            else:
                cdict[n].update(cnt)


def save_arg_type_counts(fnc):
    """
    Keep track of the count of the types passed as each argument of a decorated function.

    Parameters
    ----------
    fnc : function
        The function to be decorated.

    Returns
    -------
    function
        The function wrapper.
    """
    global _do_atc_atexit
    if _do_atc_atexit:
        # register _dump_typ_counts before any save_arg_type_counts is called so
        # _dump_typ_counts will always be called last.
        atexit.register(_dump_typ_counts)
        _do_atc_atexit = False

    _typcounts = [(n, Counter()) for n in signature(fnc).parameters]
    atexit.register(partial(_save_typ_counts_atexit, fnc.__name__, _typcounts))

    @wraps(fnc)
    def _wrap(*args, **kwargs):
        for i, a in enumerate(args):
            _typcounts[i][1][type(a).__name__] += 1
        for i, val in enumerate(kwargs.values()):
            _typcounts[i][1][type(val).__name__] += 1
        return fnc(*args, **kwargs)
    return _wrap


