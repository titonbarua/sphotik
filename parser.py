
from ruleparser import Rule
from vowelshaper import Vowelshaper
from utils import SrcBead, DstBead, Cord
from transliterator import Transliterator


class Parser:

    def __init__(self, transliterator, cord=Cord()):
        self.transliterator = transliterator
        self.cord = cord
        self.cursor = len(cord)

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

    def delete(self, steps):
        from_ = self.cursor
        to = max(0, self.cursor + steps)
        start, end = min(from_, to), max(from_, to)
        self.cord = self.cord[:start] + self.cord[end:]
        if steps < 0:
            self.cursor = max(0, self.cursor + steps)


if __name__ == "__main__":
    rule = Rule('avro_rule')
    trans = Transliterator(rule.transtree)
    parser = Parser(trans)

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

    vs = Vowelshaper(rule)
    print(vs(parser.cord))
    print(vs(parser.cord).text)
