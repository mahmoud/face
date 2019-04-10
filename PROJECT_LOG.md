face Project Log
================

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
* Built-in entrypoints-based plugin convention?
  * How to add subcommands mostly, but maybe middleware
* posargspec aliases:
  * count (exact min and max count)
  * name (display name and provides name)
