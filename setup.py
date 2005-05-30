#!/usr/bin/env python

#
# Setup script for i2py
#

from distutils.core import setup

# Need to do this to ensure that ytab.py exists and is up to date
import i2py

# Grab the description from the package's doc string
desc = i2py.__doc__.split('\n\n')

setup(name='i2py',
      version=i2py.__version__,
      author='Christopher J. Stawarz',
      author_email='chris@pseudogreen.org',
      url='http://software.pseudogreen.org/i2py/',
      license='http://www.fsf.org/licensing/licenses/gpl.html',
      platforms=['any'],
      description=desc[0].strip(),
      long_description=('\n' + '\n\n'.join(desc[1:]).strip() + '\n'),
      packages=['i2py'],
      scripts=['idl2python'],
     )

