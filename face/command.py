
import sys
from collections import OrderedDict

from utils import unwrap_text
from parser import Parser, Flag, ArgumentParseError, FaceException
from middleware import (inject,
                        is_middleware,
                        face_middleware,
                        check_middleware,
                        make_middleware_chain,
                        _BUILTIN_PROVIDES)


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
    def __init__(self, func, name=None, desc=None, posargs=False, middlewares=None):
        name = name if name is not None else _get_default_name()

        if desc is None:
            desc = _docstring_to_desc(func)

        self._parser = Parser(name, desc, posargs=posargs)
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
            if is_middleware(subcmd):
                return self.add_middleware(subcmd)

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
        self_mw = self.path_mw_map[()]
        self._parser.add(subcmd.parser)
        # map in new functions
        for path in self._parser.subprs_map:
            if path not in self.path_func_map:
                self.path_func_map[path] = subcmd.path_func_map[path[1:]]
                sub_mw = subcmd.path_mw_map[path[1:]]
                self.path_mw_map[path] = self_mw + sub_mw  # TODO: check for conflicts
        return

    def add_middleware(self, mw):
        if not is_middleware(mw):
            mw = face_middleware(mw)
        check_middleware(mw)

        for path, mws in self.path_mw_map.items():
            self.path_mw_map[path] = [mw] + mws

        return

    def prepare(self, paths=None):
        if paths is None:
            paths = self.path_func_map.keys()

        for path, func in self.path_func_map.items():
            mws = self.path_mw_map[path]
            flag_names = self.parser.path_flag_map[path].keys()
            provides = _BUILTIN_PROVIDES + flag_names
            wrapped = make_middleware_chain(mws, func, provides)

            self._path_wrapped_map[path] = wrapped

        return

    def run(self, argv=None, extras=None):
        kwargs = dict(extras) if extras else {}
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

        if self._parser.help_flag and prs_res.flags.get(self._parser.help_flag.attr_name):
            # TODO: should the "help" path go through middlewares of any sort?
            print 'help!'
            # argparse exits 0 on help
            sys.exit(0)

        self.prepare(paths=[prs_res.subcmds])

        # default in case no middlewares have been installed
        func = self.path_func_map[prs_res.subcmds]
        wrapped = self._path_wrapped_map.get(prs_res.subcmds, func)

        kwargs.update({'args_': prs_res,
                       'cmd_': self,  # TODO: see also command_, should this be prs_res.name, or argv[0]?
                       'subcmds_': prs_res.subcmds,
                       'flag_map_': prs_res.flags,
                       'posargs_': prs_res.posargs,
                       'post_posargs_': prs_res.post_posargs,
                       'command_': self,
                       'parser_': self._parser})  # TODO: parser necessary?
        kwargs.update(prs_res.flags)

        return inject(wrapped, kwargs)


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
    * PosArgSpecs for posargs, post_posargs
    * flagfile flag
    * help flag (or help subcommand)

TODO: allow user to configure the message for CommandLineErrors
TODO: should Command take resources?
TODO: should version_ be a built-in/injectable?

Need to split up the checks. Basic verification of middleware
structure OK. Can check for redefinitions of provides and
conflicts. Need a final .check() method that checks that all
subcommands have their requirements fulfilled. Technically a .run()
only needs to run one specific subcommand, only thta one needs to get
its middleware chain built. .check() would have to build/check them
all.

Different error message for when the command's handler function is
unfulfilled vs middlewares.

DisplayOptions/DisplaySpec class? (display name and hidden)

Should Commands have resources like clastic?

# TODO: need to check for middleware provides names + flag names
# conflict

"""
