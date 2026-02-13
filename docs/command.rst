Command
=======

.. contents:: Contents
   :local:
   :depth: 2

:class:`face.Command` is the central type in face. It wraps a
:class:`~face.Parser` with handler dispatch, middleware, help generation,
and dependency injection. Build a CLI by creating a Command, adding flags
and subcommands, then calling :meth:`~face.Command.run`.

Construction
------------

The minimal Command takes a handler function:

.. code-block:: python

    from face import Command

    def greet():
        print('hello')

    cmd = Command(greet)
    cmd.run()

``name`` defaults to the function name (``greet`` above). ``doc`` defaults
to the first line of the function's docstring. Override either explicitly:

.. code-block:: python

    def greet():
        """Say hello to the world.

        This longer description is ignored by face.
        """
        print('hello')

    cmd = Command(greet, name='hi', doc='A greeting command')

Pass flags, positional arg specs, and middlewares at construction time:

.. code-block:: python

    from face import Command, Flag

    def serve(host, port):
        print(f'Serving on {host}:{port}')

    cmd = Command(
        serve,
        name='serve',
        flags=[
            Flag('--host', missing='localhost'),
            Flag('--port', parse_as=int, missing=8080),
        ],
    )

See `Positional arguments`_ below and :doc:`middleware` for those
constructor parameters.


Adding flags
------------

The most common way to add flags is through :meth:`~face.Command.add`
with a flag string as the first argument:

.. code-block:: python

    cmd = Command(handler)
    cmd.add('--verbose', parse_as=True, doc='enable verbose output')
    cmd.add('--output', char='-o', missing='out.txt', doc='output file path')
    cmd.add('--count', parse_as=int, missing=1, doc='repetition count')

``parse_as`` controls how the flag's argument is parsed:

- ``parse_as=str`` (default): flag takes one string argument.
- ``parse_as=int``, ``parse_as=float``, or any callable: flag takes one
  argument, converted by the callable.
- ``parse_as=True`` (or any non-callable): flag takes no argument. When
  present, the flag yields that value.

``missing`` controls the value when the flag is absent:

- ``missing=None`` (default): flag is optional, ``None`` when absent.
- ``missing=ERROR``: flag is required. Parse fails if absent.
- ``missing=<value>``: flag is optional, uses this default when absent.

``multi`` controls behavior when a flag appears more than once:

- ``multi='error'`` (default): raises :class:`~face.DuplicateFlag`.
- ``multi='extend'`` or ``multi=True``: collects all values into a list.
- ``multi='override'``: last value wins.

``char`` sets a short alias (e.g., ``char='-v'``).

Required flags
~~~~~~~~~~~~~~

Use :data:`face.ERROR` as the ``missing`` value:

.. code-block:: python

    from face import Command, ERROR

    def deploy(target):
        print(f'deploying to {target}')

    cmd = Command(deploy)
    cmd.add('--target', missing=ERROR, doc='deploy target (required)')

ListParam and ChoicesParam
~~~~~~~~~~~~~~~~~~~~~~~~~~

:class:`face.ListParam` parses comma-separated (or other delimiter) values
into a list. :class:`face.ChoicesParam` restricts input to a fixed set.

.. code-block:: python

    from face import Command, ListParam, ChoicesParam

    def tag(tags, env):
        print(f'tagging {env} with {tags}')

    cmd = Command(tag)
    cmd.add('--tags', parse_as=ListParam(str), doc='comma-separated tags')
    cmd.add('--env', parse_as=ChoicesParam(['dev', 'staging', 'prod']),
            missing='dev', doc='target environment')


Adding subcommands
------------------

Pass a callable to :meth:`~face.Command.add` to create a subcommand:

.. code-block:: python

    from face import Command, echo

    def add(posargs_):
        echo(str(sum(int(x) for x in posargs_)))

    def mul(posargs_):
        result = 1
        for x in posargs_:
            result *= int(x)
        echo(str(result))

    def main():
        cmd = Command(None, name='calc')
        cmd.add(add, posargs=True)
        cmd.add(mul, posargs=True)
        cmd.run()

``name`` defaults to the function name. Override with ``name='sub-name'``.

You can also add a pre-built :class:`~face.Command` instance:

.. code-block:: python

    sub = Command(handler, name='sub')
    sub.add('--flag', parse_as=True)

    root = Command(None, name='app')
    root.add(sub)

Subcommands nest arbitrarily. A subcommand is itself a Command, so it
can have its own subcommands, flags, and middleware.

Positional arguments
--------------------

Control positional argument handling with the ``posargs`` parameter:

- ``posargs=True``: accept any number of string positional args.
- ``posargs=False`` or omitted: no positional args allowed.
- ``posargs=int``: accept exactly that many positional args.
- ``posargs=str``: sets the display name and provides name.
- ``posargs=callable``: accept any number, each parsed with the callable.
- ``posargs=dict``: keyword arguments forwarded to :class:`~face.PosArgSpec`.
- ``posargs=PosArgSpec(...)``: full control over parsing and display.

Post-positional arguments (after ``--``) are controlled by
``post_posargs``, which accepts the same forms.


Adding middleware
-----------------

Add middleware decorated with :func:`face.face_middleware`:

.. code-block:: python

    from face import Command, face_middleware

    @face_middleware(provides=['db'])
    def provide_db(next_):
        db = connect_db()
        try:
            next_(db=db)
        finally:
            db.close()

    cmd = Command(handler)
    cmd.add(provide_db)

Both ``cmd.add(mw)`` and ``cmd.add_middleware(mw)`` work.
``add_middleware`` also accepts undecorated callables (it wraps them
automatically).

Middleware flags are automatically added to any Command that uses the
middleware. See :doc:`middleware` for full details.


Running
-------

Call :meth:`~face.Command.run` to parse ``sys.argv`` and dispatch:

.. code-block:: python

    cmd.run()

Pass explicit arguments for testing or embedding:

.. code-block:: python

    cmd.run(argv=['myapp', '--verbose', 'subcommand', 'arg1'])

``run()`` parses arguments, resolves the subcommand path, builds the
middleware chain, and calls the handler with injected dependencies.

For pre-validation of all subcommand paths without executing, call
:meth:`~face.Command.prepare`:

.. code-block:: python

    cmd.prepare()  # raises if any subcommand has unmet dependencies

``run()`` only validates the specific subcommand invoked. Call
``prepare()`` after all flags, subcommands, and middlewares are added to
catch configuration errors early.


Dependency injection
--------------------

Handler functions and middleware receive arguments by parameter name.
Face inspects the function signature and injects matching values
automatically. There are two categories of injectables: flags and
builtins.

Flag values are injected by the flag's ``name`` attribute (derived from
the flag string, e.g., ``--output-file`` becomes ``output_file``).

Builtin injectables are always available:

``args_``
    The :class:`~face.CommandParseResult` instance containing all parsed
    data.

``cmd_``
    String of the command name (``argv[0]``).

``subcmds_``
    Tuple of subcommand name strings for the matched path.

``flags_``
    :class:`~collections.OrderedDict` mapping flag name to parsed value.

``posargs_``
    Tuple of positional argument strings.

``post_posargs_``
    Tuple of post-positional argument strings (after ``--``).

``command_``
    The root :class:`~face.Command` instance.

``subcommand_``
    The specific subparser (:class:`~face.Parser`) for the matched
    subcommand path. Same as ``command_`` when no subcommand is used.

A handler can request any combination of these:

.. code-block:: python

    from face import Command, echo

    def status(verbose, flags_, subcmds_):
        echo(f'subcommands: {subcmds_}')
        echo(f'verbose: {verbose}')
        echo(f'all flags: {dict(flags_)}')

    cmd = Command(status)
    cmd.add('--verbose', parse_as=True)

Parameters not matching any flag or builtin name cause a
:exc:`NameError` at ``prepare()`` or ``run()`` time.


Error handling
--------------

:class:`face.CommandLineError` is raised on parse failures (bad flags,
missing required flags, invalid subcommands). It is a subclass of both
:class:`~face.FaceException` and :exc:`SystemExit`, so uncaught it exits
the process with a nonzero status code.

:class:`face.UsageError` is for handler-level validation errors. Raise it
from your handler or middleware to signal incorrect usage with a message:

.. code-block:: python

    from face import Command, UsageError

    def deploy(target):
        if '/' in target:
            raise UsageError('--target must not contain slashes')
        print(f'deploying to {target}')

    cmd = Command(deploy)
    cmd.add('--target', missing='prod')

``UsageError`` is also a :exc:`SystemExit` subclass, so it exits cleanly
when uncaught.


API reference
-------------

.. autoclass:: face.Command
   :members:

Command Exception Types
~~~~~~~~~~~~~~~~~~~~~~~

In addition to all the Parser-layer exceptions, a command or user endpoint function can raise:

.. autoclass:: face.CommandLineError

.. autoclass:: face.UsageError
