# Design

Unlike URLs, there is no spec for parsing arguments. Much to my
dismay, frankly. Living through argparse and docopt and click, it was
like lash after lash against my poor CLI-loving flesh.

* getopt basis?
* Single- or no-argument flags only. No multi-argument flags
* Configurable behavior as to multiple appearances of the same flag
    * error (default)
    * additive - value will be an int for no-arg flags (as with
      --verbose and -vvv), and added to a list for single-argument
      flags
* Short flag support?
* strong subcommand support (compositionally similar to clastic?)
* store_true and store_false, or something better?
* single argument flags support space-based and 'x=y' style arguments
* transparent transformation between underscore and dash-based
  arguments (--enable-action and --enable_action are the same)
* single variadic argument list
    * only valid for leaf subcommands
* support partial parsing (a la parse_known_args)
* support taking multiple flagfiles
    * always the same argument name, like a builtin, then warn on conflict
    * could be an argument type
    * might need to take a flagfilereader argument for testin purposes
* No multi-level flag support. Flags push down under subcommands,
  conflicts raise errors early (at setup time). Flags can be masked
  out against being pushed under further subcommands (i.e., make the
  flag subcommand-local).

Big challenge: helpful error messages
