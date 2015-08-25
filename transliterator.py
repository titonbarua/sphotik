import operator
from functools import reduce
from utils import SrcBead, DstBead


class Transliterator:

    def __init__(self, tree):
        self._tree = tree
        self.longest_path_size = tree.get_longest_subpath_size()

    def _make_bead(self, dst: str, src: str):
        sbead = SrcBead(src)
        if isinstance(dst, list) or isinstance(dst, tuple):
            return reduce(operator.add, [DstBead(d, sbead) for d in dst])
        else:
            return DstBead(dst, sbead)

    def _transliterate_a_letter(self, source_str):
        candidate = source_str[:self.longest_path_size]
        while candidate:
            try:
                converted = self._tree.get_value_for_path(candidate)
                if converted is None:
                    candidate = candidate[:-1]
                    continue

                converted_bead = self._make_bead(converted, candidate)
                unconverted = source_str[len(candidate):]
                return (converted_bead, unconverted)

            except KeyError:
                candidate = candidate[:-1]
                continue
        else:
            # Couldn't find a successful transliteration, which
            # implies that the first character of the roman string
            # is not part of any transliteration.
            converted_bead = self._make_bead(source_str[0], source_str[0])
            unconverted = source_str[1:]
            return (converted_bead, unconverted)

    def _transliterate(self, source_str):
        beads = []
        while source_str:
            bead, source_str = self._transliterate_a_letter(source_str)
            beads.append(bead)

        return reduce(operator.add, beads)

    def __call__(self, source_str):
        return self._transliterate(source_str)
