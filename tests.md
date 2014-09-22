
Testing the `toolbox` module
===============================

To run, do this at the command prompt:

    $ python -m doctest tests.txt

Note: nothing will be shown if tests pass. You can add a verbose flag
(`-v`) to show passing tests.


Using the `toolbox` module
-----------------------------

The `toolbox` module is meant to be used as a library, not a script, so
your own code would import it as here:

    >>> import toolbox

Since `toolbox` is a common module name, in the event of a collision,
you can rename it on import as done here:

    >>> import toolbox as tb

The rest of the tests below will use `tb` as the module name.


Basic Parsing Tests via `read_toolbox_file()`
---------------------------------------------

The `read_toolbox_file()` function takes a file-like object as the first
parameter. In general this will be an open file, but if the data exists
in memory (as in this test), `io.StringIO` objects can be used.

    >>> from io import StringIO
    >>> s1 = StringIO('''
    ... \\mkr1 basic
    ... \\mkr2 extra  whitespace
    ... \\mkr3 multi-
    ... line
    ... \\mkr4 multiline
    ...
    ... with a gap
    ... \\mkr5 multiline
    ...
    ... with a gap and trailing newline
    ...
    ... \\mkr6 unicode　テキスト
    ... \\nullcontent
    ... \\marker_in_text this is not a \\marker
    ... \\emptycontent ''')
    >>> for mkr, text in tb.read_toolbox_file(s1):
    ...    print((mkr, text))
    ('\\mkr1', 'basic')
    ('\\mkr2', 'extra  whitespace')
    ('\\mkr3', 'multi-\nline')
    ('\\mkr4', 'multiline\n\nwith a gap')
    ('\\mkr5', 'multiline\n\nwith a gap and trailing newline')
    ('\\mkr6', 'unicode　テキスト')
    ('\\nullcontent', None)
    ('\\marker_in_text', 'this is not a \\marker')
    ('\\emptycontent', '')

All whitespace is preserved except for trailing whitespace. Even this
can be preserved by using the `strip=False` parameter.

    >>> list(tb.read_toolbox_file(StringIO('\\mkr trailing space '),
    ...                           strip=False))
    [('\\mkr', 'trailing space ')]
    >>> list(tb.read_toolbox_file(StringIO('\\mkr trailing newline\n'),
    ...                           strip=False))
    [('\\mkr', 'trailing newline\n')]
    >>> list(tb.read_toolbox_file(StringIO('\\mkr newline and space\n '),
    ...                           strip=False))
    [('\\mkr', 'newline and space\n ')]