import re
import logging
import itertools
from os.path import join as pjoin

from tree import TreeNode
from utils import SrcBead, DstBead, Cord
from conjunction_parser import parse_conjunction_line


class Rule:
    MODIFIER_FILE = 'modifier.txt'
    MODIFIER_MARK = '[MOD]'
    TRANSLITERATIONS_FILE = 'transliterations.txt'
    VOWELMAP_FILE = 'vowelmap.txt'
    CONSONANTS_FILE = 'consonants.txt'
    VOWELHOSTS_FILE = 'vowelhosts.txt'
    PUNCTUATIONS_FILE = 'punctuations.txt'
    CONJUNCTIONS_FILE = 'conjunctions.txt'
    CONJUNCTION_GLUE_FILE = 'conjunction_glue.txt'
    SPECIAL_RULES_FILE = 'special_rules.txt'

    def __init__(self, ruledir):
        self.ruledir = ruledir

        self.transtree = TreeNode(key='root', parent=None)

        self.modifier = None

        self.vowelmap = {}
        self.vowels = set()
        self.vowels_distinct = set()
        self.vowels_diacritic = set()

        self.conjtree = TreeNode(key='root', parent=None)
        self.conjglue = None

        self.consonants = set()
        self.vowelhosts = set()
        self.punctuations = set()

        self.special_rules = []

        with open(pjoin(ruledir, self.MODIFIER_FILE)) as f:
            self.modifier = self._parse_char(f.read())

        with open(pjoin(ruledir, self.TRANSLITERATIONS_FILE)) as f:
            for k, v in self._parse_transliterations(
                    f.read(), self.modifier).items():
                self.transtree.set_value_for_path(list(k), v)

        with open(pjoin(ruledir, self.VOWELMAP_FILE)) as f:
            self.vowelmap = self._parse_vowelmap(f.read())
            self.vowels_distinct = set(self.vowelmap.keys())
            self.vowels_diacritic = set(filter(
                lambda x: len(x), self.vowelmap.values()))
            self.vowels = self.vowels_distinct.union(self.vowels_diacritic)

        with open(pjoin(ruledir, self.CONSONANTS_FILE)) as f:
            self.consonants = self._parse_chardump(f.read())

        with open(pjoin(ruledir, self.VOWELHOSTS_FILE)) as f:
            self.vowelhosts = self._parse_chardump(f.read())

        with open(pjoin(ruledir, self.PUNCTUATIONS_FILE)) as f:
            self.punctuations = self._parse_chardump(f.read())

        with open(pjoin(ruledir, self.CONJUNCTIONS_FILE)) as f:
            for k in self._parse_conjunctions(f.read()):
                self.conjtree.set_value_for_path(list(k), True)

        with open(pjoin(ruledir, self.CONJUNCTION_GLUE_FILE)) as f:
            self.conjglue = self._parse_char(f.read())

        with open(pjoin(ruledir, self.SPECIAL_RULES_FILE)) as f:
            self.special_rules = self._parse_special_rules(f.read())

        logging.debug(
            "Parsed rules from '{}':\n\t".format(ruledir) +
            "\n\t".join(
                map(
                    lambda x: "{}: {}".format(
                        x,
                        getattr(
                            self,
                            x)),
                    ("vowels",
                     "vowels_distinct",
                     "vowels_diacritic",
                     "vowelhosts",
                     "consonants",
                     "punctuations",
                     "conjglue",
                     "vowelmap",
                     ))) +
            "\n\tconjtree:\n\t\t" +
            "\n\t\t".join(
                str(
                    self.conjtree).splitlines()) +
            "\n\ttranstree:\n\t\t" +
            "\n\t\t".join(
                str(
                    self.transtree).splitlines()) +
            "\n\tspecial_rules:\n\t\t" +
            "\n\t\t".join(map(str, self.special_rules)))

    _ESCAPED_UNICHAR_REGEX = re.compile(r'\\u[0-9A-F]{4}', re.I)

    def _unescape_unichar(self, text):
        def replace(matchobj):
            return chr(int(matchobj.group(0)[2:], 16))
        return re.sub(self._ESCAPED_UNICHAR_REGEX, replace, text)

    def _parse_char(self, text):
        return self._unescape_unichar(''.join(filter(
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

    def _parse_transliterations(self, text, modifier):
        transmap = {}

        # Replace any modifier mark with the modifier char.
        text = text.replace(self.MODIFIER_MARK, modifier)

        for line in text.splitlines():
            line = line.strip()

            # Ignore empty lines and comments.
            if not line or line.startswith('#'):
                continue

            parts = line.split('#', maxsplit=2)
            src = parts[0]
            dst = parts[1] if len(parts) > 1 else ''
            flags = parts[2] if len(parts) > 2 else ''

            srcfrags = list(map(self._unescape_unichar, src.split()))
            dstfrags = list(map(self._unescape_unichar, dst.split()))
            flaglist = list(filter(
                lambda x: x, map(str.strip, flags.split('|'))))

            for sf in srcfrags:
                srcbead = SrcBead(sf)
                dstcord = Cord([
                    DstBead(v, srcbead, flaglist) for v in dstfrags])
                transmap[sf] = dstcord

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

            src = self._unescape_unichar(src)
            dst = self._unescape_unichar(dst)

            vowelmap[src] = dst

        return vowelmap

    def _parse_chardump(self, text):
        chars = set()

        for line in text.splitlines():
            line = line.strip()

            if not line or line.startswith('#'):
                continue

            chars.update(map(self._unescape_unichar, line.split()))

        return chars

    def _parse_special_rules(self, text):
        rules = []

        for line in text.splitlines():
            line = line.strip()

            if not line or line.startswith('#'):
                continue

            try:
                src, dst = line.split('#', maxsplit=1)
            except ValueError:
                src, dst = line, ''

            rules.append((tuple(src.split()), tuple(dst.split())))

        return rules


if __name__ == '__main__':
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    rule = Rule('avro_rule')
