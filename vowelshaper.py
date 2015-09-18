
# vim: tabstop=4 expandtab shiftwidth=4
from utils import SrcBead, DstBead, Cord

class Vowelshaper:
    def __init__(self, rule):
        self.rule = rule

    def _to_diacritic(self, bead):
        try:
            diac = self.rule.vowelmap[bead.v]
            return DstBead(diac, bead.source, bead.flags)
        except KeyError:
            return bead
        

    def __call__(self, input_cord):
        output_cord = Cord()

        for pos, bead in enumerate(input_cord):
            if bead.v not in self.rule.vowels:
                output_cord += bead
                continue

            if 'FORCED_DIACRITIC' in bead.flags:
                output_cord += self._to_diacritic(bead)
                continue

            if pos == 0:
                output_cord += bead
                continue

            if input_cord[max(0, pos-1)].v in self.rule.vowelhosts:
                output_cord += self._to_diacritic(bead)
                continue

            output_cord += bead

        return output_cord
