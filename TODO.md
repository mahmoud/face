# TODO

## Big tickets

* Help generation
* Tests
* Calculator example
* Docs

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

### DisplayOptions

* Group
* Sort order
* Display name
* Display name singular
* Value display name
* Hidden (suggestability?)

Related:

* Behavior on error (e.g., display usage)

## Error messages

* Add edit distance calculation for better error messages on unknown
  flags and invalid subcommands.
* Fix up error message for positional arguments

## Compatibility

* Check up on how cpython decodes argv (locale stuff)
* Check sinter against new argspecs
