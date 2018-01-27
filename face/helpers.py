
class AutoHelpBuilder(object):
    default_context = {
        'usage_label': 'Usage: ',
        'subcmd_section_heading': 'Subcommands: ',
        'flags_section_heading': 'Flags: ',
        'section_break': '\n\n',
        'group_break': '\n'
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

        return ' '.join(parts)

    def get_usage_subcmd_example(self):
        subcmds_count = max([len(subcmd_path) for subcmd_path in self.cmd.path_func_map])

        if not subcmds_count:
            return ''

        if self.cmd.func:
            return '[' + self.ctx['subcmd_example'] + ']'

        return '<' + self.ctx['subcmd_example'] + '>'





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

"""
