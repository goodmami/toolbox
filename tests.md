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

```python
>>> import toolbox

```

Since `toolbox` is a common module name, in the event of a collision,
you can rename it on import as done here:

```python
>>> import toolbox as tb

```

The rest of the tests below will use `tb` as the module name.


Basic Parsing Tests via `read_toolbox_file()`
---------------------------------------------

The `read_toolbox_file()` function takes a file-like object as the first
parameter. In general this will be an open file, but if the data exists
in memory (as in this test), `io.StringIO` objects can be used.

```python
>>> from io import StringIO

```

Also note that `read_toolbox_file()` returns a generator, so you'll need
to cast it as a list, if that's what you need, or just iterate over the
results. The generator yields tuples of (marker, text).

```python
>>> next(tb.read_toolbox_file(StringIO('\\mkr text')))
('\\mkr', 'text')
>>> list(tb.read_toolbox_file(StringIO('\\mkr text')))
[('\\mkr', 'text')]

```

For convenience, I define a simple lambda expression `rtf()` that deals
with the boilerplate code here. It behaves like `read_toolbox_file()`, but
takes a string as the first parameter, and returns a list.

```python
>>> rtf = lambda s, strip=True: list(
...     tb.read_toolbox_file(StringIO(s), strip=strip)
... )

```

The tests below show the behavior of the Toolbox parser:

The most basic functionality is to split a marker and the following text:

```python
>>> rtf('\\mkr basic tokens')
[('\\mkr', 'basic tokens')]

```

The space after the marker is mandatory and not included in the text, but
all other non-trailing spacing should be maintained:

```python
>>> rtf('\\mkr   maintain    internal  whitespace')
[('\\mkr', '  maintain    internal  whitespace')]

```

Even newlines:

```python
>>> rtf('''\\mkr multi-
... line''')
[('\\mkr', 'multi-\nline')]

```

Even blank lines:

```python
>>> rtf('''\\mkr multiline
...
... with a gap''')
[('\\mkr', 'multiline\n\nwith a gap')]

```

But whitespace (including blank lines) at the end will be trimmed:

```python
>>> rtf('''\\mkr multiline
...
... with a gap and trailing newline
... ''')
[('\\mkr', 'multiline\n\nwith a gap and trailing newline')]

```

Unless the `strip=False` parameter is used:

```python
>>> rtf('\\mkr trailing space  ', strip=False)
[('\\mkr', 'trailing space  ')]
>>> rtf('''\\mkr trailing newline
... ''', strip=False)
[('\\mkr', 'trailing newline\n')]
>>> rtf('''\mkr trailing newline and spaces
...   ''', strip=False)
[('\\mkr', 'trailing newline and spaces\n  ')]

```

If no space appears after the marker, the text is considered null:

```python
>>> rtf('\\mkr')
[('\\mkr', None)]

```

But if a space and nothing else follows, it's considered empty content:

```python
>>> rtf('\\mkr ')
[('\\mkr', '')]

```

Markers only appear at the beginning of a line:

```python
>>> rtf('\\mkr \\mkr is just a token')
[('\\mkr', '\\mkr is just a token')]

```

And furthermore only in the first column (note: this means that you can't
have marker-like text as the first thing after a newline):

```python
>>> rtf('''\\mkr newline then a marker
...  \\mkr''')
[('\\mkr', 'newline then a marker\n \\mkr')]

```

Markers can be very long:

```python
>>> rtf('\\this_is_a_very_long_marker and some text')
[('\\this_is_a_very_long_marker', 'and some text')]

```

But in practice they are very short:

```python
>>> rtf('\\f just one char')
[('\\f', 'just one char')]

```

But they can't be nothing or just a space:

```python
>>> rtf('\\ text')
[]
>>> rtf('\\ ')
[]
>>> rtf('\\\nmkr text')
[]
>>> rtf('\\')
[]

```

Unicode text is not a problem:

```python
>>> rtf('\\mkr unicode　テキスト')
[('\\mkr', 'unicode　テキスト')]

```

Even for markers:

```python
>>> rtf('\\マーカー テキスト')
[('\\マーカー', 'テキスト')]

```

But (currently) double-width spaces don't count as a marker delimiter:

```python
>>> rtf('\\マーカー　テキスト')
[]

```

But the double-width spaces do get trimmed from the right edge:

```python
>>> rtf('\\マーカー テキスト　')
[('\\マーカー', 'テキスト')]
>>> rtf('\\マーカー テキスト　', strip=False)
[('\\マーカー', 'テキスト　')]

```

Multiple markers and text are ok, but preceding text without a marker will
be ignored:

```python
>>> lines = rtf('''some text
... without \\mkr or some other marker
...
... and some more
... \\mkr finally a marker
... \\mkr2 and another with
... a newline, followed by
...
... \\mkr3 yet another''')
>>> for mkr, text in lines:
...     print((mkr, text))
('\\mkr', 'finally a marker')
('\\mkr2', 'and another with\na newline, followed by')
('\\mkr3', 'yet another')

```

Line Grouping with `iterparse()`
--------------------------------

Groups of (marker, value) pairs often come in blocks of related data.
The `toolbox.iterparse()` function helps in processing this kind of
data. Given some keys, it will report events with the associated data.
The 'key', 'start', and 'end' events simply give the (marker, value)
pairs as the result if '\key', '\+key', or '\-key', respectively, were
seen. The result of the 'data' event is the list of (marker, value)
pairs that occur between keys.

```python
>>> pairs = rtf('''
... \\ref 1
... \\a val
... \\b val
... \\ref 2
... \\a val2''')
>>> records = tb.iterparse(pairs, keys=['\\ref'])
>>> for event, result in records:
...     print((event, result))
('key', ('\\ref', '1'))
('data', [('\\a', 'val'), ('\\b', 'val')])
('key', ('\\ref', '2'))
('data', [('\\a', 'val2')])

```

The 'start' and 'end' events are treated as normal keys (no special
grouping of data between related start and end events is performed),
but the user only needs to specify the key without the `+` or `-`:

```python
>>> pairs = rtf('''
... \\+block
... \\a val
... \\+subblock
... \\b val
... \\-subblock
... \\c val
... \\-block''')
>>> events = tb.iterparse(pairs, keys=['\\block', '\\subblock'])
>>> for event, result in events:
...     print((event, result))
('start', ('\\block', None))
('data', [('\\a', 'val')])
('start', ('\\subblock', None))
('data', [('\\b', 'val')])
('end', ('\\subblock', None))
('data', [('\\c', 'val')])
('end', ('\\block', None))

```


Record Grouping with `records()`
--------------------------------

```python
>>> pairs = rtf('''
... \\header info
... \\ref 1
... \\t some words
... \\m some word -s
... \\ref 2
... \\t more words
... \\m more word -s''')
>>> recs = tb.records(pairs, '\\ref')
>>> for ctxt, data in recs:
...    print((sorted(ctxt.items()), data))
([('\\ref', None)], [('\\header', 'info')])
([('\\ref', '1')], [('\\t', 'some words'), ('\\m', 'some word -s')])
([('\\ref', '2')], [('\\t', 'more words'), ('\\m', 'more word -s')])

```

```python
>>> pairs = rtf('''
... \\ref 1
... \\t text
... \\id i1
... \\header info
... \\ref 2
... \\t text again
... \\ref 3
... \\t and again''')
>>> recs = tb.records(pairs, ['\\id', '\\ref'])
>>> for ctxt, data in recs:
...     print((sorted(ctxt.items()), data))
([('\\id', None), ('\\ref', '1')], [('\\t', 'text')])
([('\\id', 'i1'), ('\\ref', None)], [('\\header', 'info')])
([('\\id', 'i1'), ('\\ref', '2')], [('\\t', 'text again')])
([('\\id', 'i1'), ('\\ref', '3')], [('\\t', 'and again')])

```

```python
>>> pairs = rtf('''
... \\ref 1
... \\t text
... \\id i1
... \\header info
... \\ref 2
... \\t text again
... \\page 5
... \\ref 3
... \\t and again''')
>>> recs = tb.records(pairs, ['\\id', '\\ref'], context_keys=['\\page'])
>>> for ctxt, data in recs:
...     print((sorted(ctxt.items()), data))
([('\\id', None), ('\\page', None), ('\\ref', '1')], [('\\t', 'text')])
([('\\id', 'i1'), ('\\page', None), ('\\ref', None)], [('\\header', 'info')])
([('\\id', 'i1'), ('\\page', None), ('\\ref', '2')], [('\\t', 'text again')])
([('\\id', 'i1'), ('\\page', '5'), ('\\ref', '3')], [('\\t', 'and again')])

```


Field Grouping with `field_groups()`
------------------------------------

```python
>>> pairs = rtf('''
... \\j 犬が吠える
... \\t inu=ga   hoeru
... \\m inu =ga  hoe  -ru
... \\g dog =NOM bark -IPFV
... \\f A dog barks.
... ''')
>>> for pair_list in tb.field_groups(pairs, set(['\\t', '\\m', '\\g'])):
...     print(pair_list)  # doctest: +NORMALIZE_WHITESPACE
[('\\j', '犬が吠える')]
[('\\t', 'inu=ga   hoeru'),
 ('\\m', 'inu =ga  hoe  -ru'),
 ('\\g', 'dog =NOM bark -IPFV')]
[('\\f', 'A dog barks.')]

```

Unwrapping and Respacing with `normalize_record()`
------------------------------------------------

Aligned fields that Toolbox has wrapped can be reconstructed into single
lines that keep the column spacing intact. Unaligned fields will be wrapped
without considering spaced columns.

```python
>>> pairs = rtf('''
... \\ref s1
... \\t waadorappu sareta
... \\m waadorappu sare-ta
... \\g word.wrap  PASS-PFV
... \\t tekisuto
... \\m tekisuto
... \\g text
... \\f word-wrapped text
... ''')
>>> normrecs = tb.normalize_record(pairs, set(['\\t', '\\m', '\\g']))
>>> for mkr, val in normrecs:
...     print((mkr, val))
('\\ref', 's1')
('\\t', 'waadorappu sareta   tekisuto')
('\\m', 'waadorappu sare-ta  tekisuto')
('\\g', 'word.wrap  PASS-PFV text')
('\\f', 'word-wrapped text')

```

By default, trailing spaces are stripped from each line, but (as in
`toolbox.read_toolbox_file()`), this behavior can be turned off by setting
`strip=False`:

```python
>>> pairs = rtf('''
... \\a abc
... \\b s
... \\a def
... \\b tuvwxyz
... ''')
>>> for mkr, val in tb.normalize_record(pairs, ['\\a', '\\b']):
...     print((mkr, val))
('\\a', 'abc def')
('\\b', 's   tuvwxyz')
>>> for mkr, val in tb.normalize_record(pairs, ['\\a', '\\b'], strip=False):
...     print((mkr, val))
('\\a', 'abc def    ')
('\\b', 's   tuvwxyz')

```


Aligning Interlinear Columns with `align_fields()`
--------------------------------------------------

The `align_fields()` function attempts to interpret the interlinear structure
that is implicitly encoded in the spacing of the tokens. Not all lines are
so aligned, so `align_fields()` requires a dictionary mapping the marker of
one line to the marker of the line it aligns to. For example, often the `\m`
morphemes line aligns to the `\t` text line, so `'\m': '\t'` would encode
this alignment. This function returns tuples of (marker, alignments) for each
line, where marker is the line's marker and alignments is a list of
(token, aligned_tokens) tuples.

```python
>>> pairs = rtf('''
... \\t inu=ga   ippiki           hoeru
... \\m inu =ga  ichi -hiki       hoe  -ru
... \\g dog =NOM one  -CLF.ANIMAL bark -IPFV
... \\f One dog barks.
... \\x''')
>>> algns = tb.align_fields(pairs, alignments={'\\m': '\\t', '\\g': '\\m'})
>>> for algn in algns:
...     print(algn)  # doctest: +NORMALIZE_WHITESPACE
('\\t', [('inu=ga   ippiki           hoeru', ['inu=ga', 'ippiki', 'hoeru'])])
('\\m', [('inu=ga', ['inu', '=ga']),
         ('ippiki', ['ichi', '-hiki']),
         ('hoeru', ['hoe', '-ru'])])
('\\g', [('inu', ['dog']),
         ('=ga', ['=NOM']),
         ('ichi', ['one']),
         ('-hiki', ['-CLF.ANIMAL']),
         ('hoe', ['bark']),
         ('-ru', ['-IPFV'])])
('\\f', [(None, ['One dog barks.'])])
('\\x', [(None, None)])

```

This function also has some capability to recover from inaccurate column
spacings. There is an optional parameter `errors` that defaults to `strict`
but can be set to `ratio` or `reanalyze`. The `strict` setting raises an error
when a token crosses an observed column boundary, but `ratio` will group the
token with whichever column it is most covered by, and `reanalyze` will ignore
tabular spacing and rely on token delimiters to find groupings. The possible
misalignment will still raise an warning (instead of an error), but these can
be silenced. However, it may be useful for the maintainer of a corpus to see
the warnings, as it can point out possible errors in the corpus. For example,
here is the `ratio` method:

```python
>>> import warnings
>>> warnings.simplefilter('ignore')
>>> pairs = rtf('''
... \\t inu=ga   ippiki           hoeru
... \\m inu    =ga  ichi -hiki       hoe  -ru
... \\g dog    =NOM one  -CLF.ANIMAL bark -IPFV
... \\f One dog barks.''')
>>> algns = tb.align_fields(
...     pairs,
...     alignments={'\\m': '\\t', '\\g': '\\m'},
...     errors='ratio'
... )
>>> for algn in algns:
...     print(algn)  # doctest: +NORMALIZE_WHITESPACE
('\\t', [('inu=ga   ippiki           hoeru', ['inu=ga', 'ippiki', 'hoeru'])])
('\\m', [('inu=ga', ['inu', '=ga']),
         ('ippiki', ['ichi', '-hiki']),
         ('hoeru', ['hoe', '-ru'])])
('\\g', [('inu', ['dog']),
         ('=ga', ['=NOM']),
         ('ichi', ['one']),
         ('-hiki', ['-CLF.ANIMAL']),
         ('hoe', ['bark']),
         ('-ru', ['-IPFV'])])
('\\f', [(None, ['One dog barks.'])])

```

And here is the `reanalyze` method. Note that morpheme delimiters that group
with their morpheme are kept attached, but unattached delimiters or those not
adjacent to a space get separated as tokens (because it is impossible to
determine which side it attaches to):

```python
>>> import warnings
>>> warnings.simplefilter('ignore')
>>> pairs = rtf('''
... \\t inu=ga ippiki hoeru
... \\m inu =ga ichi-hiki hoe - ru
... \\g dog =NOM one-CLF.ANIMAL bark - IPFV
... \\f One dog barks.''')
>>> algns = tb.align_fields(
...     pairs,
...     alignments={'\\m': '\\t', '\\g': '\\m'},
...     errors='reanalyze'
... )
>>> for algn in algns:
...     print(algn)  # doctest: +NORMALIZE_WHITESPACE
('\\t', [('inu=ga ippiki hoeru', ['inu=ga', 'ippiki', 'hoeru'])])
('\\m', [('inu=ga', ['inu', '=ga']),
         ('ippiki', ['ichi', '-', 'hiki']),
         ('hoeru', ['hoe', '-', 'ru'])])
('\\g', [('inu', ['dog']),
         ('=ga', ['=NOM']),
         ('ichi', ['one']),
         ('-', ['-']),
         ('hiki', ['CLF', '.', 'ANIMAL']),
         ('hoe', ['bark']),
         ('-', ['-']),
         ('ru', ['IPFV'])])
('\\f', [(None, ['One dog barks.'])])

```
