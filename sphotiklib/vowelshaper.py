
# vim: tabstop=4 expandtab shiftwidth=4
from .utils import SrcBead, DstBead, Cord


class Vowelshaper:

    def __init__(self, vowels, vowelhosts):
        self.vowels = vowels
        self.vowelhosts = vowelhosts

    def __call__(self, cord):
        for pos, bead in enumerate(cord):
            if bead.v not in self.vowels:
                continue

            if 'FORCED_DIACRITIC' in bead.flags:
                continue

            if pos == 0:
                bead.remove_flags('DIACRITIC')
                continue

            if cord[max(0, pos - 1)].v in self.vowelhosts:
                bead.add_flags('DIACRITIC')
                continue
            else:
                bead.remove_flags('DIACRITIC')
                continue

        return cord
