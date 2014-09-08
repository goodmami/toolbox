
import os.path
from os import listdir
import re
from collections import OrderedDict, deque
import logging

class ToolboxException(Exception): ...
class ToolboxInitError(ToolboxException): ...

def find_project_file(path):
    proj_path = None
    if os.path.isfile(path):
        if path.lower().endswith('.prj'):
            proj_path = path
    elif os.path.isdir(path):
        fns = [fn for fn in listdir(path) if fn.lower().endswith('.prj')]
        if len(fns) == 1:
            proj_path = fns[0]
    if proj_path is None:
        raise ToolboxInitError(
            'Toolbox project file not found at {}.'.format(path)
        )
    return proj_path


toolbox_line_re = re.compile(r'(?P<mkr>\\[^\s]+)( (?P<val>.*))?$')

# inspired by the NLTK's implementation:
#   http://www.nltk.org/_modules/nltk/toolbox.html
def read_toolbox_file(f, strip=True):
    """
    Parse a Toolbox file and yield pairs of (marker, value). By default,
    no interpretation or normalization of the data is done besides
    stripping the trailing whitespace of each value (set the `strip`
    parameter to False to leave whitespace on).

    Args:
        f: An open file-like object.
        strip: If True, strip trailing whitespace from each value.
    Yields:
        Pairs of (marker, value)
    """
    def make_val(val_lines, strip):
        if val_lines == [None]:
            return None
        val = '\n'.join([s or '' for s in val_lines])  # first s might be None
        if strip:
            val = val.rstrip()
        return val
    mkr = None
    val_lines = []
    for line in f:
        mkr_match = toolbox_line_re.match(line)
        if mkr_match is not None:
            # first yield the current pair
            if mkr is not None:
                yield (mkr, make_val(val_lines, strip))
            mkr = mkr_match.group('mkr')
            val_lines = [mkr_match.group('val')]
        else:
            val_lines.append(line)
    # when we reach the end of the file, yield the final pair
    if mkr is not None:
        yield (mkr, make_val(val_lines, strip))


def item_iter(pairs, keys=None):
    """
    Yield pairs of (event, result) based on `keys` for the given
    `pairs`. Events are either `key` or `item`. If the event is `key`,
    the result is a pair of (marker, value) where the marker is the key
    that was matched. If the event is `item`, the result is a list of
    all pairs of (marker, value) that occur between one key and the
    next.

    Args:
        pairs: An iterable of (marker, value) pairs.
        keys: A container of markers that delimit items.
    Yields:
        Pairs of (event, result).
    """
    data = []
    for mkr, val in pairs:
        if mkr in (keys):
            if len(data) > 0:
                yield ('item', data)
                data = []
            yield ('key', (mkr, val))
        else:
            data.append((mkr, val))
    # don't forget to yield the last one
    if len(data) > 0:
        yield ('item', data)


def normalize_item(pairs, aligned_tiers):
    """
    Return a list of pairs of (marker, value) from `pairs`, where values
    with the same marker are recombined (i.e. unwrapped). If the marker
    is in `aligned_tiers`, spacing will also be normalized (taking the
    length of the longest token) so that the tokens still align visually
    in columns.

    Args:
        pairs: An iterable of (marker, value) pairs.
        aligned_tiers: A container of markers that are aligned.
    Return:
        The list of pairs with aligned tiers normalized.

    Example:

    >>> data = [
    ...     ('\\t', 'inu=ga   ippiki'),
    ...     ('\\m', 'inu =ga  ichi -hiki'),
    ...     ('\\g', 'dog =NOM one  -CLF.ANIMAL'),
    ...     ('\\t', 'hoeru'),
    ...     ('\\m', 'hoe  -ru'),
    ...     ('\\g', 'bark -IPFV'),
    ...     ('\\f', 'One dog barks.')
    ... ]
    >>> for (mkr, val) in normalize_item(data, set(['\\t', \\g', '\\m'])):
    ...     print(mkr, val)
    \t inu=ga   ippiki           hoeru
    \m inu =ga  ichi -hiki       hoe  -ru
    \g dog =NOM one  -CLF.ANIMAL bark -IPFV
    \f One dog barks.
    """
    tier_data = OrderedDict()
    # gather lines with the same marker, and keep track of the longest
    # aligned tiers at each position
    maxlens = {}
    for mkr, val in pairs:
        if mkr not in tier_data:
            tier_data[mkr] = []
        if val is None:
            continue
        tier_data[mkr].append(val)
        i = len(tier_data[mkr]) - 1
        # this string length counts unicode combining characters, so
        # the lengths may appear off when printed
        if mkr in aligned_tiers and len(val) > maxlens.get(i, -1):
            maxlens[i] = len(val)
    # join and normalize spacing (use longest length for each position)
    mkrs = list(tier_data.keys())
    for mkr in mkrs:
        data = tier_data[mkr]
        if data == []:
            joined = None
        elif mkr in aligned_tiers:
            joined = ' '.join(s.ljust(maxlens[i]) for i, s in enumerate(data))
        else:
            joined = ' '.join(data)
        tier_data[mkr] = joined
    return list(tier_data.items())


default_tokenizer = re.compile(r'\S+\s*')

def align_tiers(pairs, alignments=None, tokenizers=None):
    """
    Align source to target tokens for each line in `pairs` using
    alignment mappings given in `alignments`. Line values are tokenized
    by whitespace by default, but can be handled specially by giving a
    custom tokenizer in `tokenizers`.

    Args:
        pairs: An iterable of (marker, value) pairs
        alignments: A dictionary of {marker1: marker2} alignments, where
            marker1 is aligned to marker2. If `alignments` is None, each
            value will still be put in a list as the only item with an
            alignment target of None.
        tokenizers: A dictionary of {marker: regex}, where the compiled
            regular expression `regex` is used to find sub-parts of the
            original value of the tier. If `tokenizers` is None or a
            tokenizer regex is not given for a marker, and the marker is
            the source or target of an alignment, the values will be
            split by whitespace.

    Returns:
        A list of alignment pairs. Each alignment pair is a structure
        (marker, [(target_token, [source_tokens])]). That is, for each
        target token, a list of source tokens is aligned to it. For
        unaligned lines, the target token is None and the source tokens
        has the original line as the only list item. Lines that are a
        target but not source of any alignment have their own
        untokenized line as the target token. If the value of a line is
        None (e.g. there was a marker but no content), then both the
        target_token and the source_tokens will be None, even if the
        line should have been aligned to something.

    Example:

    >>> data = [
    ...     ('\\t', 'inu=ga   ippiki           hoeru'),
    ...     ('\\m', 'inu =ga  ichi -hiki       hoe  -ru'),
    ...     ('\\g', 'dog =NOM one  -CLF.ANIMAL bark -IPFV'),
    ...     ('\\f', 'One dog barks.'),
    ...     ('\\x', None)
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
     ('\\x', [(None, None)])
    ]
    """
    aligned_tiers = set(alignments.keys()).union(alignments.values())
    alignments = dict(alignments or [])
    tokenizers = dict(tokenizers or [])
    prev = {}  # previous tokenization matches used for alignment
    aligned_pairs = []
    for mkr, val in pairs:
        tokenizer = tokenizers.get(mkr, default_tokenizer)
        # empty content
        if val is None:
            aligned_pairs.append((mkr, [(None, None)]))
        # unaligned tiers; don't do any tokenization
        elif mkr not in aligned_tiers:
            aligned_pairs.append((mkr, [(None, [val])]))
        else:
            toks = list(tokenizer.finditer(val))
            prev[mkr] = toks
            # target, but not source, of alignments; just tokenize
            if mkr not in alignments:
                aligned_pairs.append(
                    (mkr, [(val, [t.group(0).rstrip() for t in toks])])
                )
            # source of an alignment; tokenize and align
            else:
                tgt_toks = prev.get(alignments[mkr])
                if tgt_toks is None:
                    logging.warning(
                        'Alignment target {} must precede source {}.'
                        .format(alignments[mkr], mkr)
                    )
                    continue
                aligned = _collect_aligned_tokens(toks, tgt_toks)
                aligned_pairs.append((mkr, aligned))
    return aligned_pairs


def _collect_aligned_tokens(src, tgt):
    # make a deque so we can efficiently pop from the front; also this
    # makes a copy of src so we don't affect the original
    src = deque(src)
    aligned = []
    for t in tgt:
        grp = [s.group(0).rstrip() for s in src
               if s.start() >= t.start() and s.start() < t.end()]
        # get rid of them for efficiency's sake
        for g in grp:
            src.popleft()
        aligned.append((t.group(0).rstrip(), grp))
    return aligned


class ToolboxProject(object):
    def __init__(self, path):
        self.path = find_project_file(path)
        self.alignments = {}
        self.initialize()

    def initialize(self):
        pass