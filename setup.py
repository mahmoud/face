"""A command-line interface parser and framework, friendly for users,
full-featured for developers.
"""

from setuptools import setup


__author__ = 'Mahmoud Hashemi'
__version__ = '24.0.0'
__contact__ = 'mahmoud@hatnote.com'
__url__ = 'https://github.com/mahmoud/face'
__license__ = 'BSD'


setup(name='face',
      version=__version__,
      description="A command-line application framework (and CLI parser). Friendly for users, full-featured for developers.",
      long_description=__doc__,
      author=__author__,
      author_email=__contact__,
      url=__url__,
      packages=['face', 'face.test'],
      include_package_data=True,
      zip_safe=False,
      license=__license__,
      platforms='any',
      install_requires=['boltons>=20.0.0'],
      classifiers=[
          'Topic :: Utilities',
          'Intended Audience :: Developers',
          'Topic :: Software Development :: Libraries',
          'Programming Language :: Python :: 3.7',
          'Programming Language :: Python :: 3.8',
          'Programming Language :: Python :: 3.9',
          'Programming Language :: Python :: 3.10',
          'Programming Language :: Python :: 3.11',
          'Programming Language :: Python :: 3.12',
          'Programming Language :: Python :: 3 :: Only',
          'Programming Language :: Python :: Implementation :: CPython',
          'Programming Language :: Python :: Implementation :: PyPy', ]
      )

"""
A brief checklist for release:

* tox
* git commit (if applicable)
* Bump setup.py version off of -dev
* git commit -a -m "bump version for vx.y.z release"
* rm -rf dist/*
* python setup.py sdist bdist_wheel
* twine upload dist/*
* bump docs/conf.py version
* git commit
* git tag -a vx.y.z -m "brief summary"
* write CHANGELOG
* git commit
* bump setup.py version onto n+1 dev
* git commit
* git push

"""
