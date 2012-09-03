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


from i2py_map import map_var, map_pro, map_func
import config
import error
import re
from numpy import array
from operator import isSequenceType

################################################################################
#
# Type maps
#
################################################################################

# Map from IDL typecodes to numpy/numarray type strings
typemap =  [
    None,               #  0 - UNDEFINED
    'uint8',            #  1 - BYTE (unsigned)
    config.inttype,     #  2 - INT
    'int32',            #  3 - LONG
    'float32',          #  4 - FLOAT
    'float64',          #  5 - DOUBLE
    'complex64',        #  6 - COMPLEX
    'string',           #  7 - STRING
    None,               #  8 - STRUCT
    'complex128',       #  9 - DCOMPLEX
    None,               # 10 - POINTER
    None,               # 11 - OBJREF
    config.uinttype,    # 12 - UINT
    'uint32',           # 13 - ULONG
    'int64',            # 14 - LONG64
    'uint64',           # 15 - ULONG64
]


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
map_pro('ON_IOERROR', inpars=[1],
        callfunc=(lambda i,o: '# ON_IOERROR, %s' % i[0]))
map_pro('CATCH', inpars=[1], inkeys=['CANCEL'],
        callfunc=lambda i,o: '# CATCH, %s' % i)
map_pro('PRINT', inpars=range(1,101), noptional=100, inkeys=['FORMAT'],
        callfunc=(lambda i,o: 'print ' + ', '.join(i)))


################################################################################
#
# Function maps
#
################################################################################

########################################################
# Things with different names in Python

map_func('ABS',    inpars=[1], pyname='absolute')
map_func('ACOS',   inpars=[1], pyname='arccos')
map_func('ASIN',   inpars=[1], pyname='arcsin')
map_func('ALOG',   inpars=[1], pyname='log')
map_func('ALOG10', inpars=[1], pyname='log10')

# ATAN with two arguments is a separate function in numpy
# ATAN with complex argument and /phase is also special
def map_atan(i, o):
    if len(i) == 1:
        return 'arctan(%s)' % (i[0])
    elif len(i) == 2:
        if re.match('PHASE', i[1]):
            return 'arctan2(%s.imag, %s.real)' % (i[0], i[0])
        else:
            return 'arctan2(%s, %s)' % (i[0], i[1])

map_func('ATAN',   inpars=[1,2], inkeys=['PHASE'], noptional=1, callfunc=map_atan)


# map_func('HAS_TAG', inpars=[1,2], pyname='hasattr')
# map_func('TAGEXIST', inpars=[1,2], pyname='hasattr')

########################################################
# Type conversion functions

map_func('STRING', pyname='str', inpars=range(1,101), noptional=100,
    inkeys=['AM_PM', 'DAYS_OF_WEEK', 'FORMAT', 'MONTHS', 'PRINT'])

def typeconv(typename):
   "Returns a type-conversion callfunc for type typename"
   return (lambda i,o: 'array(%s, copy=0).astype(%s)' % (i[0], typename))

# FIX is the trickiest type conversion function, as it can convert to arbitrary type
def fix(i, o):
    def _error_ret():
        return '#{ FIX(%s) [%s]}#' % (", ".join(i), ", ".join(o))

    typename = config.inttype
    for ii in range(len(i)):
        m = re.match(r'type=(\d+)', i[ii], re.I)
        if m:
            typename = typemap[int(m.groups()[0])]
            i.pop(ii)
            break
    if len(i) > 1:
        return _error_ret()
    if typename is None:
        return _error_ret()
    if typename is 'String':
        return '(%s).astype("int8").tostring()' % (i[0])
    return 'array(%s, copy=0).astype(%s)' % (i[0], typename)

def complex_conv(typename, i, o):
    for ii in range(len(i)):
        m = re.match(r'double=(\S+)', i[ii], re.I)
        if m:
            # import ipdb; ipdb.set_trace()
            try:
                res = eval(m.groups()[0], {})
            except:
                res = True  # unless it evaluates to 0 or false, it is True
            if res:
                typename = 'complex128'
            i.pop(ii)
            break
    if len(i) == 1:
        return 'array(%s, copy=0).astype(%s)' % (i[0], typename)
    if len(i) == 2:
        rt = { 'complex64' : 'float32', 'complex128' : 'float64' }
        return '(array(%s, copy=0).astype(%s) + 1j*array(%s, copy=0).astype(%s))' \
                % (i[0], rt[typename], i[1], rt[typename])
    # more than two arguments
    return '#{ COMPLEX/DCOMPLEX(%s) [%s]}#' % (", ".join(i), ", ".join(o))
    # error.conversion_error("COMPLEX/DCOMPLEX with OFFSET not supported", 0)

map_func('FIX', inpars=range(1,11), noptional=9, inkeys=['TYPE', 'PRINT'],
        callfunc=fix)
        # callfunc=(lambda i, o: 'fix(' + ', '.join(i) + ')'))

# These conversion functions, if given extra parameters, perform bytewise
# unpacking of data, analogously to Pythons struct.pack/unpack
# This functionality is NOT implemented yet
map_func('BYTE', inpars=[1], callfunc=typeconv('uint8'))
map_func('UINT', inpars=[1], callfunc=typeconv(config.uinttype))
map_func('LONG', inpars=[1], callfunc=typeconv('int32'))
map_func('ULONG', inpars=[1], callfunc=typeconv('uint32'))
map_func('LONG64', inpars=[1], callfunc=typeconv('int64'))
map_func('ULONG64', inpars=[1], callfunc=typeconv('uint64'))
map_func('FLOAT', inpars=[1], callfunc=typeconv('float32'))
map_func('DOUBLE', inpars=[1], callfunc=typeconv('float64'))
# map_func('DOUBLE', inpars=[1], callfunc=typeconv('float64'))

# Complex conversion can take either
# 1) a real number/array
# 2) real and imaginary parts
# 3) an expression with offset and dimensions (1 to 8)
#  (all of which can also have the DOUBLE keyword for the COMPLEX function)
map_func('COMPLEX', inpars=range(1,11), noptional=10, inkeys=['DOUBLE'],
            callfunc=lambda i, o: complex_conv('complex64', i, o))
map_func('DCOMPLEX', inpars=range(1,10), noptional=9, 
            callfunc=lambda i, o: complex_conv('complex128', i, o))

########################################################
# Various array generation functions, *ARR, *INDGEN 

def arrgen(typename):
   "Returns an array-generation callfunc for type typename"
   return (lambda i,o: 'zeros([%s], "%s")' %
           (', '.join([ i[n] for n in xrange(len(i)-1, -1, -1) ]), typename))

# advanced uses of make_array will have to be converted manually
def make_array(i, o):
    keymap = { 'byte' :         'uint8',
               'complex' :      'complex64',
               'dcomplex' :     'complex128',
               'double' :       'float64',
               'float' :        'float32',
               'l64' :          'int64',
               'integer' :      config.inttype,
               'long' :         'int32',
               'uint' :         config.uinttype,
               'ul64' :         'uint64',
               'ulong' :        'uint32',
    }
    func = 'zeros'
    value = 0
    dim = None

    shape = []
    dtype = 'float'
    def _fallback():
        return '#{ MAKE_ARRAY(%s) }#' % ", ".join(i + o)
    for ii in range(len(i)):
        parts = i[ii].split('=')
        if len(parts) == 1:
            shape.insert(0, i[ii])
            continue
        key = parts[0].lower()
        if key in keymap:
            dtype = keymap[key]
            continue
        if key == 'size':
            return _fallback()
        if key == 'type':
            try:
                dtype = typemap[int(parts[1])]
                if not dtype: raise
            except:
                return _fallback()
            continue
        if key == 'dimension':
            dim = 'array(%s, copy=0)[::-1]' % pycode(parts[1])
            continue
        if key == 'value':
            value = parts[1]
            continue
        if key == 'nozero':
            continue    # ignore
        return _fallback()

    if dim is None:
        dim = ", ".join(shape[::-1])
    if value == 0:
        return 'zeros(%s, dtype="%s")' % (dim, dtype)
    if value == 1:
        return 'ones(%s, dtype="%s")' % (dim, dtype)
    return '((%s)*ones(%s, dtype="%s"))' % (value, dim, dtype)

map_func('MAKE_ARRAY', inpars=range(1,10), noptional=9, 
    inkeys=[ 'BYTE', 'COMPLEX', 'DCOMPLEX', 'DOUBLE', 'FLOAT', 'L64',
            'INTEGER', 'LONG', 'UINT', 'UL64', 'ULONG',
            'TYPE', 'SIZE', 'DIMENSION', 'INDEX', 'VALUE', 'OBJ', 'PTR'], callfunc=make_array)

map_func('BYTARR', inpars=range(1,9), noptional=7, callfunc=arrgen('uint8'))
map_func('INTARR', inpars=range(1,9), noptional=7, callfunc=arrgen('int16'))
map_func('UINTARR', inpars=range(1,9), noptional=7, callfunc=arrgen('uint16'))
map_func('LONARR', inpars=range(1,9), noptional=7, callfunc=arrgen('int32'))
map_func('ULONARR', inpars=range(1,9), noptional=7, callfunc=arrgen('uint32'))
map_func('LON64ARR', inpars=range(1,9), noptional=7, callfunc=arrgen('int64'))
map_func('ULON64ARR', inpars=range(1,9), noptional=7, callfunc=arrgen('uint64'))

map_func('FLTARR', inpars=range(1,9), noptional=7, callfunc=arrgen('float32'))
map_func('DBLARR', inpars=range(1,9), noptional=7, callfunc=arrgen('float64'))
map_func('COMPLEXARR', inpars=range(1,9), noptional=7, callfunc=arrgen('complex64'))
map_func('DCOMPLEXARR', inpars=range(1,9), noptional=7, callfunc=arrgen('complex128'))

def indgen_shape(typename, shape):
    shape = array(shape, copy=0).ravel()
    N = reduce(lambda a,b:a*b, shape)
    return 'arange(%d, dtype=%s).reshape(%s)' % (N, typename, ", ".join(map(str, (x for x in shape))))

def indgen_worker(typename, i, o):
    if len(i) == 1:
        try:
            #import ipdb; ipdb.set_trace()
            shape = eval(i[0])
            if isSequenceType(shape):
                return indgen_shape(typename, shape)
        except:
            pass
        # the argument is unknown or scalar, so just use it as-is
        return 'arange(%s, dtype=%s)' % (i[0], typename)
    else:
        shape = map(lambda x: int(eval(x,{})), i)
        return indgen_shape(typename, shape)


def indgen_dispatch(i, o):

    def _error_ret():
        return '#{ INDGEN(%s) [%s]}#' % (", ".join(i), ", ".join(o))

    typename = config.inttype

    kws = filter(lambda x: x.find('=') != -1, i)
    if len(kws) == 0:
        return indgen_worker(typename, i, o)

    if len(kws) > 1: 
        # error.conversion_error("multiple keywords to INDGEN", 0)
        return _error_ret()

    types = {
        'BYTE' : 'uint8', 
        'COMPLEX':      'complex64',
        'DCOMPLEX':	'complex128',
        'DOUBLE':	'float64',
        'FLOAT':	'float32',
        'L64':		'int64',
        'LONG':		'int32',
        'STRING':	None,
        'UINT':		config.uinttype,
        'UL64':		'uint64',
        'ULONG':        'uint32',
    }

    for ii in range(len(i)):
        m = re.match('(\w+)=(\w+)', i[ii])
        if m:
            key, val = m.groups()
            key = key.upper()
            if key == 'TYPE':
                return indgen_worker(typemap[int(val)], i, o)
            if key == 'STRING':
                # error.conversion_error("INDGEN with /STRING not supported", 0)
                return _error_ret()
            if key not in types:
                error.conversion_error("unknown keyword to INDGEN", 0)
            try:
                res = eval(val, {})
            except:
                res = True
            if res:
                typename = types[key]
            i.pop(ii)
            break

    return indgen_worker(typename, i, o)

map_func('INDGEN', inpars=range(1,9), noptional=8,
    inkeys=['BYTE', 'COMPLEX', 'DCOMPLEX', 'DOUBLE', 'FLOAT', 'L64', 'LONG',
            'STRING', 'UINT', 'UL64', 'ULONG', 'TYPE'],
    callfunc=indgen_dispatch)

map_func('BINDGEN', inpars=range(1,8), noptional=7, callfunc=lambda i,o: indgen_worker('uint8', i, o))
map_func('UINDGEN', inpars=range(1,8), noptional=7,
            callfunc=lambda i,o: indgen_worker(config.uinttype, i, o))
map_func('LINDGEN', inpars=range(1,8), noptional=7,
            callfunc=lambda i,o: indgen_worker('int32', i, o))
map_func('ULINDGEN', inpars=range(1,8), noptional=7,
            callfunc=lambda i,o: indgen_worker('uint32', i, o))
map_func('L64INDGEN', inpars=range(1,8), noptional=7,
            callfunc=lambda i,o: indgen_worker('int64', i, o))
map_func('UL64INDGEN', inpars=range(1,8), noptional=7,
            callfunc=lambda i,o: indgen_worker('uint64', i, o))

map_func('FINDGEN', inpars=range(1,8), noptional=7,
            callfunc=lambda i,o: indgen_worker('float32', i, o))
map_func('DINDGEN', inpars=range(1,8), noptional=7,
            callfunc=lambda i,o: indgen_worker('float64', i, o))
map_func('CINDGEN', inpars=range(1,8), noptional=7,
            callfunc=lambda i,o: indgen_worker('complex64', i, o))
map_func('DCINDGEN', inpars=range(1,8), noptional=7,
            callfunc=lambda i,o: indgen_worker('complex128', i, o))

map_func('N_ELEMENTS', inpars=[1],
         callfunc=(lambda i,o: '%s.size' % i[0]))
map_func('REPLICATE', inpars=range(1,10), noptional=7,
         callfunc=(lambda i,o: '(%s)*ones([%s])' % (i[0],
	           ', '.join([ i[n] for n in xrange(len(i)-1, 0, -1) ]))))
map_func('WHERE', inpars=[1,2], noptional=1,
         callfunc=(lambda i,o: 'where(ravel(%s))[0]' % i[0]))
map_func('ARG_PRESENT', inpars=[1],
        callfunc=lambda i, o: '(%s is not None)' % (i[0]))

########################################################
# Object lifecycle methods

def ptr_new(i, o):
    if len(i) == 0: return 'None'               # ptr_new() is a placeholder.  None will do

    # Every named variable in Python is a pointer, in some sense.  Just copy it
    return str(i[0])

map_func('PTR_NEW', inpars=[1,2], inkeys=['ALLOCATE_HEAP', 'NO_COPY'], noptional=2, callfunc=ptr_new)

def obj_new(i, o):
    if len(i) == 0: return 'None'               # obj_new() is a placeholder.  None will do
    m = re.match(r'([\'"])(\w+)\1', i[0])
    if m:
        return '%s(%s)' % (m.groups()[1], ", ".join(i[1:]))
    return '#{ OBJ_NEW(%s) [%s] }#' % (", ".join(i), ", ".join(o))

map_func('OBJ_NEW', inpars=range(1,101), noptional=100, callfunc=obj_new)

map_func('OBJ_DESTROY', inpars=range(1,101), noptional=100,
        callfunc=lambda i,o: '%s = None' % (i[0]))



########################################################
# Things that just look different in Python


def randomfunc(fname):
    def rfunc(i, o):
        if len(i) == 1:
            return 'random.%s(0,1)' % fname
        return 'random.%s(0, 1, (%s))' % (fname, ', '.join(i[1:]))
    return rfunc

map_func('RANDOMN', inpars=range(1,9), noptional=8, callfunc=randomfunc('normal'))
map_func('RANDOMU', inpars=range(1,9), noptional=8, callfunc=randomfunc('uniform'))

# POINT_LUN with positive first arg is f.seek(), 
# with negative first arg it is f.tell().
def point_lun(i, o):
    if i[0][0] == '-':
        return '%s = %s.tell()' % (i[1], i[0][1:])
    else:
        return '%s.seek(%s)' % (i[0], i[1])
map_func('POINT_LUN', inpars=[1,2], callfunc=point_lun)

def minmax(i, o, fname):
    # print "i : <", i, ">"
    if len(i) == 1:
        return 'array(%s, copy=0).%s()' % (i[0], fname)

    return '#{ %s = array(%s, copy=0).arg%s() array(%s, copy=0)[%s] }#' % \
        (o[0], i[0], fname, i[0], o[0])
    

map_func('MIN', inpars=[1], outpars=[2], inkeys=['ABSOLUTE', 'DIMENSION', 'NAN'],
            outkeys=['MAX', 'SUBSCRIPT_MAX'], noptional=1,
         callfunc=lambda i, o: minmax(i, o, 'min'))

map_func('MAX', inpars=[1], outpars=[2], inkeys=['ABSOLUTE', 'DIMENSION', 'NAN'],
            outkeys=['MIN', 'SUBSCRIPT_MIN'], noptional=1,
         callfunc=lambda i, o: minmax(i, o, 'max'))

