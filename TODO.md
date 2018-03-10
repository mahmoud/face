# TODO

## Big tickets

* Tests
* Calculator example
* Docs
* Autocompletion

## Big questions

* Handle conversion of argv to unicode on Py2? Or support bytes argv?

## API

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

### DisplayOptions

Some form of object acting as partial rendering context for instances
of Command, Flag, PosArgSpec.

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

## Error messages

* Add edit distance calculation for better error messages on unknown
  flags and invalid subcommands.
* Fix up error message for positional arguments
* Hook for HelpHandler to add a line to error messages? (e.g., "For
  more information try --help" (or the help subcommand))

## Compatibility

* Check up on how cpython decodes argv (locale stuff)
* Check sinter against new argspecs

## Target projects

* mp4_cut.py
* Example calculator project
* PocketProtector
* Montage admin tools

## Small Questions

* How bad of an idea is it to have HelpHandler take the remaining
  kwargs and pass them through to the helpformatter? kind of locks us
  into an API should we ever want to change the default help
  formatter.
