
import unittest

from .ruleparser import Rule
from .conjunctor import Conjunctor
from .vowelshaper import Vowelshaper
from .utils import SrcBead, DstBead, Cord
from .transliterator import Transliterator


class Parser:

    def __init__(self, rule, cord=Cord()):
        self.rule = rule
        self.transliterator = Transliterator(rule.transtree)
        self.vowelshaper = Vowelshaper(rule.vowels, rule.vowelhosts)
        self.conjunctor = Conjunctor(rule.conjtree)
        self.cord = cord
        self.cursor = len(cord)

    def _adjust_flags(self, cord):
        return self.conjunctor(self.vowelshaper(cord))

    def _insert_at_rightmost(self, text):
        lps = self.transliterator.longest_path_size

        reverted = ""
        while len(reverted) < lps:
            try:
                lastdst = self.cord[-1]
                lastsrc = lastdst.source
                reverted = lastsrc.v + reverted
                self.cord = self.cord[
                    :max(0, len(self.cord) - len(lastsrc.destinations))]
            except IndexError:
                break

        self.cord = self.cord + self.transliterator(reverted + text)
        self.cursor = len(self.cord)

    def _insert_at_middle(self, text):
        newcord = self.transliterator(text)
        self.cord = self.cord[:self.cursor] + newcord + self.cord[self.cursor:]
        self.cursor += len(newcord)

    def insert(self, text):
        if self.cursor >= len(self.cord):
            self._insert_at_rightmost(text)
        else:
            self._insert_at_middle(text)

        self.cord = self._adjust_flags(self.cord)

    def delete(self, steps):
        from_ = self.cursor
        to = max(0, self.cursor + steps)
        start, end = min(from_, to), max(from_, to)
        self.cord = self.cord[:start] + self.cord[end:]
        if steps < 0:
            self.cursor = max(0, self.cursor + steps)

        self.cord = self._adjust_flags(self.cord)

    def clear(self):
        self.cord = Cord()
        self.cursor = 0

    @property
    def text(self):
        return self._render_text(self.cord)

    def _render_text(self, cord):
        output = ""
        for bead in cord:
            # Change vowels to diacritic form when flagged.
            if (('DIACRITIC' in bead.flags) or
                    ('FORCED_DIACRITIC' in bead.flags)):
                output += self._to_diacritic(bead).v
                continue

            # Add a conjunction glue in front of every
            # conjoined character.
            if 'CONJOINED' in bead.flags:
                output += self.rule.conjglue + bead.v
                continue

            # Hide the modifier character.
            if bead.v == self.rule.modifier:
                continue

            output += bead.v

        return output

    def _to_diacritic(self, bead):
        try:
            diac = self.rule.vowelmap[bead.v]
            return DstBead(diac, bead.source, bead.flags)
        except KeyError:
            return bead


class _TestParser(unittest.TestCase):

    def setUp(self):
        self.rule = Rule('avro')

    def test_simple(self):
        parser = Parser(self.rule)
        parser.insert('amar sOnar bangla')
        # Automatic test assertions are useless in this case IMO.
        # I am not gonna bother with them.
        print("'amar sOnar bagnla' -> '{}'".format(parser.text))

    def test_simple_onebyone(self):
        parser = Parser(self.rule)
        for c in 'amar sOnar bangla':
            parser.insert(c)
        print("(one-by-one) 'amar sOnar bagnla' -> '{}'".format(parser.text))

    def test_front_deletion(self):
        parser = Parser(self.rule)
        parser.insert('amar sOnar bangla')
        parser.cursor = 5
        parser.delete(6)
        print("(delete front) Removed 'sOnar ' -> '{}'".format(parser.text))

    def test_back_deletion(self):
        parser = Parser(self.rule)
        parser.insert('amar sOnar bangla')
        parser.cursor = 5
        parser.delete(-100)
        print("(delete back) Removed 'amar ' -> '{}'".format(parser.text))

    def test_back_deletion_and_insertion(self):
        parser = Parser(self.rule)
        parser.insert('amar sOnar bangla')
        parser.cursor = 5
        parser.delete(-100)
        parser.insert('tOmar ')
        print(
            "(delete back + insert)"
            " Replace 'amar ' with 'tomar ' -> '{}'".format(parser.text))

    def test_forced_diacritic(self):
        parser = Parser(self.rule)
        parser.insert('a`mar')
        print("(with forced diacritic) 'a`mar' -> '{}'".format(parser.text))

    def test_conjunctions(self):
        parser = Parser(self.rule)
        parser.insert('kukkuT sondhZa kingkortobZbimURh')
        print("conjunction formation -> '{}'".format(parser.text))

    def test_conjunction_bypass(self):
        parser = Parser(self.rule)
        parser.insert('am`ra')
        print("(conjunction bypass) 'am`ra' -> '{}'".format(parser.text))

    def test_vowelshaping_bypass(self):
        parser = Parser(self.rule)
        parser.insert('h`Oya')
        print("(vowelshaping bypass) 'h`Oya' -> '{}'".format(parser.text))

    def test_forced_jo_fola(self):
        parser = Parser(self.rule)
        parser.insert('obZy')
        print("(forced jo-fola) 'obZy' -> '{}'".format(parser.text))
