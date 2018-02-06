
from face.parser import ERROR, Flag

class AutoHelpBuilder(object):
    default_context = {
        'usage_label': 'Usage:',
        'subcmd_section_heading': 'Subcommands: ',
        'flags_section_heading': 'Flags: ',
        'section_break': '\n\n',
        'group_break': '\n',
        'subcmd_example': 'subcommand',
    }

    def __init__(self, cmd, ctx=None):
        self.cmd = cmd
        new_ctx = dict(self.default_context)
        if ctx:
            new_ctx.update(ctx)
        self.ctx = new_ctx

    def get_text(self):
        # get usage string
        lines = [self.get_usage_line()]
        return '\n'.join(lines)

    def get_usage_line(self):
        cmd, ctx = self.cmd, self.ctx
        parts = [ctx['usage_label']] if ctx['usage_label'] else []
        append = parts.append

        append(cmd.name)

        if len(cmd.path_func_map) > 1:
            append('subcommand')

        flags = cmd.parser.path_flag_map[()]
        shown_flags = [f for f in flags.values() if f.display_name is not False]

        if shown_flags:
            append('[FLAGS]')

        if cmd.parser.posargs:
            if cmd.parser.posargs.display_full:
                append(cmd.parser.posargs.display_full)
            elif cmd.parser.posargs.min_count:
                append('args ...')
            else:
                append('[args ...]')

        return ' '.join(parts)


class SimpleUsageLineBuilder(object):
    def __init__(self, cmd, ctx):
        self.cmd = cmd
        self.ctx = ctx


class FullUsageLineBuilder(object):
    def __init__(self, cmd, ctx):
        self.cmd = cmd
        self.ctx = ctx

    def get_usage_line(self):
        parts = []
        subcmd_example = self.get_usage_subcmd_example()
        if subcmd_example:
            parts.append(subcmd_example)

        posargs_example = self.get_usage_pos_arg_example()
        if posargs_example:
            parts.append(posargs_example)

        return ' '.join(parts)

    def _get_subcmd_depth(self):
        return max([len(subcmd_path) for subcmd_path in self.cmd.path_func_map])

    def get_usage_subcmd_example(self):
        if not self._get_subcmd_depth():
            return ''

        if self.cmd.func:
            return '[' + self.ctx['subcmd_example'] + ']'

        return self.ctx['subcmd_example']
        # try without angle brackets at first, see if it's
        # sufficiently indicative of "required" return '<' +
        # self.ctx['subcmd_example'] + '>'

    def get_usage_pos_arg_example(self):
        posargs = self.cmd.parser.posargs
        if not posargs:
            return ''

        if posargs.display_full:
            return posargs.display_full
        if not posargs.display_name:
            return ''  # a way of hiding that the command accepts pos args

        display_name = posargs.display_name
        min_count, max_count = posargs.min_count, posargs.max_count

        if not min_count and not max_count:
            return '[' + display_name + ' ...]'

        # generate arg names
        parts, i = [], 0
        for i in range(min_count):
            parts.append('%s%s' % (display_name, i + 1))
        if len(parts) > 4:
            parts = parts[:2] + ['...'] + parts[-1:]
        if i < max_count:
            max_parts = []
            if (max_count - i) <= 2:
                max_parts.extend(['%s%s' % (display_name, x + 1)
                                  for x in range(i, max_count)])
            else:
                max_parts.append('...')
                max_parts.append('%s%s' % (display_name, max_count))
            max_part = '[%s]' % ' '.join(max_parts)
            parts.append(max_part)

        return ' '.join(parts)



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





"""

import sys

from boltons.iterutils import unique

class HelpHandler(object):
    default_context = {
        'usage_label': 'Usage:',
        'subcmd_section_heading': 'Subcommands: ',
        'flags_section_heading': 'Flags: ',
        'section_break': '\n',
        'group_break': '',
        'subcmd_example': 'subcommand',
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

        ret = [self.get_usage_line(parser, subcmds=subcmds)]
        append = ret.append

        if subcmds:
            parser = parser.subprs_map[subcmds]

        append(ctx['section_break'])

        if parser.doc:
            append(parser.doc)
            append(ctx['section_break'])

        if parser.subprs_map:
            append(ctx['subcmd_section_heading'])
            append(ctx['group_break'])
            for sub_name in unique([sp[0] for sp in parser.subprs_map if sp]):
                subprs = parser.subprs_map[(sub_name,)]
                append(sub_name + '   ' + subprs.doc)
            append(ctx['section_break'])

        flags = parser.path_flag_map[()]
        shown_flags = [f for f in flags.values() if not f.display.hidden]
        if shown_flags:
            append(ctx['flags_section_heading'])
            append(ctx['group_break'])
            for flag in unique(shown_flags):
                entry_name = flag.display.label
                doc_parts = [] if not flag.doc else [flag.doc]
                doc_parts.append(flag.display.post_doc)
                append(entry_name + '  ' + ' '.join(doc_parts))


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
