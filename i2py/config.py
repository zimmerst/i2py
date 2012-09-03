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
Package-wide configuration data
"""


import string


arraymodule	= 'numpy'	# Name of array module
idltab		= '    '	# Tab for IDL code
pytab		= '    '	# Tab for Python code
sysvarprefix	= '_sys_'	# Replacement for '!' in system variable names
idlnameconv	= string.upper	# Conversion function for IDL identifiers
pynameconv	= string.strip	# Conversion function for Python identifiers
baseclassname   = 'I2PY_Struct'

inttype  = 'int32'		# Change to Int16 if you want IDL's default short ints
uinttype = 'uint32'		# Change to Uint16 if you want IDL's default short ints

