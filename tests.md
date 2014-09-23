Testing the `toolbox` module
===============================

To run, do this at the command prompt:

    $ python -m doctest tests.md

Note: nothing will be shown if tests pass. You can add a verbose flag
(`-v`) to all results.

Note 2: The `toolbox` module was created for Python3, but it may work for
Python2, as well (no promises). These tests, however, will likely only work
for Python3, so, depending on your distribution, you may need to explicitly
use it at the command line:

    $ python3 -m doctest tests.md

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

Also note that `read_toolbox_file()` returns a generator, so you'll need
to cast it as a list, if that's what you need, or just iterate over the
results. The generator yields tuples of (marker, text).

    >>> next(tb.read_toolbox_file(StringIO('\\mkr text')))
    ('\\mkr', 'text')
    >>> list(tb.read_toolbox_file(StringIO('\\mkr text')))
    [('\\mkr', 'text')]

For convenience, I define a simple lambda expression `rtf()` that deals
with the boilerplate code here. It behaves like `read_toolbox_file()`, but
takes a string as the first parameter, and returns a list.

    >>> rtf = lambda s, strip=True: list(
    ...     tb.read_toolbox_file(StringIO(s), strip=strip)
    ... )

The tests below show the behavior of the Toolbox parser:

The most basic functionality is to split a marker and the following text:

    >>> rtf('\\mkr basic tokens')
    [('\\mkr', 'basic tokens')]

The space after the marker is mandatory and not included in the text, but
all other non-trailing spacing should be maintained:

    >>> rtf('\\mkr   maintain    internal  whitespace')
    [('\\mkr', '  maintain    internal  whitespace')]

Even newlines:

    >>> rtf('''\\mkr multi-
    ... line''')
    [('\\mkr', 'multi-\nline')]

Even blank lines:

    >>> rtf('''\\mkr multiline
    ...
    ... with a gap''')
    [('\\mkr', 'multiline\n\nwith a gap')]

But whitespace (including blank lines) at the end will be trimmed:

    >>> rtf('''\\mkr multiline
    ...
    ... with a gap and trailing newline
    ... ''')
    [('\\mkr', 'multiline\n\nwith a gap and trailing newline')]

Unless the `strip=False` parameter is used:

    >>> rtf('\\mkr trailing space  ', strip=False)
    [('\\mkr', 'trailing space  ')]
    >>> rtf('''\\mkr trailing newline
    ... ''', strip=False)
    [('\\mkr', 'trailing newline\n')]
    >>> rtf('''\mkr trailing newline and spaces
    ...   ''', strip=False)
    [('\\mkr', 'trailing newline and spaces\n  ')]

If no space appears after the marker, the text is considered null:

    >>> rtf('\\mkr')
    [('\\mkr', None)]

But if a space an nothing else follows, it's considered empty content:

    >>> rtf('\\mkr ')
    [('\\mkr', '')]

Markers only appear at the beginning of a line:

    >>> rtf('\\mkr \\mkr is just a token')
    [('\\mkr', '\\mkr is just a token')]

And furthermore only in the first column (note: this means that you can't
have marker-like text as the first thing after a newline):

    >>> rtf('''\\mkr newline then a marker
    ...  \\mkr''')
    [('\\mkr', 'newline then a marker\n \\mkr')]

Markers can be very long:

    >>> rtf('\\this_is_a_very_long_marker and some text')
    [('\\this_is_a_very_long_marker', 'and some text')]

But in practice they are very short:

    >>> rtf('\\f just one char')
    [('\\f', 'just one char')]

But they can't be nothing or just a space:

    >>> rtf('\\ text')
    []
    >>> rtf('\\ ')
    []
    >>> rtf('\\\nmkr text')
    []
    >>> rtf('\\')
    []

Unicode text is not a problem:

    >>> rtf('\\mkr unicode　テキスト')
    [('\\mkr', 'unicode　テキスト')]

Even for markers:

    >>> rtf('\\マーカー テキスト')
    [('\\マーカー', 'テキスト')]

But (currently) double-width spaces don't count as a marker delimiter:

    >>> rtf('\\マーカー　テキスト')
    []

But the double-width spaces do get trimmed from the right edge:

    >>> rtf('\\マーカー テキスト　')
    [('\\マーカー', 'テキスト')]
    >>> rtf('\\マーカー テキスト　', strip=False)
    [('\\マーカー', 'テキスト　')]
