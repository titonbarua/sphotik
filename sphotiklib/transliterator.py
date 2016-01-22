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

    def _transliterate_a_letter(self, source_str):
        candidate = source_str[:self.longest_path_size]
        while candidate:
            try:
                converted = self._tree.get_value_for_path(candidate)
                if converted is None:
                    candidate = candidate[:-1]
                    continue

                unconverted = source_str[len(candidate):]
                return (deepcopy(converted), unconverted)

            except KeyError:
                candidate = candidate[:-1]
                continue
        else:
            # Couldn't find a successful transliteration, which
            # implies that the first character of the roman string
            # is not part of any transliteration.
            unconverted = source_str[1:]
            converted = Cord([
                DstBead(source_str[0], SrcBead(source_str[0]))])
            return (converted, unconverted)

    def _transliterate(self, source_str):
        converted = Cord()
        while True:
            converted, source_str = self._contextual_modifier(
                converted, source_str)
            if len(source_str) == 0:
                break

            newconv, source_str = self._transliterate_a_letter(source_str)
            converted += newconv
            if len(source_str) == 0:
                break

        return converted

    def __call__(self, source_str):
        return self._transliterate(source_str)


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

        self._trans = Transliterator(t)

    def test_simple(self):
        self.assertTrue(self._trans('aaabcba').text, "2431")
        self.assertTrue(self._trans('aaa dbcba').text, "21 d3c21")
        self.assertTrue(self._trans('abcdefg').text, "4defg")
        self.assertTrue(self._trans('aaaaaaa').text, "2221")
        self.assertTrue(self._trans('abcab c').text, "413 c")
