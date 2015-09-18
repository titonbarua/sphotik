
from ruleparser import Rule
from conjunctor import Conjunctor
from vowelshaper import Vowelshaper
from utils import SrcBead, DstBead, Cord
from transliterator import Transliterator


class Parser:

    def __init__(self, rule, cord=Cord()):
        self.rule = rule
        self.transliterator = Transliterator(rule.transtree)
        self.vowelshaper = Vowelshaper(rule.vowels, rule.vowelhosts)
        self.conjunctor = Conjunctor(rule.conjtree)
        self.cord = cord
        self.cursor = len(cord)

    def _adjust_flags(self):
        self.cord = self.vowelshaper(self.cord)
        self.cord = self.conjunctor(self.cord)

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
        self.cord = newcord
        self.cursor += len(newcord)

    def insert(self, text):
        if self.cursor >= len(self.cord):
            self._insert_at_rightmost(text)
        else:
            self._insert_at_middle(text)

        self._adjust_flags()

    def delete(self, steps):
        from_ = self.cursor
        to = max(0, self.cursor + steps)
        start, end = min(from_, to), max(from_, to)
        self.cord = self.cord[:start] + self.cord[end:]
        if steps < 0:
            self.cursor = max(0, self.cursor + steps)

        self._adjust_flags()

    @property
    def text(self):
        output = ""
        for bead in self.cord:
            if (('DIACRITIC' in bead.flags) or
                    ('FORCED_DIACRITIC' in bead.flags)):
                output += self._to_diacritic(bead).v
                continue

            if 'CONJOINED' in bead.flags:
                output += self.rule.conjglue + bead.v
                continue

            output += bead.v

        return output

    def _to_diacritic(self, bead):
        try:
            diac = self.rule.vowelmap[bead.v]
            return DstBead(diac, bead.source, bead.flags)
        except KeyError:
            return bead


if __name__ == "__main__":
    rule = Rule('avro_rule')
    parser = Parser(rule)

    parser.insert('a')
    parser.insert('a')
    parser.insert('mar sonar bangla')
    print(parser.cord)

    parser.cursor += -3
    parser.delete(-100)
    print(parser.cord)

    parser.delete(100)
    print(parser.cord)

    parser.insert('a`mi` tOmay valobashi')
    print(parser.cord)
    print(parser.text)

    parser.insert(' kosTe achi skondho')
    print(parser.cord)
    print(parser.text)
