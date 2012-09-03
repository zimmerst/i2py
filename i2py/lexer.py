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
Defines the tokens in the IDL grammar, handling any preprocessing they
need before being passed to the parser, and generates the lexer.
"""


import re
import lex
import ir
import error


################################################################################
#
# Define string tokens
#
################################################################################


tokens = {
  # 't_STRING'		: r"""('[^'\n]*')|("[^"\n]*")""",

  't_MINUSMINUS'	: r'--',
  't_ARROW'	        : r'->',
  't_DCOLON'	        : r'::',
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

keywords = (
  'AND', 'BEGIN', 'BREAK', 'CASE', 'COMMON', 'COMPILE_OPT', 'CONTINUE', 'DO',
  'ELSE', 'END', 'ENDCASE', 'ENDELSE', 'ENDFOR', 'ENDFOREACH', 'ENDIF', 'ENDREP', 'ENDSWITCH',
  'ENDWHILE', 'EQ', 'FOR', 'FOREACH', 'FORWARD_FUNCTION', 'FUNCTION', 'GE', 'GOTO', 'GT',
  'IF', 'INHERITS', 'LE', 'LT', 'MOD', 'NE', 'NOT', 'OF', 'OR',
  'PRO', 'REPEAT', 'RETURN', 'SWITCH', 'THEN', 'UNTIL', 'WHILE', 'XOR',
)

tokens += keywords


################################################################################
#
# Define function tokens
#
################################################################################


tokens += (
  'AMPAMP', 'EXTRA', 'IDENTIFIER', 'NEWLINE', 'NUMBER', 'OP_EQUALS', 'STRING', 'SYS_VAR',
)

def t_STRING(t):
   r"""
      (?: ('[^'\n]*(?:''[^'\n]*)*') |
          ("[^"\n]*(?:""[^"\n]*)*") ) (?![xob])
   """

   # IDL literal strings uses doubled quotation marks to escape quotes inside strings,
   # e.g. 'foo''bar' => "foo'bar"
   g = string_re.match(t.value).groups()
   if g[0]:
      if len(g[0]) > 2:
          t.value = g[0].replace("''", "\\'")
   else:
      if len(g[1]) > 2:
          t.value = g[1].replace('""', '\\"')
   return t

string_re = re.compile(t_STRING.__doc__, re.VERBOSE|re.IGNORECASE)

def t_NUMBER(t):
   r"""
     (?P<float>
       (?P<dec> (\d+\.\d+) | (\d+\.) | (\.\d+) | ( \d+ (?=[ed]) ) )
       (?P<exp>
         (?P<expchar> [ed] )
         (?P<expval>  [+-]?\d+ )?
       )?
     ) |
     (?P<integer>
       (?P<val>  (\d+) | ('[a-f\d]+'x) | ('[0-7]+'o) | ("[0-7]+) | '[01]+'b )
       (?P<type> b | ( u? ( s | LL? )? ) )?
     )
   """
   t.value = ir.Number(number_re.match(t.value.upper()).groupdict())
   return t

# Leaving group tags in the RE for t_NUMBER will confuse the lexer, so we
# compile and store the RE and then strip the tags from the doc string
number_re = re.compile(t_NUMBER.__doc__, re.VERBOSE|re.IGNORECASE)
t_NUMBER.__doc__ = re.sub(r'\?P<\w+>', '', t_NUMBER.__doc__)


def t_OP_EQUALS(t):
   r'''
     (and=)		|
     (mod=)		|
     (xor=)		|
     (eq=)		|
     (ge=)		|
     (gt=)		|
     (le=)		|
     (lt=)		|
     (ne=)		|
     (or=)		|
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
   r'(_ref)?_extra'
   t.value = t.value.upper()
   return t


# Handles identifiers, system variables, and keywords
def t_IDENTIFIER(t):
   r'!?[a-z][\w$]*'
   #r'!?[a-z][\w$]*((::|->|\.)[a-z][\w$]*)*'
   #r'(!|[a-z][\w$]*(::|->|\.))?[a-z][\w$]*'

   if t.value.upper() in keywords:
      t.value = t.value.upper()
      t.type = t.value
   else:
      t.value = ir.Name(t.value)
      value = str(t.value)
      if value[0] == "!":
         t.type = 'SYS_VAR'
   return t

def t_continuation(t):
   r'\$([ \t]*(;.*)?\n)+'
   t.lineno += t.value.count('\n')


# Need this to avoid treating '&&' as NEWLINE
def t_AMPAMP(t):
   r'&&'
   return t


def t_NEWLINE(t):
   r'([ \t]* (((;.*)? \n) | &) [ \t]*)+'
   t.lineno += t.value.count('\n')
   t.value = ir.Newline(t.value)
   return t


# Need to define this as a function (rather than using t_ignore) so that we can
# catch leading whitespace in NEWLINE tokens
def t_whitespace(t):
   r'[ \t]+'
   pass


def t_error(t):
   error.syntax_error('illegal character: %s\n  next: %s' \
        % (repr(t.value[0]), repr(t.value[0:50])), t.lineno)
   t.skip(1)


################################################################################
#
# Create the lexer
#
################################################################################


lexer = lex.lex(reflags=re.IGNORECASE)


