face
====

|release| |calver| |changelog|

**face** is a Pythonic microframework for building command-line applications:

* First-class subcommand support
* Powerful middleware architecture
* Separate Parser layer
* Built-in flagfile support
* Handy testing utilities
* Themeable help display

Installation
------------

face is pure Python, and tested on Python 3.7+, as well as PyPy. Installation is easy::

  pip install face

Then get to building your first application!

.. code-block:: python

  from face import Command, echo

  def hello_world():
      "A simple greeting command."
      echo('Hello, world!')

  cmd = Command(hello_world)

  cmd.run()

  """
  # Here's what the default help looks like at the command-line:

  $ cmd --help
  Usage: cmd [FLAGS]

    A simple greeting command.


  Flags:

    --help / -h   show this help message and exit
  """

Getting Started
---------------

Check out our :doc:`tutorial` for more.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   tutorial
   command
   middleware
   testing
   io
   faq

.. |release| image:: https://img.shields.io/pypi/v/face.svg
             :target: https://pypi.org/project/face/

.. |calver| image:: https://img.shields.io/badge/calver-YY.MINOR.MICRO-22bfda.svg
            :target: https://calver.org

.. |changelog| image:: https://img.shields.io/badge/CHANGELOG-UPDATED-b84ad6.svg
            :target: https://github.com/mahmoud/face/blob/master/CHANGELOG.md
