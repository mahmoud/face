Input / Output
================

Face provides I/O utilities for CLI applications. These functions handle
TTY detection, ANSI escape code stripping, and cross-platform concerns so
your output behaves correctly whether piped to a file or displayed in a
terminal.

Use these instead of bare ``print()`` and ``input()`` calls. They respect
output redirection, handle encoding edge cases, and integrate with face's
error handling.

.. code-block:: python

   from face import echo, echo_err, prompt

   def my_handler(verbose):
       if verbose:
           echo_err('starting work...')
       result = do_work()
       echo(result)

   def interactive_handler():
       name = prompt('Enter your name: ')
       echo(f'Hello, {name}!')

.. autofunction:: face.echo

.. autofunction:: face.echo_err

.. autofunction:: face.prompt

.. autofunction:: face.prompt_secret

.. note::

   Additional I/O utilities (choice prompting, color flag integration) may
   be added in future releases.
