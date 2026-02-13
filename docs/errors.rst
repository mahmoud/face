Errors
======

face uses a hierarchy of exceptions for parse errors and runtime errors.
All inherit from :class:`~face.FaceException`.

Exception hierarchy
-------------------

.. code-block:: text

   FaceException
   +-- ArgumentParseError
   |   +-- ArgumentArityError
   |   +-- InvalidSubcommand
   |   +-- UnknownFlag
   |   +-- InvalidFlagArgument
   |   +-- InvalidPositionalArgument
   |   +-- MissingRequiredFlags
   |   +-- DuplicateFlag
   +-- CommandLineError (also inherits SystemExit)
       +-- UsageError

Parse errors
------------

These are raised during argument parsing, before the handler runs.

.. autoclass:: face.FaceException
   :members:

.. autoclass:: face.ArgumentParseError
   :members:

.. autoclass:: face.errors.ArgumentArityError
   :members:

.. autoclass:: face.InvalidSubcommand
   :members:

.. autoclass:: face.UnknownFlag
   :members:

.. autoclass:: face.InvalidFlagArgument
   :members:

.. autoclass:: face.errors.InvalidPositionalArgument
   :members:

.. autoclass:: face.errors.MissingRequiredFlags
   :members:

.. autoclass:: face.DuplicateFlag
   :members:

Parse errors in practice
~~~~~~~~~~~~~~~~~~~~~~~~

When a command is run via :meth:`Command.run() <face.Command.run>`, parse errors
are caught internally, printed to stderr, and the process exits with code 1.
When using :class:`~face.CommandChecker` in tests, parse errors surface through
the :attr:`~face.testing.RunResult.exit_code` attribute.

To trigger specific parse errors:

.. code-block:: python

   from face import Command, Flag, ERROR

   cmd = Command(lambda: None, name='example')
   cmd.add('--count', parse_as=int, missing=ERROR)

   # Missing required flag -> MissingRequiredFlags
   # Bad flag value like --count abc -> InvalidFlagArgument
   # Unknown flag like --bogus -> UnknownFlag
   # Duplicate flag like --count 1 --count 2 -> DuplicateFlag (default multi='error')

Runtime errors
--------------

Runtime errors are raised from handler or middleware code during execution.

.. autoclass:: face.CommandLineError
   :no-index:

:class:`~face.CommandLineError` inherits from both :class:`~face.FaceException`
and :exc:`SystemExit`. If uncaught, it exits the process with code 1.

.. autoclass:: face.UsageError
   :no-index:

Raise :class:`~face.UsageError` in a handler to signal incorrect usage:

.. code-block:: python

   import os
   from face import UsageError

   def my_handler(path):
       if not os.path.exists(path):
           raise UsageError(f'path does not exist: {path}')

When :meth:`Command.run() <face.Command.run>` catches a
:class:`~face.UsageError`, it prints the message to stderr and exits with
code 1. In tests with :class:`~face.CommandChecker`, use
:meth:`~face.CommandChecker.fail` or ``fail_1()`` to assert the error.
