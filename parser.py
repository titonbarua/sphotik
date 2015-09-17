
from ruleparser import Rule
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

        self.cord = self.transliterator(reverted + text)
        self.cursor = len(self.cord)

    def _insert_at_middle(self, text):
        newcord = self.transliterate(text)
        self.cord = newcord
        self.cursor += len(newcord)

    def insert(self, text):
        if self.cursor >= len(self.cord):
            self._insert_at_rightmost(text)
        else:
            self._insert_at_middle(text)

    def delete_back(self, number):
        assert number >= 0


if __name__ == "__main__":
    rule = Rule('avro_rule')
    trans = Transliterator(rule.transtree)
    parser = Parser(trans)

    parser.insert('a')
    parser.insert('a')
    parser.insert('mar sonar bangla')
    print(parser.cord)
