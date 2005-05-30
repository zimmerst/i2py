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
Defines the IDL grammar (productions and precedence rules) and generates the
parser.  Also completes the ir module by adding some information that's
automatically extracted from the grammar.
"""


import os.path
import error
from lexer import lexer, tokens
import yacc
import ir
import map
try:
   set
except NameError:
   from sets import Set as set  # Python 2.3


################################################################################
#
# Grammar specification
#
################################################################################


precedence = (
   ('nonassoc', 'LOWER_THAN_ELSE', 'LOWER_THAN_KEYWORD'),
   ('nonassoc', 'ELSE', 'KEYWORD'),
)


productions = '''
translation_unit
	: program
	| NEWLINE program
	| statement_list
	| NEWLINE statement_list

program
	: subroutine_definition
	| program subroutine_definition

subroutine_definition
	: PRO subroutine_body
	| FUNCTION subroutine_body

subroutine_body
	: IDENTIFIER NEWLINE statement_list END NEWLINE
	| IDENTIFIER COMMA parameter_list NEWLINE statement_list END NEWLINE

parameter_list
	: parameter
	| parameter_list COMMA parameter

parameter
	: IDENTIFIER
	| IDENTIFIER EQUALS IDENTIFIER
	| EXTRA EQUALS IDENTIFIER
	| EXTRA EQUALS EXTRA

statement_list
	: statement NEWLINE
	| statement_list statement NEWLINE

statement
	: compound_statement
	| simple_statement

compound_statement
	: labeled_statement
	| if_statement
	| selection_statement
	| for_statement
	| while_statement
	| repeat_statement

labeled_statement
	: IDENTIFIER COLON statement
	| IDENTIFIER COLON NEWLINE statement

if_statement 
	: IF expression THEN if_clause			%prec LOWER_THAN_ELSE
	| IF expression THEN if_clause ELSE else_clause %prec ELSE

if_clause
	: statement
	| BEGIN NEWLINE statement_list ENDIF
	| BEGIN NEWLINE statement_list END

else_clause
	: statement
	| BEGIN NEWLINE statement_list ENDELSE
	| BEGIN NEWLINE statement_list END

selection_statement
	: CASE selection_statement_body ENDCASE
	| CASE selection_statement_body END
	| SWITCH selection_statement_body ENDSWITCH
	| SWITCH selection_statement_body END

selection_statement_body
	: expression OF NEWLINE selection_clause_list
	| expression OF NEWLINE selection_clause_list ELSE selection_clause

selection_clause_list
	: expression selection_clause
	| selection_clause_list expression selection_clause

selection_clause
	: COLON NEWLINE
	| COLON statement NEWLINE
	| COLON BEGIN NEWLINE statement_list END NEWLINE

for_statement
	: FOR for_index DO statement
	| FOR for_index DO BEGIN NEWLINE statement_list ENDFOR
	| FOR for_index DO BEGIN NEWLINE statement_list END

for_index
	: IDENTIFIER EQUALS expression COMMA expression
	| IDENTIFIER EQUALS expression COMMA expression COMMA expression

while_statement
	: WHILE expression DO statement
	| WHILE expression DO BEGIN NEWLINE statement_list ENDWHILE
	| WHILE expression DO BEGIN NEWLINE statement_list END

repeat_statement
	: REPEAT statement UNTIL expression
	| REPEAT BEGIN NEWLINE statement_list ENDREP UNTIL expression
	| REPEAT BEGIN NEWLINE statement_list END UNTIL expression

simple_statement
	: COMMON identifier_list
	| COMPILE_OPT identifier_list
	| FORWARD_FUNCTION identifier_list
	| ON_IOERROR COMMA IDENTIFIER
	| jump_statement
	| procedure_call
	| assignment_statement
	| increment_statement

identifier_list
	: IDENTIFIER
	| identifier_list COMMA IDENTIFIER

jump_statement
	: RETURN
	| RETURN COMMA expression
	| GOTO COMMA IDENTIFIER
	| BREAK
	| CONTINUE

procedure_call
	: IDENTIFIER
	| IDENTIFIER COMMA argument_list

argument_list
	: argument
	| argument_list COMMA argument

argument
	: expression			%prec LOWER_THAN_KEYWORD
	| IDENTIFIER EQUALS expression	%prec KEYWORD
	| DIVIDE IDENTIFIER
	| EXTRA EQUALS IDENTIFIER
	| EXTRA EQUALS EXTRA

assignment_statement
	: pointer_expression assignment_operator expression

assignment_operator
	: EQUALS
	| OP_EQUALS

increment_statement
	: PLUSPLUS pointer_expression
	| MINUSMINUS pointer_expression
	| pointer_expression PLUSPLUS
	| pointer_expression MINUSMINUS

expression
	: assignment_statement
	| conditional_expression

conditional_expression
	: logical_expression
	| logical_expression QUESTIONMARK expression COLON conditional_expression

logical_expression
	: bitwise_expression
	| logical_expression AMPAMP bitwise_expression
	| logical_expression PIPEPIPE bitwise_expression
	| TILDE bitwise_expression

bitwise_expression
	: relational_expression
	| bitwise_expression AND relational_expression
	| bitwise_expression OR relational_expression
	| bitwise_expression XOR relational_expression

relational_expression
	: additive_expression
	| relational_expression EQ additive_expression
	| relational_expression NE additive_expression
	| relational_expression LE additive_expression
	| relational_expression LT additive_expression
	| relational_expression GE additive_expression
	| relational_expression GT additive_expression

additive_expression
	: multiplicative_expression
	| additive_expression PLUS multiplicative_expression
	| additive_expression MINUS multiplicative_expression
	| additive_expression LESSTHAN multiplicative_expression
	| additive_expression GREATERTHAN multiplicative_expression
	| NOT multiplicative_expression

multiplicative_expression
	: exponentiative_expression
	| multiplicative_expression TIMES exponentiative_expression
	| multiplicative_expression POUND exponentiative_expression
	| multiplicative_expression POUNDPOUND exponentiative_expression
	| multiplicative_expression DIVIDE exponentiative_expression
	| multiplicative_expression MOD exponentiative_expression

exponentiative_expression
	: unary_expression
	| exponentiative_expression CARET unary_expression

unary_expression
	: pointer_expression
	| PLUS pointer_expression
	| MINUS pointer_expression
	| increment_statement

pointer_expression
	: postfix_expression
	| TIMES pointer_expression

postfix_expression
	: primary_expression
	| postfix_expression LBRACKET subscript_list RBRACKET
	| IDENTIFIER LPAREN RPAREN
	| IDENTIFIER LPAREN argument_list RPAREN
	| postfix_expression DOT IDENTIFIER
	| postfix_expression DOT LPAREN expression RPAREN

primary_expression
	: IDENTIFIER
	| SYS_VAR
	| constant
	| LPAREN expression RPAREN
	| LBRACKET expression_list RBRACKET
	| LBRACE structure_body RBRACE

constant
	: NUMBER
	| STRING

subscript_list
	: subscript
	| subscript_list COMMA subscript

subscript
	: expression
	| expression COLON expression
	| expression COLON expression COLON expression
	| expression COLON TIMES
	| expression COLON TIMES COLON expression
	| TIMES

expression_list
	: expression
	| expression_list COMMA expression

structure_body
	: structure_field_list
	| IDENTIFIER COMMA structure_field_list
	| IDENTIFIER

structure_field_list
	: structure_field
	| structure_field_list COMMA structure_field

structure_field
	: IDENTIFIER COLON expression
	| INHERITS IDENTIFIER
'''


################################################################################
#
# Parser creation
#
################################################################################


def p_error(p):
   "Error function used by the parser"
   error.syntax_error('invalid syntax at %s' % repr(str(p.value)), p.lineno)


def build_productions():
   """
   From the productions string, creates the functions needed by yacc() to
   generate the parser.  Also completes the hierarchy of Node classes in the
   ir module by creating Node subclasses for all non-terminal symbols that
   don't already have one and setting the _symbols field (the list of symbols
   in the relevant production) in each Node subclass.
   """

   funcdefs = []
   classdefs = []

   for prod in productions.strip().split('\n\n'):
      symbols = [ s for s in prod.split() if s not in (':', '|', '%prec') ]
      prodname = symbols[0]
      funcname = 'p_' + prodname
      classname = ''.join([ s.capitalize() for s in prodname.split('_') ])

      if not hasattr(ir, classname):
         exec ('class %s(Node):  pass\n' % classname) in ir.__dict__
      cls = getattr(ir, classname)
      if (not isinstance(cls, type)) or (not issubclass(cls, ir.Node)):
         raise error.InternalError('object %s is not a Node' % classname)
      cls._symbols = set(symbols)

      funcdoc = prod.replace('\n\t', ' ', 1)
      funcdefs.append("def %s(p):\n   '''%s'''\n   p[0] = ir.%s(p)\n" %
                      (funcname, funcdoc, classname))

   exec ''.join(funcdefs) in globals()


def parse(input, debug=False):
   """
   Parses the given input string (which must contain IDL code).  If the parsing
   is successful, returns the root of the resulting abstract syntax tree;
   otherwise, returns None.  If debug is true, any syntax errors will
   produce parser debugging output.
   """

   # Reset global state stuff
   error.clear_error_list()
   map.clear_extra_code()
   lexer.lineno = 1   # This needs to be reset manually (PLY bug?)

   # Ensure that the input contains a final newline (the parser will choke
   # otherwise)
   if input[-1] != '\n':
      input += '\n'

   # Parse input and return the result
   return parser.parse(input, lexer, debug)


#
# Create the parser
#

build_productions()
parser = yacc.yacc(method='LALR', debug=True, tabmodule='ytab',
                   debugfile='y.output', outputdir=os.path.dirname(__file__))


