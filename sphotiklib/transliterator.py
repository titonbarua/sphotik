import operator
import unittest
from copy import deepcopy
from functools import reduce

from .tree import TreeNode
from .utils import SrcBead, DstBead, Cord


class Transliterator:

    def __init__(self, tree, contextual_modifier):
        self._tree = tree
        self._contextual_modifier = contextual_modifier
        self.longest_path_size = tree.longest_subpath_size

    def _transliterate_a_letter(self, raw):
        candidate = raw[:self.longest_path_size]
        while candidate:
            try:
                converted = self._tree.get_value_for_path(candidate)
                if converted is None:
                    candidate = candidate[:-1]
                    continue

                unconverted = raw[len(candidate):]
                return (deepcopy(converted), unconverted)

            except KeyError:
                candidate = candidate[:-1]
                continue
        else:
            # Couldn't find a successful transliteration, which
            # implies that the first character of the roman string
            # is not part of any transliteration.
            unconverted = raw[1:]
            converted = Cord([
                DstBead(raw[0], SrcBead(raw[0]))])
            return (converted, unconverted)

    def _transliterate(self, context, raw):
        conv = Cord()
        while True:
            partconv, raw = self._contextual_modifier(context + conv, raw)
            conv += partconv
            if len(raw) == 0:
                break

            partconv, raw = self._transliterate_a_letter(raw)
            conv += partconv
            if len(raw) == 0:
                break

        return conv

    def __call__(self, context, raw):
        return self._transliterate(context, raw)


class _TestTransliterator(unittest.TestCase):

    def setUp(self):
        def cc(s, d):
            """ A convenience function to create a single-beaded Cord."""
            return Cord([DstBead(d, SrcBead(s))])

        t = TreeNode("root")
        t.set_value_for_path("a", cc("a", "1"))
        t.set_value_for_path("aa", cc("aa", "2"))
        t.set_value_for_path("b", cc("b", "3"))
        t.set_value_for_path("abc", cc("abc", "4"))

        def dummy_contextual_modifier(conv, raw):
            return conv, raw

        self._trans = Transliterator(t, dummy_contextual_modifier)

    def test_simple(self):
        self.assertTrue(self._trans(Cord(), 'aaabcba').text, "2431")
        self.assertTrue(self._trans(Cord(), 'aaa dbcba').text, "21 d3c21")
        self.assertTrue(self._trans(Cord(), 'abcdefg').text, "4defg")
        self.assertTrue(self._trans(Cord(), 'aaaaaaa').text, "2221")
        self.assertTrue(self._trans(Cord(), 'abcab c').text, "413 c")
