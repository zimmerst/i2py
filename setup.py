#!/usr/bin/env python

# 
#  Copyright (C) 2005 Christopher J. Stawarz <chris@pseudogreen.org>
# 
#  This file is part of i2py.
# 
#  i2py is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
# 
#  i2py is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
# 
#  You should have received a copy of the GNU General Public License
#  along with i2py; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#


import sys
from distutils.core import setup

# Need to do this to ensure that ytab.py exists and is up to date
import i2py


################################################################################
#
# Generate documentation with pydoc
#
################################################################################


if sys.argv[1] == 'sdist':
   import os, os.path
   import pydoc
   os.chdir('doc')
   moddir = os.path.join(os.pardir, 'i2py')
   sys.path.insert(0, moddir)
   pydoc.writedocs(moddir, 'i2py.')
   sys.path.pop(0)
   os.chdir(os.pardir)


################################################################################
#
# Run setup()
#
################################################################################


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


