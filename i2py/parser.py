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
This file contains the IDL grammar specification.  From the specification
string, it generates the functions needed for PLY's yacc for each non-terminal
symbol; each function generates a Node object of the appropriate subclass, as
defined in ir.py.  Finally, it uses yacc to generate the parser.
"""

from lexer import *
import yacc
import ir
import error

def p_error(p):
   msg = 'invalid syntax at %s' % repr(str(p.value))
   if p.type == 'IDENTIFIER':
      msg += ' (undeclared procedure or function?)'
   error.syntax_error(msg, p.lineno)

def build_productions():
   funcdefs = []
   classdefs = []

   for rule in productions.strip().split('\n\n'):
      rulename = rule.split()[0]
      funcname = 'p_' + rulename
      classname = ''.join([ s.capitalize() for s in rulename.split('_') ])

      if not hasattr(ir, classname):
         classdefs.append('class %s(Node):  pass\n' % classname) 
      else:
	 cls = getattr(ir, classname)
         if (not isinstance(cls, type)) or (not issubclass(cls, ir.Node)):
	    raise ir.InternalError('object %s is not a Node' % classname)

      funcdoc = rule.replace('\n\t', ' ', 1)
      funcdefs.append('def %s(p):\n   \'\'\'%s\'\'\'\n   p[0] = ir.%s(p)\n' %
                      (funcname, funcdoc, classname))

   if classdefs:  exec ''.join(classdefs) in ir.__dict__
   exec ''.join(funcdefs) in globals()

precedence = (
   ('nonassoc', 'LOWER_THAN_ELSE'),
   ('nonassoc', 'ELSE'),
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
	: PRO PRO_ID subroutine_body
	| FUNCTION FUNCTION_ID subroutine_body

subroutine_body
	: NEWLINE statement_list END NEWLINE
	| parameter_list NEWLINE statement_list END NEWLINE

parameter_list
	: COMMA parameter
	| parameter_list COMMA parameter

parameter
	: IDENTIFIER
	| IDENTIFIER EQUALS IDENTIFIER
	| EXTRA EQUALS IDENTIFIER

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
	: expression COLON statement
	| expression COLON NEWLINE statement

if_statement 
	: IF expression THEN if_clause %prec LOWER_THAN_ELSE
	| IF expression THEN if_clause ELSE else_clause 

if_clause
	: statement
	| BEGIN NEWLINE statement_list ENDIF

else_clause
	: statement
	| BEGIN NEWLINE statement_list ENDELSE

selection_statement
	: CASE selection_statement_body ENDCASE
	| SWITCH selection_statement_body ENDSWITCH

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

for_index
	: IDENTIFIER EQUALS expression COMMA expression
	| IDENTIFIER EQUALS expression COMMA expression COMMA expression

while_statement
	: WHILE expression DO statement
	| WHILE expression DO BEGIN NEWLINE statement_list ENDWHILE

repeat_statement
	: REPEAT statement UNTIL expression
	| REPEAT BEGIN NEWLINE statement_list ENDREP UNTIL expression

simple_statement
	: COMMON identifier_list
	| COMPILE_OPT identifier_list
	| FORWARD_FUNCTION identifier_list
	| ON_IOERROR COMMA IDENTIFIER
	| jump_statement
	| procedure_call
	| expression

identifier_list
	: IDENTIFIER
	| identifier_list COMMA IDENTIFIER

jump_statement
	: RETURN
	| RETURN COMMA expression
	| GOTO IDENTIFIER
	| BREAK
	| CONTINUE

procedure_call
	: PRO_ID
	| PRO_ID COMMA argument_list

argument_list
	: argument
	| argument_list COMMA argument

argument
	: expression
	| DIVIDE IDENTIFIER
	| EXTRA EQUALS IDENTIFIER

expression
	: assignment_expression

assignment_expression
	: conditional_expression
	| pointer_expression assignment_operator assignment_expression

assignment_operator
	: EQUALS
	| OP_EQUALS

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
	| PLUSPLUS pointer_expression
	| MINUSMINUS pointer_expression
	| pointer_expression PLUSPLUS
	| pointer_expression MINUSMINUS

pointer_expression
	: postfix_expression
	| TIMES pointer_expression

postfix_expression
	: primary_expression
	| postfix_expression LBRACKET subscript_list RBRACKET
	| FUNCTION_ID LPAREN RPAREN
	| FUNCTION_ID LPAREN argument_list RPAREN
	| postfix_expression DOT IDENTIFIER
	| postfix_expression DOT LPAREN expression RPAREN

primary_expression
	: IDENTIFIER
	| SYS_VAR
	| constant
	| LPAREN expression RPAREN
	| LBRACKET expression_list RBRACKET
	| LBRACE structure_field_list RBRACE

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

structure_field_list
	: structure_field
	| structure_field_list COMMA structure_field

structure_field
	: expression
	| expression COLON expression
	| INHERITS IDENTIFIER
'''

build_productions()

yacc.yacc(debug=0, tabmodule='ytab', debugfile='y.output')
parse = yacc.parse

