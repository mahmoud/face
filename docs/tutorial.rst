Tutorial
========


Part I: Say
-----------

The field of overdone versions of ``echo`` has been too long dominated
by Big GNU.
Today, we start taking back the power.
We will implement the ``say`` command.

Positional arguments
~~~~~~~~~~~~~~~~~~~~

To demonstrate, we'll start with the basics.
``say hello world``
should just print ``hello world``:

.. code::

    from face import Command, echo


    def main():
        cmd = Command(say, posargs=True)  # posargs=True tells face we want positional arguments
        cmd.run()


    def say(posargs_):  # we access positional arguments through the posargs_ parameter face passes
        echo(' '.join(posargs_))  # our business logic


    if __name__ == '__main__':  # standard fare Python: https://stackoverflow.com/questions/419163
        main()


Flags
~~~~~

``say --upper-case hello world``
or
``say -U hello world``
should print
``HELLO WORLD``.

While we're at it,
let's implement lower-case too!

Counting Flags
~~~~~~~~~~~~~~

``say --space hello world``
should print
``hello  world``
(two spaces).
This can be repeated:
``say --space --space --space hello world``,
or
``say -S -S -S hello world``
or just
``say -SSS hello world``
will print
``hello    world``.

Different Types of Flags
~~~~~~~~~~~~~~~~~~~~~~~~

``say --separator=. hello world``
will print
``hello.world``.

Likewise,
``say --repeat=2 hello world``
will repeat it twice:
``hello world hello world``

More Interesting Flags
~~~~~~~~~~~~~~~~~~~~~~


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
