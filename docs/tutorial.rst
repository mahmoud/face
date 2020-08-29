Fake Face Tutorial
==================


Part I: Say
-----------

The field of overdone versions of ``echo`` has been too long dominated
by Big GNU.
Today, we start taking back the power.
We will implement ``say``.

Positional arguments
~~~~~~~~~~~~~~~~~~~~

When there are no special flags,
``say hello world``
should just print ``hello world``:

.. code::

    fake code

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
