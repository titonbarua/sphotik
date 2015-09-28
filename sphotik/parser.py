from gi.repository import IBus

from sphotiklib.parser import Parser


class ParserIbus(Parser):
    preedit_cursor = ('|', 0x555555, 0xFFBBBB)
    preedit_cursor_alt = ('+', 0x555555, 0xBBFFBB)
    preedit_cursor_enabled = True

    chars_to_skip_while_moving = set(["\u09CD"])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chars_to_skip_while_moving.add(self.rule.modifier)

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
                    if v not in self.chars_to_skip_while_moving:
                        steps += -1
                except IndexError:
                    break
        else:
            while steps < 0 and self.cursor > 0:
                try:
                    self.cursor += -1
                    v = self.cord[self.cursor].v
                    if v not in self.chars_to_skip_while_moving:
                        steps += 1

                except IndexError:
                    break

        self.cursor = min(len(self.cord), max(0, self.cursor))

    def _render_text(self, cord):
        return IBus.Text.new_from_string(super()._render_text(cord))

    @property
    def preedit_text(self):
        return self._render_preddit_text(
            self.cord, self.cursor if self.preedit_cursor_enabled else None)

    def _render_preddit_text(self, cord, cursor):
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
    def auxiliary_text(self):
        return self._render_auxiliary_text(self.cord)

    def _render_auxiliary_text(self, cord):
        srcbeads = []
        for i, bead in enumerate(cord):
            if not i == 0:
                if bead.source is srcbeads[-1]:
                    continue
            srcbeads.append(bead.source)

        return IBus.Text.new_from_string(
            "".join([sb.v for sb in srcbeads]))
