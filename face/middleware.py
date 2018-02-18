
from face.parser import Flag
from face.sinter import make_chain, get_arg_names, getargspec, inject, get_func_name


INNER_NAME = 'next_'

_BUILTIN_PROVIDES = [INNER_NAME, 'args_', 'cmd_', 'subcmds_',
                     'flags_', 'posargs_', 'post_posargs_',
                     'command_']


def is_middleware(target):
    if callable(target) and getattr(target, 'is_face_middleware', None):
        return True
    return False


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
    flags = list(kwargs.pop('flags', []))
    if flags:
        for flag in flags:
            if not isinstance(flag, Flag):
                raise TypeError('expected Flag object, not: %r' % flag)
    if kwargs:
        raise TypeError('unexpected keyword arguments: %r' % kwargs.keys())

    def decorate_face_middleware(func):
        check_middleware(func, provides=provides)
        func.is_face_middleware = True
        func._face_flags = list(flags)
        func._face_provides = list(provides)
        return func

    if args and callable(args[0]):
        return decorate_face_middleware(args[0])

    return decorate_face_middleware


def resolve_middleware_chain(middlewares, innermost, preprovided):
    mw_avail = set(preprovided) - set([INNER_NAME])
    mw_provides = [mw._face_provides for mw in middlewares]

    return make_chain(middlewares, mw_provides, innermost, mw_avail, INNER_NAME)


def get_middleware_chain(middlewares, innermost, preprovided):
    _inner_exc_msg = "argument %r reserved for middleware use only (%r)"
    if INNER_NAME in get_arg_names(innermost):
        raise NameError(_inner_exc_msg % (INNER_NAME, innermost))

    mw_chain, mw_chain_args, mw_unres = resolve_middleware_chain(middlewares,
                                                                 innermost,
                                                                 preprovided)

    if mw_unres:
        raise NameError("unresolved request middleware arguments: %r"
                        % sorted(mw_unres))
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
