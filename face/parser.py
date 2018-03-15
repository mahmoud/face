
import re
import sys
import shlex
import codecs
import keyword
import os.path

from collections import OrderedDict

from boltons.iterutils import split, unique
from boltons.typeutils import make_sentinel
from boltons.dictutils import OrderedMultiDict as OMD


ERROR = make_sentinel('ERROR')


class FaceException(Exception):
    """The basest base exception Face has. Rarely directly instantiated
    if ever, but useful for catching.
    """
    pass


class ArgumentParseError(FaceException):
    """A base exception used for all errors raised during argument
    parsing.

    Many subtypes have a ".from_parse()" classmethod that creates an
    exception message from the values available during the parse
    process.
    """
    pass


class ArgumentArityError(ArgumentParseError):
    """Raised when too many or too few positional arguments are passed to
    the command. See PosArgSpec for more info.
    """
    pass


class InvalidSubcommand(ArgumentParseError):
    """
    Raised when an unrecognized subcommand is passed.
    """
    @classmethod
    def from_parse(cls, prs, subcmd_name):
        # TODO: add edit distance calculation
        valid_subcmds = unique([path[:1][0] for path in prs.subprs_map.keys()])
        msg = ('unknown subcommand "%s", choose from: %s'
               % (subcmd_name, ', '.join(valid_subcmds)))
        return cls(msg)


class UnknownFlag(ArgumentParseError):
    """
    Raised when an unrecognized flag is passed.
    """
    @classmethod
    def from_parse(cls, cmd_flag_map, flag_name):
        # TODO: add edit distance calculation
        valid_flags = unique([format_flag_label(flag) for flag in
                              cmd_flag_map.values() if not flag.display.hidden])
        msg = ('unknown flag "%s", choose from: %s'
               % (flag_name, ', '.join(valid_flags)))
        return cls(msg)


FRIENDLY_TYPE_NAMES = {int: 'integer',
                       float: 'decimal'}


class InvalidFlagArgument(ArgumentParseError):
    """Raised when the argument passed to a flag (the value directly
    after it in argv) fails to parse. Tries to automatically detect
    when an argument is missing.
    """
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
    "Kind of a hacky way to improve message readability around argument types"
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
    """Raised when one of the positional arguments does not
    parse/validate as specified. See PosArgSpec for more info.
    """
    @classmethod
    def from_parse(cls, posargspec, arg, exc):
        prep, type_desc = _get_type_desc(posargspec.parse_as)
        return cls('positional argument failed to parse %s'
                   ' %s: %r (got error: %r)' % (prep, type_desc, arg, exc))


class MissingRequiredFlags(ArgumentParseError):
    """
    Raised when a required flag is not passed. See Flag for more info.
    """
    @classmethod
    def from_parse(cls, cmd_flag_map, parsed_flag_map, missing_flag_names):
        msg = ('missing required arguments for flags: %s'
               % ', '.join(missing_flag_names))
        return cls(msg)


class DuplicateFlag(ArgumentParseError):
    """Raised when a flag is passed multiple times, and the flag's
    "multi" setting is set to 'error'.
    """
    @classmethod
    def from_parse(cls, flag, arg_val_list):
        avl_text = ', '.join([repr(v) for v in arg_val_list])
        if callable(flag.parse_as):
            msg = ('more than one value was passed for flag "%s": %s'
                   % (flag.name, avl_text))
        else:
            msg = ('flag "%s" was used multiple times, but can be used only once' % flag.name)
        return cls(msg)



# keep it just to subset of valid ASCII python identifiers for now
_VALID_FLAG_RE = re.compile(r"^[A-z][-_A-z0-9]*\Z")


def flag_to_identifier(flag):
    """Validate and canonicalize a flag name to a valid Python identifier
    (variable name).

    Valid input strings include only letters, numbers, '-', and/or
    '_'. Only single/double leading dash allowed (-/--). No trailing
    dashes or underscores. Must not be a Python keyword.

    Input case doesn't matter, output case will always be lower.
    """
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
    """
    Turn an identifier back into its flag format (e.g., "Flag" -> --flag).
    """
    if identifier.startswith('-'):
        raise ValueError('expected identifier, not flag name: %r' % identifier)
    ret = identifier.lower().replace('_', '-')
    return '--' + ret


def process_command_name(name):
    """Validate and canonicalize a Command's name, generally on
    construction or at subcommand addition. Like
    ``flag_to_identifier()``, only letters, numbers, '-', and/or
    '_'. Must begin with a letter, and no trailing underscores or
    dashes.

    Python keywords are allowed, as subcommands are never used as
    attributes or variables in injection.

    """

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
    "Raise a DuplicateFlag if more than one value is specified for an argument"
    if len(arg_val_list) > 1:
        raise DuplicateFlag.from_parse(flag, arg_val_list)
    return arg_val_list[0]


def _multi_extend(flag, arg_val_list):
    "Return a list of all arguments specified for a flag"
    return arg_val_list


def _multi_override(flag, arg_val_list):
    "Return only the last argument specified for a flag"
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
    """The Flag object represents all there is to know about a resource
    that can be parsed from argv and consumed by a Command
    function. It also references a FlagDisplay, used by HelpHandlers
    to control formatting of the flag during --help output

    Args:
       name (str): A string name for the flag, starting with a letter,
          and consisting of only ASCII letters, numbers, '-', and '_'.
       parse_as: How to interpret the flag. If *parse_as* is a
         callable, it will be called with the argument to the flag,
         the return value of which is stored in the parse result. If
         *parse_as* is not a callable, then the flag takes no
         argument, and the presence of the flag will produce this
         value in the parse result. Defaults to ``str``, meaning a
         default flag will take one string argument.
       missing: How to interpret the absence of the flag. Can be any
         value, which will be in the parse result when the flag is not
         present. Can also be the special value ``face.ERROR``, which
         will make the flag required. Defaults to ``None``.
       multi (str): How to handle multiple instances of the same
         flag. Pass 'overwrite' to accept the last flag's value. Pass
         'extend' to collect all values into a list. Pass 'error' to
         get the default behavior, which raises a DuplicateFlag
         exception. *multi* can also take a callable, which accepts a
         list of flag values and returns the value to be stored in the
         :class:`CommandParseResult`.
       char (str): A single-character short form for the flag. Can be
         user-friendly for commonly-used flags. Defaults to ``None``.
       doc (str): A summary of the flag's behavior, used in automatic
         help generation.
       display: Controls how the flag is displayed in automatic help
         generation. Pass False to hide the flag, pass a string to
         customize the label, and pass a FlagDisplay instance for full
         customizability.
    """
    def __init__(self, name, parse_as=str, missing=None, multi='error',
                 char=None, doc=None, display=None):
        self.name = flag_to_identifier(name)
        self.doc = doc
        self.parse_as = parse_as
        self.missing = missing
        if missing is ERROR and not callable(parse_as):
            raise ValueError('cannot make an argument-less flag required.'
                             ' expected non-ERROR for missing, or a callable'
                             ' for parse_as, not: %r' % parse_as)
        self.char = _validate_char(char) if char else None

        if callable(multi):
            self.multi = multi
        elif multi in _MULTI_SHORTCUTS:
            self.multi = _MULTI_SHORTCUTS[multi]
        else:
            raise ValueError('multi expected callable, bool, or one of %r, not: %r'
                             % (list(_MULTI_SHORTCUTS.keys()), multi))

        self.set_display(display)

    def set_display(self, display):
        """Controls how the flag is displayed in automatic help
        generation. Pass False to hide the flag, pass a string to
        customize the label, and pass a FlagDisplay instance for full
        customizability.
        """
        if display is None:
            display = {}
        elif isinstance(display, bool):
            display = {'hidden': not display}
        elif isinstance(display, str):
            display = {'label': display}
        if isinstance(display, dict):
            display = FlagDisplay(self, **display)
        if not isinstance(display, FlagDisplay):
            raise TypeError('expected bool, text name, dict of display'
                            ' options, or FlagDisplay instance, not: %r'
                            % display)
        self.display = display

    # TODO: __eq__ and copy


def format_flag_label(flag):
    "The default flag label formatter, used in help and error formatting"
    if flag.display.label is not None:
        return flag.display.label
    parts = [identifier_to_flag(flag.name)]
    if flag.char:
        parts.append('-' + flag.char)
    ret = ' / '.join(parts)
    if flag.display.value_name:
        ret += ' ' + flag.display.value_name
    return ret


def format_posargs_label(posargspec):
    "The default positional argument label formatter, used in help formatting"
    if posargspec.display.label:
        return posargspec.display.label
    if not posargspec.accepts_args:
        return ''
    # TODO pluralize
    if posargspec.min_count:
        return 'args ...'
    return '[args ...]'


def format_flag_post_doc(flag):
    "The default positional argument label formatter, used in help formatting"
    if flag.display.post_doc is not None:
        return flag.display.post_doc
    if not flag.display.value_name:
        return ''
    if flag.missing is ERROR:
        return '(required)'
    if flag.missing is None or repr(flag.missing) == object.__repr__(flag.missing):
        # avoid displaying unhelpful defaults
        return '(optional)'
    return '(defaults to %r)' % flag.missing


class FlagDisplay(object):
    """Provides individual overrides for most of a given flag's display
    settings, as used by HelpFormatter instances attached to Parser
    and Command objects. Pass an instance of this to
    Flag.set_display() for full control of help output.

    FlagDisplay instances are meant to be used 1:1 with Flag
    instances, as they maintain a reference back to their associated
    Flag. They are generally automatically created by a Flag
    constructor, based on the "display" argument.

    Args:
       flag (Flag): The Flag instance to which this FlagDisplay applies.
       label (str): The formatted version of the string used to
         represent the flag in help and error messages. Defaults to
         None, which allows the label to be autogenerated by the
         HelpFormatter.
       post_doc (str): An addendum string added to the Flag's own
         doc. Defaults to a parenthetical describing whether the flag
         takes an argument, and whether the argument is required.
       full_doc (str): A string of the whole flag's doc, overriding
         the doc + post_doc default.
       value_name (str): For flags which take an argument, the string
         to use as the placeholder of the flag argument in help and
         error labels.
       hidden (bool): Pass True to hide this flag in general help and
         error messages. Defaults to False.
       group: An integer or string indicating how this flag should be
         grouped in help messages, improving readability. Integers are
         unnamed groups, strings are for named groups. Defaults to 0.
       sort_key: Flags are sorted in help output, pass an integer or
         string to override the sort order.

    """
    # value_name -> arg_name?
    def __init__(self, flag, **kw):
        self.flag = flag
        self._label = kw.pop('label', None)

        self.doc = flag.doc
        if self.doc is None and callable(flag.parse_as):
            _prep, desc = _get_type_desc(flag.parse_as)
            self.doc = 'Parsed with ' + desc
            if _prep == 'as':
                self.doc = desc

        self.post_doc = kw.pop('post_doc', None)
        self.full_doc = kw.pop('full_doc', None)

        self.value_name = ''
        if callable(flag.parse_as):
            # TODO: use default when it's set and it's a basic renderable type
            self.value_name = kw.pop('value_name', None) or self.flag.name.upper()

        self.group = kw.pop('group', 0)   # int or str
        self.hidden = kw.pop('hidden', False)  # bool
        self.sort_key = kw.pop('sort_key', 0)  # int or str
        # TODO: sort_key is gonna need to be partitioned on type for py3
        # TODO: maybe sort_key should be a counter so that flags sort
        # in the order they are created

        if kw:
            TypeError('unexpected keyword arguments: %r' % kw.keys())
        return

    @property
    def label(self):
        return self._label

    @label.setter
    def _set_label(self, val):
        self._label = val
        # stay hidden if set to hidden, else hide if empty
        self.hidden = self.hidden or (not val)


class PosArgDisplay(object):
    """Provides individual overrides for PosArgSpec display in automated
    help formatting. Pass to a PosArgSpec constructor, which is in
    turn passed to a Command/Parser.

    Args:
       spec (PosArgSpec): The associated PosArgSpec.
       name (str): The string name of an individual positional
         argument. Automatically pluralized in the label according to
         PosArgSpec values. Defaults to 'arg'.
       label (str): The full display label for positional arguments,
         bypassing the automatic formatting of the *name* parameter.
       doc (str): A summary description of the positional arguments.
       post_doc (str): An informational addendum about the arguments,
         often describes default behavior.

    """
    def __init__(self, spec, **kw):
        self.spec = spec
        self.name = kw.pop('name', 'arg')
        self.doc = kw.pop('doc', '')
        self.post_doc = kw.pop('post_doc', '')
        self.label = kw.pop('label', None)

        if kw:
            TypeError('unexpected keyword arguments: %r' % kw.keys())
        return


class PosArgSpec(object):
    """Passed to Command/Parser as posargs and post_posargs parameters to
    configure the number and type of positional arguments.

    Args:
       parse_as (callable): A function to call on each of the passed
          arguments. Also accepts special argument ERROR, which will raise
          an exception if positional arguments are passed. Defaults to str.
       min_count (int): A minimimum number of positional
          arguments. Defaults to 0.
       max_count (int): A maximum number of positional arguments. Also
          accepts None, meaning no maximum. Defaults to None.
       display: Pass a string to customize the name in help output, or
          False to hide it completely. Also accepts a PosArgDisplay
          instance, or a dict of the respective arguments.

    PosArgSpec instances are stateless and safe to be used multiple
    times around the application.
    """
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
        """True if this PosArgSpec is configured to accept one or
        more arguments.
        """
        if self.parse_as is ERROR:
            return False
        if self.max_count is not None and self.max_count == 0:
            return False
        return True

    def parse(self, posargs):
        """Parse a list of strings as positional arguments.

        Args:
           posargs (list): List of strings, likely parsed by a Parser
              instance from sys.argv.

        Raises an ArgumentArityError if there are too many or too few
        arguments.

        Raises InvalidPositionalArgument if the argument doesn't match
        the configured *parse_as*. See PosArgSpec for more info.

        Returns a list of arguments, parsed with *parse_as*.
        """
        len_posargs = len(posargs)
        if posargs and not self.accepts_args:
            # TODO: check for likely subcommands
            raise ArgumentArityError('unexpected positional arguments: %r' % posargs)
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
                arg_range_text += 's' if (max_count and max_count > 1) else ''
            elif max_count is None:
                arg_range_text = 'at least %s argument' % min_count
                arg_range_text += 's' if min_count > 1 else ''
            else:
                arg_range_text = '%s - %s arguments' % (min_count, max_count)

        if len_posargs < min_count:
            raise ArgumentArityError('too few arguments, expected %s, got %s'
                                     % (arg_range_text, len_posargs))
        if max_count is not None and len_posargs > max_count:
            raise ArgumentArityError('too many arguments, expected %s, got %s'
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


FLAGFILE_ENABLED = Flag('--flagfile', parse_as=str, multi='extend', missing=None, display=False, doc='')


def _ensure_posargspec(posargs, posargs_name):
    if not posargs:
        # take no posargs
        posargs = PosArgSpec(parse_as=ERROR)
    elif posargs is True:
        # take any number of posargs
        posargs = PosArgSpec()
    elif isinstance(posargs, int):
        # take an exact number of posargs
        # (True and False are handled above, so only real ints get here)
        posargs = PosArgSpec(min_count=posargs, max_count=posargs)
    elif callable(posargs):
        # take any number of posargs of a given format
        posargs = PosArgSpec(parse_as=posargs)

    if not isinstance(posargs, PosArgSpec):
        raise ValueError('expected %s as True, False,'
                         ' or instance of PosArgSpec, not: %r' % (posargs_name, posargs))

    return posargs


# TODO: should post_posargs default to True?
class Parser(object):
    """The Parser lies at the center of face, primarily providing a
    configurable validation logic on top of the conventional grammar
    for CLI argument parsing.

    Args:
       name (str): A name used to identify this command. Important
          when the command is embedded as a subcommand of another
          command.
       doc (str): An optional summary description of the command, used
          to generate help and usage information.
       flags (list): A list of Flag instances. Optional, as flags can
          be added with :meth:`~Parser.add()`.
       posargs (bool): Defaults to disabled, pass ``True`` to enable
          the Parser to accept positional arguments. Pass a callable
          to parse the positional arguments using that
          function/type. Pass a :class:`PosArgSpec` for full
          customizability.
       post_posargs (bool): Same as *posargs*, but refers to the list
          of arguments following the ``--`` conventional marker. See
          ``git`` and ``tox`` for examples of commands using this
          style of positional argument.
       flagfile (bool): Defaults to enabled, pass ``False`` to disable
          flagfile support. Pass a :class:`Flag` instance to use a
          custom flag instead of ``--flagfile``. Read more about
          Flagfiles below.

    Once initialized, parsing is performed by calling
    :meth:`Parser.parse()` with ``sys.argv`` or any other list of strings.
    """
    def __init__(self, name, doc=None, flags=None, posargs=None,
                 post_posargs=None, flagfile=True):
        self.name = process_command_name(name)
        self.doc = doc
        flags = list(flags or [])
        for flag in flags:
            self.add(flag)

        self.posargs = _ensure_posargspec(posargs, 'posargs')
        self.post_posargs = _ensure_posargspec(post_posargs, 'post_posargs')

        if flagfile is True:
            self.flagfile_flag = FLAGFILE_ENABLED
        elif isinstance(flagfile, Flag):
            self.flagfile_flag = flagfile
        elif not flagfile:
            self.flagfile_flag = None
        else:
            raise ValueError('expected True, False, or Flag instance for'
                             ' flagfile, not: %r' % flagfile)

        self.subprs_map = OrderedDict()
        self._path_flag_map = OrderedDict()
        self._path_flag_map[()] = OrderedDict()

        if self.flagfile_flag:
            self.add(self.flagfile_flag)
        return

    def get_flag_map(self, path, with_hidden=True):
        flag_map = self._path_flag_map[path]
        return OrderedDict([(k, f) for k, f in flag_map.items()
                            if with_hidden or not f.display.hidden])

    def get_flags(self, path=(), with_hidden=True):
        flag_map = self.get_flag_map(path=path, with_hidden=with_hidden)

        return unique(flag_map.values())


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
        subprs_name = process_command_name(subprs.name)

        # then, check for conflicts with existing subcommands and flags
        for prs_path in self.subprs_map:
            if prs_path[0] == subprs_name:
                raise ValueError('conflicting subcommand name: %r' % subprs_name)
        parent_flag_map = self._path_flag_map[()]

        check_no_conflicts = lambda parent_flag_map, subcmd_path, subcmd_flags: True
        for path, flags in subprs._path_flag_map.items():
            if not check_no_conflicts(parent_flag_map, path, flags):
                # TODO
                raise ValueError('subcommand flags conflict with parent command: %r' % flags)

        # with checks complete, add parser and all subparsers
        self.subprs_map[(subprs_name,)] = subprs
        for subprs_path in subprs.subprs_map:
            new_path = (subprs_name,) + subprs_path
            self.subprs_map[new_path] = subprs

        # Flags inherit down (a parent's flags are usable by the child)
        for path, flags in subprs._path_flag_map.items():
            new_flags = parent_flag_map.copy()
            new_flags.update(flags)
            self._path_flag_map[(subprs_name,) + path] = new_flags

        # If two flags have the same name, as long as the "parse_as"
        # is the same, things should be ok. Need to watch for
        # overlapping aliases, too. This may allow subcommands to
        # further document help strings. Should the same be allowed
        # for defaults?

    def add(self, *a, **kw):
        """Add a flag or subparser.

        Unless the first argument is a Parser or Flag object, the
        arguments are the same as the Flag constructor, and will be
        used to create a new Flag instance to be added.

        May raise ValueError if arguments are not recognized as
        Parser, Flag, or Flag parameters. ValueError may also be
        raised on duplicate definitions and other conflicts.
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

        for subcmds, flag_map in self._path_flag_map.items():
            if flag_name in flag_map:
                # TODO: need a better error message here, one that
                # properly exposes the existing flag (same goes for
                # aliases below)
                raise ValueError('duplicate definition for flag name: %r' % flag_name)
            if False:
                # TODO
                raise ValueError('conflicting short form for flag %r: %r' % (flag_name, flag.char))

        # ... then we add the flags
        for flag_map in self._path_flag_map.values():
            flag_map[flag_name] = flag
            if flag.char:
                flag_map[flag.char] = flag

        return

    def parse(self, argv):
        """This method takes a list of strings and converts them into a
        validated :class:`CommandParseResult` according to the flags,
        subparsers, and other options configured.

        Args:
           argv (list): A required list of strings. Pass ``None`` to
              use ``sys.argv``.

        This method may raise ArgumentParseError (or one of its
        subtypes) if the list of strings fails to parse.

        .. note:: The *argv* parameter does not automatically default
                  to using ``sys.argv`` because it's best practice for
                  implementing codebases to perform that sort of
                  defaulting in their ``main()``, which should accept
                  an ``argv=None`` parameter. This simple step ensures
                  that the Python CLI application has some sort of
                  programmatic interface that doesn't require
                  subprocessing. See here for an example.

        """
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
            # NOTE: get_flag_map() is used so that inheritors, like Command,
            # can filter by actually-used arguments, not just
            # available arguments.
            cmd_flag_map = self.get_flag_map(path=tuple(subcmds))

            # parse supported flags and validate their arguments
            flag_map, flagfile_map, posargs = self._parse_flags(cmd_flag_map, args)

            # take care of dupes and check required flags
            resolved_flag_map = self._resolve_flags(cmd_flag_map, flag_map, flagfile_map)

            # separate out any trailing arguments from normal positional arguments
            post_posargs = None  # TODO: default to empty list?
            parsed_post_posargs = None
            if '--' in posargs:
                posargs, post_posargs = split(posargs, '--', 1)
                parsed_post_posargs = prs.post_posargs.parse(post_posargs)

            parsed_posargs = prs.posargs.parse(posargs)
        except ArgumentParseError as ape:
            ape.parser = prs
            ape.subcmds = subcmds
            raise

        ret = CommandParseResult(cmd_name, subcmds, resolved_flag_map,
                                 parsed_posargs, parsed_post_posargs,
                                 parser=self, argv=argv)
        return ret

    def _parse_subcmds(self, args):
        """Expects arguments after the initial command (i.e., argv[1:])

        Returns a tuple of (list_of_subcmds, remaining_args).

        Raises on unknown subcommands."""
        ret = []

        for arg in args:
            if arg.startswith('-'):
                break  # subcmd parsing complete

            arg = _arg_to_subcmd(arg)
            if tuple(ret + [arg]) not in self.subprs_map:
                prs = self.subprs_map[tuple(ret)] if ret else self
                if prs.posargs:
                    break
                raise InvalidSubcommand.from_parse(prs, arg)
            ret.append(arg)

        return ret, args[len(ret):]

    def _parse_single_flag(self, cmd_flag_map, args):
        arg = args[0]
        flag = cmd_flag_map.get(_normalize_flag_name(arg))
        if flag is None:
            raise UnknownFlag.from_parse(cmd_flag_map, arg)
        flag_conv = flag.parse_as
        if not callable(flag_conv):
            # e.g., True is effectively store_true, False is effectively store_false
            return flag, flag_conv, args[1:]

        try:
            arg_text = args[1]
        except IndexError:
            raise InvalidFlagArgument.from_parse(cmd_flag_map, flag, arg=None)
        try:
            arg_val = flag_conv(arg_text)
        except Exception as e:
            raise InvalidFlagArgument.from_parse(cmd_flag_map, flag, arg_text, exc=e)

        return flag, arg_val, args[2:]

    def _parse_flags(self, cmd_flag_map, args):
        """Expects arguments after the initial command and subcommands (i.e.,
        the second item returned from _parse_subcmds)

        Returns a tuple of (multidict of flag names to parsed and validated values, remaining_args).

        Raises on unknown subcommands.
        """
        flag_value_map = OMD()
        ff_path_res_map = OrderedDict()
        ff_path_seen = set()

        orig_args = args
        while args:
            arg = args[0]
            if not arg or arg[0] != '-' or arg == '-' or arg == '--':
                # posargs or post_posargs beginning ('-' is a conventional pos arg for stdin)
                break
            flag, value, args = self._parse_single_flag(cmd_flag_map, args)
            flag_value_map.add(flag.name, value)

            if flag is self.flagfile_flag:
                self._parse_flagfile(cmd_flag_map, value, res_map=ff_path_res_map)
                for path, ff_flag_value_map in ff_path_res_map.items():
                    if path in ff_path_seen:
                        continue
                    flag_value_map.update_extend(ff_flag_value_map)
                    ff_path_seen.add(path)

        return flag_value_map, ff_path_res_map, args

    def _parse_flagfile(self, cmd_flag_map, path_or_file, res_map=None):
        ret = res_map if res_map is not None else OrderedDict()
        if callable(getattr(path_or_file, 'read', None)):
            # enable StringIO and custom flagfile opening
            f_name = getattr(path_or_file, 'name', None)
            path = os.path.abspath(f_name) if f_name else repr(path_or_file)
            ff_text = path_or_file.read()
        else:
            path = os.path.abspath(path_or_file)
            try:
                with codecs.open(path_or_file, 'r', 'utf-8') as f:
                    ff_text = f.read()
            except (UnicodeError, EnvironmentError) as ee:
                raise ArgumentParseError('failed to load flagfile "%s", got: %r' % (path, ee))
        if path in res_map:
            # we've already seen this file
            return res_map
        ret[path] = cur_file_res = OMD()
        lines = ff_text.splitlines()
        for lineno, line in enumerate(lines, 1):
            try:
                args = shlex.split(line, comments=True)
                if not args:
                    continue  # comment or empty line
                flag, value, leftover_args = self._parse_single_flag(cmd_flag_map, args)

                if leftover_args:
                    raise ArgumentParseError('excessive flags or arguments for flag "%s",'
                                             ' expected one flag per line' % flag.name)

                cur_file_res.add(flag.name, value)
                if flag is self.flagfile_flag:
                    self._parse_flagfile(cmd_flag_map, value, res_map=ret)

            except FaceException as fe:
                fe.args = (fe.args[0] + ' (on line %s of flagfile "%s")' % (lineno, path),)
                raise

        return ret

    def _resolve_flags(self, cmd_flag_map, parsed_flag_map, flagfile_map=None):
        ret = OrderedDict()
        cfm, pfm = cmd_flag_map, parsed_flag_map
        flagfile_map = flagfile_map or {}

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
            try:
                ret[flag_name] = flag.multi(flag, arg_val_list)
            except FaceException as fe:
                ff_paths = []
                for ff_path, ff_value_map in flagfile_map.items():
                    if flag_name in ff_value_map:
                        ff_paths.append(ff_path)
                if ff_paths:
                    ff_label = 'flagfiles' if len(ff_paths) > 1 else 'flagfile'
                    msg = ('\n\t(check %s with definitions for flag "%s": %s)'
                           % (ff_label, flag_name, ', '.join(ff_paths)))
                    fe.args = (fe.args[0] + msg,)
                raise
        return ret


def parse_sv_line(line, sep=','):
    """Parse a single line of values, separated by the delimiter
    *sep*. Supports quoting.

    """
    # TODO: this doesn't support unicode, which is intended to be
    # handled at the layer above.
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
    """The ListParam takes an argument as a character-separated list, and
    produces a Python list of parsed values. Basically, the argument
    equivalent of CSV (Comma-Separated Values)::

      --flag a1,b2,c3

    By default, this yields a ``['a1', 'b2', 'c3']`` as the value for
    ``flag``. The format is also similar to CSV in that it supports
    quoting when values themselves contain the separator::

      --flag 'a1,"b,2",c3'

    Args:
       parse_one_as (callable): Turns a single value's text into its
          parsed value.
       sep (str): A single-character string representing the list
         value separator. Defaults to ``,``.
       strip (bool): Whether or not each value in the list should have
          whitespace stripped before being passed to
          *parse_one_as*. Defaults to False.

    .. note:: Aside from using ListParam, an alternative method for
              accepting multiple arguments is to use the
              ``multi=True`` on the :class:`Flag` constructor. The
              approach tends to be more verbose and can be confusing
              because arguments can get spread across the command
              line.

    """
    def __init__(self, parse_one_as=str, sep=',', strip=False):
        # TODO: min/max limits?
        self.parse_one_as = parse_one_as
        self.sep = sep
        self.strip = strip

    def parse(self, list_text):
        "Parse a single string argument into a list of arguments."
        split_vals = parse_sv_line(list_text, self.sep)
        if self.strip:
            split_vals = [v.strip() for v in split_vals]
        return [self.parse_one_as(v) for v in split_vals]

    __call__ = parse

    def __repr__(self):
        cn = self.__class__.__name__
        return ("%s(%r, sep=%r, strip=%r)"
                % (cn, self.parse_one_as, self.sep, self.strip))


class ChoicesParam(object):
    """Parses a single value, limited to a set of *choices*. The actual
    converter used to parse is inferred from *choices* by default, but
    an explicit one can be set *parse_as*.
    """
    def __init__(self, choices, parse_as=None):
        if not choices:
            raise ValueError('expected at least one choice, not: %r' % choices)
        try:
            self.choices = sorted(choices)
        except Exception:
            # in case choices aren't sortable
            self.choices = list(choices)
        if parse_as is None:
            parse_as = type(self.choices[0])
            # TODO: check for builtins, raise if not a supported type
        self.parse_as = parse_as

    def parse(self, text):
        choice = self.parse_as(text)
        if choice not in self.choices:
            raise ValueError('expected one of %r, not: %r' % (self.choices, text))
        return choice

    __call__ = parse

    def __repr__(self):
        cn = self.__class__.__name__
        return "%s(%r, parse_as=%r)" % (cn, self.choices, self.parse_as)


class FilePathParam(object):
    """TODO

    ideas: exists, minimum permissions, can create, abspath, type=d/f
    (technically could also support socket, named pipe, and symlink)

    could do missing=TEMP, but that might be getting too fancy tbh.
    """

class FileValueParam(object):
    """
    TODO: file with a single value in it, like a pidfile
    or a password file mounted in. Read in and treated like it
    was on the argv.
    """


class CommandParseResult(object):
    """The result of :meth:`Parser.parse`, instances of this type
    semantically store all that a command line can contain. Each
    argument corresponds 1:1 with an attribute.

    Args:
       name (str): Top-level program name, typically the first
          argument on the command line, i.e., ``sys.argv[0]``.
       subcmds (tuple): Sequence of subcommand names.
       flags (OrderedDict): Mapping of canonical flag names to matched values.
       posargs (tuple): Sequence of parsed positional arguments.
       post_posargs (tuple): Sequence of parsed post-positional
          arguments (args following ``--``)
       parser (Parser): The Parser instance that parsed this
          result. Defaults to None.
       argv (tuple): The sequence of strings parsed by the Parser to
          yield this result. Defaults to ``()``.

    Instances of this class can be injected by accepting the "args_"
    builtin in their Command handler function.

    """
    def __init__(self, name, subcmds, flags, posargs, post_posargs,
                 parser=None, argv=()):
        self.name = name
        self.subcmds = tuple(subcmds)
        self.flags = OrderedDict(flags)
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

x = 10

"""
ideas for flag types:

* iso8601 date/time/datetime
* duration
"""
