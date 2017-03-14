# toolbox

Python implementation of [SIL's Toolbox](www.sil.org/computing/toolbox)
Standard Format Markers (SFM) format. The basic format looks like this:

```
\mkr a line of text
```

Where `\mkr` is called a *marker* and is followed by a space, then one
or more lines of text.


## Basic Usage

The `toolbox` module is meant to be used as a library, not a script, so
you'll need to first make sure it's findable by Python. Either copy
`toolbox.py` to your project directory, or adjust `PYTHONPATH`:

```bash
export PYTHONPATH=/path/to/toolbox:"$PYTHONPATH"
```

You can then load it in Python and use it to read stored Toolbox files.
For example, the `read_toolbox_file()` function reads a Toolbox file and
yields (marker, text) pairs:

```python
>>> import toolbox
>>> for mkr, text in toolbox.read_toolbox_file(open('example/corpus.txt')):
...     print('Marker: {0!r:<8}Text: {1!r}'.format(mkr, text))
Marker: '\\ref' Text: 'item1'
Marker: '\\t'   Text: 'O        Pedro baixou'
Marker: '\\m'   Text: 'O        Pedro bai   -xou'
Marker: '\\g'   Text: 'the.M.SG Pedro lower -PST.IND.3SG'
Marker: '\\t'   Text: 'a        bola'
Marker: '\\m'   Text: 'a        bola'
Marker: '\\g'   Text: 'the.F.SG ball.F.SG'
Marker: '\\f'   Text: 'Pedro calmed down.'
Marker: '\\l'   Text: 'Pedro lowered the ball.'

```

(By default, trailing whitespace (including newlines) is stripped, but
this can be turned off.)

In this example corpus, we have a single record (starting with the
`\ref` marker), with text (`\t`), morphemes (`\m`), glosses (`\g`),
a free translation (`\f`), and a literal translation (`\l`).
Furthermore, the interlinear lines have been wrapped (perhaps from
Toolbox itself). Below I show how the `toolbox` module can handle these
kinds of examples.

## Extra Features

Beyond simply reading Toolbox files, the `toolbox` module can perform
some analysis of the data.

### Iterating over records based on keys

A Toolbox corpus file contains groups of (marker, text) pairs for
representing linguistic examples, called "records". Records are
delimited by certain markers (called, "record markers"), and there may
be more than one of such markers (e.g. `\ref` for each record, and
`\id` for grouping records into a text, etc.). The `records()` function
can automatically group the data in each record and keep track of the
context of the record markers previously seen. Here is how one might
read a corpus file with a `\id` key for a text (sub-corpus) and a `\ref`
key for each record.

```python
>>> pairs = toolbox.read_toolbox_file(open('example/corpus.txt'))
>>> for (context, data) in toolbox.records(pairs, ['\\id', '\\ref']):
...     print(sorted(context.items()))
...     print('\n'.join(map(repr, data)))
[('\\id', None), ('\\ref', 'item1')]
('\\t', 'O        Pedro baixou')
('\\m', 'O        Pedro bai   -xou')
('\\g', 'the.M.SG Pedro lower -PST.IND.3SG')
('\\t', 'a        bola')
('\\m', 'a        bola')
('\\g', 'the.F.SG ball.F.SG')
('\\f', 'Pedro calmed down.')
('\\l', 'Pedro lowered the ball.')

```

Note that there were no `\id` markers in the corpus file, so the value
is `None`.

### Normalizing tiers

Some toolbox data are line-wrapped, but logically the wrapped lines
continue where the first one stopped. Working with line-wrapped data
just makes things harder, so the `normalize_record()` function will
restore them to a single line per marker. As the function name implies,
this works on a record rather than file contents, so it may take the
results of the `records()` function. The second parameter to
`normalize_item()` is a container of markers for lines that should still
be visually aligned in columns after normalization.

```python
>>> pairs = toolbox.read_toolbox_file(open('example/corpus.txt'))
>>> records = toolbox.records(pairs, ['\\id', '\\ref'])
>>> rec1 = next(records)
>>> for mkr, val in toolbox.normalize_record(rec1[1], ['\\t', '\\g', '\\m']):
...     print((mkr, val))
('\\t', 'O        Pedro baixou             a        bola')
('\\m', 'O        Pedro bai   -xou         a        bola')
('\\g', 'the.M.SG Pedro lower -PST.IND.3SG the.F.SG ball.F.SG')
('\\f', 'Pedro calmed down.')
('\\l', 'Pedro lowered the ball.')

```

### Aligning fields

Toolbox encodes token alignments implicitly through spacing such that
aligned tokens appear visually in columns. The `toolbox` module provides
an `align_fields()` function to analyze the columns and return a more
explicit representation of the alignments. The function takes a list of
marker-text pairs and a marker-to-marker mapping to describe the
alignments. The result is a list of (marker, aligned_data) pairs, where
*aligned_data* is a list of (token, aligned_tokens).

```python
>>> pairs = toolbox.read_toolbox_file(open('example/corpus.txt'))
>>> records = toolbox.records(pairs, ['\\id', '\\ref'])
>>> rec1 = next(records)
>>> normdata = toolbox.normalize_record(rec1[1], ['\\t', '\\g', '\\m'])
>>> alignments = {'\\m': '\\t', '\\g': '\\m'}
>>> for mkr, algns in toolbox.align_fields(normdata, alignments=alignments):
...     print((mkr, algns))  # doctest: +NORMALIZE_WHITESPACE
('\\t', [('O        Pedro baixou             a        bola',
          ['O', 'Pedro', 'baixou', 'a', 'bola'])])
('\\m', [('O', ['O']),
         ('Pedro', ['Pedro']),
         ('baixou', ['bai', '-xou']),
         ('a', ['a']),
         ('bola', ['bola'])])
('\\g', [('O', ['the.M.SG']),
         ('Pedro', ['Pedro']),
         ('bai', ['lower']),
         ('-xou', ['-PST.IND.3SG']),
         ('a', ['the.F.SG']),
         ('bola', ['ball.F.SG'])])
('\\f', [(None, ['Pedro calmed down.'])])
('\\l', [(None, ['Pedro lowered the ball.'])])

```

## Examples and testing

The examples in this README file and in the [`tests.md`](tests.md) file
can be run as unit tests, while at the same time serving as useful
documentation. To run them as unit tests, do this from the command line:

```bash
python3 -m doctest README.md tests.md
```

## Acknowledgments

This project is partially supported by the Affectedness project, under
the Singapore Ministry of Education Tier 2 grant (grant number
MOE2013-T2-1-016).
