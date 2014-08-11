
import os.path
from os import listdir
import re

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


toolbox_line_re = re.compile(r'(?P<mkr>\\[^\s]+)(\s|$)(?P<val>.*)$')

# inspired by the NLTK's implementation:
#   http://www.nltk.org/_modules/nltk/toolbox.html
def open_toolbox_file(f, strip=True):
    """
    Parse a Toolbox file and yield pairs of (marker, value).

    Args:
        f: An open file-like object
    """
    def make_val(val_lines):
        return '\n'.join(val_lines).rstrip()
    mkr = None
    val_lines = []
    for line in f:
        mkr_match = toolbox_line_re.match(line)
        if mkr_match is not None:
            # first yield the current pair
            if mkr is not None:
                yield (mkr, make_val(val_lines))
            mkr = mkr_match.group('mkr')
            val_lines = [mkr_match.group('val')]
        else:
            val_lines.append(line)
    # when we reach the end of the file, yield the final pair
    if mkr is not None:
        yield (mkr, make_val(val_lines))


class ToolboxProject(object):
    def __init__(self, path):
        self.path = find_project_file(path)
        self.initialize()

    def initialize(self):
        pass