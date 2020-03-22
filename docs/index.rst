.. face documentation master file, created by
   sphinx-quickstart on Tue Mar 21 23:21:21 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

face
====

|release| |calver| |changelog|

**face** is a Pythonic microframework for building web applications featuring:

* Fast, coherent routing system
* Powerful middleware architecture
* Built-in observability features via the ``meta`` Application
* Extensible support for multiple templating systems
* Werkzeug_-based WSGI/HTTP primitives, same as Flask_

.. _Werkzeug: https://github.com/pallets/werkzeug
.. _Flask: https://github.com/pallets/flask

Installation
------------

face is pure Python, and tested on Python 2.7-3.7+, as well as PyPy. Installation is easy::

  pip install face

Then get to building your first application!

.. code-block:: python

  from face import Command, echo

  def hello_world():
      "A simple greeting command."
      echo('Hello, world!')

  cmd = Command(hello_world)

  cmd.run()


Getting Started
---------------

Check out our :doc:`tutorial` for more.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   tutorial
   command
   middleware
   utilities
   faq

.. |release| image:: https://img.shields.io/pypi/v/face.svg
             :target: https://pypi.org/project/face/

.. |calver| image:: https://img.shields.io/badge/calver-YY.MINOR.MICRO-22bfda.svg
            :target: https://calver.org

.. |changelog| image:: https://img.shields.io/badge/CHANGELOG-UPDATED-b84ad6.svg
            :target: https://github.com/mahmoud/face/blob/master/CHANGELOG.md
