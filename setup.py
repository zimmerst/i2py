#!/usr/bin/env python

#
# Setup script for i2py
#

# Make sure i2py/ytab.py exists and is up to date
import i2py.parser

from distutils.core import setup, Extension

setup(name='i2py',
      version='0.0.9',
      author='Christopher J. Stawarz',
      author_email='chris@pseudogreen.org',
      url='http://software.pseudogreen.org/i2py/',
      license='http://www.fsf.org/copyleft/gpl.html',
      packages=['i2py'],
      scripts=['idl2python'],
     )

