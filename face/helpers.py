
import os
import sys
import array
import textwrap

from boltons.iterutils import unique

from face.parser import Flag


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
    lhs = indent + label

    if not doc:
        append(lhs)
        return ret

    len_sep = len(sep)
    wrapped_doc = textwrap.wrap(doc, max_doc_width)
    if len(lhs) <= doc_start:
        lhs_f = lhs.ljust(doc_start - len(sep)) + sep
        append(lhs_f + wrapped_doc[0])
    else:
        append(lhs)
        append((' ' * (doc_start - len_sep)) + sep + wrapped_doc[0])

    for line in wrapped_doc[1:]:
        append(' ' * doc_start + line)

    return ret


def _get_shown_flags(target):
    from face import Parser
    # TODO: evaluate whether Command should inherit from Parser so
    # that this can be removed. After writing tests.
    if isinstance(target, Parser):
        return unique([f for f in target.path_flag_map[()].values() if not f.display.hidden])
    return target.get_flags()


DEFAULT_HELP_FLAG = Flag('--help', parse_as=True, char='-h', doc='show this help message and exit')


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
        'doc_separator': '   ',  # '   + ' is pretty classy as bullet points, too
        'section_indent': '  ',
        'pre_doc': '',  # TODO: these should go on CommandDisplay
        'post_doc': '\n',
    }

    def __init__(self, flag=DEFAULT_HELP_FLAG, func=None, subcmd=None, **kwargs):
        # subcmd expects a string
        ctx = {}
        for key, val in self.default_context.items():
            ctx[key] = kwargs.pop(key, val)
        if kwargs:
            raise TypeError('unexpected keyword arguments: %r' % list(kwargs.keys()))
        self.ctx = ctx
        self.flag = flag
        self.func = func if func is not None else self.default_help_func
        self.subcmd = subcmd
        if not callable(self.func):
            raise TypeError('expected func to be callable, not %r' % func)

    def default_help_func(self, cmd_, subcmds_, args_):
        try:
            program_name = args_.argv[0]
        except IndexError:
            program_name = cmd_.name
        print(self.get_help_text(cmd_.parser, subcmds=subcmds_, program_name=program_name))
        sys.exit(0)

    def _get_layout(self, labels):
        ctx = self.ctx
        return get_layout(labels=labels,
                          indent=ctx['section_indent'],
                          sep=ctx['doc_separator'],
                          width=ctx['width'],
                          max_width=ctx['max_width'],
                          min_doc_width=ctx['min_doc_width'])

    def get_help_text(self, parser, subcmds=(), flags=None, program_name=None):
        # TODO: filter by actually-used flags (note that help_flag and
        # flagfile_flag are semi-built-in, thus used by all subcommands)
        # TODO: incorporate "Arguments" section if posargs has a doc set
        ctx = self.ctx

        ret = [self.get_usage_line(parser, subcmds=subcmds, program_name=program_name)]
        append = ret.append
        append(ctx['group_break'])

        if subcmds:
            parser = parser.subprs_map[subcmds]

        if parser.doc:
            append(parser.doc)
            append(ctx['section_break'])

        if parser.subprs_map:
            subcmd_labels = unique([sp[0] for sp in parser.subprs_map if sp])
            subcmd_layout = self._get_layout(labels=subcmd_labels)

            append(ctx['subcmd_section_heading'])
            append(ctx['group_break'])
            for sub_name in unique([sp[0] for sp in parser.subprs_map if sp]):
                subprs = parser.subprs_map[(sub_name,)]
                subcmd_lines = _wrap_pair(indent=ctx['section_indent'],
                                          label=sub_name,
                                          sep=ctx['doc_separator'],
                                          doc=subprs.doc,
                                          doc_start=subcmd_layout['doc_start'],
                                          max_doc_width=subcmd_layout['doc_width'])
                ret.extend(subcmd_lines)

            append(ctx['section_break'])

        shown_flags = _get_shown_flags(parser)
        if not shown_flags:
            return '\n'.join(ret)

        flag_labels = [flag.display.label for flag in shown_flags]
        flag_layout = self._get_layout(labels=flag_labels)

        append(ctx['flags_section_heading'])
        append(ctx['group_break'])
        for flag in shown_flags:
            flag_lines = _wrap_pair(indent=ctx['section_indent'],
                                    label=flag.display.label,
                                    sep=ctx['doc_separator'],
                                    doc=flag.display.full_doc,
                                    doc_start=flag_layout['doc_start'],
                                    max_doc_width=flag_layout['doc_width'])

            ret.extend(flag_lines)

        return ctx['pre_doc'] + '\n'.join(ret) + ctx['post_doc']

    def get_usage_line(self, parser, subcmds=(), program_name=None):
        ctx = self.ctx
        subcmds = tuple(subcmds or ())
        parts = [ctx['usage_label']] if ctx['usage_label'] else []
        append = parts.append

        program_name = program_name or parser.name

        append(' '.join((program_name,) + subcmds))

        # TODO: put () in subprs_map to handle some of this sorta thing
        if not subcmds and parser.subprs_map:
            append('subcommand')
        elif subcmds and parser.subprs_map[subcmds].subprs_map:
            append('subcommand')

        # with subcommands out of the way, look up the parser for flags and args
        if subcmds:
            parser = parser.subprs_map[subcmds]

        flags = _get_shown_flags(parser)

        if flags:
            append('[FLAGS]')

        if parser.posargs:
            append(parser.posargs.display.label)

        return ' '.join(parts)


def get_layout(labels, indent, sep, width=None, max_width=120, min_doc_width=40):
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

TODO: padding_top and padding_bottom attributes on various displays
(esp FlagDisplay) to enable finer grained whitespace control without
complicated group setups.

"""
