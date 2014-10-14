
import os.path
from os import listdir
import re
from collections import OrderedDict, deque, Sequence
import logging

default_tokenizer = re.compile(r'\S+\s*')

class ToolboxError(Exception): pass
class ToolboxInitError(ToolboxError): pass

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


toolbox_line_re = re.compile(r'(?P<mkr>\\[^\s]+)( (?P<val>.*\n?))?$')

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
        val = ''.join([s or '' for s in val_lines])  # first s might be None
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


def iterparse(pairs, keys):
    """
    Yield pairs of (event, result) based on `keys` for the given
    `pairs`. Events and associated results are given below:

    =====  =============================================
    event                     result
    =====  =============================================
    key    the (key, value) pair for when \key was seen
    start  the (key, value) pair for when \+key was seen
    end    the (key, value) pair for when \-key was seen
    data   list of (marker, value) pairs between keys
    =====  =============================================

    Args:
        pairs: An iterable of (marker, value) pairs.
        keys: A container of markers that delimit blocks of associated
              data.
    Yields:
        Pairs of (event, result).
    """
    start_keys = set(re.sub(r'\\(.*)', r'\+\1', k) for k in keys)
    end_keys = set(re.sub(r'\\(.*)', r'\-\1', k) for k in keys)
    all_keys = set(keys).union(start_keys, end_keys)
    data = []
    for mkr, val in pairs:
        if mkr in all_keys:
            if len(data) > 0:
                yield ('data', data)
                data = []
            if mkr in keys:
                yield ('key', (mkr, val))
            elif mkr in start_keys:
                yield ('start', ('\\{}'.format(mkr[2:]), val))
            elif mkr in end_keys:
                yield ('end', ('\\{}'.format(mkr[2:]), val))
        else:
            data.append((mkr, val))
    # don't forget to yield the last one
    if len(data) > 0:
        yield ('data', data)


def records(pairs, record_marker, context_keys=None):
    """
    An alternative parsing function to iterparse(), which yields pairs
    of (context, data), where context is a dictionary mapping each key
    to the previously seen value, and data is the list of
    (marker, value) pairs delimited by the keys. The basic usage is:

        records(pairs, '\\ref')

    Where `'\\ref'` is the delimiter of records in `pairs`.

    Args:
        pairs: An iterable of (marker, value) pairs.
        record_marker: The marker(s) that delimits records. If the
            value is a string, it is considered the only record
            marker. Any other Sequence (list, tuple, etc.) become an
            ordered hierarchy of record delimiters. When a higher
            marker is encountered, it resets the value of the lower
            markers to None. For instance, if ['\\id', '\\ref'] is
            used, '\\ref' is reset to None whenever '\\id' is
            encountered.
        context_keys: A container of additional delimiters to include
            in the context, but unlike `record_marker`, these do not
            reset other markers. E.g. one might use \\page to group
            elements in a section that spans several pages.
    Yields:
        Pairs of (context, data)
    Raises:
        ToolboxError when block-start markers (\\+key) or block-end
        markers (\\-key) are seen, as they are considered invalid
        within records.
    """
    if isinstance(record_marker, str):
        record_marker = [record_marker]
    if not isinstance(record_marker, Sequence):
        raise ToolboxError('Record marker must be a string or a sequence.')
    keys = set(record_marker).union(context_keys or [])
    context = dict((key, None) for key in keys)
    for event, result in iterparse(pairs, keys):
        if event == 'key':
            mkr, val = result
            try:
                idx = record_marker.index(mkr)
                for m in record_marker[idx:]:
                    context[m] = None
            except ValueError:
                pass
            context[mkr] = val
        elif event == 'data':
            yield (context, result)
        else:
            raise ToolboxError('Illegal event in record: {}'
                               .format(event, result))


def field_groups(pairs, aligned_fields):
    """
    Yield lists of (marker, value) pairs where all pairs in the list
    are aligned. Unaligned fields will be returned as the only pair in
    the list, and repeating groups (e.g. where they are wrapped) will
    be returned separately.
    """
    group = []
    seen = set()
    for mkr, val in pairs:
        # unaligned or repeated fields start over grouping
        if mkr not in aligned_fields or mkr in seen:
            if group:
                yield group
            group = []
            seen = set()
            if mkr not in aligned_fields:
                yield [(mkr, val)]
                continue
        group.append((mkr, val))
        seen.add(mkr)
    # yield the last group if non-empty
    if group:
        yield group


def normalize_record(pairs, aligned_fields, strip=True):
    """
    Return a list of pairs of (marker, value) from `pairs`, where values
    with the same marker are recombined (i.e. unwrapped). If the marker
    is in `aligned_fields`, spacing will also be normalized (taking the
    length of the longest token) so that the tokens still align visually
    in columns.

    Args:
        pairs: An iterable of (marker, value) pairs.
        aligned_fields: A container of markers that are aligned.
    Return:
        The list of pairs with aligned fields normalized.

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
    >>> for (mkr, val) in normalize_record(data, set(['\\t', \\g', '\\m'])):
    ...     print(mkr, val)
    \t inu=ga   ippiki           hoeru
    \m inu =ga  ichi -hiki       hoe  -ru
    \g dog =NOM one  -CLF.ANIMAL bark -IPFV
    \f One dog barks.
    """
    field_data = OrderedDict()
    # gather lines with the same marker, and keep track of the longest
    # aligned fields at each position
    maxlens = {}
    for mkr, val in pairs:
        if mkr not in field_data:
            field_data[mkr] = []
        if val is None:
            continue
        field_data[mkr].append(val)
        i = len(field_data[mkr]) - 1
        # this string length counts unicode combining characters, so
        # the lengths may appear off when printed
        if mkr in aligned_fields and len(val) > maxlens.get(i, -1):
            maxlens[i] = len(val)
    # join and normalize spacing (use longest length for each position)
    mkrs = list(field_data.keys())
    for mkr in mkrs:
        data = field_data[mkr]
        if data == []:
            joined = None
        elif mkr in aligned_fields:
            joined = ' '.join(s.ljust(maxlens[i]) for i, s in enumerate(data))
        else:
            joined = ' '.join(data)
        if strip and joined is not None:
            joined = joined.rstrip()
        field_data[mkr] = joined
    return list(field_data.items())


def align_fields(pairs, alignments=None, tokenizers=None, errors='strict'):
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
            original value of the field. If `tokenizers` is None or a
            tokenizer regex is not given for a marker, and the marker is
            the source or target of an alignment, the values will be
            split by whitespace.
        errors: If 'strict', errors during alignment will be raised.
            Otherwise they will be ignored.

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
    ...     ('\\t', 'inu=ga   ippiki           hoeru     '),
    ...     ('\\m', 'inu =ga  ichi -hiki       hoe  -ru  '),
    ...     ('\\g', 'dog =NOM one  -CLF.ANIMAL bark -IPFV'),
    ...     ('\\f', 'One dog barks.'),
    ...     ('\\x', None)
    ... ]
    >>> align_fields(data, alignments={'\\m': '\\t', '\\g': '\\m'})
    [('\\t', [('inu=ga   ippiki           hoeru     ',
               ['inu=ga', 'ippiki', 'hoeru'])]),
     ('\\m', [('inu=ga', ['inu', '=ga']),
              ('ippiki', ['ichi', '-hiki']),
              ('hoeru', ['hoe', '-ru'])]),
     ('\\g', [('inu', ['dog']),
              ('=ga', ['=NOM']),
              ('ichi', ['one']),
              ('-hiki' ['-CLF.ANIMAL']),
              ('hoe', ['bark']),
              ('-ru', ['-IPFV'])]),
     ('\\f', [(None, ['One dog barks.'])]),
     ('\\x', [(None, None)])
    ]
    """
    aligned_fields = set(alignments.keys()).union(alignments.values())
    alignments = dict(alignments or [])
    tokenizers = dict(tokenizers or [])
    prev = {}  # previous tokenization matches used for alignment
    aligned_pairs = []
    for mkr, val in pairs:
        tokenizer = tokenizers.get(mkr, default_tokenizer)
        # empty content
        if val is None:
            aligned_pairs.append((mkr, [(None, None)]))
        # unaligned fields; don't do any tokenization
        elif mkr not in aligned_fields:
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
                aligned = _collect_aligned_tokens(toks, tgt_toks, marker=mkr)
                aligned_pairs.append((mkr, aligned))
    return aligned_pairs


def _collect_aligned_tokens(src, tgt, marker=None, errors='strict'):
    # make a deque so we can efficiently pop from the front; also this
    # makes a copy of src so we don't affect the original
    src = deque(src)
    tgt = list(tgt)
    last_tgt_idx = len(tgt) - 1
    last_end = -1  # the end pos of the last source token
    aligned = []
    for i, t in enumerate(tgt):
        if last_end > t.start():
            if errors == 'strict':
                raise ToolboxError(
                    'Possible misalignment of field {} at position {}.'
                    .format(marker or '???', t.start()),
                )
        remaining = last_tgt_idx - i
        t_end = t.end()
        grp = []
        while src and (remaining == 0 or src[0].start() < (t_end)):
            s = src.popleft()
            s_tok = s.group(0).rstrip()
            last_end = s.start() + len(s_tok)  # .end() doesn't always work
            grp.append(s_tok)
        aligned.append((t.group(0).rstrip(), grp))
    return aligned


class ToolboxProject(object):
    def __init__(self, path):
        self.path = find_project_file(path)
        self.alignments = {}
        self.initialize()

    def initialize(self):
        pass
