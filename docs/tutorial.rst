Tutorial
========

.. contents:: Contents
   :local:
   :depth: 2


Part I: Say
-----------

The field of overdone versions of ``echo`` has been too long dominated
by Big GNU.
Today, we start taking back the power.
We will implement the ``say`` command.

Positional arguments
~~~~~~~~~~~~~~~~~~~~

While face offers a Parser interface underneath, the canonical way to
create even the simplest CLI is with the Command object.

To demonstrate, we'll start with the basics, positional arguments.
``say hello world`` should print ``hello world``:

.. code::

    from face import Command, echo


    def main():
        cmd = Command(say, posargs=True)  # posargs=True means we accept positional arguments
        cmd.run()


    def say(posargs_):  # positional arguments are passed through the posargs_ parameter
        echo(' '.join(posargs_))  # our business logic


    if __name__ == '__main__':  # standard fare Python: https://stackoverflow.com/questions/419163
        main()

A basic Command takes a single function entrypoint, in our case, the
``say`` function.

.. note::

   Face's :func:`echo` function is a version of :func:`print` with
   improved options and handling of console states, ideal for CLIs.

Flags
~~~~~

Let's give ``say`` some options:

``say --upper hello world``
or
``say -U hello world``
should print
``HELLO WORLD``.

.. code::

   ...

    def main():
        cmd = Command(say, posargs=True)
        cmd.add('--upper', char='-U', parse_as=True, doc='uppercase all output')
        cmd.run()


    def say(posargs_, upper):  # our --upper flag is bound to the upper parameter
        args = posargs_
        if upper:
            args = [a.upper() for a in args]
        echo(' '.join(args))

    ...

The ``parse_as`` keyword argument being set to ``True`` means that the
presence of the flag results in the ``True`` value itself. As we'll
see below, flags can take arguments, too.

Flags with values
~~~~~~~~~~~~~~~~~

Let's add more flags, this time ones that take values.

``say --separator . hello world`` will print ``hello.world``.
Likewise,
``say --count 2 hello world``
will repeat it twice:
``hello world hello world``

.. code::

   ...

   def main():
       cmd = Command(say, posargs=True)
       cmd.add('--upper', char='-U', parse_as=True, doc='uppercase all output')
       cmd.add('--separator', missing=' ', doc='text to put between arguments')
       cmd.add('--count', parse_as=int, missing=1, doc='how many times to repeat')
       cmd.run()


    def say(posargs_, upper, separator, count):
        args = posargs_ * count
        if upper:
            args = [a.upper() for a in args]
        echo(separator.join(args))

    ...

Now we can see that ``parse_as``:

  - Can take a value (e.g., ``True``), which make the flag no-argument
  - Can take a callable (e.g., ``int``), which is used to convert the single argument
  - Defaults to ``str`` (as used by ``separator``)

We can also see the ``missing`` keyword argument, which specifies the
value to be passed to the Command's handler function if the flag is
absent. Without this, ``None`` is passed.

.. note::

   Face also supports required flags, though they are not an ideal CLI
   UX best practice. Simply set ``missing`` to :data:`face.ERROR`.

More Interesting Flag Types
~~~~~~~~~~~~~~~~~~~~~~~~~~~


``say --multi-separator=@,# hello wonderful world``
prints
``hello@wonderful#world``
(The separators repeat)

``say --from-file=fname``
reads the file and adds all words from it to its
output

``say --animal=dog|cat|cow``
will prepend "woof", "meow", or "moo" respectively.


Part II: Calc
-------------

(Details TBD!)

With ``echo`` having met its match,
we are on to bigger and better:
this time,
with math

.. code::

    $ num
    <Big help text>

Add and Multiply
~~~~~~~~~~~~~~~~

.. code::

    $ num add 1 2
    3


.. code::

    $ num mul 3 5
    15


Subtract
~~~~~~~~

.. code::

    $ num sub 10 5
    5
    $ num sub 5 10
    Error: can't substract
    $ num --allow-negatives 5 10
    -5


Divide
~~~~~~

.. code::

    $ num div 2 3
    0.6666666666666666
    $ num div --int 2 3
    0


Precision support
~~~~~~~~~~~~~~~~~


.. code::

    $ num add 0.1 0.2
    0.30000000000000004
    $ num add --precision=3 0.1 0.2
    0.3

Oh, now let's add it to all subcommands.

Part III: Middleware
--------------------

(Details TBD!)

Doing math locally is all well and good,
but sometimes we need to use the web.

We will add an "expression" sub-command
to num that uses ``https://api.mathjs.org/v4/``.
But since we want to unit test it,
we will create the ``httpx.Client`` in a middleware.

.. code::

    $ num expression "1 + (2 * 3)"
    7

But we can also write a unit test that does
not touch the web:

.. code::

    $ pytest test_num.py


Part IV: Examples
-----------------

There are more realistic examples of
`face`
usage out there,
that can serve as a reference.

Cut MP4
~~~~~~~

The script
`cut_mp4`_
is a quick but useful tool to cut recordings using
``ffmpeg``.
I use it to slice and dice the Python meetup recordings.
It does not have subcommands or middleware,
just a few flags.


.. _cut_mp4: https://github.com/mahmoud/face/blob/master/examples/cut_mp4.py

Glom
~~~~

`Glom`_
is a command-line interface front end for the ``glom`` library.
It does not have any subcommands,
but does have some middleware usage.


.. _Glom: https://github.com/mahmoud/glom/blob/master/glom/cli.py

Pocket Protector
~~~~~~~~~~~~~~~~

`Pocket Protector`_ is a secrets management tool.
It is a medium-sized application with quite a few subcommands
for manipulating a YAML file.

.. _Pocket Protector: https://github.com/SimpleLegal/pocket_protector/blob/master/pocket_protector/cli.py

Montage Admin Tools
~~~~~~~~~~~~~~~~~~~

`Montage Admin Tools`_
is a larger application.
It has nested subcommands
and a database connection.
It is used to administer a web application.

.. _Montage Admin Tools: https://github.com/hatnote/montage/blob/master/tools/admin.py
