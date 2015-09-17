import operator
from functools import reduce
from utils import SrcBead, DstBead, Cord


class Transliterator:

    def __init__(self, tree):
        self._tree = tree
        self.longest_path_size = tree.get_longest_subpath_size()

    def _transliterate_a_letter(self, source_str):
        candidate = source_str[:self.longest_path_size]
        while candidate:
            try:
                converted = self._tree.get_value_for_path(candidate)
                if converted is None:
                    candidate = candidate[:-1]
                    continue

                unconverted = source_str[len(candidate):]
                return (converted, unconverted)

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
        while source_str:
            newconv, source_str = self._transliterate_a_letter(source_str)
            converted += newconv

        return converted

    def __call__(self, source_str):
        return self._transliterate(source_str)
