Face FAQs
=========

*TODO*

What sets Face apart from other CLI libraries?
----------------------------------------------

In the Python world, you certainly have a lot of choices among
argument parsers. Software isn't a competition, but there are many
good reasons to choose face.

* Rich dependency semantics guarantee that endpoints and their dependencies
  line up before the Command will build to start up.
* Streamlined, Pythonic API.
* Handy testing tools
* Focus on CLI UX (arg order, discouraging required flag)
* TODO: contrast with argparse, optparse, click, etc.

Why is Face so picky about argument order?
------------------------------------------

In short, command-line user experience and history hygiene. While it's
easy for us to be tempted to add flags to the ends of commands, anyone
reading that command later is going to suffer::

  cmd subcmd posarg1 --flag arg posarg2

Does ``posarg2`` look more like a positional argument or an argument
of ``--flag``?

This is also why Face doesn't allow non-leaf commands to accept
positional arguments (is it a subcommand or an argument?), or flags
which support more than one whitespace-separated argument.

Any recommended patterns for laying out CLI code?
-------------------------------------------------

- Dedicated cli.py which constructs commands.
- main function should take argv as an argument
- ``if __name__ == '__main__': main(sys.argv)``
- Entrypoints are nicer than ``-m``
