face Project Log
================

20.1.0
------
* Add testing facilities (CommandChecker())
* Add echo() and prompt()

20.0.0
------
* Many bugfixes
* New shortcuts for posarg count and injection

19.1.0
------
* posargspec aliases:
  * count (exact min and max count)
  * name (display name and provides name)

Ideas
-----

* Add an .add_version() method to Command
  * Automatically adds version subcommand if other subcommands are present
  * Automatically adds "-v" flag if one is not present
* Check that subcommands may override parent flags
  * Should "signature" be enforced?
* Utilities
  * confirm (default yes/no [Y/n], strict=True means type the whole word)
  * get_input (flag for password mode)
  * consistent behavior for ctrl-c/ctrl-d
    * ctrl-c cancels current input but does not exit
    * ctrl-d exits if it's the full message
  * banner (prints a banner)
  * debug/info/warn/critical
    * '..', '--', '!!', '**'
    * attach your own sinks for fun and profit
  * some hook for testing endpoints that use stdin/stdout
  * middleware + flag type that prompts the user for a value if it
    wasn't passed as a flag.
* Built-in entrypoints-based plugin convention?
  * How to add subcommands mostly, but maybe middleware
* Better error message around misordered middlewares
  * (check if mw_unres is in any of the mw provides)
* What to do if flag and posargs provide the same thing?
  * If one is on parent and the other is on subcommand, pick the most
    local one?
  * If both are at the same level, raise an error as soon as one is set.
* Allow middlewares to "override", "update", or "transform"
  injectables, aka provide an injectable which has already been
  provided. We don't want to invite conflicts, so they would need to
  explicitly accept that injectable as well as provide it.
* Better document that if middleware arguments have a default value,
  they will not pull in flags.
* Allow setting of "name" alias on PosArgSpec. Specifies an alternate
  name by which posargs_ (or post_posargs_) will be injected into the
  target function.
* Work PosArgSpec name into ArgumentArityError messages
* DisplayOptions: Some form of object acting as partial rendering
  context for instances of Command, Flag, PosArgSpec.
* Add edit distance calculation for better error messages on unknown
  flags and invalid subcommands.
* Hook for HelpHandler to add a line to error messages? (e.g., "For
  more information try --help" (or the help subcommand))
    * Automatically add a message about the help subcommand or -h flag to
      parse errors, when help handler is present.

### Big Ticket Items

* Calculator example
* Docs
* Autocompletion

### API

* Handle conversion of argv to unicode on Py2? Or support bytes argv?
* Better check for conflicting Flags (`__eq__` on Flag?)
* Better exception for conflicting subcommands
* Easier copying of Flags, Commands, etc.
* CommandParseResult needs Source object
* ListParam, FileValueParam
* "display_name" to "display" (convenience: accept string display name
  which turns into DisplayOptions) (also affects help)
* Possible injectables: target function, set of all dependencies of
  downstream function + middlewares (enables basic/shallow conditional
  middlewares)
* Split out HelpFormatter to be a member of HelpHandler

#### Parser / Command

* Group (same as flags below)
* Sort order (same as flags below)
* Hidden? (doesn't make sense to customize label as with flags)
* Doc (text between the usage line and the subcommands/flags)
* Post-doc (text that comes after flags and subcommands)
* What about multi-line usage strings?

#### Flag

* Group (default 0, unlabeled groups if integer, labeled group if string)
* Sort order (default 0. first sorted by this number then
  alphabetical. sorting only happens within groups.)
* Name (--canonical-name) (does it make sense to customize this?)
* Label (--canonical-name / --alias / -C VALUE) (hide if empty/falsy, probably)
* Value Label (name_of_the_flag.upper())
* "parse_as" label (see parser._get_type_desc)
* pre_padding, post_padding
* Should format_label live on FlagDisplay or in HelpHandler/HelpFormatter?

Related:

* Behavior on error (e.g., display usage)

#### PosArgSpec

* Description suffix (takes up to 2 integer args, takes 1-4 float args, etc.)
* Usage line display (args ...)

### Small Questions

* How bad of an idea is it to have HelpHandler take the remaining
  kwargs and pass them through to the helpformatter? kind of locks us
  into an API should we ever want to change the default help
  formatter.
* Should we allow keywords to be flag/injectable names, but just
  automatically remap them internally such that a `--class` flag
  becomes available under `flags['class_']`. Might want to do this
  with builtin functions like sum, too?
* Most useful default sort? Currently doing by insertion order, which
  works well for smaller command as it exposes quite a bit of control,
  but this will change for larger commands which may need to compose
  differently. Could keep an _id = next(itertools.count()) approach to
  record creation order.
* Should we accept flags _anywhere_ in argv? Or just between
  subcommands and arguments? There is a case to be made for the
  occasional quick addition of a flag to the end of a command.
* Mark as subinjectable? When lots of arguments might complicate a
  function API, create a config object that soaks them up and is
  itself injectable. (strata "lite")
* Recommended practice for exiting with an error?
* Need to also wrap command-level doc to width

### Common errors

Errors a face-using developer might run into.

* Flag nested under one command not available under another. Could do
  a quick look around and give a "did you mean"
* posargs display expects name to be singular bc it's going to be
  pluralized. too smart?
