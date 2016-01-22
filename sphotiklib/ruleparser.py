import re
import logging
import itertools
from pkgutil import get_data
from os.path import join as pjoin

from .tree import TreeNode
from .conjunctor import Conjunctor
from .vowelshaper import Vowelshaper
from .utils import SrcBead, DstBead, Cord
from .transliterator import Transliterator
from .contextual_modifier import ContextualModifier
from .conjunction_parser import parse_conjunction_line


class Rule:
    MODIFIER_FILE = 'modifier.txt'
    MODIFIER_MARK = '[MOD]'
    HASH_MARK = '[HASH]'
    TRANSLITERATIONS_FILE = 'transliterations.txt'
    VOWELMAP_FILE = 'vowelmap.txt'
    CONSONANTS_FILE = 'consonants.txt'
    VOWELHOSTS_FILE = 'vowelhosts.txt'
    PUNCTUATIONS_FILE = 'punctuations.txt'
    CONJUNCTIONS_FILE = 'conjunctions.txt'
    CONJUNCTION_GLUE_FILE = 'conjunction_glue.txt'
    CONTEXTUAL_RULES_FILE = 'contextual_rules.txt'

    def __init__(self, rulename):
        ruledir = pjoin('rules', rulename)

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

        self.contextual_rules = []

        fdata = get_data(
            __package__, pjoin(ruledir, self.MODIFIER_FILE)).decode()
        self.modifier = self._parse_char(fdata)

        fdata = get_data(
            __package__, pjoin(ruledir, self.TRANSLITERATIONS_FILE)).decode()
        for k, v in self._parse_transliterations(fdata, self.modifier).items():
            self.transtree.set_value_for_path(list(k), v)

        fdata = get_data(
            __package__, pjoin(ruledir, self.VOWELMAP_FILE)).decode()
        self.vowelmap = self._parse_vowelmap(fdata)
        self.vowels_distinct = set(self.vowelmap.keys())
        self.vowels_diacritic = set(filter(
            lambda x: len(x), self.vowelmap.values()))
        self.vowels = self.vowels_distinct.union(self.vowels_diacritic)

        fdata = get_data(
            __package__, pjoin(ruledir, self.CONSONANTS_FILE)).decode()
        self.consonants = self._parse_chardump(fdata)

        fdata = get_data(
            __package__, pjoin(ruledir, self.VOWELHOSTS_FILE)).decode()
        self.vowelhosts = self._parse_chardump(fdata)

        fdata = get_data(
            __package__, pjoin(ruledir, self.PUNCTUATIONS_FILE)).decode()
        self.punctuations = self._parse_chardump(fdata)

        fdata = get_data(
            __package__, pjoin(ruledir, self.CONJUNCTIONS_FILE)).decode()
        for k in self._parse_conjunctions(fdata):
            self.conjtree.set_value_for_path(list(k), True)

        fdata = get_data(
            __package__, pjoin(ruledir, self.CONJUNCTION_GLUE_FILE)).decode()
        self.conjglue = self._parse_char(fdata)

        fdata = get_data(
            __package__, pjoin(ruledir, self.CONTEXTUAL_RULES_FILE)).decode()
        self.contextual_rules = self._parse_contextual_rules(fdata)

        self.transliterator = Transliterator(
            self.transtree,
                ContextualModifier(
                    self.contextual_rules, self.vowels, self.consonants))
        self.vowelshaper = Vowelshaper(self.vowels, self.vowelhosts)
        self.conjunctor = Conjunctor(self.conjtree)

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
            "\n\tcontextual_rules:\n\t\t" +
            "\n\t\t".join(map(str, self.contextual_rules)))

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
            # Unescape literal hash sign.
            parts = [x.replace(self.HASH_MARK, '#') for x in parts]
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

    def _parse_contextual_rules(self, text):
        rules = []

        for line in text.splitlines():
            line = line.strip()

            if not line or line.startswith('#'):
                continue

            try:
                conv, raw, result = line.split('#', maxsplit=2)
            except ValueError:
                conv, raw = line.split('#', maxsplit=1)
                result = ''

            rules.append((
                tuple(conv.split()),
                ''.join(raw.split()),
                tuple(result.split())))

        return rules


if __name__ == '__main__':
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    rule = Rule('avro')
