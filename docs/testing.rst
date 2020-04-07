Testing
=======

Face provides a full-featured test client for maintaining high-quality
command-line applications.

.. autoclass:: face.CommandChecker

   .. automethod:: run

   .. automethod:: fail

   .. method:: fail_X

      Test that a command fails with exit code ``X``, where ``X`` is an integer.

      For testing convenience, any method of pattern ``fail_X()`` is the
      equivalent to ``fail(exit_code=X)``, and ``fail_X_Y()`` is
      equivalent to ``fail(exit_code=[X, Y])``, providing ``X`` and
      ``Y`` are integers.



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



.. autoexception:: face.testing.CheckError
