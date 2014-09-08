# toolbox

Python implementation of [SIL's Toolbox](www.sil.org/computing/toolbox) format


## Basic Usage

The `toolbox` module currently supports the reading of Toolbox-formatted files. The basic format looks like this:

```
\mkr a line of text
```

Where `\mkr` is called a *marker* and is followed by a space, then one or more lines of text. The `read_toolbox_file()` function reads such a file and yields (marker, text) pairs:

```python3
>>> for mkr, text in read_toolbox_file(open('example.txt')):
...     print('Marker: {}\tText:{}'.format(mkr, text))
Marker: \mkr  Text: a line of text
```

By default, trailing whitespace (including newlines) is stripped, but this can be turned off.


## Extra Features

Beyond simply reading Toolbox files, the `toolbox` module can perform some analysis of the data.

### Iterating over groups based on keys

A Toolbox corpus file contains groups of (marker, text) pairs for representing linguistic examples. These examples are separated with special markers called keys. The `item_iter()` function can group marker-text pairs by one or more keys. The function itself returns pairs of (event, result), where *event* is `key` and *result* is the key itself if it encountered a key marker, or if *event* is `item` then *result* is the list of marker-text pairs included from the previous key. For example, here is how one might read a corpus file with a `\id` key for sub-corpora and a `\ref` key for each item.

```python3
>>> tb = toolbox.read_toolbox_file(open('example2.txt'))
>>> id_key = ref_key = None
>>> for (event, result) in toolbox.item_iter(tb, keys=set(['\\id', '\\ref'])):
...     if event == 'key':
...         mkr, val = result
...         if mkr == '\\ref':
...             ref_key = val
...         elif mkr == '\\id':
...             id_key = val
...             ref_key = None
...     elif event == 'item':
...         if ref is None:
...             continue  # this is not included in an item (e.g. header info)
...         print(result)
[('\\t', 'inu=ga   ippiki           hoeru'),
 ('\\m', 'inu =ga  ichi -hiki       hoe  -ru'),
 ('\\g', 'dog =NOM one  -CLF.ANIMAL bark -IPFV'),
 ('\\f', 'One dog barks.')
]
...
```

### Normalizing tiers

Some toolbox data are line-wrapped, but logically the wrapped lines continue where the first one stopped. Working with line-wrapped data just makes things harder, so the `normalize_item()` function will restore them to a single line per marker. As the function name implies, this works on an item rather than file contents, so it may take the item results of the `item_iter()` function. The second parameter to `normalize_item()` is a container of markers for lines that should still be visually aligned in columns after normalization.

```python3
>>> data = [
...     ('\\t', 'inu=ga   ippiki'),
...     ('\\m', 'inu =ga  ichi -hiki'),
...     ('\\g', 'dog =NOM one  -CLF.ANIMAL'),
...     ('\\t', 'hoeru'),
...     ('\\m', 'hoe  -ru'),
...     ('\\g', 'bark -IPFV'),
...     ('\\f', 'One dog barks.')
... ]
>>> for (mkr, val) in normalize_item(data, set(['\\t', '\\g', '\\m'])):
...     print(mkr, val)
\t inu=ga   ippiki           hoeru
\m inu =ga  ichi -hiki       hoe  -ru
\g dog =NOM one  -CLF.ANIMAL bark -IPFV
\f One dog barks.
```

### Aligning tiers

Toolbox encodes token alignments implicitly through spacing such that aligned tokens appear visually in columns. The `toolbox` module provides an `align_tiers()` function to analyze the columns and return a more explicit representation of the alignments. The function takes a list of marker-text pairs and a marker-to-marker mapping to describe the alignments. The result is a list of (marker, aligned_data) pairs, where *aligned_data* is a list of (token, aligned_tokens).

```python3
>>> data = [
...     ('\\t', 'inu=ga   ippiki           hoeru'),
...     ('\\m', 'inu =ga  ichi -hiki       hoe  -ru'),
...     ('\\g', 'dog =NOM one  -CLF.ANIMAL bark -IPFV'),
...     ('\\f', 'One dog barks.')
... ]
>>> align_tiers(data, alignments={'\\m': '\\t', '\\g': '\\m'})
[('\\t', [('inu=ga ippiki hoeru', ['inu=ga', 'ippiki', 'hoeru'])]),
 ('\\m', [('inu=ga', ['inu', '=ga']),
          ('ippiki', ['ichi', '-hiki']),
          ('hoeru', ['hoe', '-ru'])]),
 ('\\g', [('inu', ['dog']),
          ('=ga', ['=NOM']),
          ('ichi', ['one']),
          ('-hiki' ['-CLF.ANIMAL']),
          ('hoe', ['bark']),
          ('-ru, ['-IPFV'])]),
 ('\\f', [(None, ['One dog barks.'])])
]
