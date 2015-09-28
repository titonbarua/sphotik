#!/usr/bin/env python3
import sys
import string
import os.path
import unicodedata
from pkgutil import get_data
from tempfile import NamedTemporaryFile

from gi.repository import IBus, GLib
from gi.repository.IBus import ModifierType as Mod

from sphotiklib.parser import Parser
from sphotiklib.ruleparser import Rule

from .parser import ParserIbus


# Keys to look after. An example of uninteresting event is
# CTRL key press event ( note that this is seperate from
# CTRL + some other key press event ).
INTERESTING_KEYS = set([getattr(IBus, c) for c in (
    [
        "space",
        "Return",
        "BackSpace",
        "Delete",
        "Tab",

        "asciitilde",
        "grave",

        "exclam",
        "at",
        "numbersign",
        "dollar",
        "percent",
        "asciicircum",
        "ampersand",
        "asterisk",
        "parenleft",
        "parenright",
        "minus",
        "underscore",
        "plus",
        "equal",

        "colon",
        "semicolon",
        "quotedbl",
        "apostrophe",

        "less",
        "comma",
        "greater",
        "period",
        "question",
        "slash",

        "Left",
        "Right",
        "Up",
        "Down",
    ]
    + list(string.digits)
    + list(string.ascii_letters)
)])

# Ignore key release events.
STATES_TO_IGNORE = Mod.RELEASE_MASK

# Commit as soon as ALT/CTRL/SUPER modifiers are set.
# Pass the character unmodified as it is most probably
# an editor command.
STATES_TO_COMMIT_ASAP = (
    Mod.CONTROL_MASK
    | Mod.MOD1_MASK
    | Mod.SUPER_MASK
    | Mod.META_MASK
    | Mod.HYPER_MASK)


ENGINE_NAME = "sphotik"
ENGINE_BUS_NAME = "org.freedesktop.IBus.Sphotik"
COMPONENT_TEMPLATE = "sphotik.xml.tmpl"


def count_graphemes(text):
    """This is probably the most stupid grapheme counter ever,
    but hopefully it will be enough for our purpose.
    """
    return len([
        # Count all chars except unicode 'mark's.
        c for c in text if not unicodedata.category(c).startswith('M')])


class EngineSphotik(IBus.Engine):
    max_word_length = 40

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._parser = ParserIbus(Rule('avro'))

    def _update(self):
        petext = self._parser.preedit_text
        self.update_preedit_text_with_mode(
            petext,
            petext.get_length(),
            True,
            IBus.PreeditFocusMode.CLEAR)

        self.update_auxiliary_text(
            self._parser.auxiliary_text, len(self._parser.cord) > 0)

    def _commit(self):
        self.commit_text(self._parser.text)
        self._parser.clear()
        self._update()

    def _commit_upto_cursor(self):
        cursor=self._parser.cursor

        to_commit=self._parser.cord[:cursor]
        self.commit_text(self._parser._render_text(to_commit))

        to_retain=self._parser.cord[cursor:]
        self._parser=ParserIbus(self._parser.rule, to_retain, 0)

        self._update()

    def _idle_update(self):
        GLib.idle_add(self._update)

    def do_enable(self):
        self._parser.clear()

    def do_disable(self):
        self._parser.clear()

    def do_focus_in(self):
        self._parser.clear()

    def do_focus_out(self):
        self._parser.clear()

    def do_process_key_event(self, keyval, keycode, state):
        if keyval not in INTERESTING_KEYS:
            return False

        if state & STATES_TO_IGNORE:
            return False

        if state & STATES_TO_COMMIT_ASAP:
            self._commit()
            return False

        if keyval in (IBus.space, IBus.Return):
            self._commit_upto_cursor()
            return False

        elif keyval == IBus.Tab:
            if len(self._parser.cord) == 0:
                return False

            self._commit()
            return True

        elif keyval == IBus.BackSpace:
            if len(self._parser.cord) == 0:
                return False

            self._parser.delete(-1)
            self._idle_update()
            return True

        elif keyval == IBus.Delete:
            if self._parser.cursor >= len(self._parser.cord):
                return False

            self._parser.delete(1)
            self._idle_update()
            return True

        elif keyval == IBus.Left:
            if len(self._parser.cord) == 0:
                return False

            if self._parser.cursor == 0:
                # Commit the current text and update immediately.
                text=self._parser.text
                self.commit_text(text)
                self._parser.clear()
                self._update()

                # Since our cursor is placed at right side of the committed
                # text, let's go back to previous position by going left by
                # the number of graphemes commited. Go an extra step back to
                # account for the actual key press.
                for x in range(count_graphemes(text.get_text()) + 1):
                    self.forward_key_event(keyval, keycode, state)

                return True

            self._parser.normcursor += -1
            self._idle_update()
            return True

        elif keyval == IBus.Right:
            if len(self._parser.cord) == 0:
                return False

            self._parser.normcursor += 1
            self._idle_update()
            return True

        elif keyval in (IBus.Up, IBus.Down):
            self._commit()
            return False

        else:
            keystr=IBus.keyval_to_unicode(keyval)
            self._parser.insert(keystr)

            if len(self._parser.cord) >= self.max_word_length:
                self._commit()
            else:
                self._idle_update()

            return True


def render_component_template(version, run_path, setup_path, icon_path):
    component_xml=(
        get_data(__package__, COMPONENT_TEMPLATE)
        .decode()
        .format(
            sphotik_version=version,
            sphotik_exec_path=run_path,
            sphotik_setup_path=setup_path,
            sphotik_icon_path=icon_path,
        )
    )

    return component_xml


def main():
    mainloop=GLib.MainLoop()
    bus=IBus.Bus()

    def quit(*args, **kwargs):
        mainloop.quit()

    bus.connect("disconnected", quit)

    factory=IBus.Factory.new(bus.get_connection())
    factory.add_engine(ENGINE_NAME, EngineSphotik)

    if len(sys.argv) > 1 and sys.argv[1] == '--ibus':
        bus.request_name(ENGINE_BUS_NAME, 0)
    else:
        # Let us do the ridiculous procedure of rendering the xml template
        # file and then saving it's content to a temporary file, then pass
        # the filename to generate a new ibus component!
        #-------------------------------------------------------------------\
        version_file=os.path.join(
            os.path.dirname(__file__), "..", "VERSION.txt")
        with open(version_file) as f:
            version=f.read().strip()

        component_data=render_component_template(
            version, '{} --ibus'.format(os.path.realpath(sys.argv[0])), '', '')

        with NamedTemporaryFile() as f:
            f.write(component_data.encode())  # Write data to a file.
            f.seek(0)  # Rewind.
            bus.register_component(IBus.Component.new_from_file(f.name))
        #-------------------------------------------------------------------/
        bus.set_global_engine_async(ENGINE_NAME, -1, None, None, None)

    mainloop.run()

if __name__ == "__main__":
    sys.path.insert(0, '..')
    main()
