
import re
import sys
import keyword

from collections import OrderedDict

from boltons.iterutils import split, unique
from boltons.typeutils import make_sentinel
from boltons.dictutils import OrderedMultiDict as OMD


ERROR = make_sentinel('ERROR')


class FaceException(Exception):
    pass


# Not inheriting from SystemExit here; the exiting behavior will be
# handled by the Command dispatcher
class ArgumentParseError(FaceException):
    pass


class UnexpectedArgs(ArgumentParseError):
    pass


class InvalidSubcommand(ArgumentParseError):
    @classmethod
    def from_parse(cls, prs, subcmd_name):
        # TODO: add edit distance calculation
        valid_subcmds = unique([path[:1][0] for path in prs.subprs_map.keys()])
        msg = ('unknown subcommand "%s", choose from: %s'
               % (subcmd_name, ', '.join(valid_subcmds)))
        return cls(msg)


class UnknownFlag(ArgumentParseError):
    @classmethod
    def from_parse(cls, cmd_flag_map, flag_name):
        # TODO: add edit distance calculation
        valid_flags = unique([flag.display_name for flag in
                              cmd_flag_map.values() if flag.display_name])
        msg = ('unknown flag "%s", choose from: %s'
               % (flag_name, ', '.join(valid_flags)))
        return cls(msg)


FRIENDLY_TYPE_NAMES = {int: 'integer',
                       float: 'decimal'}


class InvalidFlagArgument(ArgumentParseError):
    @classmethod
    def from_parse(cls, cmd_flag_map, flag, arg):
        if arg is None:
            return cls('expected argument for flag %s' % flag.name)

        val_parser = flag.parse_as
        vp_label = getattr(val_parser, 'display_name', FRIENDLY_TYPE_NAMES.get(val_parser))
        if vp_label is None:
            vp_label = repr(val_parser)
            tmpl = 'flag %s converter (%r) failed to parse value: %r'
        else:
            tmpl = 'flag %s expected a valid %s value, not %r'
        msg = tmpl % (flag.name, vp_label, arg)

        if arg.startswith('-'):
            msg += '. (Did you forget to pass an argument?)'

        return cls(msg)


class InvalidPositionalArgument(ArgumentParseError):
    @classmethod
    def from_parse(cls, posargspec, arg, exc):
        parse_as = posargspec.parse_as
        # TODO: type name if type, function name if function
        # TODO: "parse as" if type, "parse with" if function
        # TODO: do we need the underlying error message?
        friendly_name = FRIENDLY_TYPE_NAMES.get(parse_as, parse_as)
        return cls('positional argument failed to parse as'
                   ' %s: %r (got error: %r)' % (friendly_name, arg, exc))


class MissingRequiredFlags(ArgumentParseError):
    @classmethod
    def from_parse(cls, cmd_flag_map, parsed_flag_map, missing_flag_names):
        msg = ('missing required arguments for flags: %s'
               % ', '.join(missing_flag_names))
        return cls(msg)


class DuplicateFlagValue(ArgumentParseError):
    @classmethod
    def from_parse(cls, flag, arg_val_list):
        return cls('more than one value passed for flag %s: %r'
                   % (flag.name, arg_val_list))


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


def process_subcmd_name(name):
    # validate and canonicalize flag name. Basically, subset of valid
    # Python variable identifiers.
    #
    # Only letters, numbers, '-', and/or '_'. Only single/double
    # leading dash allowed (-/--). No trailing dashes or
    # underscores. Python keywords are allowed, as subcommands are
    # never used in injection.
    if not name or not isinstance(name, str):
        raise ValueError('expected non-zero length string for subcommand name, not: %r' % name)

    if name.endswith('-') or name.endswith('_'):
        raise ValueError('expected subcommand name without trailing dashes'
                         ' or underscores, not: %r' % name)

    name_match = _VALID_FLAG_RE.match(name)
    if not name_match:
        raise ValueError('valid subcommand name must begin with a letter, and'
                         ' consist only of letters, digits, underscores, and'
                         ' dashes, not: %r' % name)

    subcmd_name = _normalize_flag_name(name)

    return subcmd_name


def _normalize_flag_name(flag):
    ret = flag.lstrip('-')
    if (len(flag) - len(ret)) > 1:
        # only single-character flags are considered case-sensitive (like an initial)
        ret = ret.lower()
    ret = ret.replace('-', '_')
    return ret


def _arg_to_subcmd(arg):
    return arg.lower().replace('-', '_')


def _on_dup_error(flag, arg_val_list):
    if len(arg_val_list) > 1:
        raise DuplicateFlagValue.from_parse(flag, arg_val_list)
    return arg_val_list[0]


def _on_dup_extend(flag, arg_val_list):
    return arg_val_list


def _on_dup_override(flag, arg_val_list):
    return arg_val_list[-1]

# TODO: _on_dup_ignore?

_ON_DUP_SHORTCUTS = {'error': _on_dup_error,
                     'extend': _on_dup_extend,
                     'override': _on_dup_override}


class Flag(object):
    def __init__(self, name, parse_as=True, missing=None, alias=None,
                 display_name=None, on_duplicate='error'):
        self.name = name
        self.parse_as = parse_as
        self.missing = missing
        # TODO: parse_as=scalar + missing=ERROR seems like an invalid
        # case (a flag whose presence is always required? what's the
        # point?)
        if not alias:
            alias = []
        elif isinstance(alias, str):
            alias = [alias]
        self.alias_list = list(alias)
        self._display_name = display_name

        if callable(on_duplicate):
            self.on_duplicate = on_duplicate
        elif on_duplicate in _ON_DUP_SHORTCUTS:
            self.on_duplicate = _ON_DUP_SHORTCUTS[on_duplicate]
        else:
            raise ValueError('on_duplicate expected callable or one of %r, not: %r'
                             % (list(_ON_DUP_SHORTCUTS.keys()), on_duplicate))

    # TODO: __eq__ and copy

    @property
    def attr_name(self):
        return _normalize_flag_name(self.name)

    @property
    def display_name(self):
        orig_dn = self._display_name
        if orig_dn is False:
            return ''
        if orig_dn:
            return orig_dn
        if len(self.name) == 1:
            return '-' + self.name
        return self.name.replace('_', '-')


class PosArgSpec(object):
    def __init__(self, parse_as=None, min_count=None, max_count=None,
                 display_name='arg', display_full=None):
        self.parse_as = parse_as or str
        self.min_count = int(min_count) if min_count else 0
        self.max_count = int(max_count) if max_count else 0
        self.display_name = display_name
        self.display_full = display_full

        if self.max_count and self.min_count > self.max_count:
            raise ValueError('expected min_count > max_count, not: %r > %r'
                             % (self.min_count, self.max_count))
        if self.min_count < 0:
            raise ValueError('expected min_count >= 0, not: %r' % self.min_count)
        if self.max_count < 0:
            raise ValueError('expected min_count >= 0, not: %r' % self.max_count)

        # display_name='arg', min_count = 2, max_count = 3 ->
        # arg1 arg2 [arg3]

        # TODO: default? type check that it's a sequence matching min/max reqs


POSARGS_ENABLED = PosArgSpec()
FLAG_FILE_ENABLED = Flag('--flagfile', parse_as=str, on_duplicate='extend', missing=None, display_name='')
HELP_FLAG_ENABLED = Flag('--help', parse_as=True, alias='-h')


class Parser(object):
    """
    Parser parses, Command parses with Parser, then dispatches.
    """
    def __init__(self, name, desc=None, posargs=None):
        if not name or name[0] in ('-', '_'):
            # TODO: more complete validation
            raise ValueError('expected name beginning with ASCII letter, not: %r' % (name,))
        self.name = name
        self.desc = desc
        if posargs is True:
            posargs = POSARGS_ENABLED
        if posargs and not isinstance(posargs, PosArgSpec):
            raise ValueError('expected posargs as True, False,'
                             ' or instance of PosArgSpec, not: %r' % posargs)
        self.posargs = posargs

        self.help_flag = HELP_FLAG_ENABLED
        self.flagfile_flag = FLAG_FILE_ENABLED
        # TODO: should flagfile and help flags be hidden by default?

        self.subprs_map = OrderedDict()
        self.path_flag_map = OrderedDict()
        self.path_flag_map[()] = OrderedDict()

        if self.flagfile_flag:
            self.add(self.flagfile_flag)
        if self.help_flag:
            self.add(self.help_flag)
        return

    def _add_subparser(self, subprs):
        """Process subcommand name, check for subcommand conflicts, check for
        subcommand flag conflicts, then finally add subcommand.

        To add a command under a different name, simply make a copy of
        that parser or command with a different name.
        """
        if self.posargs:
            raise ValueError('commands accepting positional arguments'
                             ' cannot take subcommands')

        # validate that the subparser's name can be used as a subcommand
        subprs_name = process_subcmd_name(subprs.name)

        # then, check for conflicts with existing subcommands and flags
        for prs_path in self.subprs_map:
            if prs_path[0] == subprs_name:
                raise ValueError('conflicting subcommand name: %r' % subprs_name)
        parent_flag_map = self.path_flag_map[()]

        check_no_conflicts = lambda parent_flag_map, subcmd_path, subcmd_flags: True
        for path, flags in subprs.path_flag_map.items():
            if not check_no_conflicts(parent_flag_map, path, flags):
                # TODO
                raise ValueError('subcommand flags conflict with parent command: %r' % flags)

        # with checks complete, add parser and all subparsers
        self.subprs_map[(subprs_name,)] = subprs
        for subprs_path in subprs.subprs_map:
            new_path = (subprs_name,) + subprs_path
            self.subprs_map[new_path] = subprs

        # Flags inherit down (a parent's flags are usable by the child)
        for path, flags in subprs.path_flag_map.items():
            new_flags = parent_flag_map.copy()
            new_flags.update(flags)
            self.path_flag_map[(subprs_name,) + path] = new_flags

        # If two flags have the same name, as long as the "parse_as"
        # is the same, things should be ok. Need to watch for
        # overlapping aliases, too. This may allow subcommands to
        # further document help strings. Should the same be allowed
        # for defaults?

    def add(self, *a, **kw):
        """Add a flag or subparser. Unless the first argument is a Parser or
        Flag object, the arguments are the same as the Flag
        constructor, and will be used to create a new Flag instance to
        be added.
        """
        if isinstance(a[0], Parser):
            subprs = a[0]
            self._add_subparser(subprs)
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

        for subcmds, flag_map in self.path_flag_map.items():
            if flag_name in flag_map:
                # TODO: need a better error message here, one that
                # properly exposes the existing flag (same goes for
                # aliases below)
                raise ValueError('duplicate definition for flag name: %r' % flag_name)
            for alias in flag.alias_list:
                if flag_to_attr_name(alias) in flag_map:
                    raise ValueError('conflicting alias for flag %r: %r' % (flag_name, alias))

        # ... then we add the flags
        for flag_map in self.path_flag_map.values():
            flag_map[flag_name] = flag
            for alias in flag.alias_list:
                flag_map[flag_to_attr_name(alias)] = flag

        return

    def parse(self, argv):
        if argv is None:
            argv = sys.argv
        if not argv:
            raise ArgumentParseError('expected non-empty sequence of arguments, not: %r' % (argv,))

        # first snip off the first argument, the command itself
        cmd_name, args = argv[0], list(argv)[1:]

        # then figure out the subcommand path
        subcmds, args = self._parse_subcmds(args)
        prs = self.subprs_map[tuple(subcmds)] if subcmds else self

        try:
            # then look up the subcommand's supported flags
            cmd_flag_map = self.path_flag_map[tuple(subcmds)]

            # parse and validate the supported flags
            flag_map, posargs = self._parse_flags(cmd_flag_map, args)

            # separate out any trailing arguments from normal positional arguments
            post_posargs = None  # TODO: default to empty list? Rename to post_posargs?
            if '--' in posargs:
                posargs, post_posargs = split(posargs, '--', 1)

            if posargs:
                if not prs.posargs:
                    raise UnexpectedArgs('extra arguments passed: %r' % posargs)
                for pa in posargs:
                    try:
                        val = prs.posargs.parse_as(pa)
                    except Exception as exc:
                        raise InvalidPositionalArgument.from_parse(prs.posargs, pa, exc)
                posargs = [prs.posargs.parse_as(pa) for pa in posargs]
        except ArgumentParseError as ape:
            ape.parser = prs
            ape.subcmds = subcmds
            raise

        ret = CommandParseResult(cmd_name, subcmds, flag_map, posargs, post_posargs)
        return ret

    def _parse_subcmds(self, args):
        """Expects arguments after the initial command (i.e., argv[1:])

        Returns a tuple of (list_of_subcmds, remaining_args).

        Raises on unknown subcommands."""
        ret = []

        for arg in args:
            if not arg:
                continue # TODO: how bad of an idea is it to ignore this?
            if arg[0] == '-':
                break  # subcmd parsing complete

            arg = _arg_to_subcmd(arg)
            if tuple(ret + [arg]) not in self.subprs_map:
                prs = self.subprs_map[tuple(ret)] if ret else self
                if prs.posargs:
                    break
                raise InvalidSubcommand.from_parse(prs, arg)
            ret.append(arg)

        return ret, args[len(ret):]

    def _parse_flags(self, cmd_flag_map, args):
        """Expects arguments after the initial command and subcommands (i.e.,
        the second item returned from _parse_subcmds)

        Returns a tuple of (list_of_subcmds, remaining_args).

        Raises on unknown subcommands.
        """
        ret, idx = OMD(), 0

        _consumed_val = False
        for i, arg in enumerate(args):
            idx += 1
            if _consumed_val:
                _consumed_val = False
                continue
            if not arg:
                # TODO
                raise ArgumentParseError('unexpected empty arg between [...] and [...]')
            elif arg[0] != '-' or arg == '-' or arg == '--':
                # posargs or post_posargs beginning ('-' is a
                # conventional pos arg for stdin)
                idx -= 1
                break

            flag = cmd_flag_map.get(_normalize_flag_name(arg))
            if flag is None:
                raise UnknownFlag.from_parse(cmd_flag_map, arg)
            flag_key = flag.attr_name

            flag_conv = flag.parse_as
            if not callable(flag_conv):
                # e.g., True is effectively store_true, False is effectively store_false
                ret.add(flag_key, flag_conv)
                continue
            try:
                arg_text = args[i + 1]
            except IndexError:
                raise InvalidFlagArgument.from_parse(cmd_flag_map, flag, arg=None)
            try:
                arg_val = flag_conv(arg_text)
            except Exception:
                raise InvalidFlagArgument.from_parse(cmd_flag_map, flag, arg)
            ret.add(flag_key, arg_val)
            _consumed_val = True

        # take care of dupes and check required flags
        ret = self._resolve_flags(cmd_flag_map, ret)
        return ret, args[idx:]

    def _resolve_flags(self, cmd_flag_map, parsed_flag_map):
        # resolve dupes and then...
        ret = OrderedDict()
        cfm, pfm = cmd_flag_map, parsed_flag_map

        for flag_name in pfm:
            flag = cfm[flag_name]
            arg_val_list = pfm.getlist(flag_name)
            ret[flag_name] = flag.on_duplicate(flag, arg_val_list)

        # ... check requireds and set defaults.
        missing_flags = []
        for flag_name, flag in cfm.items():
            if flag_name in ret:
                continue
            if flag.missing is ERROR:
                missing_flags.append(flag.name)
            else:
                ret[flag_name] = flag.missing
        if missing_flags:
            raise MissingRequiredFlags(cfm, pfm, missing_flags)

        return ret



class ListParam(object):
    def __init__(self, arg_type=str, sep=',', trim=True):
        "basically a CSV as a parameter"
        # trim = trim each parameter in the list before calling arg_type


class FileValueParam(object):
    # Basically a file with a single value in it, like a pidfile
    # or a password file mounted in. Read in and treated like it
    # was on the argv.
    pass


class CommandParseResult(object):
    # TODO: add parser + argv
    def __init__(self, name, subcmds, flag_map, posargs, post_posargs):
        self.name = name
        self.subcmds = tuple(subcmds)
        self.flags = dict(flag_map)
        self.posargs = tuple(posargs or ())
        self.post_posargs = tuple(post_posargs or ())

    def __getattr__TODO(self, name):
        """TODO: how to provide easy access to flag values while also
        providing access to "args" and "cmd" members. Could treat them
        as reserved keywords. Could "_"-prefix them. Could "_"-suffix
        them. Could "_"-suffix conflicting args so they'd still be
        accessible.

        Could return three things from parse(), but still have
        this issue when it comes to deciding what name to inject them
        as. probably need to make a reserved keyword.

        Even if this result object doesn't have the __getattr__
        behavior, whatever does should have a better behavior than
        just KeyError or AttributeError. Perhaps a new error
        inheriting from those which also has a nice systemexit
        behavior re: missing arguments.

        This behavior could be keyed off of a private Source attribute
        which keeps track of whether the arguments were sys.argv, even.

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

4

"""A command cannot have positional arguments _and_ subcommands.

Need to be able to set display name for posargs

Which is the best default behavior for a flag? single flag where
presence=True (e.g., --verbose) or flag which accepts single string
arg (e.g., --path /a/b/c)

What to do if there appears to be flags after positional arguments?
How to differentiate between a bad flag and a positional argument that
starts with a dash?

"""

x = 6

""""Face: the CLI framework that's friendly to your end-user."

* Flag-first design that ensures flags stay consistent across all
  subcommands, for a more coherent API, less likely to surprise, more
  likely to delight.

(Note: need to do some research re: non-unicode flags to see how much
non-US CLI users care about em.)

Case-sensitive flags are bad for business *except for*
single-character flags (single-dash flags like -v vs -V).

TODO: normalizing subcommands

Should parse_as=List() with on_duplicate=extend give one long list or
a list of lists?

Parser is unable to determine which subcommands are valid leaf
commands, i.e., which ones can be handled as the last subcommand. The
Command dispatcher will have to raise an error if a specific
intermediary subcommand doesn't have a handler to dispatch to.

TODO: Duplicate arguments passed at the command line with the same value = ok?

"""

x = 7

"""strata-minded thoughts:

* will need to disable and handle flagfiles separately if provenance
is going to be retained?


clastic-related thoughts:

* middleware seems unavoidable for setting up logs and generic
  teardowns/exit messages
* Might need an error map that maps various errors to exit codes for
  convenience. Neat idea, sort a list of classes by class hierarchy.

"""

x = 8

"""There are certain parse errors, such as the omission of a value
that takes a string argument which can semi-silently pass. For instance:

copy --dest --verbose /a/b/c

In this terrible CLI, --verbose could be absorbed as --dest's value
and now there's a file called --verbose on the filesystem. Here are a
few ideas to improve the situation:

1. Raise an exception for all flags' string arguments which start with
   a "-". Create a separate syntax for passing these args such as
   --flag=--dashedarg.
2. Similar to the above, but only raise exceptions on known
   flags. This creates a bit of a moving API, as a new flag could cause
   old values to fail.
3. Let particularly bad APIs like the above fail, but keep closer
   track of state to help identify missing arguments earlier in the line.

"""

x = 9

"""One big difference between Clastic and Face is that with Face, you
typically know your first and only request at startup time. With
Clastic, you create an Application and have to wait for some remote
user to issue a request.

This translates to a different default behavior. With Clastic, all
routes are checked for dependency satisfaction at Application
creation. With Face, this check is performed on-demand, and only the
single subcommand being executed is checked.

"""
