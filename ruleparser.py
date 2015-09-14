import re
import logging
import itertools
from os.path import join as pjoin

from tree import TreeNode
from conjunction_parser import parse_conjunction_line


_ESCAPED_UNICHAR_REGEX = re.compile(r'\\u[0-9A-F]{4}', re.I)


def _unescape_unichar(text):
    def replace(matchobj):
        return chr(int(matchobj.group(0)[2:], 16))

    return re.sub(_ESCAPED_UNICHAR_REGEX, replace, text)


class Rule:
    TRANSLITERATIONS_FILE = 'transliterations.txt'
    VOWELMAP_DIST2DIAC_FILE = 'vowelmap_dist2diac.txt'
    VOWELMAP_DIAC2DIST_FILE = 'vowelmap_diac2dist.txt'
    CONSONANTS_FILE = 'consonants.txt'
    VOWELHOSTS_FILE = 'vowelhosts.txt'
    PUNCTUATIONS_FILE = 'punctuations.txt'
    CONJUNCTIONS_FILE = 'conjunctions.txt'
    CONJUNCTION_GLUE_FILE = 'conjunction_glue.txt'

    def __init__(self, ruledir):
        self.ruledir = ruledir

        self.transtree = TreeNode(key='root', parent=None)

        self.vowelmap_dist2diac = {}
        self.vowelmap_diac2dist = {}

        self.conjtree = TreeNode(key='root', parent=None)
        self.conjglue = None

        self.consonants = set()
        self.vowelhosts = set()
        self.vowels = set()
        self.punctuations = set()
        self.vowels_distinct = set()
        self.vowels_diacritic = set()

        with open(pjoin(ruledir, self.TRANSLITERATIONS_FILE)) as f:
            for k, v in self._parse_transliterations(f.read()).items():
                self.transtree.set_value_for_path(list(k), v)

        with open(pjoin(ruledir, self.VOWELMAP_DIST2DIAC_FILE)) as f:
            self.vowelmap_dist2diac = self._parse_vowelmap(f.read())

        with open(pjoin(ruledir, self.VOWELMAP_DIAC2DIST_FILE)) as f:
            self.vowelmap_diac2dist = self._parse_vowelmap(f.read())

        with open(pjoin(ruledir, self.CONSONANTS_FILE)) as f:
            self.consonants = self._parse_consonants(f.read())

        with open(pjoin(ruledir, self.VOWELHOSTS_FILE)) as f:
            self.vowelhosts = self._parse_vowelhosts(f.read())

        with open(pjoin(ruledir, self.PUNCTUATIONS_FILE)) as f:
            self.punctuations = self._parse_punctuations(f.read())

        with open(pjoin(ruledir, self.CONJUNCTIONS_FILE)) as f:
            for k in self._parse_conjunctions(f.read()):
                self.conjtree.set_value_for_path(list(k), True)

        with open(pjoin(ruledir, self.CONJUNCTION_GLUE_FILE)) as f:
            self.conjglue = self._parse_conjunction_glue(f.read())

        self.vowels_distinct = set(self.vowelmap_dist2diac.keys())
        self.vowels_diacritic = set(self.vowelmap_diac2dist.keys())
        self.vowels = self.vowels_distinct.union(self.vowels_diacritic)

        logging.debug(
            "Parsed rules from '{}':\n\t".format(ruledir) +
            "\n\t".join(map(
                lambda x: "{}: {}".format(x, getattr(self, x)), (
                    "vowels",
                    "vowels_distinct",
                    "vowels_diacritic",
                    "vowelhosts",
                    "consonants",
                    "punctuations",
                    "vowelmap_dist2diac",
                    "vowelmap_diac2dist",
                    "conjglue",
                    "conjtree",
                    "transtree",
                ),
            ))
        )

    def _parse_conjunction_glue(self, text):
        return _unescape_unichar(''.join(filter(
            lambda x: not x.startswith('#'),
            map(str.strip, text.splitlines())
        ))).strip()

    def _parse_conjunctions(self, text):
        conjs = set()
        for line in text.splitlines():
            line = line.strip()

            if not line or line.startswith('#'):
                continue

            conjs.update(parse_conjunction_line(line))

        return conjs

    def _parse_transliterations(self, text):
        transmap = {}

        for line in text.splitlines():
            line = line.strip()

            # Ignore empty lines and comments.
            if not line or line.startswith('#'):
                continue

            try:
                src, dst = line.split('#', maxsplit=1)
            except ValueError:
                src, dst = line, ''

            srcfrags = list(map(_unescape_unichar, src.split()))
            dstfrags = list(map(_unescape_unichar, dst.split()))

            for sf in srcfrags:
                transmap[sf] = dstfrags

        return transmap

    def _parse_vowelmap(self, text):
        vowelmap = {}

        for line in text.splitlines():
            line = line.strip()

            if not line or line.startswith('#'):
                continue

            try:
                src, dst = line.split(maxsplit=1)
            except ValueError:
                src, dst = line, ''

            src = _unescape_unichar(src)
            dst = _unescape_unichar(dst)

            vowelmap[src] = dst

        return vowelmap

    def _parse_chardump(self, text):
        chars = set()

        for line in text.splitlines():
            line = line.strip()

            if not line or line.startswith('#'):
                continue

            chars.update(map(_unescape_unichar, line.split()))

        return chars

    _parse_vowelhosts = _parse_consonants = _parse_punctuations = _parse_chardump


if __name__ == '__main__':
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    rule = Rule('avro_rule')
