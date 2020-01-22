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
