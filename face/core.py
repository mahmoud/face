
import re
import sys
import keyword

from collections import OrderedDict

from boltons.dictutils import OrderedMultiDict as OMD


class Command(object):
    def __init__(self, name, desc, func):
        name = name if name is not None else _get_default_name()
        self._parser = Parser(name, desc)
        # TODO: properties for name/desc/other parser things
        self.func = func


def _get_default_name(frame_level=1):
    frame = sys._getframe(frame_level + 1)
    mod_name = frame.f_globals.get('__name__')
    if mod_name is None:
        return 'COMMAND'
    module = sys.modules[mod_name]
    if mod_name == '__main__':
        return module.__file__
    # TODO: reverse lookup entrypoint?
    return mod_name


# keep it just to subset of valid python identifiers for now
# TODO: switch [A-z] to [^\W\d_] for unicode support in future?
_VALID_FLAG_RE = re.compile(r"^[A-z][-_A-z0-9]*\Z")


def flag_to_attr_name(flag):
    # validate and canonicalize flag name. Basically, subset of valid
    # Python variable identifiers.
    #
    # Only letters, numbers, '-', and/or '_'. Only single/double
    # leading dash allowed (-/--). No trailing dashes or
    # underscores. Must not be a Python keyword.
    if not flag or not isinstance(flag, str):
        raise ValueError('expected non-zero length string for flag, not: %r' % flag)
    # TODO: possible exception, bare '--' used to separate args, but
    # this should be a builtin
    if flag.endswith('-') or flag.endswith('_'):
        raise ValueError('expected flag without trailing dashes'
                         ' or underscores, not: %r' % flag)

    lstripped = flag.lstrip('-')
    flag_match = _VALID_FLAG_RE.match(lstripped)
    if not flag_match:
        raise ValueError('valid flags must begin with one or two dashes, '
                         ' followed by a letter, and consist only of'
                         ' letters, digits, underscores, and dashes, not: %r'
                         % flag)
    len_diff = len(flag) - len(lstripped)
    if len_diff == 0 or len_diff > 2:
        raise ValueError('expected flag to start with "-" or "--", not: %r'
                         % flag)
    if len_diff == 1 and len(lstripped) > 1:
        raise ValueError('expected single-dash flag to consist of a single'
                         ' character, not: %r' % flag)

    flag_name = _normalize_flag_name(flag)

    if keyword.iskeyword(flag_name):
        raise ValueError('valid flags must not be a Python keyword: %r'
                         % flag)

    return flag_name


def _normalize_flag_name(flag):
    ret = flag.lstrip('-')
    if (len(flag) - len(ret)) > 1:
        # only single-character flags are considered case-sensitive (like an initial)
        ret = ret.lower()
    ret = ret.replace('-', '_')
    return ret


# TODO: CLISpec may be a better name for the top-level object
class Parser(object):
    """
    Parser parses, Command parses with Parser, then dispatches.
    """
    def __init__(self, name=None, desc=None, pos_args=None):
        if name is None:
            name = _get_default_name()
        self.name = name
        self.desc = desc

        self.subcmd_map = OrderedDict()
        self.flag_map = OrderedDict()
        self.flagfile_flag = Flag('--flagfile', parse_as=str, on_duplicate='add')
        # for now, assume this will accept a string as well as None/bool,
        # for use as the display name
        self.pos_args = pos_args

    def add(self, *a, **kw):
        if isinstance(a[0], Parser):
            prs = a[0]
            if self.pos_args:
                raise ValueError('commands accepting positional arguments'
                                 ' cannot take subcommands')
            # Copy in subcommands, checking for conflicts the name
            # comes from the parser, so if you want to add it as a
            # different name, make a copy of the parser.
            self.subcmd_map[prs.name] = prs
            return

        if isinstance(a[0], Flag):
            flag = a[0]
        else:
            try:
                flag = Flag(*a, **kw)
            except TypeError as te:
                raise ValueError('expected Parser, Flag, or Flag parameters,'
                                 ' not: %r, %r (got %r)' % (a, kw, te))

        # first check there are no conflicts...
        flag_name = flag_to_attr_name(flag.name)
        if flag_name in self.flag_map:
            # TODO: need a better error message here, one that
            # properly exposes the existing flag (same goes for
            # aliases below)
            raise ValueError('duplicate definition for flag name: %r' % flag_name)
        for alias in flag.alias_list:
            if flag_to_attr_name(alias) in self.flag_map:
                raise ValueError('conflicting alias for flag %r: %r' % (flag_name, alias))

        # ... then we add the flags
        self.flag_map[flag_name] = flag
        for alias in flag.alias_list:
            self.flag_map[flag_to_attr_name(alias)] = flag

        return

    def parse(self, argv):
        if argv is None:
            argv = sys.argv

        cmd_path = []
        flag_map = OMD()
        pos_args = []
        for i, arg in enumerate(argv):
            if not arg:
                pass # is this possible?
            elif arg in self.subcmd_map:
                cmd_path.append(arg)
                subprs = self.subcmd_map[arg]
                subcmd_args = subprs.parse(argv[i:])
                cmd_path.extend(subcmd_args.cmd)
                flag_map.update(subcmd_args.flags.items(multi=True))
                pos_args.extend(subcmd_args.args)
                break
            elif arg[0] == '-':
                # check presence in flag map, strip dashes
                # if arg == '-V':
                #    import pdb;pdb.set_trace()
                flag = self.flag_map.get(_normalize_flag_name(arg))
                if flag is None:
                    raise ValueError('unknown flag: %s' % arg)
                flag_key = _normalize_flag_name(flag.name)

                flag_conv = flag.parse_as
                if callable(flag_conv):
                    try:
                        arg_text = argv[i + 1]
                    except IndexError:
                        raise ValueError('expected argument for flag %r' % arg)
                    try:
                        arg_val = flag_conv(arg_text)
                    except Exception:
                        raise ValueError('flag %s converter (%r) failed to parse argument: %r'
                                         % (arg, flag_conv, arg_text))
                    flag_map.add(flag_key, arg_val)
                else:
                    # e.g., True is effectively store_true, False is effectively store_false
                    flag_map.add(flag_key, flag_conv)
            elif False:  # TODO: flagfile
                pass
            else:
                if self.pos_args:
                    pos_args.extend(argv[i:])
                    break
        # TODO: check for required
        # TODO: resolve dupes
        args = CommandArguments(cmd_path, flag_map, pos_args)
        return args


# TODO: default
class Flag(object):
    def __init__(self, name, parse_as=True, required=False, alias=None, display_name=None, on_duplicate=None):
        # None = no arg
        # 'int' = int, 'float' = float, 'str' = str
        # List(int, sep=',', trim=True)  # see below
        # other = single callable
        self.name = name
        if not alias:
            alias = []
        elif isinstance(alias, str):
            alias = [alias]
        self.alias_list = list(alias)
        self.display_name = display_name or name
        self.parse_as = parse_as
        self.required = required
        # duplicates raise error by default
        # also have convenience param values: 'error'/'add'/'replace'
        # otherwise accept callable that takes argument + ArgResult
        self.on_duplicate = on_duplicate


class ListParam(object):
    def __init__(self, arg_type=str, sep=',', trim=True):
        "basically a CSV as a parameter"
        # trim = trim each parameter in the list before calling arg_type


class CommandArguments(object):
    def __init__(self, cmd_path, flag_map, pos_args):
        self.cmd = tuple(cmd_path)
        self.flags = dict(flag_map)
        self.args = tuple(pos_args or ())

    def __getattr__(self, name):
        """TODO: how to provide easy access to flag values while also
        providing access to "args" and "cmd" members. Could treat them
        as reserved keywords. Could "_"-prefix them. Could "_"-suffix
        them. Could "_"-suffix conflicting args so they'd still be
        accessible.

        Could return three things from parse(), but still have
        this issue when it comes to deciding what name to inject them
        as. probably need to make a reserved keyword.

        """
        return self.flags.get(_normalize_flag_name(name))


"""# Problems with argparse

argparse is a pretty solid library, and despite many competitors over
the years, the best argument parsing library available. Until now, of
course. Here's an inventory of problems argparse did not solve, and in
many ways, created.

* "Fuzzy" flag matching
* Inconvenient subcommand interface
* Flags at each level of the subcommand tree
* Positional arguments acceptable everywhere
* Bad help rendering (esp for subcommands)
* Inheritance-based API for extension with a lot of _*

At the end of the day, the real sin of argparse is that it enables the
creation of bad CLIs, often at the expense of ease of making good UIs
Despite this friction, argparse is far from infinitely powerful. As a
library, it is still relatively opinionated, and can only model a
somewhat-conventional UNIX-y CLI.

"""

x = 0

"""
clastic calls your function for you, should this do that, too?  is
there an advantage to sticking to the argparse route of handing back
a namespace? what would the signature of a CLI route be?
"""

x = 1

"""

* Specifying the CLI
* Wiring up the routing/dispatch
* OR Using the programmatic result of the parse (the Result object)
* Formatting the help messages?
* Using the actual CLI

"""

x = 2

"""

# "Types" discussion

* Should we support arbitrary validators (schema?) or go the clastic route and only basic types:
  * str
  * int
  * float
  * bool (TODO: default to true/false, think store_true, store_false in argparse)
  * list of the above
  * (leaning toward just basic types)


"""

x = 3

"""

- autosuggest on incorrect subcommand
- allow subcommand grouping
- hyphens and underscores equivalent for flags and subcommands

"""

x = 4

"""TODO: thought experiment

What about instead of requiring an explicit dependence up front,
provider functions had access to the current state and could raise a
special exception that simply said "wait". As long as we didn't
complete a full round of "waits", we'd be making progress.

There will of course be exceptions for stop/failure/errors.

Is this a bad design, or does it help with nuanced dependency
situations?

"""

x = 5

"""A command cannot have positional arguments _and_ subcommands.

Need to be able to set display name for pos_args

Which is the best default behavior for a flag? single flag where
presence=True (e.g., --verbose) or flag which accepts single string
arg (e.g., --path /a/b/c)

What to do if there appears to be flags after positional arguments?
How to differentiate between a bad flag and a positional argument that
starts with a dash?

"""

x = 6

""""Face: the CLI framework that's friendly to your end-user."

(Note: need to do some research re: non-unicode flags to see how much
non-US CLI users care about em.)

Case-sensitive flags are bad for business *except for*
single-character flags (single-dash flags like -v vs -V).

"""
