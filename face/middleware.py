
import itertools
from sinter import make_chain, get_arg_names, getargspec, inject, get_func_name


INNER_NAME = 'next_'
# TODO: might need to make pos_args_ nicer
_BUILTIN_PROVIDES = ['next_', 'args_', 'cmd_', 'subcmds_',
                     'flag_map_', 'pos_args_', 'trailing_args_',
                     'command_', 'parser_']


def face_middleware(*args, **kwargs):
    """Mark a function as face middleware, which wraps execution of a
    subcommand handler function.

    The first argument of a middleware function must be named
    "next_". This argument is a function, representing the next
    function in, toward execution of the endpoint.

    Use the provides keyword argument to specify a list of arguments
    this function can inject for the handler function and other
    middlewares.

    """
    provides = kwargs.pop('provides', [])
    if isinstance(provides, basestring):
        provides = [provides]

    if kwargs:
        raise TypeError('unexpected keyword arguments: %r' % kwargs.keys())

    def decorate_face_middleware(func):
        check_middleware(func, provides=provides)
        func.is_face_middleware = True
        func._face_provides = provides
        return func

    if args and callable(args[0]):
        return decorate_face_middleware(args[0])

    return decorate_face_middleware


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


def check_middleware(func, provides=None):
    if not callable(func):
        raise TypeError('expected middleware %r to be a function' % func)
    func_name = get_func_name(func)
    argspec = getargspec(func)
    arg_names = argspec.args
    if not arg_names:
        raise TypeError('middleware function %r must take at least one'
                        ' argument "%s" as its first parameter'
                        % (func_name, INNER_NAME))
    if arg_names[0] != INNER_NAME:
        raise TypeError('middleware function %r must take argument'
                        ' "%s" as the first parameter, not "%s"'
                        % (func_name, INNER_NAME, arg_names[0]))
    if argspec.varargs:
        raise TypeError('middleware function %r may only take explicitly'
                        ' named arguments, not "*%s"' % (func_name, argspec.varargs))
    if argspec.keywords:
        raise TypeError('middleware function %r may only take explicitly'
                        ' named arguments, not "**%s"' % (func_name, argspec.keywords))

    provides = provides if provides is not None else func._face_provides
    conflict_args = list(set(_BUILTIN_PROVIDES) & set(provides))
    if conflict_args:
        raise TypeError('middleware function %r provides conflict with'
                        ' reserved face builtins: %r' % (func_name, conflict_args))

    return


"""
    if not getattr(func, 'is_face_middleware', None):
        raise TypeError('expected face middleware function, not: %r'
                        ' (try decorating with @face_middleware)' % func_name)
"""
