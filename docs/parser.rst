Parser
======

The :class:`~face.Parser` handles argv parsing without dispatch. :class:`~face.Command`
inherits from Parser and adds dispatch, middleware, and help handling. Use Parser
directly when you need full control of program flow, or when integrating face
parsing into an existing application.

Parser
------

.. autoclass:: face.Parser
   :members:

Basic usage: create a Parser, add flags, call :meth:`~face.Parser.parse`, and
inspect the :class:`~face.CommandParseResult`:

.. code-block:: python

   from face import Parser, Flag, ERROR

   p = Parser('mytool', posargs=True)
   p.add('--output', doc='output file path')
   p.add('--verbose', parse_as=True, char='-v')
   p.add('--count', parse_as=int, missing=1)

   result = p.parse(['mytool', '--verbose', '--count', '5', 'input.txt'])

   print(result.flags)
   # OrderedDict([('output', None), ('verbose', True), ('count', 5), ...])

   print(result.posargs)
   # ('input.txt',)

The :meth:`~face.Parser.add` method accepts either a :class:`~face.Flag` instance
or the same arguments as the Flag constructor:

.. code-block:: python

   # These are equivalent:
   p.add(Flag('--output', doc='output file'))
   p.add('--output', doc='output file')

Parser also supports subcommands. Add a sub-Parser to create a command hierarchy:

.. code-block:: python

   p = Parser('git')
   sub = Parser('clone')
   sub.add('--depth', parse_as=int)
   p.add(sub)

   result = p.parse(['git', 'clone', '--depth', '1'])
   print(result.subcmds)   # ('clone',)
   print(result.flags)     # OrderedDict([('depth', 1), ...])


Flag
----

.. autoclass:: face.Flag

Flags are the primary configuration unit for CLI arguments. The ``--flag-name``
form is normalized to ``flag_name`` as the key in the parse result and as the
parameter name for dependency injection in Command handlers.

**Basic string flag** (default ``parse_as=str``):

.. code-block:: python

   Flag('--output', doc='output file path')
   # --output report.txt  =>  flags['output'] = 'report.txt'

**Boolean flag** (no argument, presence yields the value):

.. code-block:: python

   Flag('--verbose', parse_as=True, char='-v')
   # --verbose  =>  flags['verbose'] = True
   # (absent)   =>  flags['verbose'] = None

**Integer flag with default**:

.. code-block:: python

   Flag('--count', parse_as=int, missing=1)
   # --count 5  =>  flags['count'] = 5
   # (absent)   =>  flags['count'] = 1

**Required flag** (raises :class:`~face.ArgumentParseError` if missing):

.. code-block:: python

   from face import ERROR

   Flag('--name', missing=ERROR)

**Multi flag** (collect repeated flags into a list):

.. code-block:: python

   Flag('--tag', multi='extend')
   # --tag a --tag b  =>  flags['tag'] = ['a', 'b']

The ``multi`` parameter accepts:

- ``'error'`` (default): raise :class:`~face.DuplicateFlag` on repeat
- ``'extend'`` or ``True``: collect all values into a list
- ``'override'``: last value wins
- A callable: receives list of all values, returns final value

**Name normalization**: ``--my-flag`` becomes ``my_flag`` in the result dict
and as a handler parameter name.


FlagDisplay
-----------

.. autoclass:: face.FlagDisplay

Controls how a flag appears in help output. Usually created automatically
by the Flag constructor from its ``display`` argument. Pass ``False`` to
hide a flag, a string to set a custom label, or a :class:`~face.FlagDisplay`
instance for full control.


PosArgSpec
----------

.. autoclass:: face.PosArgSpec
   :members:

PosArgSpec configures positional argument acceptance. It is passed to
:class:`~face.Parser` or :class:`~face.Command` via the ``posargs`` or
``post_posargs`` constructor parameters.

**Shortcut forms** in the Parser/Command constructor:

.. code-block:: python

   Parser('cmd', posargs=True)           # accept any number of string args
   Parser('cmd', posargs=False)          # no positional args (default)
   Parser('cmd', posargs=int)            # parse each arg as int
   Parser('cmd', posargs='filename')     # sets display name and provides name
   Parser('cmd', posargs={'min_count': 1, 'max_count': 3})  # dict of kwargs

**Full PosArgSpec with provides**:

.. code-block:: python

   from face import PosArgSpec

   spec = PosArgSpec(parse_as=int, min_count=1, max_count=3, name='number')
   p = Parser('sum', posargs=spec)
   result = p.parse(['sum', '1', '2', '3'])
   print(result.posargs)  # (1, 2, 3)

When ``provides`` (or ``name``) is set, the parsed positional args are injected
into Command handler functions under that name. With ``min_count=1`` and
``max_count=1``, the single value is unwrapped (not a tuple).

**Disabling positional args explicitly**:

.. code-block:: python

   PosArgSpec(parse_as=ERROR)  # raises if any positional args are passed


PosArgDisplay
-------------

.. autoclass:: face.PosArgDisplay

Controls how positional arguments appear in help output. Usually created
automatically by :class:`~face.PosArgSpec` from its ``display`` argument.


ListParam
---------

.. autoclass:: face.ListParam

ListParam lets a single flag accept a comma-separated list:

.. code-block:: python

   from face import Flag, ListParam

   Flag('--tags', parse_as=ListParam())
   # --tags a,b,c  =>  flags['tags'] = ['a', 'b', 'c']

   Flag('--ports', parse_as=ListParam(parse_one_as=int))
   # --ports 80,443,8080  =>  flags['ports'] = [80, 443, 8080]

   Flag('--items', parse_as=ListParam(sep=';', strip=True))
   # --items "one ; two ; three"  =>  flags['items'] = ['one', 'two', 'three']

Values containing the separator can be quoted:
``--tags 'a,"b,c",d'`` yields ``['a', 'b,c', 'd']``.


ChoicesParam
------------

.. autoclass:: face.ChoicesParam

Restricts a flag's value to a fixed set of choices. The parse type is inferred
from the first choice by default:

.. code-block:: python

   from face import Flag, ChoicesParam

   Flag('--color', parse_as=ChoicesParam(['red', 'green', 'blue']))
   # --color red    =>  flags['color'] = 'red'
   # --color yellow =>  raises ArgumentParseError

   Flag('--level', parse_as=ChoicesParam([1, 2, 3]))
   # --level 2  =>  flags['level'] = 2  (parsed as int)


CommandParseResult
------------------

.. autoclass:: face.CommandParseResult
   :members:

The result object returned by :meth:`Parser.parse`. Contains all parsed data:

- ``name``: the program name (argv[0])
- ``subcmds``: tuple of matched subcommand names
- ``flags``: :class:`~collections.OrderedDict` mapping flag names to values
- ``posargs``: tuple of parsed positional arguments
- ``post_posargs``: tuple of post-positional arguments (after ``--``)

When used with :class:`~face.Command`, the result is also available via the
``args_`` builtin in handler functions. Individual flags are also injected
by name (e.g., a ``--output`` flag becomes the ``output`` parameter).


ERROR Sentinel
--------------

``face.ERROR`` is a sentinel value used in two places:

1. ``Flag('--name', missing=ERROR)`` makes a flag required. Parsing raises
   :class:`~face.ArgumentParseError` if the flag is absent.
2. ``PosArgSpec(parse_as=ERROR)`` disables positional arguments. Parsing raises
   if any positional arguments are provided.

Import it directly:

.. code-block:: python

   from face import ERROR
