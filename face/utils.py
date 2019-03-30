
import re
import keyword

from boltons.strutils import pluralize
from boltons.iterutils import split, unique
from boltons.typeutils import make_sentinel

import face


ERROR = make_sentinel('ERROR')  # used for parse_as=ERROR

# keep it just to subset of valid ASCII python identifiers for now
VALID_FLAG_RE = re.compile(r"^[A-z][-_A-z0-9]*\Z")

FRIENDLY_TYPE_NAMES = {int: 'integer',
                       float: 'decimal'}


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

    name_match = VALID_FLAG_RE.match(name)
    if not name_match:
        raise ValueError('valid subcommand name must begin with a letter, and'
                         ' consist only of letters, digits, underscores, and'
                         ' dashes, not: %r' % name)

    subcmd_name = normalize_flag_name(name)

    return subcmd_name


def normalize_flag_name(flag):
    ret = flag.lstrip('-')
    if (len(flag) - len(ret)) > 1:
        # only single-character flags are considered case-sensitive (like an initial)
        ret = ret.lower()
    ret = ret.replace('-', '_')
    return ret


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

    flag_match = VALID_FLAG_RE.match(flag)
    if not flag_match:
        raise ValueError('valid flag names must begin with a letter, optionally'
                         ' prefixed by two dashes, and consist only of letters,'
                         ' digits, underscores, and dashes, not: %r' % orig_flag)

    flag_name = normalize_flag_name(flag)

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
    return get_cardinalized_args_label(posargspec.display.name, posargspec.min_count, posargspec.max_count)


def get_cardinalized_args_label(name, min_count, max_count):
    '''
    Examples for parameter values: (min_count, max_count): output for name=arg:

      1, 1: arg
      0, 1: [arg]
      0, None: [args ...]
      1, 3: args ...
    '''
    if min_count == max_count:
        return ' '.join([name] * min_count)
    if min_count == 1:
        return name + ' ' + get_cardinalized_args_label(name,
                                                        min_count=0,
                                                        max_count=max_count - 1 if max_count is not None else None)

    tmpl = '[%s]' if min_count == 0 else '%s'
    if max_count == 1:
        return tmpl % name
    return tmpl % (pluralize(name) + ' ...')


def format_flag_post_doc(flag):
    "The default positional argument label formatter, used in help formatting"
    if flag.display.post_doc is not None:
        return flag.display.post_doc
    if not flag.display.value_name:
        return ''
    if flag.missing is face.ERROR:
        return '(required)'
    if flag.missing is None or repr(flag.missing) == object.__repr__(flag.missing):
        # avoid displaying unhelpful defaults
        return '(optional)'
    return '(defaults to %r)' % flag.missing


def get_type_desc(parse_as):
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



def unwrap_text(text):
    all_grafs = []
    cur_graf = []
    for line in text.splitlines():
        line = line.strip()
        if line:
            cur_graf.append(line)
        else:
            all_grafs.append(' '.join(cur_graf))
            cur_graf = []
    if cur_graf:
        all_grafs.append(' '.join(cur_graf))
    return '\n'.join(all_grafs)


def get_rdep_map(dep_map):
    """
    expects and returns a dict of {item: set([deps])}

    item can be a string or any other hashable object.
    """
    # TODO: the way this is used, this function doesn't receive
    # information about what functions take what args. this ends up
    # just being args depending on args, with no mediating middleware
    # names. this can make circular dependencies harder to debug.
    ret = {}
    for key in dep_map:
        to_proc, rdeps, cur_chain = [key], set(), []
        while to_proc:
            cur = to_proc.pop()
            cur_chain.append(cur)

            cur_rdeps = dep_map.get(cur, [])

            if key in cur_rdeps:
                raise ValueError('dependency cycle: %r recursively depends'
                                 ' on itself. full dep chain: %r' % (cur, cur_chain))

            to_proc.extend([c for c in cur_rdeps if c not in to_proc])
            rdeps.update(cur_rdeps)

        ret[key] = rdeps
    return ret


def format_nonexp_repr(obj, req_names=None, opt_names=None, opt_key=None):
    """Format a non-expression-style repr

    Some object reprs look like object instantiation, e.g., App(r=[], mw=[]).

    This makes sense for smaller, lower-level objects whose state
    roundtrips. But a lot of objects contain values that don't
    roundtrip, like types and functions.

    For those objects, there is the non-expression style repr, which
    mimic's Python's default style to make a repr like this:

    <Flag name='abc' parse_as=<type 'int'>>
    """
    cn = obj.__class__.__name__
    req_names = req_names or []
    opt_names = opt_names or []
    all_names = unique(req_names + opt_names)

    if opt_key is None:
        opt_key = lambda v: v is None
    assert callable(opt_key)

    items = [(name, getattr(obj, name, None)) for name in all_names]
    labels = ['%s=%r' % (name, val) for name, val in items
              if not (name in opt_names and opt_key(val))]
    if not labels:
        labels = ['id=%s' % id(obj)]
    ret = '<%s %s>' % (cn, ' '.join(labels))
    return ret


def format_exp_repr(obj, pos_names, req_names=None, opt_names=None, opt_key=None):
    cn = obj.__class__.__name__
    req_names = req_names or []
    opt_names = opt_names or []
    all_names = unique(req_names + opt_names)

    if opt_key is None:
        opt_key = lambda v: v is None
    assert callable(opt_key)

    args = [getattr(obj, name, None) for name in pos_names]

    kw_items = [(name, getattr(obj, name, None)) for name in all_names]
    kw_items = [(name, val) for name, val in kw_items
                if not (name in opt_names and opt_key(val))]

    return format_invocation(cn, args, kw_items)



def format_invocation(name='', args=(), kwargs=None):
    kwargs = kwargs or {}
    a_text = ', '.join([repr(a) for a in args])
    if isinstance(kwargs, dict):
        kwarg_items = kwargs.items()
    else:
        kwarg_items = kwargs
    kw_text = ', '.join(['%s=%r' % (k, v) for k, v in kwarg_items])

    star_args_text = a_text
    if star_args_text and kw_text:
        star_args_text += ', '
    star_args_text += kw_text

    return '%s(%s)' % (name, star_args_text)
