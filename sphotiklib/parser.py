
import unittest

from .ruleparser import Rule
from .utils import SrcBead, DstBead, Cord


class Parser:

    def __init__(self, rule, cord=Cord(), insertion_sequence=0):
        self.rule = rule
        self.transliterator = rule.transliterator
        self.vowelshaper = rule.vowelshaper
        self.conjunctor = rule.conjunctor
        self.cord = self._adjust_flags(cord)
        self.cursor = len(self.cord)

        # Insertion sequence is a necessary ugliness. It is an
        # integer that is incremented everytime an insertion is made.
        # Also, an inserted bead has this number attached to it, so
        # that beads inserted in sequence can be related with one another.
        # 
        # This is important for inserting new characters in the middle, as
        # without it, we have will either have to revert unrelated characters
        # inserted in a different context or sacrifice multi-character
        # transliterations.
        self.insseq = insertion_sequence

    def _adjust_flags(self, cord):
        return self.conjunctor(self.vowelshaper(cord))

    def _insert(self, text):
        lps = self.transliterator.longest_path_size

        # If the cursor is positioned at the middle of the cord,
        # reverting texts right to the cursor makes no sense.
        revertible, preserved_right = (
            self.cord[:self.cursor], self.cord[self.cursor:])

        reverted = ""
        backstep = 1
        # We will keep reverting characters from back until we have
        # roman chars enough to cover the longest possible transliteration
        # path. This is like an worst case scenerio management.
        while len(reverted) < lps:
            try:
                # Collect the rightmost bead.
                bead = revertible[-1]

                # Check if the collected bead is relevant (in sequence).
                # Otherwise, reverting them is pointless.
                if self.insseq - bead.insseq != backstep:
                    break

                # Collect the reverted source text.
                reverted = bead.source.v + reverted

                # Adjust the revertible cord.
                n_reverted_cords = len(bead.source.destinations)
                revertible = revertible[
                    :max(0, len(revertible) - n_reverted_cords)]

                backstep += n_reverted_cords

            except IndexError:
                break

        # Whatever is 'left' in the revertible stays unchanged.
        preserved_left = revertible

        # Perform the transliteration.
        reforged = self.transliterator(
                preserved_left, reverted + text)

        # Attach insertion sequence to the reforged beads.
        for bead in reforged:
            bead.insseq = self.insseq
            self.insseq += 1

        self.cord = preserved_left + reforged + preserved_right
        self.cursor = len(preserved_left) + len(reforged)

    def insert(self, text):
        self._insert(text)
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

    def move_cursor_to_rightmost(self):
        self.cursor = len(self.cord)

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

    def test_insertion_at_middle(self):
        parser = Parser(self.rule)
        parser.insert('polu')
        org_text = parser.text

        parser.cursor = 1
        parser.insert('h')

        # The result should be 'পহলু', not 'ফলু'.
        # This is the expected behavior, since the 'p' was inserted
        # at a different context than the 'h', 'ph' being interpreted
        # as part of same transliteration is wrong.
        print(
            "Test of insertion at middle: '{}' -> '{}"
            .format(org_text, parser.text))
