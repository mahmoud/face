
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


class ArgumentParseError(FaceException):
    pass


class InvalidPosArgs(ArgumentParseError):
    pass


class TooManyArguments(InvalidPosArgs):
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
        valid_flags = unique([flag.display.name for flag in
                              cmd_flag_map.values() if not flag.display.hidden])
        msg = ('unknown flag "%s", choose from: %s'
               % (flag_name, ', '.join(valid_flags)))
        return cls(msg)


FRIENDLY_TYPE_NAMES = {int: 'integer',
                       float: 'decimal'}


class InvalidFlagArgument(ArgumentParseError):
    @classmethod
    def from_parse(cls, cmd_flag_map, flag, arg, exc=None):
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

        if exc:
            # TODO: put this behind a verbose flag?
            msg += ' (got error: %r)' % exc
        if arg.startswith('-'):
            msg += '. (Did you forget to pass an argument?)'

        return cls(msg)


def _get_type_desc(parse_as):
    if not callable(parse_as):
        raise TypeError('expected parse_as to be callable, not %r' % parse_as)
    try:
        return 'as', FRIENDLY_TYPE_NAMES[parse_as]
    except KeyError:
        pass
    try:
        # return the type name if it looks like a type
        return 'as', parse_as.__name__
    except AttributeError:
        pass
    try:
        # return the func name if it looks like a function
        return 'with', parse_as.func_name
    except AttributeError:
        pass
    # if all else fails
    return 'with', repr(parse_as)



class InvalidPositionalArgument(ArgumentParseError):
    @classmethod
    def from_parse(cls, posargspec, arg, exc):
        prep, type_desc = _get_type_desc(posargspec.parse_as)
        return cls('positional argument failed to parse %s'
                   ' %s: %r (got error: %r)' % (prep, type_desc, arg, exc))


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


def flag_to_identifier(flag):
    # validate and canonicalize flag name. Basically, subset of valid
    # Python variable identifiers.
    #
    # Only letters, numbers, '-', and/or '_'. Only single/double
    # leading dash allowed (-/--). No trailing dashes or
    # underscores. Must not be a Python keyword.
    orig_flag = flag
    if not flag or not isinstance(flag, str):
        raise ValueError('expected non-zero length string for flag, not: %r' % flag)

    if flag.endswith('-') or flag.endswith('_'):
        raise ValueError('expected flag without trailing dashes'
                         ' or underscores, not: %r' % orig_flag)

    if flag[:2] == '--':
        flag = flag[2:]

    flag_match = _VALID_FLAG_RE.match(flag)
    if not flag_match:
        raise ValueError('valid flag names must begin with a letter, optionally'
                         ' prefixed by two dashes, and consist only of letters,'
                         ' digits, underscores, and dashes, not: %r' % orig_flag)

    flag_name = _normalize_flag_name(flag)

    if keyword.iskeyword(flag_name):
        raise ValueError('valid flag names must not be Python keywords: %r'
                         % orig_flag)

    return flag_name


def identifier_to_flag(identifier):
    if identifier.startswith('-'):
        raise ValueError('expected identifier, not flag name: %r' % identifier)
    ret = identifier.lower().replace('_', '-')
    return '--' + ret


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


def _multi_error(flag, arg_val_list):
    if len(arg_val_list) > 1:
        raise DuplicateFlagValue.from_parse(flag, arg_val_list)
    return arg_val_list[0]


def _multi_extend(flag, arg_val_list):
    return arg_val_list


def _multi_override(flag, arg_val_list):
    return arg_val_list[-1]

# TODO: _multi_ignore?

_MULTI_SHORTCUTS = {'error': _multi_error,
                    False: _multi_error,
                    'extend': _multi_extend,
                    True: _multi_extend,
                    'override': _multi_override}


_VALID_CHARS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!*+./?@_'
def _validate_char(char):
    orig_char = char
    if char[0] == '-' and len(char) > 1:
        char = char[1:]
    if len(char) > 1:
        raise ValueError('char flags must be exactly one character, optionally'
                         ' prefixed by a dash, not: %r' % orig_char)
    if char not in _VALID_CHARS:
        raise ValueError('expected valid flag character (ASCII letters, numbers,'
                         ' or shell-compatible punctuation), not: %r' % orig_char)
    return char


# TODO: allow name="--flag / -F" and do the split for automatic
# char form?
class Flag(object):
    def __init__(self, name, parse_as=True, missing=None, doc=None, char=None,
                 display=None, multi='error'):
        self.name = flag_to_identifier(name)
        self.doc = doc
        self.parse_as = parse_as
        self.missing = missing
        # TODO: parse_as=scalar + missing=ERROR seems like an invalid
        # case (a flag whose presence is always required? what's the
        # point?)
        self.char = _validate_char(char) if char else None


        if callable(multi):
            self.multi = multi
        elif multi in _MULTI_SHORTCUTS:
            self.multi = _MULTI_SHORTCUTS[multi]
        else:
            raise ValueError('multi expected callable, bool, or one of %r, not: %r'
                             % (list(_MULTI_SHORTCUTS.keys()), multi))

        if display is None:
            display = {}
        elif isinstance(display, bool):
            display = {'hidden': not display}
        elif isinstance(display, str):
            display = {'name': display}
        if isinstance(display, dict):
            display = FlagDisplay(self, **display)
        self.display = display

    # TODO: __eq__ and copy

    def set_display(self, display):
        if display is None:
            display = {}
        elif isinstance(display, bool):
            display = {'hidden': not display}
        elif isinstance(display, str):
            display = {'name': display}
        if isinstance(display, dict):
            display = FlagDisplay(self, **display)
        if not isinstance(display, FlagDisplay):
            raise TypeError('expected bool, text name, dict of display'
                            ' options, or FlagDisplay instance, not: %r'
                            % display)
        self.display = display


class FlagDisplay(object):
    def __init__(self, flag, **kw):
        self.flag = flag
        self.name = kw.pop('name', flag.name)
        self._label = kw.pop('label', None)
        self.format_label = kw.pop('format_label', self.default_format_label)

        self.doc = flag.doc
        if self.doc is None and callable(flag.parse_as):
            _prep, desc = _get_type_desc(flag.parse_as)
            self.doc = 'Parsed with ' + desc
            if _prep == 'as':
                self.doc = desc

        self._post_doc = kw.pop('post_doc', None)
        self.format_post_doc = kw.pop('format_post_doc', self.default_format_post_doc)

        self._full_doc = kw.pop('full_doc', None)

        self.value_name = ''
        if callable(flag.parse_as):
            self.value_name = kw.pop('value_name', None) or self.flag.name.upper()

        self.group = kw.pop('group', 0)   # int or str
        self.hidden = kw.pop('hidden', False)  # bool
        self.sort_key = kw.pop('sort_key', 0)  # int or str

        if kw:
            TypeError('unexpected keyword arguments: %r' % kw.keys())
        return

    @property
    def label(self):
        if self._label is not None:
            return self._label
        return self.format_label()

    @label.setter
    def _set_label(self, val):
        self._label = val
        # stay hidden if set to hidden, else hide if empty
        self.hidden = self.hidden or (not val)

    def default_format_label(self):
        parts = [identifier_to_flag(self.flag.name)]
        if self.flag.char:
            parts.append('-' + self.flag.char)
        ret = ' / '.join(parts)
        if self.value_name:
            ret += ' ' + self.value_name
        return ret

    @property
    def post_doc(self):
        if self._post_doc is not None:
            return self._post_doc
        return self.format_post_doc()

    @post_doc.setter
    def _set_post_doc(self, val):
        self._post_doc = val

    def default_format_post_doc(self):
        if not self.value_name:
            return ''
        if self.flag.missing is ERROR:
            return '(required)'
        if repr(self.flag.missing) == object.__repr__(self.flag.missing):
            # avoid displaying unhelpful defaults
            return '(optional)'
        return '(defaults to %r)' % self.flag.missing

    @property
    def full_doc(self):
        if self._full_doc is not None:
            return self._full_doc

        doc_parts = [] if not self.doc else [self.doc]
        doc_parts.append(self.post_doc)
        return ' '.join(doc_parts)

    @post_doc.setter
    def _set_full_doc(self, val):
        self._full_doc = val


class PosArgDisplay(object):
    def __init__(self, spec, **kw):
        self.spec = spec
        self.name = kw.pop('name', 'arg')
        self.doc = kw.pop('doc', '')
        self.post_doc = kw.pop('post_doc', '')
        self._label = kw.pop('label', None)

        if kw:
            TypeError('unexpected keyword arguments: %r' % kw.keys())
        return

    @property
    def label(self):
        if not self.spec.accepts_args:
            return ''
        if self._label is not None:
            return self._label
        elif self.spec.min_count:
            return 'args ...'
        return '[args ...]'

    @label.setter
    def _set_label(self, val):
        self._label = val


class PosArgSpec(object):
    def __init__(self, parse_as=str, min_count=None, max_count=None, display=None):
        if not callable(parse_as) and parse_as is not ERROR:
            raise TypeError('expected callable or ERROR for parse_as, not %r' % parse_as)
        self.parse_as = parse_as
        self.min_count = int(min_count) if min_count else 0
        self.max_count = int(max_count) if max_count is not None else None

        if self.min_count < 0:
            raise ValueError('expected min_count >= 0, not: %r' % self.min_count)
        if self.max_count is not None and self.max_count < 0:
            raise ValueError('expected max_count >= 0, not: %r' % self.max_count)
        if self.max_count and self.min_count > self.max_count:
            raise ValueError('expected min_count > max_count, not: %r > %r'
                             % (self.min_count, self.max_count))

        if display is None:
            display = {}
        elif isinstance(display, bool):
            display = {'hidden': not display}
        elif isinstance(display, str):
            display = {'name': display}
        if isinstance(display, dict):
            display = PosArgDisplay(self, **display)
        self.display = display

        # TODO: default? type check that it's a sequence matching min/max reqs

    @property
    def accepts_args(self):
        if self.parse_as is ERROR:
            return False
        if self.max_count is not None and self.max_count == 0:
            return False
        return True

    def parse(self, posargs):
        len_posargs = len(posargs)
        if posargs and not self.accepts_args:
            raise InvalidPosArgs('unexpected arguments: %r' % posargs)
        min_count, max_count = self.min_count, self.max_count
        if min_count == max_count:
            if min_count == 0:
                arg_range_text = 'no arguments'
            else:
                arg_range_text = '%s argument' % min_count
            if min_count > 1:
                arg_range_text += 's'
        else:
            if min_count == 0:
                arg_range_text = 'up to %s argument' % max_count
                arg_range_text += 's' if max_count > 1 else ''
            elif max_count is None:
                arg_range_text = 'at least %s argument' % min_count
                arg_range_text += 's' if min_count > 1 else ''
            else:
                arg_range_text = '%s - %s arguments' % (min_count, max_count)

        if len_posargs < min_count:
            raise InvalidPosArgs('too few arguments, expected %s, got %s'
                                 % (arg_range_text, len_posargs))
        if max_count is not None and len_posargs > max_count:
            raise InvalidPosArgs('too many arguments, expected %s, got %s'
                                 % (arg_range_text, len_posargs))
        ret = []
        for pa in posargs:
            try:
                val = self.parse_as(pa)
            except Exception as exc:
                raise InvalidPositionalArgument.from_parse(self, pa, exc)
            else:
                ret.append(val)
        return ret


FLAG_FILE_ENABLED = Flag('--flagfile', parse_as=str, multi='extend', missing=None, display=False, doc='')


class Parser(object):
    """
    Parser parses, Command parses with Parser, then dispatches.
    """
    def __init__(self, name, doc=None, posargs=None):
        if not name or name[0] in ('-', '_'):
            # TODO: more complete validation
            raise ValueError('expected name beginning with ASCII letter, not: %r' % (name,))
        self.name = name
        self.doc = doc

        if not posargs:
            posargs = PosArgSpec(parse_as=ERROR)
        elif posargs is True:
            posargs = PosArgSpec()
        elif callable(posargs):
            posargs = PosArgSpec(parse_as=posargs)
        if not isinstance(posargs, PosArgSpec):
            raise ValueError('expected posargs as True, False,'
                             ' or instance of PosArgSpec, not: %r' % posargs)
        self.posargs = posargs

        self.flagfile_flag = FLAG_FILE_ENABLED

        self.subprs_map = OrderedDict()
        self.path_flag_map = OrderedDict()
        self.path_flag_map[()] = OrderedDict()

        if self.flagfile_flag:
            self.add(self.flagfile_flag)
        return

    def _add_subparser(self, subprs):
        """Process subcommand name, check for subcommand conflicts, check for
        subcommand flag conflicts, then finally add subcommand.

        To add a command under a different name, simply make a copy of
        that parser or command with a different name.
        """
        if self.posargs.accepts_args:
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
        flag_name = flag.name

        for subcmds, flag_map in self.path_flag_map.items():
            if flag_name in flag_map:
                # TODO: need a better error message here, one that
                # properly exposes the existing flag (same goes for
                # aliases below)
                raise ValueError('duplicate definition for flag name: %r' % flag_name)
            if False:
                # TODO
                raise ValueError('conflicting short form for flag %r: %r' % (flag_name, flag.char))

        # ... then we add the flags
        for flag_map in self.path_flag_map.values():
            flag_map[flag_name] = flag
            if flag.char:
                flag_map[flag.char] = flag

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

            parsed_posargs = prs.posargs.parse(posargs)
        except ArgumentParseError as ape:
            ape.parser = prs
            ape.subcmds = subcmds
            raise

        ret = CommandParseResult(cmd_name, subcmds, flag_map, parsed_posargs, post_posargs,
                                 parser=self, argv=argv)
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

            flag_conv = flag.parse_as
            if not callable(flag_conv):
                # e.g., True is effectively store_true, False is effectively store_false
                ret.add(flag.name, flag_conv)
                continue
            try:
                arg_text = args[i + 1]
            except IndexError:
                raise InvalidFlagArgument.from_parse(cmd_flag_map, flag, arg=None)
            try:
                arg_val = flag_conv(arg_text)
            except Exception as e:
                raise InvalidFlagArgument.from_parse(cmd_flag_map, flag, arg_text, exc=e)
            ret.add(flag.name, arg_val)
            _consumed_val = True

        # take care of dupes and check required flags
        ret = self._resolve_flags(cmd_flag_map, ret)
        return ret, args[idx:]

    def _resolve_flags(self, cmd_flag_map, parsed_flag_map):
        ret = OrderedDict()
        cfm, pfm = cmd_flag_map, parsed_flag_map

        # check requireds and set defaults and then...
        missing_flags = []
        for flag_name, flag in cfm.items():
            if flag_name in pfm:
                continue
            if flag.missing is ERROR:
                missing_flags.append(flag.name)
            else:
                pfm[flag_name] = flag.missing
        if missing_flags:
            raise MissingRequiredFlags(cfm, pfm, missing_flags)

        # ... resolve dupes
        for flag_name in pfm:
            flag = cfm[flag_name]
            arg_val_list = pfm.getlist(flag_name)
            ret[flag_name] = flag.multi(flag, arg_val_list)

        return ret


def parse_sv_line(line, sep=','):
    # TODO: this doesn't support unicode, which is mostly handled at
    # the layer above.
    from csv import reader, Dialect, QUOTE_MINIMAL

    class _face_dialect(Dialect):
        delimiter = sep
        escapechar = '\\'
        quotechar = '"'
        doublequote = True
        skipinitialspace = False
        lineterminator = '\n'
        quoting = QUOTE_MINIMAL

    parsed = list(reader([line], dialect=_face_dialect))
    return parsed[0]


class ListParam(object):
    # TODO: repr
    def __init__(self, parse_one_as=str, sep=',', strip=False):
        # TODO: min/max limits?
        self.parse_one_as = parse_one_as
        self.sep = sep
        self.strip = strip

    def parse(self, list_text):
        split_vals = parse_sv_line(list_text, self.sep)
        if self.strip:
            split_vals = [v.strip() for v in split_vals]
        return [self.parse_one_as(v) for v in split_vals]

    __call__ = parse



class FileValueParam(object):
    # Basically a file with a single value in it, like a pidfile
    # or a password file mounted in. Read in and treated like it
    # was on the argv.
    pass


class CommandParseResult(object):
    def __init__(self, name, subcmds, flag_map, posargs, post_posargs,
                 parser=None, argv=()):
        self.name = name
        self.subcmds = tuple(subcmds)
        self.flags = OrderedDict(flag_map)
        self.posargs = tuple(posargs or ())
        self.post_posargs = tuple(post_posargs or ())
        self.parser = parser
        self.argv = tuple(argv)


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

Should parse_as=List() with multi=extend give one long list or
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
