#!/usr/bin/env python

#
# Setup script for i2py
#

# Make sure i2py/ytab.py exists and is up to date
import i2py.parser

from distutils.core import setup

setup(name='i2py',
      version='0.0.9',
      author='Christopher J. Stawarz',
      author_email='chris@pseudogreen.org',
      url='http://software.pseudogreen.org/i2py/',
      license='http://www.fsf.org/copyleft/gpl.html',
      platforms=['any'],
      description='Convert IDL programs and scripts to Python',
      long_description="""
i2py provides tools for converting programs and scripts written in Research
System Inc.'s IDL programming language to Python.  It is not an IDL-compatible
front end for the Python interpreter, nor does it make any attempt to replicate
the functionality of the IDL standard library.  Rather, its only purpose is to
perform source-to-source conversion of legacy IDL code to Python.  Currently,
it supports only procedural IDL, although support for object-oriented code may
be added in the future.
      """,
      packages=['i2py'],
      scripts=['idl2python'],
     )

