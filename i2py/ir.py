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
The classes defined in this file provide abstract representations of the
terminal and non-terminal symbols defined in the grammar.  Each such class has
an __str__() method that generates IDL code for the given object and a pycode()
method that produces the corresponding Python code.  To understand what's going
on in those methods, you need to refer to the grammar specification in
parser.py.
"""

import yacc
import fmap
import maps
import error


#
# Utility classes and functions
#

class InternalError(Exception):
   pass

def pycode(obj):
   if hasattr(obj, 'pycode'):
      return obj.pycode()
   return str(obj)

idltab = '   '
pytab  = '   '

def indent(obj, ntabs=1, tab=None):
   if not tab:  tab = idltab
   pad = ntabs * tab
   return pad + str(obj).replace('\n', '\n' + pad).rstrip(tab)

def pyindent(obj, ntabs=1, tab=None):
   if not tab:  tab = pytab
   pad = ntabs * tab
   return pad + pycode(obj).replace('\n', '\n' + pad).rstrip(tab)

def pycomment(obj):
   return pyindent(obj, tab='# ')

def reduce_expression(expr):
   # Try to reduce a constant expression
   try:
      return str(eval(expr, {}))
   except:
      return expr

def find_nodes(root, nodetype=None):
   if not isinstance(root, Node):
      raise InternalError('expecting Node, got ' + root.__class__.__name__)

   nodes = []

   for child in root:
      if nodetype and isinstance(child, nodetype):
         nodes.append(child)
      elif isinstance(child, Node):
         nodes += find_nodes(child, nodetype)
      else:
         # FIXME: throw an exception here?
	 pass

   return nodes


#
# Abstract base classes
#

class Leaf(object):
   pass

class Node(object):
   def __init__(self, prod):
      if not isinstance(prod, yacc.YaccProduction):
         raise InternalError('expecting YaccProduction, got ' +
	                     prod.__class__.__name__)

      self.lineno = prod.lineno(0)
      self.child_list = list(prod)[1:]

      self.child_dict = {}
      for item in prod.slice[1:]:
	 if item.type not in self.child_dict:
            self.child_dict[item.type] = item.value
	 else:
	    if isinstance(self.child_dict[item.type], list):
	       self.child_dict[item.type].append(item.value)
	    else:
	       self.child_dict[item.type] = ([self.child_dict[item.type],
	                                      item.value])

   def __getattr__(self, name):
      return self.child_dict.get(name)

   def __getitem__(self, index):
      return self.child_list[index]

   def __len__(self):
      return len(self.child_list)

   def __str__(self):
      return ''.join([ str(child) for child in self ])

   def pycode(self):
      return ''.join([ pycode(child) for child in self ])


#
# Terminal symbols
#

class Name(Leaf):
   def __init__(self, raw):
      self.raw = raw
   def __str__(self):
      return self.raw.upper()
   def pycode(self):
      s = self.raw.lower()
      if s[0] == '!':
         s = '_sys_' + s[1:]
      return s

class Number(Leaf):
   def __init__(self, parts):
      self.parts = parts

   def __getattr__(self, name):
      return self.parts[name]

   def __str__(self):
      if self.float:
         return self.float
      return self.integer

   def pycode(self):
      if self.float:
         s = self.dec
         if self.exp:
	    s += 'e'
	    if self.expval:
	       s += self.expval
            else:
	       s += '0'
      else:
         if self.val[0] == "'":
	    if self.val[-1] == 'X':
	       s = '0x' + self.val[1:-2].lower()
	    else:
	       s = self.val[1:-2]
	       if s[0] != '0':
	          s = '0' + s
	 elif self.val[0] == '"':
	    s = self.val[1:]
	    if s[0] != '0':
	       s = '0' + s
	 else:
	    s = self.val
      return s


#
# Nonterminal symbols
#

class TranslationUnit(Node):
   def __str__(self):
      return str(self[-1])
   def pycode(self):
      parts = [pycode(self[-1])]
      if fmap.extra_code:
         parts.append('\n'.join(fmap.extra_code))
      parts.append('from numarray import *')
      parts.reverse()
      return '\n\n'.join(parts)

_in_pro = False
_in_function = False

class SubroutineDefinition(Node):
   def __str__(self):
      return '%s %s%s' % tuple(self)
   def pycode(self):
      global _in_pro, _in_function

      if self.PRO:
         _in_pro = True
	 map = fmap.procedures[str(self.PRO_ID)]
      else:
         _in_function = True
	 map = fmap.functions[str(self.FUNCTION_ID)]

      pars = []
      keys = []

      plist = self.subroutine_body.parameter_list
      if plist:
	 for p in find_nodes(plist, Parameter):
	    if p.EXTRA:
	       # FIXME: implement this!
	       error.conversion_error("can't handle _EXTRA yet", self.lineno)
	       return ''
	    if p.EQUALS:
	       keys.append((pycode(p.IDENTIFIER[0]), pycode(p.IDENTIFIER[1])))
	    else:
	       pars.append(pycode(p.IDENTIFIER))

      try:
         s = map.pydef(pars, keys)
      except fmap.Error, e:
         error.mapping_error(str(e), self.lineno)
	 s = ''

      s += pyindent(self.subroutine_body.statement_list)

      _in_pro = False
      _in_function = False

      return s

class SubroutineBody(Node):
   def __str__(self):
      if self.parameter_list:
         params = str(self.parameter_list)
      else:
         params = ''
      return '%s\n%sEND\n' % (params, indent(self.statement_list))

class ParameterList(Node):
   def __str__(self):
      if self.parameter_list:
         plist = str(self.parameter_list)
      else:
         plist = '' 
      return '%s, %s' % (plist, self.parameter)

class LabeledStatement(Node):
   def __str__(self):
      return '%s: %s' % (self.expression, self.statement)
   def pycode(self):
      return '%s:\n%s' % (pycomment(self.expression), pycode(self.statement))

class IfStatement(Node):
   def __str__(self):
      s = 'IF %s THEN %s' % (self.expression, self.if_clause)
      if self.else_clause:
         s += ' ELSE %s' % self.else_clause
      return s
   def pycode(self):
      s = 'if %s:\n%s' % (pycode(self.expression),
                          pyindent(self.if_clause).rstrip('\n'))
      if self.else_clause:
         s += '\nelse:\n%s' % pyindent(self.else_clause)
      return s

class _IfOrElseClause(Node):
   def __str__(self):
      if not self.BEGIN:
         return str(self.statement)
      return 'BEGIN\n%s%s' % (indent(self.statement_list), self[-1])
   def pycode(self):
      if not self.BEGIN:
         return pycode(self.statement)
      return pycode(self.statement_list)
class IfClause(_IfOrElseClause):  pass
class ElseClause(_IfOrElseClause):  pass

class SelectionStatement(Node):
   def pycode(self):
      body = self.selection_statement_body
      s = '_expr = %s\n' % pycode(body.expression)

      if self.CASE:
         is_switch = False
      else:
         is_switch = True
	 s += '_match = False\n'

      cases, actions = body.selection_clause_list.get_cases_and_actions()

      key = 'if'
      first = True
      for c, a in zip(cases, actions):
	 test = reduce_expression('(%s)' % c)
	 test = '_expr == %s' % test
	 if (not first) and is_switch:
	    test = '_match or (%s)' % test

         s += '%s %s:\n%s' % (key, test, pyindent(a))

	 if is_switch:
	    s += '\n%s' % pyindent('_match = True')

         if first:
	    if is_switch:
	       key = '\nif'
	    else:
	       key = '\nelif'
	    first = False

      if body.ELSE:
         s += '\nelse:\n%s' % pyindent(body.selection_clause)
      elif not is_switch:
         s += '\nelse:\n%s' % pyindent("raise RuntimeError('no match found " +
	                               "for expression')")

      return s

class SelectionStatementBody(Node):
   def __str__(self):
      s = ' %s OF\n%s' % (self.expression,
                          indent(self.selection_clause_list))
      if self.ELSE:
         s += '   ELSE %s' % self.selection_clause
      return s

class SelectionClauseList(Node):
   def get_cases_and_actions(self):
      if self.selection_clause_list:
         cases, actions = self.selection_clause_list.get_cases_and_actions()
      else:
         cases = []
         actions = []

      cases.append(pycode(self.expression))
      actions.append(pycode(self.selection_clause))

      return (cases, actions)

class SelectionClause(Node):
   def __str__(self):
      if self.BEGIN:
         stmt = ' BEGIN\n%s   END' % indent(self.statement_list, 2)
      elif self.statement:
         stmt = ' %s' % self.statement
      else:
         stmt = ''
      return ':%s\n' % stmt
   def pycode(self):
      if self.statement_list:
         return pycode(self.statement_list).rstrip('\n')
      if self.statement:
         return pycode(self.statement)
      return 'pass'

class ForStatement(Node):
   def __str__(self):
      if self.BEGIN:
         stmt = 'BEGIN\n%sENDFOR' % indent(self.statement_list)
      else:
         stmt = str(self.statement)
      return 'FOR %s DO %s' % (self.for_index, stmt)
   def pycode(self):
      if self.statement:
         body = self.statement
      else:
         body = self.statement_list
      return 'for %s:\n%s' % (pycode(self.for_index),
                              pyindent(body).rstrip('\n'))

class ForIndex(Node):
   def __str__(self):
      s = '%s = %s, %s' % (self.IDENTIFIER, self.expression[0],
                           self.expression[1])
      if len(self) == 7:
         s += ', %s' % self.expression[2]
      return s
   def pycode(self):
      maxval = reduce_expression('(%s)+1' % pycode(self.expression[1]))
      s = '%s in xrange(%s, %s' % (pycode(self.IDENTIFIER),
                                   pycode(self.expression[0]), maxval)
      if len(self) == 7:
         s += ', %s' % pycode(self.expression[2])
      return s + ')'

class WhileStatement(Node):
   def __str__(self):
      if self.BEGIN:
         stmt = 'BEGIN\n%sENDWHILE' % indent(self.statement_list)
      else:
         stmt = str(self.statement)
      return 'WHILE %s DO %s' % (self.expression, stmt)
   def pycode(self):
      if self.statement:
         body = self.statement
      else:
         body = self.statement_list
      return 'while %s:\n%s' % (pycode(self.expression),
                                pyindent(body).rstrip('\n'))

class RepeatStatement(Node):
   def __str__(self):
      if self.BEGIN:
         stmt = 'BEGIN\n%sENDREP' % indent(self.statement_list)
      else:
         stmt = str(self.statement)
      return 'REPEAT %s UNTIL %s' % (stmt, self.expression)
   def pycode(self):
      if self.statement:
         body = self.statement
      else:
         body = self.statement_list
      return 'while True:\n%s\n%s' % (pyindent(body).rstrip('\n'),
				      pyindent('if %s:  break' %
				               pycode(self.expression)))

class SimpleStatement(Node):
   def __str__(self):
      if self.ON_IOERROR:
         return 'ON_IOERROR, %s' % self.IDENTIFIER
      return ' '.join([ str(c) for c in self ])
   def pycode(self):
      if self.COMMON:
	 if (not _in_pro) and (not _in_function):
            error.syntax_error('COMMON outside of PRO or FUNCTION', self.lineno)
	    return ''
         return 'global ' + pycode(self.identifier_list)
      if len(self) == 1:
         return Node.pycode(self)
      return pycomment(str(self))

class _CommaSeparatedList(Node):
   def __str__(self):
      if len(self) == 1:
         return str(self[0])
      return '%s, %s' % (self[0], self[2])
   def pycode(self):
      if len(self) == 1:
         return pycode(self[0])
      return '%s, %s' % (pycode(self[0]), pycode(self[2]))

class IdentifierList(_CommaSeparatedList):
   pass

class JumpStatement(Node):
   def __str__(self):
      if self.RETURN and self.expression:
         return 'RETURN, %s' % self.expression
      return ' '.join([ str(c) for c in self ])
   def pycode(self):
      if self.GOTO:
         error.conversion_error('cannot convert GOTO statements; please ' +
	                        'remove them and try again', self.lineno)
         return pycomment(str(self))
      if not self.RETURN:
         return str(self[0]).lower()
      if _in_pro:
         return 'return _ret()'
      if _in_function:
         return 'return ' + pycode(self.expression)
      error.syntax_error('RETURN outside of PRO or FUNCTION', self.lineno)
      return ''

class ProcedureCall(Node):
   def __str__(self):
      if not self.argument_list:
         return str(self.PRO_ID)
      return '%s, %s' % (self.PRO_ID, self.argument_list)
   def pycode(self):
      if self.argument_list:
         pars, keys = self.argument_list.get_pars_and_keys()
      else:
         pars = []
         keys = []

      try:
         return fmap.procedures[str(self.PRO_ID)].pycall(pars, keys)
      except fmap.Error, e:
         error.mapping_error(str(e), self.lineno)
	 return ''

class ArgumentList(_CommaSeparatedList):
   def get_pars_and_keys(self):
      pars = []
      keys = []

      for a in find_nodes(self, Argument):
	 if a.EXTRA:
	    # FIXME: implement this!
	    error.conversion_error("can't handle _EXTRA yet", self.lineno)
	    return ''
	 if a.DIVIDE:
	    keys.append((pycode(a.IDENTIFIER), 'True'))
	 else:
	    ae = a.expression.assignment_expression
	    if ae.assignment_operator:
	       keys.append((pycode(ae.pointer_expression),
		            pycode(ae.assignment_expression)))
	    else:
	       pars.append(pycode(a.expression))

      return (pars, keys)

class _SpacedExpression(Node):
   def __str__(self):
      if (len(self) == 2) and (not self.NOT):
         return '%s%s' % tuple(self)
      return ' '.join([ str(c) for c in self ])
   def pycode(self):
      if (len(self) == 2) and (not self.NOT):
         return '%s%s' % (pycode(self[0]), pycode(self[1]))
      return ' '.join([ pycode(c) for c in self ])

class AssignmentExpression(_SpacedExpression):
   def pycode(self):
      if (len(self) == 1) or self.assignment_operator.EQUALS:
         return _SpacedExpression.pycode(self)

      op = self.assignment_operator.OP_EQUALS
      lvalue = pycode(self.pointer_expression)
      rvalue = pycode(self.assignment_expression)

      if op == '#=':
         return (('%s = transpose(matrixmultiply(transpose(%s), ' +
	          'transpose(%s)))') % (lvalue, lvalue, rvalue))

      augops = {'AND=':'&=', 'MOD=':'%=', 'XOR=':'^=', 'OR=':'|=', '+=':'+=',
                '-=':'-=', '*=':'*=', '/=':'/=', '^=':'**='}
      binops = {'EQ=':'==', 'GE=':'>=', 'GT=':'>', 'LE=':'<=', 'LT=':'<',
                'NE=':'!='}
      funcops = {'##=':'matrixmultiply', '<=':'minimum', '>=':'maximum'}

      if op in augops:
         return '%s %s %s' % (lvalue, augops[op], rvalue)
      if op in binops:
         return '%s = %s %s %s' % (lvalue, lvalue, binops[op], rvalue)
      return '%s = %s(%s, %s)' % (lvalue, funcops[op], lvalue, rvalue)

class ConditionalExpression(_SpacedExpression):
   def pycode(self):
      if not self.QUESTIONMARK:
         return _SpacedExpression.pycode(self)
      return ('((%s) and [%s] or [%s])[0]' %
              (pycode(self.logical_expression), pycode(self.expression),
	       pycode(self.conditional_expression)))

class LogicalExpression(_SpacedExpression):
   def pycode(self):
      if len(self) == 1:
         return _SpacedExpression.pycode(self)
      if self.TILDE:
         return 'logical_not(%s)' % pycode(self[1])
      if self.AMPAMP:
         op = 'and'
      else:
         op = 'or'
      return 'logical_%s(%s, %s)' % (op, pycode(self.logical_expression),
                                     pycode(self.bitwise_expression))

class BitwiseExpression(_SpacedExpression):
   def pycode(self):
      if len(self) == 1:
         return _SpacedExpression.pycode(self)
      if self.AND:
         op = 'and'
      elif self.OR:
         op = 'or'
      else:
         op = 'xor'
      return 'bitwise_%s(%s, %s)' % (op, pycode(self.bitwise_expression),
                                     pycode(self.relational_expression))

class RelationalExpression(_SpacedExpression):
   def pycode(self):
      if len(self) == 1:
         return _SpacedExpression.pycode(self)
      if self.EQ:
         op = '=='
      elif self.NE:
         op = '!='
      elif self.LE:
         op = '<='
      elif self.LT:
         op = '<'
      elif self.GE:
         op = '>='
      else:
         op = '>'
      return '%s %s %s' % (pycode(self.relational_expression), op,
                           pycode(self.additive_expression))

class AdditiveExpression(_SpacedExpression):
   def pycode(self):
      if (len(self) == 1) or self.PLUS or self.MINUS:
         return _SpacedExpression.pycode(self)
      if self.NOT:
         return 'bitwise_not(%s)' % pycode(self.multiplicative_expression)
      if self.LESSTHAN:
         f = 'minimum'
      else:
         f = 'maximum'
      return '%s(%s, %s)' % (f, pycode(self.additive_expression),
                             pycode(self.multiplicative_expression))

class MultiplicativeExpression(_SpacedExpression):
   def pycode(self):
      if len(self) == 1:
         return _SpacedExpression.pycode(self)
      if self.POUND:
         return ('transpose(matrixmultiply(transpose(%s), transpose(%s)))' %
	         (pycode(self.multiplicative_expression),
		 pycode(self.exponentiative_expression)))
      if self.POUNDPOUND:
         return ('matrixmultiply(%s, %s)' %
	         (pycode(self.multiplicative_expression),
		 pycode(self.exponentiative_expression)))
      if self.TIMES:
         op = '*'
      elif self.DIVIDE:
         op = '/'
      else:
         op = '%'
      return '%s %s %s' % (pycode(self.multiplicative_expression), op,
                           pycode(self.exponentiative_expression))

class ExponentiativeExpression(_SpacedExpression):
   def pycode(self):
      if len(self) == 1:
         return _SpacedExpression.pycode(self)
      return '%s ** %s' % (pycode(self.exponentiative_expression),
                           pycode(self.unary_expression))

class UnaryExpression(Node):
   def pycode(self):
      if self.PLUSPLUS or self.MINUSMINUS:
         # FIXME: implement this!
         error.conversion_error("can't handle ++,-- yet", self.lineno)
         return ''
      return Node.pycode(self)

class PointerExpression(Node):
   def pycode(self):
      if self.TIMES:
         # FIXME: implement this!
         error.conversion_error("can't handle pointers yet", self.lineno)
         return ''
      return Node.pycode(self)

class PostfixExpression(Node):
   def pycode(self):
      if self.DOT and self.LPAREN:
         # FIXME: implement this!
         error.conversion_error("can't handle '<struct>.(<field_index>)' yet",
	                        self.lineno)
         return ''

      if not self.FUNCTION_ID:
         return Node.pycode(self)

      if self.argument_list:
         pars, keys = self.argument_list.get_pars_and_keys()
      else:
         pars = []
         keys = []

      try:
         return fmap.functions[str(self.FUNCTION_ID)].pycall(pars, keys)
      except fmap.Error, e:
         error.mapping_error(str(e), self.lineno)
	 return ''

class PrimaryExpression(Node):
   def pycode(self):
      if self.LBRACE:
         # FIXME: implement this!
         error.conversion_error("can't handle structures yet", self.lineno)
         return ''
      if self.LBRACKET:
         return 'concatenate(%s)' % Node.pycode(self)
      return Node.pycode(self)

class SubscriptList(Node):
   def pycode(self):
      if len(self) == 1:
         return pycode(self[0])
      return ','.join([pycode(self[2]), pycode(self[0])])

class Subscript(Node):
   def pycode(self):
      if self.COLON:
         if not self.TIMES:
	    ulim = reduce_expression('(%s)+1' % pycode(self.expression[1]))
	    s = '%s:%s' % (pycode(self.expression[0]), ulim)
	    if len(self.expression) == 3:
	       s += ':%s' % pycode(self.expression[2])
	    return s
	 if len(self.expression) == 1:
	    return '%s:' % pycode(self.expression)
	 return '%s::%s' % (pycode(self.expression[0]),
	                    pycode(self.expression[1]))
      if self.TIMES:
         return ':'
      return pycode(self.expression)

class ExpressionList(_CommaSeparatedList):
   pass

class StructureFieldList(_CommaSeparatedList):
   pass

class StructureField(Node):
   def __str__(self):
      if self.INHERITS:
         return 'INHERITS %s' % self.IDENTIFIER
      return ''.join([ str(c) for c in self ])

