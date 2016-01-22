from .utils import SrcBead, DstBead, Cord


class ContextualModifier:

    def __init__(self, contextual_rules, vowels, consonants):
        self._vowels = vowels
        self._consonants = consonants
        self._contextual_rules = contextual_rules

    def _match(self, subject, target):
        if subject == target:
            return True

        elif target == '[CONSONANT]':
            if subject in self._consonants:
                return True

        elif target == '[VOWEL]':
            if subject in self._vowels:
                return True

        else:
            return False

    def __call__(self, context, raw):
        # The format of contextuals is: (tuple, str, tuple)
        for context_targets, raw_target, result in self._contextual_rules:
            # Match raw target.
            if not raw.startswith(raw_target):
                continue

            # Match context targets. Rough workflow is -
            #   Start iterating targets(context) from right side.
            #   Choose equivalent subject from the actual context
            #   string. If there is none, an special subject '[START]'
            #   is produced. Match the subject and target. If any match
            #   fails, we discard the rule.
            try:
                failed = False
                for i, t in enumerate(reversed(context_targets)):
                    if i == len(context):
                        s = '[START]'
                    else:
                        s = context[-(i + 1)].v

                    if not self._match(s, t):
                        failed = True
                        break
                if failed:
                    continue

            except IndexError:
                continue

            # We have a match!
            src_bead = SrcBead(raw_target)
            dst_beads = [DstBead(c, src_bead) for c in result]
            return Cord(dst_beads), raw[len(raw_target):]

        return Cord(), raw
