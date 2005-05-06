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
This code handles the mapping of IDL functions to Python ones.  It's a nasty
mess that needs to be cleaned up!
"""

procedures = {}
functions = {}

extra_code = []


class Error(Exception):
   pass


class SubroutineMapping(object):
   def __init__(self, name, pyname=None, function=False,
                inpars=(), outpars=(), noptional=0, inkeys=(), outkeys=(),
		callfunc=None, extracode=None):

      self.name = name.upper()

      self.inpars = tuple(inpars)
      if outpars and function:
         raise Error('functions cannot have output parameters')
      self.outpars = tuple(outpars)

      pars = list(self.inpars)
      pars += [ p for p in self.outpars if p not in self.inpars ]
      pars.sort()
      self.npars = len(pars)
      if pars != range(1, self.npars+1):
         raise Error('incomplete or invalid parameter list: %s' % pars)

      noptional = int(noptional)
      if noptional < 0:  noptional = 0
      self.noptional = noptional

      self.inkeys = tuple([ k.lower() for k in inkeys ])
      if outkeys and function:
         raise Error('functions cannot have output keywords')
      self.outkeys = tuple([ k.lower() for k in outkeys ])

      allkeys = list(self.inkeys)
      allkeys += [ k for k in self.outkeys if k not in self.inkeys ]
      self.allkeys = tuple(allkeys)

      if pyname:
         self.pyname = pyname
      else:
         self.pyname = name.lower()

      self.function = function
      self.extracode = extracode
      self.callfunc = callfunc

   def pydef(self, pars=(), keys=()):
      pars = tuple([ p.lower() for p in pars ])
      keys = tuple([ (lname.lower(), rname.lower()) for
                     (lname, rname) in keys ])

      if len(pars) != self.npars:
         raise Error("subroutine '%s' has %d parameters (defined with %d)" %
		     (self.name, self.npars, len(pars)))

      keys_expected = list(self.allkeys)
      keys_expected.sort()
      keys_got = [ k[0] for k in keys ]
      keys_got.sort()
      if keys_got != keys_expected:
         raise Error(("keywords for subroutine '%s' are %s " +
	              "(defined with keywords %s)") %
		     (self.name, keys_expected, keys_got))

      fdef = 'def %s(' % self.pyname

      nrequired = self.npars - self.noptional
      in_required = [ pars[i] for i in range(nrequired) if i+1 in self.inpars ]
      in_optional = ([ pars[i] for i in range(nrequired, self.npars)
                       if i+1 in self.inpars ])
      out_keys = [ k for k in keys if k[0].upper() in self.outkeys ]

      fdef += ', '.join(in_required + [ p + '=None' for p in in_optional ] +
                        [ k[0] + '=None' for k in keys ])

      fdef += '):\n   n_params = %d' % self.npars
      if in_optional:
	 fdef += ' - [%s].count(None)' % ', '.join(in_optional)
      fdef += '\n'

      if out_keys:
         fdef += '   _outkeys = (%s' % ', '.join([ k[0] for k in out_keys ])
         if len(out_keys) == 1:  fdef += ','
	 fdef += ')\n'

      out = [ pars[i] for i in range(self.npars) if i+1 in self.outpars ]
      out_only = ([ pars[i] for i in range(self.npars) if (i+1 in self.outpars)
                    and (i+1 not in self.inpars) ])
      for par in out_only:
         fdef += '   %s = None\n' % par

      for k in keys:
         if k[0] != k[1]:
            fdef += '   %s = %s\n' % (k[1], k[0])

      # If this is a function defintion, we don't need to create a _ret()
      if self.function:  return fdef

      fdef += '   def _ret():'
      if (not out) and (not out_keys):
         fdef += '  return None'
      elif out and (not out_keys):
	 if len(out) == 1:
	    fdef += '  return %s' % out[0]
	 else:
	    fdef += '  return (%s)' % ', '.join(out)
      else:
	 if out:
	    fdef += '\n      retvals = [%s]\n      retvals += ' % ', '.join(out)
	 else:
	    fdef += '\n      retvals = '
	 fdef += ('[k[1] for k in zip(_outkeys, [%s]) if k[0] is not None]\n' %
	          ', '.join([ k[1] for k in out_keys ]))
	 fdef += '      return tuple(retvals)'
         
      fdef += '\n'

      if self.extracode:
         if self.extracode not in extra_code:
	    extra_code.append(self.extracode)

      return fdef

   def pycall(self, pars=(), keys=()):
      pars = tuple(pars)
      keys = tuple(keys)

      npars = len(pars)
      nrequired = self.npars - self.noptional
      if npars > self.npars:
         raise Error(("subroutine '%s' takes at most %d parameters " +
	              "(called with %d)") % (self.name, self.npars, npars))
      if npars < nrequired:
         raise Error(("subroutine '%s' requires at least %d " +
	              "parameters (called with %d)") %
		     (self.name, nrequired, npars))

      input  = [ pars[i] for i in range(npars) if i+1 in self.inpars ]
      output = [ pars[i] for i in range(npars) if i+1 in self.outpars ]

      keydict = {}

      for (name, value) in keys:
	 name = name.lower()
         matches = [ k for k in self.allkeys if k.startswith(name) ]
	 if len(matches) == 0:
	    raise Error("'%s' is not a valid keyword for subroutine '%s'" %
	                (name, self.name))
	 if len(matches) > 1:
	    raise Error(("identifier '%s' matches multiple keywords " +
	                 "for subroutine '%s': %s") %
			(name, self.name, matches))
         name = matches[0]
	 keydict[name] = value
	 if name in self.inkeys:
	    input.append('%s=%s' % (name, value))

      for name in self.outkeys:
         if name in keydict:
	    if name not in self.inkeys:
	       input.append('%s=True' % name)
	    output.append(keydict[name])

      if self.extracode:
         if self.extracode not in extra_code:
	    extra_code.append(self.extracode)

      if self.callfunc:
         return self.callfunc(input, output)

      input  = ', '.join(input)
      if output:
         output = ', '.join(output) + ' = '
      else:
         output = ''

      return '%s%s(%s)' % (output, self.pyname, input)


def add_proc(name, pyname=None, inpars=(), outpars=(), noptional=0,
             inkeys=(), outkeys=(), callfunc=None, extracode=None):
   map = SubroutineMapping(name, pyname=pyname, function=False,
                           inpars=inpars, outpars=outpars, noptional=noptional,
                           inkeys=inkeys, outkeys=outkeys, callfunc=callfunc,
			   extracode=extracode)
   procedures[map.name] = map


def add_func(name, pyname=None, pars=(), noptional=0, keys=(), callfunc=None,
             extracode=None):
   map = SubroutineMapping(name, pyname=pyname, function=True, inpars=pars,
                           noptional=noptional, inkeys=keys, callfunc=callfunc,
			   extracode=extracode)
   functions[map.name] = map

