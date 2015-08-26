# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import unittest
from copy import copy
from itertools import product, chain


def _make_conjunction_parser(multi_start='(', multi_end=')'):
    def parse(line):
        """
        This function parses a line of conjunction rule into a nested list.
        """
        conjrule = []
        multichoice = False

        for c in line.strip():
            # Eliminate spacing characters.
            c = c.strip()
            if not c:
                continue

            if c.lower() == multi_start.lower():
                # Nesting is not supported..
                if multichoice:
                    continue

                # Start of a multiple choice entry ...
                conjrule.append(list())
                multichoice = True
                continue

            if c.lower() == multi_end.lower():
                # End of the multiple choice entry ...
                multichoice = False
                continue

            if multichoice:
                # Inside multiple choice entry ...
                conjrule[-1].append(c)
                continue

            # Just a sinlge entry character ...
            conjrule.append(c)

        return conjrule

    def express(conj):
        """
        Express the nested list into a list of all possible conjunctions.
        """
        multichoices = []
        monochoices = []

        # The following algorithm(in general) -
        #   -> Break the nested list into fixed(mono choice) and
        #      variable(multi choice) portions.
        #
        #   -> Evaluate all possible combinations from the variable parts.
        #
        #   -> Combine results from above with fixed choice parts,
        #      producing a combo for each variation.
        #-------------------------------------------------------------,
        for i, c in enumerate(conj):
            if isinstance(c, list) or isinstance(c, tuple):
                if len(c):
                    multichoices.append((i, c))
            else:
                monochoices.append(c)

        exprlist = []

        products = list(product(*(e[1] for e in multichoices)))
        for p in products:
            expr = copy(monochoices)
            for j, (i, c) in enumerate(multichoices):
                expr.insert(i, p[j])

            if len(expr):
                exprlist.append("".join(expr))
        #-------------------------------------------------------------'

        return exprlist

    return (lambda x: express(parse(x)))


parse_conjunction_line = _make_conjunction_parser()


class TestConjunctionParser(unittest.TestCase):

    def _test_conjunction_parsing(self, inp, exp_outp):
        outp = set(chain(*map(parse, inp.splitlines())))
        self.assertEqual(outp, set(exp_outp))

    def test_1(self):
        inp = "ক(কটতবমলসষ)\nকষ(বণরয)\nখ(র)\nগগ()\n(ঘ  \tঙ)\n()()()\n"
        exp_outp = [
            'কক', 'কট', 'কত', 'কব', 'কম', 'কল', 'কস',
            'কষ', 'কষব', 'কষণ', 'কষর', 'কষয', 'খর', 'গগ', 'ঘ', 'ঙ',
        ]
        self._test_conjunction_parsing(inp, exp_outp)
