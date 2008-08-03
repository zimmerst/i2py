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
Error-handling classes and functions
"""


################################################################################
#
# Internal error handling
#
################################################################################


class InternalError(Exception):
   "An internal (i.e. implementation) error that should halt execution"
   pass


################################################################################
#
# Application error handling
#
################################################################################


#
# Error classes
#

# List where all Error objects store themselves
_errors = []

class Error(object):
   """
   A runtime error produced by invalid or unusable input that should be
   handled and reported gracefully.  Upon creation, instances automatically
   register themselves with the internal error list.
   """

   def __init__(self, msg, lineno):
      self.msg = msg
      self.lineno = lineno
      _errors.append(self)

   def __str__(self):
      return '%d: %s: %s' % (self.lineno, type(self).__name__.replace('_', ' '),
                             self.msg)

class syntax_error(Error):
   "Syntax error thrown during lexing or parsing"
   pass

class conversion_error(Error):
   "Conversion error thrown during code generation"
   pass

class mapping_error(Error):
   "Mapping error thrown during code generation"
   pass


#
# Error list management functions
#

def error_occurred():
   "Returns a boolean indicating if any errors occurred"
   return bool(_errors)

def get_error_list():
   "Returns a copy of the error list"
   return list(_errors)

def clear_error_list():
   "Clears the error list"
   global _errors
   _errors = []

