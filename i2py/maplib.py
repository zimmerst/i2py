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
Defines mappings for some builtin IDL variables, procedures, and functions
"""


from map import map_var, map_pro, map_func


################################################################################
#
# Variable maps
#
################################################################################


# pi is in Numeric/numarray
map_var('!DPI', 'pi')
map_var('!RADEG', '_radeg', '_radeg = 180.0 / pi')


################################################################################
#
# Procedure maps
#
################################################################################


map_pro('ON_ERROR', inpars=[1],
        callfunc=(lambda i,o: '# ON_ERROR, %s' % i[0]))
map_pro('PRINT', inpars=range(1,101), noptional=99, inkeys=['FORMAT'],
        callfunc=(lambda i,o: 'print ' + ', '.join(i)))


################################################################################
#
# Function maps
#
################################################################################


def arrgen(typename):
   "Returns an array-generation callfunc for type typename"
   return (lambda i,o: 'zeros([%s], %s)' %
           (', '.join([ i[n] for n in xrange(len(i)-1, -1, -1) ]), typename))

def typeconv(typename):
   "Returns a type-conversion callfunc for type typename"
   return (lambda i,o: 'array(%s, copy=0).astype(%s)' % (i[0], typename))

map_func('DOUBLE', inpars=[1], callfunc=typeconv('Float64'))
map_func('FIX', inpars=[1], callfunc=typeconv('Int32'))
map_func('FLOAT', inpars=[1], callfunc=typeconv('Float32'))
map_func('FLTARR', inpars=range(1,9), noptional=7, callfunc=arrgen('Float32'))
map_func('LONG', inpars=[1], callfunc=typeconv('Int32'))
map_func('MIN', inpars=[1],
         callfunc=(lambda i,o: 'array(%s, copy=0).min()' % i[0]))
map_func('N_ELEMENTS', inpars=[1],
         callfunc=(lambda i,o: 'array(%s, copy=0).nelements()' % i[0]))
map_func('REPLICATE', inpars=range(1,10), noptional=7,
         callfunc=(lambda i,o: '(%s)*ones([%s])' % (i[0],
	           ', '.join([ i[n] for n in xrange(len(i)-1, 0, -1) ]))))
map_func('WHERE', inpars=[1,2], noptional=1,
         callfunc=(lambda i,o: 'where(ravel(%s))[0]' % i[0]))

