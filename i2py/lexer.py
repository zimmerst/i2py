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
This file defines the tokens in the grammar and handles any preprocessing they
need before being passed to the parser.  It also generates the lexer with lex
(from PLY).
"""

import re
import lex
import ir
import fmap
import error

tokens = {
  't_STRING'		: r"""('[^'\n]*')|("[^"\n]*")""",

  't_MINUSMINUS'	: r'--',
  't_PIPEPIPE'		: r'\|\|',
  't_PLUSPLUS'		: r'\+\+',
  't_POUNDPOUND'	: r'\#\#',

  't_CARET'		: r'\^',
  't_COLON'		: r':',
  't_COMMA'		: r',',
  't_DIVIDE'		: r'/',
  't_DOT'		: r'\.',
  't_EQUALS'		: r'=',
  't_GREATERTHAN'	: r'>',
  't_LBRACE'		: r'\{',
  't_LESSTHAN'		: r'<',
  't_LPAREN'		: r'\(',
  't_LPAREN'		: r'\(',
  't_LBRACKET'		: r'\[',
  't_MINUS'		: r'-',
  't_PLUS'		: r'\+',
  't_POUND'		: r'\#',
  't_QUESTIONMARK'	: r'\?',
  't_RBRACE'		: r'\}',
  't_RPAREN'		: r'\)',
  't_RBRACKET'		: r'\]',
  't_TILDE'		: r'~',
  't_TIMES'		: r'\*',
}

globals().update(tokens)
tokens = tuple([ t[2:] for t in tokens.keys() ])

tokens += (
  'AMPAMP', 'EXTRA', 'FUNCTION_ID', 'IDENTIFIER', 'NEWLINE', 'NUMBER',
  'OP_EQUALS', 'PRO_ID', 'SYS_VAR',
)

keywords = (
  'AND', 'BEGIN', 'BREAK', 'CASE', 'COMMON', 'COMPILE_OPT', 'CONTINUE', 'DO',
  'ELSE', 'END', 'ENDCASE', 'ENDELSE', 'ENDFOR', 'ENDIF', 'ENDREP', 'ENDSWITCH',
  'ENDWHILE', 'EQ', 'FOR', 'FORWARD_FUNCTION', 'FUNCTION', 'GE', 'GOTO', 'GT',
  'IF', 'INHERITS', 'LE', 'LT', 'MOD', 'NE', 'NOT', 'OF', 'ON_IOERROR', 'OR',
  'PRO', 'REPEAT', 'RETURN', 'SWITCH', 'THEN', 'UNTIL', 'WHILE', 'XOR',
)

tokens += keywords

def t_NUMBER(t):
   r"""
     (?P<float>
       (?P<dec> (\d+\.\d+) | (\d+\.) | (\.\d+) | ( \d+ (?=[eEdD]) ) )
       (?P<exp>
         (?P<expchar> [eEdD] )
         (?P<expval>  [+-]?\d+ )?
       )?
     ) |
     (?P<integer>
       (?P<val>  (\d+) | ('[a-fA-F\d]+'[xX]) | ('[0-7]+'[oO]) | ("[0-7]+) )
       (?P<type> [bB] | ( [uU]? ( [sS] | [lL][lL]? )? ) )?
     )
   """
   t.value = ir.Number(number_re.match(t.value.upper()).groupdict())
   return t

number_re = re.compile(t_NUMBER.__doc__, re.VERBOSE)
t_NUMBER.__doc__ = re.sub(r'\?P<\w+>', '', t_NUMBER.__doc__)  # Strip group tags

def t_OP_EQUALS(t):
   r'''
     ([aA][nN][dD]=)	|
     ([mM][oO][dD]=)	|
     ([xX][oO][rR]=)	|
     ([eE][qQ]=)	|
     ([gG][eE]=)	|
     ([gG][tT]=)	|
     ([lL][eE]=)	|
     ([lL][tT]=)	|
     ([nN][eE]=)	|
     ([oO][rR]=)	|
     (\#\#=)		|
     (\+=)		|
     (-=)		|
     (\*=)		|
     (/=)		|
     (\^=)		|
     (\#=)		|
     (<=)		|
     (>=)
   '''
   t.value = t.value.upper()
   return t

def t_EXTRA(t):
   r'(_[rR][eE][fF])?_[eE][xX][tT][rR][aA]'
   t.value = t.value.upper()
   return t

def t_IDENTIFIER(t):
   r'!?[a-zA-Z][\w$]*'

   if t.value.upper() in keywords:
      t.value = t.value.upper()
      t.type = t.value
   else:
      t.value = ir.Name(t.value)
      value = str(t.value)
      if value[0] == "!":
         t.type = 'SYS_VAR'
      elif value in fmap.procedures:
         t.type = 'PRO_ID'
      elif value in fmap.functions:
         t.type = 'FUNCTION_ID'

   return t

def t_continuation(t):
   r'\$\n'
   t.lineno += 1

# Need this to avoid treating '&&' as NEWLINE
def t_AMPAMP(t):
   r'&&'
   return t

def t_NEWLINE(t):
   r'((((;.*)? \n) | &) [ \t]*)+'
   t.lineno += t.value.count('\n')
   t.value = '\n'
   return t

def t_error(t):
   error.syntax_error('illegal character: %s' % repr(t.value[0]), t.lineno)
   t.skip(1)

t_ignore = ' \t'

lex.lex()

if __name__ == '__main__':
   lex.runmain()

