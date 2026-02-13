Testing
=======

:class:`~face.CommandChecker` wraps a :class:`~face.Command` for
testing. It captures stdout, stderr, and exit codes in-process. No
subprocess spawning, no shell quoting issues.

Basic usage
-----------

Create a :class:`~face.CommandChecker` from your :class:`~face.Command`,
call :meth:`~face.CommandChecker.run` with argument strings, and inspect
the :class:`~face.testing.RunResult`:

.. code-block:: python

    from face import Command, CommandChecker

    def hello(name='world'):
        print(f'Hello, {name}')

    cmd = Command(hello)
    cmd.add('--name')

    cc = CommandChecker(cmd)
    result = cc.run('hello --name Alice')
    assert result.stdout == 'Hello, Alice\n'
    assert result.exit_code == 0

:meth:`~face.CommandChecker.run` returns a :class:`~face.testing.RunResult`.
If the command exits with an unexpected exit code, :exc:`~face.testing.CheckError`
is raised. By default, ``run()`` expects exit code ``0``.

Testing failures
----------------

Use :meth:`~face.CommandChecker.fail` to assert that a command exits
with a non-zero code. It has the same signature as ``run()``, but
raises :exc:`~face.testing.CheckError` if the command exits ``0``:

.. code-block:: python

    from face import Command, CommandChecker, ERROR

    def greet(name):
        print(f'Hello, {name}')

    cmd = Command(greet)
    cmd.add('--name', missing=ERROR)

    cc = CommandChecker(cmd)
    result = cc.fail('greet')  # --name is required, so this fails
    assert result.exit_code != 0
    assert 'name' in result.stderr

For a specific exit code, use the ``fail_X`` shorthand. ``cc.fail_1(args)``
is equivalent to ``cc.fail(args, exit_code=1)``. Multiple codes work
too: ``cc.fail_1_2(args)`` accepts exit code 1 or 2.

Environment and directory isolation
------------------------------------

:class:`~face.CommandChecker` accepts ``env`` and ``chdir`` to isolate
tests from the host environment. Both can be set at construction time
(as defaults) or per-run:

.. code-block:: python

    import tempfile
    from face import Command, CommandChecker

    def show_env(home='/default'):
        print(home)

    cmd = Command(show_env)
    cmd.add('--home')

    # Set base environment and working directory
    with tempfile.TemporaryDirectory() as tmpdir:
        cc = CommandChecker(cmd, env={'APP_MODE': 'test'}, chdir=tmpdir)
        result = cc.run('show_env --home /tmp/test')
        assert result.stdout == '/tmp/test\n'

        # Override env per-run
        result = cc.run('show_env --home /other', env={'APP_MODE': 'prod'})

Environment variables are restored after each run. The working directory
is also restored, even if the command raises an exception.

Testing stdin and prompts
-------------------------

Pass ``input`` to :meth:`~face.CommandChecker.run` to simulate user
input. This works with :func:`face.prompt` and :func:`face.prompt_secret`:

.. code-block:: python

    from face import Command, CommandChecker, prompt

    def ask_name():
        name = prompt('Your name: ')
        print(f'Hello, {name}')

    cmd = Command(ask_name)
    cc = CommandChecker(cmd)
    result = cc.run('ask_name', input='Alice\n')
    assert 'Hello, Alice' in result.stdout

For multiple prompts, provide all answers separated by newlines in
the ``input`` string.

RunResult reference
-------------------

.. autoclass:: face.testing.RunResult

   .. attribute:: args

      The arguments passed to :meth:`~face.CommandChecker.run()`.

   .. attribute:: input

      The string input passed to the command, if any.

   .. attribute:: exit_code

      The integer exit code returned by the command. ``0`` conventionally indicates success.

   .. autoattribute:: stdout

   .. autoattribute:: stderr

   .. attribute:: stdout_bytes

      The output ("stdout") of the command, as an encoded bytestring. See
      :attr:`stdout` for the decoded text.

   .. attribute:: stderr_bytes

      The error output ("stderr") of the command, as an encoded
      bytestring. See :attr:`stderr` for the decoded text. May be
      ``None`` if *mix_stderr* was set to ``True`` in the
      :class:`CommandChecker`.

   .. autoattribute:: returncode

   .. attribute:: exc_info

      A 3-tuple of the internal exception, in the same fashion as
      :func:`sys.exc_info`, representing the captured uncaught
      exception raised by the command function from a
      :class:`~face.CommandChecker` with *reraise* set to
      ``True``. For advanced use only.

   .. autoattribute:: exception


CheckError reference
--------------------

.. autoexception:: face.testing.CheckError


CommandChecker reference
------------------------

.. autoclass:: face.CommandChecker

   .. automethod:: run

   .. automethod:: fail

   .. method:: fail_X

      Test that a command fails with exit code ``X``, where ``X`` is an integer.

      For testing convenience, any method of pattern ``fail_X()`` is the
      equivalent to ``fail(exit_code=X)``, and ``fail_X_Y()`` is
      equivalent to ``fail(exit_code=[X, Y])``, providing ``X`` and
      ``Y`` are integers.
