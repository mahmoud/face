Middleware
==========

Middleware wraps command handler dispatch. A middleware stack is a series of
functions, each calling the next, until the innermost handler function runs.
Outermost middleware is added first and called first.

Middleware is useful for cross-cutting concerns: logging, timing, error
handling, authentication, verbosity flags. Because middleware functions live
on a normal Python call stack, you get ``try``/``except``, early return, and
all other control flow for free.

Basic middleware
----------------

A middleware function is decorated with :func:`face.face_middleware`. Its
first parameter **must** be named ``next_``. Call ``next_()`` to continue
execution down the chain. If you return without calling ``next_()``, the
handler (and any downstream middleware) will not run.

.. code-block:: python

    import time

    from face import face_middleware, echo

    @face_middleware
    def timing_middleware(next_):
        start_time = time.time()
        ret = next_()
        echo('command executed in:', time.time() - start_time, 'seconds')
        return ret

Add middleware to a :class:`face.Command` with :meth:`~face.Command.add`:

.. code-block:: python

    from face import Command

    cmd = Command(my_handler)
    cmd.add(timing_middleware)

Middleware has the same dependency injection as handler functions. Flags and
builtins (``flags_``, ``args_``, ``subcmds_``, etc.) are automatically
available as parameters.


Providing values
----------------

Middleware can provide values to downstream middleware and handlers via
dependency injection. Declare what the middleware provides with the
``provides`` argument, then pass the values as keyword arguments to
``next_()``.

.. code-block:: python

    import time

    from face import face_middleware, echo

    @face_middleware(provides=['start_time'])
    def timing_middleware(next_):
        start_time = time.time()
        ret = next_(start_time=start_time)
        echo('command executed in:', time.time() - start_time, 'seconds')
        return ret

Any handler or downstream middleware that accepts a ``start_time`` parameter
will receive the value automatically:

.. code-block:: python

    def my_handler(start_time):
        # start_time injected by timing_middleware
        print('started at', start_time)


Middleware with flags
---------------------

Middleware can declare its own flags. These flags are automatically added to
any :class:`~face.Command` that uses the middleware. Flag values are injected
into the middleware function like any other dependency.

.. code-block:: python

    import time

    from face import face_middleware, Flag, echo

    @face_middleware(provides=['start_time'], flags=[Flag('--echo-time', parse_as=True)])
    def timing_middleware(next_, echo_time):
        start_time = time.time()
        ret = next_(start_time=start_time)
        if echo_time:
            echo('command executed in:', time.time() - start_time, 'seconds')
        return ret

Every :class:`~face.Command` that adds ``timing_middleware`` will gain the
``--echo-time`` flag. The flag value is injected into ``echo_time`` by name.


Optional middleware
-------------------

Set ``optional=True`` to skip middleware when none of its ``provides`` are
needed by the handler or other middleware in the chain.

.. code-block:: python

    @face_middleware(provides=['start_time'], optional=True)
    def timing_middleware(next_):
        start_time = time.time()
        ret = next_(start_time=start_time)
        return ret

If the resolved handler does not accept ``start_time``, this middleware is
removed from the chain entirely. This keeps overhead and help output minimal
for commands that do not use the provided values.


Weak dependencies
-----------------

Middleware parameters with default values create "weak" dependencies. If no
downstream function (handler or other middleware) needs the associated
injectable, the corresponding flag will not be parsed or shown in help
output.

.. code-block:: python

    @face_middleware(provides=['start_time'], flags=[Flag('--echo-time', parse_as=True)])
    def timing_middleware(next_, echo_time=False):
        start_time = time.time()
        ret = next_(start_time=start_time)
        if echo_time:
            echo('command executed in:', time.time() - start_time, 'seconds')
        return ret

Here ``echo_time`` defaults to ``False``. If no downstream function accepts
``echo_time``, the ``--echo-time`` flag will not appear in generated help.
This differs from handler functions, which always accept their declared
arguments regardless of defaults.


API Reference
-------------

.. autofunction:: face.face_middleware

.. autofunction:: face.middleware.is_middleware

.. autofunction:: face.middleware.check_middleware
