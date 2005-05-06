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
This file defines error-handling classes and functions that are used throughout
the package.
"""

class Error(object):
   def __init__(self, msg, lineno):
      global _errors
      self.msg = msg
      self.lineno = lineno
      _errors.append(self)

   def __str__(self):
      return '%d: %s: %s' % (self.lineno, type(self).__name__.replace('_', ' '),
                             self.msg)

class syntax_error(Error):
   pass

class conversion_error(Error):
   pass

class mapping_error(Error):
   pass

def error_occurred():
   if _errors:  return True
   return False

def get_error_list():
   return _errors

def clear_error_list():
   global _errors
   _errors = []

# Initialize error list
clear_error_list()

