
import os
import sys
import array
import textwrap

from boltons.iterutils import unique


def _get_termios_winsize():
    # TLPI, 62.9 (p. 1319)
    import fcntl
    import termios

    winsize = array.array('H', [0, 0, 0, 0])

    assert not fcntl.ioctl(sys.stdout, termios.TIOCGWINSZ, winsize)

    ws_row, ws_col, _, _ = winsize

    return ws_row, ws_col


def _get_environ_winsize():
    # the argparse approach. not sure which systems this works or
    # worked on, if any. ROWS/COLUMNS are special shell variables.
    try:
        rows, columns = int(os.environ['ROWS']), int(os.environ['COLUMNS'])
    except (KeyError, ValueError):
        rows, columns = None, None
    return rows, columns


def get_winsize():
    rows, cols = None, None
    try:
        rows, cols = _get_termios_winsize()
    except Exception:
        try:
            rows, cols = _get_environ_winsize()
        except Exception:
            pass
    return rows, cols


def _wrap_pair(indent, label, sep, doc, doc_start, max_doc_width):
    # TODO: consider making sep align to the right of the fill-space,
    # so that it can act more like bullets when it's more than just
    # whitespace
    # TODO: consider making the fill character configurable (ljust
    # uses space by default, the just() methods can only take
    # characters, might be a useful bolton to take a repeating
    # sequence)
    ret = []
    append = ret.append
    lhs = indent + label + sep

    lhs_f = lhs.ljust(doc_start)
    if not doc:
        append(lhs)
        return ret

    wrapped_doc = textwrap.wrap(doc, max_doc_width)
    if len(lhs) <= doc_start:
        append(lhs_f + wrapped_doc[0])
    else:
        append(lhs)
        append(' ' * doc_start + wrapped_doc[0])

    for line in wrapped_doc[1:]:
        append(' ' * doc_start + line)

    return ret


class HelpHandler(object):
    default_context = {
        'usage_label': 'Usage:',
        'subcmd_section_heading': 'Subcommands: ',
        'flags_section_heading': 'Flags: ',
        'posargs_section_heading': 'Positional arguments:',
        'section_break': '\n',
        'group_break': '',
        'subcmd_example': 'subcommand',
        'width': None,
        'max_width': 120,
        'min_doc_width': 50,
        'doc_separator': '  ',
        'section_indent': '  '
    }

    def __init__(self, flag=('--help', '-h'), func=None, **kwargs):
        ctx = {}
        for key, val in self.default_context.items():
            ctx[key] = kwargs.pop(key, val)
        if kwargs:
            raise TypeError('unexpected keyword arguments: %r' % list(kwargs.keys()))
        self.ctx = ctx
        self.func = func if func is not None else self.default_help_func
        if not callable(self.func):
            raise TypeError('expected func to be callable, not %r' % func)

    def default_help_func(self, cmd_, subcmds_):
        print(self.get_help_text(cmd_.parser, subcmds=subcmds_))
        sys.exit(0)

    def get_help_text(self, parser, subcmds=(), flags=None):
        # TODO: filter by actually-used flags (note that help_flag and
        # flagfile_flag are semi-built-in, thus used by all subcommands)
        ctx = self.ctx
        widths = self.get_widths(parser, subcmds)
        flag_labels = [flag.display.label for flag in
                       unique(parser.path_flag_map[subcmds].values())]
        flag_widths = get_widths(labels=flag_labels,
                                 indent=ctx['section_indent'],
                                 sep=ctx['doc_separator'],
                                 width=ctx['width'],
                                 max_width=ctx['max_width'],
                                 min_doc_width=ctx['min_doc_width'])

        print sorted(widths.items())
        print sorted(flag_widths.items())

        ret = [self.get_usage_line(parser, subcmds=subcmds)]
        append = ret.append

        if subcmds:
            parser = parser.subprs_map[subcmds]

        append(ctx['group_break'])

        if parser.doc:
            append(parser.doc)
            append(ctx['section_break'])

        if parser.subprs_map:
            append(ctx['subcmd_section_heading'])
            append(ctx['group_break'])
            for sub_name in unique([sp[0] for sp in parser.subprs_map if sp]):
                subprs = parser.subprs_map[(sub_name,)]
                append(ctx['section_indent'] + sub_name + ctx['doc_separator'] + subprs.doc)
            append(ctx['section_break'])

        flags = parser.path_flag_map[()]
        shown_flags = [f for f in flags.values() if not f.display.hidden]

        if not shown_flags:
            return '\n'.join(ret)

        append(ctx['flags_section_heading'])
        append(ctx['group_break'])
        for flag in unique(shown_flags):
            flag_lines = _wrap_pair(indent=ctx['section_indent'],
                                    label=flag.display.label,
                                    sep=ctx['doc_separator'],
                                    doc=flag.display.full_doc,
                                    doc_start=flag_widths['doc_start'],
                                    max_doc_width=flag_widths['doc_width'])

            ret.extend(flag_lines)

        return '\n'.join(ret)

    def get_usage_line(self, parser, subcmds=()):
        ctx = self.ctx
        subcmds = tuple(subcmds or ())
        parts = [ctx['usage_label']] if ctx['usage_label'] else []
        append = parts.append

        append(' '.join((parser.name,) + subcmds))

        # TODO: put () in subprs_map to handle some of this sorta thing
        if not subcmds and parser.subprs_map:
            append('subcommand')
        elif subcmds and parser.subprs_map[subcmds].subprs_map:
            append('subcommand')

        flags = parser.path_flag_map[subcmds]
        shown_flags = [f for f in flags.values() if f.display_name is not False]

        if shown_flags:
            append('[FLAGS]')

        if parser.posargs:
            if parser.posargs.display_full:
                append(parser.posargs.display_full)
            elif parser.posargs.min_count:
                append('args ...')
            else:
                append('[args ...]')

        return ' '.join(parts)

    def get_widths(self, prs, subprs_path=(), max_width=None, max_width_limit=120):
        if max_width is None:
            _, max_width = get_winsize()
            if max_width is None:
                max_width = 80
            max_width = min(max_width, max_width_limit)
            max_width -= 2

        len_sep = len(self.ctx['doc_separator'])
        len_indent = len(self.ctx['section_indent'])
        min_doc_width = self.ctx['min_doc_width']

        max_flag_width = 0
        max_flag_doc_width = min_doc_width
        flag_doc_start = max_width - min_doc_width
        for flag in unique(prs.path_flag_map[subprs_path].values()):
            cur_len = len(flag.display.label)
            if cur_len > max_flag_width:
                # print len_indent, '+', cur_len, '+', len_sep, '+', min_doc_width
                # print (len_indent + cur_len + len_sep + min_doc_width), '<', max_width
                max_flag_width = cur_len
                if (len_indent + cur_len + len_sep + min_doc_width) < max_width:
                    max_flag_doc_width = max_width - max_flag_width - len_sep - len_indent
                    flag_doc_start = len_indent + cur_len + len_sep

        max_subcmd_width = 0
        for subcmd_name in unique([path[0] for path in prs.subprs_map if path]):
            cur_len = len(subcmd_name)
            if cur_len > max_subcmd_width:
                max_subcmd_width = cur_len

        subcmd_doc_start = len_indent + len_sep + max_subcmd_width

        return {'max_flag_doc_width': max_flag_doc_width,
                'max_flag_width': max_flag_width,
                'max_subcmd_width': max_subcmd_width,
                'flag_doc_start': flag_doc_start,
                'subcmd_doc_start': subcmd_doc_start,
                'min_doc_width': min_doc_width,
                'max_width': max_width}


def get_widths(labels, indent, sep, width=None, max_width=120, min_doc_width=40):
    if width is None:
        _, width = get_winsize()
        if width is None:
            width = 80
        width = min(width, max_width)
        width -= 2

    len_sep = len(sep)
    len_indent = len(indent)

    max_label_width = 0
    max_doc_width = min_doc_width
    doc_start = width - min_doc_width
    for label in labels:
        cur_len = len(label)
        if cur_len < max_label_width:
            continue
        max_label_width = cur_len
        if (len_indent + cur_len + len_sep + min_doc_width) < width:
            max_doc_width = width - max_label_width - len_sep - len_indent
            doc_start = len_indent + cur_len + len_sep

    return {'width': width,
            'label_width': max_label_width,
            'doc_width': max_doc_width,
            'doc_start': doc_start}


"""
{'flag_doc_start': 24, 'max_flag_doc_width': 58, 'max_width': 78, 'subcmd_doc_start': 12, 'max_flag_width': 47, 'max_subcmd_width': 8, 'min_doc_width': 58}

  --flagfile FLAGFILE       (defaults to None)
  --help / -h
  --num NUM                 a number to include in the sum, expects integers at the
                        moment because it is fun to change things later (defaults
                        to 0)


  --loop-count LOOP_COUNT  (defaults to None)
"""

"""Usage: cmd_name sub_cmd [..as many subcommands as the max] --flags args ...

Possible commands:

(One of the possible styles below)

Flags:
  Group name (if grouped):
    -F, --flag VALUE      Help text goes here. (integer, defaults to 3)

Flag help notes:

* don't display parenthetical if it's string/None
* Also need to indicate required and mutual exclusion ("not with")
* Maybe experimental / deprecated support
* Need to respect display_name=False
* General flag listing should also include flags up the chain

Subcommand listing styles:

* Grouped, one-deep, flag overview on each
* One-deep, grouped or alphabetical, help string next to each
* Grouped by tree (new group whenever a subtree of more than one
  member finishes), with help next to each.

What about extra lines in the help (like zfs) (maybe each individual
line can be a template string?)

TODO: does face need built-in support for version subcommand/flag,
basically identical to help?

Group names can be ints or strings. When, group names are strings,
flags are indented under a heading consisting of the string followed
by a colon. All ungrouped flags go under a 'General Flags' group
name. When group names are ints, groups are not indented, but a
newline is still emitted by each group.

Alphabetize should be an option, otherwise everything stays in
insertion order.

Subcommands without handlers should not be displayed in help. Also,
their implicit handler prints the help.

Subcommand groups could be Commands with name='', and they can only be
added to other commands, where they would embed as siblings instead of
as subcommands. Similar to how clastic subapplications can be mounted
without necessarily adding to the path.

Is it better to delegate representations out or keep them all within
the help builder?

---

Help needs: a flag (and a way to disable it), as well as a renderer.

Usage:

Doc

Subcommands:

...   ...

Flags:

...

Postdoc


{usage_label} {cmd_name} {subcmd_path} {subcmd_blank} {flags_blank} {posargs_label}

{cmd.doc}

{subcmd_heading}

  {subcmd.name}   {subcmd.doc} {subcmd.post_doc}

{flags_heading}

  {group_name}:

    {flag_label}   {flag.doc} {flag.post_doc}

{cmd.post_doc}


def default_fmt_flag_label(self, flag):
   ret = ' / '.join([flag.name] + flag.alias_list)
   if callable(flag.parse_as):
      ret += ' ' + (self.flag_value_name or self.flag.attr_name.upper())
   return ret



--------

# Grouping

Effectively sorted on: (group_name, group_index, sort_order, label)

But group names should be based on insertion order, with the
default-grouped/ungrouped items showing up in the last group.

# Wrapping / Alignment

Docs start at the position after the longest "left-hand side"
(LHS/"key") item that would not cause the first line of the docs to be
narrower than the minimum doc width.

LHSes which do extend beyond this point will be on their own line,
with the doc starting on the line below.

# Window width considerations

With better termios-based logic in place to get window size, there are
going to be a lot of wider-than-80-char help messages.

The goal of help message alignment is to help eyes track across from a
flag or subcommand to its corresponding doc. Rather than maximizing
width usage or topping out at a max width limit, we should be
balancing or at least limiting the amount of whitespace between the
shortest flag and its doc.  (TODO)

A width limit might still make sense because reading all the way
across the screen can be tiresome, too.

"""
