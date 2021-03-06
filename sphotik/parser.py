from copy import deepcopy

from gi.repository import IBus

from sphotiklib.parser import Parser


class ParserIbus(Parser):
    preedit_cursor = ('|', 0x555555, 0xFFBBBB)
    preedit_cursor_alt = ('+', 0x555555, 0xBBFFBB)
    preedit_cursor_enabled = True

    # TODO: Move these parameters to rule files.
    unaccounted_in_deletion = set(["\u09CD", "`"])
    unaccounted_in_cursor_movement = set(["\u09CD", "`"])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def delete(self, steps):
        """Delete characters, but don't count metachars."""
        taken_steps = 0
        target_steps = steps

        if target_steps > 0:
            start, end = self.cursor, self.cursor
            while target_steps > 0:
                try:
                    end += 1
                    taken_steps += 1
                    if self.cord[end].v not in self.unaccounted_in_deletion:
                        target_steps += -1

                except IndexError:
                    break
        else:
            start, end = self.cursor, self.cursor
            while target_steps < 0:
                try:
                    start = max(0, start - 1)
                    taken_steps += 1
                    if self.cord[start].v not in self.unaccounted_in_deletion:
                        target_steps += 1

                except IndexError:
                    break

        self.cord = self.cord[:start] + self.cord[end:]
        self.cursor = (
            max(0, self.cursor - taken_steps)
                if (steps < 0) else self.cursor)

        self.cord = self._adjust_flags(self.cord)

    @property
    def normcursor(self):
        """A normalized cursor is a cursor that skips some characters
        while moving.

        Normalized cursor is a necessity because modifier chars and
        some other things like the 'hasanta' should be skipped while
        moving the cursor with left and right arrows.
        """
        return self.cursor

    @normcursor.setter
    def normcursor(self, value):
        steps = value - self.cursor
        if steps >= 0:
            while steps > 0 and self.cursor < len(self.cord):
                try:
                    self.cursor += 1
                    v = self.cord[self.cursor].v
                    if v not in self.unaccounted_in_cursor_movement:
                        steps += -1
                except IndexError:
                    break
        else:
            while steps < 0 and self.cursor > 0:
                try:
                    self.cursor += -1
                    v = self.cord[self.cursor].v
                    if v not in self.unaccounted_in_cursor_movement:
                        steps += 1

                except IndexError:
                    break

        self.cursor = min(len(self.cord), max(0, self.cursor))

    @property
    def itext(self):
        return self._render_itext(self.cord)

    def _render_itext(self, cord):
        return IBus.Text.new_from_string(super().render_text(cord))

    @property
    def preedit_itext(self):
        return self._render_preddit_itext(
            self.cord, self.cursor if self.preedit_cursor_enabled else None)

    def _render_preddit_itext(self, cord, cursor):
        output = ""
        alt_cursor_used = False
        rendered_cursor_pos = None

        for i, bead in enumerate(cord):
            show_cursor = (i == cursor)

            if (('DIACRITIC' in bead.flags) or
                    ('FORCED_DIACRITICT' in bead.flags)):
                if show_cursor:
                    rendered_cursor_pos = len(output)
                    output += (self.preedit_cursor_alt[0] + bead.v)
                    alt_cursor_used = True
                else:
                    output += self._to_diacritic(bead).v
                continue

            if 'CONJOINED' in bead.flags:
                if show_cursor:
                    rendered_cursor_pos = len(output)
                    output += (self.preedit_cursor_alt[0] + bead.v)
                    alt_cursor_used = True
                else:
                    output += (self.rule.conjglue + bead.v)
                continue

            if show_cursor:
                rendered_cursor_pos = len(output)
                output += self.preedit_cursor[0]

            if bead.v == self.rule.modifier:
                continue

            output += bead.v

        t = IBus.Text.new_from_string(output)

        if rendered_cursor_pos is not None:
            if alt_cursor_used:
                fgc, bgc = self.preedit_cursor_alt[1:]
            else:
                fgc, bgc = self.preedit_cursor[1:]

            # Add background color.
            if bgc is not None:
                t.append_attribute(
                    IBus.AttrType.BACKGROUND,
                    bgc,
                    rendered_cursor_pos,
                    rendered_cursor_pos + 1)

            # Add foreground color.
            if fgc is not None:
                t.append_attribute(
                    IBus.AttrType.FOREGROUND,
                    fgc,
                    rendered_cursor_pos,
                    rendered_cursor_pos + 1)

        return t

    @property
    def auxiliary_itext(self):
        return self._render_auxiliary_itext(self.cord)

    def _render_auxiliary_itext(self, cord):
        return IBus.Text.new_from_string(self.render_input_text(cord))

    @property
    def input_text(self):
        return self.render_input_text(self.cord)

    def render_input_text(self, cord):
        srcbeads = []
        for i, bead in enumerate(cord):
            if not i == 0:
                if bead.source is srcbeads[-1]:
                    continue
            srcbeads.append(bead.source)

        return "".join([sb.v for sb in srcbeads])

    def suggest_flag_modifications(self):
        """
        Create some basic suggestions by modifying flags.

        By suggesting last constructed conjunction to be disjoined and/or
        last diacritic vowel to be distinct, we can account for almost all
        of the annoyances of automatic vowelform and conjunction creation.
        """
        suggestions = []

        def suggest_without_flags(index, flags_to_remove):
            newbead = deepcopy(self.cord[index])
            newbead.remove_flags(*flags_to_remove)

            newcord = self.cord[:index] + newbead + self.cord[index + 1:]
            suggestions.append(self.render_text(newcord))

        # Find first (from right) consonant that is conjoined and
        # suggest it to be disjoined.
        for i, bead in reversed(list(enumerate(self.cord))):
            if 'CONJOINED' in bead.flags:
                suggest_without_flags(i, ('CONJOINED',))
                break

        # Find first (from left) consonant that is conjoined and
        # suggest it to be disjoined.
        for i, bead in enumerate(self.cord):
            if 'CONJOINED' in bead.flags:
                suggest_without_flags(i, ('CONJOINED',))
                break

        # Shape of these vowels are usually ambiguous except at the
        # start of a word.
        vowels_to_modify = (
            "\N{BENGALI LETTER I}",
            "\N{BENGALI LETTER II}",
            "\N{BENGALI LETTER O}",
            "\N{BENGALI LETTER U}",
            "\N{BENGALI LETTER UU}",)

        # Find first (from right) vowel that is diacritic and
        # suggest it to be distinct.
        for i, bead in reversed(list(enumerate(self.cord))):
            if bead.v not in vowels_to_modify:
                continue

            if (('DIACRITIC' in bead.flags) or
                    ('FORCED_DIACRITIC' in bead.flags)):
                suggest_without_flags(i, ('DIACRITIC', 'FORCED_DIACRITIC'))
                break

        # Find first (from left) vowel that is diacritic and
        # suggest it to be distinct.
        for i, bead in enumerate(self.cord):
            if bead.v not in vowels_to_modify:
                continue

            if (('DIACRITIC' in bead.flags) or
                    ('FORCED_DIACRITIC' in bead.flags)):
                suggest_without_flags(i, ('DIACRITIC', 'FORCED_DIACRITIC'))
                break

        return suggestions
