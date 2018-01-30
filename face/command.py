
import sys
from collections import OrderedDict

from utils import unwrap_text
from parser import Parser, Flag, ArgumentParseError, FaceException
from middleware import make_middleware_chain, check_middleware, face_middleware, inject, _BUILTIN_PROVIDES


class CommandLineError(FaceException, SystemExit):
    pass


def _get_default_name(frame_level=1):
    # TODO: is this a good idea? What if multiple parsers are created
    # in the same function for the sake of subparsers. This should
    # probably only be used from a classmethod or maybe a util
    # function.  TODO: what happens if a python module file contains a
    # non-ascii character?
    frame = sys._getframe(frame_level + 1)
    mod_name = frame.f_globals.get('__name__')
    if mod_name is None:
        return 'COMMAND'
    module = sys.modules[mod_name]
    if mod_name == '__main__':
        return module.__file__
    # TODO: reverse lookup entrypoint?
    return mod_name


def _docstring_to_desc(func):
    doc = func.__doc__
    if not doc:
        return ''

    unwrapped = unwrap_text(doc)
    try:
        first_graf = [g for g in unwrapped.splitlines() if g][0]
    except IndexError:
        return ''

    ret = first_graf[:first_graf.find('.')][:80]
    return ret


class Command(object):
    def __init__(self, func, name=None, desc=None, pos_args=False, middlewares=None):
        name = name if name is not None else _get_default_name()

        if desc is None:
            desc = _docstring_to_desc(func)

        self._parser = Parser(name, desc, pos_args=pos_args)
        # TODO: properties for name/desc/other parser things

        self.path_func_map = OrderedDict()
        self.path_func_map[()] = func

        middlewares = list(middlewares or [])
        self.path_mw_map = OrderedDict()
        self.path_mw_map[()] = []
        self._path_wrapped_map = OrderedDict()
        self._path_wrapped_map[()] = func
        for mw in middlewares:
            self.add_middleware(mw)
        return

    @property
    def name(self):
        return self._parser.name

    @property
    def func(self):
        return self.path_func_map[()]

    @property
    def parser(self):
        return self._parser

    def add(self, *a, **kw):
        subcmd = a[0]
        if not isinstance(subcmd, Command) and callable(subcmd):
            subcmd = Command(*a, **kw)  # attempt to construct a new subcmd
        if isinstance(subcmd, Command):
            self.add_command(subcmd)
            return subcmd
        flag = a[0]
        if not isinstance(flag, Flag):
            flag = Flag(*a, **kw)  # attempt to construct a Flag from arguments
        self._parser.add(flag)

        return flag

    def add_command(self, subcmd):
        self._parser.add(subcmd.parser)
        # map in new functions
        for path in self._parser.subprs_map:
            if path not in self.path_func_map:
                self.path_func_map[path] = subcmd.path_func_map[path[1:]]
                self.path_mw_map[path] = subcmd.path_mw_map[path[1:]]
        return

    def add_middleware(self, mw):
        if not getattr(mw, 'is_face_middleware', None):
            mw = face_middleware(mw)
        check_middleware(mw)
        _res = []
        # make sure all wrapping succeeds before making changes to the
        # local object
        for path, func in self.path_func_map.items():
            cur_mws = self.path_mw_map[path]
            new_mws = [mw] + cur_mws
            wrapped = make_middleware_chain(new_mws, func, _BUILTIN_PROVIDES)
            _res.append((path, new_mws, wrapped))

        for path, new_mws, wrapped in _res:
            self.path_mw_map[path] = new_mws
            self._path_wrapped_map[path] = wrapped

        return

    def run(self, argv=None):
        # TODO: turn parse exceptions into nice error messages
        try:
            prs_res = self._parser.parse(argv=argv)
        except ArgumentParseError as ape:
            msg = 'error: ' + self.name
            if getattr(ape, 'subcmds', None):
                msg += ' ' + ' '.join(ape.subcmds or ())
            msg += ': ' + ape.message
            cle = CommandLineError(msg)
            print msg  # stderr
            raise cle

        func = self.path_func_map[prs_res.cmd]
        wrapped = self._path_wrapped_map.get(prs_res.cmd, func)
        return wrapped(prs_res)


"""Middleware thoughts:

* Clastic-like, but single function
* Mark with a @middleware(provides=()) decorator for provides

* Keywords (ParseResult members) end with _ (e.g., flags_), leaving
  injection namespace wide open for flags. With clastic, argument
  names are primarily internal, like a path parameter's name is not
  exposed to the user. With face, the flag names are part of the
  exposed API, and we don't want to reserve keywords or have
  excessively long prefixes.

* add() supports @middleware decorated middleware

* add_middleware() exists for non-decorated middleware functions, and
  just conveniently calls middleware decorator for you (decorator only
  necessary for provides)

Also Kurt says an easy way to access the subcommands to tweak them
would be useful. I think it's better to build up from the leaves than
to allow mutability that could trigger rechecks and failures across
the whole subcommand tree. Better instead to make copies of
subparsers/subcommands/flags and treat them as internal state.


TODO:

In addition to the existing function-as-first-arg interface, Command
should take a list of add()-ables as the first argument. This allows
easy composition from subcommands and common flags.

# What goes in a bound command?

* name
* description
* handler func
* list of middlewares
* parser (currently contains the following)
    * flag map
    * PosArgSpecs for pos_args, trailing_args
    * flagfile flag
    * help flag (or help subcommand)

TODO: allow user to configure the message for CommandLineErrors
TODO: should Command take resources?
TODO: should version_ be a built-in/injectable?
"""
