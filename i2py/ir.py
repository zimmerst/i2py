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
import re
from util import *
import yacc
import i2py_map


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
      return name in self.child_dict and self.child_dict[name]


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
	 # if l.strip()[:1] == ';':
	 #    l = l.replace(';', '#', 1)
         m = re.match(r'\s*(;+)', l)
         if m:
	    l = l.replace(';', '#', len(m.groups()[0]))
	 else:
	    l = l.replace('&', ';')
         lines.append(l)
      return '\n'.join(lines)

   def asdocstring(self):
      doc = self.pycode().strip()
      try:
         ii = doc.index('#+')
         jj = doc.index('#-')
         doc = doc[ii:jj+2]
      except ValueError:
         pass
      doc = '\n'.join([ l.replace('#', '', 1)
	                for l in doc.split('\n') ][1:-1])
      if len(doc):
         return '"""\n%s\n"""' % doc
      return ''


class Name(Leaf):
   def __init__(self, raw):
      self.raw = raw
   def __str__(self):
      return config.idlnameconv(self.raw)
   def pycode(self):
      vmap = i2py_map.get_variable_map(self.raw)
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
	    if self.val[-1].lower() == 'x':
	       s = '0x' + self.val[1:-2].lower()
	    elif self.val[-1].lower() == 'o':
	       s = self.val[1:-2]
	       if s[0] != '0':
	          s = '0' + s
            elif self.val[-1].lower() == 'b':
               s = '0b' + self.val[1:-2]
            else:
               raise RuntimeError("Invalid numeric literal")
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
      global _classes_used
      _classes_used = {}

      import ipdb; ipdb.set_trace()


      parts = []
      if self.statement_list:
         parts.append(pycode(self.statement_list))
      if self.program:
         parts.append(pycode(self.program))

      ec = i2py_map.get_extra_code()
      if ec:
         parts.append(ec)

      for cname in _classes_used:
         c = _classes_used[cname]
         if ~hasattr(c, 'init_def'):    # bare methods, no class definition or initializer method
            parts.append(('class %s(%s):\n'% (pycode(cname), config.baseclassname) \
                  + "\n".join([ pyindent(m) for m in c.methods])))
            continue
         parts.append(('class %s(%s):\n'% (pycode(cname), c.base_classes) \
               + "\n".join([ pyindent(m)
                     for m in ['__i2py_tagnames__ = %s\n' % (c.tag_names), c.init_def ] + c.methods])))

      if _classes_used:
         # IDL structs become objects of type I2PY_Struct, or subclasses thereof
         init_def = 'def __init__(self, *args, **kws):\n' \
               + pyindent('self.__dict__.update(zip(self.__i2py_tagnames__, args))\n') \
               + pyindent('self.__dict__.update(kws)')
         get_def = 'def __getitem__(self, key):\n' \
               + pyindent('return self.__dict__[self.__i2py_tagnames__[key]]')
         repr_def = 'def __repr__(self):\n'  \
               + pyindent('return "%s(%s)" % (self.__class__.__name__,\n') \
               + pyindent(pyindent('", ".join("%s=%s" % (k, v) for k, v in self.__dict__.iteritems()))'))
         parts.append(('class %s(object):\n'% config.baseclassname) \
               + pyindent('__i2py_tagnames__ = []') + '\n' \
               + pyindent(init_def) + '\n' \
               + pyindent(get_def) + '\n' \
               + pyindent(repr_def))


      parts.append('from %s import *' % config.arraymodule)
      # import ipdb; ipdb.set_trace()

      try:
         nl = self.NEWLINE[0]
      except TypeError:
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

def find_structure_body(self):
   # Dig through the AST to find the class definition
   try:
      sb = self.structure_body
      if sb: return sb
      for child in self.child_list:
         sb = find_structure_body(child)
         if sb: return sb
   except:
      pass
   return None

def ClassDefinition(name, structbody):
   """ will this work? """
   global _classes_used

   #import ipdb; ipdb.set_trace()
   if name not in _classes_used:
      _classes_used[name] = type("", (), {})()       # anonymous type
      _classes_used[name].methods = []

   p = _classes_used[name] 
   bc_names, tag_names, init_body = structbody.structure_field_list.classdef()
   p.base_classes = ", ".join(bc_names + [config.baseclassname])
   p.tag_names = tag_names
   # header = 'class %s(%s):' % (pycode(name), superclasses)

   # tag_names = '__i2py_tagnames__ = ' + str(tag_names)

   init_body = init_body + '\n' + "%s.__init__(self, *args, **kws)\n" % config.baseclassname
   if hasattr(p, 'init_def'):
      p.init_def = p.init_def[0] + pyindent(init_body) + p.init_def[1]
   else:
      p.init_def = "def __init__(self, *args, **kws):" + '\n' + pyindent(init_body)

   return ''


class SubroutineDefinition(Node):
   def __str__(self):
      return '%s %s' % tuple(self)
   def pycode(self):
      global _in_pro, _in_function, _classes_used

      pars = []
      keys = []
      extra = []
      method = False

      # import ipdb; ipdb.set_trace()
      plist = self.subroutine_body.parameter_list

      if self.subroutine_body.method_name.DCOLON is None:
         name = pycode(self.subroutine_body.method_name)
         if name[-8:].lower() == '__define':       # class definition
            if plist:
               print "Class definition with parameters -- probably not allowed!"
            return ClassDefinition(name[:-8], find_structure_body(self))
      else:
         # Method definition
         classname, name = map(pycode, self.subroutine_body.method_name.IDENTIFIER)
         # methodname = pycode(methodname)
         # classname = pycode(classname)
         method = True



      if plist:
	 for p in plist.get_items():
	    if p.EXTRA:
               extra = pycode(p.IDENTIFIER) if p.IDENTIFIER else "extra"
               continue
	    if p.EQUALS:
	       keys.append((pycode(p.IDENTIFIER[0]), pycode(p.IDENTIFIER[1])))
	    else:
	       pars.append(pycode(p.IDENTIFIER))

      fmap = i2py_map.get_subroutine_map(name)
      if not fmap:
         inpars  = range(1, len(pars)+1)
	 outpars = inpars
	 inkeys  = [ k[0] for k in keys ]
	 outkeys = inkeys

      if self.PRO:
         _in_pro = True
	 if not fmap:
	    fmap = i2py_map.map_pro(name, inpars=inpars, outpars=outpars,
	                       inkeys=inkeys, outkeys=outkeys, method=method)
      elif self.FUNCTION:
         _in_function = True
	 if not fmap:
	    fmap = i2py_map.map_func(name, inpars=inpars, inkeys=inkeys, method=method)
      else:
         raise RuntimeError("not PRO, not FUNCTION, then what?")

      try:
         header, body = fmap.pydef(pars, keys, extra=extra)
      except i2py_map.Error, e:
         error.mapping_error(str(e), self.lineno)
	 header, body = '', ''

      # import ipdb; ipdb.set_trace()

      body += '\n' + pycode(self.subroutine_body.statement_list)

      if self.PRO or self.FUNCTION:
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

      # Plain functions
      if self.subroutine_body.method_name.DCOLON is None:
         return (header + nl + pyindent(body) +
                 pycode(self.subroutine_body.NEWLINE[1]))

      # Methods
      #import ipdb; ipdb.set_trace()
      # header = header.replace(name, methodname)

      if classname not in _classes_used:
         _classes_used[classname] = type("", (), {})()       # anonymous type
         _classes_used[classname].methods = []
      p = _classes_used[classname]

      if name == 'init':
         header = header.replace('init', '__init__')
         p.init_def = [header + nl, pyindent(body)]
      else:
         p.methods.append(header + nl + pyindent(body) +
                 pycode(self.subroutine_body.NEWLINE[1]))
      return ""



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
   def classdef(self):
      if len(self) == 1:
         return classdef(self[0])
      sc0, n0, b0 = classdef(self[0])
      sc1, n1, b1 = classdef(self[2])
      return sc0+sc1, n0+n1, '%s%s' % (b0, b1)
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


class ForeachStatement(Node):
   def __str__(self):
      # ids = self.identifier_list.get_items()
      # if len(ids) != 2: raise ValueError("Need two identifiers in FOREACH")
      for_ind = str(self.foreach_index)

      if self.BEGIN:
         stmt = 'BEGIN%s%sENDFOREACH' % (self.NEWLINE,
                                           indent(self.statement_list))
      else:
         stmt = str(self.statement)
      return 'FOREACH %s DO %s' % (for_ind, stmt)
   def pycode(self):
      # import ipdb; ipdb.set_trace()
      # ids = self.identifier_list.get_items()
      # if len(ids) != 2: raise ValueError("Need two identifiers in FOREACH")

      if self.statement:
         body = self.statement
         nl = '\n'
      else:
         body = self.statement_list
         nl = pycode(self.NEWLINE)
      return 'for %s:%s%s' % (pycode(self.foreach_index),
                                    nl, pyindent(body).rstrip('\n'))


class ForeachIndex(Node):
   def __str__(self):
      # import ipdb; ipdb.set_trace()
      try:
         return "%s, %s, %s" % (self.IDENTIFIER[0], self.expression, self.IDENTIFIER[1])
      except TypeError:
         return "%s, %s" % (self.IDENTIFIER, self.expression)

   def pycode(self):
      # if self.IDENTIFIER is a list, then there is a KEY which is hard to deal
      # with properly in the general case.  Assume EXPRESSION is a hashtable for now.
      # import ipdb; ipdb.set_trace()
      try:
         if len(self.IDENTIFIER) != 2:
            raise ValueError("Need two identifiers to FOREACH with key")
         return "%s, %s in %s.iteritems()" % (pycode(self.IDENTIFIER[1]),
                                              pycode(self.IDENTIFIER[0]),
                                              pycode(self.expression))
      except TypeError:
         return "%s in %s.itervalues()" % (pycode(self.IDENTIFIER), 
                                           pycode(self.expression))

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
         return str(self.method_or_proc)
      return '%s, %s' % (self.method_or_proc, self.argument_list)
   def pycode(self):
      if self.argument_list:
         pars, keys, extra = self.argument_list.get_pars_and_keys()
      else:
         pars = []
         keys = []
         extra = []

      name = str(self.method_or_proc)
      fmap = i2py_map.get_subroutine_map(name)

      if not fmap:
	 keys = [ '%s=%s' % (k[0], k[1]) for k in keys ]
         return '%s(%s)' % (pycode(self.method_or_proc), ', '.join(pars + keys + extra))

      try:
         return fmap.pycall(pars, keys)
      except i2py_map.Error, e:
         error.mapping_error(str(e), self.lineno)
	 return ''


class ArgumentList(_CommaSeparatedList):
   def get_pars_and_keys(self):
      pars = []
      keys = []
      extra = []

      for a in self.get_items():
	 if a.EXTRA:
	    # FIXME: implement this!
	    # error.conversion_error("can't handle _EXTRA yet", self.lineno)
	    extra = ['**' + pycode(a[-1])]
	 elif a.DIVIDE:
	    keys.append((pycode(a.IDENTIFIER), 'True'))
	 elif a.IDENTIFIER:
	    keys.append((pycode(a.IDENTIFIER), pycode(a.expression)))
	 else:
	    pars.append(pycode(a.expression))

      return (pars, keys, extra)


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
      #return ('((%s) and [%s] or [%s])[0]' %
      #        (pycode(self.logical_expression), pycode(self.expression),
      #       pycode(self.conditional_expression)))
      return '%s if %s else %s' % (pycode(self.conditional_expression[0]),
         pycode(self.logical_expression), pycode(self.conditional_expression[1]))


class LogicalExpression(_SpacedExpression):
   def pycode(self):
      if len(self) == 1:
         return _SpacedExpression.pycode(self)
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
         f = '>'        # looks wrong, but is correct.
      else:
         f = '<'
      a = pycode(self.additive_expression)
      m = pycode(self.multiplicative_expression)
      return 'choose(%s %s %s, (%s, %s))' % (a, f, m, a, m)


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
      if self.TILDE:
         return 'logical_not(%s)' % pycode(self.pointer_expression)
      if self.increment_statement:
         # FIXME: implement this!
         #error.conversion_error("can't handle ++,-- in expressions yet", self.lineno)

         return '%s #{ %s }#' % (Node.pycode(self.increment_statement.pointer_expression),
                    "".join(pycode(x) for x in self.increment_statement[:]))
      return Node.pycode(self)


class PointerExpression(Node):
   def pycode(self):
      if self.TIMES:
         # FIXME: implement this!
         #error.conversion_error("can't handle pointers yet", self.lineno)
         return self.pointer_expression.pycode()
      return Node.pycode(self)


class PostfixExpression(Node):
   def pycode(self):
      if self.DOT and self.LPAREN:
         # import ipdb; ipdb.set_trace()
         return "%s[%s]" % (pycode(self.postfix_expression), pycode(self.expression))

      if self.ARROW:
         return "%s.%s" % (pycode(self.postfix_expression[0]), pycode(self.postfix_expression[1]))

      if self.DOT or (not self.method_or_proc):
         return Node.pycode(self)

      if self.argument_list:
         pars, keys, extra = self.argument_list.get_pars_and_keys()
      else:
         pars = []
         keys = []
         extra = []

      name = str(self.method_or_proc)
      fmap = i2py_map.get_subroutine_map(name)

      if not fmap:
	 keys = [ '%s=%s' % (k[0], k[1]) for k in keys ]
         return '%s(%s)' % (pycode(self.method_or_proc), ', '.join(pars + keys + extra))

      try:
         return fmap.pycall(pars, keys)
      except i2py_map.Error, e:
         error.mapping_error(str(e), self.lineno)
	 return ''


class PrimaryExpression(Node):
   def pycode(self):
      if self.LBRACE:
         return pycode(self.structure_body)
      if self.LBRACKET:
         return 'array([%s])' % Node.pycode(self)
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


# Anonymous IDL structures will become instances of the class I2PY_Struct,
# and all structure creation will become object instantiation
class StructureBody(Node):
   def __str__(self):
      if self.IDENTIFIER:
	 s = str(self.IDENTIFIER)
	 if self.COMMA:
	    s += ', %s' % self.structure_field_list
         return s
      return Node.__str__(self)
   def pycode(self):
      global _classes_used
      # print "jobbing"
      # return self.__super__.pycode(self)
      # import ipdb; ipdb.set_trace()
      classname = config.baseclassname
      if self.IDENTIFIER:
         classname = pycode(self.IDENTIFIER)
         classbody = pycode(self.structure_field_list)
      else:
         classname = config.baseclassname
         classbody = pycode(self.anonymous_struct_field_list)
      return '%s(%s)' % (classname, classbody)



class StructureFieldList(_CommaSeparatedList):
   def pycode(self):
      if self.structure_field.INHERITS:
         if self.structure_field_list:
            return pycode(self.structure_field_list)
         return None
      if len(self) == 1:
         return pycode(self[0])
      sflist, sf = (pycode(self[0]), pycode(self[2]))
      if sflist is None:
         return sf
      return '%s, %s' % (sflist, sf)




class AnonymousStructFieldList(_CommaSeparatedList):
   pass

class StructureField(Node):
   def __str__(self):
      if self.INHERITS:
         return 'INHERITS %s' % self.IDENTIFIER
      return ''.join([ str(c) for c in self ])
   def pycode(self):
      #import ipdb; ipdb.set_trace()
      if self.INHERITS:
         return ''
      if self.IDENTIFIER:
         return "%s=%s" % (pycode(self.IDENTIFIER), pycode(self.expression))
      return pycode(self.expression)
   def classdef(self):
      if self.INHERITS:
         return [pycode(self.IDENTIFIER)], [], ''
      return [], [pycode(self.IDENTIFIER)], "self.%s=%s\n" % (pycode(self.IDENTIFIER), pycode(self.expression)) 

class AnonymousStructField(Node):
   def pycode(self):
      return "%s=%s" % (pycode(self.IDENTIFIER), pycode(self.expression))
   def classdef(self):
      return [], [pycode(self.IDENTIFIER)], "self.%s=%s\n" % (pycode(self.IDENTIFIER), pycode(self.expression)) 


class MethodOrProc(Node):
   def pycode(self):
      if self.object_method:
         return "%s.%s" % (pycode(self.object_method.pointer_expression), pycode(self.object_method.method_name))
      return pycode(self.IDENTIFIER)

class MethodName(Node):
   def pycode(self):
      if self.DCOLON:
         return ".".join(pycode(x) for x in self.IDENTIFIER)
      else:
         return pycode(self.IDENTIFIER)



