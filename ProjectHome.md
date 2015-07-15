i2py provides tools for converting programs and scripts written in the [IDL](http://www.ittvis.com/idl/) programming language to [Python](http://python.org/). It is not an IDL-compatible front end for the Python interpreter, nor does it make any attempt to replicate the functionality of the IDL standard library. Rather, its only purpose is to perform source-to-source conversion of legacy IDL code to Python.

i2py is implemented in pure Python and should run on any system for which the Python interpreter is available. It uses the excellent [PLY](http://www.dabeaz.com/ply/) package to handle lexing and parsing. (The needed modules are distributed with i2py, so there is no need to install PLY separately.)

## Project Status ##

i2py was abandoned in 2005, with known limitations listed below.  TG assumed co-ownership in 2012, with main concern to have a translator which is a help when migrating a codebase, not necessarily to produce valid Python code.  It may get you 75-80% of the way, but you must accept that some editing by hand will be necessary after the machine translation.  Therefore, the translator will currently mark untranslateable constructs with the "#{" and "}#" markers instead of aborting.

Structs and objects are translated as Python classes with a default constructor, and the class definition is used to create an (internal) class member containing (public) member names, thus supporting the `s.(i)` construct.  Class and struct inheritance works, except for the `s.(i)` construct.  (This might be fixed).

Almost all Python variables behave like IDL pointers with automatic dereferencing, so `ptr_new()` is translated as `None` and `ptr_new(expr)` as `expr`.  Any fancy use of pointers must be checked by hand after translation.

In Python, increment and decrement are statements, not expressions (i.e. they have no value).  Any IDL statement using increment and decrement for their value are inherently untranslateable for an automated tool.  Such statements will be flagged, and must be fixed by hand.

Output parameters for functions and procedures should be handled better.

Several IDL constructions with straightforward equivalents have been added to `maplib.py`, but coverage is still far from comprehensive.

## Statement of limitations for release 0.1 ##

i2py is still in the alpha stage.  Although the package is definitely
usable, it may undergo extensive changes and
will require a good deal of testing and debugging before it's ready for
production use.

Here are some known issues with release 0.1 of i2py:

  * The following IDL constructs cannot be converted yet, and i2py will signal an error and abort if it encounters any of them:
    * extra keywords (`_EXTRA`)
    * assignment and increment/decrement statements in expressions (e.g. `b = 2 + (a = 3)`)
    * structure definitions
    * accessing structure fields by number (`<struct>.(<field_index>)`)
    * pointers
  * There are only a few predefined mappings for IDL variables and subroutines.  (These are in the file `maplib.py`.)
  * The current mapping for IDL's `WHERE` function does not support its second parameter. (This is one example of the general problem of converting functions with output parameters to Python.)
  * The package has undergone only limited testing (mostly on examples from the [IDL Astronomy User's Library](http://idlastro.gsfc.nasa.gov/)), so there are probably quite a few bugs lurking in the code.
  * The author of i2py isn't actually an IDL programmer, so the package may not properly account for subtle (or perhaps not so subtle) differences between the semantics of IDL and Python.