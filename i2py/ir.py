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
Defines classes representing the nodes and leaves of the abstract syntax tree
(AST).  Each such class can produce IDL or Python code for itself via its
__str__() or pycode() method, respectively.
"""


import config
import error
from util import *
import yacc
import map


################################################################################
#
# Abstract base classes
#
################################################################################


class Leaf(object):
   "Base class for leaves of the AST (terminal symbols)"
   pass


class Node(object):
   "Base class for nodes of the AST (nonterminal symbols)"

   # Set of symbols that appear in the RHS of the grammar production for this
   # node
   _symbols = ()

   def __init__(self, prod):
      "Creates a new Node from prod (a yacc.YaccProduction instance)"

      # Validate input (just a sanity check)
      if not isinstance(prod, yacc.YaccProduction):
         raise error.InternalError('expecting YaccProduction, got ' +
	                           prod.__class__.__name__)

      # Store line number and create child_list
      self.lineno = prod.lineno(0)
      self.child_list = list(prod)[1:]

      #
      # Create child_dict
      #

      self.child_dict = {}

      for item in prod.slice[1:]:
	 if item.type not in self.child_dict:
	    # No entry for this symbol in child_dict, so make one
            self.child_dict[item.type] = item.value
	 else:
	    # There's already an entry for this symbol in child_dict, so the
	    # entry's value must be a list
	    if isinstance(self.child_dict[item.type], list):
	       # Already a list, so append to it
	       self.child_dict[item.type].append(item.value)
	    else:
	       # Make list from previous and current value
	       self.child_dict[item.type] = ([self.child_dict[item.type],
	                                      item.value])

      # For each valid symbol that isn't involved in this instance, make an
      # entry in child_dict with value None
      for symbol in self._symbols:
         if symbol not in self.child_dict:
	    self.child_dict[symbol] = None

   def __getattr__(self, name):
      """
      Given a symbol name from the right-hand side of the grammar production
      for this node, returns the corresponding child node.  If the production
      includes multiple instances of the symbol, returns a list of their values
      (ordered from left to right).  If the given symbol is not used in the
      current instance, returns None.
      """
      return self.child_dict[name]

   def __getitem__(self, index):
      """
      Returns the child node for the symbol at the corresponding position in
      the right-hand side of the grammar production for this node.  Note that,
      unlike __getattr__, this function only provides access to symbols
      actually used in the current instance.
      """
      return self.child_list[index]

   def __len__(self):
      """
      Returns the number of child nodes in the current instance.  This is
      useful for distinguishing which branch of a grammar production applies to
      the instance.
      """
      return len(self.child_list)

   def __str__(self):
      """
      Returns a string containing the IDL code for the AST rooted at this node.
      """
      return ''.join([ str(child) for child in self ])

   def pycode(self):
      """
      Returns a string containing the Python code for the AST rooted at this
      node.
      """
      return ''.join([ pycode(child) for child in self ])


################################################################################
#
# Terminal symbols
#
################################################################################


class Newline(Leaf):
   def __init__(self, raw):
      rawlines = raw.split('\n')
      rawlines = [rawlines[0]] + [ l.strip() for l in rawlines[1:] ]

      self.lines = []

      for l in rawlines:
	 if l.strip() == '':
	    l = ''
	 else:
	    if l[:1] == '&':
	       l = ' ' + l
	    if l[len(l) - 1] == '&':
	       l = l + ' '
         self.lines.append(l)

   def __str__(self):
      return '\n'.join(self.lines)

   def pycode(self):
      lines = []
      for l in self.lines:
	 if l.strip()[:1] == ';':
	    l = l.replace(';', '#', 1)
	 else:
	    l = l.replace('&', ';')
         lines.append(l)
      return '\n'.join(lines)

   def asdocstring(self):
      doc = self.pycode().strip()
      if doc and (doc[:2] == '#+') and (doc[len(doc)-2:] == '#-'):
	 doc = '\n'.join([ l.replace('#', '', 1)
	                   for l in doc.split('\n') ][1:-1])
	 return '"""\n%s\n"""' % doc
      return ''


class Name(Leaf):
   def __init__(self, raw):
      self.raw = raw
   def __str__(self):
      return config.idlnameconv(self.raw)
   def pycode(self):
      vmap = map.get_variable_map(self.raw)
      if vmap:
         return vmap.pyname()
      return pyname(self.raw)


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


################################################################################
#
# Nonterminal symbols
#
################################################################################


class TranslationUnit(Node):
   def pycode(self):
      parts = [pycode(self[-1])]

      ec = map.get_extra_code()
      if ec:
         parts.append(ec)

      parts.append('from %s import *' % config.arraymodule)

      nl = self.NEWLINE
      if nl:
         doc = nl.asdocstring()
	 if doc:
	    parts.append(doc)
	 else:
            parts[0] = pycode(nl) + parts[0]

      parts.reverse()
      return '\n\n'.join(parts)


_in_pro = False
_in_function = False

class SubroutineDefinition(Node):
   def __str__(self):
      return '%s %s' % tuple(self)
   def pycode(self):
      global _in_pro, _in_function

      pars = []
      keys = []

      plist = self.subroutine_body.parameter_list
      if plist:
	 for p in plist.get_items():
	    if p.EXTRA:
	       # FIXME: implement this!
	       error.conversion_error("can't handle _EXTRA yet", self.lineno)
	       return ''
	    if p.EQUALS:
	       keys.append((pycode(p.IDENTIFIER[0]), pycode(p.IDENTIFIER[1])))
	    else:
	       pars.append(pycode(p.IDENTIFIER))

      name = str(self.subroutine_body.IDENTIFIER)
      fmap = map.get_subroutine_map(name)
      if not fmap:
         inpars  = range(1, len(pars)+1)
	 outpars = inpars
	 inkeys  = [ k[0] for k in keys ]
	 outkeys = inkeys

      if self.PRO:
         _in_pro = True
	 if not fmap:
	    fmap = map.map_pro(name, inpars=inpars, outpars=outpars,
	                       inkeys=inkeys, outkeys=outkeys)
      else:
         _in_function = True
	 if not fmap:
	    fmap = map.map_func(name, inpars=inpars, inkeys=inkeys)

      try:
         header, body = fmap.pydef(pars, keys)
      except map.Error, e:
         error.mapping_error(str(e), self.lineno)
	 header, body = '', ''

      body += '\n' + pycode(self.subroutine_body.statement_list)

      if self.PRO:
         last = self.subroutine_body.statement_list.get_statements()[-1]
         jump = last.simple_statement and last.simple_statement.jump_statement
         if (not jump) or (not jump.RETURN):
            body += '\nreturn _ret()\n'

      nl = self.subroutine_body.NEWLINE[0]
      doc = nl.asdocstring()
      if doc:
         nl = '\n' + pyindent(doc) + '\n\n'
      else:
         nl = pycode(nl)

      _in_pro = False
      _in_function = False

      return (header + nl + pyindent(body) +
              pycode(self.subroutine_body.NEWLINE[1]))


class SubroutineBody(Node):
   def __str__(self):
      if self.parameter_list:
         params = ', ' + str(self.parameter_list)
      else:
         params = ''
      return '%s%s%s%sEND%s' % (self.IDENTIFIER, params, self.NEWLINE[0],
                                indent(self.statement_list), self.NEWLINE[1])


class _CommaSeparatedList(Node):
   def __str__(self):
      if len(self) == 1:
         return str(self[0])
      return '%s, %s' % (self[0], self[2])
   def pycode(self):
      if len(self) == 1:
         return pycode(self[0])
      return '%s, %s' % (pycode(self[0]), pycode(self[2]))
   def get_items(self):
      if len(self) == 1:
         items = [self[0]]
      else:
         items = self[0].get_items()
	 items.append(self[2])
      return items


class ParameterList(_CommaSeparatedList):
   pass


class LabeledStatement(Node):
   def __str__(self):
      if self.NEWLINE:
         return '%s:%s%s' % (self.IDENTIFIER, self.NEWLINE, self.statement)
      return '%s: %s' % (self.IDENTIFIER, self.statement)
   def pycode(self):
      if self.NEWLINE:
         nl = pycode(self.NEWLINE)
      else:
         nl = '\n'
      return '%s:%s%s' % (pycomment(self.IDENTIFIER), nl,
                          pycode(self.statement))


class StatementList(Node):
   def get_statements(self):
      if not self.statement_list:
         stmts = [self.statement]
      else:
         stmts = self.statement_list.get_statements()
	 stmts.append(self.statement)
      return stmts


class IfStatement(Node):
   def __str__(self):
      s = 'IF %s THEN %s' % (self.expression, self.if_clause)
      if self.else_clause:
         s += ' ELSE %s' % self.else_clause
      return s
   def pycode(self):
      s = 'if %s:%s' % (pycode(self.expression),
                          pyindent(self.if_clause).rstrip('\n'))
      if self.else_clause:
         s += '\nelse:%s' % pyindent(self.else_clause).rstrip('\n')
      return s


class _IfOrElseClause(Node):
   def __str__(self):
      if not self.BEGIN:
         return str(self.statement)
      return 'BEGIN%s%s%s' % (self.NEWLINE, indent(self.statement_list),
                              self[-1])
   def pycode(self):
      if not self.BEGIN:
         return '\n' + pycode(self.statement)
      return pycode(self.NEWLINE) + pycode(self.statement_list)

class IfClause(_IfOrElseClause):  pass
class ElseClause(_IfOrElseClause):  pass


class SelectionStatement(Node):
   def pycode(self):
      body = self.selection_statement_body
      s = '_expr = %s%s' % (pycode(body.expression), pycode(body.NEWLINE))

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

         s += '%s %s:%s' % (key, test, pyindent(a))

	 if is_switch:
	    s += '%s\n' % pyindent('_match = True')

         if first:
	    if is_switch:
	       key = 'if'
	    else:
	       key = 'elif'
	    first = False

      if body.ELSE:
         s += 'else:%s' % pyindent(body.selection_clause)
      elif not is_switch:
         s += 'else:\n%s' % pyindent("raise RuntimeError('no match found " +
	                               "for expression')")

      return s


class SelectionStatementBody(Node):
   def __str__(self):
      s = ' %s OF%s%s' % (self.expression, self.NEWLINE,
                          indent(self.selection_clause_list))
      if self.ELSE:
         s += indent('ELSE %s' % self.selection_clause)
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
         nl = self.NEWLINE[1]
         stmt = ' BEGIN%s%s   END' % (self.NEWLINE[0],
	                              indent(self.statement_list, 2))
      else:
	 nl = self.NEWLINE
         if self.statement:
            stmt = ' %s' % self.statement
         else:
            stmt = ''
      return ':%s%s' % (stmt, nl)
   def pycode(self):
      if self.statement_list:
         return '%s%s%s' % (pycode(self.NEWLINE[0]),
	                    pycode(self.statement_list).rstrip('\n'),
			    pycode(self.NEWLINE[1]))
      if self.statement:
         return '\n' + pycode(self.statement) + pycode(self.NEWLINE)
      return '\npass' + pycode(self.NEWLINE)


class ForStatement(Node):
   def __str__(self):
      if self.BEGIN:
         stmt = 'BEGIN%s%sENDFOR' % (self.NEWLINE, indent(self.statement_list))
      else:
         stmt = str(self.statement)
      return 'FOR %s DO %s' % (self.for_index, stmt)
   def pycode(self):
      if self.statement:
         body = self.statement
	 nl = '\n'
      else:
         body = self.statement_list
	 nl = pycode(self.NEWLINE)
      return 'for %s:%s%s' % (pycode(self.for_index), nl,
                              pyindent(body).rstrip('\n'))


class ForIndex(Node):
   def __str__(self):
      s = '%s = %s, %s' % (self.IDENTIFIER, self.expression[0],
                           self.expression[1])
      if len(self.expression) == 3:
         s += ', %s' % self.expression[2]
      return s
   def pycode(self):
      minval = pycode(self.expression[0])
      maxval = pycode(self.expression[1])
      if len(self.expression) == 3:
         incval = pycode(self.expression[2])
      else:
         incval = '1'

      maxval = reduce_expression('(%s)+(%s)' % (maxval, incval))

      s = '%s in arange(%s, %s' % (pycode(self.IDENTIFIER), minval, maxval)
      if len(self.expression) == 3:
         s += ', %s' % incval

      return s + ')'


class WhileStatement(Node):
   def __str__(self):
      if self.BEGIN:
         stmt = 'BEGIN%s%sENDWHILE' % (self.NEWLINE,
	                               indent(self.statement_list))
      else:
         stmt = str(self.statement)
      return 'WHILE %s DO %s' % (self.expression, stmt)
   def pycode(self):
      if self.statement:
         body = self.statement
	 nl = '\n'
      else:
         body = self.statement_list
	 nl = pycode(self.NEWLINE)
      return 'while %s:%s%s' % (pycode(self.expression), nl,
                                pyindent(body).rstrip('\n'))


class RepeatStatement(Node):
   def __str__(self):
      if self.BEGIN:
         stmt = 'BEGIN%s%sENDREP' % (self.NEWLINE, indent(self.statement_list))
      else:
         stmt = str(self.statement)
      return 'REPEAT %s UNTIL %s' % (stmt, self.expression)
   def pycode(self):
      if self.statement:
         body = self.statement
	 nl = '\n'
      else:
         body = self.statement_list
	 nl = pycode(self.NEWLINE)
      return 'while True:%s%s\n%s' % (nl, pyindent(body).rstrip('\n'),
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
         return 'global ' + ', '.join([ pycode(id) for id in
	                                self.identifier_list.get_items()[1:] ])
      if len(self) == 1:
         return Node.pycode(self)
      return pycomment(str(self))


class IdentifierList(_CommaSeparatedList):
   pass


class JumpStatement(Node):
   def __str__(self):
      if self.RETURN and self.expression:
         return 'RETURN, %s' % self.expression
      if self.GOTO:
         return 'GOTO, %s' % self.IDENTIFIER
      return Node.__str__(self)
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
         return str(self.IDENTIFIER)
      return '%s, %s' % (self.IDENTIFIER, self.argument_list)
   def pycode(self):
      if self.argument_list:
         pars, keys = self.argument_list.get_pars_and_keys()
      else:
         pars = []
         keys = []

      name = str(self.IDENTIFIER)
      fmap = map.get_subroutine_map(name)

      if not fmap:
	 keys = [ '%s=%s' % (k[0], k[1]) for k in keys ]
         return '%s(%s)' % (pycode(self.IDENTIFIER), ', '.join(pars + keys))

      try:
         return fmap.pycall(pars, keys)
      except map.Error, e:
         error.mapping_error(str(e), self.lineno)
	 return ''


class ArgumentList(_CommaSeparatedList):
   def get_pars_and_keys(self):
      pars = []
      keys = []

      for a in self.get_items():
	 if a.EXTRA:
	    # FIXME: implement this!
	    error.conversion_error("can't handle _EXTRA yet", self.lineno)
	    return ''
	 if a.DIVIDE:
	    keys.append((pycode(a.IDENTIFIER), 'True'))
	 elif a.IDENTIFIER:
	    keys.append((pycode(a.IDENTIFIER), pycode(a.expression)))
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


class AssignmentStatement(_SpacedExpression):
   def pycode(self):
      if (len(self) == 1) or self.assignment_operator.EQUALS:
         return _SpacedExpression.pycode(self)

      op = self.assignment_operator.OP_EQUALS
      lvalue = pycode(self.pointer_expression)
      rvalue = pycode(self.expression)

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


class IncrementStatement(Node):
   def pycode(self):
      if self.PLUSPLUS:
         op = '+'
      else:
         op = '-'
      return '%s %s= 1' % (pycode(self.pointer_expression), op)


class Expression(Node):
   def pycode(self):
      if self.assignment_statement:
         # FIXME: implement this!
         error.conversion_error("can't handle assignment in expressions yet",
	                        self.lineno)
         return ''
      return Node.pycode(self)


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
      if self.increment_statement:
         # FIXME: implement this!
         error.conversion_error("can't handle ++,-- in expressions yet",
	                        self.lineno)
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

      if self.DOT or (not self.IDENTIFIER):
         return Node.pycode(self)

      if self.argument_list:
         pars, keys = self.argument_list.get_pars_and_keys()
      else:
         pars = []
         keys = []

      name = str(self.IDENTIFIER)
      fmap = map.get_subroutine_map(name)

      if not fmap:
	 keys = [ '%s=%s' % (k[0], k[1]) for k in keys ]
         return '%s(%s)' % (pycode(self.IDENTIFIER), ', '.join(pars + keys))

      try:
         return fmap.pycall(pars, keys)
      except map.Error, e:
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


class StructureBody(Node):
   def __str__(self):
      if self.IDENTIFIER:
	 s = str(self.IDENTIFIER)
	 if self.COMMA:
	    s += ', %s' % self.structure_field_list
         return s
      return Node.__str__(self)


class StructureFieldList(_CommaSeparatedList):
   pass


class StructureField(Node):
   def __str__(self):
      if self.INHERITS:
         return 'INHERITS %s' % self.IDENTIFIER
      return ''.join([ str(c) for c in self ])


