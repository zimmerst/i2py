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


"""
Convert IDL programs and scripts to Python

i2py provides tools for converting programs and scripts written in Research
System Inc.'s IDL programming language to Python.  It is not an IDL-compatible
front end for the Python interpreter, nor does it make any attempt to replicate
the functionality of the IDL standard library.  Rather, its only purpose is to
perform source-to-source conversion of legacy IDL code to Python.  Currently,
it supports only procedural IDL, although support for object-oriented code may
be added in the future.
"""


import os, os.path
import config
from error import error_occurred, get_error_list
from parser import parse
from map import map_var, map_pro, map_func
import maplib


__version__ = '0.1.0'


def load_rcfile(filename=None):
   """
   Loads an i2py rcfile, which is a regular Python script that modifies i2py's
   runtime configuration.  The file is evaluated with execfile in a namespace
   that contains only the builtins; the functions map_var, map_proc,
   and map_func from i2py.map; and i2py's config module.  Custom variable and
   subroutine mappings are defined by calls to the map_* functions, and global
   configuration settings are made by assigning to the appropriate attributes
   of config.

   If filename is given, the specified file will be loaded.  Otherwise, the
   function looks for the following files, in order, and loads the first one it
   finds:
   
     Current directory:		i2pyrc
     Current directory:		i2pyrc.py
     User's home directory:	.i2pyrc
     User's home directory:	.i2pyrc.py

   If filename is not given and none of the standard configuration files are
   found, the function does nothing.
   """

   if not filename:
      stem = 'i2pyrc'
      suffixes = ('', '.py')

      for s in suffixes:
         f = stem + s
         if os.path.isfile(f):
            filename = f
	    break
      else:
         home = os.environ.get('HOME')
         if home:
            for s in suffixes:
	       f = os.path.join(home, '.' + stem + s)
               if os.path.isfile(f):
                  filename = f
	          break
	    else:
	       # Couldn't find a standard rcfile, so quit
	       return

   # Evaluate the rcfile, using rcdict for the globals dict so that our
   # namespace doesn't get polluted
   rcdict = {'map_var':map_var, 'map_pro':map_pro, 'map_func':map_func,
             'config':config}
   execfile(filename, rcdict)


