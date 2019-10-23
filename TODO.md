# TODO

* Allow setting of "name" alias on PosArgSpec. Specifies an alternate
  name by which posargs_ (or post_posargs_) will be injected into the
  target function.
* Work PosArgSpec name into ArgumentArityError messages
* Automatically add a message about the help subcommand or -h flag to
  parse errors, when help handler is present.

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

## Small things

* Recommended practice for exiting with an error?
* Need to also wrap command-level doc to width

## Common errors

Errors a face-using developer might run into.

* Flag nested under one command not available under another. Could do
  a quick look around and give a "did you mean"
* posargs display expects name to be singular bc it's going to be
  pluralized. too smart?
