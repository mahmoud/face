
import itertools
from sinter import make_chain, get_arg_names, INNER_NAME


# TODO: INNER_NAME may have to be inner_ (or next_ ?)
def make_middleware_chain(middlewares, innermost, preprovided):
    _inner_exc_msg = "argument %r reserved for middleware use only (%r)"
    if INNER_NAME in get_arg_names(innermost):
        raise NameError(_inner_exc_msg % (INNER_NAME, innermost))

    mw_avail = set(preprovided) - set([INNER_NAME])
    mw_provides = [mw.provides for mw in mw]

    mw_chain, mw_chain_args, mw_unres = make_chain(middlewares,
                                                   mw_provides,
                                                   innermost,
                                                   mw_avail)
    if mw_unres:
        raise NameError("unresolved request middleware arguments: %r"
                        % list(mw_unres))
    return mw_chain
