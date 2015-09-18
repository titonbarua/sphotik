# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

from utils import DstBead, Cord


class Conjunctor:

    def __init__(self, conjtree):
        self.conjtree = conjtree
        self.longest_conj_size = conjtree.get_longest_subpath_size()

    def _make_a_conjunction(self, unjoined_cord):
        candidate = unjoined_cord[:self.longest_conj_size]
        while len(candidate):
            try:
                # See if current candidate yields a conjunction.
                path = [c.v for c in candidate]
                value = self.conjtree.get_value_for_path(path)
                if value is None:
                    candidate = candidate[:-1]
                    continue

                for bead in candidate[1:]:
                    bead.add_flags('CONJOINED')

                return (candidate, unjoined_cord[len(candidate):])

            except KeyError:
                candidate = candidate[:-1]
                continue
        else:
            unjoinable = unjoined_cord[:1]
            for bead in unjoinable:
                bead.remove_flags('CONJOINED')

            return (unjoinable, unjoined_cord[1:])

    def _conjoin(self, unjoined_cord):
        conjoined = Cord()
        while len(unjoined_cord):
            newjoined, unjoined_cord = self._make_a_conjunction(unjoined_cord)
            conjoined += newjoined

        return conjoined

    def __call__(self, unjoined_cord):
        return self._conjoin(unjoined_cord)
