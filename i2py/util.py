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
General utility functions
"""


import config


def indent(obj, ntabs=1, tab=None):
   """
   Converts obj to a string, pads the beginning of each line with ntabs copies
   of tab, and returns the result.  If tab is not given, config.idltab is used.
   """
   if not tab:  tab = config.idltab
   pad = ntabs * tab
   return pad + str(obj).replace('\n', '\n' + pad).rstrip(tab)


def classdef(obj):
   if hasattr(obj, 'classdef'):
      return obj.classdef()
   return [], [], ''

def pycode(obj):
   """
   If obj has a pycode() method, returns the result of calling it.  Otherwise,
   returns obj converted to a string.
   """
   if hasattr(obj, 'pycode'):
      return obj.pycode()
   return str(obj)


def pyindent(obj, ntabs=1, tab=None):
   """
   Converts obj to a string of Python code with pycode(), pads the beginning
   of each line with ntabs copies of tab, and returns the result.  If tab is
   not given, config.pytab is used.
   """
   if not tab:  tab = config.pytab
   pad = ntabs * tab
   return pad + pycode(obj).replace('\n', '\n' + pad).rstrip(tab)


def pycomment(obj):
   """
   Calls pyindent() on obj with tab set to '# ' and returns the result.
   """
   return pyindent(obj, tab='# ')


def pyname(name):
   """
   Converts name to a Python name by calling config.pynameconv() on it.  If the
   converted name begins with '!', the '!' is replaced by config.sysvarprefix.
   Also, replaces "$" with the string "_dollar_".
   Returns the resulting name.
   """
   name = config.pynameconv(name)
   if name[0] == '!':
      name = config.sysvarprefix + name[1:]
   name = name.replace('$', '_dollar_')
   # As preparation for classes, replaces '::' and '->' with '.'
   # name = name.replace('->', '.')
   # name = name.replace('::', '.')
   return name


def reduce_expression(expr):
   """
   Tries to reduce expr (a string containing a Python expression) to a constant
   value by evaluating it.  If no exception occurs during the evaluation, a
   string representation of the result is returned.  Otherwise, expr is
   returned unchanged.
   """
   try:
      return str(eval(expr, {}))
   except:
      return expr


