
class AutoHelpBuilder(object):
    default_context = {
        'usage_label': 'Usage: ',
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

        subcmd_example = self.get_usage_subcmd_example()
        if subcmd_example:
            append(subcmd_example)

        pos_args_example = self.get_usage_pos_arg_example()
        if pos_args_example:
            append(pos_args_example)

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
        pos_args = self.cmd.parser.pos_args
        if not pos_args:
            return ''

        if pos_args.display_full:
            return pos_args.display_full
        if not pos_args.display_name:
            return ''  # a way of hiding that the command accepts pos args

        display_name = pos_args.display_name
        min_count, max_count = pos_args.min_count, pos_args.max_count

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
                max_parts.append('%s%s' (display_name, max_count))
            max_part = '[%s]' % ''.join(max_parts)
            parts.append(max_part)

        return ' '.join(parts)
        # replace everything from the second to the last with a single '...'





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

"""
