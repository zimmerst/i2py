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
Classes and functions for mapping IDL variables and subroutines to Python ones
"""


import util


################################################################################
#
# Extra code handling
#
################################################################################


_extracode = []   # List of extra code strings


def add_extra_code(code):
   """
   Given code, a single string or sequence of strings containing Python code,
   checks whether each string is already in the extra code list and, if not,
   appends it to the list.  Extra code is injected into the top level of the
   Python module created by ir.TranslationUnit.pycode().
   """
   if not code:  return   # Do nothing for a false/empty argument
   if isinstance(code, basestring):
      code = [code]
   for item in code:
      item = item.strip()
      if item not in _extracode:
         _extracode.append(item)


def get_extra_code():
   """
   Returns a string containing all the code in the extra code list, suitable
   for direct injection into a Python module.
   """
   return '\n\n'.join(_extracode)


def clear_extra_code():
   "Empties the extra code list"
   global _extracode
   _extracode  = []


################################################################################
#
# Mapping base classes
#
################################################################################


class Error(Exception):
   "A runtime mapping error"
   pass


class Mapping(object):
   "Base class for all mappings"

   def pyname(self):
      "Returns a Pythonized name for this mapping"
      if self._pyname:
         return self._pyname
      return util.pyname(self.name)


################################################################################
#
# Variable maps
#
################################################################################


# Dictionary where all VariableMapping objects store themselves.  The key for
# each mapping is its name converted to upper case.
_variables = {}


class VariableMapping(Mapping):
   "Defines how to generate Python code for a specific IDL variable"

   def __init__(self, name, pyname=None, extracode=None, readonly=False):
      """
      Creates a new VariableMapping.  name is the IDL name of the variable,
      pyname is the Python code that should replace the IDL name (if not
      provided, defaults to util.pyname(name)), and extracode is a string or
      list of strings containing necessary top-level module code (e.g. import
      statements, variable definitions).  If readonly is True, then the mapping
      for this variable is fixed and cannot be overwritten.
      """

      self.name = name
      uc_name = name.upper()

      old_map = _variables.get(uc_name)
      if old_map and old_map.readonly:
         raise Error("a read-only mapping for variable '%s' already exists",
	             self.name)

      self._pyname = pyname
      self.extracode = extracode
      self.readonly = readonly

      _variables[uc_name] = self

   def pyname(self):
      "Returns appropriate Python code for the variable"
      add_extra_code(self.extracode)
      return Mapping.pyname(self)


def map_var(name, pycode=None, extracode=None, readonly=False):
   """
   Creates and returns a new VariableMapping, passing the given arguments to
   the constructor
   """
   return VariableMapping(name, pycode, extracode, readonly)


def get_variable_map(name):
   """
   If a VariableMapping exists for the given variable name, returns it.
   Otherwise, returns None.
   """
   return _variables.get(name.upper())


################################################################################
#
# Subroutine maps
#
################################################################################


# Dictionary where all SubroutineMapping objects store themselves.  The key for
# each mapping is its name converted to upper case.
_subroutines = {}


class SubroutineMapping(Mapping):
   """
   Defines how to generate Python code for the definition and invocation of a
   specific IDL subroutine
   """

   def __init__(self, name, pyname=None, function=False,
                inpars=(), outpars=(), noptional=0, inkeys=(), outkeys=(),
		callfunc=None, extracode=None, readonly=False):
      """
      Creates a new SubroutineMapping.

      name is the IDL name of the subroutine.  pyname is the Python name that
      should replace the IDL name (if not provided, defaults to
      util.pyname(name)).  function is a flag indicating whether the mapping is
      for an IDL function (as opposed to a procedure).

      inpars and outpars are sequences of integers.  Each integer is the
      position index (starting at 1) of a parameter in the IDL definition of
      the subroutine.  If a parameter is used for input, its index should be in
      inpars.  If a parameter is used for output, its index should be in
      outpars.  If a parameter is used for both input and output, its index
      should be in both inpars and outpars.  noptional is an integer specifying
      the number of parameters (input and output) that are optional.

      inkeys and outkeys are sequences of strings.  Each string is the name of
      a keyword in the IDL definition of the subroutine.  If a keyword is used
      for input, its name should be in inkeys.  If a keyword is used for
      output, its name should be in outkeys.  If a keyword is used for both
      input and output, its name should be in both inkeys and outkeys.

      If given, callfunc is used to perform custom generation of the Python
      calling code for the subroutine.  It must be a function that accepts two
      arguments and returns a string.  The first argument is a list of strings,
      each element of which is the Python code for an argument to the
      subroutine.  The second is another list of strings containing the Python
      code for the targets to which the subroutine's output is assigned.  The
      string returned must contain a complete Python statement/expression for
      the call to the procedure/function.

      extracode is a string or list of strings containing necessary top-level
      module code (e.g. import statements, variable and function defintions).

      If readonly is True, then the mapping for this subroutine is fixed and
      cannot be overwritten.
      """

      self.name = name
      uc_name = name.upper()

      # Check for an existing read-only map
      old_map = _subroutines.get(uc_name)
      if old_map and old_map.readonly:
         raise Error("a read-only mapping for subroutine '%s' already exists",
	             self.name)

      # Store input and output parameters
      self.inpars = tuple(inpars)
      if outpars and function:
         raise Error('functions cannot have output parameters')
      self.outpars = tuple(outpars)

      # Store number of parameters and validate parameter list
      pars = list(self.inpars)
      pars += [ p for p in self.outpars if p not in self.inpars ]
      pars.sort()
      self.npars = len(pars)
      if pars != range(1, self.npars+1):
         raise Error('incomplete or invalid parameter list: %s' % pars)

      # Store number of optional parameters, ensuring it's >=0
      noptional = int(noptional)
      if noptional < 0:  noptional = 0
      self.noptional = noptional

      # Store input and output keywords
      self.inkeys = tuple([ k.upper() for k in inkeys ])
      if outkeys and function:
         raise Error('functions cannot have output keywords')
      self.outkeys = tuple([ k.upper() for k in outkeys ])

      # Store list of all keywords
      allkeys = list(self.inkeys)
      allkeys += [ k for k in self.outkeys if k not in self.inkeys ]
      self.allkeys = tuple(allkeys)

      # Store everything else
      self._pyname = pyname
      self.function = function
      self.callfunc = callfunc
      self.extracode = extracode
      self.readonly = readonly

      # Register the mapping
      _subroutines[uc_name] = self

   def pydef(self, pars=(), keys=()):
      """
      Creates the skeleton of the Python definition of the subroutine.

      pars is a sequence of strings, each of which is the Pythonized name of a
      parameter of the subroutine.  keys is a sequence of sequences, each of
      which contains two strings.  The strings are the Pythonized versions of
      the names from the left-hand and right-hand sides of the equals sign in
      the declaration of a keyword for the subroutine.

      Returns a tuple of two strings.  The first is the 'def' line for the
      function definition.  The second is the beginning of the function body
      (not indented with respect to the 'def'), which contains needed machinery
      for handling input and output for the function.
      """

      # Make copies of the parameter and keyword lists
      pars = tuple(pars)
      keys = tuple(keys)

      # Verify number of parameters
      if len(pars) != self.npars:
         raise Error("subroutine '%s' has %d parameters (defined with %d)" %
		     (self.name, self.npars, len(pars)))

      # Verify that all needed keywords were supplied
      keys_expected = list(self.allkeys)
      keys_expected.sort()
      keys_got = [ k[0].upper() for k in keys ]
      keys_got.sort()
      if keys_got != keys_expected:
         raise Error(("keywords for subroutine '%s' are %s " +
	              "(defined with %s)") %
		     (self.name, keys_expected, keys_got))

      # Number of required parameters
      nrequired = self.npars - self.noptional

      # Required input parameters
      in_required = [ pars[i] for i in range(nrequired) if i+1 in self.inpars ]

      # Optional input parameters (also includes optional output-only
      # parameters because the function needs to accept a boolean argument
      # indicating whether the optional output should be returned)
      in_optional = ([ pars[i] for i in range(nrequired, self.npars)
                       if (i+1 in self.inpars) or (i+1 in self.outpars) ])

      # Build the parameter list and function header
      params = ', '.join(in_required + [ p + '=None' for p in in_optional ] +
			 [ k[0] + '=None' for k in keys ])
      header = 'def %s(%s):' % (self.pyname(), params)

      # Add code to define n_params (which replaces IDL's N_PARAMS function)
      body = 'n_params = %d' % self.npars
      if in_optional:
	 body += ' - [%s].count(None)' % ', '.join(in_optional)

      # Required output parameters
      out = [ pars[i] for i in range(nrequired) if i+1 in self.outpars ]

      # Parameters that are output only
      out_only = ([ pars[i] for i in range(nrequired) if (i+1 in self.outpars)
                    and (i+1 not in self.inpars) ])

      # Output-only parameters need to be initialized in the function
      for par in out_only:
         body += '\n%s = None' % par

      # If the right-hand name for a keyword is different than it's left-hand
      # name, the right-hand name needs to be initialized with the left-hand
      # name's value, because the right-hand name is what's used in the
      # subroutine body
      for k in keys:
         if k[0] != k[1]:
            body += '\n%s = %s' % (k[1], k[0])

      # Optional output values (parameters and keywords)
      out_optional = ([ pars[i] for i in range(nrequired, self.npars)
                        if i+1 in self.outpars ])
      out_optional += [ k[1] for k in keys if k[0].upper() in self.outkeys ]

      # The function needs to store the initial values of optional output
      # parameters and keywords so that it can later decide whether to return
      # them (i.e. it will return them if the initial value is not None)
      if out_optional:
         body += '\n_opt = (%s' % ', '.join(out_optional)
         if len(out_optional) == 1:  body += ','   # Single-item tuple
	 body += ')'

      if not self.function:
	 #
	 # Since all output values must be explicitly returned by the Python
	 # function, we create a local function '_ret' that returns a tuple of
	 # all the function's return values.  IDL return statements in the
	 # subroutine become 'return _ret()' in Python.
	 #
	 # Since the Python version of an IDL function cannot have output
	 # parameters/keywords, this is necessary only for procedures.
	 #

         body += '\ndef _ret():'

         if (not out) and (not out_optional):
	    # No output values
            body += '  return None'
         elif out and (not out_optional):
	    # Output values but no optional ones
	    if len(out) == 1:
	       body += '  return %s' % out[0]
	    else:
	       body += '  return (%s)' % ', '.join(out)
         else:
	    # Output values, some or all of which are optional
	    retbody = '_optrv = zip(_opt, [%s])\n' % ', '.join(out_optional)
	    if out:
	       retbody += '_rv = [%s]\n_rv += ' % ', '.join(out)
	    else:
	       retbody += '_rv = '
	    retbody += '[_o[1] for _o in _optrv if _o[0] is not None]'
	    retbody += '\nreturn tuple(_rv)'
	    body += '\n' + util.pyindent(retbody)
         
      # Add a final newline
      body += '\n'

      # Add any needed extra code
      add_extra_code(self.extracode)

      # Return the definition code
      return (header, body)

   def pycall(self, pars=(), keys=()):
      """
      Returns a string containing the Python statement or expression code for a
      call to the subroutine.

      pars is a sequence of strings, each of which is the Pythonized value of a
      parameter argument to the subroutine.  keys is a sequence of sequences,
      each of which contains two strings.  The strings are the Pythonized
      name and value of a keyword argument to the subroutine.
      """

      # Make copies of the parameter and keyword lists
      pars = tuple(pars)
      keys = tuple(keys)

      # Verify number of parameters
      npars = len(pars)
      nrequired = self.npars - self.noptional
      if npars > self.npars:
         raise Error(("subroutine '%s' takes at most %d parameters " +
	              "(called with %d)") % (self.name, self.npars, npars))
      if npars < nrequired:
         raise Error(("subroutine '%s' requires at least %d " +
	              "parameters (called with %d)") %
		     (self.name, nrequired, npars))

      #
      # Handle the parameter arguments
      #

      # Required input parameters
      input = ([ pars[i] for i in range(min(nrequired, npars))
                 if i+1 in self.inpars ])

      # Optional input parameters
      if npars > nrequired:
         for i in range(nrequired, npars):
	    if i+1 in self.inpars:
	       # Real optional input parameter
	       input.append(pars[i])
	    elif i+1 in self.outpars:
	       # Flag to indicate that an optional output parameter should be
	       # returned
	       input.append('True')

      # Output parameters
      output = [ pars[i] for i in range(npars) if i+1 in self.outpars ]

      #
      # Handle the keyword arguments
      #

      for (name, value) in keys:
	 uc_name = name.upper()

	 # Try to find a match for the keyword.  This is complicated by the
	 # fact that, in IDL, keyword names can be abbreviated as long as they
	 # can still be uniquely identified.
         matches = [ k for k in self.allkeys if k.startswith(uc_name) ]
	 if len(matches) == 0:
	    # No matches; throw an error
	    raise Error("'%s' is not a valid keyword for subroutine '%s'" %
	                (name, self.name))
	 elif len(matches) == 1:
	    # Only one match; good
	    uc_name = matches[0]
	 elif uc_name not in matches:
	    # Multiple matches; unless one of the matches is exactly what we
	    # want (i.e. the keyword is a prefix of one or more others), throw
	    # an error
	    raise Error(("identifier '%s' matches multiple keywords " +
	                 "for subroutine '%s': %s") %
			(name, self.name, matches))

	 # Pythonize the full name
         name = util.pyname(uc_name)

	 if uc_name in self.inkeys:
	    # Input keyword
	    input.append('%s=%s' % (name, value))
	 if uc_name in self.outkeys:
	    # Output keyword
	    if uc_name not in self.inkeys:
	       # If the keyword is output only, we need to flag that the value
	       # should be returned
	       input.append('%s=True' % name)
	    output.append(value)

      # Add any needed extra code
      add_extra_code(self.extracode)

      # If there's a custom callfunc, use it to generate the call code
      if self.callfunc:
         return self.callfunc(input, output)

      # Build the input and output strings
      input  = ', '.join(input)
      if output:
         output = ', '.join(output) + ' = '
      else:
         output = ''

      # Return the call code
      return '%s%s(%s)' % (output, self.pyname(), input)


def map_pro(name, pyname=None, inpars=(), outpars=(), noptional=0,
            inkeys=(), outkeys=(), callfunc=None, extracode=None,
	    readonly=False):
   """
   Creates and returns a new SubroutineMapping for an IDL procedure, passing
   the given arguments to the constructor
   """
   return SubroutineMapping(name, pyname=pyname, function=False,
                            inpars=inpars, outpars=outpars, noptional=noptional,
                            inkeys=inkeys, outkeys=outkeys, callfunc=callfunc,
			    extracode=extracode, readonly=readonly)


def map_func(name, pyname=None, inpars=(), noptional=0, inkeys=(),
             callfunc=None, extracode=None, readonly=False):
   """
   Creates and returns a new SubroutineMapping for an IDL function, passing
   the given arguments to the constructor.  Note that unlike procedure
   mappings, function mappings cannot have output parameters/keywords.
   """
   return SubroutineMapping(name, pyname=pyname, function=True,
                            inpars=inpars, noptional=noptional, inkeys=inkeys,
			    callfunc=callfunc, extracode=extracode,
			    readonly=readonly)


def get_subroutine_map(name):
   """
   If a SubroutineMapping exists for the given subroutine name, returns it.
   Otherwise, returns None.
   """
   return _subroutines.get(name.upper())


#
# Read-only builtin mappings (these are needed by the subroutine-mapping
# mechanism itself)
#

map_func('N_PARAMS', callfunc=(lambda i,o: 'n_params'), readonly=True)
map_func('KEYWORD_SET', inpars=[1],
         callfunc=(lambda i,o: '(%s is not None)' % i[0]), readonly=True)


