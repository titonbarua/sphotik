
# vim: tabstop=4 expandtab shiftwidth=4
from utils import SrcBead, DstBead, Cord


class Vowelshaper:

    def __init__(self, rule):
        self.rule = rule

    def __call__(self, cord):
        for pos, bead in enumerate(cord):
            if bead.v not in self.rule.vowels:
                continue

            if 'FORCED_DIACRITIC' in bead.flags:
                continue

            if pos == 0:
                if 'DIACRITIC' in bead.flags:
                    bead.flags.remove('DIACRITIC')
                continue

            if cord[max(0, pos - 1)].v in self.rule.vowelhosts:
                bead.flags.add('DIACRITIC')
                continue

        return cord
