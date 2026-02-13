Face FAQs
=========

What sets Face apart from other CLI libraries?
-----------------------------------------------

In the Python world, you certainly have a lot of choices among
argument parsers. Software isn't a competition, but there are many
good reasons to choose face.

* **Dependency injection.** Handler functions declare what they need as
  parameter names. Face resolves flags, builtins, and middleware-provided
  values automatically. No namespace objects, no decorator gymnastics.
* **Rich dependency semantics** guarantee that endpoints and their dependencies
  line up before the Command will build to start up. Errors surface at
  :meth:`~face.Command.prepare` time, not at runtime in production.
* **Streamlined, Pythonic API.** One :meth:`~face.Command.add` method handles
  flags, subcommands, and middleware. Plain functions serve as handlers.
* **Handy testing tools** via :class:`face.CommandChecker` for exercising
  CLI commands without subprocess overhead.
* **Focus on CLI UX:** strict argument ordering, discouraging required flags,
  and sensible defaults that prevent ambiguous command lines.

Compared to **argparse**, face uses dependency injection instead of
namespace objects. You declare parameters on your handler function and face
fills them in. No more ``args.verbose``.

Compared to **click**, face uses plain functions instead of requiring
decorators on every command. Subcommands are added with ``cmd.add(func)``,
not ``@group.command()``.

Compared to **docopt**, face is programmatic, not docstring-based.
You get full IDE support, type checking, and refactoring safety.

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

How does dependency injection work?
-----------------------------------

Handler functions declare what they need as parameter names. Face
inspects the function signature and provides matching values at call
time.

Flags map to parameters by name. A flag ``--verbose`` becomes the
parameter ``verbose``. A flag ``--output-file`` becomes ``output_file``.

Builtins use trailing underscores:

- ``args_`` -- :class:`~face.CommandParseResult` instance with all parsed state
- ``flags_`` -- ``OrderedDict`` of flag name to value
- ``cmd_`` -- string of the command name (argv[0])
- ``subcmds_`` -- tuple of subcommand strings
- ``posargs_`` -- tuple of positional arguments
- ``post_posargs_`` -- tuple of arguments after ``--``
- ``command_`` -- the root :class:`~face.Command` instance
- ``subcommand_`` -- the matched subparser for the current subcommand path

Middleware can provide custom injectables via the ``provides`` argument
to :func:`face.face_middleware`. Face checks at :meth:`~face.Command.prepare`
or :meth:`~face.Command.run` time that all dependencies are satisfiable.

.. code-block:: python

   from face import Command

   def greet(name, verbose):
       if verbose:
           print(f'About to greet {name}')
       print(f'Hello, {name}!')

   cmd = Command(greet, name='greet')
   cmd.add('--name', missing='world')
   cmd.add('--verbose', parse_as=True, missing=False)
   cmd.run()

How do I make a flag required?
------------------------------

Set ``missing`` to :data:`face.ERROR`:

.. code-block:: python

   from face import Command, ERROR

   cmd = Command(my_handler)
   cmd.add('--name', missing=ERROR)

When ``--name`` is not provided on the command line, face raises an error
with a clear message. Use this sparingly. Required flags are a UX smell
in most CLIs. Prefer sensible defaults or positional arguments.

How do I accept multiple values for a flag?
-------------------------------------------

Two approaches:

**Repeated flags** with ``multi='extend'``. The user passes the flag
multiple times:

.. code-block:: python

   from face import Command

   cmd = Command(my_handler)
   cmd.add('--tag', multi='extend')
   # Usage: mycli --tag a --tag b --tag c
   # tags parameter receives ['a', 'b', 'c']

**Comma-separated values** with :class:`~face.ListParam`:

.. code-block:: python

   from face import Command, ListParam

   cmd = Command(my_handler)
   cmd.add('--tags', parse_as=ListParam(strip=True))
   # Usage: mycli --tags a,b,c
   # tags parameter receives ['a', 'b', 'c']

Use ``multi='extend'`` when values may contain commas. Use
:class:`~face.ListParam` when brevity matters.
