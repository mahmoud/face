
import itertools
from sinter import make_chain, get_arg_names, inject


INNER_NAME='next_'


def face_middleware(func):
    # TODO (needs provides arg)
    func.is_face_middleware = True
    func._face_provides = []
    return func


def make_middleware_chain(middlewares, innermost, preprovided):
    _inner_exc_msg = "argument %r reserved for middleware use only (%r)"
    if INNER_NAME in get_arg_names(innermost):
        raise NameError(_inner_exc_msg % (INNER_NAME, innermost))

    mw_avail = set(preprovided) - set([INNER_NAME])
    mw_provides = [mw._face_provides for mw in middlewares]

    mw_chain, mw_chain_args, mw_unres = make_chain(middlewares,
                                                   mw_provides,
                                                   innermost,
                                                   mw_avail,
                                                   INNER_NAME)
    if mw_unres:
        raise NameError("unresolved request middleware arguments: %r"
                        % list(mw_unres))
    return mw_chain


def check_middleware(func, next_name=INNER_NAME):
    # TODO: raise errors on *args and **kwargs
    if not callable(func):
        raise TypeError('expected middleware %r to be a function' % func)
    if not get_arg_names(func)[0] == next_name:
        raise TypeError("middleware function %r must take argument"
                        " '%s' as the first parameter"
                        % (func, next_name))
    return
